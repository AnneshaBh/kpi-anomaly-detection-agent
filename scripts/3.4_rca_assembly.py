#!/usr/bin/env python3
"""
3.4_rca_assembly.py

Step 3.4 -- RCA Assembly and Layer 3 Quality Tests.

This is the final step of Layer 3. It assembles the three intermediate
outputs from Steps 3.1-3.3 into a single curated table optimised for
Layer 4 (Intelligence Engine) consumption, adds derived metadata fields,
and runs 12 numbered quality tests that validate the end-to-end Layer 3
pipeline.

Assembly pipeline:
    1. Validate all three intermediate files (shape, columns, ID coverage).
    2. Load rca_results.csv (Step 3.3 output -- all 3.1-3.3 columns merged).
    3. Merge actual_value and expected_value from anomaly_results.csv (not
       carried through Steps 3.1-3.3; needed by Layer 4 for dollar impact).
    4. Add three derived metadata columns:
         rca_completeness_score  0-3  int(depth>0) + int(ci_ran) + int(dw_ran)
         confidence_tier         str  HIGH / MEDIUM / LOW / UNAVAILABLE
         layer4_priority_flag    str  ESCALATE / INVESTIGATE / MONITOR / SUPPRESSED
    5. Select ~37 curated columns (exclude verbose internal fields used
       only within Layer 3).
    6. Run 12 quality tests -- all must PASS before writing output.
    7. Write rca_assembly.csv + SQLite table rca_assembly.

Inputs:
    data/rca_graph_results.csv    Step 3.1  (181, 18)
    data/rca_causal_results.csv   Step 3.2  (181, 40)
    data/rca_results.csv          Step 3.3  (181, 52)
    data/anomaly_results.csv      Layer 2   (181, 25)  -- source of actual/expected

Outputs:
    data/rca_assembly.csv         Final Layer 3 output  (181, ~37)
    data/kpi_anomaly_detection.db new table: rca_assembly

Run from project root:  python scripts/3.4_rca_assembly.py
"""

import sqlite3
import warnings
import pandas as pd
import numpy as np
from pathlib import Path

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────

BASE          = Path(__file__).parent.parent
DATA          = BASE / "data"
GRAPH_CSV     = DATA / "rca_graph_results.csv"
CAUSAL_CSV    = DATA / "rca_causal_results.csv"
RCA_CSV       = DATA / "rca_results.csv"
ANOMALY_CSV   = DATA / "anomaly_results.csv"
OUT_CSV       = DATA / "rca_assembly.csv"
DB_PATH       = DATA / "kpi_anomaly_detection.db"

# Expected intermediate file shapes (Step, rows, cols)
EXPECTED_SHAPES = {
    GRAPH_CSV:  (181, 18),
    CAUSAL_CSV: (181, 40),
    RCA_CSV:    (181, 52),
}

# ─────────────────────────────────────────────────────────────
# Curated column selection for Layer 4 handoff
# ─────────────────────────────────────────────────────────────

ASSEMBLY_COLS = [
    # --- Identity & severity ---
    "anomaly_id", "date", "kpi", "tier", "severity", "votes",

    # --- Anomaly characterisation ---
    "direction", "actual_value", "expected_value", "deviation_pct", "z_score",
    "anomaly_flag", "anomaly_event",

    # --- Step 3.1: Dependency graph ---
    "dependency_chain", "suspected_driver_kpi", "driver_z_score",
    "driver_direction", "graph_depth_reached", "co_anomalous_kpis",
    "affected_tier1_kpis",

    # --- Step 3.2: Causal inference ---
    "root_cause_confidence", "confidence_tier",
    "ci_ran", "ci_relative_effect_pct", "ci_effect_significant", "ci_confidence",
    "dw_ran", "dw_treatment", "dw_effect_pct", "dw_refutation_passed", "dw_p_value",

    # --- Step 3.3: External drivers ---
    "is_externally_driven", "external_driver_type", "external_driver_detail",
    "snap_economic_index", "snap_marketing_pressure",
    "snap_seasonal_index", "snap_consumer_sentiment",
    "actionability_score", "actionability_label",
    "escalation_suppressed", "suppression_reason",

    # --- Assembly metadata ---
    "rca_completeness_score", "layer4_priority_flag",

    # --- Final narrative ---
    "rca_narrative",
]

# ─────────────────────────────────────────────────────────────
# Step 1: Validate intermediate files
# ─────────────────────────────────────────────────────────────

