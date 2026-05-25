# Schema Reference

## customers.csv
| Column | Type | Description |
|---|---|---|
| customer_id | string | PK. Format: C0000001 |
| segment | string | loyalty / regular / occasional / new / churned |
| country | string | ISO country code |
| cohort_month | string | YYYY-MM of first activity |
| age | int | Customer age |
| is_loyalty_member | int | 0/1 flag |
| lifetime_value_usd | float | Estimated LTV |
| email_opt_in | int | 0/1 flag |
| avg_review_score | float | 1-5 scale; ~2% nulls |

## products.csv
| Column | Type | Description |
|---|---|---|
| product_id | string | PK. Format: P000001 |
| category | string | Electronics / Apparel / Home / Sports / Beauty / Food / Toys / Books |
| brand | string | Brand_A … Brand_T |
| base_price_usd | float | List price |
| cost_usd | float | COGS |
| gross_margin | float | (price-cost)/price |
| is_premium | int | 1 if price > 75th percentile |

## orders.csv
| Column | Type | Description |
|---|---|---|
| order_id | string | PK. Format: O000000001 |
| customer_id | string | FK → customers |
| order_date | date | YYYY-MM-DD |
| channel | string | organic_search / paid_search / email / social / direct / affiliate / referral |
| status | string | completed / returned / cancelled |
| order_total_usd | float | Sum of line totals after discount |
| discount_pct | float | Overall order discount fraction |
| country | string | Customer country |

## order_items.csv
| Column | Type | Description |
|---|---|---|
| order_item_id | string | PK |
| order_id | string | FK → orders |
| product_id | string | FK → products |
| quantity | int | Units purchased |
| unit_price_usd | float | Price after discount |
| discount_pct | float | Line-level discount |
| line_total_usd | float | unit_price × quantity |

## inventory_daily.csv
| Column | Type | Description |
|---|---|---|
| date | date | YYYY-MM-DD |
| product_id | string | FK → products |
| stock_on_hand | int | Units available at day end |
| units_sold | int | Demand consumed |
| reorder_triggered | int | 0/1 |
| stockout_flag | int | 1 if stock hit 0 |

## marketing_spend_daily.csv
| Column | Type | Description |
|---|---|---|
| date | date | YYYY-MM-DD |
| channel | string | paid_search / social / email / affiliate / display |
| spend_usd | float | Daily channel spend |
| impressions | int | Ad impressions |
| clicks | int | Clicks |
| conversions | int | Attributed conversions |
| attributed_revenue_usd | float | Revenue attributed |
| roas | float | attributed_revenue / spend |

## website_traffic_daily.csv
| Column | Type | Description |
|---|---|---|
| date | date | YYYY-MM-DD |
| sessions | int | Total sessions |
| unique_visitors | int | Deduplicated visitors |
| bounce_rate | float | 0-1 |
| pages_per_session | float | Avg pages viewed |
| avg_session_duration_sec | float | Avg duration in seconds |
| conversion_rate | float | 0-1 |
| conversions | int | Sessions converting |

## master_dataset.csv
All columns from the daily aggregates of every table above, joined on `date`.

Additional derived columns:
| Column | Source |
|---|---|
| n_orders | orders aggregated by date |
| n_returns | returned orders by date |
| return_rate | n_returns / n_orders |
| economic_index | latent driver |
| marketing_pressure | latent driver |
| consumer_sentiment | latent driver |
| seasonal_index | latent driver |
| inventory_health | latent driver |
| anomaly_flag | 1 if any anomaly event on this date |
| anomaly_events | pipe-delimited list of event names |
