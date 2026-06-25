#!/usr/bin/env python3
"""
2.3_Ensemble_Voting.py

Step 2.3 --" Ensemble Voting and Ground-Truth Evaluation.

Combines the flags from all three detection methods into a single confirmed
anomaly signal and produces the final anomaly_results dataset for Layer 3.

Join architecture:
    Base   : Method A  (8,772 rows --" 12 KPIs x 731 days)
    + join : Method B  (731 rows --" day-level; broadcast to every KPI on that date)
    + join : Method C  (2,924 rows --" Tier 1 KPIs only; False for Tier 2 / 3)

Voting:
    votes = method_a_flag + method_b_flag + method_c_flag
    confirmed = votes >= 2

Methods available per tier:
    Tier 1  total_revenue_usd, n_orders, avg_roas, conversion_rate
            A + B + C  (max 3 votes)
    Tier 2  return_rate, n_stockouts, avg_order_value_usd, bounce_rate
            A + B      (max 2 votes --" C does not cover Tier 2)
    Tier 3  total_clicks, sessions, inventory_health, avg_discount_pct
            A + B      (max 2 votes --" C does not cover Tier 3)

Severity:
    HIGH    Tier 1: all 3 methods agree (votes == 3)
    MEDIUM  Tier 1: 2 methods agree  |  Tier 2: both methods agree
    LOW     Tier 3: both methods agree

Anomaly ID format:  ANO-YYYYMMDD-{KPI_CODE}
    e.g. ANO-20240315-REV  (revenue anomaly on 2024-03-15)

Inputs :  data/method_a_results.csv
          data/method_b_results.csv
          data/method_c_results.csv
Outputs:  data/anomaly_results.csv              confirmed anomalies only
          data/ensemble_voting_matrix.csv        full 8,772-row vote matrix
          data/kpi_anomaly_detection.db          tables: anomaly_results,
                                                          ensemble_voting_matrix

Run from project root:  python scripts/2.3_Ensemble_Voting.py
"""

import json
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path

# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
# Paths
# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "

BASE         = Path(__file__).parent.parent.parent
DATA         = BASE / "data"
METHOD_A_CSV = DATA / "detection/method_a_results.csv"
METHOD_B_CSV = DATA / "detection/method_b_results.csv"
METHOD_C_CSV = DATA / "detection/method_c_results.csv"
OUTPUT_CSV   = DATA / "detection/anomaly_results.csv"
MATRIX_CSV   = DATA / "detection/ensemble_voting_matrix.csv"
OUTPUT_DB    = DATA / "db/kpi_anomaly_detection.db"
TIER_JSON    = DATA / "config/tier_config.json"

KPI_CODES = {
    "total_revenue_usd":    "REV",
    "n_orders":             "ORD",
    "avg_roas":             "ROAS",
    "conversion_rate":      "CVR",
    "return_rate":          "RET",
    "n_stockouts":          "STK",
    "avg_order_value_usd":  "AOV",
    "bounce_rate":          "BNC",
    "total_clicks":         "CLK",
    "sessions":             "SES",
    "inventory_health":     "INV",
    "avg_discount_pct":     "DSC",
}

# Method name labels for the methods_flagged column
METHOD_LABELS = {
    "method_a_flag": "statistical",
    "method_b_flag": "isolation_forest",
    "method_c_flag": "prophet",
}

# Per-tier max votes (methods available)
TIER_MAX_VOTES = {1: 3, 2: 2, 3: 2}

# Individual method day-level results (for the comparison table)
INDIVIDUAL_RESULTS = {
    "Method A (Statistical)": {"flagged": 696, "tp": 20, "fp": 676, "fn": 0},
    "Method B (Isolation F.)": {"flagged": 34,  "tp": 8,  "fp": 26,  "fn": 12},
    "Method C (Prophet)":      {"flagged": 47,  "tp": 8,  "fp": 39,  "fn": 12},
}

# -----------------------------------------------------------------------------
# Tier config helpers
# -----------------------------------------------------------------------------

def load_tier_config() -> dict:
    with open(TIER_JSON, encoding="utf-8") as f:
        return json.load(f)


def build_pig_map(tier_cfg: dict) -> dict:
    """Return {kpi: positive_is_good (bool)} for all tiered KPIs."""
    pig_map = {}
    for tier_data in tier_cfg["tiers"].values():
        for kpi, meta in tier_data["kpi_metadata"].items():
            pig_map[kpi] = meta["positive_is_good"]
    return pig_map

# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
# Load & build ensemble matrix
# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "

def load_methods():
    a = pd.read_csv(METHOD_A_CSV, parse_dates=["date"])
    b = pd.read_csv(METHOD_B_CSV, parse_dates=["date"])
    c = pd.read_csv(METHOD_C_CSV, parse_dates=["date"])
    return a, b, c


def build_matrix(a: pd.DataFrame,
                 b: pd.DataFrame,
                 c: pd.DataFrame) -> pd.DataFrame:
    """
    Join all three method results into a single 8,772-row matrix.
    One row per (date, kpi) pair across all 12 tiered KPIs x 731 days.
    """
    # Base: Method A --" keep the columns needed for output
    base = a[[
        "date", "kpi", "tier",
        "actual_value", "rolling_mean", "z_score",
        "stl_residual_z", "wow_change", "mom_change",
        "deviation_pct", "direction",
        "flag_a1", "flag_a2", "flag_a3", "method_a_flag",
        "anomaly_flag", "anomaly_event", "anomaly_kpi",
    ]].copy()

    # Method B: day-level --" merge on date, broadcast to all KPIs
    b_slim = b[["date", "method_b_flag", "method_b_score",
                 "top_5_features"]].copy()
    base = base.merge(b_slim, on="date", how="left")
    base["method_b_flag"] = base["method_b_flag"].fillna(False)
    base["method_b_score"] = base["method_b_score"].fillna(np.nan)

    # Method C: per-KPI, Tier 1 only --" merge on date + kpi
    c_slim = c[["date", "kpi", "method_c_flag",
                 "yhat", "yhat_lower", "yhat_upper"]].copy()
    base = base.merge(c_slim, on=["date", "kpi"], how="left")
    base["method_c_flag"] = base["method_c_flag"].fillna(False)

    return base


# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
# Voting & severity
# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "

def assign_severity(tier: int, votes: int) -> str:
    if tier == 1:
        return "HIGH" if votes == 3 else "MEDIUM"
    elif tier == 2:
        return "MEDIUM"
    else:
        return "LOW"


def build_methods_flagged(row) -> str:
    active = [
        label
        for col, label in METHOD_LABELS.items()
        if row[col]
    ]
    return ", ".join(active)


def add_votes(matrix: pd.DataFrame) -> pd.DataFrame:
    m = matrix.copy()

    m["votes"] = (
        m["method_a_flag"].astype(int)
        + m["method_b_flag"].astype(int)
        + m["method_c_flag"].astype(int)
    )
    m["confirmed"] = m["votes"] >= 2

    m["severity"] = m.apply(
        lambda r: assign_severity(r["tier"], r["votes"]) if r["confirmed"] else "NONE",
        axis=1,
    )

    m["methods_flagged"] = m.apply(build_methods_flagged, axis=1)

    m["anomaly_id"] = m.apply(
        lambda r: f"ANO-{pd.Timestamp(r['date']).strftime('%Y%m%d')}-{KPI_CODES.get(r['kpi'], r['kpi'].upper())}"
        if r["confirmed"] else "",
        axis=1,
    )

    # expected_value = 7-day rolling mean from Method A
    m["expected_value"] = m["rolling_mean"]

    return m

# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
# Direction filter
# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "

def apply_direction_filter(matrix: pd.DataFrame, pig_map: dict) -> pd.DataFrame:
    """
    Suppress vote-confirmed anomalies whose direction is not the actionable
    direction for that KPI, based on positive_is_good from tier_config.json.

        positive_is_good = True  ->  UP is growth (suppress); DOWN is the problem
        positive_is_good = False ->  UP is the problem; DOWN is improvement (suppress)

    Adds two audit columns to every row:
        direction_suppressed         bool
        direction_suppression_reason str  (empty when not suppressed)

    The confirmed column is NOT modified here; callers filter on
    confirmed & ~direction_suppressed so the voting record stays intact.
    """
    m = matrix.copy()

    def _check(row):
        if not row["confirmed"]:
            return False, ""
        pig       = pig_map.get(row["kpi"], True)
        direction = row["direction"]
        if pig and direction == "UP":
            return True, "directionally_invalid: UP change on positive_is_good KPI"
        if not pig and direction == "DOWN":
            return True, "directionally_invalid: DOWN change on inverse KPI"
        return False, ""

    result = m.apply(_check, axis=1, result_type="expand")
    m["direction_suppressed"]         = result[0]
    m["direction_suppression_reason"] = result[1]
    return m


# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
# Evaluation
# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "

def evaluate(matrix: pd.DataFrame) -> dict:
    """Day-level precision / recall / F1 for the ensemble."""
    daily = (
        matrix.groupby("date")["confirmed"]
        .any()
        .reset_index()
        .rename(columns={"confirmed": "flagged"})
    )
    gt = matrix[["date", "anomaly_flag", "anomaly_event", "anomaly_kpi"]].drop_duplicates("date")
    merged = gt.merge(daily, on="date", how="left")
    merged["flagged"] = merged["flagged"].fillna(False)

    tp = int(((merged["anomaly_flag"] == 1) &  merged["flagged"]).sum())
    fp = int(((merged["anomaly_flag"] == 0) &  merged["flagged"]).sum())
    fn = int(((merged["anomaly_flag"] == 1) & ~merged["flagged"]).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    caught = merged.loc[(merged["anomaly_flag"] == 1) &  merged["flagged"]].copy()
    missed = merged.loc[(merged["anomaly_flag"] == 1) & ~merged["flagged"]].copy()

    flagged_days = int(merged["flagged"].sum())

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 3),
        "recall":    round(recall, 3),
        "f1_score":  round(f1, 3),
        "total_anomaly_days":  int((merged["anomaly_flag"] == 1).sum()),
        "total_flagged_days":  flagged_days,
        "caught": caught,
        "missed": missed,
    }

# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
# Print summary
# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "

def print_summary(matrix: pd.DataFrame,
                  confirmed: pd.DataFrame,
                  metrics: dict) -> None:
    W = 115
    total_kpi_days = len(matrix)
    n_confirmed = len(confirmed)
    n_unique_dates = confirmed["date"].nunique() if n_confirmed > 0 else 0

    print()
    print("=" * W)
    print("  STEP 2.3 - ENSEMBLE VOTING  |  Layer 2 Detection Summary")
    print("=" * W)
    print(f"  Input records :  "
          f"Method A: {len(matrix):,} KPI-day pairs  |  "
          f"Method B: 731 day-level flags (broadcast)  |  "
          f"Method C: 2,924 Tier 1 KPI-day pairs")
    print(f"  Voting rule   :  >= 2 of 3 methods must agree -> confirmed anomaly")
    print(f"  Methods/tier  :  Tier 1: A+B+C (max 3 votes)  |  "
          f"Tier 2/3: A+B only (max 2 votes, C covers Tier 1 only)")
    print()

    # " -- " Vote distribution " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
    print("-" * W)
    print("  Vote Distribution  (8,772 KPI-day pairs)")
    print("-" * W)
    vote_counts = matrix["votes"].value_counts().sort_index()
    for v, cnt in vote_counts.items():
        tag = {
            0: "NORMAL     -- no detection",
            1: "WATCH      -- 1 method flagged, not confirmed",
            2: "CONFIRMED  -- 2 methods agree",
            3: "CONFIRMED  -- all 3 methods agree (Tier 1 only)",
        }.get(v, "")
        bar = "#" * int(cnt / total_kpi_days * 50)
        print(f"  votes={v}  {cnt:>5} ({cnt/total_kpi_days*100:5.1f}%)  {tag:<48}  {bar}")
    print()

    # " -- " Direction filter summary " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
    print("-" * W)
    print("  Direction Filter  (positive_is_good from tier_config.json)")
    print("-" * W)
    n_vote_confirmed  = int(matrix["confirmed"].sum())
    n_dir_suppressed  = int(
        (matrix["confirmed"] & matrix["direction_suppressed"]).sum()
    ) if "direction_suppressed" in matrix.columns else 0
    n_final_confirmed = n_confirmed
    print(f"  Vote-confirmed       : {n_vote_confirmed:>4} KPI-day pairs")
    print(f"  Direction-suppressed : {n_dir_suppressed:>4}  "
          f"(UP on positive_is_good KPI  |  DOWN on inverse KPI)")
    print(f"  Final confirmed      : {n_final_confirmed:>4}  -> written to anomaly_results.csv")

    if "direction_suppressed" in matrix.columns and n_dir_suppressed > 0:
        sup = matrix[matrix["confirmed"] & matrix["direction_suppressed"]]
        by_kpi = sup.groupby(["kpi", "direction_suppression_reason"]).size()
        print()
        print("  Suppressed breakdown by KPI:")
        for (kpi, reason), count in by_kpi.items():
            print(f"    {kpi:<28}  {count:>3}  ({reason})")
    print()

    # " -- " Per-tier vote breakdown " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
    print("-" * W)
    print("  Confirmed Anomalies by Tier and Severity")
    print("-" * W)
    for tier_num in [1, 2, 3]:
        t_conf = confirmed[confirmed["tier"] == tier_num]
        t_all  = matrix[matrix["tier"] == tier_num]
        sevs   = t_conf["severity"].value_counts().to_dict() if len(t_conf) > 0 else {}
        sev_str = "  ".join(f"{s}: {n}" for s, n in sorted(sevs.items()))
        print(f"  Tier {tier_num}  --  {len(t_conf):>3} confirmed KPI-day pairs "
              f"across {t_conf['date'].nunique() if len(t_conf)>0 else 0} unique dates  |  "
              f"{sev_str if sev_str else 'none'}")
    print()

    # " -- " Confirmed anomalies table " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
    print("-" * W)
    print(f"  All Confirmed Anomalies  "
          f"({n_confirmed} KPI-day records  |  {n_unique_dates} unique dates)")
    print("-" * W)
    print(f"  {'anomaly_id':<26} {'Date':<12} {'KPI':<24} {'T':>2}  "
          f"{'Sev':<7}  {'V':>2}  {'Dir':<5}  {'Dev%':>7}  {'Z':>6}  "
          f"{'GT?':>4}  Methods")
    print()

    sorted_conf = confirmed.sort_values(
        ["date", "tier", "severity"],
        key=lambda col: col if col.name != "severity"
        else col.map({"HIGH": 0, "MEDIUM": 1, "LOW": 2}),
    )

    prev_date = None
    for _, row in sorted_conf.iterrows():
        d    = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
        sep  = "" if d == prev_date else "\n" if prev_date is not None else ""
        prev_date = d
        gt   = "YES" if row["anomaly_flag"] == 1 else "no"
        dev  = f"{row['deviation_pct']:+.1f}%" if pd.notna(row["deviation_pct"]) else "  N/A"
        z    = f"{row['z_score']:+.2f}"         if pd.notna(row["z_score"])       else "  N/A"
        print(f"{sep}  {row['anomaly_id']:<26} {d:<12} {row['kpi']:<24} "
              f"{int(row['tier']):>2}  {row['severity']:<7}  {int(row['votes']):>2}  "
              f"{row['direction']:<5}  {dev:>7}  {z:>6}  "
              f"{gt:>4}  {row['methods_flagged']}")

    print()

    # " -- " Ground-truth evaluation " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
    print("-" * W)
    print(f"  Ground-Truth Evaluation  "
          f"({metrics['total_anomaly_days']} labeled anomaly days  vs  "
          f"{metrics['total_flagged_days']} confirmed-anomaly days)")
    print("-" * W)
    print(f"  True positives   : {metrics['tp']:>3}  (anomaly days correctly caught)")
    print(f"  False positives  : {metrics['fp']:>3}  (normal days with confirmed anomaly)")
    print(f"  False negatives  : {metrics['fn']:>3}  (anomaly days with no confirmed signal)")
    print()
    print(f"  Precision  :  {metrics['precision']:.3f}")
    print(f"  Recall     :  {metrics['recall']:.3f}")
    print(f"  F1 Score   :  {metrics['f1_score']:.3f}")
    print()

    if not metrics["caught"].empty:
        print(f"  Anomaly days CAUGHT  "
              f"({len(metrics['caught'])}/{metrics['total_anomaly_days']}):")
        for _, row in metrics["caught"].sort_values("date").iterrows():
            d = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
            day_conf = confirmed[confirmed["date"] == pd.Timestamp(row["date"])]
            kpis_conf = day_conf["kpi"].tolist()
            sevs_conf = day_conf["severity"].tolist()
            details   = ", ".join(f"{k} [{s}]" for k, s in zip(kpis_conf, sevs_conf))
            print(f"    [+]  {d}  |  {str(row['anomaly_event']):<35}  "
                  f"(target: {row['anomaly_kpi']})  ->  {details}")

    if not metrics["missed"].empty:
        print()
        print(f"  Anomaly days MISSED  "
              f"({len(metrics['missed'])}/{metrics['total_anomaly_days']}):")
        for _, row in metrics["missed"].sort_values("date").iterrows():
            d = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
            print(f"    [-]  {d}  |  {str(row['anomaly_event']):<35}  "
                  f"(target: {row['anomaly_kpi']})  "
                  f"-- only Method A detected; B and C both missed")

    # " -- " Method comparison " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
    print()
    print("-" * W)
    print("  Method Comparison  (day-level precision / recall / F1  |  20 ground-truth anomaly days)")
    print("-" * W)
    print(f"  {'Method':<28} {'Flagged days':>13} {'TP':>4} {'FP':>5} {'FN':>4} "
          f"{'Precision':>10} {'Recall':>8} {'F1':>7}")
    print()

    rows = list(INDIVIDUAL_RESULTS.items()) + [
        ("Ensemble (>=2 methods)", {
            "flagged": metrics["total_flagged_days"],
            "tp": metrics["tp"],
            "fp": metrics["fp"],
            "fn": metrics["fn"],
        })
    ]
    for name, r in rows:
        tp, fp, fn = r["tp"], r["fp"], r["fn"]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        bold = ">>  " if "Ensemble" in name else "    "
        print(f"  {bold}{name:<24} {r['flagged']:>13,} {tp:>4} {fp:>5} {fn:>4} "
              f"{prec:>10.3f} {rec:>8.3f} {f1:>7.3f}")

    print()
    print("=" * W)


# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
# Write outputs
# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "

def write_outputs(confirmed: pd.DataFrame,
                  matrix: pd.DataFrame) -> None:
    # Format dates for CSV/SQLite
    conf_out   = confirmed.copy()
    matrix_out = matrix.copy()
    conf_out["date"]   = conf_out["date"].dt.strftime("%Y-%m-%d")
    matrix_out["date"] = matrix_out["date"].dt.strftime("%Y-%m-%d")

    # Reorder confirmed anomaly columns to match the output schema
    conf_cols = [
        "anomaly_id", "date", "kpi", "tier", "severity", "votes",
        "methods_flagged", "direction",
        "actual_value", "expected_value", "deviation_pct", "z_score",
        "method_b_score", "yhat", "yhat_lower", "yhat_upper",
        "flag_a1", "flag_a2", "flag_a3",
        "method_a_flag", "method_b_flag", "method_c_flag",
        "anomaly_flag", "anomaly_event", "anomaly_kpi",
    ]
    conf_out = conf_out[[c for c in conf_cols if c in conf_out.columns]]

    conf_out.to_csv(OUTPUT_CSV, index=False)
    print(f"  CSV written    ->  {OUTPUT_CSV.relative_to(BASE)}")
    print(f"  Shape          :   {conf_out.shape[0]} rows x {conf_out.shape[1]} cols "
          f"({conf_out['date'].nunique()} unique anomaly dates)")

    matrix_out.to_csv(MATRIX_CSV, index=False)
    print(f"  Matrix CSV     ->  {MATRIX_CSV.relative_to(BASE)}")
    print(f"  Shape          :   {matrix_out.shape[0]:,} rows x {matrix_out.shape[1]} cols "
          f"(full voting record -- all 8,772 KPI-day pairs)")

    conn = sqlite3.connect(OUTPUT_DB)
    conf_out.to_sql("anomaly_results",          conn, if_exists="replace", index=False)
    matrix_out.to_sql("ensemble_voting_matrix", conn, if_exists="replace", index=False)
    conn.close()
    print(f"  SQLite written ->  {OUTPUT_DB.relative_to(BASE)}")
    print(f"                     tables: anomaly_results, ensemble_voting_matrix")


# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "
# Main
# " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- " -- "

def main() -> None:
    print()
    print("=" * 60)
    print("  Step 2.3 - Ensemble Voting")
    print("=" * 60)

    print("  Loading method results ...")
    a, b, c = load_methods()
    print(f"    Method A : {len(a):,} rows  |  "
          f"Method B : {len(b):,} rows  |  "
          f"Method C : {len(c):,} rows")

    print("  Building 8,772-row vote matrix ...")
    matrix = build_matrix(a, b, c)
    matrix = add_votes(matrix)

    print("  Applying direction filter ...")
    pig_map = build_pig_map(load_tier_config())
    matrix  = apply_direction_filter(matrix, pig_map)

    n_vote_confirmed = int(matrix["confirmed"].sum())
    n_dir_suppressed = int((matrix["confirmed"] & matrix["direction_suppressed"]).sum())
    confirmed = matrix[matrix["confirmed"] & ~matrix["direction_suppressed"]].copy()

    print(f"  Vote-confirmed       : {n_vote_confirmed} KPI-day records")
    print(f"  Direction-suppressed : {n_dir_suppressed} "
          f"(UP on positive_is_good KPI | DOWN on inverse KPI)")
    print(f"  Confirmed anomalies  : {len(confirmed)} KPI-day records  "
          f"({confirmed['date'].nunique()} unique dates)")
    print()

    metrics = evaluate(matrix)
    print_summary(matrix, confirmed, metrics)

    print("  Writing outputs ...")
    write_outputs(confirmed, matrix)
    print()
    print("  Step 2.3 complete.")
    print("  anomaly_results.csv is ready for Layer 3 (Root Cause Analysis).")
    print()


if __name__ == "__main__":
    main()
