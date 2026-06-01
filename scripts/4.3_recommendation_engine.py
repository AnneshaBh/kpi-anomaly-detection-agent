"""
Layer 4, Step 4.3 — Recommendation Engine
Generates actionable recommendations for each confirmed anomaly via:
  1. Deterministic playbook lookup  — all 181 rows
  2. Claude API (Haiku) enhancement — 101 ESCALATE + INVESTIGATE rows only

Prompt caching is applied to the system prompt so it is transmitted once and
reused across all 101 API calls, minimising latency and cost.

Input  : data/priority_results.csv   (181 x 59)
Output : data/recommendations.csv    (181 x 68)
         SQLite table: recommendations
"""

import os
import sqlite3
import sys

import anthropic
import pandas as pd
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows so LLM-generated unicode (arrows, etc.) prints cleanly.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE_DIR, "data")
DB_PATH    = os.path.join(DATA_DIR, "kpi_anomaly_detection.db")
INPUT_CSV  = os.path.join(DATA_DIR, "priority_results.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "recommendations.csv")

# ── Model ─────────────────────────────────────────────────────────────────────
# Haiku for 101 structured-output recommendation calls (fast, cost-efficient).
# The Layer 6 orchestrator uses claude-sonnet-4-6.
MODEL      = "claude-haiku-4-5-20251001"
MAX_TOKENS = 350


# ── Playbooks ─────────────────────────────────────────────────────────────────
# Keyed by (kpi, direction, suspected_driver_kpi).
# Lookup: specific 3-tuple first, then (kpi, direction, None) fallback.

PLAYBOOKS = {
    # avg_roas
    ("avg_roas", "DOWN", "total_clicks"): {
        "key": "roas_collapse_click_drop",
        "immediate": "Pause ad groups with CPA > $50; audit for account-level policy violations or budget exhaustion",
        "short_term": "Review keyword targeting and negative-keyword lists; run auction insights to diagnose competitor spend surge",
        "preventive": "Build co-monitoring dashboard for ROAS + click volume; set auto-alert at 20% below 30-day rolling average",
        "owner": "Performance Marketing",
        "effort": "H",
    },
    ("avg_roas", "DOWN", None): {
        "key": "roas_collapse",
        "immediate": "Pause underperforming ad groups above $50 CPA; check for pixel tracking issues or attribution window changes",
        "short_term": "Shift 30% of budget from underperforming channels to email/organic; review bid strategy against target ROAS",
        "preventive": "Set ROAS floor alerts at 20% below 30-day average; review attribution model and bidding strategy quarterly",
        "owner": "Performance Marketing",
        "effort": "M",
    },
    ("avg_roas", "UP", "total_clicks"): {
        "key": "roas_surge_click_driven",
        "immediate": "Confirm attribution accuracy; check for pixel or tracking changes inflating attributed revenue",
        "short_term": "Identify campaigns driving ROAS and click uplift; reallocate budget toward top performers",
        "preventive": "Document the campaign mix and bid strategy driving this efficiency as a replication playbook",
        "owner": "Performance Marketing",
        "effort": "L",
    },
    ("avg_roas", "UP", None): {
        "key": "roas_surge",
        "immediate": "Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue",
        "short_term": "Identify which campaigns and keywords are driving the uplift; scale budget toward those performers",
        "preventive": "Document the channel mix and bid strategy driving this efficiency for future campaign planning",
        "owner": "Performance Marketing",
        "effort": "L",
    },
    # total_revenue_usd
    ("total_revenue_usd", "DOWN", "n_orders"): {
        "key": "revenue_drop_order_volume",
        "immediate": "Check payment gateway health and checkout error logs; verify all promotional codes are active",
        "short_term": "Activate win-back campaign for 30-day lapsed customers; A/B test checkout friction points",
        "preventive": "Implement real-time order volume monitoring with automated gateway health checks",
        "owner": "Revenue Operations / Product",
        "effort": "H",
    },
    ("total_revenue_usd", "DOWN", "sessions"): {
        "key": "revenue_drop_traffic",
        "immediate": "Check organic and paid traffic sources for drops; review Search Console for crawl or indexing issues",
        "short_term": "Boost paid acquisition budget to offset organic shortfall; audit top acquisition channels for recent changes",
        "preventive": "Diversify traffic sources; set traffic floor alerts at 15% below 7-day rolling average",
        "owner": "Growth Marketing / SEO",
        "effort": "H",
    },
    ("total_revenue_usd", "UP", None): {
        "key": "revenue_surge",
        "immediate": "Confirm inventory availability to fulfil the demand surge; validate attribution and data integrity",
        "short_term": "Analyse customer segment and channel mix driving the surge; project 30-day forward demand",
        "preventive": "Build surge-response playbook: inventory buffers, dynamic pricing triggers, campaign scaling thresholds",
        "owner": "Revenue Operations",
        "effort": "L",
    },
    # n_orders
    ("n_orders", "DOWN", "avg_discount_pct"): {
        "key": "order_drop_despite_discount",
        "immediate": "Check checkout completion rate and payment errors; verify demand signals across all acquisition channels",
        "short_term": "Review competitive pricing; test deeper discount or bundle offers to stimulate demand recovery",
        "preventive": "Build demand elasticity model to understand effective discount thresholds by customer segment",
        "owner": "Revenue Operations / Pricing",
        "effort": "H",
    },
    ("n_orders", "DOWN", None): {
        "key": "order_volume_drop",
        "immediate": "Check checkout completion rate, payment errors, and whether active promotional codes are functioning",
        "short_term": "Activate win-back campaign for lapsed customers; review pricing vs nearest competitors",
        "preventive": "Set real-time order volume floor alerts with automated checkout health monitoring",
        "owner": "Revenue Operations / Product",
        "effort": "M",
    },
    ("n_orders", "UP", "sessions"): {
        "key": "order_surge_traffic_driven",
        "immediate": "Verify fulfilment capacity and SLA commitments can handle the order spike volume",
        "short_term": "Scale customer support capacity; fast-track inventory reorder for top-revenue SKUs",
        "preventive": "Build demand forecasting model linking session volume to order spikes for proactive capacity planning",
        "owner": "Operations / Supply Chain",
        "effort": "M",
    },
    ("n_orders", "UP", None): {
        "key": "order_volume_surge",
        "immediate": "Confirm fulfilment capacity; flag to warehouse team for additional staffing if needed",
        "short_term": "Identify customer segments and channels driving the surge; optimise for repeat purchase",
        "preventive": "Build order surge protocols with auto-scaling triggers for fulfilment and support resources",
        "owner": "Operations",
        "effort": "L",
    },
    # conversion_rate
    ("conversion_rate", "UP", "avg_discount_pct"): {
        "key": "conversion_rate_discount_driven",
        "immediate": "Validate conversion uplift is margin-positive after discount cost; check gross margin on converted orders",
        "short_term": "A/B test discount depth vs conversion rate to find the optimal profitability threshold",
        "preventive": "Build promo effectiveness scorecard tracking incremental revenue per discount percentage point",
        "owner": "Pricing / CRO",
        "effort": "M",
    },
    ("conversion_rate", "UP", None): {
        "key": "conversion_improvement",
        "immediate": "Confirm no tag or tracking changes could inflate counts; audit recent A/B test deployments",
        "short_term": "Identify landing page or checkout change driving the lift; document for rollout to other pages",
        "preventive": "Establish continuous A/B testing programme for conversion optimisation with significance gates",
        "owner": "Product / CRO",
        "effort": "L",
    },
    # bounce_rate
    ("bounce_rate", "UP", None): {
        "key": "bounce_rate_spike",
        "immediate": "Check for page errors, load times over 3s, or broken mobile layouts; review recent deployments",
        "short_term": "Run UX audit on highest-traffic entry pages; roll back A/B tests launched in the last 7 days",
        "preventive": "Implement automated page-speed and error-rate monitoring with deployment gating thresholds",
        "owner": "Product / Engineering",
        "effort": "M",
    },
    ("bounce_rate", "DOWN", None): {
        "key": "bounce_rate_improvement",
        "immediate": "Confirm improvement is genuine and not a tracking or session-timeout configuration change",
        "short_term": "Identify which pages or traffic sources drove the improvement; replicate the approach",
        "preventive": "Incorporate the changes driving lower bounce rate into design system and content standards",
        "owner": "Product / CRO",
        "effort": "L",
    },
    # return_rate
    ("return_rate", "UP", None): {
        "key": "return_rate_spike",
        "immediate": "Pull return reason codes from last 48h; identify top 5 returned SKUs and primary return reasons",
        "short_term": "Review product descriptions and sizing accuracy for high-return SKUs; audit recent shipment quality",
        "preventive": "Improve product imagery and sizing guides; add post-purchase survey to capture early return signal",
        "owner": "Customer Experience / Merchandising",
        "effort": "M",
    },
    ("return_rate", "DOWN", None): {
        "key": "return_rate_improvement",
        "immediate": "Confirm improvement is genuine and not caused by a processing backlog or return policy change",
        "short_term": "Identify which categories or segments show most improvement; share learnings across teams",
        "preventive": "Scale the practices reducing returns — better descriptions, sizing guides, QC checks",
        "owner": "Customer Experience",
        "effort": "L",
    },
    # n_stockouts
    ("n_stockouts", "UP", None): {
        "key": "stockout_surge",
        "immediate": "Trigger emergency reorder for top 20 SKUs by revenue; surface in-stock alternatives in recommendation engine",
        "short_term": "Escalate to merchandising and supplier teams; increase demand forecast for affected SKUs",
        "preventive": "Review safety stock levels and reorder point formulas; implement dynamic reorder triggers based on velocity",
        "owner": "Supply Chain / Merchandising",
        "effort": "H",
    },
    ("n_stockouts", "DOWN", None): {
        "key": "stockout_recovery",
        "immediate": "Confirm replenishment has arrived and inventory levels are accurate across all fulfilment nodes",
        "short_term": "Re-enable paid ads for previously out-of-stock SKUs; update availability on all sales channels",
        "preventive": "Codify the reorder lead time adjustment that resolved this stockout event as standing policy",
        "owner": "Supply Chain",
        "effort": "L",
    },
    # avg_order_value_usd
    ("avg_order_value_usd", "UP", None): {
        "key": "aov_increase",
        "immediate": "Confirm uplift is not driven by a data error, test orders, or one-off large B2B purchase",
        "short_term": "Identify which product categories, bundles, or upsell features are driving higher AOV",
        "preventive": "Scale proven upsell and cross-sell mechanics; run AOV-targeted bundle pricing experiments",
        "owner": "Merchandising / Product",
        "effort": "L",
    },
    # avg_discount_pct
    ("avg_discount_pct", "UP", None): {
        "key": "excess_discounting",
        "immediate": "Identify which coupon codes or promotions are over-indexing; check for leaked or unauthorised codes",
        "short_term": "Cap active discount depth and audit promo calendar for unintended offer stacking",
        "preventive": "Build discount governance framework with approval thresholds and gross margin guardrails",
        "owner": "Pricing / Promotions",
        "effort": "M",
    },
    # sessions
    ("sessions", "UP", None): {
        "key": "traffic_surge",
        "immediate": "Confirm site performance under load; check for bot traffic or scraper activity inflating session counts",
        "short_term": "Identify traffic source driving the surge; optimise landing pages to maximise conversion of the inflow",
        "preventive": "Set traffic ceiling alerts to trigger capacity-planning review; strengthen bot detection coverage",
        "owner": "Growth Marketing / Engineering",
        "effort": "L",
    },
    ("sessions", "DOWN", None): {
        "key": "traffic_drop",
        "immediate": "Check site uptime, DNS, and CDN status; verify paid campaigns are serving and not budget-exhausted",
        "short_term": "Boost paid acquisition to compensate; investigate organic ranking drops in Google Search Console",
        "preventive": "Diversify traffic acquisition mix; set floor alerts at 15% below 7-day rolling average",
        "owner": "Growth Marketing / SEO",
        "effort": "H",
    },
    # total_clicks
    ("total_clicks", "UP", None): {
        "key": "click_surge",
        "immediate": "Verify click quality metrics; check for invalid click activity or bot traffic in platform reports",
        "short_term": "Identify campaigns driving the uplift; optimise bids toward clicks that convert, not just volume",
        "preventive": "Implement click fraud monitoring; review audience targeting quality vs volume signal balance",
        "owner": "Performance Marketing",
        "effort": "L",
    },
    ("total_clicks", "DOWN", None): {
        "key": "click_drop",
        "immediate": "Check campaign budgets, ad serving status, and billing health across all paid platforms",
        "short_term": "Review Quality Scores and ad relevance; refresh creatives and expand keyword or audience targeting",
        "preventive": "Set click volume floor alerts; build backup campaign templates for rapid deployment on volume drops",
        "owner": "Performance Marketing",
        "effort": "M",
    },
    # inventory_health
    ("inventory_health", "DOWN", None): {
        "key": "inventory_health_decline",
        "immediate": "Identify SKUs contributing most to health decline; check incoming shipment ETAs and supplier status",
        "short_term": "Expedite reorders for critical SKUs; adjust safety stock levels based on current demand trajectory",
        "preventive": "Implement predictive inventory health scoring with 30-day forward-looking reorder triggers",
        "owner": "Supply Chain",
        "effort": "M",
    },
    ("inventory_health", "UP", None): {
        "key": "inventory_health_improvement",
        "immediate": "Confirm inventory accuracy across all warehouse locations and channels; check for data entry corrections",
        "short_term": "Review slow-moving SKUs and consider targeted markdowns to maintain healthy stock turns",
        "preventive": "Document supply chain adjustments driving the health improvement as standing best practices",
        "owner": "Supply Chain / Merchandising",
        "effort": "L",
    },
}


def lookup_playbook(kpi: str, direction, driver) -> dict | None:
    """3-tuple specific match, then (kpi, direction, None) fallback."""
    direction = direction if pd.notna(direction) else None
    driver    = driver    if pd.notna(driver)    else None
    return (
        PLAYBOOKS.get((kpi, direction, driver))
        or PLAYBOOKS.get((kpi, direction, None))
    )


# ── System prompt (cached across all 101 LLM calls) ──────────────────────────
SYSTEM_PROMPT = """\
You are a KPI Intelligence Agent for a mid-market e-commerce business. Your role is to generate
precise, actionable recommendations when business KPI anomalies are detected.

BUSINESS PROFILE:
- ~200 orders/day | ~$11,700 daily revenue | ~8,400 daily web sessions
- Average order value: $57 | Conversion rate: 2.45% | Bounce rate: 42% | Return rate: 7.7%
- Product catalogue: 500 SKUs across Electronics, Apparel, Home, Sports, Beauty, Food, Toys, Books
- Marketing channels: paid_search, social, email, affiliate, display

KPI TIER OWNERSHIP:
Tier 1 (immediate escalation):
  total_revenue_usd -> Revenue Operations
  n_orders          -> Revenue Operations
  avg_roas          -> Performance Marketing
  conversion_rate   -> Product / CRO

Tier 2 (1-hour escalation):
  return_rate          -> Customer Experience
  n_stockouts          -> Supply Chain / Merchandising
  avg_order_value_usd  -> Merchandising
  bounce_rate          -> Product / Engineering

Tier 3 (daily digest):
  total_clicks     -> Performance Marketing
  sessions         -> Growth Marketing
  inventory_health -> Supply Chain
  avg_discount_pct -> Pricing / Promotions

KPI GLOSSARY:
  avg_roas         : Return on Ad Spend = attributed_revenue / ad_spend (baseline 34x; higher = efficient)
  conversion_rate  : sessions that result in a purchase (baseline 2.45%; higher = better)
  bounce_rate      : sessions leaving after one page (baseline 42%; lower = better)
  return_rate      : orders returned (baseline 7.7%; lower = better)
  inventory_health : composite supply-chain stability score -1 to +1 (higher = healthier)
  avg_discount_pct : average discount fraction applied (e.g. 0.10 = 10%; excess erodes margin)

KPI DEPENDENCY CHAIN (effect -> cause):
  total_revenue_usd -> n_orders -> sessions -> bounce_rate
                               -> conversion_rate -> avg_discount_pct
                               -> n_stockouts -> inventory_health
                 -> avg_order_value_usd -> avg_discount_pct
                 -> return_rate
  avg_roas -> total_clicks

RECOMMENDATION FRAMEWORK:
  IMMEDIATE  (next 24h): Triage -- stop the bleeding or capture the uplift right now
  SHORT_TERM (next 7d) : Root-cause investigation and tactical fix
  PREVENTIVE (next 30d): Structural change to prevent recurrence or lock in the gain

OUTPUT FORMAT -- output EXACTLY 3 lines, no preamble, no explanation:
IMMEDIATE | <specific actionable task> | <owner team> | <expected outcome> | <effort: H/M/L>
SHORT_TERM | <specific actionable task> | <owner team> | <expected outcome> | <effort: H/M/L>
PREVENTIVE | <specific actionable task> | <owner team> | <expected outcome> | <effort: H/M/L>

RULES:
1. Be specific -- name tools, thresholds, and concrete actions. Never say "investigate further" alone.
2. Calibrate effort: H = multi-day cross-team project | M = same-day task | L = under 1-hour check.
3. DOWN anomalies: address root cause and reduce further exposure.
4. UP anomalies: validate data integrity, capitalise on the gain, sustain momentum.
5. Externally driven anomalies: acknowledge the external context; focus on what IS within business control.
6. Enhance the playbook baseline with specifics from the anomaly context -- do not repeat it verbatim.
"""

KPI_LABELS = {
    "total_revenue_usd"  : "Total Revenue (USD)",
    "n_orders"           : "Order Volume",
    "avg_roas"           : "Marketing ROAS",
    "conversion_rate"    : "Conversion Rate",
    "return_rate"        : "Return Rate",
    "n_stockouts"        : "Stockout Count",
    "avg_order_value_usd": "Average Order Value",
    "bounce_rate"        : "Bounce Rate",
    "total_clicks"       : "Total Ad Clicks",
    "sessions"           : "Web Sessions",
    "inventory_health"   : "Inventory Health Score",
    "avg_discount_pct"   : "Average Discount Rate",
}


def build_user_prompt(row: pd.Series, playbook: dict | None) -> str:
    label     = KPI_LABELS.get(row["kpi"], row["kpi"])
    conf_str  = (f"{row['root_cause_confidence']:.0%}"
                 if pd.notna(row["root_cause_confidence"]) else "N/A")
    direction = row["direction"] if pd.notna(row["direction"]) else "UNKNOWN"
    dev_str   = f"{row['deviation_pct']:+.1f}%" if pd.notna(row["deviation_pct"]) else "N/A"
    risk_label = "at risk" if float(row["revenue_at_risk"]) > 0 else "captured upside"

    # External context sentence
    ext_parts = []
    if abs(float(row["snap_economic_index"])) > 0.05:
        mood = "expanding" if float(row["snap_economic_index"]) > 0 else "contracting"
        ext_parts.append(f"macro economy {mood} (index {row['snap_economic_index']:+.2f})")
    if float(row["snap_marketing_pressure"]) > 0.20:
        ext_parts.append(f"elevated competitive marketing pressure ({row['snap_marketing_pressure']:.2f})")
    if abs(float(row["snap_seasonal_index"])) > 0.10:
        mood = "peak" if float(row["snap_seasonal_index"]) > 0 else "trough"
        ext_parts.append(f"seasonal {mood} (index {row['snap_seasonal_index']:+.2f})")
    if float(row["snap_consumer_sentiment"]) < -0.05:
        ext_parts.append(f"declining consumer sentiment ({row['snap_consumer_sentiment']:+.2f})")
    ext_context = "; ".join(ext_parts) if ext_parts else "no significant external pressures"

    ext_note = ""
    if row["is_externally_driven"] and str(row["external_driver_type"]) not in ("none", "nan", ""):
        ext_note = (f"NOTE: Attributed to external driver ({row['external_driver_type']}). "
                    f"Focus recommendations on what IS within business control.\n")

    pb_block = (
        f"Playbook baseline (enhance with context below):\n"
        f"  Immediate  : {playbook['immediate']}\n"
        f"  Short-term : {playbook['short_term']}\n"
        f"  Preventive : {playbook['preventive']}"
    ) if playbook else "No specific playbook entry -- apply general best practices for this KPI type."

    return (
        f"ANOMALY:\n"
        f"  KPI       : {label} ({row['kpi']})\n"
        f"  Date      : {row['date']} | Severity: {row['severity']} | Direction: {direction}\n"
        f"  Deviation : {dev_str} vs forecast  "
        f"(actual={row['actual_value']:.4g}, expected={row['expected_value']:.4g})\n"
        f"\nROOT CAUSE:\n"
        f"  Suspected driver : {row['suspected_driver_kpi']}\n"
        f"  RCA narrative    : {row['rca_narrative']}\n"
        f"  Causal confidence: {conf_str}\n"
        f"\nBUSINESS IMPACT:\n"
        f"  Revenue (7-day): ${float(row['revenue_at_risk']):,.0f} ({risk_label})\n"
        f"  {row['impact_narrative']}\n"
        f"\nEXTERNAL CONTEXT: {ext_context}\n"
        f"{ext_note}"
        f"\n{pb_block}\n"
        f"\nGenerate 3 recommendations:"
    )


def parse_llm_response(text: str) -> dict:
    result = {
        "immediate_action"  : "",
        "short_term_fix"    : "",
        "preventive_measure": "",
        "recommended_owner" : "",
        "effort_level"      : "M",
    }
    for line in text.strip().splitlines():
        parts = [p.strip() for p in line.split("|")]
        if not parts or not parts[0].strip():
            continue
        label = parts[0].upper().strip()
        if label == "IMMEDIATE" and len(parts) >= 2:
            result["immediate_action"]  = parts[1]
            result["recommended_owner"] = parts[2] if len(parts) > 2 else ""
            raw_effort = parts[4] if len(parts) > 4 else "M"
            result["effort_level"] = raw_effort.strip().upper()[:1] if raw_effort.strip() else "M"
        elif label == "SHORT_TERM" and len(parts) >= 2:
            result["short_term_fix"] = parts[1]
        elif label == "PREVENTIVE" and len(parts) >= 2:
            result["preventive_measure"] = parts[1]
    return result


# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading priority_results.csv ...")
df = pd.read_csv(INPUT_CSV, parse_dates=["date"])
assert df.shape == (181, 59), f"Expected (181, 59), got {df.shape}"

llm_mask = (
    df["layer4_priority_flag"].isin(["ESCALATE", "INVESTIGATE"])
    & ~df["escalation_suppressed"]
)
print(f"  LLM scope : {llm_mask.sum()} rows (ESCALATE + non-suppressed INVESTIGATE)")
print(f"  Playbook  : {(~llm_mask).sum()} rows (MONITOR + SUPPRESSED)")
print()

# ── Anthropic client ──────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ── Main loop ─────────────────────────────────────────────────────────────────
print("Generating recommendations ...")
print()

cols: dict[str, list] = {
    "playbook_match"    : [],
    "playbook_key"      : [],
    "playbook_actions"  : [],
    "immediate_action"  : [],
    "short_term_fix"    : [],
    "preventive_measure": [],
    "recommended_owner" : [],
    "effort_level"      : [],
    "llm_enhanced"      : [],
}

llm_calls     = 0
llm_failures  = 0
cache_hits    = 0
input_tokens  = 0
output_tokens = 0

for idx, row in df.iterrows():
    kpi       = row["kpi"]
    direction = row["direction"] if pd.notna(row["direction"]) else None
    driver    = row["suspected_driver_kpi"] if pd.notna(row["suspected_driver_kpi"]) else None

    # Step A: playbook lookup (all rows)
    pb = lookup_playbook(kpi, direction, driver)

    cols["playbook_match"].append(bool(pb))
    cols["playbook_key"].append(pb["key"] if pb else "no_match")
    cols["playbook_actions"].append(
        f"{pb['immediate']} | {pb['short_term']} | {pb['preventive']}" if pb else ""
    )

    # Step B: LLM enhancement (ESCALATE + INVESTIGATE only)
    if llm_mask.loc[idx]:
        llm_ok = False
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": build_user_prompt(row, pb)}],
            )

            parsed = parse_llm_response(response.content[0].text)
            usage  = response.usage
            input_tokens  += usage.input_tokens
            output_tokens += usage.output_tokens
            if getattr(usage, "cache_read_input_tokens", 0):
                cache_hits += 1

            cols["immediate_action"].append(parsed["immediate_action"])
            cols["short_term_fix"].append(parsed["short_term_fix"])
            cols["preventive_measure"].append(parsed["preventive_measure"])
            cols["recommended_owner"].append(
                parsed["recommended_owner"] or (pb["owner"] if pb else "Analytics")
            )
            cols["effort_level"].append(
                parsed["effort_level"] or (pb["effort"] if pb else "M")
            )
            cols["llm_enhanced"].append(True)

            llm_calls += 1
            llm_ok = True

            if llm_calls % 10 == 0:
                print(f"  [{llm_calls:>3}/101]  {row['anomaly_id']:<22}  "
                      f"tokens in={input_tokens:,}  out={output_tokens:,}  "
                      f"cache_hits={cache_hits}")

        except Exception as exc:
            print(f"  [WARN] LLM failed for {row['anomaly_id']}: {exc}")
            llm_failures += 1

        if not llm_ok:
            cols["immediate_action"].append(pb["immediate"] if pb else "Review anomaly details and assess impact")
            cols["short_term_fix"].append(pb["short_term"] if pb else "Investigate root cause with relevant team")
            cols["preventive_measure"].append(pb["preventive"] if pb else "Set monitoring alert for this KPI")
            cols["recommended_owner"].append(pb["owner"] if pb else "Analytics")
            cols["effort_level"].append(pb["effort"] if pb else "M")
            cols["llm_enhanced"].append(False)

    else:
        # MONITOR / SUPPRESSED: playbook text only, no LLM
        cols["immediate_action"].append(pb["immediate"] if pb else "Monitor KPI trend over next 3 days")
        cols["short_term_fix"].append(pb["short_term"] if pb else "Review KPI in weekly digest")
        cols["preventive_measure"].append(pb["preventive"] if pb else "Set alert threshold for this KPI")
        cols["recommended_owner"].append(pb["owner"] if pb else "Analytics")
        cols["effort_level"].append(pb["effort"] if pb else "L")
        cols["llm_enhanced"].append(False)

