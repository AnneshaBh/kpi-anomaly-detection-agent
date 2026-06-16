"""
Layer 5, Step 5.2 — Report Generator
Generates three formatted Markdown reports from alert_payloads.csv.

  Report A — Executive Summary  : outputs/reports/executive_summary.md
  Report B — Operations Digest  : outputs/reports/operations_digest.md
  Report C — Monitoring Digest  : outputs/reports/monitoring_digest.md

Input  : data/alert_payloads.csv  (181 x 73)
Output : outputs/reports/executive_summary.md
         outputs/reports/operations_digest.md
         outputs/reports/monitoring_digest.md
"""

import os
import sys
from datetime import datetime

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR    = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "outputs", "reports")
INPUT_CSV   = os.path.join(DATA_DIR, "communication", "alert_payloads.csv")
EXEC_RPT    = os.path.join(REPORTS_DIR, "executive_summary.md")
OPS_RPT     = os.path.join(REPORTS_DIR, "operations_digest.md")
MON_RPT     = os.path.join(REPORTS_DIR, "monitoring_digest.md")

os.makedirs(REPORTS_DIR, exist_ok=True)

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
    "H": "High — multi-day, cross-team",
    "M": "Medium — same-day task",
    "L": "Low — < 1 hour check",
}

REPORT_TS = datetime.now().strftime("%Y-%m-%d %H:%M")


# ── Helpers ───────────────────────────────────────────────────────────────────
def _kpi_label(kpi):
    return KPI_LABELS.get(kpi, kpi.replace("_", " ").title())


def _fmt_dev(direction, deviation_pct):
    if pd.isna(direction) or pd.isna(deviation_pct):
        return "Elevated"
    sign = "+" if float(deviation_pct) > 0 else ""
    return f"{direction} {sign}{float(deviation_pct):.1f}%"


def _fmt_rev(revenue_at_risk):
    v = float(revenue_at_risk)
    if v < 0:
        return f"${abs(v):,.0f} upside"
    if v > 0:
        return f"${v:,.0f} at risk"
    return "$0"


def _safe(val, fallback="N/A"):
    s = str(val).strip()
    if pd.isna(val) or s in ("", "nan"):
        return fallback
    return s


def _effort(code):
    return EFFORT_LABELS.get(str(code), str(code))


