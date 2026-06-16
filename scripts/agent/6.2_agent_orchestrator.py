"""
Layer 6 - Step 6.2: Orchestrator Agent

Claude-powered tool-use loop that processes one day's KPI data end-to-end:
  fetch -> detect -> rca -> impact -> prioritize -> playbook -> alert -> summary -> dashboard

Exports:
  KPIAnomalyOrchestrator   - main agent class
  SYSTEM_PROMPT            - full system prompt (imported by 6.3 runner)
"""

import json
import os
import sys
from pathlib import Path

import importlib.util

import anthropic
from dotenv import load_dotenv

# 6.1_agent_tools.py starts with a digit so standard import won't work.
# Load it by file path and extract the two names this module needs.
def _load_tools_module():
    path = Path(__file__).parent / "6.1_agent_tools.py"
    spec = importlib.util.spec_from_file_location("agent_tools", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_tools_mod       = _load_tools_module()
TOOL_DEFINITIONS = _tools_mod.TOOL_DEFINITIONS
dispatch_tool    = _tools_mod.dispatch_tool

load_dotenv()

BASE_DIR   = Path(__file__).parent.parent.parent
DATA_DIR   = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are the KPI Anomaly Detection Orchestrator for an e-commerce business.
Your role is to process the daily KPI snapshot, identify anomalies, determine root causes,
quantify business impact, retrieve action playbooks, route alerts, write the executive brief,
and update the dashboard dataset â€” in that exact order, every run.

You have 9 tools. Follow the 9-step decision flow below without deviation.

===========================================================================
DECISION FLOW
===========================================================================

Step 1 - FETCH
  Call fetch_kpis(date) to establish the baseline KPI context for the day.

Step 2 - DETECT
  Call run_detection(date) to retrieve all anomalies flagged by the ensemble.
  - If count = 0: skip to Step 8, then Step 9.
  - If count > 0: continue to Step 3.

Step 3 - ROOT CAUSE ANALYSIS
  For every anomaly where severity = HIGH or MEDIUM:
    Call run_rca(anomaly_id).
  LOW severity anomalies skip RCA â€” they are Tier 3 background signals.
  If escalation_suppressed = True, record the suppression reason and continue.

Step 4 - IMPACT QUANTIFICATION
  For every anomaly where severity = HIGH or MEDIUM:
    Call score_impact(anomaly_id).
  Note the total revenue_at_risk across all HIGH anomalies for the brief.

Step 5 - PRIORITISE
  Call prioritize(date) once to obtain the composite-score ranked list.
  This defines the order in which you surface issues to stakeholders.

Step 6 - PLAYBOOK LOOKUP
  For every anomaly where severity = HIGH or MEDIUM:
    Call lookup_playbook(anomaly_id).
  Extract immediate_action and recommended_owner for the brief.

Step 7 - ALERT ROUTING
  Call send_alert(anomaly_id) for every detected anomaly (all severities).
  Confirm delivery_channel and delivery_status match the routing rules below.

Step 8 - EXECUTIVE SUMMARY
  Write the full daily brief following SUMMARY FORMAT exactly, then call:
    generate_executive_summary(date=date, summary_text=<your written brief>)

Step 9 - DASHBOARD UPDATE
  Call update_dashboard_dataset(date) as the absolute final step.
  This closes the pipeline run.

===========================================================================
KPI TAXONOMY
===========================================================================

Tier 1 - ALERT IMMEDIATELY (SLA: < 10 minutes)
  KPIs : total_revenue_usd, n_orders, avg_roas, conversion_rate
  Thresholds: z-score > 2.5 | WoW deviation > 20% | MoM deviation > 15%

Tier 2 - ALERT WITHIN 1 HOUR (SLA: < 1 hour)
  KPIs : return_rate, n_stockouts, avg_order_value_usd, bounce_rate
  Thresholds: z-score > 2.5 | WoW deviation > 20% | MoM deviation > 15%

Tier 3 - DAILY DIGEST (SLA: 24 hours)
  KPIs : total_clicks, sessions, inventory_health, avg_discount_pct
  Thresholds: z-score > 3.0 | WoW deviation > 25% | MoM deviation > 20%

===========================================================================
DEPENDENCY GRAPH  (driver -> outcome)
===========================================================================

  sessions           -> n_orders, total_revenue_usd
  total_clicks       -> avg_roas
  avg_discount_pct   -> conversion_rate, n_orders
  avg_order_value_usd -> total_revenue_usd
  n_orders           -> total_revenue_usd

Interpretation:
- Tier 3 driver anomalous + downstream Tier 1/2 also anomalous
    => Tier 3 KPI is the ROOT CAUSE; Tier 1/2 is a downstream effect.
- Tier 1/2 anomalous but its driver is NOT anomalous
    => Internal or demand-side issue (funnel, pricing, inventory).
- Tier 2/3 KPI appears as its own suspected_driver_kpi
    => Self-driven: it IS the root cause, no further traversal needed.

===========================================================================
SEVERITY AND ALERT ROUTING
===========================================================================

Severity assignment (from ensemble detector):
  HIGH   : z-score >= 3.5  OR  priority_band = CRITICAL / HIGH
  MEDIUM : z-score 2.5-3.4
  LOW    : z-score < 2.5 (soft signal, Tier 3 only)

Routing rules:
  Immediate (HIGH, escalation_suppressed=False) -> Slack + Email -> Executive + Operations (SENT)
  Daily     (MEDIUM, escalation_suppressed=False) -> Email -> Operations + Analyst (QUEUED)
  Weekly    (LOW)                                  -> Digest -> Analyst (SCHEDULED)
  Suppressed (escalation_suppressed=True)          -> No executive alert; digest only

Suppression triggers:
  external_driver_type in {macro, competitive, seasonal} AND actionability_score < 0.50
  Common example: avg_roas DOWN MEDIUM when marketing_pressure > 0.30

===========================================================================
PLAYBOOK OWNER REFERENCE
===========================================================================

  revenue_drop_order_volume    -> Revenue Operations + Engineering
  revenue_surge                -> Supply Chain + Analytics
  order_volume_drop            -> Revenue Operations + Product Engineering
  roas_collapse                -> Performance Marketing
  roas_collapse_click_drop     -> Performance Marketing
  return_rate_spike            -> Customer Experience
  stockout_surge               -> Supply Chain / Merchandising
  bounce_rate_spike            -> Product / Engineering
  excess_discounting           -> Pricing / Promotions

===========================================================================
EXECUTIVE SUMMARY FORMAT
===========================================================================

Write the summary using this structure exactly before calling
generate_executive_summary. Replace all {placeholders}.

---
DAILY KPI ANOMALY BRIEF - {date}
==================================

SITUATION OVERVIEW
{2-3 sentences: total anomalies detected, total revenue at risk, most critical finding}

HIGH PRIORITY ALERTS  ({count} anomalies)
- {KPI} {direction} {deviation_pct}% | Root cause: {driver} | Revenue at risk: ${amount}
  Action: {immediate_action} | Owner: {owner}
[Repeat for each HIGH anomaly. If none, write "No HIGH severity anomalies today."]

MEDIUM PRIORITY OBSERVATIONS  ({count} anomalies)
- {KPI} {direction}: {brief rca_narrative or context}  [SUPPRESSED / ACTIVE]
[Repeat for each MEDIUM anomaly. Note suppressed alerts clearly.]

SUPPRESSED ALERTS  ({count})
{Explain which alerts were suppressed, the external driver type, and the rationale
for not escalating to the executive channel.}
[If none suppressed, write "None."]

LOW SEVERITY SIGNALS  ({count} anomalies)
{One-line summary of Tier 3 background signals to be aware of.}
[If none, write "None."]

RECOMMENDED IMMEDIATE ACTIONS
1. {Highest-priority action from the top-ranked anomaly â€” specific and actionable}
2. {Second priority}
3. {Third priority}

WATCH LIST FOR TOMORROW
{1-2 KPIs showing early warning signals (z-score 1.5-2.5) that warrant monitoring.
If nothing noteworthy, write "No early warning signals at this time."}
---

===========================================================================
OPERATING RULES
===========================================================================

- Always complete all 9 steps, even when anomaly count is low.
- Do not skip send_alert for LOW severity anomalies â€” routing still applies.
- Do not call update_dashboard_dataset before generate_executive_summary.
- If a tool returns an error, note it in the summary and continue.
- Be specific with numbers: always include deviation_pct, revenue_at_risk,
  root_cause_confidence, and recommended_owner in your brief.
""".strip()


# ---------------------------------------------------------------------------
# Orchestrator class
# ---------------------------------------------------------------------------

class KPIAnomalyOrchestrator:
    """
    Runs the 9-step KPI anomaly detection pipeline for a given date via
    Claude tool-use. Persists a full tool-call trace to data/agent_run_log.json.
    """

    MODEL     = "claude-sonnet-4-6"
    MAX_TURNS = 60

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY not set. Add it to .env or the system environment."
            )
        self.client     = anthropic.Anthropic(api_key=api_key)
        self.tool_trace = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, date: str) -> dict:
        """
        Run the full daily pipeline for a given date.
        Returns the run_log dict and writes data/agent_run_log.json.
        """
        print(f"\n{'=' * 60}")
        print(f"  KPI Anomaly Orchestrator  |  date: {date}")
        print(f"  Model: {self.MODEL}")
        print(f"{'=' * 60}")

        self.tool_trace = []
        messages = [
            {
                "role": "user",
                "content": (
                    f"Run the daily KPI anomaly detection and analysis pipeline "
                    f"for {date}. Follow the 9-step decision flow exactly."
                ),
            }
        ]

        turns = 0
        final_text = ""

        while turns < self.MAX_TURNS:
            turns += 1

            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=8096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            # Append assistant message to conversation history
            messages.append({"role": "assistant", "content": response.content})

            # Capture any text blocks for the run log
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            # --- DONE ---
            if response.stop_reason == "end_turn":
                print(f"\n  [done]  Pipeline complete after {turns} turn(s), "
                      f"{len(self.tool_trace)} tool call(s).")
                break

            # --- TOOL CALL(S) ---
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    step       = len(self.tool_trace) + 1
                    input_keys = list(block.input.keys())
                    print(f"  [tool {step:02d}]  {block.name}  args={input_keys}")

                    result_str = dispatch_tool(block.name, block.input)
                    result_obj = json.loads(result_str)

                    self.tool_trace.append(
                        {
                            "step":        step,
                            "tool_name":   block.name,
                            "tool_use_id": block.id,
                            "input":       block.input,
                            "output":      result_obj,
                        }
                    )

                    tool_results.append(
                        {
                            "type":        "tool_result",
                            "tool_use_id": block.id,
                            "content":     result_str,
                        }
                    )

                messages.append({"role": "user", "content": tool_results})
                continue

            # Unexpected stop reason â€” log and exit loop
            print(f"  [warn]  Unexpected stop_reason: {response.stop_reason!r}")
            break

        if turns >= self.MAX_TURNS:
            print(f"  [warn]  Hit MAX_TURNS={self.MAX_TURNS} safety limit.")

        # ------------------------------------------------------------------
        # Build and persist run log
        # ------------------------------------------------------------------
        tools_used = list(dict.fromkeys(t["tool_name"] for t in self.tool_trace))

        run_log = {
            "date":            date,
            "model":           self.MODEL,
            "status":          "completed" if turns < self.MAX_TURNS else "max_turns_reached",
            "total_turns":     turns,
            "tool_call_count": len(self.tool_trace),
            "tools_used":      tools_used,
            "final_text":      final_text.strip(),
            "tool_trace":      self.tool_trace,
        }

        log_path = DATA_DIR / "agent/agent_run_log.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(run_log, f, indent=2, default=str, ensure_ascii=False)

        print(f"  [log]   agent_run_log.json  ({len(self.tool_trace)} tool calls, "
              f"tools: {tools_used})")

        return run_log

    # ------------------------------------------------------------------
    # Pretty-print helpers
    # ------------------------------------------------------------------

    def print_trace(self) -> None:
        """Print the tool call trace from the most recent run."""
        if not self.tool_trace:
            print("No tool trace available.")
            return
        print("\nTool Call Trace:")
        print("-" * 50)
        for entry in self.tool_trace:
            inp_summary = {k: str(v)[:60] for k, v in entry["input"].items()}
            print(f"  Step {entry['step']:02d}  {entry['tool_name']}")
            print(f"          in : {inp_summary}")
            out = entry["output"]
            if isinstance(out, dict):
                # Show a compact summary of the output
                snippet = {
                    k: str(v)[:60]
                    for k, v in list(out.items())[:4]
                }
                print(f"          out: {snippet}")
            print()

    def print_summary_path(self, date: str) -> None:
        path = OUTPUT_DIR / "alerts" / f"executive_summary_{date}.txt"
        if path.exists():
            print(f"\nExecutive summary: {path}")
            print("-" * 50)
            # Use errors='replace' so non-cp1252 chars don't crash on Windows terminals
            text = path.read_text(encoding="utf-8")
            sys.stdout.buffer.write((text + "\n").encode(sys.stdout.encoding, errors="replace"))
        else:
            print(f"\n[warn] Executive summary not found at {path}")


# ---------------------------------------------------------------------------
# Smoke test  (python scripts/6.2_agent_orchestrator.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Pick a date that has at least one HIGH severity anomaly for a full demo
    import pandas as pd

    df = pd.read_csv(DATA_DIR / "detection/anomaly_results.csv")
    high_dates = df[df["severity"] == "HIGH"]["date"].unique()

    if len(high_dates) == 0:
        # Fall back to any date with anomalies
        test_date = df["date"].iloc[0]
        print(f"No HIGH severity dates found. Using first anomaly date: {test_date}")
    else:
        test_date = high_dates[0]
        n_high = len(df[(df["date"] == test_date) & (df["severity"] == "HIGH")])
        print(f"Selected test date: {test_date}  ({n_high} HIGH anomaly/ies)")

    orchestrator = KPIAnomalyOrchestrator()
    run_log = orchestrator.run(test_date)

    print("\n" + "=" * 60)
    print("Run Summary")
    print("=" * 60)
    print(f"  Status          : {run_log['status']}")
    print(f"  Total turns     : {run_log['total_turns']}")
    print(f"  Tool calls      : {run_log['tool_call_count']}")
    print(f"  Tools used      : {run_log['tools_used']}")

    orchestrator.print_trace()
    orchestrator.print_summary_path(test_date)
