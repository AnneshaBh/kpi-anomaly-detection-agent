# KPI Anomaly Detection — Operations Digest

**Report generated:** 2026-06-16 11:38  
**Analysis period:** 2024-01-11 – 2025-12-24  
**Audience:** Operations, Performance Marketing, Product & Engineering  

---

## Summary

| | |
|---|---|
| Total actionable anomalies | 102 |
| Immediate escalation (ESCALATE) | 15 |
| Daily investigation (INVESTIGATE) | 87 |
| Revenue at risk | $241,688 |
| Captured upside | $3,092,643 |

---

## Part 1 — ESCALATE: Immediate Action Required
_15 anomalies — Urgency: Immediate — Channel: Slack + Email_

### #1 — ANO-20241129-REV | Total Revenue (USD) | 2024-11-29

**Severity:** HIGH | **Movement:** UP +223.8% | **Revenue Impact:** $319,977 upside  
**Owner:** Revenue Operations | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] total_revenue_usd moved UP +223.8% on 2024-11-29. Chain: total_revenue_usd -> avg_order_value_usd. Suspected driver: avg_order_value_usd. Causal confidence: 90%. No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm inventory availability to fulfil the demand surge; validate attribution and data integrity

**Short-term Fix:**  
Analyse customer segment and channel mix driving the surge; project 30-day forward demand

**Preventive Measure:**  
Build surge-response playbook: inventory buffers, dynamic pricing triggers, campaign scaling thresholds

---

### #2 — ANO-20251128-REV | Total Revenue (USD) | 2025-11-28

**Severity:** HIGH | **Movement:** UP +246.6% | **Revenue Impact:** $307,164 upside  
**Owner:** Revenue Operations | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] total_revenue_usd moved UP +246.6% on 2025-11-28. Chain: total_revenue_usd -> avg_order_value_usd. Suspected driver: avg_order_value_usd. Causal confidence: 90%. No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm inventory availability to fulfil the demand surge; validate attribution and data integrity

**Short-term Fix:**  
Analyse customer segment and channel mix driving the surge; project 30-day forward demand

**Preventive Measure:**  
Build surge-response playbook: inventory buffers, dynamic pricing triggers, campaign scaling thresholds

---

### #3 — ANO-20240111-ROAS | Avg. ROAS | 2024-01-11

**Severity:** HIGH | **Movement:** UP +304.4% | **Revenue Impact:** $74,895 upside  
**Owner:** Performance Marketing | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] avg_roas moved UP +304.4% on 2024-01-11. Chain: avg_roas -> total_clicks. Suspected driver: total_clicks. Causal confidence: 90%. No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm attribution accuracy; check for pixel or tracking changes inflating attributed revenue

**Short-term Fix:**  
Identify campaigns driving ROAS and click uplift; reallocate budget toward top performers

**Preventive Measure:**  
Document the campaign mix and bid strategy driving this efficiency as a replication playbook

---

### #4 — ANO-20250525-ROAS | Avg. ROAS | 2025-05-25

**Severity:** HIGH | **Movement:** UP +263.9% | **Revenue Impact:** $64,923 upside  
**Owner:** Performance Marketing | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] avg_roas moved UP +263.9% on 2025-05-25. Chain: avg_roas -> total_clicks. Suspected driver: total_clicks. Causal confidence: 90%. No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm attribution accuracy; check for pixel or tracking changes inflating attributed revenue

**Short-term Fix:**  
Identify campaigns driving ROAS and click uplift; reallocate budget toward top performers

**Preventive Measure:**  
Document the campaign mix and bid strategy driving this efficiency as a replication playbook

---

### #6 — ANO-20240820-REV | Total Revenue (USD) | 2024-08-20

**Severity:** HIGH | **Movement:** UP +49.1% | **Revenue Impact:** $52,190 upside  
**Owner:** Revenue Operations | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] total_revenue_usd moved UP +49.1% on 2024-08-20. Chain: total_revenue_usd -> n_orders -> sessions. Suspected driver: sessions. Causal confidence: 90%. No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm inventory availability to fulfil the demand surge; validate attribution and data integrity

**Short-term Fix:**  
Analyse customer segment and channel mix driving the surge; project 30-day forward demand

**Preventive Measure:**  
Build surge-response playbook: inventory buffers, dynamic pricing triggers, campaign scaling thresholds

---

### #7 — ANO-20240820-ORD | Order Volume | 2024-08-20

**Severity:** HIGH | **Movement:** UP +50.9% | **Revenue Impact:** $50,152 upside  
**Owner:** Operations / Supply Chain | **Effort:** Medium — same-day task  
**Root cause:** [HIGH] n_orders moved UP +50.9% on 2024-08-20. Chain: n_orders -> sessions. Suspected driver: sessions. Causal confidence: 90%. No external suppression. Fully actionable.  