def validate_intermediates() -> None:
    """Assert each intermediate file exists and has the expected shape."""
    print("Validating intermediate files ...")
    for path, (exp_rows, exp_cols) in EXPECTED_SHAPES.items():
        assert path.exists(), f"Missing: {path.name}"
        df = pd.read_csv(path)
        assert df.shape == (exp_rows, exp_cols), (
            f"{path.name}: expected ({exp_rows}, {exp_cols}), got {df.shape}"
        )
        print(f"  OK  {path.name:30}  {df.shape}")
    print()


# ─────────────────────────────────────────────────────────────
# Step 2-4: Load, merge, derive
# ─────────────────────────────────────────────────────────────

def build_assembly() -> pd.DataFrame:
    """
    Load Step 3.3 output, merge actual/expected values from Layer 2,
    and add three derived metadata columns.
    """
    rca      = pd.read_csv(RCA_CSV)
    anomaly  = pd.read_csv(ANOMALY_CSV, usecols=[
        "anomaly_id", "actual_value", "expected_value", "votes"
    ])

    # Merge actual / expected values and vote count
    df = rca.merge(anomaly, on="anomaly_id", how="left")

    # ── Derived column 1: rca_completeness_score (0-3) ────────
    # +1 if dependency graph traversal found a distinct upstream driver
    # +1 if CausalImpact ran
    # +1 if DoWhy ran
    df["rca_completeness_score"] = (
        (df["graph_depth_reached"] > 0).astype(int)
        + df["ci_ran"].fillna(False).astype(int)
        + df["dw_ran"].fillna(False).astype(int)
    )

    # ── Derived column 2: confidence_tier ─────────────────────
    def _conf_tier(rcc) -> str:
        if pd.isna(rcc):
            return "UNAVAILABLE"
        if rcc >= 0.80:
            return "HIGH"
        if rcc >= 0.60:
            return "MEDIUM"
        return "LOW"

    df["confidence_tier"] = df["root_cause_confidence"].apply(_conf_tier)

    # ── Derived column 3: layer4_priority_flag ─────────────────
    def _priority(row) -> str:
        if row["escalation_suppressed"]:
            return "SUPPRESSED"
        if row["severity"] == "HIGH":
            return "ESCALATE"
        if row["severity"] == "MEDIUM":
            return "INVESTIGATE"
        return "MONITOR"

    df["layer4_priority_flag"] = df.apply(_priority, axis=1)

    return df


# ─────────────────────────────────────────────────────────────
# Step 5: Column selection
# ─────────────────────────────────────────────────────────────