# ── Assemble and write ────────────────────────────────────────────────────────
print()
out = df.copy()
for col, vals in cols.items():
    out[col] = vals

assert out.shape == (181, 68), f"Expected (181, 68), got {out.shape}"

print("Writing outputs ...")
out.to_csv(OUTPUT_CSV, index=False)
conn = sqlite3.connect(DB_PATH)
out.to_sql("recommendations", conn, if_exists="replace", index=False)
conn.close()
print(f"  Saved {OUTPUT_CSV}")
print(f"  Saved SQLite table: recommendations")
print()

# ── Summary ───────────────────────────────────────────────────────────────────
print("=" * 68)
print("RECOMMENDATION ENGINE SUMMARY")
print("=" * 68)

print(f"\nCoverage:")
print(f"  LLM-enhanced      : {out['llm_enhanced'].sum():>3} / 181")
print(f"  Playbook match    : {out['playbook_match'].sum():>3} / 181")
print(f"  No playbook match : {(~out['playbook_match']).sum():>3} / 181")
print(f"  LLM calls made    : {llm_calls:>3}  (failures: {llm_failures})")
print(f"  Cache hits        : {cache_hits:>3}")
print(f"  Total input tokens : {input_tokens:,}")
print(f"  Total output tokens: {output_tokens:,}")

