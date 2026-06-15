"""
Layer 6 — Step 6.1: Agent Tool Definitions

Nine Python functions that the orchestrator agent (Step 6.2) calls via Anthropic tool_use.
Each tool queries the pre-computed Layer 1–5 CSV outputs in data/ rather than re-running
detection or causal inference pipelines from scratch.

Also exports:
  TOOL_DEFINITIONS  — list of Anthropic tool schemas (passed to the Claude API)
  dispatch_tool()   — routes a tool_name + tool_input dict to the correct function
"""

import json
import math
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BASE_DIR   = Path(__file__).parent.parent
DATA_DIR   = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(record: dict) -> dict:
    """Replace float NaN with None so json.dumps produces valid JSON."""
    return {
        k: (None if isinstance(v, float) and math.isnan(v) else v)
        for k, v in record.items()
    }


def _read(filename: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / filename)


# ---------------------------------------------------------------------------
# Tool 1 — fetch_kpis
# ---------------------------------------------------------------------------

def fetch_kpis(date: str) -> dict:
    """Return the full daily KPI row for a given date from master_dataset."""
    df = _read("master_dataset.csv")
    row = df[df["date"] == date]
    if row.empty:
        return {"error": f"No KPI data found for date {date}. Available range: {df['date'].min()} to {df['date'].max()}"}
    return _clean(row.iloc[0].to_dict())


# ---------------------------------------------------------------------------
# Tool 2 — run_detection
# ---------------------------------------------------------------------------

def run_detection(date: str) -> dict:
    """Return all anomalies detected on a given date with severity and ensemble votes."""
    df = _read("anomaly_results.csv")
    rows = df[df["date"] == date]
    if rows.empty:
        return {"anomalies": [], "count": 0, "message": f"No anomalies detected on {date}"}

    cols = [
        "anomaly_id", "kpi", "tier", "severity", "direction",
        "deviation_pct", "z_score", "votes", "methods_flagged", "anomaly_event"
    ]
    records = [_clean(r) for r in rows[cols].to_dict(orient="records")]
    return {
        "anomalies": records,
        "count": len(records),
        "severity_summary": rows["severity"].value_counts().to_dict(),
    }


# ---------------------------------------------------------------------------
# Tool 3 — run_rca
# ---------------------------------------------------------------------------

def run_rca(anomaly_id: str) -> dict:
    """Return root cause analysis results for a single anomaly."""
    df = _read("rca_results.csv")
    row = df[df["anomaly_id"] == anomaly_id]
    if row.empty:
        return {"error": f"No RCA found for anomaly_id {anomaly_id}"}

    cols = [
        "anomaly_id", "kpi", "severity", "direction", "deviation_pct", "z_score",
        "suspected_driver_kpi", "dependency_chain", "driver_z_score", "driver_direction",
        "co_anomalous_kpis", "root_cause_confidence",
        "ci_ran", "ci_relative_effect_pct", "ci_effect_significant", "ci_confidence",
        "dw_ran", "dw_treatment", "dw_effect_pct", "dw_refutation_passed",
        "is_externally_driven", "external_driver_type", "external_driver_detail",
        "snap_economic_index", "snap_marketing_pressure", "snap_seasonal_index", "snap_consumer_sentiment",
        "actionability_score", "actionability_label",
        "escalation_suppressed", "suppression_reason",
        "rca_narrative",
    ]
    return _clean(row[cols].iloc[0].to_dict())


# ---------------------------------------------------------------------------
# Tool 4 — score_impact
# ---------------------------------------------------------------------------

def score_impact(anomaly_id: str) -> dict:
    """Return quantified business impact for a single anomaly."""
    df = _read("impact_results.csv")
    row = df[df["anomaly_id"] == anomaly_id]
    if row.empty:
        return {"error": f"No impact data found for anomaly_id {anomaly_id}"}

    cols = [
        "anomaly_id", "kpi", "severity", "direction",
        "revenue_at_risk", "margin_impact", "customer_impact",
        "monthly_shortfall", "impact_pct_of_plan", "impact_narrative",
    ]
    return _clean(row[cols].iloc[0].to_dict())