**Immediate Action:**  
Verify fulfilment capacity and SLA commitments can handle the order spike volume

**Short-term Fix:**  
Scale customer support capacity; fast-track inventory reorder for top-revenue SKUs

**Preventive Measure:**  
Build demand forecasting model linking session volume to order spikes for proactive capacity planning

---

### #10 — ANO-20241202-REV | Total Revenue (USD) | 2024-12-02

**Severity:** HIGH | **Movement:** UP +44.7% | **Revenue Impact:** $74,532 upside  
**Owner:** Revenue Operations | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] total_revenue_usd moved UP +44.7% on 2024-12-02. Root: total_revenue_usd (no deeper driver above watch threshold). No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm inventory availability to fulfil the demand surge; validate attribution and data integrity

**Short-term Fix:**  
Analyse customer segment and channel mix driving the surge; project 30-day forward demand

**Preventive Measure:**  
Build surge-response playbook: inventory buffers, dynamic pricing triggers, campaign scaling thresholds

---

### #15 — ANO-20250114-ROAS | Avg. ROAS | 2025-01-14

**Severity:** HIGH | **Movement:** UP +173.8% | **Revenue Impact:** $42,747 upside  
**Owner:** Performance Marketing | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] avg_roas moved UP +173.8% on 2025-01-14. Root: avg_roas (no deeper driver above watch threshold). No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

**Short-term Fix:**  
Identify which campaigns and keywords are driving the uplift; scale budget toward those performers

**Preventive Measure:**  
Document the channel mix and bid strategy driving this efficiency for future campaign planning

---

### #16 — ANO-20240131-ROAS | Avg. ROAS | 2024-01-31

**Severity:** HIGH | **Movement:** UP +165.6% | **Revenue Impact:** $40,739 upside  
**Owner:** Performance Marketing | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] avg_roas moved UP +165.6% on 2024-01-31. Root: avg_roas (no deeper driver above watch threshold). No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

**Short-term Fix:**  
Identify which campaigns and keywords are driving the uplift; scale budget toward those performers

**Preventive Measure:**  
Document the channel mix and bid strategy driving this efficiency for future campaign planning

---

### #17 — ANO-20241129-ROAS | Avg. ROAS | 2024-11-29

**Severity:** HIGH | **Movement:** UP +159.7% | **Revenue Impact:** $39,300 upside  
**Owner:** Performance Marketing | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] avg_roas moved UP +159.7% on 2024-11-29. Root: avg_roas (no deeper driver above watch threshold). No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

**Short-term Fix:**  
Identify which campaigns and keywords are driving the uplift; scale budget toward those performers

**Preventive Measure:**  
Document the channel mix and bid strategy driving this efficiency for future campaign planning

---

### #18 — ANO-20251128-ORD | Order Volume | 2025-11-28

**Severity:** HIGH | **Movement:** UP +42.2% | **Revenue Impact:** $34,544 upside  
**Owner:** Operations | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] n_orders moved UP +42.2% on 2025-11-28. Root: n_orders (no deeper driver above watch threshold). No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm fulfilment capacity; flag to warehouse team for additional staffing if needed

**Short-term Fix:**  
Identify customer segments and channels driving the surge; optimise for repeat purchase

**Preventive Measure:**  
Build order surge protocols with auto-scaling triggers for fulfilment and support resources

---

### #19 — ANO-20241129-ORD | Order Volume | 2024-11-29

**Severity:** HIGH | **Movement:** UP +37.3% | **Revenue Impact:** $33,855 upside  
**Owner:** Operations | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] n_orders moved UP +37.3% on 2024-11-29. Root: n_orders (no deeper driver above watch threshold). No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm fulfilment capacity; flag to warehouse team for additional staffing if needed

**Short-term Fix:**  
Identify customer segments and channels driving the surge; optimise for repeat purchase

**Preventive Measure:**  
Build order surge protocols with auto-scaling triggers for fulfilment and support resources

---

### #23 — ANO-20250924-ROAS | Avg. ROAS | 2025-09-24

**Severity:** HIGH | **Movement:** UP +92.6% | **Revenue Impact:** $22,774 upside  
**Owner:** Performance Marketing | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] avg_roas moved UP +92.6% on 2025-09-24. Root: avg_roas (no deeper driver above watch threshold). No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

**Short-term Fix:**  
Identify which campaigns and keywords are driving the uplift; scale budget toward those performers

**Preventive Measure:**  
Document the channel mix and bid strategy driving this efficiency for future campaign planning

---

### #27 — ANO-20250925-ROAS | Avg. ROAS | 2025-09-25

**Severity:** HIGH | **Movement:** UP +60.0% | **Revenue Impact:** $14,764 upside  
**Owner:** Performance Marketing | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] avg_roas moved UP +60.0% on 2025-09-25. Root: avg_roas (no deeper driver above watch threshold). No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

