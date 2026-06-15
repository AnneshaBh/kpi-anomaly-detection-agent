"""
Layer 5, Step 5.5 — Dashboard Data Preparation

Reads data/communication_results.csv (181 × 78) and writes the star-schema
CSVs consumed by the React dashboard.

Outputs → outputs/dashboard/
  fact_anomalies.csv      181 rows × 40 cols
  dim_kpi.csv              12 rows ×  5 cols
  dim_date.csv            731 rows × 13 cols
  summary_kpi_impact.csv   ~17 rows ×  9 cols
  summary_timeline.csv     ~68 rows × 10 cols
"""

import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUT_DIR  = BASE_DIR / "outputs" / "dashboard"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Load ───────────────────────────────────────────────────────────────────────
print("Loading communication_results.csv ...")
src = pd.read_csv(DATA_DIR / "communication_results.csv", parse_dates=["date"])
assert src.shape[0] == 181, f"Expected 181 rows, got {src.shape[0]}"
print(f"  Loaded {src.shape[0]} rows × {src.shape[1]} cols")


# ── 1. fact_anomalies ──────────────────────────────────────────────────────────
FACT_COLS = [
    "anomaly_id", "date", "kpi", "tier", "severity", "direction",
    "deviation_pct", "z_score", "suspected_driver_kpi", "driver_direction",
    "root_cause_confidence", "confidence_tier", "is_externally_driven",
    "external_driver_type", "actionability_score", "actionability_label",
    "escalation_suppressed", "rca_narrative", "revenue_at_risk", "margin_impact",
    "customer_impact", "monthly_shortfall", "impact_pct_of_plan", "impact_narrative",
    "priority_score", "priority_band", "priority_rank", "layer4_priority_flag",
    "immediate_action", "short_term_fix", "recommended_owner", "effort_level",
    "llm_enhanced", "urgency_label", "delivery_channel", "delivery_status",
    "sent_at", "message_id", "recipient", "alert_subject",
]
missing = [c for c in FACT_COLS if c not in src.columns]
if missing:
    print(f"  WARNING: missing columns {missing} — filling with None")
    for c in missing:
        src[c] = None

fact = src[FACT_COLS].copy()
fact["date"] = fact["date"].astype(str)
fact.to_csv(OUT_DIR / "fact_anomalies.csv", index=False)
print(f"  fact_anomalies.csv:     {fact.shape}")


# ── 2. dim_kpi ─────────────────────────────────────────────────────────────────
KPI_META = {
    "conversion_rate":           ("Conversion Rate",       1, "Acquisition",   "Percentage of visitors who complete a purchase"),
    "avg_order_value":           ("Avg Order Value",        1, "Revenue",       "Mean transaction value across all orders"),
    "revenue_per_visitor":       ("Revenue per Visitor",    1, "Revenue",       "Total revenue divided by unique site visitors"),
    "cart_abandonment_rate":     ("Cart Abandonment Rate",  1, "Acquisition",   "Share of initiated carts not completed"),
    "gross_margin_pct":          ("Gross Margin %",         2, "Profitability", "Profit retained after COGS as a percentage of revenue"),
    "avg_roas":                  ("Avg ROAS",               2, "Marketing",     "Revenue generated per dollar of ad spend"),
    "customer_acquisition_cost": ("CAC",                    2, "Marketing",     "Total marketing spend divided by new customers acquired"),
    "inventory_turnover":        ("Inventory Turnover",     2, "Operations",    "How many times inventory sells and is restocked per period"),
    "return_rate":               ("Return Rate",            3, "Customer",      "Percentage of items returned by customers"),
    "repeat_purchase_rate":      ("Repeat Purchase Rate",   3, "Customer",      "Share of customers who buy more than once"),
    "customer_lifetime_value":   ("CLV",                    3, "Customer",      "Projected net profit from a customer relationship"),
    "nps_score":                 ("NPS Score",              3, "Customer",      "Net Promoter Score measuring customer loyalty"),
}
dim_kpi = pd.DataFrame([
    {"kpi": k, "kpi_label": v[0], "tier": v[1], "kpi_category": v[2], "description": v[3]}
    for k, v in KPI_META.items()
])
dim_kpi.to_csv(OUT_DIR / "dim_kpi.csv", index=False)
print(f"  dim_kpi.csv:            {dim_kpi.shape}")


