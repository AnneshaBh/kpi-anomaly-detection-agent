# Update 2: Dimensional Decomposition for Root Cause Analysis

## 1. The Problem — Why Dimensional Analysis Is Missing

### 1.1 Root Cause of the Gap

The current pipeline makes a structural decision in **Step 1.1** (`1.1_build_master_dataset.py`): all raw transactional data is aggregated into **one row per date**, producing `master_dataset.csv` (731 rows × 33 columns). Every downstream step — detection, RCA, prioritization, communication — operates on this flat, dimensionless file.

The raw tables contain rich categorical breakdowns:

| Raw Table | Dimensional Columns Available | Rows |
|---|---|---|
| `customers.csv` | segment, country, age, cohort_month, is_loyalty_member | 10,000 |
| `orders.csv` | channel (acquisition), country, status | ~142,000 |
| `order_items.csv` | product_id (links to category, brand, premium flag) | ~370,000 |
| `products.csv` | category, brand, is_premium, gross_margin | 500 |
| `inventory_daily.csv` | product_id (links to category, brand) | 365,500 |
| `marketing_spend_daily.csv` | channel (paid_search, social, email, affiliate, display) | 3,655 |
| `website_traffic_daily.csv` | no sub-dimensions — single daily aggregate | 731 |

These columns are discarded during aggregation. By the time an anomaly is confirmed in Layer 2, the information about *which* country, segment, category, or channel contributed to it is gone.

### 1.2 Three Downstream Consequences

**Detection is dimensionless.** The ensemble (Z-score, Isolation Forest, Prophet) confirms that `total_revenue_usd` is down −36% on a given date. It cannot detect that Germany is down −80% while all other markets are flat, because Germany's revenue is never separated from the aggregate.

**RCA traverses the wrong graph first.** Step 3.1's dependency graph walks KPI-to-KPI relationships (e.g., `total_revenue_usd → n_orders → sessions`). This correctly identifies *which metric moved upstream*, but it skips the dimensional question that analysts check before the metric graph: *where in the business is this anomaly concentrated?*

**Recommendations are generic.** Step 4.3 produces advice like "shift budget from underperforming channels" — but it cannot name the channel, because no channel-level signal is in the pipeline. The direction is correct but the specificity needed to act is missing.

---

## 2. Why This Extension Makes Sense

In everyday business operations, a KPI anomaly triggers a two-stage diagnostic:

1. **Dimensional question first:** Which market, segment, category, or channel is driving this? (e.g., is Germany down or is this broad-based?)
2. **Metric question second:** Within that dimension, which upstream KPI explains the movement? (e.g., is Germany down because orders dropped or because AOV collapsed?)

The current pipeline answers only the second question. This update adds the first — without replacing or disrupting any existing logic.

The data to answer the dimensional question already exists in the raw files. The extension is not a new methodology; it is a recovery of information currently discarded in aggregation, applied using the same z-score framework already in place for Step 2.2A.

The extension is:
- **Additive:** no existing script logic changes; no existing output file changes schema
- **Backward-compatible:** anomalies with no applicable dimensions (web traffic KPIs) produce nulls and flow through unchanged
- **Methodologically consistent:** uses the same 7-day rolling z-score baseline already used in Method A

---

## 3. KPI-to-Dimension Applicability

### 3.1 Mapping Table

The following table defines which dimensions apply to each monitored KPI. Dimensions are determined by whether the underlying raw data can be grouped by that attribute without requiring new data collection.

