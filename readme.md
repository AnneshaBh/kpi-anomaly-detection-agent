# KPI Anomaly Detection Agent — Complete Architecture

An agent that automatically detects anomalies in primary KPIs, sends immediate alerts, identifies root causes via causal inference, explains business impact, prioritizes what matters, recommends actions, and generates executive summaries.

---

## Architecture Overview — 6 Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 1 │  Data Foundation        → Ingestion, Storage, Feature Eng.  │
│  LAYER 2 │  Anomaly Detection      → Statistical + ML detection         │
│  LAYER 3 │  Root Cause Analysis    → Causal inference, drill-down       │
│  LAYER 4 │  Intelligence Engine    → Impact, Prioritization, Actions    │
│  LAYER 5 │  Communication Layer    → Alerts, Summaries, Power BI        │
│  LAYER 6 │  Agent Orchestration    → LLM brain coordinating all layers  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## LAYER 1 — Data Foundation

### Step 1.1 — Synthetic Data (master_dataset.csv)

The daily backbone is `data/master_dataset.csv` — 33 KPI columns including ground-truth labels (`anomaly_flag`, `anomaly_event`, `anomaly_kpi`). Dimensional tables (`customers.csv`, `products.csv`) provide customer segment and product category context.

| KPI Group  | Columns                                                                 |
|------------|-------------------------------------------------------------------------|
| Revenue    | `total_revenue_usd`, `avg_order_value_usd`, `avg_discount_pct`          |
| Demand     | `n_orders`, `n_unique_customers`, `return_rate`                         |
| Marketing  | `avg_roas`, `total_clicks`, `total_conversions_marketing`               |
| Web        | `sessions`, `bounce_rate`, `conversion_rate`, `pages_per_session`       |
| Inventory  | `total_stock_on_hand`, `n_stockouts`, `inventory_health`                |
| External   | `economic_index`, `consumer_sentiment`, `seasonal_index`, `marketing_pressure` |

### Step 1.2 — Data Ingestion Pipeline

A Python script (`scripts/ingest_and_engineer.py`) runs daily and loads the latest data row into a SQL database that Power BI reads from.

```
[master_dataset.csv] ──→ [Python Ingestor] ──→ [SQLite / PostgreSQL / Azure SQL]
[customers.csv]      ──→       │
[products.csv]       ──→       │
                               ↓
                    [Feature Engineering Module]
                               ↓
                    [Processed KPI Table]  ←── Power BI reads this
```

### Step 1.3 — Feature Engineering

Computed for every primary KPI before detection runs:

| Feature             | Formula                              | Purpose                          |
|---------------------|--------------------------------------|----------------------------------|
| 7-day rolling mean  | `kpi.rolling(7).mean()`              | Smooths daily noise              |
| 7-day rolling std   | `kpi.rolling(7).std()`               | Dynamic threshold baseline       |
| Z-score             | `(kpi - rolling_mean) / rolling_std` | Standardised deviation           |
| WoW % change        | `(today - last_week) / last_week`    | Week-over-week shift             |
| MoM % change        | `(today - last_month) / last_month`  | Structural drift detection       |
| Lag features        | `kpi.shift(1), kpi.shift(7)`         | Inputs for ML models             |
| Day-of-week         | `date.dayofweek`                     | Seasonality control              |
| External interaction| `revenue * economic_index`           | Driver interaction terms         |

> `seasonal_index`, `economic_index`, `consumer_sentiment`, and `marketing_pressure` are exogenous control variables — they are model inputs, not detection targets.

---

## LAYER 2 — Anomaly Detection Engine

A multi-method ensemble — no single algorithm catches all anomaly types.

### Step 2.1 — KPI Monitoring Tiers

```
Tier 1 (Alert immediately):    total_revenue_usd, n_orders, avg_roas, conversion_rate
Tier 2 (Alert within 1 hour): return_rate, n_stockouts, avg_order_value_usd, bounce_rate
Tier 3 (Daily digest):         total_clicks, sessions, inventory_health, avg_discount_pct
```

### Step 2.2 — Detection Methods

**Method A — Statistical Baseline (fast, interpretable)**

