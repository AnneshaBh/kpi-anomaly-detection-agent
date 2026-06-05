"""
Layer 5, Step 5.6 — Email Delivery
Reads communication_results.csv and sends real emails via SMTP for all
non-SUPPRESSED anomalies, respecting per-flag caps from .env.

Routing
  ESCALATE    → sent immediately  (up to MAX_EMAILS_ESCALATE)
  INVESTIGATE → sent in batch     (up to MAX_EMAILS_INVESTIGATE)
  MONITOR     → sent in batch     (up to MAX_EMAILS_MONITOR)
  SUPPRESSED  → skipped entirely (external factors, no action needed)

SMTP config (.env)
  SMTP_HOST             — mail server host       (default: smtp.gmail.com)
  SMTP_PORT             — mail server port       (default: 587)
  SMTP_USER             — sender Gmail address
  SMTP_PASSWORD         — 16-char Gmail App Password (spaces allowed)
  ALERT_RECIPIENTS      — comma-separated recipient list
  MAX_EMAILS_ESCALATE   — cap on ESCALATE emails per run
  MAX_EMAILS_INVESTIGATE— cap on INVESTIGATE emails per run
  MAX_EMAILS_MONITOR    — cap on MONITOR emails per run

Input  : data/communication_results.csv
Output : console delivery log
"""

import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(BASE_DIR, "data")
INPUT_CSV = os.path.join(DATA_DIR, "communication_results.csv")

# ── SMTP config ───────────────────────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "")

# Recipients — comma-separated in .env, e.g. a@x.com,b@x.com
ALERT_RECIPIENTS = [
    r.strip() for r in os.getenv("ALERT_RECIPIENTS", "").split(",") if r.strip()
]

# Per-flag send caps
MAX_ESCALATE    = int(os.getenv("MAX_EMAILS_ESCALATE",    "15"))
MAX_INVESTIGATE = int(os.getenv("MAX_EMAILS_INVESTIGATE", "86"))
MAX_MONITOR     = int(os.getenv("MAX_EMAILS_MONITOR",     "74"))

FLAG_CAPS = {
    "ESCALATE":    MAX_ESCALATE,
    "INVESTIGATE": MAX_INVESTIGATE,
    "MONITOR":     MAX_MONITOR,
}

# ── Validate config ───────────────────────────────────────────────────────────
missing = []
if not SMTP_USER:        missing.append("SMTP_USER")
if not SMTP_PASSWORD:    missing.append("SMTP_PASSWORD")
if not ALERT_RECIPIENTS: missing.append("ALERT_RECIPIENTS")

if missing:
    print(f"ERROR: Missing required .env variable(s): {', '.join(missing)}")
    sys.exit(1)

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading communication_results.csv ...")
df = pd.read_csv(INPUT_CSV, parse_dates=["date"])
print(f"  Loaded {df.shape[0]} rows x {df.shape[1]} cols")
print()

# ── Apply caps and build send queue ──────────────────────────────────────────
print("Building send queue ...")
batches = []
for flag, cap in FLAG_CAPS.items():
    total_available = (df["layer4_priority_flag"] == flag).sum()
    subset = (
        df[df["layer4_priority_flag"] == flag]
        .sort_values("priority_rank")
        .head(cap)
    )
    batches.append(subset)
    print(f"  {flag:<12}  {len(subset):>3} queued  (cap={cap}, available={total_available})")

n_suppressed = (df["layer4_priority_flag"] == "SUPPRESSED").sum()
print(f"  {'SUPPRESSED':<12}  {n_suppressed:>3} skipped  (external factors — no action needed)")
print()

send_df = pd.concat(batches).sort_values("priority_rank").reset_index(drop=True)
print(f"  Total emails to send : {len(send_df)}")
print(f"  Recipients           : {', '.join(ALERT_RECIPIENTS)}")
print()

# ── Connect ───────────────────────────────────────────────────────────────────
print(f"Connecting to {SMTP_HOST}:{SMTP_PORT} ...")
try:
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(SMTP_USER, SMTP_PASSWORD)
    print("  Authenticated successfully.")
except Exception as exc:
    print(f"  ERROR: SMTP connection failed — {exc}")
    sys.exit(1)
print()

# ── Send ──────────────────────────────────────────────────────────────────────
print("Sending emails ...")
print()

sent_counts  = {flag: 0 for flag in FLAG_CAPS}
failed_ids   = []

for _, row in send_df.iterrows():
    flag       = row["layer4_priority_flag"]
    anomaly_id = row["anomaly_id"]
    rank       = int(row["priority_rank"])

    try:
        msg = MIMEMultipart()
        msg["From"]    = SMTP_USER
        msg["To"]      = ", ".join(ALERT_RECIPIENTS)
        msg["Subject"] = str(row["alert_subject"])
        msg.attach(MIMEText(str(row["alert_body"]), "plain"))

        server.sendmail(SMTP_USER, ALERT_RECIPIENTS, msg.as_string())
        sent_counts[flag] += 1
        print(f"  SENT    [{flag:<11}]  #{rank:<4}  {anomaly_id}")

    except Exception as exc:
        failed_ids.append(anomaly_id)
        print(f"  FAILED  [{flag:<11}]  #{rank:<4}  {anomaly_id}  — {exc}")

server.quit()
print()

# ── Summary ───────────────────────────────────────────────────────────────────
total_sent   = sum(sent_counts.values())
total_failed = len(failed_ids)

print("=" * 68)
print("LAYER 5 STEP 5.6 — EMAIL DELIVERY SUMMARY")
print("=" * 68)
print()
print(f"  {'Flag':<14}  {'Sent':>6}  {'Cap':>6}")
print(f"  {'-'*13}  {'-'*6}  {'-'*6}")
for flag, cap in FLAG_CAPS.items():
    print(f"  {flag:<14}  {sent_counts[flag]:>6}  {cap:>6}")
print(f"  {'SUPPRESSED':<14}  {'–':>6}  (skipped)")
print()
print(f"  Total sent    : {total_sent}")
print(f"  Total failed  : {total_failed}")
print(f"  Recipients    : {', '.join(ALERT_RECIPIENTS)}")

if failed_ids:
    print(f"\n  Failed anomaly IDs: {failed_ids}")
    sys.exit(1)

print()
print("Step 5.6 complete.")