print("\nPlaybook key distribution (top 10):")
for key, n in out["playbook_key"].value_counts().head(10).items():
    print(f"  {key:<35}  {n:>3}")

print("\nEffort level distribution:")
for effort in ["H", "M", "L"]:
    n = (out["effort_level"] == effort).sum()
    print(f"  {effort}  {n:>3}  ({n/181*100:.1f}%)")

print("\nOwner distribution (top 8):")
for owner, n in out["recommended_owner"].value_counts().head(8).items():
    print(f"  {owner:<40}  {n:>3}")

# Spot checks
bf = out[(out["date"] == "2024-11-29") & (out["kpi"] == "total_revenue_usd")].iloc[0]
sk = out[(out["date"] == "2024-03-15") & (out["kpi"] == "n_orders")].iloc[0]
print(f"\nSpot checks:")
print(f"  Black Friday {bf['anomaly_id']}:")
print(f"    Immediate : {str(bf['immediate_action'])[:90]}")
print(f"    LLM       : {bf['llm_enhanced']}")
print(f"  Stockout {sk['anomaly_id']}:")
print(f"    Immediate : {str(sk['immediate_action'])[:90]}")
print(f"    LLM       : {sk['llm_enhanced']}")

print()
print("Step 4.3 complete -- recommendations.csv written (181 rows x 68 cols).")
