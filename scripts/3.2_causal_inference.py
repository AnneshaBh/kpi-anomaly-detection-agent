#!/usr/bin/env python3
"""
3.2_causal_inference.py

Step 3.2 -- Causal Inference (CausalImpact + DoWhy).

Two complementary methods quantify how much a suspected upstream driver
(identified in Step 3.1) actually caused each confirmed KPI anomaly.

Method CI  CausalImpact (MLE-based structural time series)
    Scope : HIGH severity anomalies (15 records)
    Model : statsmodels UnobservedComponents fit on the pre-period using the
            4 exogenous controls as covariates, projected into the post-period
            to form a counterfactual.
    Pre   : all rows before the anomaly date
    Post  : anomaly_date + 3 days (4-day window)
    Output: cumulative effect, relative effect %, 95% CI bounds,
            significance flag, pseudo-posterior-probability

Method DW  DoWhy (structural causal DAG, backdoor linear regression)
    Scope : HIGH + MEDIUM anomalies where Step 3.1 found a distinct upstream
            driver (graph_depth_reached > 0).
    Strategy: run DoWhy ONCE per unique (driver, outcome) pair (not per
              anomaly), then scale the ATE coefficient by each anomaly's
              observed driver deviation to estimate contribution.
    DAG   : domain-knowledge causal graph (cause -> effect direction)
    Output: ATE coefficient, p-value, estimated contribution %,
            random-common-cause refutation result

Combined:
    root_cause_confidence = 0.6 * ci_confidence + 0.4 * dw_confidence
    Falls back to whichever method ran when only one is available.

Note: causalimpact 0.2.6 has two pandas 3.0 incompatibilities that were
      patched directly in its source files (misc.py and analysis.py).

Inputs:
    data/rca_graph_results.csv         Step 3.1 output -- 181 rows
    data/master_dataset.csv            Raw KPIs + 4 exogenous controls
    data/processed_kpi_features.csv    Rolling means for driver baseline

Outputs:
    data/rca_causal_results.csv        181 rows with causal inference columns
    data/kpi_anomaly_detection.db      new table: rca_causal_results

Run from project root:  python scripts/3.2_causal_inference.py
"""

import io
import sys
import sqlite3
import warnings
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

warnings.filterwarnings("ignore")

# ── pandas 3.0 compat guard for causalimpact 0.2.6 ──────────────────────────
# The source files have been patched, but guard here too in case of reinstall.
if not hasattr(pd.core.dtypes.common, "is_datetime_or_timedelta_dtype"):
    pd.core.dtypes.common.is_datetime_or_timedelta_dtype = (
        lambda x: pd.api.types.is_datetime64_any_dtype(x)
        or pd.api.types.is_timedelta64_dtype(x)
    )

from causalimpact import CausalImpact
from dowhy import CausalModel

# ─────────────────────────────────────────────────────────────
# Paths & config
# ─────────────────────────────────────────────────────────────

BASE         = Path(__file__).parent.parent
DATA         = BASE / "data"
GRAPH_CSV    = DATA / "rca_graph_results.csv"
MASTER_CSV   = DATA / "master_dataset.csv"
FEATURES_CSV = DATA / "processed_kpi_features.csv"
OUT_CSV      = DATA / "rca_causal_results.csv"
DB_PATH      = DATA / "kpi_anomaly_detection.db"

EXOG_COLS   = ["economic_index", "seasonal_index", "marketing_pressure", "consumer_sentiment"]
POST_WINDOW = 4    # days in the post-period
MIN_PRE     = 30   # minimum pre-period rows for a meaningful CI model

# ─────────────────────────────────────────────────────────────
# Causal DAG for DoWhy  (cause -> effect direction)
# ─────────────────────────────────────────────────────────────