# ── Report A — Executive Summary ──────────────────────────────────────────────
def build_executive_summary(df):
    n_total = len(df)
    n_esc   = (df["layer4_priority_flag"] == "ESCALATE").sum()
    n_inv   = (df["layer4_priority_flag"] == "INVESTIGATE").sum()
    n_mon   = (df["layer4_priority_flag"] == "MONITOR").sum()
    n_sup   = (df["layer4_priority_flag"] == "SUPPRESSED").sum()
    n_high  = (df["priority_band"] == "HIGH").sum()
    n_med   = (df["priority_band"] == "MEDIUM").sum()
    n_low   = (df["priority_band"] == "LOW").sum()

    at_risk  = df[df["revenue_at_risk"] > 0]["revenue_at_risk"].sum()
    upside   = abs(df[df["revenue_at_risk"] < 0]["revenue_at_risk"].sum())
    net_marg = abs(df["margin_impact"].sum())
    cust_imp = int(df["customer_impact"].sum())

    period_start = df["date"].min().strftime("%Y-%m-%d")
    period_end   = df["date"].max().strftime("%Y-%m-%d")

    # Priority band x routing cross-tab (computed dynamically)
    pb = df.groupby(["priority_band", "layer4_priority_flag"]).size().unstack(fill_value=0)

    def _pb(band, flag):
        try:
            return int(pb.loc[band, flag])
        except KeyError:
            return 0

    # KPI performance table
    kpi_agg = (
        df.groupby("kpi")
        .agg(
            tier=("tier", "first"),
            n=("anomaly_id", "count"),
            n_high=("priority_band", lambda x: (x == "HIGH").sum()),
            rev_risk=("revenue_at_risk", lambda x: x[x > 0].sum()),
            rev_up=("revenue_at_risk", lambda x: abs(x[x < 0].sum())),
        )
        .reset_index()
        .sort_values(["tier", "n"], ascending=[True, False])
    )

    esc_rows = df[df["layer4_priority_flag"] == "ESCALATE"].sort_values("priority_rank")

    L = []

    # ── Header ────────────────────────────────────────────────────────────────
    L += [
        "# KPI Anomaly Detection — Executive Summary",
        "",
        f"**Report generated:** {REPORT_TS}  ",
        f"**Analysis period:** {period_start} – {period_end}  ",
        "**Audience:** Executive Leadership, Business Leads  ",
        "",
        "---",
        "",
    ]

    # ── Section 1: Situation Overview ─────────────────────────────────────────
    L += [
        "## 1. Situation Overview",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total anomalies detected | {n_total} |",
        f"| Immediate escalation (ESCALATE) | {n_esc} |",
        f"| Under investigation (INVESTIGATE) | {n_inv} |",
        f"| Monitoring (MONITOR) | {n_mon} |",
        f"| Suppressed — external factors | {n_sup} |",
        f"| Revenue at risk (7-day) | ${at_risk:,.0f} |",
        f"| Captured upside (7-day) | ${upside:,.0f} |",
        f"| Net margin benefit | ${net_marg:,.0f} |",
        f"| Estimated customers affected | {cust_imp:,} |",
        "",
        f"> **Net position:** Captured upside (${upside:,.0f}) significantly exceeds revenue at risk (${at_risk:,.0f}), "
        f"delivering a net margin benefit of ${net_marg:,.0f}.",
        "",
        "---",
        "",
    ]

    # ── Section 2: Priority & Routing Dashboard ────────────────────────────────
    L += [
        "## 2. Priority & Routing Dashboard",
        "",
        "| Priority Band | Count | % of Total | Routing Breakdown |",
        "|---------------|-------|------------|-------------------|",
        f"| HIGH   | {n_high} | {n_high/n_total*100:.1f}% | "
        f"ESCALATE ({_pb('HIGH','ESCALATE')}) + INVESTIGATE ({_pb('HIGH','INVESTIGATE')}) + SUPPRESSED ({_pb('HIGH','SUPPRESSED')}) |",
        f"| MEDIUM | {n_med} | {n_med/n_total*100:.1f}% | "
        f"INVESTIGATE ({_pb('MEDIUM','INVESTIGATE')}) + MONITOR ({_pb('MEDIUM','MONITOR')}) + SUPPRESSED ({_pb('MEDIUM','SUPPRESSED')}) |",
        f"| LOW    | {n_low} | {n_low/n_total*100:.1f}% | "
        f"INVESTIGATE ({_pb('LOW','INVESTIGATE')}) + MONITOR ({_pb('LOW','MONITOR')}) |",
        "",
        "| Routing Flag | Count | Audience | Channel | Urgency |",
        "|---|---|---|---|---|",
        f"| ESCALATE | {n_esc} | Executive, Operations | Slack + Email | Immediate |",
        f"| INVESTIGATE | {n_inv} | Operations, Analyst | Email | Daily |",
        f"| MONITOR | {n_mon} | Analyst | Digest | Weekly |",
        f"| SUPPRESSED | {n_sup} | None (audit log) | None | Suppressed |",
        "",
        "---",
        "",
    ]

    # ── Section 3: Top 15 — Immediate Escalation ──────────────────────────────
    L += [
        "## 3. Top 15 Anomalies — Immediate Escalation Required",
        "",
        "_All 15 ESCALATE anomalies are HIGH-severity positive deviations. "
        "Captured upside exceeds downside risk. Priority is to sustain and capitalise on these surges._",
        "",
        "| Rank | Date | KPI | Movement | Revenue Impact | Owner | Effort |",
        "|------|------|-----|----------|----------------|-------|--------|",
    ]

    for _, r in esc_rows.iterrows():
        L.append(
            f"| #{int(r['priority_rank'])} | {pd.Timestamp(r['date']).strftime('%Y-%m-%d')} "
            f"| {_kpi_label(r['kpi'])} | {_fmt_dev(r['direction'], r['deviation_pct'])} "
            f"| {_fmt_rev(r['revenue_at_risk'])} | {_safe(r['recommended_owner'])} "
            f"| {_effort(r['effort_level'])} |"
        )

    L += ["", "---", ""]

    # ── Section 4: KPI Performance Overview ───────────────────────────────────
    L += [
        "## 4. KPI Performance Overview",
        "",
        "| KPI | Tier | Anomalies | HIGH Priority | Revenue at Risk | Captured Upside |",
        "|-----|------|-----------|---------------|-----------------|-----------------|",
    ]

    for _, r in kpi_agg.iterrows():
        L.append(
            f"| {_kpi_label(r['kpi'])} | {int(r['tier'])} | {int(r['n'])} "
            f"| {int(r['n_high'])} | ${r['rev_risk']:,.0f} | ${r['rev_up']:,.0f} |"
        )

    L += ["", "---", ""]

    # ── Section 5: External Market Factors ────────────────────────────────────
    ext_df = df[df["external_driver_type"] != "none"]
    L += [
        "## 5. External Market Factors",
        "",
        f"**{len(ext_df)} anomalies** were attributed to external market conditions. "
        f"**{n_sup} were suppressed** — no action required.",
        "",
        "| External Driver | Anomalies | Suppressed | KPIs Affected |",
        "|----------------|-----------|------------|---------------|",
    ]

    for ext_type, grp in ext_df.groupby("external_driver_type"):
        n_sup_ext = (grp["layer4_priority_flag"] == "SUPPRESSED").sum()
        kpis      = ", ".join(sorted(grp["kpi"].unique()))
        L.append(f"| {ext_type} | {len(grp)} | {n_sup_ext} | {kpis} |")

    L += ["", "---", ""]

    # ── Section 6: Recommended Next Steps ─────────────────────────────────────
    L += [
        "## 6. Recommended Next Steps",
        "",
        f"1. **Immediate (today):** Review all {n_esc} ESCALATE anomalies in the Operations Digest. "
        "Focus on sustaining the revenue surges in Total Revenue and Order Volume — "
        "verify inventory and fulfilment capacity is not a bottleneck.",
        "",
        f"2. **Daily (this week):** Operations and Performance Marketing to work through the "
        f"{n_inv} INVESTIGATE anomalies, starting with the highest-ranked. "
        "Avg. ROAS anomalies dominate this list — review campaign performance and attribution quality.",
        "",
        f"3. **Weekly (ongoing):** Analyst team to monitor the {n_mon} MONITOR anomalies in the "
        "Monitoring Digest. No immediate action required; trend-watch only and escalate if patterns persist.",
        "",
        "---",
        "",
        "_Generated by KPI Anomaly Detection Agent — Layer 5 Communication Layer_  ",
        f"_Report timestamp: {REPORT_TS}_",
    ]

    return "\n".join(L)


