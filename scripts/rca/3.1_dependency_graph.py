#!/usr/bin/env python3
"""
3.1_dependency_graph.py

Step 3.1 â€” Dependency Graph Drill-Down.

For each confirmed anomaly in anomaly_results.csv, traverses a pre-defined
KPI dependency graph to identify the deepest upstream suspected driver.

Graph direction: edges run effect â†’ cause.
  Reading "X â†’ Y": "Y is a suspected upstream driver of X."

Traversal logic:
    Tier 1 (total_revenue_usd, n_orders, avg_roas, conversion_rate):
        DFS from the anomalous KPI following outgoing edges.
        At each node, check z-scores of child KPIs on the anomaly date.
        At branching nodes, pick the child with the highest |z_score|.
        Walk until |z_score| < Z_WATCH_THRESHOLD or a leaf is reached.
        The final node = suspected_driver_kpi.

    Tier 2 / 3 (return_rate, n_stockouts, bounce_rate, etc.):
        These KPIs are already mid-level or leaf-level causes.
        No further traversal â€” the KPI itself is the suspected driver.
        Records which Tier 1 KPIs this anomaly transitively feeds into.

Inputs:
    data/anomaly_results.csv           181 confirmed KPI-day anomalies
    data/processed_kpi_features.csv    731 Ã— 183 â€” z-scores per date per KPI

Outputs:
    data/rca_graph_results.csv         181 rows with dependency chain columns
    data/kpi_anomaly_detection.db      new table: rca_graph_results

Run from project root:  python scripts/3.1_dependency_graph.py
"""

import sqlite3

import networkx as nx
import pandas as pd
from pathlib import Path

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Paths & config
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

BASE        = Path(__file__).parent.parent.parent
DATA        = BASE / "data"
ANOMALY_CSV = DATA / "detection/anomaly_results.csv"
FEATURES_CSV = DATA / "processed/processed_kpi_features.csv"
OUT_CSV     = DATA / "rca/rca_graph_results.csv"
DB_PATH     = DATA / "db/kpi_anomaly_detection.db"

# Minimum |z_score| for a child node to count as co-anomalous during traversal.
# Matches the z_watch threshold in tier_config.json.
Z_WATCH_THRESHOLD = 1.5

TIER_1 = {"total_revenue_usd", "n_orders", "avg_roas", "conversion_rate"}
TIER_2 = {"return_rate", "n_stockouts", "avg_order_value_usd", "bounce_rate"}
TIER_3 = {"total_clicks", "sessions", "inventory_health", "avg_discount_pct"}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Graph definition
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_dependency_graph() -> nx.DiGraph:
    """
    Directed graph encoding KPI causal relationships.
    Edges: effect â†’ cause  (the direction of investigation when an anomaly fires).

    Revenue tree (readme Step 3.1):
        total_revenue_usd â†’ n_orders â†’ sessions â†’ bounce_rate
                                     â†’ conversion_rate â†’ bounce_rate
                                                       â†’ avg_discount_pct
                                     â†’ n_stockouts â†’ inventory_health
                          â†’ avg_order_value_usd â†’ avg_discount_pct
                          â†’ return_rate

    ROAS tree:
        avg_roas â†’ total_clicks

    bounce_rate and avg_discount_pct appear as children in multiple sub-trees
    (multiple parents) â€” this is valid in a DAG, no cycles are introduced.
    """
    G = nx.DiGraph()

    # Revenue tree
    G.add_edges_from([
        ("total_revenue_usd",   "n_orders"),
        ("total_revenue_usd",   "avg_order_value_usd"),
        ("total_revenue_usd",   "return_rate"),
    ])

    # n_orders sub-tree
    G.add_edges_from([
        ("n_orders", "sessions"),
        ("n_orders", "conversion_rate"),
        ("n_orders", "n_stockouts"),
    ])

    # sessions sub-tree
    G.add_edge("sessions", "bounce_rate")

    # avg_order_value sub-tree
    G.add_edge("avg_order_value_usd", "avg_discount_pct")

    # n_stockouts sub-tree
    G.add_edge("n_stockouts", "inventory_health")

    # ROAS tree
    G.add_edge("avg_roas", "total_clicks")

    # conversion_rate tree â€” reachable as child of n_orders AND as Tier 1 root
    # bounce_rate as cause of conversion_rate drop (high bounce â†’ low conversion)
    # avg_discount_pct as cause (incentive-dependent conversion)
    G.add_edges_from([
        ("conversion_rate", "bounce_rate"),
        ("conversion_rate", "avg_discount_pct"),
    ])

    # Guard: ensure no cycles were introduced
    assert nx.is_directed_acyclic_graph(G), "Dependency graph contains a cycle â€” check edge definitions."

    return G


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Traversal
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def traverse(
    root_kpi: str,
    z_row: pd.Series,
    G: nx.DiGraph,
    threshold: float = Z_WATCH_THRESHOLD,
) -> tuple:
    """
    DFS from root_kpi following effect â†’ cause edges.

    At each node:
      - Collect children with |z_score| >= threshold on this date.
      - Pick the child with the highest |z_score| as the primary driver.
      - Continue until no qualifying child exists or a leaf is reached.

    Returns (path: list[str], stopped_reason: str).
    """
    path = [root_kpi]
    current = root_kpi

    while True:
        children = list(G.successors(current))

        if not children:
            return path, "leaf_node_reached"

        candidates = []
        for child in children:
            z_col = f"{child}_z_score"
            if z_col in z_row.index:
                z_val = z_row[z_col]
                if pd.notna(z_val) and abs(float(z_val)) >= threshold:
                    candidates.append((child, float(z_val)))

        if not candidates:
            return path, "no_anomalous_child"

        best_child, _ = max(candidates, key=lambda x: abs(x[1]))
        path.append(best_child)
        current = best_child


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def direction_from_z(z: float) -> str:
    if pd.isna(z):
        return "UNKNOWN"
    return "UP" if z > 0 else ("DOWN" if z < 0 else "FLAT")


