# KPI Anomaly Detection — Executive Summary

**Report generated:** 2026-06-03 07:28  
**Analysis period:** 2024-01-11 – 2025-12-26  
**Audience:** Executive Leadership, Business Leads  

---

## 1. Situation Overview

| Metric | Value |
|--------|-------|
| Total anomalies detected | 181 |
| Immediate escalation (ESCALATE) | 15 |
| Under investigation (INVESTIGATE) | 86 |
| Monitoring (MONITOR) | 74 |
| Suppressed — external factors | 6 |
| Revenue at risk (7-day) | $800,375 |
| Captured upside (7-day) | $4,381,894 |
| Net margin benefit | $1,779,234 |
| Estimated customers affected | 64,988 |

> **Net position:** Captured upside ($4,381,894) significantly exceeds revenue at risk ($800,375), delivering a net margin benefit of $1,779,234.

---

## 2. Priority & Routing Dashboard

| Priority Band | Count | % of Total | Routing Breakdown |
|---------------|-------|------------|-------------------|
| HIGH   | 85 | 47.0% | ESCALATE (15) + INVESTIGATE (69) + SUPPRESSED (1) |
| MEDIUM | 89 | 49.2% | INVESTIGATE (14) + MONITOR (70) + SUPPRESSED (5) |
| LOW    | 7 | 3.9% | INVESTIGATE (3) + MONITOR (4) |

| Routing Flag | Count | Audience | Channel | Urgency |
|---|---|---|---|---|
| ESCALATE | 15 | Executive, Operations | Slack + Email | Immediate |
| INVESTIGATE | 86 | Operations, Analyst | Email | Daily |
| MONITOR | 74 | Analyst | Digest | Weekly |
| SUPPRESSED | 6 | None (audit log) | None | Suppressed |

---

## 3. Top 15 Anomalies — Immediate Escalation Required

_All 15 ESCALATE anomalies are HIGH-severity positive deviations. Captured upside exceeds downside risk. Priority is to sustain and capitalise on these surges._

| Rank | Date | KPI | Movement | Revenue Impact | Owner | Effort |
|------|------|-----|----------|----------------|-------|--------|
| #1 | 2024-11-29 | Total Revenue (USD) | UP +223.8% | $319,977 upside | Revenue Operations + Product | Low — < 1 hour check |
| #2 | 2025-11-28 | Total Revenue (USD) | UP +246.6% | $307,164 upside | Revenue Operations + Product + Supply Chain | Low — < 1 hour check |
| #3 | 2024-12-02 | Total Revenue (USD) | UP +44.7% | $74,532 upside | Revenue Operations + Product | Low — < 1 hour check |
| #4 | 2024-08-20 | Total Revenue (USD) | UP +49.1% | $52,190 upside | Revenue Operations + Supply Chain | Medium — same-day task |
| #5 | 2024-08-20 | Order Volume | UP +50.9% | $50,152 upside | Revenue Operations + Supply Chain | Medium — same-day task |
| #6 | 2024-01-11 | Avg. ROAS | UP +304.4% | $74,895 upside | Performance Marketing + Revenue Operations | Low — < 1 hour check |
| #7 | 2025-11-28 | Order Volume | UP +42.2% | $34,544 upside | Supply Chain / Operations | High — multi-day, cross-team |
| #8 | 2024-11-29 | Order Volume | UP +37.3% | $33,855 upside | Supply Chain / Warehouse Operations | Medium — same-day task |
| #9 | 2025-05-25 | Avg. ROAS | UP +263.9% | $64,923 upside | Performance Marketing | Low — < 1 hour check |
| #18 | 2025-09-24 | Avg. ROAS | UP +92.6% | $22,774 upside | Performance Marketing | Low — < 1 hour check |
| #22 | 2024-11-29 | Avg. ROAS | UP +159.7% | $39,300 upside | Performance Marketing | Low — < 1 hour check |
| #24 | 2024-01-31 | Avg. ROAS | UP +165.6% | $40,739 upside | Performance Marketing | Low — < 1 hour check |
| #27 | 2024-12-02 | Order Volume | UP +13.3% | $12,681 upside | Revenue Operations + Supply Chain | Low — < 1 hour check |
| #31 | 2025-01-14 | Avg. ROAS | UP +173.8% | $42,747 upside | Performance Marketing | Low — < 1 hour check |
| #50 | 2025-09-25 | Avg. ROAS | UP +60.0% | $14,764 upside | Performance Marketing | Low — < 1 hour check |

---

## 4. KPI Performance Overview

| KPI | Tier | Anomalies | HIGH Priority | Revenue at Risk | Captured Upside |
|-----|------|-----------|---------------|-----------------|-----------------|
| Avg. ROAS | 1 | 62 | 57 | $206,237 | $1,499,074 |
| Order Volume | 1 | 10 | 10 | $55,546 | $162,850 |
| Total Revenue (USD) | 1 | 10 | 10 | $30,382 | $862,820 |
| Conversion Rate | 1 | 6 | 6 | $0 | $107,508 |
| Avg. Order Value (USD) | 2 | 5 | 2 | $0 | $434,295 |
| Bounce Rate | 2 | 5 | 0 | $17,771 | $3,544 |
| Stockout Count | 2 | 5 | 0 | $281 | $47 |
| Return Rate | 2 | 4 | 0 | $545 | $260 |
| Inventory Health | 3 | 28 | 0 | $56,403 | $200,179 |
| Total Clicks | 3 | 24 | 0 | $368,599 | $430,280 |
| Avg. Discount % | 3 | 15 | 0 | $18,280 | $0 |
| Website Sessions | 3 | 7 | 0 | $46,331 | $681,036 |

---

## 5. External Market Factors

**8 anomalies** were attributed to external market conditions. **6 were suppressed** — no action required.

| External Driver | Anomalies | Suppressed | KPIs Affected |
|----------------|-----------|------------|---------------|
| competitive_pressure | 6 | 6 | avg_roas |
| consumer_sentiment_decline | 2 | 0 | return_rate |

---

## 6. Recommended Next Steps

1. **Immediate (today):** Review all 15 ESCALATE anomalies in the Operations Digest. Focus on sustaining the revenue surges in Total Revenue and Order Volume — verify inventory and fulfilment capacity is not a bottleneck.

2. **Daily (this week):** Operations and Performance Marketing to work through the 86 INVESTIGATE anomalies, starting with the highest-ranked. Avg. ROAS anomalies dominate this list — review campaign performance and attribution quality.

3. **Weekly (ongoing):** Analyst team to monitor the 74 MONITOR anomalies in the Monitoring Digest. No immediate action required; trend-watch only and escalate if patterns persist.

---

_Generated by KPI Anomaly Detection Agent — Layer 5 Communication Layer_  
_Report timestamp: 2026-06-03 07:28_