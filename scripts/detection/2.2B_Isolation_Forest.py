#!/usr/bin/env python3
"""
2.2B_Isolation_Forest.py

Method B of the Layer 2 anomaly detection ensemble â€” Isolation Forest.

Unlike Method A (per-KPI univariate flags), Isolation Forest operates on the
full 29-feature joint matrix simultaneously, catching correlated multi-KPI
anomalies (e.g. sessions spiking while conversion_rate drops) that
individual-column checks miss.

Design:
    Feature matrix  29 raw KPI columns from master_dataset  (0 NaN â€” no imputation needed)
    Scaler          StandardScaler  (fit on train set only â€” no data leakage)
    Model           IsolationForest(contamination=0.05, n_estimators=100, random_state=42)
    Train set       rows 0-583  (first 80% = 2024-01-01 to ~2025-07-31)
    Score set       all 731 rows  (full in-sample detection for historical audit)
    Output unit     row / day  (one flag per date, not per KPI)

Output:
    method_b_flag         True  if IsolationForest predicted -1 (anomaly)
    method_b_score        negated decision_function score  â€” higher = more anomalous
    method_b_prediction   raw sklearn output  (-1 anomaly, +1 normal)
    top_5_features        comma-separated list of the 5 most extreme standardised
                          features on that day  (interpretability aid)

Inputs :  data/processed_kpi_features.csv
          data/tier_config.json
Outputs:  data/kpi_anomaly_detection.db   table: method_b_results
          data/method_b_results.csv

Run from project root:  python scripts/2.2B_Isolation_Forest.py
"""

import json
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Paths & model configuration
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

BASE        = Path(__file__).parent.parent.parent
DATA        = BASE / "data"
INPUT_CSV   = DATA / "processed/processed_kpi_features.csv"
TIER_JSON   = DATA / "config/tier_config.json"
OUTPUT_CSV  = DATA / "detection/method_b_results.csv"
OUTPUT_DB   = DATA / "db/kpi_anomaly_detection.db"
DB_TABLE    = "method_b_results"

TRAIN_FRAC       = 0.80
CONTAMINATION    = 0.05
N_ESTIMATORS     = 100
RANDOM_STATE     = 42
TOP_N_FEATURES   = 5   # most extreme features to report per flagged day

