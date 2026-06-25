#!/usr/bin/env python3
"""
2.4_dimensional_drill_down.py

For every confirmed anomaly in anomaly_results.csv, identifies which
dimensional slice (country, segment, category, channel, etc.) is the
largest contributor to the aggregate KPI deviation.

Algorithm per anomaly
─────────────────────
1. Look up applicable dimensional datasets from dim_kpi_registry.json.
   Web-traffic KPIs have no sub-dimensions -> write a null row and skip.
2. Pre-computed 7-day rolling z-scores (matching Step 1.3 methodology)
   are loaded once per dimensional file, then queried at the anomaly date.
3. For every (dimension_name, dimension_value) pair on the anomaly date,
   compute:
     z_score          = (actual - rolling_mean) / rolling_std
     contribution_pct = (dim_actual - dim_expected) / |agg_deviation| × 100
4. Rank all pairs by |z_score|, keep the top 3.

Inputs
──────
  data/detection/anomaly_results.csv          (Step 2.3 output — 181 rows)
  data/processed/dimensional/dim_*.csv        (Step 1.4 output — 5 files)
  data/processed/dimensional/dim_kpi_registry.json

Output
──────
  data/detection/dimensional_drill_down.csv   (181 rows × 15 columns)

  Columns: anomaly_id | has_dimensional_breakdown | n_dimensions_checked |
           dim_1_name | dim_1_value | dim_1_z_score | dim_1_contribution_pct |
           dim_2_* | dim_3_*

Note: dimensional_hypothesis_confirmed (does the top dim slice also show
an anomaly in the suspected_driver_kpi?) is computed in Step 3.4, where
both this output and rca_graph_results.csv are available simultaneously.

Run from project root:
    python scripts/detection/2.4_dimensional_drill_down.py
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

BASE     = Path(__file__).resolve().parent.parent.parent
DATA     = BASE / "data"
DIM_DIR  = DATA / "processed" / "dimensional"

INPUT_ANOMALIES = DATA / "detection"  / "anomaly_results.csv"
OUTPUT_CSV      = DATA / "detection"  / "dimensional_drill_down.csv"
REGISTRY_JSON   = DIM_DIR / "dim_kpi_registry.json"

ROLLING_WINDOW = 7        # must match Step 1.3 and Step 1.4
Z_THRESH_DIM   = 1.5      # minimum |z| to treat a dimensional slice as anomalous

OUTPUT_COLS = [
    "anomaly_id",
    "has_dimensional_breakdown",
    "dim_data_sufficient",        # True = at least 1 slice had enough rolling history to score
    "n_dimensions_checked",
    "dim_1_name", "dim_1_value", "dim_1_z_score", "dim_1_contribution_pct",
    "dim_2_name", "dim_2_value", "dim_2_z_score", "dim_2_contribution_pct",
    "dim_3_name", "dim_3_value", "dim_3_z_score", "dim_3_contribution_pct",
]


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Load inputs
# ─────────────────────────────────────────────────────────────────────────────

def load_anomalies() -> pd.DataFrame:
    df = pd.read_csv(INPUT_ANOMALIES, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    print(f"  anomaly_results  : {len(df):>4} rows  "
          f"({df['kpi'].nunique()} KPIs, "
          f"{df['date'].min().date()} to {df['date'].max().date()})")
    return df


def load_registry() -> dict:
    with open(REGISTRY_JSON, encoding="utf-8") as fh:
        reg = json.load(fh)
    kpis_with_dims    = sum(1 for v in reg.values() if v)
    kpis_without_dims = sum(1 for v in reg.values() if not v)
    print(f"  kpi_registry     : {len(reg)} KPIs  "
          f"({kpis_with_dims} with dims, {kpis_without_dims} without)")
    return reg


def load_dimensional_files() -> dict[str, pd.DataFrame]:
    """Load all five dim_*.csv files keyed by filename."""
    files = sorted(DIM_DIR.glob("dim_*.csv"))
    result: dict[str, pd.DataFrame] = {}
    for f in files:
        df = pd.read_csv(f, parse_dates=["date"])
        result[f.name] = df
        print(f"  {f.name:<36} : {len(df):>7,} rows")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Pre-compute rolling z-scores for every dimensional file
#
# Groups by (dimension_name, dimension_value, kpi_name), sorts by date, then
# computes the same 7-day rolling mean / std as Step 1.3 so the z-score
# methodology is identical across aggregate and dimensional scoring.
#
# expected_value = rolling_mean.shift(1): what we would have predicted for
# this slice on date t based on the t-7 … t-1 baseline.  Used to compute
# contribution_pct (the share of total aggregate deviation coming from this
# specific dimensional slice).
# ─────────────────────────────────────────────────────────────────────────────

GRP_COLS = ["dimension_name", "dimension_value", "kpi_name"]


def precompute_rolling_stats(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(GRP_COLS + ["date"]).reset_index(drop=True)

    grp = df.groupby(GRP_COLS, sort=False)

    df["rolling_mean"] = grp["kpi_value"].transform(
        lambda s: s.rolling(ROLLING_WINDOW, min_periods=1).mean()
    )
    df["rolling_std"] = grp["kpi_value"].transform(
        lambda s: s.rolling(ROLLING_WINDOW, min_periods=2).std()
    )
    # expected_value: yesterday's rolling mean — forward-looking baseline for t
    df["expected_value"] = grp["rolling_mean"].transform(lambda s: s.shift(1))

    safe_std = df["rolling_std"].replace(0, np.nan)
    df["z_score"] = ((df["kpi_value"] - df["rolling_mean"]) / safe_std).round(4)

    return df


def build_precomputed(dim_files: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    print("\nPre-computing rolling z-scores per dimensional file...")
    precomputed: dict[str, pd.DataFrame] = {}
    for fname, df in dim_files.items():
        precomputed[fname] = precompute_rolling_stats(df)
        n_groups = precomputed[fname].groupby(GRP_COLS).ngroups
        print(f"  {fname:<36} : {n_groups:>5,} groups computed")
    return precomputed


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Score one anomaly
# ─────────────────────────────────────────────────────────────────────────────

def _null_row(anomaly_id: str, has_breakdown: bool) -> dict:
    row: dict = {
        "anomaly_id":               anomaly_id,
        "has_dimensional_breakdown": has_breakdown,
        "dim_data_sufficient":      False,
        "n_dimensions_checked":     0,
    }
    for i in range(1, 4):
        row[f"dim_{i}_name"]             = None
        row[f"dim_{i}_value"]            = None
        row[f"dim_{i}_z_score"]          = None
        row[f"dim_{i}_contribution_pct"] = None
    return row


def score_anomaly(
    anomaly: pd.Series,
    precomputed: dict[str, pd.DataFrame],
    registry: dict,
) -> dict:
    anomaly_id   = anomaly["anomaly_id"]
    date         = anomaly["date"]           # already datetime64 from parse_dates
    kpi          = anomaly["kpi"]
    agg_actual   = float(anomaly["actual_value"])
    agg_expected = float(anomaly["expected_value"])
    agg_deviation = agg_actual - agg_expected

    applicable = registry.get(kpi, [])

    # Web-traffic KPIs and any KPI not in the registry -> no dimensional data
    if not applicable:
        return _null_row(anomaly_id, has_breakdown=False)

    slices: list[dict] = []
    n_checked = 0

    for entry in applicable:
        fname     = entry["file"]
        dim_names = set(entry["dimension_names"])
        df_pre    = precomputed.get(fname)
        if df_pre is None:
            continue

        # Narrow to the anomaly date, this KPI, and applicable dimension names
        mask = (
            (df_pre["date"]           == date) &
            (df_pre["kpi_name"]       == kpi)  &
            (df_pre["dimension_name"].isin(dim_names))
        )
        day_data = df_pre.loc[mask]
        n_checked += len(day_data)

        for _, row in day_data.iterrows():
            dim_z = row["z_score"]
            if pd.isna(dim_z):
                continue

            dim_actual   = float(row["kpi_value"])
            dim_expected = row["expected_value"]

            # contribution_pct: share of aggregate deviation from this slice
            if pd.notna(dim_expected) and abs(agg_deviation) > 1e-9:
                contrib = (dim_actual - float(dim_expected)) / abs(agg_deviation) * 100
            else:
                contrib = np.nan

            slices.append({
                "dimension_name":     row["dimension_name"],
                "dimension_value":    str(row["dimension_value"]),
                "z_score":            round(float(dim_z), 4),
                "contribution_pct":   round(float(contrib), 2) if pd.notna(contrib) else np.nan,
                "abs_z":              abs(float(dim_z)),
            })

    # Rank by |z_score| descending, keep top 3
    slices.sort(key=lambda x: x["abs_z"], reverse=True)
    top3 = slices[:3]

    out: dict = {
        "anomaly_id":               anomaly_id,
        "has_dimensional_breakdown": True,
        "dim_data_sufficient":       len(top3) > 0,
        "n_dimensions_checked":      n_checked,
    }
    for i in range(1, 4):
        if i <= len(top3):
            s = top3[i - 1]
            out[f"dim_{i}_name"]             = s["dimension_name"]
            out[f"dim_{i}_value"]            = s["dimension_value"]
            out[f"dim_{i}_z_score"]          = s["z_score"]
            out[f"dim_{i}_contribution_pct"] = s["contribution_pct"]
        else:
            out[f"dim_{i}_name"]             = None
            out[f"dim_{i}_value"]            = None
            out[f"dim_{i}_z_score"]          = None
            out[f"dim_{i}_contribution_pct"] = None

    return out


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Run scoring across all anomalies
# ─────────────────────────────────────────────────────────────────────────────

def score_all(
    anomalies: pd.DataFrame,
    precomputed: dict[str, pd.DataFrame],
    registry: dict,
) -> pd.DataFrame:
    print(f"\nScoring {len(anomalies)} anomalies...")
    rows = [
        score_anomaly(row, precomputed, registry)
        for _, row in anomalies.iterrows()
    ]
    df_out = pd.DataFrame(rows, columns=OUTPUT_COLS)
    return df_out


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Validate
# ─────────────────────────────────────────────────────────────────────────────

def validate(df: pd.DataFrame, anomalies: pd.DataFrame) -> None:
    errors: list[str] = []

    # Row count
    if len(df) != len(anomalies):
        errors.append(f"Row count {len(df)} != expected {len(anomalies)}")

    # Column schema
    if list(df.columns) != OUTPUT_COLS:
        errors.append(f"Column mismatch: {df.columns.tolist()}")

    # anomaly_id uniqueness
    if df["anomaly_id"].nunique() != len(df):
        errors.append("anomaly_id is not unique")

    # All anomaly_ids present
    missing = set(anomalies["anomaly_id"]) - set(df["anomaly_id"])
    if missing:
        errors.append(f"{len(missing)} anomaly_ids missing from output")

    # No nulls in key columns
    key_nulls = df[["anomaly_id", "has_dimensional_breakdown", "n_dimensions_checked"]].isna().sum()
    if key_nulls.any():
        errors.append(f"Nulls in key columns: {key_nulls[key_nulls > 0].to_dict()}")

    # Rows without breakdown must have null dim slot columns (excludes dim_data_sufficient)
    no_breakdown = df[~df["has_dimensional_breakdown"]]
    dim_cols = [c for c in df.columns if c.startswith("dim_") and c != "dim_data_sufficient"]
    if not no_breakdown[dim_cols].isna().all().all():
        errors.append("Rows with has_dimensional_breakdown=False have non-null dim_ columns")

    # dim_data_sufficient=False is allowed when has_dimensional_breakdown=True:
    # it means the KPI type has applicable dimensions but the anomaly date had
    # insufficient rolling history for at least one scoreable slice (e.g. a
    # low-frequency dimension value with fewer than 2 observations in the
    # rolling window).  This is a data-sparsity condition, not a logic error.
    insufficient = df[df["has_dimensional_breakdown"] & ~df["dim_data_sufficient"]]
    if len(insufficient) > 0:
        sample_ids = insufficient["anomaly_id"].tolist()[:5]
        print(f"  NOTE: {len(insufficient)} anomalies have applicable dimensions "
              f"but dim_data_sufficient=False (insufficient rolling history on "
              f"sparse dimension/date combinations). Sample: {sample_ids}")

    if errors:
        raise RuntimeError("Validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    print("  All validation checks passed.")


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Write output
# ─────────────────────────────────────────────────────────────────────────────

def write_output(df: pd.DataFrame) -> None:
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"  CSV written -> {OUTPUT_CSV.relative_to(BASE)}  ({len(df)} rows × {len(df.columns)} cols)")


# ─────────────────────────────────────────────────────────────────────────────
# Step 7 — Summary
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame, anomalies: pd.DataFrame) -> None:
    with_dims      = df["has_dimensional_breakdown"].sum()
    sufficient     = df["dim_data_sufficient"].sum()
    insufficient   = (df["has_dimensional_breakdown"] & ~df["dim_data_sufficient"]).sum()
    no_dims        = (~df["has_dimensional_breakdown"]).sum()

    print()
    print("=" * 64)
    print("Dimensional Drill-Down — Summary")
    print("=" * 64)
    print(f"  Total anomalies scored        : {len(df)}")
    print(f"  KPI has applicable dimensions : {with_dims}  ({with_dims / len(df):.0%})")
    print(f"    -> dim_data_sufficient=True  : {sufficient}")
    print(f"    -> dim_data_sufficient=False : {insufficient}  "
          f"(sparse slices, insufficient rolling history)")
    print(f"  Web-traffic KPIs (no dims)    : {no_dims}")
    print()

    sub = df[df["dim_data_sufficient"]].copy()
    sub = sub.merge(anomalies[["anomaly_id", "kpi", "severity", "direction", "deviation_pct"]], on="anomaly_id")

    # Top dimension names surfaced as dim_1
    dim1_counts = sub["dim_1_name"].value_counts()
    print("  Leading dimension by anomaly count (dim_1_name):")
    for dim_name, cnt in dim1_counts.items():
        print(f"    {dim_name:<26} : {cnt:>3} anomalies")

    print()

    # Show the 10 anomalies with highest |dim_1_z_score|
    top10 = (
        sub[sub["dim_1_z_score"].notna()]
        .nlargest(10, "dim_1_z_score", keep="all")
        [["anomaly_id", "kpi", "severity", "direction", "deviation_pct",
          "dim_1_name", "dim_1_value", "dim_1_z_score", "dim_1_contribution_pct"]]
    )
    print("  Top 10 anomalies by dimensional z-score (dim_1):")
    print(f"  {'anomaly_id':<26} {'kpi':<28} {'dim_1_name':<18} "
          f"{'dim_1_value':<14} {'z':>7} {'contrib%':>9}")
    print(f"  {'-'*26} {'-'*28} {'-'*18} {'-'*14} {'-'*7} {'-'*9}")
    for _, r in top10.iterrows():
        print(f"  {r['anomaly_id']:<26} {r['kpi']:<28} {r['dim_1_name']:<18} "
              f"{str(r['dim_1_value']):<14} {r['dim_1_z_score']:>7.3f} "
              f"{r['dim_1_contribution_pct']:>9.1f}%")

    print()

    # Direction alignment: does the top dimensional slice move the same way as the aggregate?
    aligned = (
        (sub["deviation_pct"] > 0) & (sub["dim_1_contribution_pct"] > 0) |
        (sub["deviation_pct"] < 0) & (sub["dim_1_contribution_pct"] < 0)
    ).sum()
    total_valid = sub["dim_1_contribution_pct"].notna().sum()
    print(f"  Direction alignment (dim_1 moves same way as aggregate): "
          f"{aligned}/{total_valid}  ({aligned/total_valid:.0%})")

    # Contribution coverage: what % of aggregate deviation is explained by top 3 dims?
    top3_contrib = (
        sub[["dim_1_contribution_pct", "dim_2_contribution_pct", "dim_3_contribution_pct"]]
        .fillna(0).sum(axis=1)
    )
    print(f"  Median top-3 contribution coverage : {top3_contrib.median():.1f}%")
    print(f"  Mean   top-3 contribution coverage : {top3_contrib.mean():.1f}%")

    print("=" * 64)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 64)
    print("Step 2.4 — Dimensional Drill-Down Scoring")
    print("=" * 64)

    # 1. Load inputs
    print("\nLoading inputs...")
    anomalies   = load_anomalies()
    registry    = load_registry()
    dim_files   = load_dimensional_files()

    # 2. Pre-compute rolling stats across all dimensional files
    precomputed = build_precomputed(dim_files)

    # 3. Score every anomaly
    results = score_all(anomalies, precomputed, registry)

    # 4. Validate
    print("\nValidating output...")
    validate(results, anomalies)

    # 5. Write
    print("\nWriting output...")
    write_output(results)

    # 6. Summary
    print_summary(results, anomalies)


if __name__ == "__main__":
    main()
