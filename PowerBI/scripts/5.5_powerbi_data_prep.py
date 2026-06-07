"""
Layer 5, Step 5.5 — Power BI Data Prep
Reshapes communication_results into a Power BI-optimised star schema.
Drops raw detection internals and long-text columns not suited for visuals.

Outputs (outputs/powerbi/)
  fact_anomalies.csv      181 rows x 40 cols  — main fact table
  dim_kpi.csv              12 rows x  5 cols  — KPI dimension
  dim_date.csv            731 rows x 13 cols  — full calendar (2024-01-01 to 2025-12-31)
  summary_kpi_impact.csv   17 rows x  7 cols  — KPI x priority_band aggregation
  summary_timeline.csv     68 rows x 10 cols  — daily anomaly timeline

Relationships for Power BI data model
  fact_anomalies[date] -> dim_date[date]   (many-to-one)
  fact_anomalies[kpi]  -> dim_kpi[kpi]    (many-to-one)

Input  : data/communication_results.csv  (181 x 78)
"""

import os
import sys

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(BASE_DIR, "data")
PBI_DIR     = os.path.join(BASE_DIR, "outputs", "powerbi")
COMM_CSV    = os.path.join(DATA_DIR, "communication_results.csv")

FACT_CSV    = os.path.join(PBI_DIR, "fact_anomalies.csv")
DIM_KPI_CSV = os.path.join(PBI_DIR, "dim_kpi.csv")
DIM_DATE_CSV = os.path.join(PBI_DIR, "dim_date.csv")
SUM_KPI_CSV = os.path.join(PBI_DIR, "summary_kpi_impact.csv")
SUM_TL_CSV  = os.path.join(PBI_DIR, "summary_timeline.csv")

os.makedirs(PBI_DIR, exist_ok=True)


# ── Constants ─────────────────────────────────────────────────────────────────
# Columns retained in the fact table — drops CI/DoWhy internals, scoring factors,
# long-text fields (alert_body, delivery_note), and redundant raw signals
FACT_COLS = [
    # Identity
    "anomaly_id", "date", "kpi",
    # Detection
    "tier", "severity", "direction", "deviation_pct", "z_score",
    # Driver
    "suspected_driver_kpi", "driver_direction",
    # Root cause
    "root_cause_confidence", "confidence_tier",
    "is_externally_driven", "external_driver_type",
    "actionability_score", "actionability_label",
    "escalation_suppressed", "rca_narrative",
    # Impact
    "revenue_at_risk", "margin_impact", "customer_impact",
    "monthly_shortfall", "impact_pct_of_plan", "impact_narrative",
    # Priority
    "priority_score", "priority_band", "priority_rank", "layer4_priority_flag",
    # Recommendations
    "immediate_action", "short_term_fix",
    "recommended_owner", "effort_level", "llm_enhanced",
    # Communication
    "urgency_label", "delivery_channel", "delivery_status",
    "sent_at", "message_id", "recipient", "alert_subject",
]

# KPI metadata for dim_kpi
KPI_META = {
    "total_revenue_usd":   {
        "kpi_label":   "Total Revenue (USD)",
        "kpi_category": "Revenue",
        "description": "Aggregate daily revenue from all completed orders",
    },
    "n_orders":            {
        "kpi_label":   "Order Volume",
        "kpi_category": "Revenue",
        "description": "Total number of completed orders per day",
    },
    "avg_roas":            {
        "kpi_label":   "Avg. ROAS",
        "kpi_category": "Marketing",
        "description": "Return on Ad Spend averaged across all paid channels",
    },
    "conversion_rate":     {
        "kpi_label":   "Conversion Rate",
        "kpi_category": "Marketing",
        "description": "Share of website sessions resulting in a purchase",
    },
    "return_rate":         {
        "kpi_label":   "Return Rate",
        "kpi_category": "Customer",
        "description": "Share of orders that were subsequently returned",
    },
    "avg_order_value_usd": {
        "kpi_label":   "Avg. Order Value (USD)",
        "kpi_category": "Revenue",
        "description": "Average spend per completed order",
    },
    "bounce_rate":         {
        "kpi_label":   "Bounce Rate",
        "kpi_category": "Marketing",
        "description": "Share of sessions leaving without viewing a second page",
    },
    "sessions":            {
        "kpi_label":   "Website Sessions",
        "kpi_category": "Traffic",
        "description": "Total website sessions per day",
    },
    "total_clicks":        {
        "kpi_label":   "Total Clicks",
        "kpi_category": "Marketing",
        "description": "Total paid ad clicks across all channels",
    },
    "avg_discount_pct":    {
        "kpi_label":   "Avg. Discount %",
        "kpi_category": "Revenue",
        "description": "Average discount fraction applied across all orders",
    },
    "inventory_health":    {
        "kpi_label":   "Inventory Health",
        "kpi_category": "Operations",
        "description": "Composite score of stock availability and reorder status",
    },
    "n_stockouts":         {
        "kpi_label":   "Stockout Count",
        "kpi_category": "Operations",
        "description": "Number of SKUs with zero stock on hand",
    },
}


# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading communication_results.csv ...")
df = pd.read_csv(COMM_CSV, parse_dates=["date"])
print(f"  Loaded {df.shape[0]} rows x {df.shape[1]} cols")
print()


# ── Build fact_anomalies ──────────────────────────────────────────────────────
print("Building fact_anomalies ...")
fact = df[FACT_COLS].copy().sort_values("priority_rank").reset_index(drop=True)
print(f"  {fact.shape[0]} rows x {fact.shape[1]} cols")


# ── Build dim_kpi ─────────────────────────────────────────────────────────────
print("Building dim_kpi ...")
kpi_tiers = df.groupby("kpi")["tier"].first().to_dict()

dim_kpi_rows = []
for kpi, meta in KPI_META.items():
    dim_kpi_rows.append({
        "kpi":          kpi,
        "kpi_label":    meta["kpi_label"],
        "tier":         kpi_tiers.get(kpi, None),
        "kpi_category": meta["kpi_category"],
        "description":  meta["description"],
    })
dim_kpi = (
    pd.DataFrame(dim_kpi_rows)
    .sort_values(["tier", "kpi_category", "kpi"])
    .reset_index(drop=True)
)
print(f"  {dim_kpi.shape[0]} rows x {dim_kpi.shape[1]} cols")


# ── Build dim_date ────────────────────────────────────────────────────────────
print("Building dim_date (2024-01-01 to 2025-12-31) ...")
_dates = pd.date_range("2024-01-01", "2025-12-31", freq="D")
dim_date = pd.DataFrame({"date": _dates})

dim_date["year"]             = dim_date["date"].dt.year
dim_date["quarter_num"]      = dim_date["date"].dt.quarter
dim_date["quarter_label"]    = "Q" + dim_date["quarter_num"].astype(str) + " " + dim_date["year"].astype(str)
dim_date["month_num"]        = dim_date["date"].dt.month
dim_date["month_name"]       = dim_date["date"].dt.strftime("%B")
dim_date["month_short"]      = dim_date["date"].dt.strftime("%b")
dim_date["year_month"]       = dim_date["date"].dt.strftime("%Y-%m")
dim_date["yyyymm"]           = dim_date["year"] * 100 + dim_date["month_num"]
dim_date["week_num"]         = dim_date["date"].dt.isocalendar().week.astype(int)
dim_date["day_of_week_num"]  = dim_date["date"].dt.weekday      # 0 = Monday, 6 = Sunday
dim_date["day_of_week_name"] = dim_date["date"].dt.strftime("%A")
dim_date["is_weekend"]       = dim_date["day_of_week_num"] >= 5

# Store date as string for clean CSV output
dim_date["date"] = dim_date["date"].dt.strftime("%Y-%m-%d")
print(f"  {dim_date.shape[0]} rows x {dim_date.shape[1]} cols")


# ── Build summary_kpi_impact ──────────────────────────────────────────────────
print("Building summary_kpi_impact ...")
summary_kpi = (
    df.groupby(["kpi", "priority_band"])
    .agg(
        anomaly_count       = ("anomaly_id",      "count"),
        revenue_at_risk_sum = ("revenue_at_risk",  lambda x: round(x[x > 0].sum(), 2)),
        upside_sum          = ("revenue_at_risk",  lambda x: round(abs(x[x < 0].sum()), 2)),
        net_revenue_impact  = ("revenue_at_risk",  lambda x: round(x.sum(), 2)),
        avg_priority_score  = ("priority_score",   lambda x: round(x.mean(), 4)),
        total_customer_impact = ("customer_impact", "sum"),
    )
    .reset_index()
    .sort_values(["kpi", "priority_band"])
    .reset_index(drop=True)
)
# Add KPI label for convenience
summary_kpi.insert(
    1, "kpi_label",
    summary_kpi["kpi"].map(lambda k: KPI_META.get(k, {}).get("kpi_label", k))
)
print(f"  {summary_kpi.shape[0]} rows x {summary_kpi.shape[1]} cols")


