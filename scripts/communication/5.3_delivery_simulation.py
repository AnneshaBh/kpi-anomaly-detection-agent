"""
Layer 5, Step 5.3 — Delivery Simulation
Simulates routing every alert through its designated communication channel.
No external APIs are called — this is a pure structured simulation that mirrors
how a real notification system would behave.

Routing rules (counts vary by run -- good-direction/positive anomalies
are always SUPPRESSED regardless of severity, so ESCALATE can be empty)
  ESCALATE    -> Slack #kpi-alerts + Email exec-team DL    -> status: SENT       (same-day 09:30)
  INVESTIGATE -> Email ops-team DL (daily batch at 08:00)  -> status: QUEUED     (next business day)
  MONITOR     -> Email analytics-team DL (weekly digest)   -> status: SCHEDULED  (next Monday 09:00)
  SUPPRESSED  -> Audit log only                            -> status: SUPPRESSED (same-day, no send)

Input  : data/alert_payloads.csv          (181 x 73)
Output : data/delivery_log.csv            (181 x 13)
         outputs/delivery_summary.txt
         SQLite table: delivery_log
"""

import os
import sqlite3
import sys
from datetime import timedelta
from datetime import datetime

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR     = os.path.join(BASE_DIR, "data")
OUTPUTS_DIR  = os.path.join(BASE_DIR, "outputs")
DB_PATH      = os.path.join(DATA_DIR, "db", "kpi_anomaly_detection.db")
INPUT_CSV    = os.path.join(DATA_DIR, "communication", "alert_payloads.csv")
OUTPUT_CSV   = os.path.join(DATA_DIR, "communication", "delivery_log.csv")
SUMMARY_TXT  = os.path.join(OUTPUTS_DIR, "delivery_summary.txt")

os.makedirs(OUTPUTS_DIR, exist_ok=True)

# ── Routing config ─────────────────────────────────────────────────────────────
# recipient: simulated distribution lists / channel endpoints
RECIPIENTS = {
    "ESCALATE":    "exec-team-dl@company.com; ops-team-dl@company.com",
    "INVESTIGATE": "ops-team-dl@company.com; analytics-team-dl@company.com",
    "MONITOR":     "analytics-team-dl@company.com",
    "SUPPRESSED":  "audit-log@company.com",
}

STATUSES = {
    "ESCALATE":    "SENT",
    "INVESTIGATE": "QUEUED",
    "MONITOR":     "SCHEDULED",
    "SUPPRESSED":  "SUPPRESSED",
}

GENERATED_TS = datetime.now().strftime("%Y-%m-%d %H:%M")


# ── Timestamp helpers ─────────────────────────────────────────────────────────
def _next_business_day(ts):
    """Return the next calendar day that is Mon-Fri."""
    nxt = ts + timedelta(days=1)
    while nxt.weekday() >= 5:          # 5 = Saturday, 6 = Sunday
        nxt += timedelta(days=1)
    return nxt