**Short-term Fix:**  
Identify which campaigns and keywords are driving the uplift; scale budget toward those performers

**Preventive Measure:**  
Document the channel mix and bid strategy driving this efficiency for future campaign planning

---

### #29 — ANO-20241202-ORD | Order Volume | 2024-12-02

**Severity:** HIGH | **Movement:** UP +13.3% | **Revenue Impact:** $12,681 upside  
**Owner:** Operations | **Effort:** Low — < 1 hour check  
**Root cause:** [HIGH] n_orders moved UP +13.3% on 2024-12-02. Root: n_orders (no deeper driver above watch threshold). No external suppression. Fully actionable.  

**Immediate Action:**  
Confirm fulfilment capacity; flag to warehouse team for additional staffing if needed

**Short-term Fix:**  
Identify customer segments and channels driving the surge; optimise for repeat purchase

**Preventive Measure:**  
Build order surge protocols with auto-scaling triggers for fulfilment and support resources

---

## Part 2 — INVESTIGATE: Daily Review
_87 anomalies — Urgency: Daily — Channel: Email_

### Avg. ROAS (Tier 1) — 50 anomalies
_Primary owner: Performance Marketing_

| Rank | Anomaly ID | Date | Severity | Movement | Revenue Impact | Effort |
|------|-----------|------|----------|----------|----------------|--------|
| #5 | ANO-20241031-ROAS | 2024-10-31 | MEDIUM | UP +234.6% | $57,717 upside | Low — < 1 hour check |
| #8 | ANO-20240428-ROAS | 2024-04-28 | MEDIUM | UP +197.7% | $48,634 upside | Low — < 1 hour check |
| #9 | ANO-20251224-ROAS | 2025-12-24 | MEDIUM | UP +169.9% | $41,790 upside | Low — < 1 hour check |
| #11 | ANO-20241024-ROAS | 2024-10-24 | MEDIUM | UP +114.8% | $28,244 upside | Low — < 1 hour check |
| #13 | ANO-20240227-ROAS | 2024-02-27 | MEDIUM | UP +96.9% | $23,847 upside | Low — < 1 hour check |
| #14 | ANO-20250609-ROAS | 2025-06-09 | MEDIUM | UP +87.2% | $21,441 upside | Low — < 1 hour check |
| #21 | ANO-20251128-ROAS | 2025-11-28 | MEDIUM | DOWN -58.8% | $14,464 at risk | High — multi-day, cross-team |
| #34 | ANO-20240809-ROAS | 2024-08-09 | MEDIUM | UP +265.1% | $65,226 upside | Low — < 1 hour check |
| #35 | ANO-20250121-ROAS | 2025-01-21 | MEDIUM | UP +263.1% | $64,724 upside | Low — < 1 hour check |
| #36 | ANO-20240130-ROAS | 2024-01-30 | MEDIUM | UP +259.1% | $63,747 upside | Low — < 1 hour check |
| #37 | ANO-20250920-ROAS | 2025-09-20 | MEDIUM | UP +229.6% | $56,480 upside | Low — < 1 hour check |
| #39 | ANO-20240412-ROAS | 2024-04-12 | MEDIUM | UP +195.6% | $48,110 upside | Low — < 1 hour check |
| #40 | ANO-20251108-ROAS | 2025-11-08 | MEDIUM | UP +192.1% | $47,259 upside | Low — < 1 hour check |
| #41 | ANO-20240708-ROAS | 2024-07-08 | MEDIUM | UP +184.1% | $45,300 upside | Low — < 1 hour check |
| #42 | ANO-20240311-ROAS | 2024-03-11 | MEDIUM | UP +161.9% | $39,841 upside | Low — < 1 hour check |
| #43 | ANO-20240601-ROAS | 2024-06-01 | MEDIUM | UP +148.2% | $36,466 upside | Low — < 1 hour check |
| #44 | ANO-20240612-ROAS | 2024-06-12 | MEDIUM | UP +143.2% | $35,238 upside | Low — < 1 hour check |
| #45 | ANO-20240624-ROAS | 2024-06-24 | MEDIUM | UP +142.0% | $34,933 upside | Low — < 1 hour check |
| #46 | ANO-20250127-ROAS | 2025-01-27 | MEDIUM | DOWN -7.3% | $1,801 at risk | High — multi-day, cross-team |
| #47 | ANO-20250830-ROAS | 2025-08-30 | MEDIUM | UP +131.2% | $32,281 upside | Low — < 1 hour check |
| #48 | ANO-20250430-ROAS | 2025-04-30 | MEDIUM | UP +124.2% | $30,556 upside | Low — < 1 hour check |
| #50 | ANO-20250226-ROAS | 2025-02-26 | MEDIUM | UP +121.1% | $29,789 upside | Low — < 1 hour check |
| #51 | ANO-20250217-ROAS | 2025-02-17 | MEDIUM | UP +117.7% | $28,945 upside | Low — < 1 hour check |
| #52 | ANO-20250726-ROAS | 2025-07-26 | MEDIUM | UP +116.7% | $28,701 upside | Low — < 1 hour check |
| #53 | ANO-20250819-ROAS | 2025-08-19 | MEDIUM | UP +113.8% | $27,995 upside | Low — < 1 hour check |
| #55 | ANO-20240429-ROAS | 2024-04-29 | MEDIUM | UP +111.7% | $27,481 upside | Low — < 1 hour check |
| #56 | ANO-20250131-ROAS | 2025-01-31 | MEDIUM | UP +105.9% | $26,054 upside | Low — < 1 hour check |
| #57 | ANO-20240711-ROAS | 2024-07-11 | MEDIUM | UP +96.6% | $23,776 upside | Low — < 1 hour check |
| #58 | ANO-20240814-ROAS | 2024-08-14 | MEDIUM | UP +90.6% | $22,292 upside | Low — < 1 hour check |
| #59 | ANO-20250707-ROAS | 2025-07-07 | MEDIUM | UP +90.1% | $22,167 upside | Low — < 1 hour check |
| #60 | ANO-20240723-ROAS | 2024-07-23 | MEDIUM | DOWN -88.4% | $21,758 at risk | Medium — same-day task |
| #61 | ANO-20240817-ROAS | 2024-08-17 | MEDIUM | UP +86.1% | $21,173 upside | Low — < 1 hour check |
| #62 | ANO-20250505-ROAS | 2025-05-05 | MEDIUM | UP +77.3% | $19,015 upside | Low — < 1 hour check |
| #63 | ANO-20250710-ROAS | 2025-07-10 | MEDIUM | UP +74.6% | $18,351 upside | Low — < 1 hour check |
| #64 | ANO-20240621-ROAS | 2024-06-21 | MEDIUM | DOWN -74.1% | $18,221 at risk | Medium — same-day task |
| #65 | ANO-20250220-ROAS | 2025-02-20 | MEDIUM | UP +72.6% | $17,864 upside | Low — < 1 hour check |
| #66 | ANO-20240626-ROAS | 2024-06-26 | MEDIUM | DOWN -67.8% | $16,668 at risk | Medium — same-day task |
| #67 | ANO-20250917-ROAS | 2025-09-17 | MEDIUM | DOWN -61.1% | $15,035 at risk | Medium — same-day task |
| #69 | ANO-20240710-ROAS | 2024-07-10 | MEDIUM | DOWN -59.4% | $14,621 at risk | Medium — same-day task |
| #70 | ANO-20250129-ROAS | 2025-01-29 | MEDIUM | UP +56.7% | $13,942 upside | Low — < 1 hour check |
| #71 | ANO-20240202-ROAS | 2024-02-02 | MEDIUM | UP +54.4% | $13,384 upside | Low — < 1 hour check |
| #73 | ANO-20240820-ROAS | 2024-08-20 | MEDIUM | DOWN -53.1% | $13,061 at risk | Medium — same-day task |
| #74 | ANO-20240620-ROAS | 2024-06-20 | MEDIUM | UP +52.9% | $13,010 upside | Low — < 1 hour check |
| #75 | ANO-20250130-ROAS | 2025-01-30 | MEDIUM | UP +47.8% | $11,750 upside | Low — < 1 hour check |
| #76 | ANO-20240417-ROAS | 2024-04-17 | MEDIUM | DOWN -46.2% | $11,364 at risk | Medium — same-day task |
| #77 | ANO-20250202-ROAS | 2025-02-02 | MEDIUM | UP +45.5% | $11,194 upside | Low — < 1 hour check |
| #78 | ANO-20241202-ROAS | 2024-12-02 | MEDIUM | UP +45.0% | $11,071 upside | Low — < 1 hour check |
| #79 | ANO-20240622-ROAS | 2024-06-22 | MEDIUM | DOWN -41.3% | $10,171 at risk | Medium — same-day task |
| #81 | ANO-20240619-ROAS | 2024-06-19 | MEDIUM | UP +23.8% | $5,846 upside | Low — < 1 hour check |
| #82 | ANO-20240821-ROAS | 2024-08-21 | MEDIUM | UP +22.5% | $5,543 upside | Low — < 1 hour check |