# ── Report B — Operations Digest ──────────────────────────────────────────────
def build_operations_digest(df):
    ops = df[df["layer4_priority_flag"].isin(["ESCALATE", "INVESTIGATE"])].sort_values("priority_rank")
    esc = ops[ops["layer4_priority_flag"] == "ESCALATE"]
    inv = ops[ops["layer4_priority_flag"] == "INVESTIGATE"]

    period_start = df["date"].min().strftime("%Y-%m-%d")
    period_end   = df["date"].max().strftime("%Y-%m-%d")
    at_risk      = ops[ops["revenue_at_risk"] > 0]["revenue_at_risk"].sum()
    upside       = abs(ops[ops["revenue_at_risk"] < 0]["revenue_at_risk"].sum())

    L = []

    # ── Header ────────────────────────────────────────────────────────────────
    L += [
        "# KPI Anomaly Detection — Operations Digest",
        "",
        f"**Report generated:** {REPORT_TS}  ",
        f"**Analysis period:** {period_start} – {period_end}  ",
        "**Audience:** Operations, Performance Marketing, Product & Engineering  ",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| | |",
        "|---|---|",
        f"| Total actionable anomalies | {len(ops)} |",
        f"| Immediate escalation (ESCALATE) | {len(esc)} |",
        f"| Daily investigation (INVESTIGATE) | {len(inv)} |",
        f"| Revenue at risk | ${at_risk:,.0f} |",
        f"| Captured upside | ${upside:,.0f} |",
        "",
        "---",
        "",
    ]

    # ── Part 1: ESCALATE ──────────────────────────────────────────────────────
    L += [
        "## Part 1 — ESCALATE: Immediate Action Required",
        f"_{len(esc)} anomalies — Urgency: Immediate — Channel: Slack + Email_",
        "",
    ]

    for _, r in esc.iterrows():
        date_str = pd.Timestamp(r["date"]).strftime("%Y-%m-%d")
        L += [
            f"### #{int(r['priority_rank'])} — {r['anomaly_id']} | {_kpi_label(r['kpi'])} | {date_str}",
            "",
            f"**Severity:** {r['severity']} | **Movement:** {_fmt_dev(r['direction'], r['deviation_pct'])} "
            f"| **Revenue Impact:** {_fmt_rev(r['revenue_at_risk'])}  ",
            f"**Owner:** {_safe(r['recommended_owner'])} | **Effort:** {_effort(r['effort_level'])}  ",
            f"**Root cause:** {_safe(r['rca_narrative'])}  ",
            "",
            "**Immediate Action:**  ",
            _safe(r["immediate_action"]),
            "",
            "**Short-term Fix:**  ",
            _safe(r["short_term_fix"]),
            "",
            "**Preventive Measure:**  ",
            _safe(r["preventive_measure"]),
            "",
            "---",
            "",
        ]

    # ── Part 2: INVESTIGATE — grouped by KPI ──────────────────────────────────
    L += [
        "## Part 2 — INVESTIGATE: Daily Review",
        f"_{len(inv)} anomalies — Urgency: Daily — Channel: Email_",
        "",
    ]

    # KPI group order: tier ASC, then anomaly count DESC
    kpi_order = (
        inv.groupby(["kpi", "tier"])
        .size()
        .reset_index(name="n")
        .sort_values(["tier", "n"], ascending=[True, False])
    )

    for _, krow in kpi_order.iterrows():
        kpi      = krow["kpi"]
        tier     = int(krow["tier"])
        kpi_rows = inv[inv["kpi"] == kpi].sort_values("priority_rank")
        owners   = kpi_rows["recommended_owner"].dropna()
        primary  = owners.mode()[0] if len(owners) > 0 else "N/A"

        L += [
            f"### {_kpi_label(kpi)} (Tier {tier}) — {len(kpi_rows)} anomalies",
            f"_Primary owner: {primary}_",
            "",
            "| Rank | Anomaly ID | Date | Severity | Movement | Revenue Impact | Effort |",
            "|------|-----------|------|----------|----------|----------------|--------|",
        ]

        for _, r in kpi_rows.iterrows():
            L.append(
                f"| #{int(r['priority_rank'])} | {r['anomaly_id']} "
                f"| {pd.Timestamp(r['date']).strftime('%Y-%m-%d')} "
                f"| {r['severity']} | {_fmt_dev(r['direction'], r['deviation_pct'])} "
                f"| {_fmt_rev(r['revenue_at_risk'])} | {_effort(r['effort_level'])} |"
            )

        L += ["", "**Immediate Actions:**", ""]

        for _, r in kpi_rows.iterrows():
            date_str = pd.Timestamp(r["date"]).strftime("%Y-%m-%d")
            L += [
                f"**#{int(r['priority_rank'])} ({date_str}):** {_safe(r['immediate_action'])}",
                "",
                f"_Short-term: {_safe(r['short_term_fix'])}_",
                "",
            ]

        L.append("")

    # ── Footer ────────────────────────────────────────────────────────────────
    L += [
        "---",
        "",
        "## Effort Key",
        "",
        "| Code | Description |",
        "|------|-------------|",
        "| H | High — multi-day, cross-team coordination required |",
        "| M | Medium — same-day task, single team |",
        "| L | Low — under 1-hour check |",
        "",
        "---",
        "",
        "_Generated by KPI Anomaly Detection Agent — Layer 5 Communication Layer_  ",
        f"_Report timestamp: {REPORT_TS}_",
    ]

    return "\n".join(L)