def _next_monday(ts):
    """Return the next Monday strictly after ts (if ts is already Monday, still next week)."""
    days_ahead = (7 - ts.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return ts + timedelta(days=days_ahead)


def _sent_at(flag, date):
    ts = pd.Timestamp(date)
    if flag == "ESCALATE":
        return ts.replace(hour=9, minute=30, second=0, microsecond=0)
    if flag == "INVESTIGATE":
        return _next_business_day(ts).replace(hour=8, minute=0, second=0, microsecond=0)
    if flag == "MONITOR":
        return _next_monday(ts).replace(hour=9, minute=0, second=0, microsecond=0)
    # SUPPRESSED — logged at 09:00 same day, no send
    return ts.replace(hour=9, minute=0, second=0, microsecond=0)


# ── Delivery note builder ─────────────────────────────────────────────────────
def _delivery_note(row, sent_at):
    flag = row["layer4_priority_flag"]
    if flag == "ESCALATE":
        return (
            f"Sent to Slack #kpi-alerts and exec-team-dl@company.com. "
            f"Priority #{int(row['priority_rank'])}. Sent at {sent_at.strftime('%Y-%m-%d %H:%M')}."
        )
    if flag == "INVESTIGATE":
        return (
            f"Queued for daily digest email to ops-team-dl@company.com "
            f"on {sent_at.strftime('%Y-%m-%d')} at {sent_at.strftime('%H:%M')}."
        )
    if flag == "MONITOR":
        return (
            f"Scheduled for weekly digest email to analytics-team-dl@company.com "
            f"on {sent_at.strftime('%A %Y-%m-%d')} at {sent_at.strftime('%H:%M')}."
        )
    # SUPPRESSED
    ext = str(row.get("external_driver_type", "external factor"))
    reason = str(row.get("suppression_reason", "")).strip()
    return (
        f"Logged to audit log only. No notification sent. "
        f"External driver: {ext}. {reason}"
    )


# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading alert_payloads.csv ...")
df = pd.read_csv(INPUT_CSV, parse_dates=["date"])
print(f"  Loaded {df.shape[0]} rows x {df.shape[1]} cols")
print()


# ── Build delivery log ────────────────────────────────────────────────────────
print("Simulating deliveries ...")

# Assign message IDs: MSG-{FLAG_PREFIX}-{NNNN} scoped per flag, ordered by priority_rank
df_sorted = df.sort_values(["layer4_priority_flag", "priority_rank"]).copy()
flag_seq  = {}
msg_ids   = []
for flag in df_sorted["layer4_priority_flag"]:
    prefix = flag[:3].upper()
    flag_seq[prefix] = flag_seq.get(prefix, 0) + 1
    msg_ids.append(f"MSG-{prefix}-{flag_seq[prefix]:04d}")
df_sorted["message_id"] = msg_ids

# Compute sent_at and delivery metadata
df_sorted["sent_at"]         = df_sorted.apply(lambda r: _sent_at(r["layer4_priority_flag"], r["date"]), axis=1)
df_sorted["delivery_status"] = df_sorted["layer4_priority_flag"].map(STATUSES)
df_sorted["recipient"]       = df_sorted["layer4_priority_flag"].map(RECIPIENTS)
df_sorted["delivery_note"]   = df_sorted.apply(lambda r: _delivery_note(r, r["sent_at"]), axis=1)

# Build the output table with 13 columns (restore original sort order by priority_rank)
LOG_COLS = [
    "anomaly_id", "date", "kpi", "layer4_priority_flag",
    "urgency_label", "delivery_channel", "audience",
    "recipient", "alert_subject", "message_id",
    "sent_at", "delivery_status", "delivery_note",
]
log = (
    df_sorted[LOG_COLS + ["priority_rank"]]
    .sort_values("priority_rank")
    .drop(columns="priority_rank")
    .reset_index(drop=True)
)

print(f"  Simulated {len(log)} deliveries  ({log.shape[1]} columns)")
print()

# Status counts
for status, n in log["delivery_status"].value_counts().items():
    print(f"    {status:<12}  {n:>3}")
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
    "T01  Shape (n, 13)",
    log.shape[0] > 0 and log.shape[1] == 13,
    f"got {log.shape}",
)

# T02 — delivery_status values are valid
valid_statuses = {"SENT", "QUEUED", "SCHEDULED", "SUPPRESSED"}
found_statuses = set(log["delivery_status"].unique())
check(
    "T02  delivery_status only contains SENT / QUEUED / SCHEDULED / SUPPRESSED",
    found_statuses.issubset(valid_statuses),
    f"unexpected: {found_statuses - valid_statuses}",
)

# T03 — ESCALATE → SENT (can legitimately be 0 rows -- good-direction
# anomalies are always suppressed, regardless of severity)
esc = log[log["layer4_priority_flag"] == "ESCALATE"]
check(
    "T03  ESCALATE rows, all SENT",
    (esc["delivery_status"] == "SENT").all(),
    f"n={len(esc)}  non-SENT={( esc['delivery_status'] != 'SENT').sum()}",
)

# T04 — INVESTIGATE → QUEUED (86 rows)
inv = log[log["layer4_priority_flag"] == "INVESTIGATE"]
check(
    "T04  INVESTIGATE rows, all QUEUED",
    len(inv) > 0 and (inv["delivery_status"] == "QUEUED").all(),
    f"n={len(inv)}  non-QUEUED={( inv['delivery_status'] != 'QUEUED').sum()}",
)

# T05 — MONITOR → SCHEDULED (74 rows)
mon = log[log["layer4_priority_flag"] == "MONITOR"]
check(
    "T05  MONITOR rows, all SCHEDULED",
    len(mon) > 0 and (mon["delivery_status"] == "SCHEDULED").all(),
    f"n={len(mon)}  non-SCHEDULED={( mon['delivery_status'] != 'SCHEDULED').sum()}",
)

# T06 — SUPPRESSED → SUPPRESSED (6 rows)
sup = log[log["layer4_priority_flag"] == "SUPPRESSED"]
check(
    "T06  SUPPRESSED rows, all SUPPRESSED status",
    len(sup) >= 0 and (sup["delivery_status"] == "SUPPRESSED").all(),
    f"n={len(sup)}  non-SUPPRESSED={( sup['delivery_status'] != 'SUPPRESSED').sum()}",
)

# T07 — No null sent_at
null_sent = log["sent_at"].isna().sum()
check("T07  No null sent_at", null_sent == 0, f"{null_sent} nulls")

# T08 — message_id non-null and all unique
null_msg  = log["message_id"].isna().sum()
uniq_msg  = log["message_id"].nunique()
check(
    "T08  message_id: 0 nulls and all unique",
    null_msg == 0 and uniq_msg == len(log),
    f"nulls={null_msg}  unique={uniq_msg}",
)

