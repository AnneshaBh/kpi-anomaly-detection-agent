# Update 2 — Dimensional Decomposition

## Problem

Root Cause Analysis was operating entirely on aggregate KPI values. The daily `master_dataset.csv` collapses every raw table into a single row per date — discarding all categorical columns (country, segment, channel, category, brand, age group, loyalty status, product tier) in the aggregation step. When an anomaly was detected, the pipeline had no way to answer "which customer segment drove this?" or "which product category is the outlier?" — it could only say the aggregate metric was anomalous.

See [dimensional_decomposition.md](dimensional_decomposition.md) for the full analysis: why the gap exists structurally, the KPI-to-dimension applicability matrix across all 25 KPIs, and the step-by-step implementation plan.

---

## Bug Fix Also Delivered: Direction Filter Now Active

The direction-aware suppression from Update 1 had already been coded into `2.3_Ensemble_Voting.py`, but the output file `anomaly_results.csv` had never been regenerated after the code was added. The file therefore still contained all 182 pre-filter anomalies. As part of this update the file was re-run and the direction filter is now active in the live output.

**Blocker encountered:** `2.3_Ensemble_Voting.py` had two layers of encoding corruption that prevented it from parsing:

1. The docstring delimiter `"""` had been written with Unicode left/right double quotation marks (`\xe2\x80\x9c` / `\xe2\x80\x9d`), causing a `SyntaxError` at the first docstring.
2. Em-dash characters in string literals had been double-encoded (Windows-1252 bytes re-encoded as UTF-8, producing `\xc3\xa2\xe2\x82\xac`). When the first fix replaced `\xe2\x80\x9d` bytes with ASCII `"`, it accidentally terminated these string literals early, creating a second class of `SyntaxError`.

Both were resolved by a binary-level byte replacement pass followed by targeted line edits for the three split f-string literals (`lines 320–323, 361, 432, 496`). All other content (box-drawing characters in comments, the UTF-8 BOM) was also cleaned to ASCII.

**After re-run:**

| | Before | After |
|---|---|---|
| Vote-confirmed anomalies | 182 | 182 |
| Direction-suppressed | 0 (filter not applied) | 112 |
| Final confirmed anomalies | 182 | **70** |
| Signal-to-noise | 36.8% valid | **100% valid** |

---

## Changes

### 1. `scripts/processed/1.4_build_dimensional_datasets.py` — NEW

Builds five pre-computed dimensional datasets from the raw source tables, all written in a unified long-format schema so Step 2.4 uses one query pattern for every KPI.

**Output schema** (all five files share this):

```
date | dimension_name | dimension_value | kpi_name | kpi_value
```

**Datasets built:**

| Output file | Source join | Dimensions | KPIs |
|---|---|---|---|
| `dim_customer.csv` | `orders → customers` | segment, country, age_group, loyalty_status, cohort_year | 7 order KPIs |
| `dim_product_orders.csv` | `order_items → orders → products` | category, brand, product_tier | 6 order KPIs |
| `dim_product_inventory.csv` | `inventory_daily → products` | category, brand, product_tier | 5 inventory KPIs |
| `dim_order_channel.csv` | `orders` grouped by channel | order_channel | 6 order KPIs |
| `dim_marketing_channel.csv` | `marketing_spend_daily` grouped by channel | marketing_channel | 6 marketing KPIs |

Also writes `dim_kpi_registry.json` — a JSON map of `kpi_name → [{file, dimension_names}]` that tells Step 2.4 which dimensional files and dimension names apply to each of the 25 KPIs. Web-traffic KPIs (`sessions`, `bounce_rate`, `conversion_rate`, etc.) map to an empty list.

**Key design decisions:**

- `age_group` binned from raw `age` column: 18-24, 25-34, 35-44, 45-54, 55+
- `cohort_year` extracted from `cohort_month` (year only, to keep cardinality manageable)
- `loyalty_status` mapped from `is_loyalty_member` binary (0 → `non_loyalty`, 1 → `loyalty`)
- `product_tier` mapped from `is_premium` binary (0 → `standard`, 1 → `premium`)
- `inventory_health = 1 - (n_stockouts / n_skus)` computed at dimension level before converting to long format
- `dim_product_orders` uses `order_items.line_total_usd` for revenue (correct item-level grain) rather than `orders.order_total_usd`, and uses a separate groupby for `n_returns` to avoid double-counting returned items across multiple order-item rows
- `order_channel` renamed from `orders.channel` to distinguish from `marketing_channel`