| KPI | Customer: segment | Customer: country | Customer: age_group | Customer: loyalty | Customer: cohort | Product: category | Product: brand | Product: premium | Order channel | Marketing channel |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `total_revenue_usd` | yes | yes | yes | yes | yes | yes | yes | yes | yes | — |
| `n_orders` | yes | yes | yes | yes | yes | — | — | — | yes | — |
| `avg_order_value_usd` | yes | yes | — | yes | — | yes | yes | yes | yes | — |
| `n_unique_customers` | yes | yes | yes | yes | yes | — | — | — | yes | — |
| `n_returns` | yes | yes | — | yes | — | yes | yes | yes | yes | — |
| `return_rate` | yes | yes | — | yes | — | yes | yes | yes | yes | — |
| `avg_discount_pct` | — | — | — | — | — | yes | yes | yes | yes | — |
| `total_units_sold` | — | — | — | — | — | yes | yes | yes | — | — |
| `n_stockouts` | — | — | — | — | — | yes | yes | yes | — | — |
| `n_reorders` | — | — | — | — | — | yes | yes | yes | — | — |
| `total_stock_on_hand` | — | — | — | — | — | yes | yes | yes | — | — |
| `inventory_health` | — | — | — | — | — | yes | yes | yes | — | — |
| `avg_roas` | — | — | — | — | — | — | — | — | — | yes |
| `total_spend_usd` | — | — | — | — | — | — | — | — | — | yes |
| `total_clicks` | — | — | — | — | — | — | — | — | — | yes |
| `total_impressions` | — | — | — | — | — | — | — | — | — | yes |
| `total_conversions_marketing` | — | — | — | — | — | — | — | — | — | yes |
| `total_attributed_revenue_usd` | — | — | — | — | — | — | — | — | — | yes |
| `sessions` | no sub-dimensions | | | | | | | | | |
| `unique_visitors` | no sub-dimensions | | | | | | | | | |
| `bounce_rate` | no sub-dimensions | | | | | | | | | |
| `conversion_rate` | no sub-dimensions | | | | | | | | | |
| `avg_session_duration_sec` | no sub-dimensions | | | | | | | | | |
| `pages_per_session` | no sub-dimensions | | | | | | | | | |
| `conversions_web` | no sub-dimensions | | | | | | | | | |

Web traffic KPIs (`sessions`, `bounce_rate`, `conversion_rate`, etc.) have no sub-dimensional breakdown available — `website_traffic_daily.csv` is already a single daily aggregate with no grouping columns. This is a data limitation, not a design gap.

### 3.2 Dimension Definitions

| Dimension | Source column | Values | Notes |
|---|---|---|---|
| `segment` | `customers.segment` | new, regular, occasional, loyalty | Customer lifecycle stage |
| `country` | `orders.country` (denormalised from customers) | FR, US, DE, UK, etc. | Geography at order level |
| `age_group` | `customers.age` (binned) | 18–24, 25–34, 35–44, 45–54, 55+ | Age binned to protect individual identity |
| `is_loyalty_member` | `customers.is_loyalty_member` | 0, 1 | Binary loyalty flag |
| `cohort_year` | `customers.cohort_month` (year extracted) | 2022, 2023, 2024, etc. | Annual cohort bucket to avoid high cardinality |
| `category` | `products.category` | Toys, Books, Home, Apparel, Beauty, etc. | Product taxonomy |
| `brand` | `products.brand` | Brand_A through Brand_N | Supplier/brand line |
| `is_premium` | `products.is_premium` | 0, 1 | Premium product flag |
| `order_channel` | `orders.channel` | organic_search, paid_search, email, social, direct, affiliate, referral | Acquisition channel at order level — distinct from marketing channel |
| `marketing_channel` | `marketing_spend_daily.channel` | paid_search, social, email, affiliate, display | Spend channel from marketing ops |

---

## 4. How Each KPI Is Sliced — Join Paths and Aggregations

Five pre-computed dimensional datasets are built once at ingestion time. All five share the same long-format schema:

```
date | dimension_name | dimension_value | kpi_name | kpi_value
```

This single schema means the downstream scoring step uses one query pattern for all cases.

### 4.1 `dim_customer.csv` — Customer Attribute Slices

**Covers:** `total_revenue_usd`, `n_orders`, `avg_order_value_usd`, `n_unique_customers`, `n_returns`, `return_rate`, `avg_discount_pct`

**Join path:**
```
orders.csv
  └── JOIN customers.csv ON orders.customer_id = customers.customer_id
```