```
For each Tier 1 KPI on each new day:
  1. Compute rolling_mean and rolling_std over past 28 days
  2. Apply STL seasonal decomposition → isolate residual component
  3. Flag if residual Z-score > ±2.5 (configurable per KPI)
  4. Flag if WoW change > ±20% AND MoM change > ±15% simultaneously
```

**Method B — Isolation Forest (unsupervised ML)**

Runs on all 33 KPIs as a joint feature matrix. Catches correlated multi-KPI anomalies (e.g. sessions up but conversion_rate down) that individual-KPI checks miss.

```python
IsolationForest(contamination=0.05, n_estimators=100)
# Train on first 80% of dataset, score new daily rows
```

**Method C — Prophet (time-series forecasting)**

```
For each Tier 1 KPI:
  Train Prophet with:
    - weekly_seasonality = True
    - yearly_seasonality = True
    - regressors: economic_index, seasonal_index, marketing_pressure
  Flag if actual falls outside 95% prediction interval
```

Best for structural breaks and holiday/seasonal anomalies because it explicitly uses `seasonal_index` as a regressor.

**Method D — LSTM Autoencoder (optional, deep learning)**

```
Trained on 14-day sliding windows across all Tier 1 KPIs
Flag if reconstruction error > learned threshold
Best for: subtle gradual drift that statistical methods miss
```

### Step 2.3 — Ensemble Voting

```
Anomaly confirmed if:  ≥ 2 of 4 methods agree  (configurable)

Severity:
  HIGH   → all 4 methods agree  OR  Tier 1 KPI with Z-score > 3.5
  MEDIUM → 2–3 methods agree    OR  Tier 2 KPI flagged
  LOW    → 1 method only, Tier 3 KPI
```

**Anomaly output schema:**

```json
{
  "date": "2024-03-15",
  "kpi": "total_revenue_usd",
  "direction": "DOWN",
  "severity": "HIGH",
  "actual_value": 7821.0,
  "expected_value": 11400.0,
  "deviation_pct": -31.4,
  "z_score": -3.8,
  "methods_flagged": ["statistical", "prophet", "isolation_forest"],
  "anomaly_id": "ANO-2024-0315-REV-001"
}
```

---

## LAYER 3 — Root Cause Analysis

### Step 3.1 — Dependency Graph Drill-Down

When a Tier 1 KPI anomaly is confirmed, the agent traverses a pre-defined dependency graph to find the upstream driver:

```
Revenue Anomaly
    ├── Is n_orders anomalous?          → demand problem
    │       ├── Is sessions anomalous?  → traffic problem
    │       │       └── Is bounce_rate high? → campaign / landing page problem
    │       └── Is conversion_rate anomalous? → checkout / UX problem
    ├── Is avg_order_value anomalous?   → basket size / discount problem
    │       └── Is avg_discount_pct high? → promo leak / pricing error
    └── Is return_rate anomalous?       → product quality / fulfillment problem
```

A separate dependency graph is defined for each Tier 1 KPI (ROAS, conversion rate, stockouts).

### Step 3.2 — Causal Inference

**CausalImpact** (Bayesian structural time series) quantifies how much a suspected driver caused the outcome:

```python
CausalImpact(
    data=df[['total_revenue_usd', 'avg_roas', 'sessions', 'consumer_sentiment']],
    pre_period=[start_date, anomaly_date - 1],
    post_period=[anomaly_date, anomaly_date + 3]
)
# Output: "avg_roas decline explains 67% of revenue drop (89% posterior confidence)"
```

**DoWhy** builds a causal DAG from domain knowledge:

```
economic_index ──→ consumer_sentiment ──→ sessions ──→ conversion_rate ──→ revenue
marketing_pressure ──→ avg_roas ──→ total_attributed_revenue ──→ revenue
seasonal_index ──→ n_orders ──→ revenue
inventory_health ──→ n_stockouts ──→ n_orders ──→ revenue
```

### Step 3.3 — External Driver Attribution

Before escalating any anomaly, the agent checks whether it is externally driven (macro, seasonal) and therefore not actionable:

```
If economic_index < -0.3 AND revenue_anomaly:
    → "Macro-driven decline — not actionable internally"

If marketing_pressure > 0.5 AND roas_anomaly:
    → "Competitive pressure driving ROAS degradation"

If seasonal_index < -0.1 AND orders_anomaly:
    → "Expected seasonal trough — monitor but do not alarm leadership"
```

