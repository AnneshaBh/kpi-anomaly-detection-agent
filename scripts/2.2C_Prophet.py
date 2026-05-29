#!/usr/bin/env python3
"""
2.2C_Prophet.py

Method C of the Layer 2 anomaly detection ensemble — Prophet Forecasting.

Runs on the four Tier 1 KPIs only:
    total_revenue_usd, n_orders, avg_roas, conversion_rate

For each KPI a Prophet model is fit with:
    weekly_seasonality  = True
    yearly_seasonality  = True
    daily_seasonality   = False
    interval_width      = 0.95  (95% prediction interval)
    Regressors          : economic_index, seasonal_index, marketing_pressure

A day/KPI is flagged (method_c_flag = True) if the actual value falls outside
the 95% prediction interval [yhat_lower, yhat_upper].

Prophet explicitly decomposes trend, weekly and yearly seasonality, and the
three exogenous regressors — making it the strongest method for catching
structural breaks and holiday/seasonal anomalies.

In-sample detection: each model is fit on all 731 days and scored on the
same dataset (full historical audit).

Inputs :  data/processed_kpi_features.csv
          data/tier_config.json
Outputs:  data/kpi_anomaly_detection.db   table: method_c_results
          data/method_c_results.csv        (long-format, 2,924 rows)

Run from project root:  python scripts/2.2C_Prophet.py
"""

import json
import logging
import sqlite3
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from prophet import Prophet

# Suppress verbose Stan / Prophet logs
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# Paths & configuration
# ─────────────────────────────────────────────────────────────

BASE        = Path(__file__).parent.parent
DATA        = BASE / "data"
INPUT_CSV   = DATA / "processed_kpi_features.csv"
TIER_JSON   = DATA / "tier_config.json"
OUTPUT_CSV  = DATA / "method_c_results.csv"
OUTPUT_DB   = DATA / "kpi_anomaly_detection.db"
DB_TABLE    = "method_c_results"

INTERVAL_WIDTH = 0.95
REGRESSORS     = ["economic_index", "seasonal_index", "marketing_pressure"]

# Matches anomaly_kpi labels to Tier 1 column names (for per-KPI evaluation)
ANOMALY_KPI_MAP = {
    "revenue":          "total_revenue_usd",
    "sales_volume":     "n_orders",
    "roas":             "avg_roas",
    "conversion_rate":  "conversion_rate",
}

# ─────────────────────────────────────────────────────────────
# Load
# ─────────────────────────────────────────────────────────────

