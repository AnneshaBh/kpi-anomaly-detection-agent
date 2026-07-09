# Positive Changes Incorrectly Flagged as Anomalies

## The Issue: Not All KPIs Point in the Same Direction

The anomaly detection engine treats every KPI the same way: any statistically significant deviation — up or down — is a candidate for an alert. This assumption is correct for some KPIs, but wrong for most.

In a retail e-commerce context, KPIs fall into two distinct groups:

**Standard KPIs** — positive change means growth:

| KPI | What a Positive Change Means |
|---|---|
| `total_revenue_usd` | More revenue — core business objective met |
| `n_orders` | Higher demand and sales volume |
| `avg_roas` | More efficient marketing spend |
| `conversion_rate` | More sessions converting to purchases |
| `avg_order_value_usd` | Customers spending more per order |
| `total_clicks` | More traffic reaching the site |
| `sessions` | Higher overall site traffic |
| `inventory_health` | Better stock availability and balance |
| `n_unique_customers` | Broader customer base |
| `total_impressions` | Greater ad reach and brand exposure |
| `total_conversions_marketing` | More marketing-attributed conversions |
| `total_attributed_revenue_usd` | More revenue traced to marketing investment |
| `unique_visitors` | More distinct people visiting the site |
| `pages_per_session` | Higher engagement per visit |
| `avg_session_duration_sec` | Visitors spending more time on site |
| `conversions_web` | More direct web purchase conversions |
| `total_stock_on_hand` | Larger inventory buffer, lower stockout risk |
| `total_units_sold` | Higher sell-through volume |
| `n_reorders` | Sustained demand being met via replenishment |

**Inverse KPIs** — positive change means decline:

| KPI | What a Positive Change Means |
|---|---|
| `return_rate` | More returns — signals quality or expectation issues |
| `n_returns` | Absolute return volume rising |
| `n_stockouts` | More lost-sale events — poor inventory planning |
| `bounce_rate` | More visitors leaving without engaging — poor UX or mismatched traffic |
| `avg_discount_pct` | Higher discounts — margin erosion, often signals coupon abuse or pricing errors |

---

## What This Causes: 108 False Alerts (59.3% of All Anomalies)

Because the engine has no knowledge of KPI direction semantics, it currently flags positive changes on standard KPIs as anomalies. Running against the full dataset of 182 confirmed anomalies:

| Category | Count | % of Total |
|---|---|---|
| UP on standard KPI — **incorrectly flagged** | **108** | **59.3%** |
| DOWN on standard KPI — correct alert | 45 | 24.7% |
| UP on inverse KPI — correct alert | 22 | 12.1% |
| DOWN on inverse KPI — incorrectly flagged | 4 | 2.2% |

Only **67 of 182 anomalies (36.8%) are directionally valid alerts**. The system is generating more noise than signal.

The 108 false alerts break down by KPI as follows:

| KPI | False Alerts |
|---|---|
| `avg_roas` | 47 |
| `inventory_health` | 14 |
| `total_clicks` | 13 |
| `total_revenue_usd` | 9 |
| `n_orders` | 8 |
| `sessions` | 6 |
| `conversion_rate` | 6 |
| `avg_order_value_usd` | 5 |

`avg_roas` alone accounts for 47 false alerts — more than all legitimate alerts for Tier 2 and Tier 3 KPIs combined. An improving ROAS is marketing efficiency working as intended; it should never generate an alert.

This also explains why Black Friday revenue spikes were flagged as anomalies. A revenue spike on Black Friday is a large positive deviation on a standard KPI — the engine has no mechanism to recognise this as expected growth rather than an operational problem.

---

## How to Fix It: `positive_is_good` Flag + Direction-Aware Suppression

### Step 1 — Encode direction semantics per KPI

Add a `positive_is_good` boolean field to each KPI entry in `data/config/tier_config.json`. Standard KPIs get `true`; inverse KPIs get `false`.

```json
"total_revenue_usd": { "positive_is_good": true },
"avg_roas":          { "positive_is_good": true },
"return_rate":       { "positive_is_good": false },
"n_stockouts":       { "positive_is_good": false },
"bounce_rate":       { "positive_is_good": false },
"avg_discount_pct":  { "positive_is_good": false }
```

This becomes the single source of truth referenced by all downstream steps.

### Step 2 — Suppress directionally invalid anomalies at the ensemble stage

In `scripts/detection/2.3_Ensemble_Voting.py`, after the vote count confirms an anomaly, add a direction check before writing the result:

- If `positive_is_good = true` and `direction = UP` → suppress (not an alert)
- If `positive_is_good = false` and `direction = DOWN` → suppress (not an alert)

Anomalies suppressed at this stage should be written to the output with a `suppression_reason = "directionally_invalid"` column so the data is retained for audit purposes, but they are not escalated.

### Step 3 — Propagate the flag into the RCA and external drivers steps

`scripts/rca/3.3_external_drivers.py` already has a directional guard for suppression (the `direction == "DOWN"` condition on line 205). Replacing this hardcoded `"DOWN"` check with a lookup against `positive_is_good` makes the logic generalise correctly to all KPIs rather than relying on an implicit assumption about direction.

### Expected outcome after the fix

Applying direction-aware suppression would reduce confirmed anomalies from 182 to approximately **67** — eliminating the 108 false positive UP alerts and the 4 false positive DOWN alerts on inverse KPIs. All remaining alerts would represent genuine, actionable deviations: declines in standard KPIs and increases in inverse KPIs.