This suppresses false escalations and focuses human attention on actionable root causes.

---

## LAYER 4 — Intelligence Engine

### Step 4.1 — Business Impact Quantification

```python
def calculate_impact(anomaly):
    revenue_at_risk = (expected - actual) * forward_days   # 7-day projection
    margin_impact   = revenue_at_risk * avg_gross_margin
    customer_impact = estimate_affected_customers(anomaly.kpi)
    return ImpactScore(revenue_at_risk, margin_impact, customer_impact)
```

**Impact statement format:**
> "Revenue is tracking $28,400 below forecast for the week. At current trajectory, this represents a $118,000 monthly shortfall — 8.3% below plan. Approximately 1,200 customers experienced degraded conversion."

### Step 4.2 — Prioritization Engine

Each confirmed anomaly receives a composite priority score:

| Factor               | Weight | Scoring Logic                                      |
|----------------------|--------|----------------------------------------------------|
| Revenue impact ($)   | 35%    | Log-scaled absolute dollar impact                  |
| KPI tier             | 25%    | Tier 1 = 1.0, Tier 2 = 0.6, Tier 3 = 0.3          |
| Causal confidence    | 20%    | CausalImpact posterior probability                 |
| Recoverability       | 10%    | Is there an actionable fix available?              |
| External driver?     | 10%    | Penalise if macro-driven (reduces urgency)         |

```
Priority Score = Σ(factor × weight)
HIGH   > 0.75  → page on-call, create P1 ticket
MEDIUM 0.5–0.75 → Slack alert, create P2 ticket
LOW    < 0.5   → daily digest only
```

### Step 4.3 — Recommendation Engine

A **playbook lookup + LLM generation** hybrid:

**Playbook (rule-based, deterministic):**

```python
PLAYBOOKS = {
    "roas_collapse + paid_search": [
        "Pause underperforming ad groups above $50 CPA",
        "Shift 30% of budget to email/organic for next 48h",
        "Review bid strategy — check if competitor surge caused CPCs to spike"
    ],
    "conversion_rate_drop + bounce_rate_spike": [
        "Check latest deployment for landing page regressions",
        "Review mobile vs desktop split — isolate breakage",
        "Rollback A/B test if change was deployed in last 24h"
    ],
    "stockout + n_orders_drop": [
        "Trigger emergency reorder for top 20 SKUs by revenue contribution",
        "Surface in-stock alternatives in recommendation engine",
        "Notify merchandising team for supplier escalation"
    ]
}
```

**LLM Enhancement (Claude, context-aware):**

The agent passes the full anomaly context to Claude and requests:
- Immediate action (next 24h)
- Short-term fix (next 7 days)
- Preventive measure (next 30 days)

```python
prompt = f"""
Anomaly: {anomaly.kpi} dropped {anomaly.deviation_pct}% on {anomaly.date}
Root cause: {root_cause.description} (confidence: {root_cause.confidence}%)
Business impact: ${impact.revenue_at_risk:,.0f} at risk over 7 days
External context: {external_drivers_summary}
Historical precedent: {similar_past_anomalies}

Recommend 3 actions: immediate, short-term, preventive.
Format: action | owner | expected outcome | effort (H/M/L)
"""
```

---

## LAYER 5 — Communication Layer

### Step 5.1 — Immediate Alert

Sent within minutes of anomaly confirmation via Email + Slack/Teams webhook:

```
🚨 [HIGH] Revenue Anomaly Detected — 2024-03-15
────────────────────────────────────────────────
KPI:       Total Revenue
Actual:    $7,821  (-31.4% vs expected $11,400)
Cause:     ROAS collapse in paid_search channel (confidence: 87%)
Impact:    $28,400 at risk this week
Action:    Pause underperforming ad groups → @growth-team
Dashboard: [Power BI Link]
```

**Alert routing by severity:**

| Severity | Recipients                          | Channel         | SLA       |
|----------|-------------------------------------|-----------------|-----------|
| HIGH     | VP Marketing + Ops Lead + Analytics | Slack + Email   | < 10 min  |
| MEDIUM   | Analytics team + Channel owner      | Slack           | < 1 hour  |
| LOW      | Analytics digest                    | Email (daily)   | 24h       |