**Group by (one pass per dimension_name):**
- `(order_date, segment)`
- `(order_date, country)`
- `(order_date, age_group)` — age binned into 18–24, 25–34, 35–44, 45–54, 55+
- `(order_date, is_loyalty_member)`
- `(order_date, cohort_year)` — year extracted from cohort_month

**Aggregations per group:**

| Output kpi_name | Formula |
|---|---|
| `total_revenue_usd` | `SUM(orders.order_total_usd)` |
| `n_orders` | `COUNT(DISTINCT orders.order_id)` |
| `avg_order_value_usd` | `MEAN(orders.order_total_usd)` |
| `n_unique_customers` | `COUNT(DISTINCT orders.customer_id)` |
| `n_returns` | `COUNT(orders.order_id WHERE orders.status = 'returned')` |
| `return_rate` | `n_returns / n_orders` |
| `avg_discount_pct` | `MEAN(orders.discount_pct)` |

**Resulting rows (approximate):** 731 dates × 5 dimension_names × average 6 dimension_values = ~22,000 rows

### 4.2 `dim_product_orders.csv` — Product Attribute Slices on Order-Based KPIs

**Covers:** `total_revenue_usd`, `n_orders`, `return_rate`, `avg_discount_pct`, `avg_order_value_usd`

**Join path:**
```
order_items.csv
  └── JOIN orders.csv       ON order_items.order_id   = orders.order_id
  └── JOIN products.csv     ON order_items.product_id = products.product_id
```

Revenue is summed from `order_items.line_total_usd` (product-level), not `orders.order_total_usd`, so multi-product orders are correctly attributed.

**Group by:**
- `(orders.order_date, products.category)`
- `(orders.order_date, products.brand)`
- `(orders.order_date, products.is_premium)`

**Aggregations per group:**

| Output kpi_name | Formula |
|---|---|
| `total_revenue_usd` | `SUM(order_items.line_total_usd)` |
| `n_orders` | `COUNT(DISTINCT orders.order_id)` |
| `avg_order_value_usd` | `SUM(line_total_usd) / COUNT(DISTINCT order_id)` |
| `n_returns` | `COUNT(DISTINCT order_id WHERE orders.status = 'returned')` |
| `return_rate` | `n_returns / n_orders` |
| `avg_discount_pct` | `MEAN(order_items.discount_pct)` |

**Resulting rows (approximate):** 731 × 3 dimension_names × average 8 dimension_values = ~17,500 rows

### 4.3 `dim_product_inventory.csv` — Product Attribute Slices on Inventory KPIs

**Covers:** `total_stock_on_hand`, `total_units_sold`, `n_stockouts`, `n_reorders`, `inventory_health`

**Join path:**
```
inventory_daily.csv
  └── JOIN products.csv ON inventory_daily.product_id = products.product_id
```

**Group by:**
- `(inventory_daily.date, products.category)`
- `(inventory_daily.date, products.brand)`
- `(inventory_daily.date, products.is_premium)`

**Aggregations per group:**

| Output kpi_name | Formula |
|---|---|
| `total_stock_on_hand` | `SUM(inventory_daily.stock_on_hand)` |
| `total_units_sold` | `SUM(inventory_daily.units_sold)` |
| `n_stockouts` | `COUNT(product_id WHERE stockout_flag = 1)` |
| `n_reorders` | `COUNT(product_id WHERE reorder_triggered = 1)` |
| `inventory_health` | `1 - (n_stockouts / COUNT(product_id))` — proportion of SKUs not in stockout |

**Resulting rows (approximate):** 731 × 3 dimension_names × average 8 values = ~17,500 rows

### 4.4 `dim_order_channel.csv` — Acquisition Channel Slices

**Covers:** `total_revenue_usd`, `n_orders`, `avg_order_value_usd`, `n_unique_customers`, `n_returns`, `return_rate`, `avg_discount_pct`

**Source:** `orders.csv` — the `channel` column on each order (organic_search, paid_search, email, social, direct, affiliate, referral). This is the *acquisition channel* — the channel through which the customer arrived and placed the order. It is distinct from the marketing spend channel.

**Join path:** No join required — `orders.channel` is already on the orders table.