# T09 — Black Friday spot-check: positive change -> SUPPRESSED, not sent
bf = log[log["anomaly_id"] == "ANO-20241129-REV"]
check(
    "T09  ANO-20241129-REV: delivery_status=SUPPRESSED (positive change, not sent)",
    len(bf) == 1
    and bf.iloc[0]["delivery_status"] == "SUPPRESSED"
    and pd.Timestamp(bf.iloc[0]["sent_at"]).date() == pd.Timestamp("2024-11-29").date(),
    f"status={bf.iloc[0]['delivery_status'] if len(bf) else 'n/a'}  "
    f"sent_at={bf.iloc[0]['sent_at'] if len(bf) else 'n/a'}",
)

# T10 — All SENT rows: sent_at is on the same calendar date as the anomaly
esc_same_day = (
    pd.to_datetime(esc["sent_at"]).dt.date == pd.to_datetime(esc["date"]).dt.date
).all()
check(
    "T10  All SENT (ESCALATE) rows: sent_at is same calendar day as anomaly date",
    esc_same_day,
    f"mismatches={(~(pd.to_datetime(esc['sent_at']).dt.date == pd.to_datetime(esc['date']).dt.date)).sum()}",
)

# T11 — All SUPPRESSED rows have delivery_channel = "None" / NaN
# pandas re-reads the string "None" written by 5.1 as NaN on CSV round-trip
sup_ch_ok = (sup["delivery_channel"].isna() | (sup["delivery_channel"] == "None")).all()
check(
    "T11  All SUPPRESSED rows have delivery_channel = 'None' (or NaN after CSV round-trip)",
    sup_ch_ok,
    f"unexpected non-None values={sup['delivery_channel'].dropna().tolist()}",
)

# T12 — MONITOR sent_at are all Mondays at 09:00
mon_monday = (pd.to_datetime(mon["sent_at"]).dt.weekday == 0).all()
mon_hour   = (pd.to_datetime(mon["sent_at"]).dt.hour == 9).all()
check(
    "T12  All SCHEDULED (MONITOR) sent_at fall on a Monday at 09:00",
    mon_monday and mon_hour,
    f"non-Monday={( ~(pd.to_datetime(mon['sent_at']).dt.weekday==0)).sum()}  "
    f"non-09h={( ~(pd.to_datetime(mon['sent_at']).dt.hour==9)).sum()}",
)

# T13 — INVESTIGATE sent_at are all weekdays (Mon-Fri)
inv_weekday = (pd.to_datetime(inv["sent_at"]).dt.weekday < 5).all()
check(
    "T13  All QUEUED (INVESTIGATE) sent_at fall on a weekday",
    inv_weekday,
    f"weekend sends={(~(pd.to_datetime(inv['sent_at']).dt.weekday < 5)).sum()}",
)

print()
if failures:
    print(f"FAIL — {len(failures)} assertion(s) failed: {failures}")
    sys.exit(1)
print("All assertions passed — writing output ...")
print()


# ── Write delivery_log.csv + SQLite ───────────────────────────────────────────
log.to_csv(OUTPUT_CSV, index=False)

conn = sqlite3.connect(DB_PATH)
log.to_sql("delivery_log", conn, if_exists="replace", index=False)
db_n = conn.execute("SELECT COUNT(*) FROM delivery_log").fetchone()[0]
conn.close()

check("SQLite delivery_log row count matches", db_n == len(log), f"got {db_n}")
if failures:
    sys.exit(1)


# ── Write delivery_summary.txt ────────────────────────────────────────────────
sent_rows  = log[log["delivery_status"] == "SENT"].sort_values("sent_at")
queued_rng = (
    pd.to_datetime(inv["sent_at"]).min().strftime("%Y-%m-%d"),
    pd.to_datetime(inv["sent_at"]).max().strftime("%Y-%m-%d"),
)
sched_rng  = (
    pd.to_datetime(mon["sent_at"]).min().strftime("%Y-%m-%d"),
    pd.to_datetime(mon["sent_at"]).max().strftime("%Y-%m-%d"),
)