**Immediate Actions:**

**#5 (2024-10-31):** Confirm attribution accuracy; check for pixel or tracking changes inflating attributed revenue

_Short-term: Identify campaigns driving ROAS and click uplift; reallocate budget toward top performers_

**#8 (2024-04-28):** Confirm attribution accuracy; check for pixel or tracking changes inflating attributed revenue

_Short-term: Identify campaigns driving ROAS and click uplift; reallocate budget toward top performers_

**#9 (2025-12-24):** Confirm attribution accuracy; check for pixel or tracking changes inflating attributed revenue

_Short-term: Identify campaigns driving ROAS and click uplift; reallocate budget toward top performers_

**#11 (2024-10-24):** Confirm attribution accuracy; check for pixel or tracking changes inflating attributed revenue

_Short-term: Identify campaigns driving ROAS and click uplift; reallocate budget toward top performers_

**#13 (2024-02-27):** Confirm attribution accuracy; check for pixel or tracking changes inflating attributed revenue

_Short-term: Identify campaigns driving ROAS and click uplift; reallocate budget toward top performers_

**#14 (2025-06-09):** Confirm attribution accuracy; check for pixel or tracking changes inflating attributed revenue

_Short-term: Identify campaigns driving ROAS and click uplift; reallocate budget toward top performers_