def affected_tier1(kpi: str, G: nx.DiGraph) -> list:
    """Tier 1 KPIs that `kpi` transitively feeds into.

    Uses nx.ancestors(G, kpi) which returns all nodes that have a directed
    path TO `kpi` in G (i.e., the upstream KPIs whose anomalies `kpi` rolls
    into). Filtering to TIER_1 gives the business-level outcomes at risk.
    """
    if kpi not in G.nodes():
        return []
    return sorted(n for n in nx.ancestors(G, kpi) if n in TIER_1)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Main
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main() -> None:
    # â”€â”€ Load inputs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    anomalies = pd.read_csv(ANOMALY_CSV, parse_dates=["date"])
    features  = pd.read_csv(FEATURES_CSV, parse_dates=["date"])

    features_idx = features.set_index("date")

    G = build_dependency_graph()

    # All monitored KPIs that have a z_score column in features
    monitored_kpis = sorted(TIER_1 | TIER_2 | TIER_3)
    z_cols_map = {
        kpi: f"{kpi}_z_score"
        for kpi in monitored_kpis
        if f"{kpi}_z_score" in features.columns
    }

    print(f"Loaded {len(anomalies)} anomalies, {len(features)} feature rows.")
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges  (DAG OK)\n")

    # â”€â”€ Process each anomaly â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    records = []

    for _, row in anomalies.iterrows():
        anomaly_id = row["anomaly_id"]
        date       = row["date"]
        kpi        = row["kpi"]
        tier       = int(row["tier"])

        # Fetch z-score row for this date
        if date in features_idx.index:
            z_row = features_idx.loc[date]
            if isinstance(z_row, pd.DataFrame):   # duplicate date guard
                z_row = z_row.iloc[0]
        else:
            z_row = pd.Series(dtype=float)

        # â”€â”€ Co-anomalous KPIs: other monitored KPIs at |z| >= threshold â”€â”€
        co_anomalous = [
            other_kpi
            for other_kpi, z_col in z_cols_map.items()
            if other_kpi != kpi
            and z_col in z_row.index
            and pd.notna(z_row[z_col])
            and abs(float(z_row[z_col])) >= Z_WATCH_THRESHOLD
        ]

        # â”€â”€ Tier 1: graph traversal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if tier == 1 and kpi in G.nodes():
            path, stopped_reason = traverse(kpi, z_row, G)

            driver      = path[-1]
            depth       = len(path) - 1
            dep_chain   = " -> ".join(path)

            driver_z_col = f"{driver}_z_score"
            driver_z = (
                float(z_row[driver_z_col])
                if driver_z_col in z_row.index and pd.notna(z_row[driver_z_col])
                else float("nan")
            )
            driver_dir = direction_from_z(driver_z)

            t1_affected = affected_tier1(driver, G)

        # â”€â”€ Tier 2 / 3: no traversal â€” KPI is already the driver â”€â”€
        else:
            path            = [kpi]
            stopped_reason  = "tier_2_3_no_traversal"
            driver          = kpi
            depth           = 0
            dep_chain       = kpi

            driver_z_col = f"{kpi}_z_score"
            driver_z = (
                float(z_row[driver_z_col])
                if driver_z_col in z_row.index and pd.notna(z_row[driver_z_col])
                else float(row["z_score"])
            )
            driver_dir  = row["direction"]
            t1_affected = affected_tier1(kpi, G)

        records.append({
            "anomaly_id":           anomaly_id,
            "date":                 date.strftime("%Y-%m-%d"),
            "kpi":                  kpi,
            "tier":                 tier,
            "severity":             row["severity"],
            "direction":            row["direction"],
            "deviation_pct":        round(float(row["deviation_pct"]), 4),
            "z_score":              round(float(row["z_score"]), 4),
            "anomaly_flag":         int(row["anomaly_flag"]),
            "anomaly_event":        row["anomaly_event"],
            "dependency_chain":     dep_chain,
            "suspected_driver_kpi": driver,
            "driver_z_score":       round(driver_z, 4) if pd.notna(driver_z) else None,
            "driver_direction":     driver_dir,
            "graph_depth_reached":  depth,
            "co_anomalous_kpis":    ", ".join(co_anomalous) if co_anomalous else "",
            "affected_tier1_kpis":  ", ".join(t1_affected) if t1_affected else "",
            "traversal_stopped":    stopped_reason,
        })

    out_df = pd.DataFrame(records)

    # â”€â”€ Write CSV â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    out_df.to_csv(OUT_CSV, index=False)
    print(f"Saved {len(out_df)} rows -> {OUT_CSV.name}")

    # â”€â”€ Write SQLite â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    conn = sqlite3.connect(DB_PATH)
    out_df.to_sql("rca_graph_results", conn, if_exists="replace", index=False)
    conn.close()
    print(f"Written to SQLite table: rca_graph_results\n")

    # â”€â”€ Summary report â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tier1 = out_df[out_df["tier"] == 1]
    tier2 = out_df[out_df["tier"] == 2]
    tier3 = out_df[out_df["tier"] == 3]

    print("--- Tier 1 traversal depth ---")
    for depth in sorted(tier1["graph_depth_reached"].unique()):
        n = (tier1["graph_depth_reached"] == depth).sum()
        print(f"  Depth {depth}: {n:>3} anomalies")

    print("\n--- Traversal stop reason ---")
    for reason, count in out_df["traversal_stopped"].value_counts().items():
        print(f"  {reason:<30} {count:>4}")

    print("\n--- Top suspected drivers ---")
    for driver, count in out_df["suspected_driver_kpi"].value_counts().head(8).items():
        print(f"  {driver:<30} {count:>4}")

    print(f"\n--- Tier 2/3 affected Tier 1 KPIs ---")
    t23_with_tier1 = (tier2["affected_tier1_kpis"].ne("")).sum() + \
                     (tier3["affected_tier1_kpis"].ne("")).sum()
    print(f"  Tier 2/3 anomalies linked to >=1 Tier 1 KPI: {t23_with_tier1}")

    print("\n--- Sample rows ---")
    sample_cols = ["anomaly_id", "kpi", "tier", "dependency_chain",
                   "suspected_driver_kpi", "driver_z_score", "graph_depth_reached"]
    # Show one HIGH, one MEDIUM, one Tier 3
    sample = pd.concat([
        out_df[out_df["severity"] == "HIGH"].head(2),
        out_df[out_df["severity"] == "MEDIUM"].head(2),
        out_df[out_df["tier"] == 3].head(2),
    ])
    print(sample[sample_cols].to_string(index=False))

    print("\nPASS  Step 3.1 complete -- rca_graph_results.csv ready for Step 3.2")


if __name__ == "__main__":
    main()
