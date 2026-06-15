#!/usr/bin/env python3
"""
ingest_and_engineer.py

Reads master_dataset.csv, computes 6 feature-engineering columns for every
primary KPI, and writes the processed result to:
    data/processed_kpi_features.csv   -- full-history feature table
    data/kpi_anomaly_detection.db     -- SQLite database (dashboard source)

Six features are added per KPI  (column naming: {kpi}_{feature}):
    rolling_mean   7-day rolling mean             — smooths daily noise
    rolling_std    7-day rolling std              — dynamic threshold baseline
    z_score        (kpi - rolling_mean) / rolling_std  — standardised deviation
    wow_change     (today - 7d ago)  / |7d ago|   — week-over-week % shift
    mom_change     (today - 30d ago) / |30d ago|  — month-over-month % shift
    lag_1          prior-day value                — short-term momentum input

KPI tiers (from architecture):
    Tier 1 — alert immediately:   total_revenue_usd, n_orders, avg_roas, conversion_rate
    Tier 2 — alert within 1 hour: return_rate, n_stockouts, avg_order_value_usd, bounce_rate
    Tier 3 — daily digest:        total_clicks, sessions, inventory_health, avg_discount_pct
    Supporting:                   remaining numeric KPIs in master_dataset.csv

Run from project root:  python scripts/ingest_and_engineer.py
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

BASE = Path(__file__).parent.parent
DATA = BASE / "data"

INPUT_FILE  = DATA / "master_dataset.csv"
OUTPUT_CSV  = DATA / "processed_kpi_features.csv"
OUTPUT_DB   = DATA / "kpi_anomaly_detection.db"
DB_TABLE    = "processed_kpis"

ROLLING_WINDOW = 7    # days — rolling mean / std window
WOW_LAG        = 7    # days — week-over-week comparison
MOM_LAG        = 30   # days — month-over-month comparison

# Non-KPI columns — excluded from feature engineering
NON_KPI_COLS = {
    "date",
    # Exogenous control variables — model inputs, not detection targets
    # (inventory_health is intentionally kept: it is a Tier 3 monitored KPI)
    "economic_index", "marketing_pressure", "consumer_sentiment", "seasonal_index",
    # Anomaly labels
    "anomaly_flag", "anomaly_event", "anomaly_kpi",
}

# KPI tiers drive alert routing in downstream detection layer
TIER_1 = ["total_revenue_usd", "n_orders", "avg_roas", "conversion_rate"]
TIER_2 = ["return_rate", "n_stockouts", "avg_order_value_usd", "bounce_rate"]
TIER_3 = ["total_clicks", "sessions", "inventory_health", "avg_discount_pct"]

TIER_MAP = {kpi: 1 for kpi in TIER_1}
TIER_MAP.update({kpi: 2 for kpi in TIER_2})
TIER_MAP.update({kpi: 3 for kpi in TIER_3})


# ─────────────────────────────────────────────────────────────
# Step 1 — Load
# ─────────────────────────────────────────────────────────────

def load_master(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    print(f"Loaded {len(df):,} rows  ({df['date'].min().date()} to {df['date'].max().date()})")
    return df


# ─────────────────────────────────────────────────────────────
# Step 2 — Identify KPI columns
# ─────────────────────────────────────────────────────────────

def get_kpi_columns(df: pd.DataFrame) -> list[str]:
    """Return all numeric columns that are KPI targets (not control variables or labels)."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    kpi_cols = [c for c in numeric_cols if c not in NON_KPI_COLS]
    return kpi_cols


# ─────────────────────────────────────────────────────────────
# Step 3 — Feature engineering
# ─────────────────────────────────────────────────────────────

def engineer_features(df: pd.DataFrame, kpi_cols: list[str]) -> pd.DataFrame:
    """
    Compute 6 feature columns for every KPI and return a single wide DataFrame.
    All new columns are built into a dict first and concatenated once to avoid
    the DataFrame fragmentation PerformanceWarning from repeated column inserts.
    """
    feature_dict: dict[str, pd.Series] = {}

    for kpi in kpi_cols:
        series = df[kpi].astype(float)

        # ── Rolling statistics ────────────────────────────────────────────────
        roll_mean = series.rolling(ROLLING_WINDOW, min_periods=1).mean()
        roll_std  = series.rolling(ROLLING_WINDOW, min_periods=2).std()

        # ── Z-score: (value − mean) / std ────────────────────────────────────
        # Replace zero std with NaN so result is NaN rather than ±Inf
        safe_std  = roll_std.replace(0, np.nan)
        z_score   = (series - roll_mean) / safe_std

        # ── WoW % change: (today − 7d ago) / |7d ago| ────────────────────────
        base_wow  = series.shift(WOW_LAG)
        wow       = (series - base_wow) / base_wow.replace(0, np.nan).abs()

        # ── MoM % change: (today − 30d ago) / |30d ago| ──────────────────────
        base_mom  = series.shift(MOM_LAG)
        mom       = (series - base_mom) / base_mom.replace(0, np.nan).abs()

        # ── 1-day lag ─────────────────────────────────────────────────────────
        lag_1     = series.shift(1)

        feature_dict[f"{kpi}_rolling_mean"] = roll_mean.round(4)
        feature_dict[f"{kpi}_rolling_std"]  = roll_std.round(4)
        feature_dict[f"{kpi}_z_score"]      = z_score.round(4)
        feature_dict[f"{kpi}_wow_change"]   = wow.round(4)
        feature_dict[f"{kpi}_mom_change"]   = mom.round(4)
        feature_dict[f"{kpi}_lag_1"]        = lag_1.round(4)

    # Single concat — avoids fragmentation from per-column inserts
    features_df = pd.DataFrame(feature_dict, index=df.index)
    return pd.concat([df, features_df], axis=1)