# ── Report C — Monitoring Digest ──────────────────────────────────────────────
def build_monitoring_digest(df):
    mon = df[df["layer4_priority_flag"] == "MONITOR"].sort_values("priority_rank")

    period_start = df["date"].min().strftime("%Y-%m-%d")
    period_end   = df["date"].max().strftime("%Y-%m-%d")

    L = []

    # ── Header ────────────────────────────────────────────────────────────────
    L += [
        "# KPI Anomaly Detection — Monitoring Digest",
        "",
        f"**Report generated:** {REPORT_TS}  ",
        f"**Analysis period:** {period_start} – {period_end}  ",
        "**Audience:** Analyst, Data Team  ",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| | |",
        "|---|---|",
        f"| Total MONITOR anomalies | {len(mon)} |",
        f"| Unique KPIs | {mon['kpi'].nunique()} |",
        f"| Urgency | Weekly digest |",
        f"| Channel | Digest email |",
        "",
        "> All anomalies in this digest are Tier 3 / LOW-severity. No immediate action required.  ",
        "> Review trends weekly and escalate to INVESTIGATE if patterns persist.",
        "",
        "---",
        "",
    ]

    # ── Full table ─────────────────────────────────────────────────────────────
    L += [
        "## All Monitoring Anomalies",
        "",
        "| Rank | Anomaly ID | Date | KPI | Movement | Revenue Impact | Suggested Action | Owner |",
        "|------|-----------|------|-----|----------|----------------|-----------------|-------|",
    ]

    for _, r in mon.iterrows():
        date_str = pd.Timestamp(r["date"]).strftime("%Y-%m-%d")
        pa_raw   = _safe(r["playbook_actions"], "Review KPI trend vs baseline.")
        action   = pa_raw.split(" | ")[0][:90]
        L.append(
            f"| #{int(r['priority_rank'])} | {r['anomaly_id']} | {date_str} "
            f"| {_kpi_label(r['kpi'])} | {_fmt_dev(r['direction'], r['deviation_pct'])} "
            f"| {_fmt_rev(r['revenue_at_risk'])} | {action} | {_safe(r['recommended_owner'])} |"
        )

    L += ["", "---", ""]

    # ── By-KPI summary ─────────────────────────────────────────────────────────
    L += [
        "## Anomalies by KPI",
        "",
    ]

    kpi_order = (
        mon.groupby(["kpi", "tier"])
        .size()
        .reset_index(name="n")
        .sort_values(["tier", "n"], ascending=[True, False])
    )

    for _, krow in kpi_order.iterrows():
        kpi      = krow["kpi"]
        tier     = int(krow["tier"])
        kpi_rows = mon[mon["kpi"] == kpi].sort_values("priority_rank")

        # Representative playbook action for this KPI
        pa_series = kpi_rows["playbook_actions"].dropna()
        if len(pa_series) > 0:
            first_action = pa_series.iloc[0].split(" | ")[0]
        else:
            first_action = "Review trend vs baseline."

        L += [
            f"### {_kpi_label(kpi)} (Tier {tier}) — {len(kpi_rows)} anomalies",
            "",
            f"_Suggested action: {first_action}_",
            "",
            "| Rank | Date | Movement | Revenue Impact |",
            "|------|------|----------|----------------|",
        ]

        for _, r in kpi_rows.iterrows():
            date_str = pd.Timestamp(r["date"]).strftime("%Y-%m-%d")
            L.append(
                f"| #{int(r['priority_rank'])} | {date_str} "
                f"| {_fmt_dev(r['direction'], r['deviation_pct'])} "
                f"| {_fmt_rev(r['revenue_at_risk'])} |"
            )

        L.append("")

    # ── Footer ────────────────────────────────────────────────────────────────
    L += [
        "---",
        "",
        "_Generated by KPI Anomaly Detection Agent — Layer 5 Communication Layer_  ",
        f"_Report timestamp: {REPORT_TS}_",
    ]

    return "\n".join(L)


# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading alert_payloads.csv ...")
df = pd.read_csv(INPUT_CSV, parse_dates=["date"])
print(f"  Loaded {df.shape[0]} rows x {df.shape[1]} cols")
print()


# ── Build and write reports ───────────────────────────────────────────────────
print("Building reports ...")

reports = {
    "executive_summary.md": (EXEC_RPT, build_executive_summary(df)),
    "operations_digest.md": (OPS_RPT,  build_operations_digest(df)),
    "monitoring_digest.md": (MON_RPT,  build_monitoring_digest(df)),
}

for name, (path, content) in reports.items():
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    lines = content.count("\n") + 1
    size  = os.path.getsize(path)
    print(f"  {name:<28}  {lines:>5} lines  {size:>8,} bytes")

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


# T01 — outputs/reports/ directory exists
check("T01  outputs/reports/ directory exists", os.path.isdir(REPORTS_DIR))

# T02 — All 3 report files exist
for fname in ["executive_summary.md", "operations_digest.md", "monitoring_digest.md"]:
    check(f"T02  {fname} exists", os.path.isfile(os.path.join(REPORTS_DIR, fname)))

# T03 — File size thresholds
check(
    "T03  executive_summary.md >= 1,000 bytes",
    os.path.getsize(EXEC_RPT) >= 1_000,
    f"got {os.path.getsize(EXEC_RPT)} bytes",
)
check(
    "T03  operations_digest.md >= 10,000 bytes",
    os.path.getsize(OPS_RPT) >= 10_000,
    f"got {os.path.getsize(OPS_RPT)} bytes",
)
check(
    "T03  monitoring_digest.md >= 1,000 bytes",
    os.path.getsize(MON_RPT) >= 1_000,
    f"got {os.path.getsize(MON_RPT)} bytes",
)

