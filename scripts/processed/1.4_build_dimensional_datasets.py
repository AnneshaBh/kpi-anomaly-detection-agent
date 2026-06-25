#!/usr/bin/env python3
"""
1.4_build_dimensional_datasets.py

Builds five pre-computed dimensional datasets by joining and aggregating raw
source tables at (date, dimension_name, dimension_value) grain. All five
outputs share a single long-format schema so Step 2.4 uses one query pattern
for every KPI:

    date | dimension_name | dimension_value | kpi_name | kpi_value

Outputs written to data/processed/dimensional/:
    dim_customer.csv            -- order KPIs by segment / country / age_group /
                                   loyalty_status / cohort_year
    dim_product_orders.csv      -- order KPIs by product category / brand /
                                   product_tier (premium vs standard)
    dim_product_inventory.csv   -- inventory KPIs by product category / brand /
                                   product_tier
    dim_order_channel.csv       -- order KPIs by acquisition channel
    dim_marketing_channel.csv   -- marketing KPIs by spend channel
    dim_kpi_registry.json       -- mapping: kpi_name -> applicable files +
                                   dimension_names (consumed by Step 2.4)

Run from project root:
    python scripts/processed/1.4_build_dimensional_datasets.py
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent.parent.parent
DATA = BASE / "data"
RAW  = DATA / "raw"
OUT  = DATA / "processed" / "dimensional"

ROLLING_WINDOW = 7   # matches feature engineering in Step 1.3

AGE_BINS   = [17, 24, 34, 44, 54, 200]
AGE_LABELS = ["18-24", "25-34", "35-44", "45-54", "55+"]

LONG_COLS = ["date", "dimension_name", "dimension_value", "kpi_name", "kpi_value"]

# ─────────────────────────────────────────────────────────────────────────────
# KPI registry — maps each KPI to which dimensional files and dimension_names
# apply to it.  Consumed by Step 2.4 to determine which slices to query for
# any given anomaly without hardcoding the mapping downstream.
# ─────────────────────────────────────────────────────────────────────────────

KPI_REGISTRY: dict = {
    # ── Revenue / order KPIs ─────────────────────────────────────────────────
    "total_revenue_usd": [
        {"file": "dim_customer.csv",          "dimension_names": ["segment", "country", "age_group", "loyalty_status", "cohort_year"]},
        {"file": "dim_product_orders.csv",    "dimension_names": ["category", "brand", "product_tier"]},
        {"file": "dim_order_channel.csv",     "dimension_names": ["order_channel"]},
    ],
    "n_orders": [
        {"file": "dim_customer.csv",          "dimension_names": ["segment", "country", "age_group", "loyalty_status", "cohort_year"]},
        {"file": "dim_order_channel.csv",     "dimension_names": ["order_channel"]},
    ],
    "avg_order_value_usd": [
        {"file": "dim_customer.csv",          "dimension_names": ["segment", "country", "loyalty_status"]},
        {"file": "dim_product_orders.csv",    "dimension_names": ["category", "brand", "product_tier"]},
        {"file": "dim_order_channel.csv",     "dimension_names": ["order_channel"]},
    ],
    "n_unique_customers": [
        {"file": "dim_customer.csv",          "dimension_names": ["segment", "country", "age_group", "loyalty_status", "cohort_year"]},
        {"file": "dim_order_channel.csv",     "dimension_names": ["order_channel"]},
    ],
    "n_returns": [
        {"file": "dim_customer.csv",          "dimension_names": ["segment", "country", "loyalty_status"]},
        {"file": "dim_product_orders.csv",    "dimension_names": ["category", "brand", "product_tier"]},
        {"file": "dim_order_channel.csv",     "dimension_names": ["order_channel"]},
    ],
    "return_rate": [
        {"file": "dim_customer.csv",          "dimension_names": ["segment", "country", "loyalty_status"]},
        {"file": "dim_product_orders.csv",    "dimension_names": ["category", "brand", "product_tier"]},
        {"file": "dim_order_channel.csv",     "dimension_names": ["order_channel"]},
    ],
    "avg_discount_pct": [
        {"file": "dim_product_orders.csv",    "dimension_names": ["category", "brand", "product_tier"]},
        {"file": "dim_order_channel.csv",     "dimension_names": ["order_channel"]},
    ],
    # ── Inventory KPIs ────────────────────────────────────────────────────────
    "total_units_sold": [
        {"file": "dim_product_inventory.csv", "dimension_names": ["category", "brand", "product_tier"]},
    ],
    "n_stockouts": [
        {"file": "dim_product_inventory.csv", "dimension_names": ["category", "brand", "product_tier"]},
    ],
    "n_reorders": [
        {"file": "dim_product_inventory.csv", "dimension_names": ["category", "brand", "product_tier"]},
    ],
    "total_stock_on_hand": [
        {"file": "dim_product_inventory.csv", "dimension_names": ["category", "brand", "product_tier"]},
    ],
    "inventory_health": [
        {"file": "dim_product_inventory.csv", "dimension_names": ["category", "brand", "product_tier"]},
    ],
    # ── Marketing KPIs ────────────────────────────────────────────────────────
    "avg_roas": [
        {"file": "dim_marketing_channel.csv", "dimension_names": ["marketing_channel"]},
    ],
    "total_spend_usd": [
        {"file": "dim_marketing_channel.csv", "dimension_names": ["marketing_channel"]},
    ],
    "total_impressions": [
        {"file": "dim_marketing_channel.csv", "dimension_names": ["marketing_channel"]},
    ],
    "total_clicks": [
        {"file": "dim_marketing_channel.csv", "dimension_names": ["marketing_channel"]},
    ],
    "total_conversions_marketing": [
        {"file": "dim_marketing_channel.csv", "dimension_names": ["marketing_channel"]},
    ],
    "total_attributed_revenue_usd": [
        {"file": "dim_marketing_channel.csv", "dimension_names": ["marketing_channel"]},
    ],
    # ── Web traffic KPIs — no sub-dimensions in raw data ─────────────────────
    "sessions":                 [],
    "unique_visitors":          [],
    "bounce_rate":              [],
    "conversion_rate":          [],
    "avg_session_duration_sec": [],
    "pages_per_session":        [],
    "conversions_web":          [],
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _wide_to_long(df: pd.DataFrame, dim_col: str, kpi_cols: list[str]) -> pd.DataFrame:
    """
    Convert a grouped-wide DataFrame to the standard long-format schema.

    Input:  df with columns [date, <dim_col>, kpi_1, kpi_2, ...]
    Output: df with columns [date, dimension_name, dimension_value, kpi_name, kpi_value]
    """
    df = df.copy()
    df = df.rename(columns={dim_col: "dimension_value"})
    long = df[["date", "dimension_value"] + kpi_cols].melt(
        id_vars=["date", "dimension_value"],
        value_vars=kpi_cols,
        var_name="kpi_name",
        value_name="kpi_value",
    )
    long.insert(1, "dimension_name", dim_col)
    long["kpi_value"] = long["kpi_value"].round(4)
    return long[LONG_COLS].reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Load raw tables
# ─────────────────────────────────────────────────────────────────────────────

def load_raw() -> dict[str, pd.DataFrame]:
    print("Loading raw source tables...")
    customers   = pd.read_csv(RAW / "customers.csv")
    products    = pd.read_csv(RAW / "products.csv")
    orders      = pd.read_csv(RAW / "orders.csv",      parse_dates=["order_date"])
    order_items = pd.read_csv(RAW / "order_items.csv")
    inventory   = pd.read_csv(RAW / "inventory_daily.csv", parse_dates=["date"])
    marketing   = pd.read_csv(RAW / "marketing_spend_daily.csv", parse_dates=["date"])

    print(f"  customers   : {len(customers):>7,} rows")
    print(f"  products    : {len(products):>7,} rows")
    print(f"  orders      : {len(orders):>7,} rows")
    print(f"  order_items : {len(order_items):>7,} rows")
    print(f"  inventory   : {len(inventory):>7,} rows")
    print(f"  marketing   : {len(marketing):>7,} rows")

    return dict(
        customers=customers, products=products, orders=orders,
        order_items=order_items, inventory=inventory, marketing=marketing,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Enrich dimension tables with derived attributes
# ─────────────────────────────────────────────────────────────────────────────

def _enrich_customers(customers: pd.DataFrame) -> pd.DataFrame:
    """Add age_group, cohort_year, loyalty_status derived columns."""
    cust = customers.copy()
    cust["age_group"] = pd.cut(
        cust["age"], bins=AGE_BINS, labels=AGE_LABELS, right=True
    ).astype(str)
    cust["cohort_year"] = (
        pd.to_datetime(cust["cohort_month"]).dt.year.astype(str)
    )
    cust["loyalty_status"] = cust["is_loyalty_member"].map({1: "loyalty", 0: "non_loyalty"})
    return cust


def _enrich_products(products: pd.DataFrame) -> pd.DataFrame:
    """Map is_premium binary flag to readable product_tier label."""
    prod = products.copy()
    prod["product_tier"] = prod["is_premium"].map({1: "premium", 0: "standard"})
    return prod


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Build dim_customer
# Source:  orders → customers
# KPIs:    total_revenue_usd, n_orders, avg_order_value_usd, n_unique_customers,
#          n_returns, return_rate, avg_discount_pct
# Dims:    segment, country, age_group, loyalty_status, cohort_year
# ─────────────────────────────────────────────────────────────────────────────

CUSTOMER_KPIS = [
    "total_revenue_usd", "n_orders", "avg_order_value_usd",
    "n_unique_customers", "n_returns", "return_rate", "avg_discount_pct",
]

def build_dim_customer(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    cust = _enrich_customers(customers)

    # Join orders to customer attributes — country already on orders (denormalised),
    # so we only pull the extra derived columns from customers to avoid a column conflict
    cust_cols = ["customer_id", "segment", "age_group", "loyalty_status", "cohort_year"]
    merged = orders.merge(cust[cust_cols], on="customer_id", how="left")
    merged["is_return"] = (merged["status"] == "returned").astype(int)
    merged["date"] = merged["order_date"].dt.normalize()

    frames: list[pd.DataFrame] = []
    # country lives directly on orders; all others come from the enriched customer join
    for dim_col in ["segment", "country", "age_group", "loyalty_status", "cohort_year"]:
        grp = merged.groupby(["date", dim_col], observed=True)
        agg = grp.agg(
            total_revenue_usd   =("order_total_usd", "sum"),
            n_orders            =("order_id",        "nunique"),
            avg_order_value_usd =("order_total_usd", "mean"),
            n_unique_customers  =("customer_id",     "nunique"),
            n_returns           =("is_return",       "sum"),
            avg_discount_pct    =("discount_pct",    "mean"),
        ).reset_index()
        agg["return_rate"] = (
            agg["n_returns"] / agg["n_orders"].replace(0, np.nan)
        ).fillna(0)
        frames.append(_wide_to_long(agg, dim_col, CUSTOMER_KPIS))

    result = pd.concat(frames, ignore_index=True)
    print(f"  dim_customer          : {len(result):>7,} rows  "
          f"| {result['dimension_name'].nunique()} dims "
          f"| {result['kpi_name'].nunique()} KPIs")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Build dim_product_orders
# Source:  order_items → orders, order_items → products
# KPIs:    total_revenue_usd, n_orders, avg_order_value_usd,
#          n_returns, return_rate, avg_discount_pct
# Dims:    category, brand, product_tier
# ─────────────────────────────────────────────────────────────────────────────

PRODUCT_ORDER_KPIS = [
    "total_revenue_usd", "n_orders", "avg_order_value_usd",
    "n_returns", "return_rate", "avg_discount_pct",
]

def build_dim_product_orders(
    order_items: pd.DataFrame,
    orders: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    prod = _enrich_products(products)

    # Join order_items → orders (for date and status) → products (for category etc.)
    items = order_items.merge(
        orders[["order_id", "order_date", "status"]],
        on="order_id", how="left",
    )
    items = items.merge(
        prod[["product_id", "category", "brand", "product_tier"]],
        on="product_id", how="left",
    )
    items["is_return"] = (items["status"] == "returned").astype(int)
    items["date"] = pd.to_datetime(items["order_date"]).dt.normalize()

    frames: list[pd.DataFrame] = []
    for dim_col in ["category", "brand", "product_tier"]:
        grp = items.groupby(["date", dim_col], observed=True)

        # Revenue and discount aggregate at line-item level
        agg = grp.agg(
            total_revenue_usd=("line_total_usd", "sum"),
            n_orders         =("order_id",       "nunique"),
            avg_discount_pct =("discount_pct",   "mean"),
        ).reset_index()

        # n_returns: distinct returned orders that contained items in this group
        returns_grp = (
            items[items["is_return"] == 1]
            .groupby(["date", dim_col], observed=True)["order_id"]
            .nunique()
            .rename("n_returns")
            .reset_index()
        )
        agg = agg.merge(returns_grp, on=["date", dim_col], how="left")
        agg["n_returns"] = agg["n_returns"].fillna(0).astype(int)

        agg["return_rate"] = (
            agg["n_returns"] / agg["n_orders"].replace(0, np.nan)
        ).fillna(0)
        agg["avg_order_value_usd"] = (
            agg["total_revenue_usd"] / agg["n_orders"].replace(0, np.nan)
        ).fillna(0)

        frames.append(_wide_to_long(agg, dim_col, PRODUCT_ORDER_KPIS))

    result = pd.concat(frames, ignore_index=True)
    print(f"  dim_product_orders    : {len(result):>7,} rows  "
          f"| {result['dimension_name'].nunique()} dims "
          f"| {result['kpi_name'].nunique()} KPIs")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Build dim_product_inventory
# Source:  inventory_daily → products
# KPIs:    total_stock_on_hand, total_units_sold, n_stockouts,
#          n_reorders, inventory_health
# Dims:    category, brand, product_tier
# ─────────────────────────────────────────────────────────────────────────────

PRODUCT_INV_KPIS = [
    "total_stock_on_hand", "total_units_sold",
    "n_stockouts", "n_reorders", "inventory_health",
]

def build_dim_product_inventory(
    inventory: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    prod = _enrich_products(products)

    merged = inventory.merge(
        prod[["product_id", "category", "brand", "product_tier"]],
        on="product_id", how="left",
    )

    frames: list[pd.DataFrame] = []
    for dim_col in ["category", "brand", "product_tier"]:
        grp = merged.groupby(["date", dim_col], observed=True)
        agg = grp.agg(
            total_stock_on_hand=("stock_on_hand",     "sum"),
            total_units_sold   =("units_sold",        "sum"),
            n_stockouts        =("stockout_flag",     "sum"),
            n_reorders         =("reorder_triggered", "sum"),
            n_skus             =("product_id",        "count"),
        ).reset_index()

        # inventory_health: proportion of SKUs NOT in stockout (1.0 = all healthy)
        agg["inventory_health"] = (
            1 - agg["n_stockouts"] / agg["n_skus"].replace(0, np.nan)
        ).fillna(1.0)
        agg = agg.drop(columns=["n_skus"])

        frames.append(_wide_to_long(agg, dim_col, PRODUCT_INV_KPIS))

    result = pd.concat(frames, ignore_index=True)
    print(f"  dim_product_inventory : {len(result):>7,} rows  "
          f"| {result['dimension_name'].nunique()} dims "
          f"| {result['kpi_name'].nunique()} KPIs")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Build dim_order_channel
# Source:  orders.channel (acquisition channel — organic_search, paid_search,
#          email, social, direct, affiliate, referral)
# KPIs:    total_revenue_usd, n_orders, avg_order_value_usd,
#          n_unique_customers, n_returns, return_rate, avg_discount_pct
# Dims:    order_channel
#
# NOTE: order_channel is distinct from marketing_channel in Step 7.
#       Order channel = how the customer arrived and purchased.
#       Marketing channel = how marketing ops classifies their spend.
# ─────────────────────────────────────────────────────────────────────────────

ORDER_CHANNEL_KPIS = [
    "total_revenue_usd", "n_orders", "avg_order_value_usd",
    "n_unique_customers", "n_returns", "return_rate", "avg_discount_pct",
]

def build_dim_order_channel(orders: pd.DataFrame) -> pd.DataFrame:
    df = orders.copy()
    df["is_return"] = (df["status"] == "returned").astype(int)
    df["date"] = df["order_date"].dt.normalize()
    df = df.rename(columns={"channel": "order_channel"})

    grp = df.groupby(["date", "order_channel"], observed=True)
    agg = grp.agg(
        total_revenue_usd   =("order_total_usd", "sum"),
        n_orders            =("order_id",        "nunique"),
        avg_order_value_usd =("order_total_usd", "mean"),
        n_unique_customers  =("customer_id",     "nunique"),
        n_returns           =("is_return",       "sum"),
        avg_discount_pct    =("discount_pct",    "mean"),
    ).reset_index()
    agg["return_rate"] = (
        agg["n_returns"] / agg["n_orders"].replace(0, np.nan)
    ).fillna(0)

    result = _wide_to_long(agg, "order_channel", ORDER_CHANNEL_KPIS)
    print(f"  dim_order_channel     : {len(result):>7,} rows  "
          f"| {result['dimension_name'].nunique()} dims "
          f"| {result['kpi_name'].nunique()} KPIs")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 7 — Build dim_marketing_channel
# Source:  marketing_spend_daily.csv (already at date × channel grain)
# KPIs:    total_spend_usd, total_impressions, total_clicks,
#          total_conversions_marketing, total_attributed_revenue_usd, avg_roas
# Dims:    marketing_channel
# ─────────────────────────────────────────────────────────────────────────────

MARKETING_KPIS = [
    "total_spend_usd", "total_impressions", "total_clicks",
    "total_conversions_marketing", "total_attributed_revenue_usd", "avg_roas",
]

def build_dim_marketing_channel(marketing: pd.DataFrame) -> pd.DataFrame:
    df = marketing.rename(columns={
        "channel":              "marketing_channel",
        "spend_usd":            "total_spend_usd",
        "impressions":          "total_impressions",
        "clicks":               "total_clicks",
        "conversions":          "total_conversions_marketing",
        "attributed_revenue_usd": "total_attributed_revenue_usd",
        "roas":                 "avg_roas",
    })

    result = _wide_to_long(df, "marketing_channel", MARKETING_KPIS)
    print(f"  dim_marketing_channel : {len(result):>7,} rows  "
          f"| {result['dimension_name'].nunique()} dims "
          f"| {result['kpi_name'].nunique()} KPIs")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 8 — Validate outputs
# ─────────────────────────────────────────────────────────────────────────────

def validate(datasets: dict[str, pd.DataFrame]) -> None:
    print()
    errors: list[str] = []

    for name, df in datasets.items():
        tag = f"[{name}]"

        # Schema
        if list(df.columns) != LONG_COLS:
            errors.append(f"{tag} unexpected columns: {df.columns.tolist()}")
            continue

        # No nulls in key columns
        key_nulls = df[["date", "dimension_name", "dimension_value", "kpi_name"]].isna().sum()
        if key_nulls.any():
            errors.append(f"{tag} nulls in key columns: {key_nulls[key_nulls > 0].to_dict()}")

        # kpi_value null rate — flag if > 5 %
        null_pct = df["kpi_value"].isna().mean()
        if null_pct > 0.05:
            errors.append(f"{tag} kpi_value null rate {null_pct:.1%} exceeds 5 % threshold")

        # Date range
        d_min = df["date"].min()
        d_max = df["date"].max()

        status = "PASS" if not errors else "FAIL"
        print(f"  {status}  {name:<26}  rows={len(df):>7,}  "
              f"dims={df['dimension_name'].nunique()}  "
              f"kpis={df['kpi_name'].nunique()}  "
              f"dates={d_min.date()} to {d_max.date()}")

    if errors:
        raise RuntimeError("Validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


# ─────────────────────────────────────────────────────────────────────────────
# Step 9 — Write outputs
# ─────────────────────────────────────────────────────────────────────────────

def write_outputs(datasets: dict[str, pd.DataFrame]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    for name, df in datasets.items():
        path = OUT / f"{name}.csv"
        out_df = df.copy()
        out_df["date"] = out_df["date"].dt.strftime("%Y-%m-%d")
        out_df.to_csv(path, index=False)
        print(f"  CSV     -> {path.relative_to(BASE)}  ({len(out_df):,} rows)")

    registry_path = OUT / "dim_kpi_registry.json"
    with open(registry_path, "w", encoding="utf-8") as fh:
        json.dump(KPI_REGISTRY, fh, indent=2)
    print(f"  JSON    -> {registry_path.relative_to(BASE)}")


# ─────────────────────────────────────────────────────────────────────────────
# Step 10 — Summary
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(datasets: dict[str, pd.DataFrame]) -> None:
    total_rows = sum(len(df) for df in datasets.values())
    total_kpis = len([k for k, v in KPI_REGISTRY.items() if v])

    print()
    print("=" * 64)
    print("Dimensional Dataset Build — Summary")
    print("=" * 64)
    print(f"  Output directory : data/processed/dimensional/")
    print(f"  Files written    : {len(datasets)} CSVs + dim_kpi_registry.json")
    print(f"  Total rows       : {total_rows:,}")
    print(f"  KPIs with dims   : {total_kpis} of {len(KPI_REGISTRY)}")
    print(f"  KPIs without dims: {len(KPI_REGISTRY) - total_kpis}  (web traffic — no sub-dimensions)")
    print()

    print(f"  {'Dataset':<26}  {'Rows':>8}  {'Dimensions'}")
    print(f"  {'-'*26}  {'-'*8}  {'-'*40}")
    for name, df in datasets.items():
        dim_vals = df.groupby("dimension_name", observed=True)["dimension_value"].nunique()
        dim_summary = ", ".join(f"{d}({n})" for d, n in dim_vals.items())
        print(f"  {name:<26}  {len(df):>8,}  {dim_summary}")

    print()
    print("  Registry coverage:")
    for kpi, entries in KPI_REGISTRY.items():
        if entries:
            dim_names = [d for e in entries for d in e["dimension_names"]]
            print(f"    {kpi:<34} -> {dim_names}")
        else:
            print(f"    {kpi:<34} -> (no dimensions — web traffic)")
    print("=" * 64)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 64)
    print("Step 1.4 — Build Dimensional Datasets")
    print("=" * 64)

    # 1. Load
    raw = load_raw()

    # 2. Build
    print("\nBuilding datasets...")
    datasets: dict[str, pd.DataFrame] = {
        "dim_customer":           build_dim_customer(raw["orders"], raw["customers"]),
        "dim_product_orders":     build_dim_product_orders(raw["order_items"], raw["orders"], raw["products"]),
        "dim_product_inventory":  build_dim_product_inventory(raw["inventory"], raw["products"]),
        "dim_order_channel":      build_dim_order_channel(raw["orders"]),
        "dim_marketing_channel":  build_dim_marketing_channel(raw["marketing"]),
    }

    # 3. Validate
    print("\nValidating outputs...")
    validate(datasets)

    # 4. Write
    print("\nWriting to data/processed/dimensional/...")
    write_outputs(datasets)

    # 5. Summary
    print_summary(datasets)


if __name__ == "__main__":
    main()