### Step 5.2 — Executive Summary (auto-generated, daily 8am)

```
DAILY KPI INTELLIGENCE BRIEF — [Date]
═══════════════════════════════════════
HEADLINE: [One sentence — business state today]

ANOMALIES DETECTED: [N]
  ▸ HIGH (N):   [brief list]
  ▸ MEDIUM (N): [brief list]

FINANCIAL EXPOSURE: $XXX,XXX at risk

TOP PRIORITY ACTION:
  → [Single most important action | owner | timeline]

TRENDING CONCERNS:
  → [2–3 emerging patterns not yet at anomaly threshold]

WHAT IS PERFORMING WELL:
  → [1–2 positive callouts to balance narrative]

FULL DETAILS: [Power BI dashboard link]
```

### Step 5.3 — Power BI Dashboard

Power BI connects via DirectQuery or scheduled CSV refresh to the agent's processed output.

```
┌──────────────────────────────────────────────────────┐
│  ANOMALY DETECTION DASHBOARD                         │
│                                                      │
│  Page 1: Command Center                              │
│  ├── KPI scorecards with anomaly colour coding       │
│  ├── Anomaly timeline (date × severity heatmap)      │
│  └── Active anomalies table with priority rank       │
│                                                      │
│  Page 2: Root Cause Explorer                         │
│  ├── Driver decomposition waterfall chart            │
│  ├── KPI × KPI correlation matrix                    │
│  └── External factor overlay (economic/seasonal)     │
│                                                      │
│  Page 3: Impact & Recommendations                    │
│  ├── Revenue at risk gauge                           │
│  ├── Recommendation cards (immediate / short / preventive) │
│  └── Recovery tracking (did last recommendation work?)│
│                                                      │
│  Page 4: Executive Summary                           │
│  └── Auto-text narrative (Claude-written brief)      │
└──────────────────────────────────────────────────────┘
```

**Conditional formatting DAX for anomaly colour coding:**

```dax
AnomalyColor =
VAR ZScore = [Revenue_ZScore]
RETURN
    SWITCH(
        TRUE(),
        ZScore < -2.5, "#FF4444",    -- RED:    anomaly low
        ZScore >  2.5, "#FF8C00",    -- ORANGE: anomaly high
        ABS(ZScore) > 1.5, "#FFD700",-- YELLOW: watch zone
        "#22C55E"                    -- GREEN:  normal
    )
```

---

## LAYER 6 — Agent Orchestration

### Step 6.1 — Agent Architecture

```
┌─────────────────────────────────────────────────────┐
│              ORCHESTRATOR AGENT (LLM)               │
│                  claude-sonnet-4-6                  │
└──────────────────────┬──────────────────────────────┘
                       │ Tools:
          ┌────────────┼─────────────────────┐
          ↓            ↓                     ↓
  [run_detection]  [run_rca]           [generate_summary]
  [fetch_kpis]     [lookup_playbook]   [send_alert]
  [score_impact]   [causal_inference]  [update_powerbi]
```

The agent holds a system prompt encoding KPI definitions, business rules, alert routing, dependency graphs, and the playbook index. It decides which tools to call, and in what order, based on what it detects.

### Step 6.2 — Agent Decision Flow (daily run)

```
START (triggered at 7:00am or on new data arrival)
  │
  ├─ Step 1: fetch_kpis(date=today)
  │           → Returns latest daily row from master_dataset
  │
  ├─ Step 2: run_detection(kpis, methods=['statistical','prophet','isolation_forest'])
  │           → Returns list of AnomalyObjects with severity scores
  │
  ├─ IF anomalies found:
  │   │
  │   ├─ Step 3: run_rca(anomaly)  [for each HIGH / MEDIUM anomaly]
  │   │           → Traverses dependency graph + runs CausalImpact
  │   │           → Returns RootCauseObject with confidence %
  │   │
  │   ├─ Step 4: score_impact(anomaly, root_cause)
  │   │           → Returns ImpactObject (revenue_at_risk, margin, customers)
  │   │
  │   ├─ Step 5: prioritize(all_anomalies)
  │   │           → Returns anomalies sorted by composite priority score
  │   │
  │   ├─ Step 6: generate_recommendations(anomaly, root_cause, impact)
  │   │           → Playbook lookup → Claude LLM enhancement
  │   │
  │   └─ Step 7: send_alert(severity=HIGH)
  │               → Routes to correct channel and recipients
  │
  ├─ Step 8: generate_executive_summary(all_anomalies, date)
  │           → Claude writes the daily brief
  │
  └─ Step 9: update_powerbi_dataset()
              → Writes anomaly_results.csv → Power BI refreshes
```