# ─────────────────────────────────────────────────────────────
# Step 4 — Write outputs
# ─────────────────────────────────────────────────────────────

def write_csv(df: pd.DataFrame, path: Path) -> None:
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df.to_csv(path, index=False)
    print(f"CSV written    -> {path.relative_to(BASE)}")


def write_sqlite(df: pd.DataFrame, db_path: Path, table: str) -> None:
    conn = sqlite3.connect(db_path)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d") if df["date"].dtype != object else df["date"]
    df.to_sql(table, conn, if_exists="replace", index=False)
    conn.close()
    print(f"SQLite written -> {db_path.relative_to(BASE)}  (table: {table})")


# ─────────────────────────────────────────────────────────────
# Step 5 — Summary
# ─────────────────────────────────────────────────────────────

def print_summary(df_raw: pd.DataFrame, df_eng: pd.DataFrame, kpi_cols: list[str]) -> None:
    new_cols = [c for c in df_eng.columns if c not in df_raw.columns]
    tiered   = {1: [], 2: [], 3: [], 0: []}
    for kpi in kpi_cols:
        tiered[TIER_MAP.get(kpi, 0)].append(kpi)

    print()
    print("=" * 64)
    print("Feature Engineering Summary")
    print("=" * 64)
    print(f"  Input  shape : {df_raw.shape[0]} rows x {df_raw.shape[1]} cols")
    print(f"  Output shape : {df_eng.shape[0]} rows x {df_eng.shape[1]} cols")
    print(f"  New columns  : {len(new_cols)}  ({len(kpi_cols)} KPIs x 6 features)")
    print()
    print(f"  Tier 1 KPIs ({len(tiered[1])})  : {tiered[1]}")
    print(f"  Tier 2 KPIs ({len(tiered[2])})  : {tiered[2]}")
    print(f"  Tier 3 KPIs ({len(tiered[3])})  : {tiered[3]}")
    if tiered[0]:
        print(f"  Supporting  ({len(tiered[0])}) : {tiered[0]}")
    print()

    # Show engineered features for the latest date
    latest = df_eng.iloc[-1]
    print(f"  Latest date: {latest['date']}")
    print()
    print(f"  {'KPI':<32} {'value':>10} {'z_score':>9} {'wow':>9} {'mom':>9}")
    print(f"  {'-'*32} {'-'*10} {'-'*9} {'-'*9} {'-'*9}")
    for kpi in TIER_1 + TIER_2 + TIER_3:
        if kpi not in df_eng.columns:
            continue
        val     = latest.get(kpi,                  float("nan"))
        z       = latest.get(f"{kpi}_z_score",      float("nan"))
        wow     = latest.get(f"{kpi}_wow_change",   float("nan"))
        mom     = latest.get(f"{kpi}_mom_change",   float("nan"))
        print(f"  {kpi:<32} {val:>10.3f} {z:>9.3f} {wow:>9.3f} {mom:>9.3f}")

    print("=" * 64)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 64)
    print("KPI Feature Engineering Pipeline")
    print("=" * 64)

    # 1. Load
    df_raw = load_master(INPUT_FILE)

    # 2. Identify KPI columns
    kpi_cols = get_kpi_columns(df_raw)
    print(f"KPI columns identified: {len(kpi_cols)}")

    # 3. Engineer features
    print("Computing features...")
    df_eng = engineer_features(df_raw, kpi_cols)

    # 4. Write outputs
    write_csv(df_eng.copy(), OUTPUT_CSV)
    write_sqlite(df_eng.copy(), OUTPUT_DB, DB_TABLE)

    # 5. Summary
    print_summary(df_raw, df_eng, kpi_cols)


if __name__ == "__main__":
    main()