CAUSAL_DAG = """digraph {
    economic_index      -> consumer_sentiment;
    economic_index      -> avg_order_value_usd;
    consumer_sentiment  -> sessions;
    consumer_sentiment  -> return_rate;
    marketing_pressure  -> avg_roas;
    marketing_pressure  -> total_clicks;
    seasonal_index      -> n_orders;
    seasonal_index      -> sessions;
    bounce_rate         -> sessions;
    sessions            -> n_orders;
    sessions            -> conversion_rate;
    conversion_rate     -> n_orders;
    n_orders            -> total_revenue_usd;
    avg_order_value_usd -> total_revenue_usd;
    return_rate         -> total_revenue_usd;
    avg_roas            -> total_revenue_usd;
    inventory_health    -> n_stockouts;
    n_stockouts         -> n_orders;
    avg_discount_pct    -> conversion_rate;
    avg_discount_pct    -> avg_order_value_usd;
    total_clicks        -> avg_roas;
}"""

# ─────────────────────────────────────────────────────────────
# Method CI -- CausalImpact
# ─────────────────────────────────────────────────────────────

def run_ci(data_rng: pd.DataFrame, anom_idx: int, outcome_kpi: str) -> dict:
    """
    Fit CausalImpact (MLE) for one anomaly.

    Args:
        data_rng    master_dataset with RangeIndex, sorted by date
        anom_idx    integer row position of the anomaly date
        outcome_kpi column name of the KPI being modelled

    Returns dict with CI result columns (ci_ran=True) or failure info (ci_ran=False).
    """
    if anom_idx < MIN_PRE:
        return {"ci_ran": False, "ci_skip_reason": f"pre_period too short ({anom_idx} rows)"}

    n        = len(data_rng)
    post_end = min(anom_idx + POST_WINDOW - 1, n - 1)
    ci_data  = data_rng[[outcome_kpi] + EXOG_COLS].copy()

    try:
        ci = CausalImpact(
            ci_data,
            [0, anom_idx - 1],
            [anom_idx, post_end],
            estimation="MLE",
        )
        ci.run()
        inf  = ci.inferences
        last = inf.iloc[post_end]

        cum_actual = float(last["cum_response"])
        cum_pred   = float(last["cum_pred"])
        cum_eff    = float(last["cum_effect"])
        eff_lower  = float(last["cum_effect_lower"])
        eff_upper  = float(last["cum_effect_upper"])

        lo, hi         = min(eff_lower, eff_upper), max(eff_lower, eff_upper)
        ci_significant = (lo > 0) or (hi < 0)

        # Pseudo-posterior-probability: probability the true effect != 0
        eff_std    = max(abs(hi - lo) / (2 * 1.96), 1e-9)
        ci_conf    = float(stats.norm.cdf(abs(cum_eff) / eff_std))
        rel_pct    = (cum_eff / abs(cum_pred) * 100) if abs(cum_pred) > 1e-9 else 0.0

        return {
            "ci_ran":                True,
            "ci_actual_cum":         round(cum_actual, 2),
            "ci_counterfactual_cum": round(cum_pred, 2),
            "ci_absolute_effect":    round(cum_eff, 2),
            "ci_relative_effect_pct": round(rel_pct, 2),
            "ci_lower":              round(eff_lower, 2),
            "ci_upper":              round(eff_upper, 2),
            "ci_effect_significant": ci_significant,
            "ci_confidence":         round(ci_conf, 4),
            "ci_skip_reason":        "",
        }
    except Exception as exc:
        return {"ci_ran": False, "ci_skip_reason": str(exc)[:140]}


# ─────────────────────────────────────────────────────────────
# Method DW -- DoWhy (per unique pair, results cached)
# ─────────────────────────────────────────────────────────────

