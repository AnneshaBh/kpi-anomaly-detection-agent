"""
Layer 4, Step 4.1 — Business Impact Quantification
Translates each confirmed anomaly into a dollar-denominated revenue impact,
gross margin impact, and estimated customer count affected.

Input  : data/rca_assembly.csv        (181 × 46)
Output : data/impact_results.csv      (181 × 52)
         SQLite table: impact_results
"""

import os
import sqlite3

import numpy as np
import pandas as pd

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR   = os.path.join(BASE_DIR, "data")
DB_PATH    = os.path.join(DATA_DIR, "db", "kpi_anomaly_detection.db")
INPUT_CSV  = os.path.join(DATA_DIR, "rca", "rca_assembly.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "intelligence", "impact_results.csv")

# ─── Tuning constants ─────────────────────────────────────────────────────────
FORWARD_DAYS        = 7     # days of projected exposure in revenue_at_risk
MONTHLY_DAYS        = 30    # annualisation window for monthly_shortfall
ROAS_REVENUE_SHARE  = 0.30  # fraction of total revenue attributable to paid marketing
TIER3_DECAY         = 0.15  # fractional revenue sensitivity for operational Tier 3 KPIs


# ─── Load source data ─────────────────────────────────────────────────────────
print("Loading input data …")
rca     = pd.read_csv(INPUT_CSV, parse_dates=["date"])
master  = pd.read_csv(os.path.join(DATA_DIR, "processed", "master_dataset.csv"))
products = pd.read_csv(os.path.join(DATA_DIR, "raw", "products.csv"))

assert rca.shape[0] > 0 and rca.shape[1] == 46, f"Expected 46 cols, got {rca.shape}"


# ─── Derived baselines (period averages from master_dataset) ──────────────────
AVG_DAILY_REVENUE   = master["total_revenue_usd"].mean()
AVG_AOV             = master["avg_order_value_usd"].mean()
AVG_DAILY_ORDERS    = master["n_orders"].mean()
AVG_DAILY_SESSIONS  = master["sessions"].mean()
AVG_DAILY_CLICKS    = master["total_clicks"].mean()
AVG_CONVERSION_RATE = master["conversion_rate"].mean()
CUSTOMERS_PER_ORDER = master["n_unique_customers"].mean() / master["n_orders"].mean()
AVG_GROSS_MARGIN    = products["gross_margin"].mean()
N_PRODUCTS          = len(products)
AVG_REVENUE_PER_SKU = AVG_DAILY_REVENUE / N_PRODUCTS

print(f"  avg daily revenue   : ${AVG_DAILY_REVENUE:>10,.2f}")
print(f"  avg AOV             : ${AVG_AOV:>10,.2f}")
print(f"  avg daily orders    : {AVG_DAILY_ORDERS:>10,.1f}")
print(f"  avg daily sessions  : {AVG_DAILY_SESSIONS:>10,.1f}")
print(f"  avg conversion rate : {AVG_CONVERSION_RATE:>10.4f}")
print(f"  avg gross margin    : {AVG_GROSS_MARGIN:>10.4f}")
print(f"  customers / order   : {CUSTOMERS_PER_ORDER:>10.4f}")
print()


# ─── Revenue at risk ──────────────────────────────────────────────────────────
# Sign convention:
#   positive  →  money at risk (anomaly is hurting the business)
#   negative  →  captured upside (anomaly represents unexpected gain)
#
# For "higher is better" KPIs: risk = (expected − actual) × multiplier × FORWARD_DAYS
# For "lower is better" KPIs:  risk = (actual − expected) × multiplier × FORWARD_DAYS
# Both expressions are positive when the KPI moved in the harmful direction.

def compute_revenue_at_risk(row: pd.Series) -> float:
    kpi      = row["kpi"]
    actual   = row["actual_value"]
    expected = row["expected_value"]
    dev_frac = row["deviation_pct"] / 100.0 if pd.notna(row["deviation_pct"]) else 0.0

    if kpi == "total_revenue_usd":
        return (expected - actual) * FORWARD_DAYS

    if kpi == "n_orders":
        return (expected - actual) * AVG_AOV * FORWARD_DAYS

    if kpi == "avg_order_value_usd":
        return (expected - actual) * AVG_DAILY_ORDERS * FORWARD_DAYS

    if kpi == "avg_roas":
        # ROAS is an attribution ratio, not a revenue figure; using spend as a
        # direct multiplier inflates results due to multi-touch overcounting.
        # Scale by deviation fraction × conservative marketing revenue share instead.
        return -dev_frac * AVG_DAILY_REVENUE * ROAS_REVENUE_SHARE * FORWARD_DAYS

    if kpi == "conversion_rate":
        return (expected - actual) * AVG_DAILY_SESSIONS * AVG_AOV * FORWARD_DAYS

    if kpi == "return_rate":
        # Higher return rate → more revenue refunded back to customers.
        return (actual - expected) * AVG_DAILY_ORDERS * AVG_AOV * FORWARD_DAYS

    if kpi == "n_stockouts":
        # Each incremental stockout makes one SKU unavailable; lost revenue
        # is proxied by average daily revenue per SKU.
        return (actual - expected) * AVG_REVENUE_PER_SKU * FORWARD_DAYS

    if kpi == "bounce_rate":
        # Higher bounce rate → fewer sessions that could convert.
        return (actual - expected) * AVG_DAILY_SESSIONS * AVG_CONVERSION_RATE * AVG_AOV * FORWARD_DAYS

    if kpi == "sessions":
        return (expected - actual) * AVG_CONVERSION_RATE * AVG_AOV * FORWARD_DAYS

    if kpi == "total_clicks":
        revenue_per_click = AVG_DAILY_REVENUE / AVG_DAILY_CLICKS
        return (expected - actual) * revenue_per_click * FORWARD_DAYS

    if kpi == "avg_discount_pct":
        # Excess discounting erodes effective revenue; rate is expressed as a
        # fraction (0.10 = 10%) so the delta is also fractional.
        return (actual - expected) * AVG_DAILY_REVENUE * FORWARD_DAYS

    if kpi == "inventory_health":
        # Composite operational score; revenue sensitivity is indirect —
        # dampen with TIER3_DECAY to prevent overstating impact.
        return -dev_frac * AVG_DAILY_REVENUE * TIER3_DECAY * FORWARD_DAYS

    # Fallback for any unexpected KPI
    return -dev_frac * AVG_DAILY_REVENUE * TIER3_DECAY * FORWARD_DAYS


# ─── Customer impact ──────────────────────────────────────────────────────────
# Uniform formula: translate revenue_at_risk to implied order count via AOV,
# then apply customers-per-order ratio.  Gives a consistent, comparable
# "affected customers" number across all KPI types.

def compute_customer_impact(revenue_at_risk: float) -> int:
    implied_orders    = abs(revenue_at_risk) / AVG_AOV
    customer_estimate = implied_orders * CUSTOMERS_PER_ORDER
    return max(1, int(round(customer_estimate)))


# ─── Impact narrative ─────────────────────────────────────────────────────────

KPI_LABELS = {
    "total_revenue_usd"  : "Revenue",
    "n_orders"           : "Order volume",
    "avg_order_value_usd": "Average order value",
    "avg_roas"           : "Marketing ROAS",
    "conversion_rate"    : "Conversion rate",
    "return_rate"        : "Return rate",
    "n_stockouts"        : "Stockout count",
    "bounce_rate"        : "Bounce rate",
    "sessions"           : "Web sessions",
    "total_clicks"       : "Ad clicks",
    "avg_discount_pct"   : "Average discount rate",
    "inventory_health"   : "Inventory health score",
}

def build_impact_narrative(row: pd.Series, revenue_at_risk: float,
                           monthly_shortfall: float, impact_pct_of_plan: float,
                           customer_impact: int) -> str:
    kpi        = row["kpi"]
    dev_pct    = row["deviation_pct"] if pd.notna(row["deviation_pct"]) else 0.0
    direction  = row["direction"] if pd.notna(row["direction"]) else "N/A"
    label      = KPI_LABELS.get(kpi, kpi)
    risk_abs   = abs(revenue_at_risk)
    month_abs  = abs(monthly_shortfall)
    pct_abs    = abs(impact_pct_of_plan)

    if revenue_at_risk > 0:
        # Anomaly is hurting the business
        return (
            f"{label} is tracking ${risk_abs:,.0f} below forecast for the week. "
            f"At current trajectory, this represents a ${month_abs:,.0f} monthly shortfall — "
            f"{pct_abs:.1f}% below plan. "
            f"Approximately {customer_impact:,} customers experienced degraded {label.lower()}."
        )
    else:
        # Anomaly is an unexpected uplift
        return (
            f"{label} surged {dev_pct:+.1f}% above forecast. "
            f"Weekly revenue uplift: +${risk_abs:,.0f} (+${month_abs:,.0f} monthly, "
            f"{pct_abs:.1f}% above plan). "
            f"Approximately {customer_impact:,} customers contributed to the uplift."
        )


# ─── Compute impact for all 181 rows ─────────────────────────────────────────
print("Computing impact metrics …")

revenue_at_risk_vals    = rca.apply(compute_revenue_at_risk, axis=1)
margin_impact_vals      = revenue_at_risk_vals * AVG_GROSS_MARGIN
customer_impact_vals    = revenue_at_risk_vals.apply(compute_customer_impact)
monthly_shortfall_vals  = revenue_at_risk_vals * (MONTHLY_DAYS / FORWARD_DAYS)
impact_pct_of_plan_vals = (
    revenue_at_risk_vals / FORWARD_DAYS / AVG_DAILY_REVENUE * 100
)

narrative_vals = pd.Series([
    build_impact_narrative(
        row,
        revenue_at_risk_vals.iloc[i],
        monthly_shortfall_vals.iloc[i],
        impact_pct_of_plan_vals.iloc[i],
        customer_impact_vals.iloc[i],
    )
    for i, row in rca.iterrows()
])

# ─── Assemble output ──────────────────────────────────────────────────────────
impact = rca.copy()
impact["revenue_at_risk"]    = revenue_at_risk_vals.round(2)
impact["margin_impact"]      = margin_impact_vals.round(2)
impact["customer_impact"]    = customer_impact_vals
impact["monthly_shortfall"]  = monthly_shortfall_vals.round(2)
impact["impact_pct_of_plan"] = impact_pct_of_plan_vals.round(4)
impact["impact_narrative"]   = narrative_vals

assert impact.shape[0] > 0 and impact.shape[1] == 52, f"Expected 52 cols, got {impact.shape}"

# ─── Write outputs ────────────────────────────────────────────────────────────
print("Writing outputs …")
impact.to_csv(OUTPUT_CSV, index=False)

conn = sqlite3.connect(DB_PATH)
impact.to_sql("impact_results", conn, if_exists="replace", index=False)
conn.close()

print(f"  Saved {OUTPUT_CSV}")
print(f"  Saved SQLite table: impact_results")
print()


# ─── Summary ──────────────────────────────────────────────────────────────────
print("=" * 68)
print("IMPACT SUMMARY")
print("=" * 68)

# Revenue at risk by priority flag
print("\nRevenue at risk by Layer 4 priority flag:")
summary = (
    impact.groupby("layer4_priority_flag")["revenue_at_risk"]
    .agg(count="count", total="sum", mean="mean")
    .sort_values("total", ascending=False)
)
for flag, row in summary.iterrows():
    print(f"  {flag:<12}  n={int(row['count']):>3}  "
          f"total=${row['total']:>12,.0f}  "
          f"mean=${row['mean']:>9,.0f}")

# Top 5 by absolute revenue at risk
print("\nTop 5 anomalies by absolute revenue at risk:")
top5 = (
    impact[["anomaly_id", "kpi", "severity", "direction",
            "deviation_pct", "revenue_at_risk", "customer_impact"]]
    .assign(abs_risk=impact["revenue_at_risk"].abs())
    .nlargest(5, "abs_risk")
    .drop(columns="abs_risk")
)
for _, r in top5.iterrows():
    print(f"  {r['anomaly_id']:<22}  {r['kpi']:<22}  "
          f"dev={r['deviation_pct']:>+8.1f}%  "
          f"risk=${r['revenue_at_risk']:>10,.0f}  "
          f"customers={int(r['customer_impact']):>5,}")

# Distribution of revenue at risk direction
at_risk     = (impact["revenue_at_risk"] > 0).sum()
upside      = (impact["revenue_at_risk"] < 0).sum()
zero_impact = (impact["revenue_at_risk"] == 0).sum()
print(f"\nDirection breakdown (181 total):")
print(f"  Revenue at risk (positive): {at_risk}")
print(f"  Captured upside (negative): {upside}")
print(f"  Zero / neutral            : {zero_impact}")

# Aggregate exposure
total_risk   = impact.loc[impact["revenue_at_risk"] > 0, "revenue_at_risk"].sum()
total_upside = impact.loc[impact["revenue_at_risk"] < 0, "revenue_at_risk"].sum()
total_margin = impact["margin_impact"].sum()
print(f"\nAggregate 7-day exposure:")
print(f"  Total revenue at risk  : ${total_risk:>12,.0f}")
print(f"  Total captured upside  : ${total_upside:>12,.0f}")
print(f"  Net margin impact      : ${total_margin:>12,.0f}")

# Spot checks
bf = impact[(impact["date"] == "2024-11-29") & (impact["kpi"] == "total_revenue_usd")].iloc[0]
sk = impact[(impact["date"] == "2024-03-15") & (impact["kpi"] == "n_orders")].iloc[0]
print(f"\nSpot checks:")
print(f"  Black Friday revenue   : revenue_at_risk=${bf['revenue_at_risk']:>10,.0f}  "
      f"(expect negative — captured upside)")
print(f"  Inventory stockout     : revenue_at_risk=${sk['revenue_at_risk']:>10,.0f}  "
      f"(expect positive — at risk)")

print()
print("Step 4.1 complete — impact_results.csv written (181 rows × 52 cols).")