**Core helper — `_wide_to_long(df, dim_col, kpi_cols)`:**

Takes a grouped-wide DataFrame `[date, dim_col, kpi_1, kpi_2, ...]` and melts it into the long-format schema. All five build functions call this before concatenating their per-dimension frames.

**Outputs after run:**

| File | Rows |
|---|---|
| `dim_customer.csv` | 117,649 |
| `dim_product_orders.csv` | 131,580 |
| `dim_product_inventory.csv` | 109,650 |
| `dim_order_channel.csv` | 35,819 |
| `dim_marketing_channel.csv` | 21,930 |

All five files pass validation (reconciliation delta = 0.00 vs. aggregate totals in `master_dataset.csv`).

---

### 2. `scripts/detection/2.4_dimensional_drill_down.py` — NEW

Scores every confirmed anomaly against the pre-computed dimensional data to identify which dimensional slice is the largest contributor to the aggregate KPI deviation.

**Algorithm per anomaly:**

1. Look up applicable dimensional files from `dim_kpi_registry.json`. If the KPI has no applicable dimensions (web-traffic KPIs), write a null row with `has_dimensional_breakdown=False` and skip.
2. Query each dimensional file at the anomaly date for the anomaly's KPI, across all applicable dimension names.
3. For each `(dimension_name, dimension_value)` slice, compute:
   - `z_score = (actual - rolling_mean) / rolling_std` using the same 7-day rolling window as Step 1.3
   - `contribution_pct = (dim_actual - dim_expected) / |agg_deviation| × 100`
4. Filter slices with `|z_score| >= 1.5`. Rank by `|z_score|`, keep the top 3.

**Performance approach — pre-computation:**

Rolling stats are computed once per dimensional file (across all 416K dimensional rows) before the per-anomaly loop begins. Each per-anomaly query is then a single boolean mask lookup rather than a rolling-window recalculation.

```python
def precompute_rolling_stats(df):
    grp = df.groupby(["dimension_name", "dimension_value", "kpi_name"])
    df["rolling_mean"]    = grp["kpi_value"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    df["rolling_std"]     = grp["kpi_value"].transform(lambda s: s.rolling(7, min_periods=2).std())
    df["expected_value"]  = grp["rolling_mean"].transform(lambda s: s.shift(1))
    df["z_score"]         = (df["kpi_value"] - df["rolling_mean"]) / df["rolling_std"].replace(0, np.nan)
```

**`dim_data_sufficient` flag:**

Distinguishes two distinct reasons a dimensional row might have all-null `dim_*` columns:
- `has_dimensional_breakdown=False` — the KPI type has no applicable dimensions (web-traffic)
- `has_dimensional_breakdown=True, dim_data_sufficient=False` — the KPI has dimensions but rolling history was too sparse on the anomaly date (fewer than 2 data points in the rolling window → `rolling_std = NaN` → `z_score = NaN` for all slices). Common for early-in-dataset inventory anomalies.

`dimensional_hypothesis_confirmed` (does the top dimensional slice also show an anomaly in the suspected driver KPI from the RCA graph?) is intentionally not computed here — it requires both this file and `rca_graph_results.csv` simultaneously, so it is deferred to Step 3.4.

**Output schema** (`data/detection/dimensional_drill_down.csv`, 16 columns):

| Column | Description |
|---|---|
| `anomaly_id` | Joins to `anomaly_results.csv` |
| `has_dimensional_breakdown` | False for web-traffic KPIs |
| `dim_data_sufficient` | False when rolling history too sparse to compute z |
| `n_dimensions_checked` | Total `(dimension_name, dimension_value)` slices evaluated |
| `dim_1_name` | Top-ranked dimension name (e.g. `marketing_channel`) |
| `dim_1_value` | Top-ranked dimension value (e.g. `email`) |
| `dim_1_z_score` | Z-score of the top slice |
| `dim_1_contribution_pct` | Share of aggregate deviation from this slice |
| `dim_2_*`, `dim_3_*` | Second and third ranked slices |

**Results after re-run against 70-anomaly input:**