ENGINEERED_SUFFIXES = (
    "_rolling_mean", "_rolling_std", "_z_score",
    "_wow_change",   "_mom_change",  "_lag_1",
)
EXCLUDE_COLS = {"date", "anomaly_flag", "anomaly_event", "anomaly_kpi"}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Load
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def load_inputs():
    df = pd.read_csv(INPUT_CSV, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    with open(TIER_JSON, encoding="utf-8") as f:
        tier_cfg = json.load(f)
    return df, tier_cfg


def get_feature_cols(df: pd.DataFrame) -> list[str]:
    """29 raw KPI columns â€” original master_dataset values, no engineered features."""
    return [
        c for c in df.columns
        if c not in EXCLUDE_COLS
        and not any(c.endswith(s) for s in ENGINEERED_SUFFIXES)
    ]

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Train / score
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run_isolation_forest(df: pd.DataFrame,
                         feature_cols: list[str]) -> pd.DataFrame:
    X = df[feature_cols].values.astype(float)

    n_train     = int(len(df) * TRAIN_FRAC)
    train_idx   = slice(0, n_train)
    train_date  = df["date"].iloc[n_train - 1].strftime("%Y-%m-%d")
    X_train     = X[train_idx]

    # Scaler fitted on train set only
    scaler  = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_scaled       = scaler.transform(X)

    # IsolationForest
    clf = IsolationForest(
        contamination=CONTAMINATION,
        n_estimators=N_ESTIMATORS,
        random_state=RANDOM_STATE,
    )
    clf.fit(X_train_scaled)

    predictions = clf.predict(X_scaled)            # -1 = anomaly, +1 = normal
    scores      = -clf.decision_function(X_scaled) # negate: higher = more anomalous

    # Top-N most extreme standardised features per row (for interpretability)
    z_matrix = np.abs(X_scaled)
    top_cols = []
    for i in range(len(df)):
        top_idx = np.argsort(z_matrix[i])[::-1][:TOP_N_FEATURES]
        top_cols.append(", ".join(feature_cols[j] for j in top_idx))

    in_train = [i < n_train for i in range(len(df))]

    print(f"  Train rows : {n_train}  "
          f"(2024-01-01 to {train_date})")
    print(f"  Score rows : {len(df)}  "
          f"(full dataset â€” in-sample detection)")
    print(f"  Contamination={CONTAMINATION}  "
          f"-> ~{int(n_train * CONTAMINATION)} expected anomalies in train")

    results = pd.DataFrame({
        "date":               df["date"],
        "method_b_flag":      predictions == -1,
        "method_b_score":     np.round(scores, 5),
        "method_b_prediction":predictions,
        "in_train_set":       in_train,
        "top_5_features":     top_cols,
        "anomaly_flag":       df["anomaly_flag"].values,
        "anomaly_event":      df["anomaly_event"].values,
        "anomaly_kpi":        df["anomaly_kpi"].values,
    })

    return results, scaler, clf, feature_cols, n_train

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Evaluation
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def evaluate(results: pd.DataFrame) -> dict:
    tp = int(((results["anomaly_flag"] == 1) &  results["method_b_flag"]).sum())
    fp = int(((results["anomaly_flag"] == 0) &  results["method_b_flag"]).sum())
    fn = int(((results["anomaly_flag"] == 1) & ~results["method_b_flag"]).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    caught = results.loc[(results["anomaly_flag"] == 1) &  results["method_b_flag"]].copy()
    missed = results.loc[(results["anomaly_flag"] == 1) & ~results["method_b_flag"]].copy()

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 3),
        "recall":    round(recall, 3),
        "f1_score":  round(f1, 3),
        "total_anomaly_days":  int((results["anomaly_flag"] == 1).sum()),
        "total_flagged_days":  int(results["method_b_flag"].sum()),
        "caught": caught,
        "missed": missed,
    }

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Print summary
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def print_summary(results: pd.DataFrame, metrics: dict,
                  feature_cols: list[str], n_train: int) -> None:
    W = 110

    print()
    print("=" * W)
    print("  METHOD B - ISOLATION FOREST  |  Detection Results  |  731 days")
    print("=" * W)
    print(f"  Feature matrix  :  {len(feature_cols)} raw KPI columns  "
          f"(all original master_dataset numeric columns, exogenous variables included)")
    print(f"  Model           :  IsolationForest  "
          f"contamination={CONTAMINATION}  n_estimators={N_ESTIMATORS}  "
          f"random_state={RANDOM_STATE}")
    print(f"  Scaler          :  StandardScaler fitted on train set only (no data leakage)")
    print(f"  Train / Score   :  {n_train} rows train  /  {len(results)} rows scored  "
          f"(all in-sample)")
    print(f"  Score direction :  higher method_b_score = more anomalous")
    print()

    # â”€â”€ Score distribution â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    flagged    = results[results["method_b_flag"]]
    non_flagged = results[~results["method_b_flag"]]

    print("-" * W)
    print("  Anomaly Score Distribution")
    print("-" * W)
    print(f"  {'Group':<20} {'Count':>6}  {'Mean':>8}  {'Std':>8}  "
          f"{'Min':>8}  {'Median':>8}  {'Max':>8}")
    print()
    for label, grp in [("All days", results),
                        ("Flagged (anomaly)", flagged),
                        ("Not flagged", non_flagged)]:
        s = grp["method_b_score"]
        print(f"  {label:<20} {len(grp):>6}  {s.mean():>8.4f}  {s.std():>8.4f}  "
              f"{s.min():>8.4f}  {s.median():>8.4f}  {s.max():>8.4f}")
    print()

    # â”€â”€ All flagged days (sorted by score desc) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    total_flagged = int(results["method_b_flag"].sum())
    print("-" * W)
    print(f"  All Flagged Days  ({total_flagged} days  |  "
          f"{total_flagged/len(results)*100:.1f}% of dataset)  â€”  "
          f"sorted by anomaly score descending")
    print("-" * W)
    print(f"  {'Date':<12} {'Score':>8}  {'Train?':>7}  "
          f"{'GT Anomaly?':>12}  {'Event':<36}  Top Features")
    print()

    flagged_sorted = results[results["method_b_flag"]].sort_values(
        "method_b_score", ascending=False
    )
    for _, row in flagged_sorted.iterrows():
        d      = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
        score  = f"{row['method_b_score']:.4f}"
        train  = "yes" if row["in_train_set"] else "no"
        is_gt  = "YES" if row["anomaly_flag"] == 1 else "no"
        event  = str(row["anomaly_event"]) if row["anomaly_flag"] == 1 else "-"
        feats  = row["top_5_features"]
        print(f"  {d:<12} {score:>8}  {train:>7}  "
              f"{is_gt:>12}  {event:<36}  {feats}")

    print()

    # â”€â”€ Evaluation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("-" * W)
    print(f"  Ground-Truth Evaluation  "
          f"({metrics['total_anomaly_days']} anomaly days  vs  "
          f"{metrics['total_flagged_days']} flagged days)")
    print("-" * W)
    print(f"  True positives   : {metrics['tp']:>3}  (anomaly days correctly caught)")
    print(f"  False positives  : {metrics['fp']:>3}  (normal days incorrectly flagged)")
    print(f"  False negatives  : {metrics['fn']:>3}  (anomaly days missed)")
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
            print(f"    [+]  {d}  "
                  f"score={row['method_b_score']:.4f}  |  "
                  f"{row['anomaly_event']}  "
                  f"(target: {row['anomaly_kpi']})")

    if not metrics["missed"].empty:
        print()
        print(f"  Anomaly days MISSED  "
              f"({len(metrics['missed'])}/{metrics['total_anomaly_days']}):")
        for _, row in metrics["missed"].sort_values("date").iterrows():
            d = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
            print(f"    [-]  {d}  "
                  f"score={row['method_b_score']:.4f}  |  "
                  f"{row['anomaly_event']}  "
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
    print(f"  Shape          :   {out.shape[0]} rows x {out.shape[1]} cols")

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
    print("  Method B - Isolation Forest")
    print("=" * 60)

    df, tier_cfg = load_inputs()
    print(f"  Loaded {len(df):,} rows  "
          f"({df['date'].min().date()} to {df['date'].max().date()})")

    feature_cols = get_feature_cols(df)
    print(f"  Feature columns: {len(feature_cols)}  (0 NaN â€” no imputation required)")
    print()

    print("  Fitting IsolationForest ...")
    results, scaler, clf, feature_cols, n_train = run_isolation_forest(df, feature_cols)

    print(f"  Flagged days   : {results['method_b_flag'].sum()}  "
          f"({results['method_b_flag'].sum()/len(results)*100:.1f}% of all days)")
    print()

    metrics = evaluate(results)
    print_summary(results, metrics, feature_cols, n_train)

    print("  Writing outputs ...")
    write_outputs(results)
    print()
    print("  Step 2.2B complete.")
    print("  method_b_results is ready for the ensemble voting step.")
    print()


if __name__ == "__main__":
    main()