**Group by:** `(orders.order_date, orders.channel)`

**Aggregations:** Same as `dim_customer.csv` (same KPIs, same formulas, different grouping key).

**Resulting rows (approximate):** 731 × 7 channels = ~5,100 rows

### 4.5 `dim_marketing_channel.csv` — Marketing Spend Channel Slices

**Covers:** `avg_roas`, `total_spend_usd`, `total_impressions`, `total_clicks`, `total_conversions_marketing`, `total_attributed_revenue_usd`

**Source:** `marketing_spend_daily.csv` — already has a `channel` column (paid_search, social, email, affiliate, display). No join required.

**Group by:** `(date, channel)` — the file is already at this grain. No aggregation needed; each row is directly a dimension slice.

**Column rename map to master KPI names:**

| Raw column | kpi_name in output |
|---|---|
| `spend_usd` | `total_spend_usd` |
| `impressions` | `total_impressions` |
| `clicks` | `total_clicks` |
| `conversions` | `total_conversions_marketing` |
| `attributed_revenue_usd` | `total_attributed_revenue_usd` |
| `roas` | `avg_roas` |

**Resulting rows:** 731 × 5 channels = 3,655 rows (exact — this is the raw file itself, reshaped)

---

## 5. Step-by-Step Implementation Flow

The extension inserts two new scripts into the existing pipeline and makes additive modifications to two existing scripts. No existing script logic is removed or replaced.

```
[EXISTING]  1.1_build_master_dataset.py      → data/processed/master_dataset.csv
[EXISTING]  1.2_1.3_ingest_and_engineer.py   → data/processed/processed_kpi_features.csv
[NEW]       1.4_build_dimensional_datasets.py → data/processed/dimensional/*.csv
                ↓
[EXISTING]  2.1_KPI_Monitoring_Tiers.py
[EXISTING]  2.2A/B/C Statistical / IF / Prophet
[EXISTING]  2.3_Ensemble_Voting.py            → data/detection/anomaly_results.csv
[NEW]       2.4_dimensional_drill_down.py     → data/detection/dimensional_drill_down.csv
                ↓
[EXISTING]  3.1_dependency_graph.py           → data/rca/rca_graph_results.csv
[EXISTING]  3.2_causal_inference.py           → data/rca/rca_causal_results.csv
[EXISTING]  3.3_external_drivers.py           → data/rca/rca_results.csv
[MODIFIED]  3.4_rca_assembly.py               → data/rca/rca_assembly.csv  (45 → 53 cols)
                ↓
[EXISTING]  4.1_business_impact_quantification.py
[EXISTING]  4.2_prioritization_engine.py
[MODIFIED]  4.3_recommendation_engine.py      (dimension-aware template layer added)
                ↓
[EXISTING]  5.x communication scripts
[EXISTING]  6.x agent scripts
[MODIFIED]  Dashboard                         (dimensional drill-down panel added)
```

### Step 1 — Build Dimensional Datasets (`1.4_build_dimensional_datasets.py`)

**Position in pipeline:** After Step 1.3, before Step 2.1  
**Inputs:** All five raw files in `data/raw/`  
**Output directory:** `data/processed/dimensional/`  
**Output files:** `dim_customer.csv`, `dim_product_orders.csv`, `dim_product_inventory.csv`, `dim_order_channel.csv`, `dim_marketing_channel.csv`

This script performs all raw table joins and materialises the five dimensional datasets described in Section 4. It runs once and the outputs are consumed by Step 2.4. No re-joining at query time.

All five outputs share the long-format schema: `date | dimension_name | dimension_value | kpi_name | kpi_value`

The script also writes a metadata file (`dim_kpi_registry.json`) mapping each KPI name to the list of dimensional dataset files and dimension names that apply to it. This registry is consumed by Step 2.4 to determine which slices to query for any given anomaly, without hardcoding the mapping inside Step 2.4.

### Step 2 — Dimensional Anomaly Scoring (`2.4_dimensional_drill_down.py`)