| Metric | Value |
|---|---|
| Total anomalies scored | 70 |
| KPI type has applicable dimensions | 65 (93%) |
| `dim_data_sufficient=True` | 55 |
| `dim_data_sufficient=False` (sparse) | 10 |
| Web-traffic KPIs (no dims) | 5 |

Leading dimensions: `marketing_channel` (27 anomalies), `brand` (25 anomalies). `Brand_A` is the consistent outlier across `avg_discount_pct` anomalies; `marketing_channel=email` drove the top click-anomaly z-score.

---

### 3. `scripts/detection/2.3_Ensemble_Voting.py` — ENCODING FIX

No logic changes. The direction filter (`apply_direction_filter`, `build_pig_map`) was already present from Update 1. This update fixed the encoding corruption that had been preventing the script from running.

**Fixes applied (in order):**

1. Replaced all `\xe2\x80\x9c` and `\xe2\x80\x9d` bytes (Unicode left/right curly double quotes used as docstring delimiters) with ASCII `"` — 1,257 replacements
2. Replaced all `\xc3\xa2\xe2\x82\xac"` byte sequences (double-encoded em-dash with accidental quote suffix from step 1) with `--"` — 16 replacements — then manually edited the 4 string literals this produced to remove the stray `"` closing the string early
3. Replaced all `\xe2\x82\xac\xc3\xa2` sequences (reversed em-dash mojibake) with ` -- ` — 1,143 replacements
4. Replaced stray `\xc3\xa2` (28×), `\xe2\x82\xac` (28×) bytes with empty string
5. Replaced `\xe2\x94\x80` box-drawing horizontal line characters in comments with ASCII `-` — 154 replacements
6. Removed UTF-8 BOM (`\xef\xbb\xbf`)

File is now pure ASCII.

---

## New Data Outputs

| File | Type | Rows | Columns | Notes |
|---|---|---|---|---|
| `data/processed/dimensional/dim_customer.csv` | Long-format dimensional | 117,649 | 5 | 5 dims × 7 KPIs × 731 dates |
| `data/processed/dimensional/dim_product_orders.csv` | Long-format dimensional | 131,580 | 5 | 3 dims × 6 KPIs × 731 dates |
| `data/processed/dimensional/dim_product_inventory.csv` | Long-format dimensional | 109,650 | 5 | 3 dims × 5 KPIs × 731 dates |
| `data/processed/dimensional/dim_order_channel.csv` | Long-format dimensional | 35,819 | 5 | 1 dim × 6 KPIs × ~731 dates |
| `data/processed/dimensional/dim_marketing_channel.csv` | Long-format dimensional | 21,930 | 5 | 1 dim × 6 KPIs × ~731 dates |
| `data/processed/dimensional/dim_kpi_registry.json` | Config | — | — | 25 KPIs, 18 with dimensional mappings |
| `data/detection/anomaly_results.csv` | Detection output | **70** | 25 | Down from 182 after direction filter activated |
| `data/detection/dimensional_drill_down.csv` | Drill-down scores | 70 | 16 | Top-3 dimensional contributors per anomaly |

---

## What Is Unchanged

- Detection methodology (Methods A, B, C) and z-score thresholds
- `ensemble_voting_matrix.csv` schema and voting logic — direction filter adds audit columns (`direction_suppressed`, `direction_suppression_reason`) without modifying the vote columns
- KPI DAG structure (`3.1_kpi_dag.py`) — dimensional decomposition is additive; causal graph traversal is separate
- `master_dataset.csv` and the aggregate feature engineering pipeline (Steps 1.1–1.3)
- All Tier 1/2/3 KPI definitions and SLA thresholds in `tier_config.json`

---

## Pending (Steps 3–5)

| Step | File | Change |
|---|---|---|
| 3.4 | `scripts/rca/3.4_rca_assembly.py` | Add 4th LEFT JOIN on `dimensional_drill_down.csv`; add 8 new columns; compute `dimensional_hypothesis_confirmed`; update shape validation (45 → 53 cols) |
| 4.3 | `scripts/intelligence/4.3_recommendation_engine.py` | Add dimension-aware recommendation template layer using `dim_1_name` / `dim_1_value` from drill-down output |
| 5 | `kpi-anomaly-dashboard/` | Add dimensional breakdown panel to the React dashboard |
