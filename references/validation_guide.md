# Post-Generation Validation Guide

## Expected Row Counts (10K customers, 500 products, 2-year range)

| File | Min Rows | Max Rows |
|---|---|---|
| customers.csv | 10,000 | 10,000 |
| products.csv | 500 | 500 |
| orders.csv | 30,000 | 120,000 |
| order_items.csv | 60,000 | 360,000 |
| inventory_daily.csv | 365,000 | 366,000 |
| marketing_spend_daily.csv | 3,650 | 3,660 |
| website_traffic_daily.csv | 730 | 732 |
| anomaly_log.csv | 18 | 22 |
| master_dataset.csv | 730 | 732 |

## KPI Sanity Checks

```python
import pandas as pd

master = pd.read_csv("data/master_dataset.csv")

# Revenue should be positive every day
assert master["total_revenue_usd"].min() > 0

# Anomaly flag should have ~15-20 flagged days
assert 10 <= master["anomaly_flag"].sum() <= 25

# ROAS should be positive
assert master["avg_roas"].dropna().min() > 0

# Conversion rate bounded 0-1
assert master["conversion_rate"].between(0, 1).all()

# Black Friday should be a revenue spike
bf = master[master["date"] == "2024-11-29"]["total_revenue_usd"].values[0]
avg = master["total_revenue_usd"].mean()
assert bf > avg * 2, f"Black Friday revenue not spiking: {bf:.0f} vs avg {avg:.0f}"

print("All checks passed.")
```

## Foreign Key Checks

```python
orders = pd.read_csv("data/orders.csv")
customers = pd.read_csv("data/customers.csv")
items = pd.read_csv("data/order_items.csv")
products = pd.read_csv("data/products.csv")

assert orders["customer_id"].isin(customers["customer_id"]).all(), "Orphaned customer_ids in orders"
assert items["order_id"].isin(orders["order_id"]).all(), "Orphaned order_ids in order_items"
assert items["product_id"].isin(products["product_id"]).all(), "Orphaned product_ids in order_items"

print("Foreign key checks passed.")
```