**#21 (2025-11-28):** Pause ad groups with CPA > $50; audit for account-level policy violations or budget exhaustion

_Short-term: Review keyword targeting and negative-keyword lists; run auction insights to diagnose competitor spend surge_

**#34 (2024-08-09):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#35 (2025-01-21):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#36 (2024-01-30):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#37 (2025-09-20):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#39 (2024-04-12):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#40 (2025-11-08):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#41 (2024-07-08):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#42 (2024-03-11):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#43 (2024-06-01):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#44 (2024-06-12):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#45 (2024-06-24):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#46 (2025-01-27):** Pause ad groups with CPA > $50; audit for account-level policy violations or budget exhaustion

_Short-term: Review keyword targeting and negative-keyword lists; run auction insights to diagnose competitor spend surge_

**#47 (2025-08-30):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#48 (2025-04-30):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#50 (2025-02-26):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#51 (2025-02-17):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#52 (2025-07-26):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#53 (2025-08-19):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#55 (2024-04-29):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#56 (2025-01-31):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#57 (2024-07-11):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#58 (2024-08-14):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#59 (2025-07-07):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#60 (2024-07-23):** Pause underperforming ad groups above $50 CPA; check for pixel tracking issues or attribution window changes

_Short-term: Shift 30% of budget from underperforming channels to email/organic; review bid strategy against target ROAS_

**#61 (2024-08-17):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#62 (2025-05-05):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#63 (2025-07-10):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#64 (2024-06-21):** Pause underperforming ad groups above $50 CPA; check for pixel tracking issues or attribution window changes

_Short-term: Shift 30% of budget from underperforming channels to email/organic; review bid strategy against target ROAS_

**#65 (2025-02-20):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#66 (2024-06-26):** Pause underperforming ad groups above $50 CPA; check for pixel tracking issues or attribution window changes

_Short-term: Shift 30% of budget from underperforming channels to email/organic; review bid strategy against target ROAS_

**#67 (2025-09-17):** Pause underperforming ad groups above $50 CPA; check for pixel tracking issues or attribution window changes

_Short-term: Shift 30% of budget from underperforming channels to email/organic; review bid strategy against target ROAS_

**#69 (2024-07-10):** Pause underperforming ad groups above $50 CPA; check for pixel tracking issues or attribution window changes

_Short-term: Shift 30% of budget from underperforming channels to email/organic; review bid strategy against target ROAS_

**#70 (2025-01-29):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#71 (2024-02-02):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#73 (2024-08-20):** Pause underperforming ad groups above $50 CPA; check for pixel tracking issues or attribution window changes

_Short-term: Shift 30% of budget from underperforming channels to email/organic; review bid strategy against target ROAS_

**#74 (2024-06-20):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#75 (2025-01-30):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#76 (2024-04-17):** Pause underperforming ad groups above $50 CPA; check for pixel tracking issues or attribution window changes

_Short-term: Shift 30% of budget from underperforming channels to email/organic; review bid strategy against target ROAS_

**#77 (2025-02-02):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#78 (2024-12-02):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#79 (2024-06-22):** Pause underperforming ad groups above $50 CPA; check for pixel tracking issues or attribution window changes

_Short-term: Shift 30% of budget from underperforming channels to email/organic; review bid strategy against target ROAS_

**#81 (2024-06-19):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_

**#82 (2024-08-21):** Confirm attribution accuracy; verify no pixel or tracking anomalies are skewing attributed revenue

_Short-term: Identify which campaigns and keywords are driving the uplift; scale budget toward those performers_


### Conversion Rate (Tier 1) — 6 anomalies
_Primary owner: Pricing / CRO_

