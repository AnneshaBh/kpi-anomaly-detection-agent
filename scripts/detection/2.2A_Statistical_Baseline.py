#!/usr/bin/env python3
"""
2.2A_Statistical_Baseline.py

Method A of the Layer 2 anomaly detection ensemble â€” Statistical Baseline.

Three independent flags are applied to every tiered KPI across all 731 days:

    A1  7-day rolling Z-score     |z_score| > tier threshold
                                  (uses pre-engineered column from Layer 1)

    A2  STL residual Z-score      STL seasonal decomposition (period=7) extracts
                                  the irregular residual; a rolling 28-day Z-score
                                  is applied to that residual.
                                  Catches anomalies masked by trend / seasonality.

    A3  WoW + MoM combined        |wow_change| > wow_threshold
                                  AND |mom_change| > mom_threshold simultaneously.
                                  Catches gradual structural drift invisible to
                                  short-window Z-scores.

    method_a_flag = A1 OR A2 OR A3

Inputs :  data/processed_kpi_features.csv
          data/tier_config.json
Outputs:  data/method_a_results.csv          (long-format, 8,772 rows)
          data/kpi_anomaly_detection.db       table: method_a_results

Run from project root:  python scripts/2.2A_Statistical_Baseline.py
"""

import json
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from statsmodels.tsa.seasonal import STL

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Paths & constants
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

BASE        = Path(__file__).parent.parent.parent
DATA        = BASE / "data"
INPUT_CSV   = DATA / "processed/processed_kpi_features.csv"
TIER_JSON   = DATA / "config/tier_config.json"
OUTPUT_CSV  = DATA / "detection/method_a_results.csv"
OUTPUT_DB   = DATA / "db/kpi_anomaly_detection.db"
DB_TABLE    = "method_a_results"

STL_PERIOD   = 7    # weekly seasonality (dominant cycle in daily KPI data)
STL_ROBUST   = True # down-weights outlier influence on trend/seasonal fit
RESID_WINDOW = 28   # rolling window for computing Z-score on STL residuals

