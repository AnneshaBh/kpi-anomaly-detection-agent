"""
Layer 5, Step 5.1 — Alert Formatter
Reads intelligence_results.csv and builds a structured alert payload for every
anomaly, segmented by audience and delivery urgency.

Routing logic
  ESCALATE   (15)  -> audience: Executive, Operations | channel: Slack + Email | urgency: Immediate
  INVESTIGATE(86)  -> audience: Operations, Analyst   | channel: Email          | urgency: Daily
  MONITOR    (74)  -> audience: Analyst               | channel: Digest         | urgency: Weekly
  SUPPRESSED  (6)  -> audience: None                  | channel: None           | urgency: Suppressed

Input  : data/intelligence_results.csv  (181 x 68)
Output : data/alert_payloads.csv        (181 x 73)
         SQLite table: alert_payloads
"""

import os
import sqlite3
import sys

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE_DIR, "data")
DB_PATH    = os.path.join(DATA_DIR, "kpi_anomaly_detection.db")
INPUT_CSV  = os.path.join(DATA_DIR, "intelligence_results.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "alert_payloads.csv")


# ── Constants ─────────────────────────────────────────────────────────────────
KPI_LABELS = {
    "total_revenue_usd":   "Total Revenue (USD)",
    "n_orders":            "Order Volume",
    "avg_roas":            "Avg. ROAS",
    "conversion_rate":     "Conversion Rate",
    "return_rate":         "Return Rate",
    "avg_order_value_usd": "Avg. Order Value (USD)",
    "bounce_rate":         "Bounce Rate",
    "sessions":            "Website Sessions",
    "total_clicks":        "Total Clicks",
    "avg_discount_pct":    "Avg. Discount %",
    "inventory_health":    "Inventory Health",
    "n_stockouts":         "Stockout Count",
}

EFFORT_LABELS = {
    "H": "High (multi-day, cross-team)",
    "M": "Medium (same-day task)",
    "L": "Low (< 1 hour check)",
}

# Routing table: flag -> audience, delivery channel, urgency
ROUTING = {
    "ESCALATE":    {
        "audience": "Executive, Operations",
        "channel":  "Slack + Email",
        "urgency":  "Immediate",
    },
    "INVESTIGATE": {
        "audience": "Operations, Analyst",
        "channel":  "Email",
        "urgency":  "Daily",
    },
    "MONITOR":     {
        "audience": "Analyst",
        "channel":  "Digest",
        "urgency":  "Weekly",
    },
    "SUPPRESSED":  {
        "audience": "None",
        "channel":  "None",
        "urgency":  "Suppressed",
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _kpi_label(kpi):
    return KPI_LABELS.get(kpi, kpi.replace("_", " ").title())


def _fmt_movement(direction, deviation_pct):
    """Return 'UP +X.X%' / 'DOWN -X.X%', or 'ELEVATED' when values are NaN."""
    if pd.isna(direction) or pd.isna(deviation_pct):
        return "ELEVATED"
    sign = "+" if float(deviation_pct) > 0 else ""
    return f"{direction} {sign}{float(deviation_pct):.1f}%"


def _fmt_revenue(revenue_at_risk):
    v = float(revenue_at_risk)
    if v < 0:
        return f"${abs(v):,.0f} captured upside"
    if v > 0:
        return f"${v:,.0f} at risk"
    return "$0"


def _safe(val, fallback="N/A"):
    if pd.isna(val) or str(val).strip() == "":
        return fallback
    return str(val).strip()


# ── Subject builders ──────────────────────────────────────────────────────────
def _build_subject(row):
    flag     = row["layer4_priority_flag"]
    kpi_lbl  = _kpi_label(row["kpi"])
    date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
    movement = _fmt_movement(row["direction"], row["deviation_pct"])

    if flag == "SUPPRESSED":
        ext = _safe(row["external_driver_type"], "External Factor")
        return f"[SUPPRESSED] {kpi_lbl} {movement} — External: {ext} | {date_str}"

    return f"[{flag}] {kpi_lbl} {movement} — Priority #{int(row['priority_rank'])} | {date_str}"


# ── Body builders ─────────────────────────────────────────────────────────────
def _body_escalate(row):
    movement = _fmt_movement(row["direction"], row["deviation_pct"])
    z_part   = f" (z={float(row['z_score']):.2f})" if pd.notna(row["z_score"]) else ""
    date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")

    return "\n".join([
        f"ANOMALY DETECTED — {date_str}",
        f"KPI: {_kpi_label(row['kpi'])} | Severity: {row['severity']} | Tier {int(row['tier'])}",
        f"Movement: {movement}{z_part} | Revenue Impact: {_fmt_revenue(row['revenue_at_risk'])}",
        "",
        "BUSINESS IMPACT",
        _safe(row["impact_narrative"]),
        "",
        "ROOT CAUSE",
        _safe(row["rca_narrative"]),
        "",
        "IMMEDIATE ACTION REQUIRED",
        _safe(row["immediate_action"]),
        "",
        f"Owner: {_safe(row['recommended_owner'])} | Effort: {EFFORT_LABELS.get(str(row['effort_level']), row['effort_level'])}",
    ])


def _body_investigate(row):
    movement = _fmt_movement(row["direction"], row["deviation_pct"])
    z_part   = f" (z={float(row['z_score']):.2f})" if pd.notna(row["z_score"]) else ""
    date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")

    return "\n".join([
        f"INVESTIGATION REQUIRED — {date_str}",
        f"KPI: {_kpi_label(row['kpi'])} | Severity: {row['severity']} | Tier {int(row['tier'])}",
        f"Movement: {movement}{z_part} | Revenue Impact: {_fmt_revenue(row['revenue_at_risk'])}",
        "",
        "BUSINESS IMPACT",
        _safe(row["impact_narrative"]),
        "",
        "ROOT CAUSE",
        _safe(row["rca_narrative"]),
        "",
        "RECOMMENDED ACTIONS",
        f"Immediate: {_safe(row['immediate_action'])}",
        "",
        f"Short-term: {_safe(row['short_term_fix'])}",
        "",
        f"Owner: {_safe(row['recommended_owner'])} | Effort: {EFFORT_LABELS.get(str(row['effort_level']), row['effort_level'])}",
    ])


def _body_monitor(row):
    movement = _fmt_movement(row["direction"], row["deviation_pct"])
    date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
    actions  = _safe(row["playbook_actions"], "Review KPI trend and assess against baseline.")

    return "\n".join([
        f"MONITORING ALERT — {date_str}",
        f"KPI: {_kpi_label(row['kpi'])} | Severity: {row['severity']} | Tier {int(row['tier'])}",
        f"Movement: {movement} | Rank: #{int(row['priority_rank'])}",
        "",
        "ROOT CAUSE",
        _safe(row["rca_narrative"]),
        "",
        "SUGGESTED ACTIONS",
        actions,
        "",
        f"Owner: {_safe(row['recommended_owner'])}",
    ])


def _body_suppressed(row):
    movement = _fmt_movement(row["direction"], row["deviation_pct"])
    date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")

    return "\n".join([
        f"SUPPRESSED — NO ACTION REQUIRED — {date_str}",
        f"KPI: {_kpi_label(row['kpi'])} | Severity: {row['severity']}",
        f"Movement: {movement}",
        "",
        "SUPPRESSION REASON",
        _safe(row["suppression_reason"], "Suppressed due to external market conditions."),
        "",
        "ROOT CAUSE",
        _safe(row["rca_narrative"]),
        "",
        "This anomaly has been automatically suppressed due to external market conditions.",
        "No escalation or investigation is warranted at this time.",
    ])


BODY_BUILDERS = {
    "ESCALATE":    _body_escalate,
    "INVESTIGATE": _body_investigate,
    "MONITOR":     _body_monitor,
    "SUPPRESSED":  _body_suppressed,
}


# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading intelligence_results.csv ...")
df = pd.read_csv(INPUT_CSV, parse_dates=["date"])
print(f"  Loaded {df.shape[0]} rows x {df.shape[1]} cols")
print()


# ── Build alert payloads ──────────────────────────────────────────────────────
print("Building alert payloads ...")

df["alert_subject"]    = df.apply(_build_subject, axis=1)
df["alert_body"]       = df.apply(lambda r: BODY_BUILDERS[r["layer4_priority_flag"]](r), axis=1)
df["audience"]         = df["layer4_priority_flag"].map(lambda f: ROUTING[f]["audience"])
df["delivery_channel"] = df["layer4_priority_flag"].map(lambda f: ROUTING[f]["channel"])
df["urgency_label"]    = df["layer4_priority_flag"].map(lambda f: ROUTING[f]["urgency"])

print(f"  Built {len(df)} alert payloads  ({df.shape[1]} total columns)")
print()


# ── Quality assertions ────────────────────────────────────────────────────────
print("Running quality assertions ...")
failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"  PASS  {label}")
    else:
        msg = f"  FAIL  {label}" + (f" — {detail}" if detail else "")
        print(msg)
        failures.append(label)


# T01 — Shape
check(
    "T01  Shape (181, 73)",
    df.shape == (181, 73),
    f"got {df.shape}",
)

# T02 — No null alert_subject
null_subj = df["alert_subject"].isna().sum()
check(
    "T02  No null alert_subject",
    null_subj == 0,
    f"{null_subj} nulls",
)

# T03 — No null alert_body
null_body = df["alert_body"].isna().sum()
check(
    "T03  No null alert_body",
    null_body == 0,
    f"{null_body} nulls",
)

# T04 — All subjects begin with '['
bad_fmt = (~df["alert_subject"].str.startswith("[")).sum()
check(
    "T04  All alert_subject values start with '['",
    bad_fmt == 0,
    f"{bad_fmt} malformed",
)

# T05 — ESCALATE routing
esc = df[df["layer4_priority_flag"] == "ESCALATE"]
check(
    "T05  ESCALATE: 15 rows | audience='Executive, Operations' | urgency='Immediate'",
    len(esc) == 15
    and (esc["audience"] == "Executive, Operations").all()
    and (esc["delivery_channel"] == "Slack + Email").all()
    and (esc["urgency_label"] == "Immediate").all(),
    f"n={len(esc)}",
)

# T06 — INVESTIGATE routing
inv = df[df["layer4_priority_flag"] == "INVESTIGATE"]
check(
    "T06  INVESTIGATE: 86 rows | audience='Operations, Analyst' | urgency='Daily'",
    len(inv) == 86
    and (inv["audience"] == "Operations, Analyst").all()
    and (inv["delivery_channel"] == "Email").all()
    and (inv["urgency_label"] == "Daily").all(),
    f"n={len(inv)}",
)

# T07 — MONITOR routing
mon = df[df["layer4_priority_flag"] == "MONITOR"]
check(
    "T07  MONITOR: 74 rows | audience='Analyst' | channel='Digest' | urgency='Weekly'",
    len(mon) == 74
    and (mon["audience"] == "Analyst").all()
    and (mon["delivery_channel"] == "Digest").all()
    and (mon["urgency_label"] == "Weekly").all(),
    f"n={len(mon)}",
)

# T08 — SUPPRESSED routing
sup = df[df["layer4_priority_flag"] == "SUPPRESSED"]
check(
    "T08  SUPPRESSED: 6 rows | audience='None' | channel='None' | urgency='Suppressed'",
    len(sup) == 6
    and (sup["audience"] == "None").all()
    and (sup["delivery_channel"] == "None").all()
    and (sup["urgency_label"] == "Suppressed").all(),
    f"n={len(sup)}",
)

# T09 — SUPPRESSED body contains 'NO ACTION REQUIRED'
sup_ok = sup["alert_body"].str.contains("NO ACTION REQUIRED").all()
check(
    "T09  All SUPPRESSED bodies contain 'NO ACTION REQUIRED'",
    sup_ok,
    f"missing in {(~sup['alert_body'].str.contains('NO ACTION REQUIRED')).sum()} rows",
)

# T10 — Black Friday spot-check: rank #1 ESCALATE row
bf = df[df["anomaly_id"] == "ANO-20241129-REV"]
check(
    "T10  ANO-20241129-REV subject starts '[ESCALATE]' and contains 'Priority #1'",
    len(bf) == 1
    and bf.iloc[0]["alert_subject"].startswith("[ESCALATE]")
    and "Priority #1" in bf.iloc[0]["alert_subject"],
    f"subject={bf.iloc[0]['alert_subject'] if len(bf) else 'n/a'}",
)

# T11 — All ESCALATE subjects contain 'Priority #'
esc_subj_ok = esc["alert_subject"].str.contains("Priority #").all()
check(
    "T11  All ESCALATE subjects contain 'Priority #'",
    esc_subj_ok,
    f"missing in {(~esc['alert_subject'].str.contains('Priority #')).sum()} rows",
)

# T12 — SQLite parity check (pre-write if table already exists)
conn = sqlite3.connect(DB_PATH)
tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()]
if "alert_payloads" in tables:
    db_n = conn.execute("SELECT COUNT(*) FROM alert_payloads").fetchone()[0]
    check("T12  SQLite alert_payloads = 181 rows", db_n == 181, f"got {db_n}")
else:
    print("  INFO  T12  alert_payloads table not yet in SQLite (will be written below)")
conn.close()

print()
if failures:
    print(f"FAIL — {len(failures)} assertion(s) failed: {failures}")
    sys.exit(1)
print("All passing assertions confirmed — writing output ...")
print()


# ── Write outputs ─────────────────────────────────────────────────────────────
df.to_csv(OUTPUT_CSV, index=False)

conn = sqlite3.connect(DB_PATH)
df.to_sql("alert_payloads", conn, if_exists="replace", index=False)
db_n = conn.execute("SELECT COUNT(*) FROM alert_payloads").fetchone()[0]
conn.close()

check("T12  SQLite alert_payloads = 181 rows", db_n == 181, f"got {db_n}")
if failures:
    sys.exit(1)

print()
print(f"  Saved {OUTPUT_CSV}")
print(f"  Saved SQLite table: alert_payloads")
print()


# ── Summary ───────────────────────────────────────────────────────────────────
print("=" * 68)
print("LAYER 5 STEP 5.1 — ALERT FORMATTER SUMMARY")
print("=" * 68)

print(f"\nOutput: alert_payloads.csv  ({df.shape[0]} rows x {df.shape[1]} cols)")

print("\nRouting distribution:")
for flag in ["ESCALATE", "INVESTIGATE", "MONITOR", "SUPPRESSED"]:
    n       = (df["layer4_priority_flag"] == flag).sum()
    routing = ROUTING[flag]
    print(
        f"  {flag:<12}  {n:>3}  "
        f"audience={routing['audience']:<30}  "
        f"channel={routing['channel']:<15}  "
        f"urgency={routing['urgency']}"
    )

print("\nSample alert subjects by routing flag:")
for flag in ["ESCALATE", "INVESTIGATE", "MONITOR", "SUPPRESSED"]:
    sample = df[df["layer4_priority_flag"] == flag].iloc[0]
    print(f"\n  [{flag}]")
    print(f"  Subject : {sample['alert_subject']}")

print()
print("Step 5.1 complete — alert_payloads.csv written (181 rows x 73 cols).")
print("Ready for Step 5.2 (Report Generator).")