summary_lines = [
    "=" * 68,
    "KPI ANOMALY DETECTION — DELIVERY SIMULATION SUMMARY",
    "=" * 68,
    f"Generated : {GENERATED_TS}",
    "",
    f"TOTAL ALERTS PROCESSED : {len(log)}",
    "",
    "-" * 68,
    "ROUTING & DELIVERY SUMMARY",
    "-" * 68,
    f"  {'Flag':<14}  {'Count':>5}  {'Status':<12}  {'Channel':<20}  Timing",
    f"  {'-'*13}  {'-'*5}  {'-'*11}  {'-'*20}  {'-'*30}",
    f"  {'ESCALATE':<14}  {len(esc):>5}  {'SENT':<12}  {'Slack + Email':<20}  Same-day at 09:30",
    f"  {'INVESTIGATE':<14}  {len(inv):>5}  {'QUEUED':<12}  {'Email':<20}  Next business day at 08:00",
    f"  {'MONITOR':<14}  {len(mon):>5}  {'SCHEDULED':<12}  {'Digest':<20}  Next Monday at 09:00",
    f"  {'SUPPRESSED':<14}  {len(sup):>5}  {'SUPPRESSED':<12}  {'None (Audit log)':<20}  Logged same-day at 09:00",
    "",
    "-" * 68,
    "SIMULATED TIMELINE",
    "-" * 68,
    f"  SENT      window : {sent_rows['sent_at'].min()} – {sent_rows['sent_at'].max()}",
    f"  QUEUED    window : {queued_rng[0]} 08:00 – {queued_rng[1]} 08:00",
    f"  SCHEDULED window : {sched_rng[0]} 09:00 – {sched_rng[1]} 09:00",
    "",
    "-" * 68,
    "IMMEDIATE ESCALATIONS (SENT)",
    "-" * 68,
]

for _, r in sent_rows.iterrows():
    summary_lines.append(
        f"  {str(r['sent_at'])[:16]}  {r['anomaly_id']:<22}  {r['kpi']:<22}  {r['message_id']}"
    )

summary_lines += [
    "",
    "-" * 68,
    "SUPPRESSED ALERTS (AUDIT LOG ONLY)",
    "-" * 68,
]
for _, r in sup.iterrows():
    summary_lines.append(
        f"  {r['anomaly_id']:<22}  {r['kpi']:<12}  {r['delivery_note'][:80]}"
    )

summary_lines += [
    "",
    "-" * 68,
    "RECIPIENT DISTRIBUTION LISTS",
    "-" * 68,
    f"  exec-team-dl@company.com         ← {len(esc):>3}  ESCALATE alerts (immediate)",
    f"  ops-team-dl@company.com          ← {len(esc):>3}  ESCALATE + {len(inv):>3}  INVESTIGATE alerts",
    f"  analytics-team-dl@company.com    ← {len(inv):>3}  INVESTIGATE + {len(mon):>3}  MONITOR alerts",
    f"  audit-log@company.com            ← {len(sup):>3}  SUPPRESSED alerts (no action)",
    "",
    "=" * 68,
    f"Step 5.3 complete — delivery_log.csv written ({len(log)} rows x 13 cols).",
    "=" * 68,
]

summary_text = "\n".join(summary_lines)
with open(SUMMARY_TXT, "w", encoding="utf-8") as fh:
    fh.write(summary_text)


# ── Final assertion: summary file exists and non-empty ────────────────────────
check(
    "delivery_summary.txt exists and non-empty",
    os.path.isfile(SUMMARY_TXT) and os.path.getsize(SUMMARY_TXT) > 0,
    f"size={os.path.getsize(SUMMARY_TXT) if os.path.isfile(SUMMARY_TXT) else 'missing'}",
)
if failures:
    sys.exit(1)


# ── Summary ───────────────────────────────────────────────────────────────────
print()
print(f"  Saved {OUTPUT_CSV}")
print(f"  Saved SQLite table: delivery_log")
print(f"  Saved {SUMMARY_TXT}")
print()
print("=" * 68)
print("LAYER 5 STEP 5.3 — DELIVERY SIMULATION SUMMARY")
print("=" * 68)
print(f"\nOutput: delivery_log.csv  ({log.shape[0]} rows x {log.shape[1]} cols)")
print()
print(f"  {'Flag':<14}  {'N':>4}  {'Status':<12}  Channel")
print(f"  {'-'*13}  {'-'*4}  {'-'*11}  {'-'*25}")
for flag, status, channel in [
    ("ESCALATE",    "SENT",       "Slack + Email"),
    ("INVESTIGATE", "QUEUED",     "Email (daily digest)"),
    ("MONITOR",     "SCHEDULED",  "Digest (weekly)"),
    ("SUPPRESSED",  "SUPPRESSED", "None"),
]:
    n = (log["layer4_priority_flag"] == flag).sum()
    print(f"  {flag:<14}  {n:>4}  {status:<12}  {channel}")

print(f"\n  SENT window    : {sent_rows['sent_at'].min()} – {sent_rows['sent_at'].max()}")
print(f"  QUEUED window  : {queued_rng[0]} – {queued_rng[1]}  (08:00 daily)")
print(f"  SCHED window   : {sched_rng[0]} – {sched_rng[1]}  (09:00 Mondays)")
print()
print("Step 5.3 complete — delivery_log.csv written (181 rows x 13 cols).")
print("Ready for Step 5.4 (Communication Assembly).")
