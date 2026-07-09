# Update 1 — Direction-Aware Anomaly Suppression

## Problem

The anomaly detection engine was treating every statistically significant deviation — up or down — as an alert candidate, regardless of whether the direction of the change was actually problematic for that KPI. This caused **108 of 182 confirmed anomalies (59.3%) to be false alerts**: cases where a KPI improved and the engine incorrectly flagged it as an issue. Black Friday revenue spikes were a visible example — a large positive revenue deviation was being treated the same as a fraud attack or outage.

See [positive_changes_incorrectly_flagged.md](positive_changes_incorrectly_flagged.md) for the full analysis, including the KPI direction classification table and the per-KPI breakdown of false alerts.

---

## Changes

### 1. `data/config/tier_config.json` — `positive_is_good` flag per KPI

Added a `positive_is_good` boolean field inside `kpi_metadata` for all 12 tiered KPIs. This is the single source of truth for direction semantics across the entire pipeline.

| KPI | `positive_is_good` |
|---|---|
| `total_revenue_usd` | `true` |
| `n_orders` | `true` |
| `avg_roas` | `true` |
| `conversion_rate` | `true` |
| `avg_order_value_usd` | `true` |
| `total_clicks` | `true` |
| `sessions` | `true` |
| `inventory_health` | `true` |
| `return_rate` | `false` |
| `n_stockouts` | `false` |
| `bounce_rate` | `false` |
| `avg_discount_pct` | `false` |

---

### 2. `scripts/detection/2.3_Ensemble_Voting.py` — Direction filter at the ensemble stage

Four additions to the ensemble voting script:

**`TIER_JSON` path constant**
Added `TIER_JSON = DATA / "config/tier_config.json"` alongside the existing path constants so the config is loaded from one declared location.

**`load_tier_config()` and `build_pig_map()`**
Two new helpers that read `tier_config.json` and return a `{kpi: bool}` lookup map (`pig_map`) for all 12 KPIs. Built once at startup and passed into the filter function.

**`apply_direction_filter(matrix, pig_map)`**
New function that runs after `add_votes()`. For every vote-confirmed row it applies the following logic:

- `positive_is_good = True` and `direction = "UP"` → suppress (growth, not a problem)
- `positive_is_good = False` and `direction = "DOWN"` → suppress (improvement on an inverse KPI, not a problem)

Adds two audit columns to the full 8,772-row matrix without modifying the `confirmed` column, so the original voting record stays intact in `ensemble_voting_matrix.csv`:
- `direction_suppressed` (bool)
- `direction_suppression_reason` (str)

**`main()` and `print_summary()` updates**
`main()` now loads the pig_map, calls `apply_direction_filter`, and builds the final `confirmed` DataFrame as `matrix["confirmed"] & ~matrix["direction_suppressed"]`. `print_summary()` gained a "Direction Filter" section that prints the vote-confirmed count, number suppressed with the reason, and the final confirmed count passed to `anomaly_results.csv`.

---

## Expected Outcome

| | Before | After |
|---|---|---|
| Confirmed anomalies | 182 | ~67 |
| UP alerts on positive KPIs | 108 | 0 |
| DOWN alerts on inverse KPIs | 4 | 0 |
| Directionally valid alerts | 67 (36.8%) | 67 (100%) |