def load_inputs():
    df = pd.read_csv(INPUT_CSV, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    with open(TIER_JSON, encoding="utf-8") as f:
        tier_cfg = json.load(f)
    return df, tier_cfg

# ─────────────────────────────────────────────────────────────
# Fit Prophet and score one KPI
# ─────────────────────────────────────────────────────────────

def fit_prophet(df: pd.DataFrame, kpi: str) -> pd.DataFrame:
    """
    Fit a Prophet model on `kpi` (all 731 rows) and return in-sample
    predictions with the method_c_flag per day.
    """
    prophet_df = pd.DataFrame({"ds": df["date"], "y": df[kpi].astype(float)})
    for reg in REGRESSORS:
        prophet_df[reg] = df[reg].values

    m = Prophet(
        interval_width=INTERVAL_WIDTH,
        weekly_seasonality=True,
        yearly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,   # default — moderate trend flexibility
        seasonality_prior_scale=10.0,   # default
    )
    for reg in REGRESSORS:
        m.add_regressor(reg)

    m.fit(prophet_df)

    # In-sample prediction (same dates as training)
    future   = prophet_df[["ds"] + REGRESSORS].copy()
    forecast = m.predict(future)

    actual     = df[kpi].values.astype(float)
    yhat       = forecast["yhat"].values
    yhat_lower = forecast["yhat_lower"].values
    yhat_upper = forecast["yhat_upper"].values

    # Flag: actual falls outside the 95% prediction interval
    flag = (actual < yhat_lower) | (actual > yhat_upper)

    # Direction and % deviation from model expectation
    direction = np.where(actual > yhat_upper, "UP",
                np.where(actual < yhat_lower, "DOWN", "NORMAL"))

    safe_yhat    = np.where(np.abs(yhat) > 1e-9, yhat, np.nan)
    deviation_pct = np.round((actual - yhat) / np.abs(safe_yhat) * 100, 2)

    interval_width_abs = np.round(yhat_upper - yhat_lower, 4)
    interval_width_pct = np.round(
        np.where(np.abs(safe_yhat) > 1e-9,
                 (yhat_upper - yhat_lower) / np.abs(safe_yhat) * 100,
                 np.nan),
        2,
    )

    return pd.DataFrame({
        "date":               df["date"],
        "kpi":                kpi,
        "tier":               1,
        "actual_value":       np.round(actual, 4),
        "yhat":               np.round(yhat, 4),
        "yhat_lower":         np.round(yhat_lower, 4),
        "yhat_upper":         np.round(yhat_upper, 4),
        "interval_width_abs": interval_width_abs,
        "interval_width_pct": interval_width_pct,
        "deviation_pct":      deviation_pct,
        "direction":          direction,
        "method_c_flag":      flag,
        "anomaly_flag":       df["anomaly_flag"].values,
        "anomaly_event":      df["anomaly_event"].values,
        "anomaly_kpi":        df["anomaly_kpi"].values,
    })

# ─────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────

def evaluate(results: pd.DataFrame) -> dict:
    """Day-level evaluation: a day is caught if any Tier 1 KPI was flagged."""
    daily = (
        results.groupby("date")["method_c_flag"]
        .any()
        .reset_index()
        .rename(columns={"method_c_flag": "flagged"})
    )
    gt = results[["date", "anomaly_flag", "anomaly_event", "anomaly_kpi"]].drop_duplicates("date")
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

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 3),
        "recall":    round(recall, 3),
        "f1_score":  round(f1, 3),
        "total_anomaly_days":  int((merged["anomaly_flag"] == 1).sum()),
        "total_flagged_days":  int(merged["flagged"].sum()),
        "caught": caught,
        "missed": missed,
    }

# ─────────────────────────────────────────────────────────────
# Print summary
# ─────────────────────────────────────────────────────────────