### Step 6.3 — Technology Stack

| Component            | Technology                              | Purpose                              |
|----------------------|-----------------------------------------|--------------------------------------|
| Data store           | SQLite (dev) / PostgreSQL / Azure SQL   | SQL backend Power BI reads from      |
| Feature engineering  | Python: `pandas`, `statsmodels`         | Rolling stats, z-scores, lag features|
| Statistical detection| `scipy`, `statsmodels` STL              | Fast, interpretable baseline         |
| ML detection         | `scikit-learn` IsolationForest          | Unsupervised multi-KPI detection     |
| Forecasting          | `prophet`                               | Handles seasonality + regressors     |
| Causal inference     | `causalimpact`, `dowhy`                 | Confidence-scored root cause         |
| Agent LLM            | Claude API (`claude-sonnet-4-6`)        | Orchestration + NL generation        |
| Alerts               | `smtplib` + Slack/Teams webhooks        | Multi-channel alert delivery         |
| Visualization        | Power BI Desktop + Service              | Executive dashboard                  |
| Scheduler            | Python `schedule` or GitHub Actions     | Daily pipeline trigger               |

---

## End-to-End Data Flow

```
master_dataset.csv (new daily row arrives)
         │
         ▼
  Feature Engineering
  (rolling stats, z-scores, WoW/MoM, lag features, external interactions)
         │
         ▼
  ┌──────┴──────────────┐
  │  4-Method Ensemble  │
  │  ① Statistical      │
  │  ② Isolation Forest │
  │  ③ Prophet          │
  │  ④ LSTM (optional)  │
  └──────┬──────────────┘
         │ Anomaly confirmed (≥ 2 methods agree)
         ▼
  Root Cause Analysis
  (dependency graph → CausalImpact → DoWhy → external driver check)
         │
         ▼
  Impact Quantification
  (revenue at risk, gross margin impact, affected customer count)
         │
         ▼
  Prioritization Score
  (revenue × KPI tier × causal confidence × recoverability − external driver penalty)
         │
         ├──→ Recommendations  (playbook lookup + Claude LLM enhancement)
         ├──→ Alert            (Slack / Email, routed by severity)
         ├──→ Executive Brief  (Claude-written daily summary)
         └──→ Power BI Dataset (anomaly_results.csv refresh)
                      │
                      ▼
             Power BI Dashboard
             ├── Page 1: Command Center
             ├── Page 2: Root Cause Explorer
             ├── Page 3: Impact & Recommendations
             └── Page 4: Executive Summary
```

---

## Data Dictionary

### Source Tables

Eight CSV files live in `data/`. Two are dimension tables (customers, products); six are fact / label tables that aggregate into `master_dataset.csv`.

---

#### customers.csv — Customer Dimension
10,000 rows · 1 row per customer

| Column | Type | Description |
|---|---|---|
| `customer_id` | string | Primary key. Format: `C0000001` |
| `segment` | string | Customer value segment: `loyalty` / `regular` / `occasional` / `new` / `churned` |
| `country` | string | ISO-2 country code of the customer (e.g. `US`, `DE`, `FR`) |
| `cohort_month` | string | `YYYY-MM` of the customer's first order — used for cohort retention analysis |
| `age` | int | Customer age in years |
| `is_loyalty_member` | int | `1` if enrolled in the loyalty programme, `0` otherwise |
| `lifetime_value_usd` | float | Estimated customer lifetime value in USD |
| `email_opt_in` | int | `1` if the customer has opted into marketing emails |
| `avg_review_score` | float | Average product review score left by this customer (1–5 scale); ~2% null |

---

#### products.csv — Product Dimension
500 rows · 1 row per product