| Rank | Anomaly ID | Date | Severity | Movement | Revenue Impact | Effort |
|------|-----------|------|----------|----------|----------------|--------|
| #22 | ANO-20240618-CVR | 2024-06-18 | MEDIUM | UP +16.0% | $14,155 upside | Medium — same-day task |
| #24 | ANO-20240417-CVR | 2024-04-17 | MEDIUM | UP +11.3% | $10,110 upside | Medium — same-day task |
| #26 | ANO-20250925-CVR | 2025-09-25 | MEDIUM | UP +10.4% | $9,436 upside | Medium — same-day task |
| #38 | ANO-20240903-CVR | 2024-09-03 | MEDIUM | UP +65.8% | $52,575 upside | Low — < 1 hour check |
| #72 | ANO-20240620-CVR | 2024-06-20 | MEDIUM | UP +14.0% | $13,144 upside | Low — < 1 hour check |
| #80 | ANO-20250131-CVR | 2025-01-31 | MEDIUM | UP +7.9% | $8,088 upside | Low — < 1 hour check |

**Immediate Actions:**

**#22 (2024-06-18):** Validate conversion uplift is margin-positive after discount cost; check gross margin on converted orders

_Short-term: A/B test discount depth vs conversion rate to find the optimal profitability threshold_

**#24 (2024-04-17):** Validate conversion uplift is margin-positive after discount cost; check gross margin on converted orders

_Short-term: A/B test discount depth vs conversion rate to find the optimal profitability threshold_

**#26 (2025-09-25):** Validate conversion uplift is margin-positive after discount cost; check gross margin on converted orders

_Short-term: A/B test discount depth vs conversion rate to find the optimal profitability threshold_

**#38 (2024-09-03):** Confirm no tag or tracking changes could inflate counts; audit recent A/B test deployments

_Short-term: Identify landing page or checkout change driving the lift; document for rollout to other pages_

**#72 (2024-06-20):** Confirm no tag or tracking changes could inflate counts; audit recent A/B test deployments

_Short-term: Identify landing page or checkout change driving the lift; document for rollout to other pages_

**#80 (2025-01-31):** Confirm no tag or tracking changes could inflate counts; audit recent A/B test deployments

_Short-term: Identify landing page or checkout change driving the lift; document for rollout to other pages_


### Order Volume (Tier 1) — 6 anomalies
_Primary owner: Operations_

| Rank | Anomaly ID | Date | Severity | Movement | Revenue Impact | Effort |
|------|-----------|------|----------|----------|----------------|--------|
| #12 | ANO-20250210-ORD | 2025-02-10 | MEDIUM | DOWN -34.3% | $27,658 at risk | High — multi-day, cross-team |
| #25 | ANO-20240618-ORD | 2024-06-18 | MEDIUM | UP +11.2% | $9,755 upside | Medium — same-day task |
| #31 | ANO-20240417-ORD | 2024-04-17 | MEDIUM | UP +6.0% | $5,279 upside | Medium — same-day task |
| #54 | ANO-20240315-ORD | 2024-03-15 | MEDIUM | DOWN -35.7% | $27,888 at risk | Medium — same-day task |
| #68 | ANO-20251201-ORD | 2025-12-01 | MEDIUM | UP +17.1% | $14,747 upside | Low — < 1 hour check |
| #85 | ANO-20240723-ORD | 2024-07-23 | MEDIUM | UP +1.9% | $1,836 upside | Low — < 1 hour check |

**Immediate Actions:**

**#12 (2025-02-10):** Check checkout completion rate and payment errors; verify demand signals across all acquisition channels

_Short-term: Review competitive pricing; test deeper discount or bundle offers to stimulate demand recovery_

**#25 (2024-06-18):** Verify fulfilment capacity and SLA commitments can handle the order spike volume

_Short-term: Scale customer support capacity; fast-track inventory reorder for top-revenue SKUs_

**#31 (2024-04-17):** Verify fulfilment capacity and SLA commitments can handle the order spike volume

_Short-term: Scale customer support capacity; fast-track inventory reorder for top-revenue SKUs_

**#54 (2024-03-15):** Check checkout completion rate, payment errors, and whether active promotional codes are functioning

_Short-term: Activate win-back campaign for lapsed customers; review pricing vs nearest competitors_

**#68 (2025-12-01):** Confirm fulfilment capacity; flag to warehouse team for additional staffing if needed

_Short-term: Identify customer segments and channels driving the surge; optimise for repeat purchase_

**#85 (2024-07-23):** Confirm fulfilment capacity; flag to warehouse team for additional staffing if needed

_Short-term: Identify customer segments and channels driving the surge; optimise for repeat purchase_


### Total Revenue (USD) (Tier 1) — 6 anomalies
_Primary owner: Revenue Operations_