def run_dw_pair(df: pd.DataFrame, treatment: str, outcome: str) -> dict:
    """
    Backdoor linear regression for one (treatment, outcome) pair.
    Suppresses DoWhy's Unicode stdout to avoid Windows cp1252 errors.

    Returns dict with dw_ok=True and ATE stats, or dw_ok=False on failure.
    """
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        model = CausalModel(
            data=df, treatment=treatment, outcome=outcome, graph=CAUSAL_DAG
        )
        identified = model.identify_effect(proceed_when_unidentifiable=True)
        estimate   = model.estimate_effect(
            identified,
            method_name="backdoor.linear_regression",
            target_units="ate",
        )
        ate   = float(estimate.value)
        p_val = float(estimate.test_stat_significance()["p_value"][0])

        # Refutation: random common cause (5 sims -- fast)
        refute    = model.refute_estimate(
            identified, estimate,
            method_name="random_common_cause",
            num_simulations=5,
        )
        refute_p  = float(refute.refutation_result.get("p_value", 1.0))
        # High refute_p means new_effect close to original -> estimate is robust
        ref_passed = refute_p > 0.05

        return {
            "dw_ok":               True,
            "dw_ate_coeff":        round(ate, 8),
            "dw_p_value":          round(p_val, 6),
            "dw_refutation_passed": ref_passed,
        }
    except Exception as exc:
        return {"dw_ok": False, "dw_error": str(exc)[:140]}
    finally:
        sys.stdout = old


# ─────────────────────────────────────────────────────────────
# Default dicts (no-op when a method doesn't run)
# ─────────────────────────────────────────────────────────────

def _ci_defaults() -> dict:
    return {k: None for k in [
        "ci_ran", "ci_actual_cum", "ci_counterfactual_cum", "ci_absolute_effect",
        "ci_relative_effect_pct", "ci_lower", "ci_upper",
        "ci_effect_significant", "ci_confidence", "ci_skip_reason",
    ]}


def _dw_defaults() -> dict:
    return {k: None for k in [
        "dw_ran", "dw_treatment", "dw_outcome", "dw_ate_coeff", "dw_p_value",
        "dw_driver_deviation", "dw_estimated_contribution",
        "dw_effect_pct", "dw_refutation_passed", "dw_confidence",
    ]}


# ─────────────────────────────────────────────────────────────
# Narrative builder
# ─────────────────────────────────────────────────────────────

