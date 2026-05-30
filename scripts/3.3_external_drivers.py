#!/usr/bin/env python3
"""
3.3_external_drivers.py

Step 3.3 -- External Driver Attribution (final Layer 3 output).

Checks whether each confirmed anomaly is driven by forces outside the
business's control (macro-economic conditions, competitive pressure,
seasonal patterns, consumer sentiment shifts). Anomalies fully explained
by external drivers are flagged for escalation suppression so Layer 4/5/6
focuses human attention on actionable root causes.

Four attribution rules (thresholds adapted to this dataset's actual range):

    Rule 1  Macro contraction
            README spec : economic_index < -0.30
            Adapted     : economic_index < -0.10
            Note: the synthetic dataset never reaches -0.30 (min = -0.194).
                  -0.10 captures the bottom ~15% of the distribution,
                  matching the spirit of "below-average macro conditions."
            Applies to  : revenue + order KPIs, DOWN direction only

    Rule 2  Competitive pressure
            README spec : marketing_pressure > 0.50
            Adapted     : marketing_pressure > 0.30
            Note: only 8 of 181 anomaly dates exceed 0.50 (max = 0.532).
                  0.30 captures the top quartile, matching "elevated
                  competitive intensity."
            Applies to  : avg_roas, DOWN direction only

    Rule 3  Seasonal trough
            README spec : seasonal_index < -0.10  (unchanged)
            Applies to  : n_orders, DOWN direction only
            Directional guard: UP anomalies (e.g. Black Friday) are never
                  suppressed even when seasonal_index < -0.10, because the
                  dataset's negative winter seasonal index coincides with
                  the holiday spike events.

    Rule 4  Consumer sentiment decline  (extension beyond readme)
            Threshold   : consumer_sentiment < -0.10
            Applies to  : return_rate, UP direction (high returns in low
                  sentiment periods are expected and partially external)

Actionability scoring:
    base = 1.0
    For each firing rule, a penalty is applied:
        macro_contraction      : -0.55  (dominant macro headwind on revenue)
        competitive_pressure   : -0.55  (external competition is primary ROAS driver)
        seasonal_trough        : -0.55  (expected demand trough, not actionable)
        consumer_sentiment_dec : -0.10  (partial external influence only)
    Penalties are additive but capped at 0.70, so actionability >= 0.30.
    Rules 1-3 each independently push actionability below 0.50, triggering
    suppression on their own. Rule 4 (sentiment) is weaker and only flags.

Escalation suppression (escalation_suppressed = True) when ALL of:
    1. is_externally_driven = True
    2. direction = DOWN (positive spikes are never suppressed)
    3. severity != HIGH (HIGH anomalies always escalate)
    4. actionability_score < 0.50

This step also assembles the final Layer 3 narrative (rca_narrative),
combining dependency chain, causal inference, and external context into
one human-readable sentence for each anomaly.

Inputs:
    data/rca_causal_results.csv    Step 3.2 output -- all 3.1+3.2 columns
    data/master_dataset.csv        Raw exogenous variable values per date

Outputs:
    data/rca_results.csv           Final Layer 3 output -- 181 rows, all RCA cols
    data/kpi_anomaly_detection.db  new table: rca_results

Run from project root:  python scripts/3.3_external_drivers.py
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

BASE       = Path(__file__).parent.parent
DATA       = BASE / "data"
CAUSAL_CSV = DATA / "rca_causal_results.csv"
MASTER_CSV = DATA / "master_dataset.csv"
OUT_CSV    = DATA / "rca_results.csv"
DB_PATH    = DATA / "kpi_anomaly_detection.db"

# ─────────────────────────────────────────────────────────────
# KPI groups for rule targeting
# ─────────────────────────────────────────────────────────────

REVENUE_KPIS    = {"total_revenue_usd", "n_orders", "avg_order_value_usd"}
ROAS_KPIS       = {"avg_roas"}
ORDER_KPIS      = {"n_orders"}
SENTIMENT_KPIS  = {"return_rate"}

# ─────────────────────────────────────────────────────────────
# Threshold constants (with readme reference and adaptation note)
# ─────────────────────────────────────────────────────────────

MACRO_THRESHOLD      = -0.10   # readme: -0.30; adapted: data min = -0.194
COMPETITIVE_THRESHOLD = 0.30   # readme:  0.50; adapted: top-quartile in dataset
SEASONAL_THRESHOLD   = -0.10   # readme: -0.10; unchanged
SENTIMENT_THRESHOLD  = -0.10   # extension beyond readme

MACRO_PENALTY       = 0.55   # macro contraction is a dominant revenue headwind
COMPETITIVE_PENALTY = 0.55   # competitive pressure is the primary ROAS driver
SEASONAL_PENALTY    = 0.55   # seasonal trough primarily explains demand drop
SENTIMENT_PENALTY   = 0.10   # partial external factor -- flag but don't suppress
MAX_PENALTY         = 0.70   # floor: actionability never below 0.30

# ─────────────────────────────────────────────────────────────
# Attribution logic
# ─────────────────────────────────────────────────────────────

def attribute_external_drivers(
    kpi: str,
    direction: str,
    severity: str,
    economic_index: float,
    marketing_pressure: float,
    seasonal_index: float,
    consumer_sentiment: float,
) -> dict:
    """
    Evaluate all four external driver rules for a single anomaly and
    compute actionability + suppression.

    Returns a dict of attribution columns.
    """
    drivers   = []    # list of active rule names
    penalties = []    # matching penalty amounts
    details   = []    # human-readable condition descriptions

    # ── Rule 1: Macro contraction ──────────────────────────────
    if (
        economic_index < MACRO_THRESHOLD
        and kpi in REVENUE_KPIS
        and direction == "DOWN"
    ):
        drivers.append("macro_contraction")
        penalties.append(MACRO_PENALTY)
        details.append(f"economic_index={economic_index:.3f} (threshold {MACRO_THRESHOLD})")

    # ── Rule 2: Competitive pressure ──────────────────────────
    if (
        marketing_pressure > COMPETITIVE_THRESHOLD
        and kpi in ROAS_KPIS
        and direction == "DOWN"
    ):
        drivers.append("competitive_pressure")
        penalties.append(COMPETITIVE_PENALTY)
        details.append(f"marketing_pressure={marketing_pressure:.3f} (threshold {COMPETITIVE_THRESHOLD})")

    # ── Rule 3: Seasonal trough ───────────────────────────────
    # Directional guard: UP anomalies (Black Friday, Cyber Monday) are NOT
    # suppressed even when seasonal_index < -0.10. The dataset's winter
    # seasonal_index is structurally negative, coinciding with holiday UP events.
    if (
        seasonal_index < SEASONAL_THRESHOLD
        and kpi in ORDER_KPIS
        and direction == "DOWN"
    ):
        drivers.append("seasonal_trough")
        penalties.append(SEASONAL_PENALTY)
        details.append(f"seasonal_index={seasonal_index:.3f} (threshold {SEASONAL_THRESHOLD})")

    # ── Rule 4: Consumer sentiment decline ────────────────────
    if (
        consumer_sentiment < SENTIMENT_THRESHOLD
        and kpi in SENTIMENT_KPIS
        and direction == "UP"
    ):
        drivers.append("consumer_sentiment_decline")
        penalties.append(SENTIMENT_PENALTY)
        details.append(f"consumer_sentiment={consumer_sentiment:.3f} (threshold {SENTIMENT_THRESHOLD})")

    # ── Scoring ───────────────────────────────────────────────
    is_externally_driven  = len(drivers) > 0
    total_penalty         = min(sum(penalties), MAX_PENALTY)
    actionability_score   = round(1.0 - total_penalty, 4)
    external_driver_type  = ", ".join(drivers) if drivers else "none"
    external_driver_detail = "; ".join(details) if details else ""

    # Actionability label — boundary at 0.50 intentionally mirrors the
    # escalation_suppressed threshold so label and flag always agree.
    if actionability_score >= 0.80:
        actionability_label = "HIGH"
    elif actionability_score >= 0.65:
        actionability_label = "MEDIUM"
    elif actionability_score >= 0.50:
        actionability_label = "LOW"
    else:
        actionability_label = "SUPPRESSED"

    # Escalation suppression: DOWN + externally driven + below-HIGH severity
    # + actionability below 0.50. Never suppress HIGH severity anomalies.
    escalation_suppressed = (
        is_externally_driven
        and direction == "DOWN"
        and severity != "HIGH"
        and actionability_score < 0.50
    )

    suppression_reason = ""
    if escalation_suppressed:
        suppression_reason = (
            f"Suppressed: {external_driver_type} "
            f"(actionability={actionability_score:.2f})"
        )

    return {
        "is_externally_driven":   is_externally_driven,
        "external_driver_type":   external_driver_type,
        "external_driver_detail": external_driver_detail,
        "actionability_score":    actionability_score,
        "actionability_label":    actionability_label,
        "escalation_suppressed":  escalation_suppressed,
        "suppression_reason":     suppression_reason,
    }


# ─────────────────────────────────────────────────────────────
# Narrative builder (final Layer 3 narrative)
# ─────────────────────────────────────────────────────────────

def build_rca_narrative(row: dict) -> str:
    """
    Assemble the final Layer 3 human-readable narrative for one anomaly.
    Combines dependency chain, causal inference result, and external context.
    """
    kpi      = row["kpi"]
    driver   = row["suspected_driver_kpi"]
    dir_     = row["direction"]
    dev      = float(row["deviation_pct"])
    date     = str(row["date"])[:10]
    severity = row["severity"]
    depth    = int(row["graph_depth_reached"])

    # Lead: what happened
    lead = (
        f"[{severity}] {kpi} moved {dir_} {dev:+.1f}% on {date}."
    )

    # Driver: how far did we trace?
    if depth == 0:
        driver_part = f" Root: {driver} (no deeper driver above watch threshold)."
    else:
        chain = row.get("dependency_chain", driver)
        driver_part = f" Chain: {chain}. Suspected driver: {driver}."

    # Causal confidence
    rcc = row.get("root_cause_confidence")
    if rcc is not None and not (isinstance(rcc, float) and np.isnan(rcc)):
        causal_part = f" Causal confidence: {float(rcc):.0%}."
    else:
        causal_part = ""

    # External context
    ext_type = row.get("external_driver_type", "none")
    if ext_type and ext_type != "none":
        act_label = row.get("actionability_label", "")
        ext_part  = f" External: {ext_type.replace('_',' ')} detected. Actionability: {act_label}."
    else:
        ext_part = " No external suppression. Fully actionable."

    # Suppression note
    suppressed = row.get("escalation_suppressed", False)
    sup_part   = " Escalation SUPPRESSED." if suppressed else ""

    return lead + driver_part + causal_part + ext_part + sup_part


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main() -> None:
    # ── Load inputs ──────────────────────────────────────────
    causal_df = pd.read_csv(CAUSAL_CSV)
    master_df = pd.read_csv(MASTER_CSV, parse_dates=["date"])

    causal_df["date"] = pd.to_datetime(causal_df["date"])

    # Exogenous values indexed by date
    exog_cols = ["date", "economic_index", "marketing_pressure",
                 "seasonal_index", "consumer_sentiment"]
    exog_df  = master_df[exog_cols].set_index("date")

    print(f"Loaded {len(causal_df)} anomaly rows from rca_causal_results.csv")
    print(f"Applying 4 external driver rules ...\n")

    # ── Attribution per anomaly ───────────────────────────────
    attr_records = []

    for _, row in causal_df.iterrows():
        date = row["date"]

        # Look up exogenous values for this anomaly date
        if date in exog_df.index:
            eco   = float(exog_df.loc[date, "economic_index"])
            mkt   = float(exog_df.loc[date, "marketing_pressure"])
            seas  = float(exog_df.loc[date, "seasonal_index"])
            sent  = float(exog_df.loc[date, "consumer_sentiment"])
        else:
            eco = mkt = seas = sent = 0.0

        attr = attribute_external_drivers(
            kpi                = row["kpi"],
            direction          = row["direction"],
            severity           = row["severity"],
            economic_index     = eco,
            marketing_pressure = mkt,
            seasonal_index     = seas,
            consumer_sentiment = sent,
        )
        attr_records.append(attr)

    attr_df = pd.DataFrame(attr_records)

    # ── Merge attribution into main result ────────────────────
    out_df = pd.concat([causal_df.reset_index(drop=True),
                        attr_df.reset_index(drop=True)], axis=1)

    # ── Add exogenous snapshot columns ────────────────────────
    exog_snap = master_df[exog_cols].copy()
    exog_snap = exog_snap.rename(columns={
        "economic_index":    "snap_economic_index",
        "marketing_pressure": "snap_marketing_pressure",
        "seasonal_index":    "snap_seasonal_index",
        "consumer_sentiment": "snap_consumer_sentiment",
    })
    out_df = out_df.merge(
        exog_snap.rename(columns={"date": "date"}),
        on="date", how="left"
    )

    # ── Build final narrative ─────────────────────────────────
    out_df["rca_narrative"] = [
        build_rca_narrative(r)
        for r in out_df.to_dict(orient="records")
    ]

    # Normalise date back to string for CSV
    out_df["date"] = out_df["date"].dt.strftime("%Y-%m-%d")

    # ── Write CSV ─────────────────────────────────────────────
    out_df.to_csv(OUT_CSV, index=False)
    print(f"Saved {len(out_df)} rows -> {OUT_CSV.name}")

    # ── Write SQLite ──────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    out_df.to_sql("rca_results", conn, if_exists="replace", index=False)
    conn.close()
    print("Written to SQLite table: rca_results\n")

    # ── Summary report ────────────────────────────────────────
    print("--- External driver attribution summary ---")
    ext_n     = out_df["is_externally_driven"].sum()
    sup_n     = out_df["escalation_suppressed"].sum()
    act_dist  = out_df["actionability_label"].value_counts()
    type_dist = (
        out_df[out_df["is_externally_driven"]]
        ["external_driver_type"]
        .str.split(", ").explode()
        .value_counts()
    )

    print(f"  Externally driven anomalies : {ext_n} / {len(out_df)}")
    print(f"  Escalation suppressed       : {sup_n}")
    print()
    print("  Actionability label distribution:")
    for label in ["HIGH", "MEDIUM", "LOW", "SUPPRESSED"]:
        n = act_dist.get(label, 0)
        print(f"    {label:<12} {n:>4} anomalies")
    print()
    print("  External driver type breakdown:")
    for dtype, n in type_dist.items():
        print(f"    {dtype:<30} {n:>3}")

    # ── Spot-check key ground-truth events ────────────────────
    print("\n--- Spot-check: key ground-truth events ---")
    spot_cols = [
        "anomaly_id", "kpi", "severity", "direction",
        "is_externally_driven", "external_driver_type",
        "escalation_suppressed", "actionability_score",
        "actionability_label",
    ]
    events = [
        ("2024-11-29", "total_revenue_usd", "Black Friday -- must NOT be suppressed"),
        ("2024-03-15", "n_orders",          "Inventory stockout"),
        ("2024-09-03", "conversion_rate",   "Email campaign spike"),
        ("2024-02-08", "avg_discount_pct",  "Economic sentiment drop"),
    ]
    for date_str, kpi, note in events:
        match = out_df[(out_df["date"] == date_str) & (out_df["kpi"] == kpi)]
        print(f"\n  [{note}]")
        if len(match):
            print(match[spot_cols].to_string(index=False))
        else:
            print(f"  NOT FOUND: {date_str} {kpi}")

    # ── Narrative samples ─────────────────────────────────────
    print("\n--- Sample rca_narrative (one per severity) ---")
    for sev in ["HIGH", "MEDIUM", "LOW"]:
        subset = out_df[out_df["severity"] == sev]
        if len(subset):
            print(f"\n[{sev}]")
            print(subset.iloc[0]["rca_narrative"])

    # ── Validation assertions ─────────────────────────────────
    print("\n--- Layer 3 quality checks ---")

    # Black Friday must never be suppressed
    bf = out_df[(out_df["date"] == "2024-11-29") & (out_df["kpi"] == "total_revenue_usd")]
    assert len(bf) > 0 and not bf.iloc[0]["escalation_suppressed"], \
        "FAIL: Black Friday revenue anomaly should NOT be suppressed"
    print("PASS  Black Friday not suppressed")

    # All HIGH severity anomalies must never be suppressed
    high_sup = out_df[(out_df["severity"] == "HIGH") & (out_df["escalation_suppressed"])]
    assert len(high_sup) == 0, \
        f"FAIL: {len(high_sup)} HIGH severity anomalies were suppressed (should be 0)"
    print(f"PASS  All HIGH anomalies have escalation_suppressed=False  ({len(out_df[out_df['severity']=='HIGH'])} checked)")

    # All UP anomalies must never be suppressed
    up_sup = out_df[(out_df["direction"] == "UP") & (out_df["escalation_suppressed"])]
    assert len(up_sup) == 0, \
        f"FAIL: {len(up_sup)} UP anomalies were suppressed (should be 0)"
    print(f"PASS  All UP anomalies have escalation_suppressed=False  ({len(out_df[out_df['direction']=='UP'])} checked)")

    # rca_narrative must be non-null for all rows
    null_nar = out_df["rca_narrative"].isna().sum()
    assert null_nar == 0, f"FAIL: {null_nar} null rca_narrative values"
    print(f"PASS  rca_narrative non-null for all {len(out_df)} rows")

    # Shape
    assert len(out_df) == 181, f"FAIL: expected 181 rows, got {len(out_df)}"
    print(f"PASS  Output shape: {out_df.shape}")

    # SQLite
    conn = sqlite3.connect(DB_PATH)
    db_n = conn.execute("SELECT COUNT(*) FROM rca_results").fetchone()[0]
    conn.close()
    assert db_n == 181, f"FAIL: SQLite rca_results has {db_n} rows, expected 181"
    print(f"PASS  SQLite rca_results: {db_n} rows")

    print("\nPASS  Step 3.3 complete -- rca_results.csv is the final Layer 3 output")
    print("      Ready for Layer 4 (Intelligence Engine)")


if __name__ == "__main__":
    main()