| Column | Type | Description |
|---|---|---|
| `product_id` | string | Primary key. Format: `P000001` |
| `category` | string | Product category: `Electronics` / `Apparel` / `Home` / `Sports` / `Beauty` / `Food` / `Toys` / `Books` |
| `brand` | string | Brand identifier: `Brand_A` through `Brand_T` |
| `base_price_usd` | float | List price before discount in USD |
| `cost_usd` | float | Cost of goods sold (COGS) in USD |
| `gross_margin` | float | `(base_price − cost) / base_price` — margin as a fraction |
| `is_premium` | int | `1` if `base_price_usd` is above the 75th percentile of the catalogue |

---

#### orders.csv — Order Transactions
~148,000 rows · 1 row per order

| Column | Type | Description |
|---|---|---|
| `order_id` | string | Primary key. Format: `O000000001` |
| `customer_id` | string | Foreign key → `customers.customer_id` |
| `order_date` | date | Date the order was placed (`YYYY-MM-DD`) |
| `channel` | string | Acquisition channel: `organic_search` / `paid_search` / `email` / `social` / `direct` / `affiliate` / `referral` |
| `status` | string | Order status: `completed` / `returned` / `cancelled` |
| `order_total_usd` | float | Total order value after discount, in USD |
| `discount_pct` | float | Fractional discount applied to the order (e.g. `0.07` = 7%) |
| `country` | string | Country where the order was shipped |

---

#### order_items.csv — Line Items
~370,000 rows · 1 row per product line within an order

| Column | Type | Description |
|---|---|---|
| `order_item_id` | string | Primary key. Format: `OI0000000001` |
| `order_id` | string | Foreign key → `orders.order_id` |
| `product_id` | string | Foreign key → `products.product_id` |
| `quantity` | int | Number of units of this product in the order |
| `unit_price_usd` | float | Price per unit after discount, in USD |
| `discount_pct` | float | Fractional discount applied at line level |
| `line_total_usd` | float | `unit_price_usd × quantity` — total revenue for this line |

---

#### inventory_daily.csv — Daily Stock per Product
365,500 rows · 1 row per product per day (500 products × 731 days)

| Column | Type | Description |
|---|---|---|
| `date` | date | Calendar date (`YYYY-MM-DD`) |
| `product_id` | string | Foreign key → `products.product_id` |
| `stock_on_hand` | int | Units available in inventory at end of day |
| `units_sold` | int | Units of this product sold on this day |
| `reorder_triggered` | int | `1` if a reorder was placed for this product today |
| `stockout_flag` | int | `1` if stock hit zero at any point during the day |

---

#### marketing_spend_daily.csv — Daily Ad Spend per Channel
3,655 rows · 1 row per channel per day (5 channels × 731 days)

| Column | Type | Description |
|---|---|---|
| `date` | date | Calendar date (`YYYY-MM-DD`) |
| `channel` | string | Marketing channel: `paid_search` / `social` / `email` / `affiliate` / `display` |
| `spend_usd` | float | Ad spend on this channel on this day, in USD |
| `impressions` | int | Total ad impressions served |
| `clicks` | int | Total clicks on ads |
| `conversions` | int | Orders attributed to this channel on this day |
| `attributed_revenue_usd` | float | Revenue attributed to this channel on this day, in USD |
| `roas` | float | Return on ad spend: `attributed_revenue_usd / spend_usd` |

---

#### website_traffic_daily.csv — Daily Web Traffic
731 rows · 1 row per day

| Column | Type | Description |
|---|---|---|
| `date` | date | Calendar date (`YYYY-MM-DD`) |
| `sessions` | int | Total website sessions (including returning visitors) |
| `unique_visitors` | int | Deduplicated unique visitor count |
| `bounce_rate` | float | Fraction of sessions that left after viewing one page (0–1) |
| `pages_per_session` | float | Average number of pages viewed per session |
| `avg_session_duration_sec` | float | Average session length in seconds |
| `conversion_rate` | float | Fraction of sessions that resulted in a purchase (0–1) |
| `conversions` | int | Total sessions that converted to a sale |

---

#### anomaly_log.csv — Ground-Truth Anomaly Labels
20 rows · 1 row per labeled anomaly event

| Column | Type | Description |
|---|---|---|
| `date` | date | Date the anomaly occurred (`YYYY-MM-DD`) |
| `anomaly_event` | string | Event name (e.g. `black_friday_spike`, `inventory_stockout`, `fraud_attack`) |
| `anomaly_kpi` | string | Primary KPI affected by this event (e.g. `revenue`, `sessions`, `return_rate`) |