| Rank | Anomaly ID | Date | Severity | Movement | Revenue Impact | Effort |
|------|-----------|------|----------|----------|----------------|--------|
| #20 | ANO-20240618-REV | 2024-06-18 | MEDIUM | UP +16.8% | $14,636 upside | Low — < 1 hour check |
| #28 | ANO-20240622-REV | 2024-06-22 | MEDIUM | UP +6.9% | $6,567 upside | Low — < 1 hour check |
| #30 | ANO-20240417-REV | 2024-04-17 | MEDIUM | UP +6.6% | $6,107 upside | Low — < 1 hour check |
| #32 | ANO-20240723-REV | 2024-07-23 | MEDIUM | UP +4.2% | $4,571 upside | Low — < 1 hour check |
| #33 | ANO-20251201-REV | 2025-12-01 | MEDIUM | UP +52.3% | $77,076 upside | Low — < 1 hour check |
| #49 | ANO-20240315-REV | 2024-03-15 | MEDIUM | DOWN -36.5% | $30,382 at risk | High — multi-day, cross-team |

**Immediate Actions:**

**#20 (2024-06-18):** Confirm inventory availability to fulfil the demand surge; validate attribution and data integrity

_Short-term: Analyse customer segment and channel mix driving the surge; project 30-day forward demand_

**#28 (2024-06-22):** Confirm inventory availability to fulfil the demand surge; validate attribution and data integrity

_Short-term: Analyse customer segment and channel mix driving the surge; project 30-day forward demand_

**#30 (2024-04-17):** Confirm inventory availability to fulfil the demand surge; validate attribution and data integrity

_Short-term: Analyse customer segment and channel mix driving the surge; project 30-day forward demand_

**#32 (2024-07-23):** Confirm inventory availability to fulfil the demand surge; validate attribution and data integrity

_Short-term: Analyse customer segment and channel mix driving the surge; project 30-day forward demand_

**#33 (2025-12-01):** Confirm inventory availability to fulfil the demand surge; validate attribution and data integrity

_Short-term: Analyse customer segment and channel mix driving the surge; project 30-day forward demand_

**#49 (2024-03-15):** Check payment gateway health and checkout error logs; verify all promotional codes are active

_Short-term: Activate win-back campaign for 30-day lapsed customers; A/B test checkout friction points_


### Avg. Order Value (USD) (Tier 2) — 5 anomalies
_Primary owner: Merchandising / Product_

| Rank | Anomaly ID | Date | Severity | Movement | Revenue Impact | Effort |
|------|-----------|------|----------|----------|----------------|--------|
| #83 | ANO-20251128-AOV | 2025-11-28 | MEDIUM | UP +173.6% | $191,330 upside | Low — < 1 hour check |
| #84 | ANO-20241129-AOV | 2024-11-29 | MEDIUM | UP +159.2% | $185,794 upside | Low — < 1 hour check |
| #87 | ANO-20241202-AOV | 2024-12-02 | MEDIUM | UP +38.7% | $50,900 upside | Low — < 1 hour check |
| #97 | ANO-20240618-AOV | 2024-06-18 | MEDIUM | UP +5.2% | $4,191 upside | Low — < 1 hour check |
| #101 | ANO-20240723-AOV | 2024-07-23 | MEDIUM | UP +2.2% | $2,080 upside | Low — < 1 hour check |

**Immediate Actions:**

**#83 (2025-11-28):** Confirm uplift is not driven by a data error, test orders, or one-off large B2B purchase

_Short-term: Identify which product categories, bundles, or upsell features are driving higher AOV_

**#84 (2024-11-29):** Confirm uplift is not driven by a data error, test orders, or one-off large B2B purchase

_Short-term: Identify which product categories, bundles, or upsell features are driving higher AOV_

**#87 (2024-12-02):** Confirm uplift is not driven by a data error, test orders, or one-off large B2B purchase

_Short-term: Identify which product categories, bundles, or upsell features are driving higher AOV_

**#97 (2024-06-18):** Confirm uplift is not driven by a data error, test orders, or one-off large B2B purchase

_Short-term: Identify which product categories, bundles, or upsell features are driving higher AOV_

**#101 (2024-07-23):** Confirm uplift is not driven by a data error, test orders, or one-off large B2B purchase

_Short-term: Identify which product categories, bundles, or upsell features are driving higher AOV_


### Bounce Rate (Tier 2) — 5 anomalies
_Primary owner: Product / Engineering_

| Rank | Anomaly ID | Date | Severity | Movement | Revenue Impact | Effort |
|------|-----------|------|----------|----------|----------------|--------|
| #92 | ANO-20250204-BNC | 2025-02-04 | MEDIUM | UP +20.7% | $6,783 at risk | Medium — same-day task |
| #96 | ANO-20240626-BNC | 2024-06-26 | MEDIUM | UP +12.9% | $4,461 at risk | Medium — same-day task |
| #98 | ANO-20250127-BNC | 2025-01-27 | MEDIUM | UP +11.0% | $3,883 at risk | Medium — same-day task |
| #99 | ANO-20240710-BNC | 2024-07-10 | MEDIUM | DOWN -10.5% | $3,544 upside | Low — < 1 hour check |
| #100 | ANO-20241105-BNC | 2024-11-05 | MEDIUM | UP +7.5% | $2,644 at risk | Medium — same-day task |