def select_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the curated Layer 4 handoff columns."""
    missing = [c for c in ASSEMBLY_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Assembly missing expected columns: {missing}")
    return df[ASSEMBLY_COLS].copy()


# ─────────────────────────────────────────────────────────────
# Step 6: Quality tests
# ─────────────────────────────────────────────────────────────

def _pass(test_name: str, detail: str = "") -> None:
    msg = f"PASS  {test_name}"
    if detail:
        msg += f"  ({detail})"
    print(msg)


def _fail(test_name: str, reason: str) -> None:
    raise AssertionError(f"FAIL  {test_name}: {reason}")


def run_quality_tests(df: pd.DataFrame) -> None:
    print("Running Layer 3 quality tests ...")
    print()

    # ── Test 1: Assembly shape ────────────────────────────────
    assert df.shape[0] == 181, f"Expected 181 rows, got {df.shape[0]}"
    assert df.shape[1] == len(ASSEMBLY_COLS), (
        f"Expected {len(ASSEMBLY_COLS)} cols, got {df.shape[1]}"
    )
    _pass("Test 1  Assembly shape", f"{df.shape[0]} rows x {df.shape[1]} cols")

    # ── Test 2: Anomaly ID uniqueness and integrity ───────────
    assert df["anomaly_id"].nunique() == 181, \
        f"Expected 181 unique IDs, got {df['anomaly_id'].nunique()}"
    anomaly_ids_ref = set(pd.read_csv(ANOMALY_CSV)["anomaly_id"])
    assembly_ids    = set(df["anomaly_id"])
    assert assembly_ids == anomaly_ids_ref, \
        f"ID mismatch: {anomaly_ids_ref.symmetric_difference(assembly_ids)}"
    _pass("Test 2  Anomaly ID uniqueness and integrity", "all 181 IDs unique and match Layer 2")

    # ── Test 3: actual_value and expected_value present ───────
    null_actual   = df["actual_value"].isna().sum()
    null_expected = df["expected_value"].isna().sum()
    assert null_actual == 0, f"{null_actual} null actual_value"
    assert null_expected == 0, f"{null_expected} null expected_value"
    _pass("Test 3  actual_value / expected_value non-null", "merged from anomaly_results")

    # ── Test 4: Dependency chain coverage (HIGH + MEDIUM) ─────
    hm = df[df["severity"].isin(["HIGH", "MEDIUM"])]
    null_driver = hm["suspected_driver_kpi"].isna().sum()
    empty_chain = (hm["dependency_chain"] == "").sum()
    assert null_driver == 0, f"{null_driver} HIGH/MEDIUM rows have null suspected_driver_kpi"
    assert empty_chain == 0, f"{empty_chain} HIGH/MEDIUM rows have empty dependency_chain"
    _pass("Test 4  Dependency chain coverage for HIGH+MEDIUM",
          f"all {len(hm)} rows have non-null driver and chain")

    # ── Test 5: Causal confidence quality for HIGH anomalies ──
    high = df[df["severity"] == "HIGH"]
    high_with_rcc = high["root_cause_confidence"].notna()
    n_above_07    = (high.loc[high_with_rcc, "root_cause_confidence"] > 0.70).sum()
    n_total_high  = int(high_with_rcc.sum())
    assert n_above_07 >= 10, \
        f"Only {n_above_07} of {n_total_high} HIGH anomalies have root_cause_confidence > 0.70 (need >= 10)"
    _pass("Test 5  HIGH anomaly causal confidence",
          f"{n_above_07} / {n_total_high} have root_cause_confidence > 0.70")

    # ── Test 6: Black Friday never suppressed ─────────────────
    bf = df[(df["date"] == "2024-11-29") & (df["kpi"] == "total_revenue_usd")]
    assert len(bf) > 0, "Black Friday revenue anomaly not found in assembly"
    assert not bf.iloc[0]["escalation_suppressed"], \
        "Black Friday revenue anomaly is incorrectly suppressed"
    assert bf.iloc[0]["layer4_priority_flag"] == "ESCALATE", \
        f"Black Friday layer4_priority_flag should be ESCALATE, got {bf.iloc[0]['layer4_priority_flag']}"
    _pass("Test 6  Black Friday not suppressed",
          f"escalation_suppressed=False, layer4_priority_flag=ESCALATE")

    # ── Test 7: No HIGH severity anomaly suppressed ───────────
    high_sup = df[(df["severity"] == "HIGH") & df["escalation_suppressed"]]
    assert len(high_sup) == 0, \
        f"{len(high_sup)} HIGH anomaly rows are suppressed -- should be 0"
    _pass("Test 7  No HIGH anomaly suppressed",
          f"all {len(high)} HIGH anomalies have escalation_suppressed=False")

    # ── Test 8: No UP anomaly suppressed ─────────────────────
    up_sup = df[(df["direction"] == "UP") & df["escalation_suppressed"]]
    assert len(up_sup) == 0, \
        f"{len(up_sup)} UP-direction anomalies are suppressed -- should be 0"
    n_up = (df["direction"] == "UP").sum()
    _pass("Test 8  No UP anomaly suppressed", f"all {n_up} UP anomalies unconstrained")

    # ── Test 9: rca_narrative non-null and non-empty ──────────
    null_nar  = df["rca_narrative"].isna().sum()
    empty_nar = (df["rca_narrative"].fillna("").str.strip() == "").sum()
    assert null_nar == 0,  f"{null_nar} null rca_narrative values"
    assert empty_nar == 0, f"{empty_nar} empty rca_narrative values"
    _pass("Test 9  rca_narrative non-null for all 181 rows")

    # ── Test 10: Suppression integrity ────────────────────────
    suppressed    = df[df["escalation_suppressed"]]
    n_suppressed  = len(suppressed)
    if n_suppressed > 0:
        assert (suppressed["actionability_label"] == "SUPPRESSED").all(), \
            "Suppressed rows must have actionability_label = SUPPRESSED"
        assert (suppressed["layer4_priority_flag"] == "SUPPRESSED").all(), \
            "Suppressed rows must have layer4_priority_flag = SUPPRESSED"
        assert (suppressed["direction"] == "DOWN").all(), \
            "Only DOWN anomalies can be suppressed"
        assert (suppressed["severity"] != "HIGH").all(), \
            "HIGH anomalies cannot be suppressed"
    _pass("Test 10 Suppression integrity",
          f"{n_suppressed} suppressed rows -- all DOWN, non-HIGH, labeled SUPPRESSED")

    # ── Test 11: rca_completeness_score distribution ──────────
    hm_score = df[df["severity"].isin(["HIGH", "MEDIUM"])]["rca_completeness_score"]
    n_score_ge2 = (hm_score >= 2).sum()
    pct = n_score_ge2 / len(hm_score) * 100
    assert pct >= 15, \
        f"Only {pct:.0f}% of HIGH+MEDIUM anomalies have completeness_score >= 2 (need >= 15%)"
    _pass("Test 11 Completeness score distribution",
          f"{n_score_ge2} / {len(hm_score)} HIGH+MEDIUM have score >= 2 ({pct:.0f}%)")

    # ── Test 12: SQLite parity ────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    db_n = conn.execute("SELECT COUNT(*) FROM rca_assembly").fetchone()[0]
    conn.close()
    assert db_n == 181, f"SQLite rca_assembly has {db_n} rows, expected 181"
    _pass("Test 12 SQLite rca_assembly parity", f"{db_n} rows")

    print()


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("Step 3.4 -- RCA Assembly")
    print("=" * 60)
    print()

    # ── 1. Validate intermediates ─────────────────────────────
    validate_intermediates()

    # ── 2-4. Build assembly ───────────────────────────────────
    print("Building assembly ...")
    full_df = build_assembly()
    print(f"  Merged actual_value / expected_value from anomaly_results")
    print(f"  Added rca_completeness_score, confidence_tier, layer4_priority_flag")
    print()

    # ── 5. Select curated columns ─────────────────────────────
    assembly = select_columns(full_df)
    print(f"  Selected {len(ASSEMBLY_COLS)} curated columns for Layer 4 handoff")
    print()

    # ── 6. Write outputs first (Test 12 validates the write) ──
    assembly.to_csv(OUT_CSV, index=False)
    print(f"Saved {len(assembly)} rows -> {OUT_CSV.name}")

    conn = sqlite3.connect(DB_PATH)
    assembly.to_sql("rca_assembly", conn, if_exists="replace", index=False)
    conn.close()
    print(f"Written to SQLite table: rca_assembly")
    print()

    # ── 7. Quality tests (including SQLite parity check) ──────
    run_quality_tests(assembly)


    # ── Final summary ─────────────────────────────────────────
    print("=" * 60)
    print("Layer 3 assembly summary")
    print("=" * 60)

    sev_dist = assembly["severity"].value_counts()
    pri_dist = assembly["layer4_priority_flag"].value_counts()
    ctier    = assembly["confidence_tier"].value_counts()
    score    = assembly["rca_completeness_score"].value_counts().sort_index()

    print("\nSeverity distribution:")
    for sev, n in sev_dist.items():
        print(f"  {sev:<8}  {n:>3}")

    print("\nLayer 4 priority flags:")
    for flag, n in pri_dist.items():
        print(f"  {flag:<12}  {n:>3}")

    print("\nConfidence tier:")
    for tier, n in ctier.items():
        print(f"  {tier:<12}  {n:>3}")

    print("\nRCA completeness score (0=graph only, 1=+one method, 2=+two, 3=+all):")
    for sc, n in score.items():
        print(f"  Score {sc}:  {n:>4} anomalies")

    print("\nKey ground-truth event narratives:")
    events = [
        ("2024-11-29", "total_revenue_usd"),
        ("2024-03-15", "n_orders"),
        ("2024-09-03", "conversion_rate"),
    ]
    for date_str, kpi in events:
        row = assembly[(assembly["date"] == date_str) & (assembly["kpi"] == kpi)]
        if len(row):
            r = row.iloc[0]
            print(f"\n  [{r['anomaly_id']}]  {r['layer4_priority_flag']}  "
                  f"confidence={r['root_cause_confidence']}  "
                  f"completeness={r['rca_completeness_score']}")
            print(f"  {r['rca_narrative']}")

    print()
    print("PASS  Layer 3 complete")
    print("      rca_assembly.csv is the Layer 3 -> Layer 4 handoff")
    print()
    print("SQLite tables written for Layer 3:")
    conn = sqlite3.connect(DB_PATH)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    conn.close()
    l3_tables = [t for t in tables if t.startswith("rca")]
    for t in l3_tables:
        print(f"  {t}")


if __name__ == "__main__":
    main()