def build_narrative(row: dict, ci: dict, dw: dict) -> str:
    kpi    = row["kpi"]
    driver = row["suspected_driver_kpi"]
    dir_   = row["direction"]
    dev    = float(row["deviation_pct"])
    date   = str(row["date"])[:10]

    lead = f"{kpi} moved {dir_} {dev:+.1f}% on {date}; suspected driver: {driver}."

    ci_part = ""
    if ci.get("ci_ran"):
        pct = ci.get("ci_relative_effect_pct", 0) or 0
        sig = "significant" if ci.get("ci_effect_significant") else "uncertain"
        ci_part = f" CausalImpact: {pct:+.1f}% cumulative effect ({sig})."

    dw_part = ""
    if dw.get("dw_ran"):
        pct = dw.get("dw_effect_pct", 0) or 0
        rob = "robust" if dw.get("dw_refutation_passed") else "unverified"
        dw_part = f" DoWhy: {driver} explains {pct:+.1f}% of expected outcome ({rob})."

    return lead + ci_part + dw_part


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main() -> None:
    # ── Load inputs ──────────────────────────────────────────
    graph_df    = pd.read_csv(GRAPH_CSV, parse_dates=["date"])
    master_df   = pd.read_csv(MASTER_CSV, parse_dates=["date"])
    features_df = pd.read_csv(FEATURES_CSV, parse_dates=["date"])

    master_rng = master_df.reset_index(drop=True)   # RangeIndex for CausalImpact
    master_idx = master_df.set_index("date")         # DatetimeIndex for lookups
    feats_idx  = features_df.set_index("date")

    print(f"Loaded {len(graph_df)} anomalies from rca_graph_results.csv")
    print(f"CausalImpact: HIGH severity ({(graph_df['severity']=='HIGH').sum()} records)")
    dw_scope_count = ((graph_df["severity"].isin(["HIGH","MEDIUM"])) & (graph_df["graph_depth_reached"] > 0)).sum()
    print(f"DoWhy:        HIGH+MEDIUM with distinct driver ({dw_scope_count} records)\n")

    # ── Pre-run DoWhy per unique (driver, outcome) pair ──────
    dw_pairs = (
        graph_df[
            graph_df["severity"].isin(["HIGH", "MEDIUM"]) &
            (graph_df["graph_depth_reached"] > 0)
        ][["suspected_driver_kpi", "kpi"]]
        .drop_duplicates()
    )
    print(f"Unique DoWhy pairs to estimate: {len(dw_pairs)}")

    dw_cache: dict = {}
    for _, p in dw_pairs.iterrows():
        driver, outcome = p["suspected_driver_kpi"], p["kpi"]
        key = (driver, outcome)
        if driver not in master_rng.columns or outcome not in master_rng.columns:
            dw_cache[key] = {"dw_ok": False, "dw_error": "missing_column"}
            print(f"  SKIP  {driver} -> {outcome}  (column not in master)")
            continue
        print(f"  DW    {driver} -> {outcome} ...", end="  ")
        res = run_dw_pair(master_rng, driver, outcome)
        dw_cache[key] = res
        if res["dw_ok"]:
            print(f"ATE={res['dw_ate_coeff']:.6f}  p={res['dw_p_value']:.4f}  ref_passed={res['dw_refutation_passed']}")
        else:
            print(f"FAILED: {res.get('dw_error','')}")

    print()

    # ── Process every anomaly ─────────────────────────────────
    print("Running CausalImpact on HIGH anomalies ...")
    records = []

    for _, row in graph_df.iterrows():
        rec = row.to_dict()
        rec["date"] = str(row["date"])[:10]

        # ── CI (HIGH only) ────────────────────────────────────
        ci_res = _ci_defaults()
        ci_res["ci_ran"] = False

        if row["severity"] == "HIGH":
            anom_date = row["date"]
            pos_matches = master_rng.index[master_rng["date"] == anom_date]
            if len(pos_matches):
                anom_idx = int(pos_matches[0])
                print(f"  CI  {row['anomaly_id']} ({row['kpi']}) ...", end="  ")
                ci_res = run_ci(master_rng, anom_idx, row["kpi"])
                ci_res.setdefault("ci_ran", False)
                if ci_res["ci_ran"]:
                    print(f"effect={ci_res['ci_relative_effect_pct']:+.1f}%  sig={ci_res['ci_effect_significant']}")
                else:
                    print(f"skipped -- {ci_res.get('ci_skip_reason','')}")

        rec.update(ci_res)

        # ── DoWhy (HIGH + MEDIUM, depth > 0) ──────────────────
        dw_res = _dw_defaults()
        dw_res["dw_ran"] = False

        driver  = row["suspected_driver_kpi"]
        outcome = row["kpi"]
        depth   = int(row["graph_depth_reached"])

        if row["severity"] in ("HIGH", "MEDIUM") and depth > 0:
            cached = dw_cache.get((driver, outcome), {})
            if cached.get("dw_ok"):
                ate   = cached["dw_ate_coeff"]
                dw_p  = cached["dw_p_value"]
                anom_date = row["date"]

                # Driver deviation: actual - rolling_mean (the "expected" baseline)
                driver_actual = None
                driver_mean   = None
                outcome_mean  = None

                try:
                    if anom_date in master_idx.index and driver in master_idx.columns:
                        driver_actual = float(master_idx.loc[anom_date, driver])
                    roll_col = f"{driver}_rolling_mean"
                    if anom_date in feats_idx.index and roll_col in feats_idx.columns:
                        driver_mean = float(feats_idx.loc[anom_date, roll_col])
                    out_roll = f"{outcome}_rolling_mean"
                    if anom_date in feats_idx.index and out_roll in feats_idx.columns:
                        outcome_mean = float(feats_idx.loc[anom_date, out_roll])
                except Exception:
                    pass

                if driver_actual is not None and driver_mean is not None:
                    driver_dev  = driver_actual - driver_mean
                    est_contrib = ate * driver_dev
                    effect_pct  = (
                        (est_contrib / abs(outcome_mean) * 100)
                        if outcome_mean and abs(outcome_mean) > 1e-9
                        else None
                    )
                    dw_conf = 0.9 if dw_p < 0.05 else 0.5

                    dw_res = {
                        "dw_ran":                   True,
                        "dw_treatment":             driver,
                        "dw_outcome":               outcome,
                        "dw_ate_coeff":             ate,
                        "dw_p_value":               dw_p,
                        "dw_driver_deviation":      round(driver_dev, 4),
                        "dw_estimated_contribution": round(est_contrib, 4),
                        "dw_effect_pct":            round(effect_pct, 2) if effect_pct is not None else None,
                        "dw_refutation_passed":     cached["dw_refutation_passed"],
                        "dw_confidence":            dw_conf,
                    }

        rec.update(dw_res)

        # ── Blended root_cause_confidence ─────────────────────
        ci_conf = ci_res.get("ci_confidence") if ci_res.get("ci_ran") else None
        dw_conf = dw_res.get("dw_confidence") if dw_res.get("dw_ran") else None

        if ci_conf is not None and dw_conf is not None:
            rcc = round(0.6 * ci_conf + 0.4 * dw_conf, 4)
        elif ci_conf is not None:
            rcc = round(ci_conf, 4)
        elif dw_conf is not None:
            rcc = round(dw_conf, 4)
        else:
            rcc = None

        rec["root_cause_confidence"] = rcc
        rec["causal_summary"] = build_narrative(rec, ci_res, dw_res)
        records.append(rec)

    # ── Write outputs ─────────────────────────────────────────
    out_df = pd.DataFrame(records)
    out_df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {len(out_df)} rows -> {OUT_CSV.name}")

    conn = sqlite3.connect(DB_PATH)
    out_df.to_sql("rca_causal_results", conn, if_exists="replace", index=False)
    conn.close()
    print("Written to SQLite table: rca_causal_results\n")

    # ── Summary ───────────────────────────────────────────────
    ci_ran_n = int(out_df["ci_ran"].sum())
    dw_ran_n = int(out_df["dw_ran"].sum())

    print("--- Results summary ---")
    print(f"  CausalImpact ran : {ci_ran_n} anomalies")
    if ci_ran_n:
        sig_n = int(out_df.loc[out_df["ci_ran"] == True, "ci_effect_significant"].sum())
        print(f"    Significant    : {sig_n} / {ci_ran_n}")

    print(f"  DoWhy ran        : {dw_ran_n} anomalies")
    if dw_ran_n:
        rob_n = int(out_df.loc[out_df["dw_ran"] == True, "dw_refutation_passed"].sum())
        print(f"    Refutation OK  : {rob_n} / {dw_ran_n}")

    rcc_avail = out_df["root_cause_confidence"].notna().sum()
    rcc_mean  = out_df["root_cause_confidence"].mean()
    print(f"  root_cause_confidence available : {rcc_avail}")
    print(f"  Mean root_cause_confidence      : {rcc_mean:.3f}")

    # ── Spot-check key ground-truth events ───────────────────
    print("\n--- Key ground-truth events ---")
    spot_cols = [
        "anomaly_id", "kpi", "severity", "suspected_driver_kpi",
        "ci_relative_effect_pct", "ci_effect_significant",
        "dw_effect_pct", "dw_refutation_passed", "root_cause_confidence",
    ]
    for date_str, kpi in [
        ("2024-11-29", "total_revenue_usd"),
        ("2024-03-15", "n_orders"),
        ("2024-09-03", "conversion_rate"),
    ]:
        match = out_df[(out_df["date"] == date_str) & (out_df["kpi"] == kpi)]
        if len(match):
            print(match[spot_cols].to_string(index=False))
        else:
            print(f"  NOT FOUND: {date_str} {kpi}")
        print()

    print("PASS  Step 3.2 complete -- rca_causal_results.csv ready for Step 3.3")


if __name__ == "__main__":
    main()
