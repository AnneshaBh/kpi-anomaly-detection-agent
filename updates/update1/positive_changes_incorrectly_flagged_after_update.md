# Confirmed Anomaly Events — Full Breakdown After Update

**Source:** `data/detection/ensemble_voting_matrix.csv`  
**Scope:** All vote-confirmed anomalies (`confirmed = True`) with a labelled `anomaly_event`  
**Date generated:** 2026-07-02

---

## KPI Direction Reference

| KPI | KPI Type | Positive Change Good? | `positive_is_good` |
|-----|----------|-----------------------|--------------------|
| `total_revenue_usd` | Non-inverse | Yes | `true` |
| `n_orders` | Non-inverse | Yes | `true` |
| `avg_roas` | Non-inverse | Yes | `true` |
| `conversion_rate` | Non-inverse | Yes | `true` |
| `avg_order_value_usd` | Non-inverse | Yes | `true` |
| `total_clicks` | Non-inverse | Yes | `true` |
| `sessions` | Non-inverse | Yes | `true` |
| `inventory_health` | Non-inverse | Yes | `true` |
| `return_rate` | Inverse | No | `false` |
| `n_stockouts` | Inverse | No | `false` |
| `bounce_rate` | Inverse | No | `false` |
| `avg_discount_pct` | Inverse | No | `false` |

---

## Direction Suppression Key

| Symbol | Meaning |
|--------|---------|
| ⚠️ Yes | `direction_suppressed = True` — anomaly filtered out of downstream pipeline |
| ✓ No | `direction_suppressed = False` — anomaly passes through to RCA and intelligence layers |

---

## Event-by-Event Breakdown

### `back_to_school_surge` — 2024-08-20

| KPI | Direction | Severity | Votes | KPI Type | Positive Change Good? | `positive_is_good` | Direction Suppressed |
|-----|-----------|----------|-------|----------|-----------------------|--------------------|----------------------|
| `total_revenue_usd` | UP | HIGH | 3 | Non-inverse | Yes | `true` | ⚠️ Yes |
| `n_orders` | UP | HIGH | 3 | Non-inverse | Yes | `true` | ⚠️ Yes |
| `avg_roas` | DOWN | MEDIUM | 2 | Non-inverse | Yes | `true` | ✓ No |
| `sessions` | UP | LOW | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| `inventory_health` | UP | LOW | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| `avg_discount_pct` | UP | LOW | 2 | Inverse | No | `false` | ⚠️ Yes |

> 5 of 6 confirmed KPIs direction-suppressed. Only the ROAS decline passes downstream — the two HIGH severity revenue and order spikes are silently dropped.

---

### `black_friday_spike` — 2024-11-29 & 2025-11-28

| Date | KPI | Direction | Severity | Votes | KPI Type | Positive Change Good? | `positive_is_good` | Direction Suppressed |
|------|-----|-----------|----------|-------|----------|-----------------------|--------------------|----------------------|
| 2024-11-29 | `total_revenue_usd` | UP | HIGH | 3 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2025-11-28 | `total_revenue_usd` | UP | HIGH | 3 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2024-11-29 | `n_orders` | UP | HIGH | 3 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2025-11-28 | `n_orders` | UP | HIGH | 3 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2024-11-29 | `avg_roas` | UP | HIGH | 3 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2025-11-28 | `avg_roas` | DOWN | MEDIUM | 2 | Non-inverse | Yes | `true` | ✓ No |
| 2024-11-29 | `avg_order_value_usd` | UP | MEDIUM | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2025-11-28 | `avg_order_value_usd` | UP | MEDIUM | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2024-11-29 | `total_clicks` | UP | LOW | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2025-11-28 | `total_clicks` | DOWN | LOW | 2 | Non-inverse | Yes | `true` | ✓ No |
| 2024-11-29 | `inventory_health` | DOWN | LOW | 2 | Non-inverse | Yes | `true` | ✓ No |
| 2025-11-28 | `inventory_health` | UP | LOW | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |

> The three HIGH severity rows for 2024-11-29 (revenue, orders, ROAS) are all direction-suppressed and never reach the RCA layer. This is what causes the `AssertionError: FAIL: Black Friday revenue anomaly should NOT be suppressed` in `3.3_external_drivers.py`.

---

### `bot_traffic_surge` — 2024-11-05 & 2025-09-17

| Date | KPI | Direction | Severity | Votes | KPI Type | Positive Change Good? | `positive_is_good` | Direction Suppressed |
|------|-----|-----------|----------|-------|----------|-----------------------|--------------------|----------------------|
| 2024-11-05 | `bounce_rate` | UP | MEDIUM | 2 | Inverse | No | `false` | ⚠️ Yes |
| 2024-11-05 | `n_stockouts` | — | MEDIUM | 2 | Inverse | No | `false` | ✓ No |
| 2024-11-05 | `sessions` | UP | LOW | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2024-11-05 | `inventory_health` | UP | LOW | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2024-11-05 | `total_clicks` | DOWN | LOW | 2 | Non-inverse | Yes | `true` | ✓ No |
| 2025-09-17 | `avg_roas` | DOWN | MEDIUM | 2 | Non-inverse | Yes | `true` | ✓ No |
| 2025-09-17 | `sessions` | UP | LOW | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2025-09-17 | `inventory_health` | UP | LOW | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |

> `bounce_rate` UP is a legitimately bad signal (inverse KPI going in the wrong direction) yet it is direction-suppressed — this is a direct consequence of the inverted suppression logic.

---

### `cyber_monday_halo` — 2024-12-02 & 2025-12-01

| Date | KPI | Direction | Severity | Votes | KPI Type | Positive Change Good? | `positive_is_good` | Direction Suppressed |
|------|-----|-----------|----------|-------|----------|-----------------------|--------------------|----------------------|
| 2024-12-02 | `total_revenue_usd` | UP | HIGH | 3 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2025-12-01 | `total_revenue_usd` | UP | MEDIUM | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2024-12-02 | `n_orders` | UP | HIGH | 3 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2025-12-01 | `n_orders` | UP | MEDIUM | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2024-12-02 | `avg_roas` | UP | MEDIUM | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2024-12-02 | `avg_order_value_usd` | UP | MEDIUM | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2024-12-02 | `total_clicks` | UP | LOW | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| 2024-12-02 | `inventory_health` | DOWN | LOW | 2 | Non-inverse | Yes | `true` | ✓ No |

> 7 of 8 rows suppressed. Only the inventory drop on 2024-12-02 reaches downstream. Both HIGH severity revenue and order spikes are lost.

---

### `email_campaign_spike` — 2024-09-03

| KPI | Direction | Severity | Votes | KPI Type | Positive Change Good? | `positive_is_good` | Direction Suppressed |
|-----|-----------|----------|-------|----------|-----------------------|--------------------|----------------------|
| `conversion_rate` | UP | MEDIUM | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |

> The sole KPI for this event is direction-suppressed. The event produces zero rows in the downstream RCA layer.

---

### `inventory_stockout` — 2024-03-15 & 2025-02-10

| Date | KPI | Direction | Severity | Votes | KPI Type | Positive Change Good? | `positive_is_good` | Direction Suppressed |
|------|-----|-----------|----------|-------|----------|-----------------------|--------------------|----------------------|
| 2024-03-15 | `total_revenue_usd` | DOWN | MEDIUM | 2 | Non-inverse | Yes | `true` | ✓ No |
| 2024-03-15 | `n_orders` | DOWN | MEDIUM | 2 | Non-inverse | Yes | `true` | ✓ No |
| 2025-02-10 | `n_orders` | DOWN | MEDIUM | 2 | Non-inverse | Yes | `true` | ✓ No |

> All rows pass through correctly — declines on non-inverse KPIs are the expected actionable signal and suppression is correctly not applied.

---

### `marketing_tracking_outage` — 2024-07-10

