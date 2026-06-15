# Step 5.6 — Power BI Desktop Build

> **Layer 5 Communication Layer — KPI Anomaly Detection Agent**
>
> This is the only non-Python step in the project. The `.pbix` file is built
> manually in Power BI Desktop using the five CSVs and the theme file produced
> by Step 5.5.

---

## Source files (all in `outputs/powerbi/`)

| File | Rows | Cols | Role |
|---|---|---|---|
| `fact_anomalies.csv` | 181 | 40 | Main fact table |
| `dim_kpi.csv` | 12 | 5 | KPI dimension |
| `dim_date.csv` | 731 | 13 | Full calendar 2024-01-01 – 2025-12-31 |
| `summary_kpi_impact.csv` | 17 | 9 | KPI × priority_band aggregation |
| `summary_timeline.csv` | 68 | 10 | Daily anomaly timeline |
| `kpi_anomaly_theme.json` | — | — | Custom colour theme |

---

## Color convention (applied throughout)

| Value | Colour | Hex |
|---|---|---|
| HIGH / ESCALATE | Red | `#C00000` |
| MEDIUM / INVESTIGATE | Amber | `#E8A000` |
| LOW / MONITOR | Green | `#107C41` |
| SUPPRESSED | Grey | `#767676` |

---

## 5.6.1 — Load Data

**Home → Get Data → Text/CSV** — load each file and rename the query exactly as shown:

| File | Query name |
|---|---|
| `fact_anomalies.csv` | `fact_anomalies` |
| `dim_kpi.csv` | `dim_kpi` |
| `dim_date.csv` | `dim_date` |
| `summary_kpi_impact.csv` | `summary_kpi_impact` |
| `summary_timeline.csv` | `summary_timeline` |

### Set data types in Power Query (Transform Data)

**`fact_anomalies`**

| Column | Type |
|---|---|
| `date`, `sent_at` | Date / Date Time |
| `tier`, `priority_rank`, `customer_impact` | Whole Number |
| `deviation_pct`, `z_score`, `revenue_at_risk`, `margin_impact`, `monthly_shortfall`, `impact_pct_of_plan`, `priority_score`, `root_cause_confidence`, `actionability_score` | Decimal Number |
| `is_externally_driven`, `escalation_suppressed`, `llm_enhanced` | True/False |
| All remaining columns | Text |

**`dim_date`**

| Column | Type |
|---|---|
| `date` | Date |
| `year`, `quarter_num`, `month_num`, `week_num`, `day_of_week_num`, `yyyymm` | Whole Number |
| `is_weekend` | True/False |
| All remaining columns | Text |

**`summary_timeline`**

| Column | Type |
|---|---|
| `date` | Date |
| `anomaly_count`, `escalate_count`, `investigate_count`, `monitor_count`, `suppressed_count` | Whole Number |
| `daily_at_risk`, `daily_upside`, `cumulative_at_risk`, `cumulative_upside` | Decimal Number |

Click **Close & Apply**.

---

## 5.6.2 — Apply Theme

**View → Themes → Browse for themes** → select `outputs/powerbi/kpi_anomaly_theme.json`.

The theme pre-loads the eight brand colours and sets:
- `good` = `#107C41` (green — upside / LOW)
- `neutral` = `#E8A000` (amber — MEDIUM)
- `bad` = `#C00000` (red — HIGH / at-risk)

---

## 5.6.3 — Create Relationships

Go to **Model view** and create two relationships by dragging:

| From | To | Cardinality |
|---|---|---|
| `fact_anomalies[date]` | `dim_date[date]` | Many-to-One |
| `fact_anomalies[kpi]` | `dim_kpi[kpi]` | Many-to-One |

`summary_kpi_impact` and `summary_timeline` are standalone aggregation tables — no relationships needed.

---

## 5.6.4 — Mark Date Table

In Model view, right-click **`dim_date`** → **Mark as date table** → select the `date` column.
This enables Power BI time-intelligence DAX functions (`TOTALYTD`, `SAMEPERIODLASTYEAR`, etc.).

---

## 5.6.5 — DAX Measures

**Home → Enter Data** → create a blank 1-row table named `_Measures`.
Select `_Measures` in the Fields pane, then add each measure via **New Measure**:

```dax
Total Anomalies =
COUNTROWS(fact_anomalies)
```

```dax
High Priority Count =
CALCULATE(
    COUNTROWS(fact_anomalies),
    fact_anomalies[priority_band] = "HIGH"
)
```

```dax
Total Revenue At Risk =
CALCULATE(
    SUM(fact_anomalies[revenue_at_risk]),
    fact_anomalies[revenue_at_risk] > 0
)
```

```dax
Total Captured Upside =
ABS(
    CALCULATE(
        SUM(fact_anomalies[revenue_at_risk]),
        fact_anomalies[revenue_at_risk] < 0
    )
)
```

```dax
Net Margin Benefit =
ABS(SUM(fact_anomalies[margin_impact]))
```

