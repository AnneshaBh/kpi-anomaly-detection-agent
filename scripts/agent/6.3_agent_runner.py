"""
Layer 6 - Step 6.3: Agent Runner

Entry point for the KPI Anomaly Detection pipeline.
Loads .env, picks a date, invokes the orchestrator, and prints a run report.

Usage
-----
  python scripts/6.3_agent_runner.py                      # auto: most recent anomaly date
  python scripts/6.3_agent_runner.py --date 2024-08-20    # specific date
  python scripts/6.3_agent_runner.py --demo               # highest-anomaly date in dataset
  python scripts/6.3_agent_runner.py --schedule           # daily at 07:00 (uses today's date)
"""

import argparse
import importlib.util
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import schedule
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"


# ---------------------------------------------------------------------------
# Load orchestrator module by file path (filename starts with a digit)
# ---------------------------------------------------------------------------

def _load_orchestrator():
    path = Path(__file__).parent / "6.2_agent_orchestrator.py"
    spec = importlib.util.spec_from_file_location("agent_orchestrator", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_orch_mod   = _load_orchestrator()
Orchestrator = _orch_mod.KPIAnomalyOrchestrator


# ---------------------------------------------------------------------------
# Date selection helpers
# ---------------------------------------------------------------------------

def _anomaly_df() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "detection/anomaly_results.csv")


def latest_anomaly_date() -> str:
    """Return the most recent date that has at least one detected anomaly."""
    df = _anomaly_df()
    return df["date"].max()


def demo_date() -> str:
    """
    Return the date with the most anomalies (including at least one HIGH),
    preferring dates that exercise the full 9-step flow.
    """
    df = _anomaly_df()
    high_dates = df[df["severity"] == "HIGH"]["date"].unique()
    if len(high_dates) == 0:
        return df.groupby("date").size().idxmax()
    # Among HIGH dates, pick the one with the most total anomalies
    counts = df[df["date"].isin(high_dates)].groupby("date").size()
    return counts.idxmax()


def resolve_date(args) -> str:
    """Pick a run date based on CLI flags."""
    if args.date:
        # Validate format
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"[error] --date must be YYYY-MM-DD format, got: {args.date!r}")
            sys.exit(1)
        return args.date

    if args.demo:
        d = demo_date()
        print(f"[demo]  Selected: {d}  (highest-anomaly HIGH-severity date in dataset)")
        return d

    d = latest_anomaly_date()
    print(f"[auto]  Selected: {d}  (most recent anomaly date in dataset)")
    return d


# ---------------------------------------------------------------------------
# Single-run execution
# ---------------------------------------------------------------------------

def run_pipeline(run_date: str) -> dict:
    """Run the full 9-step orchestrator for a given date and return the run log."""
    orch    = Orchestrator()
    run_log = orch.run(run_date)
    _print_report(run_log, run_date)
    return run_log


def _print_report(run_log: dict, run_date: str) -> None:
    """Print a concise post-run report to stdout."""
    # Collect summary info from the tool trace
    trace = run_log.get("tool_trace", [])

    # Anomaly count from run_detection output
    det = next((e for e in trace if e["tool_name"] == "run_detection"), None)
    anomaly_count    = det["output"].get("count", "?") if det else "?"
    severity_summary = det["output"].get("severity_summary", {}) if det else {}

    # Revenue at risk from score_impact calls
    total_at_risk = 0.0
    for entry in trace:
        if entry["tool_name"] == "score_impact":
            val = entry["output"].get("revenue_at_risk")
            if val and str(val).lstrip("-").replace(".", "", 1).isdigit():
                v = float(val)
                if v > 0:
                    total_at_risk += v

    # Executive summary word count
    from pathlib import Path
    summ_path = BASE_DIR / "outputs" / f"executive_summary_{run_date}.txt"
    word_count = len(summ_path.read_text(encoding="utf-8").split()) if summ_path.exists() else 0

    print("\n" + "=" * 60)
    print("  Pipeline Run Report")
    print("=" * 60)
    print(f"  Date              : {run_date}")
    print(f"  Status            : {run_log['status']}")
    print(f"  Model             : {run_log['model']}")
    print(f"  Agent turns       : {run_log['total_turns']}")
    print(f"  Tool calls        : {run_log['tool_call_count']}")
    print(f"  Anomalies found   : {anomaly_count}  {severity_summary}")
    print(f"  Revenue at risk   : ${total_at_risk:,.0f}")
    print(f"  Summary words     : {word_count}")
    print(f"  Outputs written:")
    print(f"    data/agent_run_log.json")
    print(f"    data/agent_results.csv")
    print(f"    outputs/executive_summary_{run_date}.txt")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Scheduled runner
# ---------------------------------------------------------------------------

def _scheduled_job() -> None:
    """
    Job called by the scheduler each day.
    Uses today's date if it exists in the master dataset, otherwise the
    most recent dataset date â€” supports both production and demo modes.
    """
    today_str = date.today().strftime("%Y-%m-%d")
    df = pd.read_csv(DATA_DIR / "processed/master_dataset.csv")

    if today_str in df["date"].values:
        run_date = today_str
        print(f"\n[scheduler]  {datetime.now():%Y-%m-%d %H:%M}  Running for today: {run_date}")
    else:
        run_date = df["date"].max()
        print(
            f"\n[scheduler]  {datetime.now():%Y-%m-%d %H:%M}  "
            f"Today ({today_str}) not in dataset â€” using latest: {run_date}"
        )

    run_pipeline(run_date)


def run_scheduled(run_time: str = "07:00") -> None:
    """Schedule the pipeline to run daily at run_time (HH:MM). Blocks until interrupted."""
    print(f"[scheduler]  Scheduling daily pipeline run at {run_time}")
    print("[scheduler]  Running once immediately, then daily. Press Ctrl+C to stop.")
    print()

    # Run immediately on start
    _scheduled_job()

    schedule.every().day.at(run_time).do(_scheduled_job)

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n[scheduler]  Stopped.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Layer 6 Agent Runner â€” runs the KPI Anomaly Detection pipeline "
            "for a single date or on a daily schedule."
        )
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Run pipeline for this specific date.",
    )
    group.add_argument(
        "--demo",
        action="store_true",
        help="Auto-select the date with the most HIGH-severity anomalies.",
    )
    group.add_argument(
        "--schedule",
        action="store_true",
        help="Run immediately then schedule daily at 07:00.",
    )
    p.add_argument(
        "--time",
        default="07:00",
        metavar="HH:MM",
        help="Scheduled run time (default: 07:00). Only used with --schedule.",
    )
    return p


if __name__ == "__main__":
    parser = _build_parser()
    args   = parser.parse_args()

    if args.schedule:
        run_scheduled(run_time=args.time)
    else:
        run_date = resolve_date(args)
        run_pipeline(run_date)