# ---------------------------------------------------------------------------
# Tool 5 — prioritize
# ---------------------------------------------------------------------------

def prioritize(date: str) -> dict:
    """Return all anomalies for a date ranked by composite priority score."""
    df = _read("priority_results.csv")
    rows = df[df["date"] == date].sort_values("priority_rank")
    if rows.empty:
        return {"ranked_anomalies": [], "count": 0}

    cols = [
        "anomaly_id", "kpi", "tier", "severity", "direction",
        "priority_score", "priority_band", "priority_rank",
        "revenue_at_risk", "escalation_suppressed",
        "revenue_impact_factor", "tier_factor", "confidence_factor",
        "recoverability_factor", "external_factor",
    ]
    records = [_clean(r) for r in rows[cols].to_dict(orient="records")]
    return {"ranked_anomalies": records, "count": len(records)}


# ---------------------------------------------------------------------------
# Tool 6 — lookup_playbook
# ---------------------------------------------------------------------------

def lookup_playbook(anomaly_id: str) -> dict:
    """Return pre-computed playbook actions and recommendations for a single anomaly."""
    df = _read("recommendations.csv")
    row = df[df["anomaly_id"] == anomaly_id]
    if row.empty:
        return {"error": f"No playbook found for anomaly_id {anomaly_id}"}

    cols = [
        "anomaly_id", "kpi", "severity", "direction",
        "playbook_match", "playbook_key", "playbook_actions",
        "immediate_action", "short_term_fix", "preventive_measure",
        "recommended_owner", "effort_level", "llm_enhanced",
    ]
    return _clean(row[cols].iloc[0].to_dict())


# ---------------------------------------------------------------------------
# Tool 7 — send_alert
# ---------------------------------------------------------------------------

def send_alert(anomaly_id: str) -> dict:
    """Look up alert routing and delivery status for a single anomaly."""
    df = _read("delivery_log.csv")
    row = df[df["anomaly_id"] == anomaly_id]
    if row.empty:
        return {"error": f"No alert log found for anomaly_id {anomaly_id}"}
    return _clean(row.iloc[0].to_dict())


# ---------------------------------------------------------------------------
# Tool 8 — generate_executive_summary
# ---------------------------------------------------------------------------