```dax
Avg Priority Score =
ROUND(AVERAGE(fact_anomalies[priority_score]), 4)
```

```dax
LLM Coverage % =
DIVIDE(
    CALCULATE(
        COUNTROWS(fact_anomalies),
        fact_anomalies[llm_enhanced] = TRUE()
    ),
    COUNTROWS(fact_anomalies),
    0
)
```

```dax
Escalation Rate % =
DIVIDE(
    CALCULATE(
        COUNTROWS(fact_anomalies),
        fact_anomalies[layer4_priority_flag] = "ESCALATE"
    ),
    COUNTROWS(fact_anomalies),
    0
)
```

**Format measures:**
- `Total Revenue At Risk`, `Total Captured Upside`, `Net Margin Benefit` → Currency ($), 0 decimal places
- `LLM Coverage %`, `Escalation Rate %` → Percentage, 1 decimal place

---

## 5.6.6 — Page 1: Executive Overview

Rename the first page tab to **Executive Overview**.

### Visual 1 — KPI Cards (top row, 4 cards side by side)

| Card | Measure | Label |
|---|---|---|
| 1 | `[Total Anomalies]` | Total Anomalies Detected |
| 2 | `[High Priority Count]` | High Priority |
| 3 | `[Total Revenue At Risk]` | Revenue At Risk (7-day) |
| 4 | `[Total Captured Upside]` | Captured Upside (7-day) |

### Visual 2 — Priority Band Distribution

- Type: **Donut Chart**
- Legend: `fact_anomalies[priority_band]`
- Values: `[Total Anomalies]`
- Set slice colours manually: HIGH → `#C00000`, MEDIUM → `#E8A000`, LOW → `#107C41`
- Enable **Data labels** (show value + %)

### Visual 3 — Routing Flag Distribution

- Type: **Clustered Bar Chart**
- Y-axis: `fact_anomalies[layer4_priority_flag]`
- X-axis: `[Total Anomalies]`
- Set bar colours: ESCALATE → `#C00000`, INVESTIGATE → `#E8A000`, MONITOR → `#107C41`, SUPPRESSED → `#767676`
- Enable data labels

### Visual 4 — Top 10 Anomalies Table

- Type: **Table**
- Columns (in order): `priority_rank`, `date`, `kpi_label` *(from dim_kpi via relationship)*, `severity`, `direction`, `deviation_pct`, `revenue_at_risk`, `recommended_owner`
- Sort: `priority_rank` ascending
- Visual-level filter: `priority_rank` ≤ 10
- Format `deviation_pct` as %, `revenue_at_risk` as currency

### Slicers

- `fact_anomalies[severity]` — Tile style
- `fact_anomalies[direction]` — Tile style

---

## 5.6.7 — Page 2: Anomaly Timeline

Add a new page tab, rename to **Anomaly Timeline**.

### Visual 1 — Daily Count + Cumulative Upside

- Type: **Line and Clustered Column Chart**
- Shared axis: `summary_timeline[date]`
- Column values: `summary_timeline[anomaly_count]`
- Line values: `summary_timeline[cumulative_upside]`
- Column colour: `#0078D4`; Line colour: `#107C41`
- Enable markers on the line; enable data labels on columns

### Visual 2 — Calendar Heatmap

- Type: **Matrix**
- Rows: `dim_date[week_num]`
- Columns: `dim_date[day_of_week_name]` *(sort column: `day_of_week_num`)*
- Values: `[Total Anomalies]`
- Format → Cell elements → Background colour → **Gradient**: white → `#C00000`
- Hot spots reveal anomaly-dense weeks

### Visual 3 — Monthly Stacked Bar

- Type: **Stacked Bar Chart**
- Y-axis: `dim_date[year_month]` *(sort by `yyyymm` for chronological order)*
- X-axis: `[Total Anomalies]`
- Legend: `fact_anomalies[priority_band]`
- Colours: HIGH → `#C00000`, MEDIUM → `#E8A000`, LOW → `#107C41`

### Slicers

- `dim_date[year]` — Dropdown
- `dim_date[quarter_label]` — Dropdown

---

## 5.6.8 — Page 3: Root Cause Analysis

Add a new page tab, rename to **Root Cause Analysis**.

### Visual 1 — External Driver Bar Chart

- Type: **Clustered Bar Chart**
- Y-axis: `fact_anomalies[external_driver_type]`
- X-axis: `[Total Anomalies]`
- Visual-level filter: exclude `external_driver_type` = "none"
- Set bar colours manually per driver type

### Visual 2 — Confidence vs Actionability Scatter

- Type: **Scatter Chart**
- X-axis: `fact_anomalies[root_cause_confidence]` (Average)
- Y-axis: `fact_anomalies[actionability_score]` (Average)
- Size: `[Total Revenue At Risk]`
- Legend: `fact_anomalies[priority_band]`
- Colours: HIGH → `#C00000`, MEDIUM → `#E8A000`, LOW → `#107C41`
- Add reference lines at X = 0.5 and Y = 0.5 to create four quadrants

