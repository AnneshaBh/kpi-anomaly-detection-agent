"""
Layer 4, Step 4.2 — Prioritization Engine
Scores each confirmed anomaly on five weighted factors and assigns a composite
priority score (0–1), a priority band (HIGH / MEDIUM / LOW), and a priority
rank (1 = most urgent) for downstream alert routing.

Input  : data/impact_results.csv       (181 × 51)
Output : data/priority_results.csv     (181 × 59)
         SQLite table: priority_results

Factor weights (from architecture spec):
  Revenue impact ($)   35 %  — log-scaled absolute dollar impact
  KPI tier             25 %  — Tier 1 = 1.0 | Tier 2 = 0.6 | Tier 3 = 0.3
  Causal confidence    20 %  — root_cause_confidence; severity fallback for NaN
  Recoverability       10 %  — actionability_score (already 0–1)
  External driver      10 %  — penalise macro-driven anomalies

Priority bands:
  HIGH   > 0.75  → page on-call, P1 ticket
  MEDIUM 0.50–0.75 → Slack alert, P2 ticket
  LOW    < 0.50  → daily digest
"""

import os
import sqlite3

import numpy as np
import pandas as pd

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR   = os.path.join(BASE_DIR, "data")
DB_PATH    = os.path.join(DATA_DIR, "db", "kpi_anomaly_detection.db")
INPUT_CSV  = os.path.join(DATA_DIR, "intelligence", "impact_results.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "intelligence", "priority_results.csv")

# ─── Factor weights (must sum to 1.0) ────────────────────────────────────────
W_REVENUE      = 0.35
W_TIER         = 0.25
W_CONFIDENCE   = 0.20
W_RECOVERY     = 0.10
W_EXTERNAL     = 0.10

assert abs(W_REVENUE + W_TIER + W_CONFIDENCE + W_RECOVERY + W_EXTERNAL - 1.0) < 1e-9

# ─── Tier scores ──────────────────────────────────────────────────────────────
TIER_SCORE = {1: 1.0, 2: 0.6, 3: 0.3}

# ─── Confidence fallback by severity (used when root_cause_confidence is NaN)
# HIGH anomalies all have causal confidence scores, so the fallback only fires
# for un-analysed MEDIUM and LOW rows.
CONFIDENCE_FALLBACK = {"HIGH": 0.80, "MEDIUM": 0.50, "LOW": 0.30}

# ─── External driver penalty ──────────────────────────────────────────────────
# Matches the 0.55 penalty applied in Step 3.3 (actionability = 1 − 0.55 = 0.45).
EXTERNAL_FACTOR_DRIVEN     = 0.45
EXTERNAL_FACTOR_NOT_DRIVEN = 1.00

# ─── Priority band thresholds ─────────────────────────────────────────────────
HIGH_THRESHOLD   = 0.75
MEDIUM_THRESHOLD = 0.50


# ─── Load ────────────────────────────────────────────────────────────────────
print("Loading impact_results.csv …")
df = pd.read_csv(INPUT_CSV, parse_dates=["date"])
assert df.shape[0] > 0 and df.shape[1] == 51, f"Expected 51 cols, got {df.shape}"


# ─── Factor 1 — Revenue impact (log-scaled, normalised to [0, 1]) ─────────────
# Uses absolute revenue_at_risk so that captured upside (negative values)
# is treated with the same urgency as equivalent downside risk.
log_abs_risk  = np.log10(df["revenue_at_risk"].abs().clip(lower=1))
log_max_risk  = log_abs_risk.max()                        # normalisation ceiling
revenue_factor = (log_abs_risk / log_max_risk).round(6)


# ─── Factor 2 — KPI tier ─────────────────────────────────────────────────────
tier_factor = df["tier"].map(TIER_SCORE)


# ─── Factor 3 — Causal confidence ────────────────────────────────────────────
# root_cause_confidence is available for the 35 anomalies where causal
# inference ran (all 15 HIGH + 20 MEDIUM).  For the remaining 146 rows the
# severity-based fallback reflects detection strength:
#   HIGH  → 0.80  (3 methods agreed — strong detection evidence)
#   MEDIUM → 0.50  (2 methods agreed — moderate evidence)
#   LOW   → 0.30  (Tier 3 — weakest detection signal)
confidence_fallback = df["severity"].map(CONFIDENCE_FALLBACK)
confidence_factor   = df["root_cause_confidence"].fillna(confidence_fallback)


# ─── Factor 4 — Recoverability ───────────────────────────────────────────────
# actionability_score from Step 3.3 already captures whether an actionable
# fix exists (1.0 = fully actionable, 0.45 = suppressed / externally driven).
recoverability_factor = df["actionability_score"]


# ─── Factor 5 — External driver ──────────────────────────────────────────────
external_factor = df["is_externally_driven"].map(
    {True: EXTERNAL_FACTOR_DRIVEN, False: EXTERNAL_FACTOR_NOT_DRIVEN}
)


# ─── Composite priority score ─────────────────────────────────────────────────
priority_score = (
    W_REVENUE    * revenue_factor
    + W_TIER     * tier_factor
    + W_CONFIDENCE * confidence_factor
    + W_RECOVERY * recoverability_factor
    + W_EXTERNAL * external_factor
).round(6)


# ─── Priority band ────────────────────────────────────────────────────────────
def assign_band(score: float) -> str:
    if score > HIGH_THRESHOLD:
        return "HIGH"
    if score >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"

priority_band = priority_score.apply(assign_band)


# ─── Priority rank (1 = most urgent) ─────────────────────────────────────────
# method='first' guarantees a clean 1–181 range with no ties or gaps.
priority_rank = priority_score.rank(ascending=False, method="first").astype(int)


# ─── Assemble output ──────────────────────────────────────────────────────────
out = df.copy()
out["revenue_impact_factor"]  = revenue_factor
out["tier_factor"]            = tier_factor
out["confidence_factor"]      = confidence_factor.round(6)
out["recoverability_factor"]  = recoverability_factor
out["external_factor"]        = external_factor
out["priority_score"]         = priority_score
out["priority_band"]          = priority_band
out["priority_rank"]          = priority_rank

assert out.shape[0] > 0 and out.shape[1] == 59, f"Expected 59 cols, got {out.shape}"
assert out["priority_score"].between(0, 1).all(), "priority_score out of [0, 1]"
assert out["priority_rank"].nunique() == len(out), "priority_rank contains duplicates"
assert set(out["priority_band"].unique()).issubset({"HIGH", "MEDIUM", "LOW"})


# ─── Write outputs ────────────────────────────────────────────────────────────
print("Writing outputs …")
out.to_csv(OUTPUT_CSV, index=False)

conn = sqlite3.connect(DB_PATH)
out.to_sql("priority_results", conn, if_exists="replace", index=False)
conn.close()

print(f"  Saved {OUTPUT_CSV}")
print(f"  Saved SQLite table: priority_results")
print()


# ─── Summary ──────────────────────────────────────────────────────────────────
print("=" * 68)
print("PRIORITIZATION SUMMARY")
print("=" * 68)

# Priority band distribution
print("\nPriority band distribution:")
band_counts = out["priority_band"].value_counts().reindex(["HIGH", "MEDIUM", "LOW"])
for band, n in band_counts.items():
    pct = n / len(out) * 100
    bar = "#" * int(pct / 2)
    print(f"  {band:<8}  {n:>3}  ({pct:>5.1f}%)  {bar}")

# Cross-tab: priority band vs layer4_priority_flag
print("\nPriority band vs Layer 3 routing flag:")
xtab = pd.crosstab(out["layer4_priority_flag"], out["priority_band"],
                   margins=True)
cols = [c for c in ["HIGH", "MEDIUM", "LOW", "All"] if c in xtab.columns]
print(xtab[cols].to_string())

# Priority score stats by severity
print("\nPriority score stats by severity:")
stats = (
    out.groupby("severity")["priority_score"]
    .agg(["count", "mean", "min", "max"])
    .round(4)
)
print(stats.to_string())

# Top 10 ranked anomalies
print("\nTop 10 highest priority anomalies:")
top10 = (
    out.sort_values("priority_rank")
    .head(10)
    [["priority_rank", "anomaly_id", "kpi", "severity", "direction",
      "revenue_at_risk", "priority_score", "priority_band"]]
)
for _, r in top10.iterrows():
    print(f"  #{int(r['priority_rank']):<3}  {r['anomaly_id']:<22}  "
          f"{r['kpi']:<22}  [{r['severity']:>6}]  "
          f"risk=${r['revenue_at_risk']:>10,.0f}  "
          f"score={r['priority_score']:.4f}  {r['priority_band']}")

# Bottom 5 (lowest priority)
print("\nBottom 5 lowest priority anomalies:")
bot5 = (
    out.sort_values("priority_rank", ascending=False)
    .head(5)
    [["priority_rank", "anomaly_id", "kpi", "severity",
      "revenue_at_risk", "priority_score", "priority_band"]]
)
for _, r in bot5.iterrows():
    print(f"  #{int(r['priority_rank']):<3}  {r['anomaly_id']:<22}  "
          f"{r['kpi']:<22}  [{r['severity']:>6}]  "
          f"risk=${r['revenue_at_risk']:>10,.0f}  "
          f"score={r['priority_score']:.4f}  {r['priority_band']}")

# Factor contribution breakdown (mean across all 181)
print("\nMean factor contributions (weight × factor, across all 181 anomalies):")
contributions = {
    "Revenue impact  (35%)": (W_REVENUE    * out["revenue_impact_factor"]).mean(),
    "KPI tier        (25%)": (W_TIER       * out["tier_factor"]).mean(),
    "Causal confid.  (20%)": (W_CONFIDENCE * out["confidence_factor"]).mean(),
    "Recoverability  (10%)": (W_RECOVERY   * out["recoverability_factor"]).mean(),
    "External driver (10%)": (W_EXTERNAL   * out["external_factor"]).mean(),
}
for label, val in contributions.items():
    print(f"  {label}: {val:.4f}")

# Spot checks
bf = out[(out["date"] == "2024-11-29") & (out["kpi"] == "total_revenue_usd")].iloc[0]
sk = out[(out["date"] == "2024-03-15") & (out["kpi"] == "n_orders")].iloc[0]
sup = out[out["layer4_priority_flag"] == "SUPPRESSED"].sort_values("priority_rank")
print(f"\nSpot checks:")
print(f"  Black Friday revenue : rank=#{int(bf['priority_rank'])}  "
      f"score={bf['priority_score']:.4f}  band={bf['priority_band']}")
print(f"  Inventory stockout   : rank=#{int(sk['priority_rank'])}  "
      f"score={sk['priority_score']:.4f}  band={sk['priority_band']}")
print(f"  Suppressed anomalies : ranks {sup['priority_rank'].tolist()}  "
      f"bands={sup['priority_band'].tolist()}")

print()
print("Step 4.2 complete — priority_results.csv written (181 rows × 59 cols).")