# ── 3. dim_date ────────────────────────────────────────────────────────────────
dates = pd.date_range("2024-01-01", "2025-12-31", freq="D")
dim_date = pd.DataFrame({
    "date":             dates.strftime("%Y-%m-%d"),
    "year":             dates.year,
    "quarter_num":      dates.quarter,
    "quarter_label":    "Q" + dates.quarter.astype(str) + " " + dates.year.astype(str),
    "month_num":        dates.month,
    "month_name":       dates.strftime("%B"),
    "month_label":      dates.strftime("%b %Y"),
    "week_num":         dates.isocalendar().week.astype(int).values,
    "day_of_week":      dates.strftime("%A"),
    "is_weekend":       dates.dayofweek >= 5,
    "is_month_start":   dates.is_month_start,
    "is_quarter_start": dates.is_quarter_start,
    "day_of_year":      dates.dayofyear,
})
dim_date.to_csv(OUT_DIR / "dim_date.csv", index=False)
print(f"  dim_date.csv:           {dim_date.shape}")


# ── 4. summary_kpi_impact ──────────────────────────────────────────────────────
kpi_label_map = dim_kpi.set_index("kpi")["kpi_label"]

grp = fact.groupby(["kpi", "priority_band"])
s = grp.agg(
    anomaly_count       = ("anomaly_id",          "count"),
    revenue_at_risk_sum = ("revenue_at_risk",      "sum"),
    avg_priority_score  = ("priority_score",       "mean"),
    avg_deviation_pct   = ("deviation_pct",        "mean"),
).reset_index()

suppressed_avg = (
    fact[fact["escalation_suppressed"].astype(str).str.lower() == "true"]
    .groupby(["kpi", "priority_band"])["revenue_at_risk"]
    .mean()
    .reset_index()
    .rename(columns={"revenue_at_risk": "upside_sum"})
)
s = s.merge(suppressed_avg, on=["kpi", "priority_band"], how="left")
s["upside_sum"] = s["upside_sum"].fillna(0)
s["kpi_label"]  = s["kpi"].map(kpi_label_map)

total_rev = s["revenue_at_risk_sum"].sum()
s["revenue_pct_of_total"] = (s["revenue_at_risk_sum"] / total_rev * 100).round(2)

summary_kpi_impact = s[[
    "kpi", "kpi_label", "priority_band", "anomaly_count",
    "revenue_at_risk_sum", "upside_sum", "avg_priority_score",
    "avg_deviation_pct", "revenue_pct_of_total",
]]
summary_kpi_impact.to_csv(OUT_DIR / "summary_kpi_impact.csv", index=False)
print(f"  summary_kpi_impact.csv: {summary_kpi_impact.shape}")


# ── 5. summary_timeline ────────────────────────────────────────────────────────
fact_t = fact.copy()
fact_t["escalation_suppressed"] = fact_t["escalation_suppressed"].astype(str).str.lower() == "true"

summary_timeline = (
    fact_t.groupby("date")
    .agg(
        anomaly_count     = ("anomaly_id",            "count"),
        escalate_count    = ("layer4_priority_flag",  lambda x: (x == "ESCALATE").sum()),
        investigate_count = ("layer4_priority_flag",  lambda x: (x == "INVESTIGATE").sum()),
        monitor_count     = ("layer4_priority_flag",  lambda x: (x == "MONITOR").sum()),
        suppressed_count  = ("escalation_suppressed", "sum"),
        revenue_at_risk   = ("revenue_at_risk",       "sum"),
        high_count        = ("severity",              lambda x: (x == "HIGH").sum()),
        medium_count      = ("severity",              lambda x: (x == "MEDIUM").sum()),
        low_count         = ("severity",              lambda x: (x == "LOW").sum()),
    )
    .reset_index()
)
summary_timeline["suppressed_count"] = summary_timeline["suppressed_count"].astype(int)
summary_timeline.to_csv(OUT_DIR / "summary_timeline.csv", index=False)
print(f"  summary_timeline.csv:   {summary_timeline.shape}")


# ── Quality checks ─────────────────────────────────────────────────────────────
print("\nQuality checks ...")
failures = []

def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {label}")
    else:
        msg = f"  FAIL  {label}" + (f" — {detail}" if detail else "")
        print(msg)
        failures.append(label)

check("fact_anomalies rows == 181",    fact.shape[0] == 181,               str(fact.shape))
check("fact_anomalies cols == 40",     fact.shape[1] == 40,                str(fact.shape))
check("dim_kpi rows == 12",            dim_kpi.shape[0] == 12,             str(dim_kpi.shape))
check("dim_date rows == 731",          dim_date.shape[0] == 731,           str(dim_date.shape))
check("summary_timeline no nulls",     summary_timeline.isnull().sum().sum() == 0,
      str(summary_timeline.isnull().sum().to_dict()))
check("all fact KPIs in dim_kpi",      set(fact["kpi"].unique()).issubset(set(dim_kpi["kpi"])),
      str(set(fact["kpi"].unique()) - set(dim_kpi["kpi"])))

if failures:
    print(f"\n{len(failures)} check(s) failed — see above.")
    sys.exit(1)

print(f"\nAll checks passed. CSVs written to {OUT_DIR}")