**Position in pipeline:** After Step 2.3, before Step 3.1  
**Inputs:** `data/detection/anomaly_results.csv` + `data/processed/dimensional/*.csv` + `dim_kpi_registry.json`  
**Output:** `data/detection/dimensional_drill_down.csv` (one row per anomaly_id)

For each confirmed anomaly:

1. **Look up applicable dimensions** from `dim_kpi_registry.json` using the anomaly's `kpi` field. If the KPI is a web traffic KPI, write a null row and skip.

2. **Compute dimension-level baseline.** For each applicable `(dimension_name, dimension_value)` pair, take the 90-day pre-period window ending the day before the anomaly date. Compute:
   - `rolling_mean` — 7-day rolling mean of `kpi_value`
   - `rolling_std` — 7-day rolling std of `kpi_value`
   - `expected_value` — rolling_mean on the last day of the pre-period

3. **Compute anomaly signals on the anomaly date:**
   - `z_score = (actual_kpi_value - rolling_mean) / rolling_std`
   - `contribution_pct = (actual - expected) / ABS(aggregate_actual - aggregate_expected) × 100`
     This measures what share of the total aggregate deviation is explained by this specific slice.

4. **Rank across all dimension values and all dimension names** by `ABS(z_score)`. Retain the top 3 findings.

5. **Dimensional confirmation check.** After Step 3.1 identifies a `suspected_driver_kpi`, check whether the top-ranked dimension value (`dim_1_name = X`, `dim_1_value = Y`) is also anomalous in `suspected_driver_kpi` on the same date. If yes, set `dimensional_hypothesis_confirmed = True`. This is a read from Step 3.1 output — it does not alter the DAG or its traversal.

**Output columns:**

| Column | Description |
|---|---|
| `anomaly_id` | Join key to all other RCA outputs |
| `has_dimensional_breakdown` | False for web traffic KPIs, True otherwise |
| `n_dimensions_checked` | How many (dimension_name, dimension_value) pairs were evaluated |
| `dim_1_name` | Dimension name of top anomalous slice (e.g., `country`) |
| `dim_1_value` | Dimension value of top anomalous slice (e.g., `DE`) |
| `dim_1_z_score` | Z-score of that slice on the anomaly date |
| `dim_1_contribution_pct` | Share of total aggregate deviation from this slice |
| `dim_2_name`, `dim_2_value`, `dim_2_z_score`, `dim_2_contribution_pct` | Second-ranked slice |
| `dim_3_name`, `dim_3_value`, `dim_3_z_score`, `dim_3_contribution_pct` | Third-ranked slice |
| `dimensional_hypothesis_confirmed` | True if top slice is also anomalous in the suspected driver KPI |

### Step 3 — Update RCA Assembly (`3.4_rca_assembly.py`)

**Change type:** Additive modification — no existing logic removed  
**Change 1:** Add a fourth LEFT JOIN on `anomaly_id` against `dimensional_drill_down.csv` after the existing three-way merge (graph + causal + external).  
**Change 2:** Include the 8 new dimensional columns in the curated output column list. The existing 45 columns remain unchanged in position.  
**Change 3:** Update the `rca_narrative` template to append a dimensional sentence when `has_dimensional_breakdown = True` and `dim_1_z_score` is not null:

> `"Top dimensional contributor: {dim_1_name} = {dim_1_value} ({dim_1_contribution_pct:.0f}% of impact, z = {dim_1_z_score:.2f})."`

If `dimensional_hypothesis_confirmed = True`, append:

> `"Driver KPI {suspected_driver_kpi} also anomalous in the same slice — dimensional hypothesis confirmed."`

**Change 4:** Update shape validation test from 45 to 53 expected columns. All other existing quality tests remain unchanged because no existing column is modified.

**Output:** `data/rca/rca_assembly.csv` — same 181 rows, grows from 45 to 53 columns.

### Step 4 — Update Recommendation Engine (`4.3_recommendation_engine.py`)

**Change type:** Additive — dimension-aware template layer appended after existing rule-based recommendations

After the existing recommendation is generated, check if `dim_1_name` and `dim_1_value` are available. If yes, append a specific secondary recommendation using the following templates:

| Dimension | Template |
|---|---|
| `country` | "Investigate {country}-specific signals: local fulfillment delays, regional promotions, regulatory or currency changes contributing {pct}% of the {kpi} anomaly." |
| `segment` | "Review {segment} customer lifecycle — cohort activation, retention risk, or campaign targeting for this segment may explain the anomalous pattern." |
| `category` | "Audit {category} category: pricing, supplier lead times, inventory position, and shelf conversion for SKUs in this category." |
| `brand` | "Review {brand} brand performance: check markdown depth, stockout rates, and recent product launches or discontinuations." |
| `is_premium` | "Examine the split between premium and non-premium demand — a shift in mix may indicate macro sensitivity or price elasticity changes." |
| `order_channel` | "Diagnose the {channel} acquisition funnel: check traffic quality, landing page conversion, and any recent campaign or SEO changes for this channel." |
| `marketing_channel` | "Review {channel} campaign performance: bid strategy, audience saturation, creative fatigue, and attribution lag for this spend channel." |
| `is_loyalty_member` | "Loyalty member behaviour is diverging — check loyalty programme engagement, benefit redemption rates, and recent programme changes." |
| `cohort_year` | "The {cohort_year} customer cohort is driving the anomaly — examine retention curves and lifetime value trajectories for this acquisition vintage." |

### Step 5 — Dashboard Update

Add a **Dimensional Breakdown** panel to the anomaly detail view in the React dashboard.

- When `has_dimensional_breakdown = True`: render a ranked horizontal bar chart showing the top 3 dimension slices by `contribution_pct`, with z-score shown as a secondary label. Include a dimension selector dropdown to switch between all applicable dimensions for that anomaly.
- When `has_dimensional_breakdown = False` (web traffic KPIs): render a static message: `"No sub-dimensional data available for this KPI — website_traffic_daily.csv is a single daily aggregate."`
- When `dimensional_hypothesis_confirmed = True`: surface a confirmation badge alongside the suspected driver KPI in the existing RCA panel.

---

## 6. What Changes vs. What Stays the Same

| Component | Status | Detail |
|---|---|---|
| `1.1_build_master_dataset.py` | Unchanged | Aggregation logic untouched |
| `1.2_1.3_ingest_and_engineer.py` | Unchanged | Feature engineering untouched |
| `2.1` – `2.3` detection scripts | Unchanged | Ensemble detection untouched |
| `3.1_dependency_graph.py` | Unchanged | KPI DAG and traversal untouched |
| `3.2_causal_inference.py` | Unchanged | CausalImpact and DoWhy untouched |
| `3.3_external_drivers.py` | Unchanged | External attribution untouched |
| `anomaly_results.csv` | Unchanged | 181 rows, 25 columns — no change |
| `rca_graph_results.csv` | Unchanged | — |
| `rca_causal_results.csv` | Unchanged | — |
| `rca_results.csv` | Unchanged | — |
| **`1.4_build_dimensional_datasets.py`** | **New script** | Builds 5 pre-computed dimensional tables |
| **`2.4_dimensional_drill_down.py`** | **New script** | Dimensional z-scoring and ranking per anomaly |
| `3.4_rca_assembly.py` | **Modified** | +4th LEFT JOIN, +8 columns, updated narrative, updated shape test |
| `4.3_recommendation_engine.py` | **Modified** | Dimension-aware template layer appended |
| `rca_assembly.csv` | **Extended** | 45 → 53 columns; 181 rows unchanged |
| Dashboard | **Modified** | Dimensional breakdown panel added |

**Detection methodology:** unchanged — the ensemble (Z-score + Isolation Forest + Prophet) is not altered. Dimensional scoring in Step 2.4 is a diagnostic step that runs after anomalies are confirmed, not a new detection method.

**KPI DAG:** unchanged — the directed acyclic graph in Step 3.1 traverses KPI-to-KPI causal edges exactly as before. The dimensional decomposition runs in parallel on a separate analytical path and does not redirect, prune, or extend the DAG. The two paths merge only in Step 3.4.