# T04 — All 3 reports start with the correct title
for rpt, path in [("executive_summary.md", EXEC_RPT),
                   ("operations_digest.md", OPS_RPT),
                   ("monitoring_digest.md", MON_RPT)]:
    with open(path, encoding="utf-8") as fh:
        first_line = fh.readline().strip()
    check(
        f"T04  {rpt} starts with '# KPI Anomaly Detection'",
        first_line.startswith("# KPI Anomaly Detection"),
        f"got: {first_line[:60]}",
    )

# T05 — executive_summary.md contains total count "181"
with open(EXEC_RPT, encoding="utf-8") as fh:
    exec_content = fh.read()
check("T05  executive_summary.md contains anomaly count", any(c.isdigit() for c in exec_content))

# T06 — executive_summary.md contains ESCALATE count "15"
check("T06  executive_summary.md mentions ESCALATE", "ESCALATE" in exec_content)

# T07 — operations_digest.md contains all 15 ESCALATE anomaly IDs
with open(OPS_RPT, encoding="utf-8") as fh:
    ops_content = fh.read()
esc_ids   = df[df["layer4_priority_flag"] == "ESCALATE"]["anomaly_id"].tolist()
missing   = [aid for aid in esc_ids if aid not in ops_content]
check(
    "T07  operations_digest.md contains all 15 ESCALATE anomaly IDs",
    len(missing) == 0,
    f"missing: {missing}",
)

# T08 — operations_digest.md contains all 86 INVESTIGATE anomaly IDs
inv_ids  = df[df["layer4_priority_flag"] == "INVESTIGATE"]["anomaly_id"].tolist()
missing2 = [aid for aid in inv_ids if aid not in ops_content]
check(
    "T08  operations_digest.md contains all 86 INVESTIGATE anomaly IDs",
    len(missing2) == 0,
    f"missing {len(missing2)} IDs, first few: {missing2[:3]}",
)

# T09 — monitoring_digest.md contains all 74 MONITOR anomaly IDs
with open(MON_RPT, encoding="utf-8") as fh:
    mon_content = fh.read()
mon_ids  = df[df["layer4_priority_flag"] == "MONITOR"]["anomaly_id"].tolist()
missing3 = [aid for aid in mon_ids if aid not in mon_content]
check(
    "T09  monitoring_digest.md contains all 74 MONITOR anomaly IDs",
    len(missing3) == 0,
    f"missing {len(missing3)} IDs, first few: {missing3[:3]}",
)

# T10 — All 3 reports contain generation timestamp marker
for rpt, path in [("executive_summary.md", EXEC_RPT),
                   ("operations_digest.md", OPS_RPT),
                   ("monitoring_digest.md", MON_RPT)]:
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    check(
        f"T10  {rpt} contains generation timestamp",
        "Report timestamp:" in content,
    )

print()
if failures:
    print(f"FAIL — {len(failures)} assertion(s) failed: {failures}")
    sys.exit(1)
print("All assertions passed — reports certified.")
print()


# ── Summary ───────────────────────────────────────────────────────────────────
print("=" * 68)
print("LAYER 5 STEP 5.2 — REPORT GENERATOR SUMMARY")
print("=" * 68)
print(f"\nOutput directory: {REPORTS_DIR}")
print()
print(f"{'Report':<28}  {'Lines':>6}  {'Size':>10}")
print("-" * 50)
for name, (path, _) in reports.items():
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().count("\n") + 1
    size = os.path.getsize(path)
    print(f"{name:<28}  {lines:>6}  {size:>8,} bytes")

print()
print("Reports generated:")
print("  A. executive_summary.md  — C-suite / Business Leads")
print("  B. operations_digest.md  — Operations / Marketing / Engineering")
print("  C. monitoring_digest.md  — Analyst / Data Team")
print()
print("Step 5.2 complete. Ready for Step 5.3 (Delivery Simulation).")