def generate_executive_summary(date: str, summary_text: str) -> dict:
    """Persist the executive summary written by the orchestrator to outputs/."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"executive_summary_{date}.txt"
    path.write_text(summary_text, encoding="utf-8")
    word_count = len(summary_text.split())
    return {
        "status": "saved",
        "path": str(path),
        "word_count": word_count,
    }


# ---------------------------------------------------------------------------
# Tool 9 — update_dashboard_dataset
# ---------------------------------------------------------------------------

def update_dashboard_dataset(date: str) -> dict:
    """
    Write agent-processed rows for a given date to data/agent_results.csv.
    Appends to the file if it already exists; replaces any prior rows for the same date.
    """
    df = _read("communication_results.csv")
    rows = df[df["date"] == date]
    if rows.empty:
        return {"error": f"No communication_results rows for date {date}", "rows_written": 0}

    out_path = DATA_DIR / "agent_results.csv"
    if out_path.exists():
        existing = pd.read_csv(out_path)
        existing = existing[existing["date"] != date]
        combined = pd.concat([existing, rows], ignore_index=True)
    else:
        combined = rows.copy()

    combined.to_csv(out_path, index=False)
    return {
        "status": "written",
        "rows_written": len(rows),
        "total_rows_in_file": len(combined),
        "path": str(out_path),
    }


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

TOOL_DISPATCH = {
    "fetch_kpis":                fetch_kpis,
    "run_detection":             run_detection,
    "run_rca":                   run_rca,
    "score_impact":              score_impact,
    "prioritize":                prioritize,
    "lookup_playbook":           lookup_playbook,
    "send_alert":                send_alert,
    "generate_executive_summary": generate_executive_summary,
    "update_dashboard_dataset":  update_dashboard_dataset,
}


def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name and return its result as a JSON string."""
    if tool_name not in TOOL_DISPATCH:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    try:
        result = TOOL_DISPATCH[tool_name](**tool_input)
        return json.dumps(result, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Anthropic tool schemas
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "fetch_kpis",
        "description": (
            "Fetch the full daily KPI row for a specific date from the master dataset. "
            "Returns all 33 KPI metrics including revenue, orders, traffic, ROAS, inventory, "
            "and external indices. Call this first to establish the baseline context for the day."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format, e.g. '2024-03-15'",
                },
            },
            "required": ["date"],
        },
    },
    {
        "name": "run_detection",
        "description": (
            "Return all anomalies detected on a given date by the Layer 2 ensemble (statistical, "
            "Isolation Forest, Prophet). Each anomaly includes KPI name, tier (1/2/3), severity "
            "(HIGH/MEDIUM/LOW), direction (UP/DOWN), deviation_pct, z_score, and vote count."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format",
                },
            },
            "required": ["date"],
        },
    },
    {
        "name": "run_rca",
        "description": (
            "Return root cause analysis results for a single anomaly. Includes the dependency chain, "
            "suspected driver KPI, CausalImpact effect estimate, DoWhy ATE, root_cause_confidence (0–1), "
            "external driver flags, actionability_score, escalation_suppressed flag, and rca_narrative. "
            "Call this for every HIGH and MEDIUM severity anomaly."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "anomaly_id": {
                    "type": "string",
                    "description": "Anomaly ID from run_detection output, e.g. 'ANO_0001'",
                },
            },
            "required": ["anomaly_id"],
        },
    },
    {
        "name": "score_impact",
        "description": (
            "Return the quantified business impact for a single anomaly: revenue_at_risk (USD), "
            "margin_impact (USD), customer_impact (count), monthly_shortfall (USD), "
            "impact_pct_of_plan (%), and a plain-language impact_narrative."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "anomaly_id": {
                    "type": "string",
                    "description": "Anomaly ID from run_detection output",
                },
            },
            "required": ["anomaly_id"],
        },
    },
    {
        "name": "prioritize",
        "description": (
            "Return all anomalies for a date sorted by composite priority score. "
            "Priority factors: revenue_impact × KPI tier × causal confidence × recoverability − external_driver_penalty. "
            "Use this to decide which anomalies to investigate first and which to surface to executives."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format",
                },
            },
            "required": ["date"],
        },
    },
    {
        "name": "lookup_playbook",
        "description": (
            "Return the pre-computed playbook for a single anomaly: immediate_action (within 24h), "
            "short_term_fix (within 1 week), preventive_measure (structural), recommended_owner, "
            "and effort_level. Also returns whether LLM enhancement was already applied in Layer 4."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "anomaly_id": {
                    "type": "string",
                    "description": "Anomaly ID from run_detection output",
                },
            },
            "required": ["anomaly_id"],
        },
    },
    {
        "name": "send_alert",
        "description": (
            "Look up the alert routing and delivery status for a single anomaly. "
            "HIGH severity → Slack + Email (SENT). "
            "MEDIUM severity → Email (QUEUED). "
            "LOW severity → Digest (SCHEDULED). "
            "Externally driven + suppressed → SUPPRESSED. "
            "Returns channel, recipient, subject, message_id, and delivery_status."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "anomaly_id": {
                    "type": "string",
                    "description": "Anomaly ID from run_detection output",
                },
            },
            "required": ["anomaly_id"],
        },
    },
    {
        "name": "generate_executive_summary",
        "description": (
            "Save the executive summary you have written to outputs/executive_summary_{date}.txt. "
            "Call this AFTER you have composed the full daily brief as plain text. "
            "The summary should cover: total anomaly count, HIGH severity items with revenue impact, "
            "top root causes, suppressed alerts rationale, and priority recommended actions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date the summary is for, YYYY-MM-DD",
                },
                "summary_text": {
                    "type": "string",
                    "description": "The complete executive summary text to persist",
                },
            },
            "required": ["date", "summary_text"],
        },
    },
    {
        "name": "update_dashboard_dataset",
        "description": (
            "Write the agent-processed rows for a given date to data/agent_results.csv for dashboard consumption. "
            "Appends to the file and replaces any prior rows for the same date. "
            "Call this as the final step after all analysis is complete."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format",
                },
            },
            "required": ["date"],
        },
    },
]