# ── Build summary_timeline ────────────────────────────────────────────────────
print("Building summary_timeline ...")
summary_tl = (
    df.groupby("date")
    .agg(
        anomaly_count     = ("anomaly_id",          "count"),
        escalate_count    = ("layer4_priority_flag", lambda x: (x == "ESCALATE").sum()),
        investigate_count = ("layer4_priority_flag", lambda x: (x == "INVESTIGATE").sum()),
        monitor_count     = ("layer4_priority_flag", lambda x: (x == "MONITOR").sum()),
        suppressed_count  = ("layer4_priority_flag", lambda x: (x == "SUPPRESSED").sum()),
        daily_at_risk     = ("revenue_at_risk",      lambda x: round(x[x > 0].sum(), 2)),
        daily_upside      = ("revenue_at_risk",      lambda x: round(abs(x[x < 0].sum()), 2)),
    )
    .reset_index()
    .sort_values("date")
    .reset_index(drop=True)
)
summary_tl["cumulative_at_risk"] = summary_tl["daily_at_risk"].cumsum().round(2)
summary_tl["cumulative_upside"]  = summary_tl["daily_upside"].cumsum().round(2)
summary_tl["date"] = summary_tl["date"].dt.strftime("%Y-%m-%d")
print(f"  {summary_tl.shape[0]} rows x {summary_tl.shape[1]} cols")
print()


# ── Quality assertions ────────────────────────────────────────────────────────
print("Running quality assertions ...")
failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"  PASS  {label}")
    else:
        msg = f"  FAIL  {label}" + (f" — {detail}" if detail else "")
        print(msg)
        failures.append(label)


# T01 — outputs/powerbi/ directory exists
check("T01  outputs/powerbi/ directory exists", os.path.isdir(PBI_DIR))

# T02 — fact_anomalies: 181 rows, 40 cols, no null anomaly_id
check(
    "T02  fact_anomalies: shape (181, 40), no null anomaly_id",
    fact.shape == (181, 40) and fact["anomaly_id"].notna().all(),
    f"shape={fact.shape}  nulls={fact['anomaly_id'].isna().sum()}",
)

# T03 — dim_kpi: 12 rows, covers all KPIs in fact_anomalies, no null kpi
check(
    "T03  dim_kpi: 12 rows, no null kpi",
    dim_kpi.shape[0] == 12 and dim_kpi["kpi"].notna().all(),
    f"rows={dim_kpi.shape[0]}  nulls={dim_kpi['kpi'].isna().sum()}",
)

# T04 — dim_date: 731 rows (2024-01-01 to 2025-12-31 inclusive)
check(
    "T04  dim_date: 731 rows (2024-01-01 to 2025-12-31)",
    dim_date.shape[0] == 731,
    f"got {dim_date.shape[0]} rows",
)

# T05 — dim_date: no duplicate dates
check(
    "T05  dim_date: no duplicate dates",
    dim_date["date"].nunique() == 731,
    f"unique={dim_date['date'].nunique()}",
)

# T06 — dim_date: all weekend dates (day_of_week_num >= 5) have is_weekend=True
weekends     = dim_date[dim_date["day_of_week_num"] >= 5]
non_weekends = dim_date[dim_date["day_of_week_num"] < 5]
check(
    "T06  dim_date: all Sat/Sun have is_weekend=True; all Mon-Fri have is_weekend=False",
    weekends["is_weekend"].all() and (~non_weekends["is_weekend"]).all(),
    f"weekend_flagged={weekends['is_weekend'].sum()}/{len(weekends)}  "
    f"weekday_flagged={non_weekends['is_weekend'].sum()}/{len(non_weekends)}",
)

# T07 — Referential integrity: all anomaly dates exist in dim_date
fact_dates  = set(fact["date"].dt.strftime("%Y-%m-%d") if hasattr(fact["date"], "dt")
                  else fact["date"])
dim_dates   = set(dim_date["date"])
orphan_dates = fact_dates - dim_dates
check(
    "T07  All anomaly dates exist in dim_date (referential integrity)",
    len(orphan_dates) == 0,
    f"orphaned dates: {orphan_dates}",
)

# T08 — Referential integrity: all KPIs in fact_anomalies exist in dim_kpi
fact_kpis  = set(fact["kpi"].unique())
dim_kpis   = set(dim_kpi["kpi"].unique())
orphan_kpis = fact_kpis - dim_kpis
check(
    "T08  All KPIs in fact_anomalies exist in dim_kpi (referential integrity)",
    len(orphan_kpis) == 0,
    f"orphaned KPIs: {orphan_kpis}",
)

# T09 — summary_timeline: total anomaly_count = 181
tl_total = int(summary_tl["anomaly_count"].sum())
check(
    "T09  summary_timeline: anomaly_count.sum() = 181",
    tl_total == 181,
    f"got {tl_total}",
)

# T10 — summary_kpi_impact revenue parity (within $0.10 of fact_anomalies totals)
fact_at_risk  = round(df[df["revenue_at_risk"] > 0]["revenue_at_risk"].sum(), 2)
summ_at_risk  = round(summary_kpi["revenue_at_risk_sum"].sum(), 2)
delta         = abs(fact_at_risk - summ_at_risk)
check(
    "T10  summary_kpi_impact revenue_at_risk_sum parity (delta < $0.10)",
    delta < 0.10,
    f"fact=${fact_at_risk:,.2f}  summary=${summ_at_risk:,.2f}  delta=${delta:.4f}",
)