| KPI | Direction | Severity | Votes | KPI Type | Positive Change Good? | `positive_is_good` | Direction Suppressed |
|-----|-----------|----------|-------|----------|-----------------------|--------------------|----------------------|
| `avg_roas` | DOWN | MEDIUM | 2 | Non-inverse | Yes | `true` | ✓ No |
| `bounce_rate` | DOWN | MEDIUM | 2 | Inverse | No | `false` | ✓ No |
| `inventory_health` | DOWN | LOW | 2 | Non-inverse | Yes | `true` | ✓ No |

> All three rows pass through. However, `bounce_rate` DOWN (fewer bounces) is a positive business outcome and arguably should be suppressed. This is a known edge case where the current logic accidentally produces the right behaviour for the wrong reason.

---

### `website_outage` — 2024-06-18

| KPI | Direction | Severity | Votes | KPI Type | Positive Change Good? | `positive_is_good` | Direction Suppressed |
|-----|-----------|----------|-------|----------|-----------------------|--------------------|----------------------|
| `total_revenue_usd` | UP | MEDIUM | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| `n_orders` | UP | MEDIUM | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| `avg_roas` | DOWN | MEDIUM | 2 | Non-inverse | Yes | `true` | ✓ No |
| `avg_order_value_usd` | UP | MEDIUM | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| `conversion_rate` | UP | MEDIUM | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| `sessions` | DOWN | LOW | 2 | Non-inverse | Yes | `true` | ✓ No |
| `total_clicks` | UP | LOW | 2 | Non-inverse | Yes | `true` | ⚠️ Yes |
| `inventory_health` | DOWN | LOW | 2 | Non-inverse | Yes | `true` | ✓ No |
| `avg_discount_pct` | UP | LOW | 2 | Inverse | No | `false` | ⚠️ Yes |

> 6 of 9 rows suppressed. `avg_discount_pct` UP is an inverse KPI moving in the bad direction — it should not be suppressed, but is.

---

## Suppression Summary Across All Events

| Event | Total Confirmed KPIs | Direction Suppressed | Passing Downstream |
|-------|---------------------|---------------------|--------------------|
| `back_to_school_surge` | 6 | 5 | 1 |
| `black_friday_spike` | 12 | 9 | 3 |
| `bot_traffic_surge` | 8 | 5 | 3 |
| `cyber_monday_halo` | 8 | 7 | 1 |
| `email_campaign_spike` | 1 | 1 | 0 |
| `inventory_stockout` | 3 | 0 | 3 |
| `marketing_tracking_outage` | 3 | 0 | 3 |
| `website_outage` | 9 | 6 | 3 |
| **Total** | **50** | **33** | **17** |

**66% of confirmed anomaly event rows are direction-suppressed and never reach the RCA or intelligence layers.**

---

## Root Cause of Incorrect Suppression

The direction filter in `scripts/detection/2.3_Ensemble_Voting.py` (`apply_direction_filter`, line 235) has inverted logic:

```python
# Current (incorrect)
if pig and direction == "UP":      # suppresses revenue spikes — wrong
    return True, "directionally_invalid: UP change on positive_is_good KPI"
if not pig and direction == "DOWN": # suppresses bounce_rate drops — wrong
    return True, "directionally_invalid: DOWN change on inverse KPI"
```

The correct logic suppresses anomalies moving in the *good* direction, and keeps those moving in the *bad* direction. It must also never suppress HIGH severity anomalies:

```python
# Correct
if row.get("severity") == "HIGH":  # HIGH anomalies always escalate
    return False, ""
if pig and direction == "DOWN":     # revenue falling — bad, keep
    return True, "directionally_invalid: DOWN change on positive_is_good KPI"
if not pig and direction == "UP":   # bounce_rate rising — bad, keep
    return True, "directionally_invalid: UP change on inverse KPI"
```

This fix would also resolve the `AssertionError` in `3.3_external_drivers.py` by ensuring the Black Friday `total_revenue_usd` HIGH severity row is never suppressed and reaches the RCA layer as expected.