# ---------------------------------------------------------------------------
# Smoke test (run directly: python scripts/6.1_agent_tools.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    TEST_DATE = "2024-03-15"

    print("=" * 60)
    print("Layer 6 - Step 6.1 Tool Smoke Test")
    print(f"Test date: {TEST_DATE}")
    print("=" * 60)

    # fetch_kpis
    result = fetch_kpis(TEST_DATE)
    if "error" not in result:
        print(f"\n[fetch_kpis]        total_revenue_usd = {result.get('total_revenue_usd')}")
    else:
        print(f"\n[fetch_kpis]        {result}")

    # run_detection
    result = run_detection(TEST_DATE)
    print(f"[run_detection]     {result['count']} anomalies | severity: {result.get('severity_summary', {})}")
    anomalies = result.get("anomalies", [])

    if anomalies:
        sample_id = anomalies[0]["anomaly_id"]

        # run_rca
        result = run_rca(sample_id)
        if "error" not in result:
            print(f"[run_rca]           {sample_id} -> driver: {result.get('suspected_driver_kpi')} | confidence: {result.get('root_cause_confidence')}")
        else:
            print(f"[run_rca]           {result}")

        # score_impact
        result = score_impact(sample_id)
        if "error" not in result:
            print(f"[score_impact]      {sample_id} -> revenue_at_risk: ${result.get('revenue_at_risk')}")
        else:
            print(f"[score_impact]      {result}")

        # prioritize
        result = prioritize(TEST_DATE)
        top = result["ranked_anomalies"][0] if result["ranked_anomalies"] else {}
        print(f"[prioritize]        {result['count']} ranked | top: {top.get('kpi')} (score={top.get('priority_score')})")

        # lookup_playbook
        result = lookup_playbook(sample_id)
        if "error" not in result:
            print(f"[lookup_playbook]   {sample_id} -> {result.get('playbook_key')} | owner: {result.get('recommended_owner')}")
        else:
            print(f"[lookup_playbook]   {result}")

        # send_alert
        result = send_alert(sample_id)
        if "error" not in result:
            print(f"[send_alert]        {sample_id} -> {result.get('delivery_channel')} | status: {result.get('delivery_status')}")
        else:
            print(f"[send_alert]        {result}")

    # generate_executive_summary
    result = generate_executive_summary(
        TEST_DATE,
        f"TEST SUMMARY for {TEST_DATE}: pipeline smoke test — {len(anomalies)} anomalies detected."
    )
    print(f"[exec_summary]      status={result['status']} | words={result['word_count']} | path={result['path']}")

    # update_dashboard_dataset
    result = update_dashboard_dataset(TEST_DATE)
    if "error" not in result:
        print(f"[dashboard_update]  rows_written={result['rows_written']} | total_in_file={result['total_rows_in_file']}")
    else:
        print(f"[dashboard_update]  {result}")

    print("\n" + "=" * 60)
    print(f"Tool definitions registered: {len(TOOL_DEFINITIONS)}")
    for t in TOOL_DEFINITIONS:
        print(f"  OK  {t['name']}")
    print("=" * 60)