def print_summary(results: pd.DataFrame, metrics: dict) -> None:
    W = 110

    print()
    print("=" * W)
    print("  METHOD C - PROPHET FORECASTING  |  Detection Results  |  4 Tier 1 KPIs x 731 days")
    print("=" * W)
    print(f"  Model config  :  interval_width={INTERVAL_WIDTH}  (95% prediction interval)")
    print(f"  Seasonality   :  weekly=True  yearly=True  daily=False")
    print(f"  Regressors    :  {', '.join(REGRESSORS)}")
    print(f"  Scope         :  Tier 1 KPIs only  —  in-sample detection on all 731 days")
    print(f"  Flag rule     :  actual < yhat_lower  OR  actual > yhat_upper")
    print()

    # ── Per-KPI section ─────────────────────────────────────
    for kpi in results["kpi"].unique():
        sub = results[results["kpi"] == kpi].copy()
        sub_normal  = sub[sub["anomaly_flag"] == 0]
        coverage    = (~sub_normal["method_c_flag"]).mean() * 100
        n_flagged   = int(sub["method_c_flag"].sum())
        avg_ci_pct  = sub["interval_width_pct"].mean()
        n_up        = int((sub["method_c_flag"] & (sub["direction"] == "UP")).sum())
        n_down      = int((sub["method_c_flag"] & (sub["direction"] == "DOWN")).sum())

        print("-" * W)
        print(f"  KPI: {kpi}  (Tier 1)  "
              f"|  Flagged: {n_flagged} days ({n_flagged/731*100:.1f}%)  "
              f"|  Up: {n_up}  Down: {n_down}")
        print(f"  CI coverage on non-anomaly days: {coverage:.1f}%  "
              f"(expected ~95.0% for a well-calibrated 95% interval)")
        print(f"  Mean interval width: +/-{avg_ci_pct/2:.1f}% of yhat")
        print()

        flagged_kpi = (
            sub[sub["method_c_flag"]]
            .assign(abs_dev=lambda x: x["deviation_pct"].abs())
            .sort_values("abs_dev", ascending=False)
        )

        if not flagged_kpi.empty:
            print(f"  {'Date':<12} {'Actual':>12} {'yhat':>12} {'Lower':>12} {'Upper':>12} "
                  f"{'Dev%':>8} {'Dir':<6}  {'GT Anomaly?':<12}  Event")
            print()
            for _, row in flagged_kpi.iterrows():
                d     = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
                gt    = "YES" if row["anomaly_flag"] == 1 else "no"
                event = str(row["anomaly_event"]) if row["anomaly_flag"] == 1 else "-"
                print(f"  {d:<12} {row['actual_value']:>12,.4f} {row['yhat']:>12,.4f} "
                      f"{row['yhat_lower']:>12,.4f} {row['yhat_upper']:>12,.4f} "
                      f"{row['deviation_pct']:>7.1f}% {row['direction']:<6}  "
                      f"{gt:<12}  {event}")
        print()

    # ── Overall evaluation ──────────────────────────────────
    total_flagged = int(results["method_c_flag"].sum())
    print("=" * W)
    print(f"  Overall  |  {total_flagged} KPI-day flags across 4 KPIs  "
          f"(~{total_flagged//4} unique days)")
    print()
    print("-" * W)
    print(f"  Ground-Truth Evaluation  "
          f"({metrics['total_anomaly_days']} anomaly days  vs  "
          f"{metrics['total_flagged_days']} flagged days  (day-level: any KPI flagged = day caught))")
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
        caught_dates = metrics["caught"]["date"].dt.strftime("%Y-%m-%d").tolist() \
            if hasattr(metrics["caught"]["date"].iloc[0], "strftime") \
            else metrics["caught"]["date"].tolist()
        for _, row in metrics["caught"].sort_values("date").iterrows():
            d = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
            kpis_flagged = results.loc[
                (results["date"] == row["date"]) & results["method_c_flag"], "kpi"
            ].tolist()
            print(f"    [+]  {d}  |  {str(row['anomaly_event']):<35}  "
                  f"(target: {row['anomaly_kpi']})  ->  flagged KPIs: {kpis_flagged}")

    if not metrics["missed"].empty:
        print()
        print(f"  Anomaly days MISSED  "
              f"({len(metrics['missed'])}/{metrics['total_anomaly_days']}):")
        for _, row in metrics["missed"].sort_values("date").iterrows():
            d = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
            print(f"    [-]  {d}  |  {str(row['anomaly_event']):<35}  "
                  f"(target: {row['anomaly_kpi']})")

    print()
    print("=" * W)

# ─────────────────────────────────────────────────────────────
# Write outputs
# ─────────────────────────────────────────────────────────────

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

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print("=" * 60)
    print("  Method C - Prophet Forecasting")
    print("=" * 60)

    df, tier_cfg = load_inputs()
    print(f"  Loaded {len(df):,} rows  "
          f"({df['date'].min().date()} to {df['date'].max().date()})")

    tier1_kpis = tier_cfg["tiers"]["1"]["kpis"]
    print(f"  Tier 1 KPIs : {tier1_kpis}")
    print(f"  Regressors  : {REGRESSORS}")
    print()

    all_results = []
    for kpi in tier1_kpis:
        print(f"  Fitting Prophet for {kpi} ...", end=" ", flush=True)
        kpi_df = fit_prophet(df, kpi)
        n_flags = int(kpi_df["method_c_flag"].sum())
        print(f"done  ({n_flags} days flagged)")
        all_results.append(kpi_df)

    results = pd.concat(all_results, ignore_index=True)

    metrics = evaluate(results)
    print_summary(results, metrics)

    print("  Writing outputs ...")
    write_outputs(results)
    print()
    print("  Step 2.2C complete.")
    print("  method_c_results is ready for the ensemble voting step.")
    print()


if __name__ == "__main__":
    main()