### Visual 3 — Externally Driven Anomalies Table

- Type: **Table**
- Columns: `date`, `kpi`, `external_driver_type`, `rca_narrative`
- Visual-level filter: `is_externally_driven` = TRUE

### Visual 4 — Two Metric Cards

| Card | Measure | Label |
|---|---|---|
| 1 | `[Escalation Rate %]` | Escalation Rate |
| 2 | `[LLM Coverage %]` | LLM-Enhanced Recommendations |

### Slicers

- `fact_anomalies[confidence_tier]`
- `fact_anomalies[is_externally_driven]`

---

## 5.6.9 — Page 4: Business Impact

Add a new page tab, rename to **Business Impact**.

### Visual 1 — Revenue Waterfall by KPI

- Type: **Waterfall Chart**
- Category: `dim_kpi[kpi_label]`
- Y-axis: `SUM(fact_anomalies[revenue_at_risk])`
- Sort by value descending
- Positive bars (at risk) → `#C00000`; Negative bars (upside captured) → `#107C41`

### Visual 2 — Impact % of Plan by Severity

- Type: **Clustered Column Chart**
- X-axis: `fact_anomalies[severity]`
- Y-axis: `AVERAGE(fact_anomalies[impact_pct_of_plan])`
- Colours: HIGH → `#C00000`, MEDIUM → `#E8A000`, LOW → `#107C41`
- Enable data labels

### Visual 3 — KPI × Priority Band Revenue Matrix

- Type: **Matrix**
- Rows: `dim_kpi[kpi_label]`
- Columns: `fact_anomalies[priority_band]`
- Values: `SUM(fact_anomalies[revenue_at_risk])`
- Format → Cell elements → Background colour → **Diverging** (negative = green, positive = red, centre = white)

### Visual 4 — Three Impact Cards

| Card | Field / Measure | Label |
|---|---|---|
| 1 | `SUM(fact_anomalies[customer_impact])` | Customers Affected |
| 2 | `[Net Margin Benefit]` | Net Margin Benefit |
| 3 | `[Avg Priority Score]` | Avg Priority Score |

### Slicer

- `dim_kpi[kpi_category]` — Dropdown (Revenue / Marketing / Operations / Customer / Traffic)

---

## 5.6.10 — Page 5: Recommendations & Actions

Add a new page tab, rename to **Recommendations & Actions**.

### Visual 1 — Effort vs Impact Scatter (Prioritisation Matrix)

- Type: **Scatter Chart**
- X-axis: `fact_anomalies[effort_level]`
- Y-axis: `[Total Revenue At Risk]`
- Size: `[Avg Priority Score]`
- Legend: `fact_anomalies[priority_band]`
- Colours: HIGH → `#C00000`, MEDIUM → `#E8A000`, LOW → `#107C41`
- **Quick wins** (L effort + high revenue at risk) appear in top-left quadrant

### Visual 2 — Recommended Owner Donut

- Type: **Donut Chart**
- Legend: `fact_anomalies[recommended_owner]`
- Values: `[Total Anomalies]`
- Enable data labels (% of total)

### Visual 3 — LLM vs Playbook Stacked Bar

- Type: **Stacked Bar Chart**
- Y-axis: `fact_anomalies[layer4_priority_flag]`
- X-axis: `[Total Anomalies]`
- Legend: `fact_anomalies[llm_enhanced]`
- Colours: TRUE → `#0078D4`, FALSE → `#767676`

### Visual 4 — Full Action Table (Drillthrough Target)

- Type: **Table**
- Columns: `anomaly_id`, `date`, `kpi`, `priority_band`, `immediate_action`, `short_term_fix`, `recommended_owner`, `effort_level`
- Sort: `priority_rank` ascending
- In the **Drillthrough** field well, add `fact_anomalies[anomaly_id]`
- Any data point on any other page can now right-click → Drill through → this table

### Slicers

- `fact_anomalies[effort_level]` — Tile style (L / M / H)
- `fact_anomalies[recommended_owner]` — Dropdown

---

## 5.6.11 — Report-Level Formatting

### Sync slicers across pages

- Add a date range slicer on Page 1 using `dim_date[date]`
- **View → Sync Slicers** → enable sync for `date`, `severity`, `priority_band` across all pages

### Cross-filter behaviour

- Select each visual → **Format → Edit interactions**
- Set all interactions to **Filter** (not Highlight) for cleaner page-wide filtering

### Global formatting settings

| Setting | Value |
|---|---|
| Page background | `#F8F8F8` |
| Visual borders | On, `#E0E0E0`, 1px, rounded corners |
| Title font | Segoe UI Semibold, 12pt |
| Currency format | `$#,##0` (no decimals) |
| Percentage format | `0.0%` |

---

## 5.6.12 — Save

**File → Save As** → save to `outputs/powerbi/kpi_anomaly_dashboard.pbix`

---

*Generated by KPI Anomaly Detection Agent — Layer 5 Communication Layer*