**Immediate Actions:**

**#92 (2025-02-04):** Check for page errors, load times over 3s, or broken mobile layouts; review recent deployments

_Short-term: Run UX audit on highest-traffic entry pages; roll back A/B tests launched in the last 7 days_

**#96 (2024-06-26):** Check for page errors, load times over 3s, or broken mobile layouts; review recent deployments

_Short-term: Run UX audit on highest-traffic entry pages; roll back A/B tests launched in the last 7 days_

**#98 (2025-01-27):** Check for page errors, load times over 3s, or broken mobile layouts; review recent deployments

_Short-term: Run UX audit on highest-traffic entry pages; roll back A/B tests launched in the last 7 days_

**#99 (2024-07-10):** Confirm improvement is genuine and not a tracking or session-timeout configuration change

_Short-term: Identify which pages or traffic sources drove the improvement; replicate the approach_

**#100 (2024-11-05):** Check for page errors, load times over 3s, or broken mobile layouts; review recent deployments

_Short-term: Run UX audit on highest-traffic entry pages; roll back A/B tests launched in the last 7 days_


### Stockout Count (Tier 2) — 5 anomalies
_Primary owner: Analytics_

| Rank | Anomaly ID | Date | Severity | Movement | Revenue Impact | Effort |
|------|-----------|------|----------|----------|----------------|--------|
| #123 | ANO-20240619-STK | 2024-06-19 | MEDIUM | UP +600.0% | $281 at risk | High — multi-day, cross-team |
| #153 | ANO-20240626-STK | 2024-06-26 | MEDIUM | DOWN -100.0% | $47 upside | Low — < 1 hour check |
| #179 | ANO-20240417-STK | 2024-04-17 | MEDIUM | Elevated | $0 | Medium — same-day task |
| #180 | ANO-20241105-STK | 2024-11-05 | MEDIUM | Elevated | $0 | Medium — same-day task |
| #181 | ANO-20241216-STK | 2024-12-16 | MEDIUM | Elevated | $0 | Medium — same-day task |

**Immediate Actions:**

**#123 (2024-06-19):** Trigger emergency reorder for top 20 SKUs by revenue; surface in-stock alternatives in recommendation engine

_Short-term: Escalate to merchandising and supplier teams; increase demand forecast for affected SKUs_

**#153 (2024-06-26):** Confirm replenishment has arrived and inventory levels are accurate across all fulfilment nodes

_Short-term: Re-enable paid ads for previously out-of-stock SKUs; update availability on all sales channels_

**#179 (2024-04-17):** Review anomaly details and assess impact

_Short-term: Investigate root cause with relevant team_

**#180 (2024-11-05):** Review anomaly details and assess impact

_Short-term: Investigate root cause with relevant team_

**#181 (2024-12-16):** Review anomaly details and assess impact

_Short-term: Investigate root cause with relevant team_


### Return Rate (Tier 2) — 4 anomalies
_Primary owner: Customer Experience_

| Rank | Anomaly ID | Date | Severity | Movement | Revenue Impact | Effort |
|------|-----------|------|----------|----------|----------------|--------|
| #135 | ANO-20250114-RET | 2025-01-14 | MEDIUM | DOWN -2.2% | $138 upside | Low — < 1 hour check |
| #139 | ANO-20240620-RET | 2024-06-20 | MEDIUM | DOWN -1.9% | $122 upside | Low — < 1 hour check |
| #160 | ANO-20250129-RET | 2025-01-29 | MEDIUM | UP +4.7% | $317 at risk | Medium — same-day task |
| #168 | ANO-20240626-RET | 2024-06-26 | MEDIUM | UP +3.6% | $228 at risk | Medium — same-day task |

**Immediate Actions:**

**#135 (2025-01-14):** Confirm improvement is genuine and not caused by a processing backlog or return policy change

_Short-term: Identify which categories or segments show most improvement; share learnings across teams_

**#139 (2024-06-20):** Confirm improvement is genuine and not caused by a processing backlog or return policy change

_Short-term: Identify which categories or segments show most improvement; share learnings across teams_

**#160 (2025-01-29):** Pull return reason codes from last 48h; identify top 5 returned SKUs and primary return reasons

_Short-term: Review product descriptions and sizing accuracy for high-return SKUs; audit recent shipment quality_

**#168 (2024-06-26):** Pull return reason codes from last 48h; identify top 5 returned SKUs and primary return reasons

_Short-term: Review product descriptions and sizing accuracy for high-return SKUs; audit recent shipment quality_


---

## Effort Key

| Code | Description |
|------|-------------|
| H | High — multi-day, cross-team coordination required |
| M | Medium — same-day task, single team |
| L | Low — under 1-hour check |

---

_Generated by KPI Anomaly Detection Agent — Layer 5 Communication Layer_  
_Report timestamp: 2026-06-16 11:38_