# Maps anomaly_kpi labels in the ground-truth log to column names in our
# 12-KPI monitored set. None = event targets a KPI outside our tiered set.
ANOMALY_KPI_MAP = {
    "revenue":          "total_revenue_usd",
    "sales_volume":     "n_orders",
    "roas":             "avg_roas",
    "conversion_rate":  "conversion_rate",
    "refunds":          "return_rate",
    "return_rate":      "return_rate",
    "fulfillment_time": None,   # not in the 12 tiered KPIs
    "discount_rate":    "avg_discount_pct",
    "sessions":         "sessions",
    "aov":              "avg_order_value_usd",
    "new_customers":    None,   # n_unique_customers exists but is not a tiered KPI
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Load
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def load_inputs():
    df = pd.read_csv(INPUT_CSV, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    with open(TIER_JSON, encoding="utf-8") as f:
        tier_cfg = json.load(f)
    print(f"  Loaded {len(df):,} rows  "
          f"({df['date'].min().date()} to {df['date'].max().date()})")
    return df, tier_cfg


def tiered_kpis(tier_cfg: dict) -> list[tuple[str, int]]:
    return [
        (kpi, int(t))
        for t, cfg in tier_cfg["tiers"].items()
        for kpi in cfg["kpis"]
    ]

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Flag A2 â€” STL residual Z-score
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def compute_stl_residual_z(series: pd.Series) -> pd.Series:
    """
    Returns the rolling Z-score of the STL residual component.
    Returns an all-NaN Series for near-constant or fully-NaN inputs.
    """
    if series.std() < 1e-6 or series.isna().all():
        return pd.Series(np.nan, index=series.index)

    clean  = series.ffill().bfill()
    result = STL(clean, period=STL_PERIOD, robust=STL_ROBUST).fit()
    resid  = pd.Series(result.resid, index=series.index)

    r_mean   = resid.rolling(RESID_WINDOW, min_periods=7).mean()
    r_std    = resid.rolling(RESID_WINDOW, min_periods=7).std()
    safe_std = r_std.where(r_std > 0, np.nan)

    return ((resid - r_mean) / safe_std).round(4)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Detection â€” one KPI at a time
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def detect_kpi(df: pd.DataFrame, kpi: str,
               tier_num: int, params: dict) -> pd.DataFrame:

    z_thr   = params["z_anomaly"]
    wow_thr = params["wow_threshold"]
    mom_thr = params["mom_threshold"]

    series = df[kpi].astype(float)
    z      = df[f"{kpi}_z_score"]
    wow    = df[f"{kpi}_wow_change"]
    mom    = df[f"{kpi}_mom_change"]
    rmean  = df[f"{kpi}_rolling_mean"]

    resid_z = compute_stl_residual_z(series)

    # â”€â”€ Three independent flags â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    flag_a1 = z.abs().gt(z_thr).fillna(False)
    flag_a2 = resid_z.abs().gt(z_thr).fillna(False)
    flag_a3 = (wow.abs().gt(wow_thr) & mom.abs().gt(mom_thr)).fillna(False)
    any_flag = flag_a1 | flag_a2 | flag_a3

    # â”€â”€ Supplementary context columns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    deviation_pct = ((series - rmean) / rmean.replace(0, np.nan) * 100).round(2)
    direction = pd.Series(
        np.where(z.isna(), "N/A", np.where(z > 0, "UP", "DOWN")),
        index=series.index,
    )

    return pd.DataFrame({
        "date":           df["date"],
        "kpi":            kpi,
        "tier":           tier_num,
        "actual_value":   series.round(4),
        "rolling_mean":   rmean.round(4),
        "z_score":        z.round(4),
        "stl_residual_z": resid_z,
        "wow_change":     wow.round(4),
        "mom_change":     mom.round(4),
        "direction":      direction,
        "deviation_pct":  deviation_pct,
        "flag_a1":        flag_a1,
        "flag_a2":        flag_a2,
        "flag_a3":        flag_a3,
        "method_a_flag":  any_flag,
    })

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Evaluation against ground truth
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def evaluate(results: pd.DataFrame, df: pd.DataFrame) -> dict:
    """
    Day-level evaluation: a day is a True Positive if anomaly_flag == 1
    and method_a_flag fired on at least one KPI that day.
    """
    daily = (
        results.groupby("date")["method_a_flag"]
        .any()
        .reset_index()
        .rename(columns={"method_a_flag": "flagged"})
    )

    gt = df[["date", "anomaly_flag", "anomaly_kpi", "anomaly_event"]].copy()
    merged = gt.merge(daily, on="date", how="left")
    merged["flagged"] = merged["flagged"].fillna(False)

    tp = int(((merged["anomaly_flag"] == 1) &  merged["flagged"]).sum())
    fp = int(((merged["anomaly_flag"] == 0) &  merged["flagged"]).sum())
    fn = int(((merged["anomaly_flag"] == 1) & ~merged["flagged"]).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    caught = merged.loc[(merged["anomaly_flag"] == 1) &  merged["flagged"]]
    missed = merged.loc[(merged["anomaly_flag"] == 1) & ~merged["flagged"]]

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 3),
        "recall":    round(recall, 3),
        "f1_score":  round(f1, 3),
        "total_anomaly_days":  int((merged["anomaly_flag"] == 1).sum()),
        "total_flagged_days":  int(merged["flagged"].sum()),
        "caught": caught[["date", "anomaly_event", "anomaly_kpi"]].copy(),
        "missed": missed[["date", "anomaly_event", "anomaly_kpi"]].copy(),
    }

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Print summary
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def fmt_flag_pct(n: int, total: int = 731) -> str:
    return f"{n:>4}  ({n/total*100:4.1f}%)"


def print_summary(results: pd.DataFrame, metrics: dict,
                  tier_cfg: dict) -> None:
    W = 100

    print()
    print("=" * W)
    print("  METHOD A - STATISTICAL BASELINE  |  Detection Results  |  731 days x 12 KPIs")
    print("=" * W)
    print(f"  Flags:")
    print(f"    A1  7-day rolling Z-score    "
          f"threshold = +/-z_anomaly per tier  "
          f"(Tier 1/2: +/-2.5  |  Tier 3: +/-3.0)")
    print(f"    A2  STL residual Z-score     "
          f"STL period={STL_PERIOD} (weekly)  |  residual rolling window={RESID_WINDOW} days")
    print(f"    A3  WoW + MoM combined       "
          f"both thresholds must breach simultaneously")
    print(f"  method_a_flag = A1 OR A2 OR A3")
    print()

    # â”€â”€ Note on A1 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    max_z = results["z_score"].abs().max()
    print(f"  Note: max |z_score| across all 12 KPIs and 731 days = {max_z:.3f}")
    print(f"        Flag A1 fires only when |z| > Tier threshold (2.5 / 3.0).")
    print(f"        The 7-day rolling window tracks the series closely, compressing z-scores.")
    print(f"        STL (Flag A2) is the primary detection signal for this dataset.")
    print()

    # â”€â”€ Per-KPI summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("-" * W)
    print("  Per-KPI Flag Counts  (across 731 days)")
    print("-" * W)
    print(f"  {'KPI':<28} {'Tier':>4}  "
          f"{'A1 (z)':>12}  {'A2 (STL)':>12}  {'A3 (WoW+MoM)':>14}  "
          f"{'Method A':>12}  {'Thresholds'}")
    print()

    for t_str, tcfg in tier_cfg["tiers"].items():
        t = int(t_str)
        print(f"  --- {tcfg['label']}  "
              f"(z+/-{tcfg['z_anomaly']}, WoW+/-{tcfg['wow_threshold']*100:.0f}%, "
              f"MoM+/-{tcfg['mom_threshold']*100:.0f}%) ---")
        for kpi in tcfg["kpis"]:
            sub = results[results["kpi"] == kpi]
            a1  = int(sub["flag_a1"].sum())
            a2  = int(sub["flag_a2"].sum())
            a3  = int(sub["flag_a3"].sum())
            am  = int(sub["method_a_flag"].sum())
            print(f"  {kpi:<28} {t:>4}  "
                  f"{fmt_flag_pct(a1):>12}  "
                  f"{fmt_flag_pct(a2):>12}  "
                  f"{fmt_flag_pct(a3):>14}  "
                  f"{fmt_flag_pct(am):>12}")
        print()

    # â”€â”€ Evaluation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("-" * W)
    print(f"  Ground-Truth Evaluation  "
          f"(20 labeled anomaly days vs {metrics['total_flagged_days']} flagged days)")
    print("-" * W)
    print(f"  True positives   : {metrics['tp']:>3}  "
          f"(anomaly days correctly caught)")
    print(f"  False positives  : {metrics['fp']:>3}  "
          f"(normal days incorrectly flagged)")
    print(f"  False negatives  : {metrics['fn']:>3}  "
          f"(anomaly days missed)")
    print()
    print(f"  Precision  :  {metrics['precision']:.3f}")
    print(f"  Recall     :  {metrics['recall']:.3f}")
    print(f"  F1 Score   :  {metrics['f1_score']:.3f}")
    print()

    if not metrics["caught"].empty:
        print(f"  Anomaly days CAUGHT  ({len(metrics['caught'])}/{metrics['total_anomaly_days']}):")
        for _, row in metrics["caught"].iterrows():
            d  = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
            kpis_flagged = results.loc[
                (results["date"] == row["date"]) & results["method_a_flag"], "kpi"
            ].tolist()
            print(f"    [+]  {d}  |  {row['anomaly_event']:<35}  "
                  f"(target: {row['anomaly_kpi']})  "
                  f"->  flagged KPIs: {kpis_flagged}")

    if not metrics["missed"].empty:
        print()
        print(f"  Anomaly days MISSED  ({len(metrics['missed'])}/{metrics['total_anomaly_days']}):")
        for _, row in metrics["missed"].iterrows():
            d = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
            print(f"    [-]  {d}  |  {row['anomaly_event']:<35}  "
                  f"(target: {row['anomaly_kpi']})")

    print()
    print("=" * W)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Write outputs
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def write_outputs(results: pd.DataFrame) -> None:
    out = results.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")

    out.to_csv(OUTPUT_CSV, index=False)
    print(f"  CSV written    ->  {OUTPUT_CSV.relative_to(BASE)}")
    print(f"  Shape          :   {out.shape[0]:,} rows x {out.shape[1]} cols  "
          f"({out['kpi'].nunique()} KPIs x {out['date'].nunique()} days)")

    conn = sqlite3.connect(OUTPUT_DB)
    out.to_sql(DB_TABLE, conn, if_exists="replace", index=False)
    conn.close()
    print(f"  SQLite written ->  {OUTPUT_DB.relative_to(BASE)}  (table: {DB_TABLE})")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Main
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main() -> None:
    print()
    print("=" * 60)
    print("  Method A â€” Statistical Baseline")
    print("=" * 60)

    df, tier_cfg = load_inputs()

    pairs = tiered_kpis(tier_cfg)
    print(f"  Running on {len(pairs)} KPIs ...\n")

    all_results = []
    for kpi, tier_num in pairs:
        params = tier_cfg["tiers"][str(tier_num)]
        kpi_df = detect_kpi(df, kpi, tier_num, params)
        kpi_df = kpi_df.merge(
            df[["date", "anomaly_flag", "anomaly_kpi", "anomaly_event"]],
            on="date", how="left",
        )
        a2_count = int(kpi_df["flag_a2"].sum())
        am_count = int(kpi_df["method_a_flag"].sum())
        print(f"  {kpi:<30}  A2 flags: {a2_count:>3}  |  Method A flags: {am_count:>3}")
        all_results.append(kpi_df)

    results = pd.concat(all_results, ignore_index=True)

    metrics = evaluate(results, df)
    print_summary(results, metrics, tier_cfg)

    print("  Writing outputs ...")
    write_outputs(results)
    print()
    print("  Step 2.2A complete.")
    print("  method_a_results.csv is ready for the ensemble voting step.")
    print()


if __name__ == "__main__":
    main()