# T11 — dim_date: starts 2024-01-01 and ends 2025-12-31
check(
    "T11  dim_date: starts 2024-01-01, ends 2025-12-31",
    dim_date.iloc[0]["date"] == "2024-01-01" and dim_date.iloc[-1]["date"] == "2025-12-31",
    f"first={dim_date.iloc[0]['date']}  last={dim_date.iloc[-1]['date']}",
)

print()
if failures:
    print(f"FAIL — {len(failures)} assertion(s) failed: {failures}")
    sys.exit(1)
print("All assertions passed — writing output files ...")
print()


# ── Write outputs ─────────────────────────────────────────────────────────────
outputs = {
    "fact_anomalies.csv":     (FACT_CSV,     fact),
    "dim_kpi.csv":            (DIM_KPI_CSV,  dim_kpi),
    "dim_date.csv":           (DIM_DATE_CSV, dim_date),
    "summary_kpi_impact.csv": (SUM_KPI_CSV,  summary_kpi),
    "summary_timeline.csv":   (SUM_TL_CSV,   summary_tl),
}

for name, (path, frame) in outputs.items():
    frame.to_csv(path, index=False)
    print(f"  {name:<28}  {frame.shape[0]:>4} rows x {frame.shape[1]:>2} cols  "
          f"({os.path.getsize(path):>8,} bytes)")

# Final check: all files exist and are non-empty
all_exist = all(os.path.isfile(p) and os.path.getsize(p) > 0 for _, (p, _) in outputs.items())
if not all_exist:
    print("FAIL — one or more output files missing or empty")
    sys.exit(1)


# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 68)
print("LAYER 5 STEP 5.5 — POWER BI DATA PREP SUMMARY")
print("=" * 68)

print(f"\nOutput directory: {PBI_DIR}")
print()
print(f"  {'File':<28}  {'Rows':>5}  {'Cols':>5}  Purpose")
print(f"  {'-'*27}  {'-'*5}  {'-'*5}  {'-'*30}")
print(f"  {'fact_anomalies.csv':<28}  {fact.shape[0]:>5}  {fact.shape[1]:>5}  Main fact table")
print(f"  {'dim_kpi.csv':<28}  {dim_kpi.shape[0]:>5}  {dim_kpi.shape[1]:>5}  KPI dimension")
print(f"  {'dim_date.csv':<28}  {dim_date.shape[0]:>5}  {dim_date.shape[1]:>5}  Calendar dimension (2024-2025)")
print(f"  {'summary_kpi_impact.csv':<28}  {summary_kpi.shape[0]:>5}  {summary_kpi.shape[1]:>5}  KPI x priority_band aggregation")
print(f"  {'summary_timeline.csv':<28}  {summary_tl.shape[0]:>5}  {summary_tl.shape[1]:>5}  Daily anomaly timeline")

print(f"\nfact_anomalies columns retained ({len(FACT_COLS)}):")
groups = [
    ("Identity",        ["anomaly_id", "date", "kpi"]),
    ("Detection",       ["tier", "severity", "direction", "deviation_pct", "z_score"]),
    ("Driver",          ["suspected_driver_kpi", "driver_direction"]),
    ("Root Cause",      ["root_cause_confidence", "confidence_tier", "is_externally_driven",
                         "external_driver_type", "actionability_score", "actionability_label",
                         "escalation_suppressed", "rca_narrative"]),
    ("Impact",          ["revenue_at_risk", "margin_impact", "customer_impact",
                         "monthly_shortfall", "impact_pct_of_plan", "impact_narrative"]),
    ("Priority",        ["priority_score", "priority_band", "priority_rank", "layer4_priority_flag"]),
    ("Recommendations", ["immediate_action", "short_term_fix", "recommended_owner",
                         "effort_level", "llm_enhanced"]),
    ("Communication",   ["urgency_label", "delivery_channel", "delivery_status",
                         "sent_at", "message_id", "recipient", "alert_subject"]),
]
for group, cols in groups:
    print(f"  {group:<16}  {', '.join(cols)}")

print(f"\ndim_kpi categories:")
for cat, grp in dim_kpi.groupby("kpi_category"):
    kpis = ", ".join(grp["kpi_label"].tolist())
    print(f"  {cat:<12}  {kpis}")

print(f"\nPower BI data model relationships:")
print("  fact_anomalies[date] -> dim_date[date]   (many-to-one)")
print("  fact_anomalies[kpi]  -> dim_kpi[kpi]     (many-to-one)")

print()
print("Step 5.5 complete — Power BI data prep files written to outputs/powerbi/.")
print("Ready for Step 5.6 (Power BI Dashboard build in Power BI Desktop).")