---

### master_dataset.csv — Daily Analytical Dataset
731 rows · 33 columns · 1 row per day (2024-01-01 to 2025-12-31)

Built by aggregating the 6 fact/label tables above and joining on `date`.

#### Orders Group — from orders.csv

| Column | Type | Description |
|---|---|---|
| `date` | date | Calendar date — primary join key |
| `n_orders` | int | Total orders placed on this day |
| `total_revenue_usd` | float | Sum of all `order_total_usd` for the day |
| `avg_order_value_usd` | float | Mean order value: `total_revenue_usd / n_orders` |
| `avg_discount_pct` | float | Mean discount fraction applied across all orders |
| `n_unique_customers` | int | Count of distinct customers who ordered on this day |
| `n_returns` | int | Count of orders with `status = 'returned'` |
| `return_rate` | float | `n_returns / n_orders` |

#### Marketing Group — from marketing_spend_daily.csv

| Column | Type | Description |
|---|---|---|
| `total_spend_usd` | float | Total ad spend across all 5 channels |
| `total_impressions` | int | Total impressions across all channels |
| `total_clicks` | int | Total clicks across all channels |
| `total_conversions_marketing` | int | Total conversions attributed to paid marketing |
| `total_attributed_revenue_usd` | float | Total revenue attributed to paid marketing |
| `avg_roas` | float | Overall ROAS: `total_attributed_revenue_usd / total_spend_usd` |

#### Web Traffic Group — from website_traffic_daily.csv

| Column | Type | Description |
|---|---|---|
| `sessions` | int | Total website sessions |
| `unique_visitors` | int | Deduplicated unique visitors |
| `bounce_rate` | float | Fraction of single-page sessions (0–1) |
| `pages_per_session` | float | Average pages viewed per session |
| `avg_session_duration_sec` | float | Average session duration in seconds |
| `conversion_rate` | float | Fraction of sessions converting to a purchase (0–1) |
| `conversions_web` | int | Total converting sessions (renamed from `conversions`) |

#### Inventory Group — from inventory_daily.csv

| Column | Type | Description |
|---|---|---|
| `total_stock_on_hand` | int | Sum of `stock_on_hand` across all 500 products |
| `total_units_sold` | int | Sum of `units_sold` across all 500 products |
| `n_stockouts` | int | Count of products that hit zero stock on this day |
| `n_reorders` | int | Count of products that triggered a reorder on this day |

#### Latent Driver Group — simulation engine variables

| Column | Type | Description |
|---|---|---|
| `economic_index` | float | Macro-economic strength index (AR(1) process); positive = expansion, negative = contraction. Drives AOV and premium product mix |
| `marketing_pressure` | float | Competitive marketing intensity index. High values indicate greater external spend pressure, suppressing ROAS |
| `consumer_sentiment` | float | Consumer confidence index. Influences return rates, review scores, and churn propensity |
| `seasonal_index` | float | Seasonal demand multiplier. Peaks at peak shopping seasons; troughs in slow periods |
| `inventory_health` | float | Composite inventory stability score. Low values indicate supply-chain stress and future stockout risk |

#### Anomaly Label Group — from anomaly_log.csv

| Column | Type | Description |
|---|---|---|
| `anomaly_flag` | int | `1` on a labeled anomaly day, `0` otherwise. 20 flagged days across the 2-year dataset |
| `anomaly_event` | string | Human-readable event name (e.g. `black_friday_spike`, `bot_traffic_surge`). Empty string on non-anomaly days |
| `anomaly_kpi` | string | The primary KPI targeted by this anomaly event (e.g. `revenue`, `sessions`, `return_rate`). Empty string on non-anomaly days |

---

## Dataset Ground Truth

The `anomaly_flag`, `anomaly_event`, and `anomaly_kpi` columns in `master_dataset.csv` contain 20 labeled anomaly events. These are the ground truth for:
- Tuning detection thresholds (optimise for recall on Tier 1 KPIs)
- Measuring ensemble precision / recall at each stage
- Validating causal inference outputs against known event causes
- Benchmarking recommendation relevance
