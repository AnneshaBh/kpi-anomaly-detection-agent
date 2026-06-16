#!/usr/bin/env python3
"""
2.1_KPI_Monitoring_Tiers.py

Defines the KPI monitoring tier configuration for the anomaly detection engine.
Loads processed_kpi_features.csv, prints a live status dashboard for every
tiered KPI, and exports data/tier_config.json for use by Steps 2.2 onward.

Z-score zones (consistent across all tiers):
    NORMAL   |z| <= 1.5
    WATCH    1.5 < |z| <= 2.5
    ANOMALY  2.5 < |z| <= 3.5
    SEVERE   |z| > 3.5

Run from project root:  python scripts/2.1_KPI_Monitoring_Tiers.py
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Tier Configuration
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

TIER_CONFIG = {
    1: {
        "label":           "TIER 1 - ALERT IMMEDIATELY",
        "alert_sla":       "< 10 minutes",
        "z_anomaly":       2.5,
        "z_severe":        3.5,
        "z_watch":         1.5,
        "wow_threshold":   0.20,
        "mom_threshold":   0.15,
        "kpis": [
            "total_revenue_usd",
            "n_orders",
            "avg_roas",
            "conversion_rate",
        ],
    },
    2: {
        "label":           "TIER 2 - ALERT WITHIN 1 HOUR",
        "alert_sla":       "< 1 hour",
        "z_anomaly":       2.5,
        "z_severe":        3.5,
        "z_watch":         1.5,
        "wow_threshold":   0.20,
        "mom_threshold":   0.15,
        "kpis": [
            "return_rate",
            "n_stockouts",
            "avg_order_value_usd",
            "bounce_rate",
        ],
    },
    3: {
        "label":           "TIER 3 - DAILY DIGEST",
        "alert_sla":       "24 hours",
        "z_anomaly":       3.0,
        "z_severe":        3.5,
        "z_watch":         1.5,
        "wow_threshold":   0.25,
        "mom_threshold":   0.20,
        "kpis": [
            "total_clicks",
            "sessions",
            "inventory_health",
            "avg_discount_pct",
        ],
    },
}

# Flat lookup: kpi_name â†’ tier number
KPI_TIER_MAP = {
    kpi: tier
    for tier, cfg in TIER_CONFIG.items()
    for kpi in cfg["kpis"]
}

# All 12 monitored KPIs in tier order
ALL_TIERED_KPIS = [kpi for cfg in TIER_CONFIG.values() for kpi in cfg["kpis"]]

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Paths
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

BASE        = Path(__file__).parent.parent.parent
DATA        = BASE / "data"
INPUT_CSV   = DATA / "processed/processed_kpi_features.csv"
OUTPUT_JSON = DATA / "config/tier_config.json"

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Z-score zone classifier
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def classify_zone(z: float, z_watch: float, z_anomaly: float, z_severe: float) -> str:
    if pd.isna(z):
        return "N/A"
    az = abs(z)
    if az > z_severe:
        return "SEVERE"
    if az > z_anomaly:
        return "ANOMALY"
    if az > z_watch:
        return "WATCH"
    return "NORMAL"


ZONE_SYMBOL = {
    "NORMAL":  " ",
    "WATCH":   "~",
    "ANOMALY": "!",
    "SEVERE":  "!!",
    "N/A":     "-",
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Load
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def load_features(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Latest-day status per KPI
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def latest_kpi_status(df: pd.DataFrame, kpi: str, tier: int) -> dict:
    cfg  = TIER_CONFIG[tier]
    row  = df.iloc[-1]

    value   = row.get(kpi, np.nan)
    mean    = row.get(f"{kpi}_rolling_mean", np.nan)
    std     = row.get(f"{kpi}_rolling_std",  np.nan)
    z       = row.get(f"{kpi}_z_score",      np.nan)
    wow     = row.get(f"{kpi}_wow_change",   np.nan)
    mom     = row.get(f"{kpi}_mom_change",   np.nan)
    zone    = classify_zone(z, cfg["z_watch"], cfg["z_anomaly"], cfg["z_severe"])

    return {
        "kpi": kpi, "tier": tier, "value": value,
        "rolling_mean": mean, "rolling_std": std,
        "z_score": z, "wow_change": wow, "mom_change": mom,
        "zone": zone,
    }


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Historical breach counts (full 731-day dataset)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def historical_breaches(df: pd.DataFrame, kpi: str, tier: int) -> dict:
    cfg    = TIER_CONFIG[tier]
    z_col  = f"{kpi}_z_score"
    if z_col not in df.columns:
        return {"watch": 0, "anomaly": 0, "severe": 0, "total_valid": 0}

    z_series = df[z_col].dropna().abs()
    return {
        "watch":       int((z_series > cfg["z_watch"]).sum()),
        "anomaly":     int((z_series > cfg["z_anomaly"]).sum()),
        "severe":      int((z_series > cfg["z_severe"]).sum()),
        "total_valid": int(z_series.notna().sum()),
    }


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Print dashboard
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def fmt_pct(v) -> str:
    if pd.isna(v):
        return "   N/A"
    return f"{v * 100:+6.1f}%"


def fmt_z(v) -> str:
    if pd.isna(v):
        return "  N/A"
    return f"{v:+6.2f}"


def fmt_val(v) -> str:
    if pd.isna(v):
        return "         N/A"
    if abs(v) >= 1_000:
        return f"{v:>12,.1f}"
    return f"{v:>12.4f}"


def print_dashboard(df: pd.DataFrame) -> None:
    latest_date   = df["date"].iloc[-1].strftime("%Y-%m-%d")
    anomaly_days  = int(df["anomaly_flag"].sum())
    normal_days   = len(df) - anomaly_days

    print()
    print("=" * 100)
    print("  KPI MONITORING TIERS - Configuration & Live Status")
    print("=" * 100)
    print(f"  Dataset : {INPUT_CSV.relative_to(BASE)}")
    print(f"  Latest  : {latest_date}  |  Total rows: {len(df)}  "
          f"|  Normal days: {normal_days}  |  Anomaly days: {anomaly_days}")
    print()
    print("  Zone legend:  [ ] NORMAL  [~] WATCH  [!] ANOMALY  [!!] SEVERE")
    print()

    hdr = (f"  {'KPI':<28} {'Latest Value':>13} {'Rolling Mean':>13} "
           f"{'Z-Score':>8} {'WoW%':>7} {'MoM%':>7}  {'Zone':<8}  "
           f"{'Watch':>6} {'Anom':>5} {'Sev':>4}")

    for tier_num, cfg in TIER_CONFIG.items():
        print("-" * 100)
        print(f"  {cfg['label']}  |  SLA: {cfg['alert_sla']}  |  "
              f"Z threshold: +/-{cfg['z_anomaly']}  |  Severe: +/-{cfg['z_severe']}  |  "
              f"WoW: +/-{cfg['wow_threshold']*100:.0f}%  |  MoM: +/-{cfg['mom_threshold']*100:.0f}%")
        print("-" * 100)
        print(hdr)
        print()

        for kpi in cfg["kpis"]:
            s  = latest_kpi_status(df, kpi, tier_num)
            h  = historical_breaches(df, kpi, tier_num)
            sym = ZONE_SYMBOL[s["zone"]]

            row_str = (
                f"  {kpi:<28}"
                f"{fmt_val(s['value'])}"
                f"{fmt_val(s['rolling_mean'])}"
                f"  {fmt_z(s['z_score'])}"
                f"  {fmt_pct(s['wow_change'])}"
                f"  {fmt_pct(s['mom_change'])}"
                f"  [{sym:<2}] {s['zone']:<8}"
                f"  {h['watch']:>5}"
                f"  {h['anomaly']:>4}"
                f"  {h['severe']:>3}"
            )
            print(row_str)

        print()

    print("=" * 100)
    print("  Column guide:")
    print("    Latest Value  - raw KPI value on the most recent date in the dataset")
    print("    Rolling Mean  - 7-day rolling average on the most recent date")
    print("    Z-Score       - (value - rolling_mean) / rolling_std on most recent date")
    print("    WoW%          - week-over-week % change on most recent date")
    print("    MoM%          - month-over-month % change on most recent date")
    print("    Watch         - historical days in dataset where |z| exceeded WATCH threshold")
    print("    Anom          - historical days where |z| exceeded ANOMALY threshold")
    print("    Sev           - historical days where |z| exceeded SEVERE threshold")
    print("=" * 100)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Export tier_config.json
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def export_config(df: pd.DataFrame, path: Path) -> None:
    exportable = {}
    for tier_num, cfg in TIER_CONFIG.items():
        kpi_meta = {}
        for kpi in cfg["kpis"]:
            h = historical_breaches(df, kpi, tier_num)
            kpi_meta[kpi] = {
                "tier":          tier_num,
                "historical_watch_days":   h["watch"],
                "historical_anomaly_days": h["anomaly"],
                "historical_severe_days":  h["severe"],
                "total_valid_z_days":      h["total_valid"],
            }

        exportable[str(tier_num)] = {
            "label":          cfg["label"],
            "alert_sla":      cfg["alert_sla"],
            "z_watch":        cfg["z_watch"],
            "z_anomaly":      cfg["z_anomaly"],
            "z_severe":       cfg["z_severe"],
            "wow_threshold":  cfg["wow_threshold"],
            "mom_threshold":  cfg["mom_threshold"],
            "kpis":           cfg["kpis"],
            "kpi_metadata":   kpi_meta,
        }

    output = {
        "description": "KPI monitoring tier configuration for the anomaly detection engine",
        "generated_on": df["date"].iloc[-1].strftime("%Y-%m-%d"),
        "total_dataset_rows": len(df),
        "tiers": exportable,
        "kpi_tier_map": KPI_TIER_MAP,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Tier config exported  ->  {path.relative_to(BASE)}")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Main
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main() -> None:
    df = load_features(INPUT_CSV)
    print_dashboard(df)
    export_config(df, OUTPUT_JSON)
    print()
    print("  Step 2.1 complete. tier_config.json is ready for Steps 2.2 onward.")
    print()


if __name__ == "__main__":
    main()
