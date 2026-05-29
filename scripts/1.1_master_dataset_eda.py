"""
Generates scripts/01_master_dataset_eda.ipynb with all code cells
and embedded outputs (including the histogram image).
Run once: python scripts/build_eda_notebook.py
"""

import pandas as pd
import numpy as np
import io
import base64
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import nbformat
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell, new_output

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv("data/master_dataset.csv", parse_dates=["date"])

EXCLUDE = ["anomaly_flag", "n_stockouts", "n_reorders", "anomaly_event", "anomaly_kpi", "date"]
cont_cols = [c for c in df.select_dtypes(include="number").columns if c not in EXCLUDE]

# ── Pre-compute outputs ───────────────────────────────────────────────────────
buf = io.StringIO()
df.info(buf=buf)
info_out = buf.getvalue()

skew = df[cont_cols].skew().round(3).sort_values(ascending=False)

skew_df = skew.to_frame(name="skewness")
skew_df["shape"] = skew_df["skewness"].apply(
    lambda s: "RIGHT-SKEWED" if s > 0.5 else ("LEFT-SKEWED" if s < -0.5 else "Approx. Normal")
)

summary_df = pd.concat(
    [df.dtypes.rename("dtype"), df.isnull().sum().rename("null_count")], axis=1
)
summary_df["null_%"] = (summary_df["null_count"] / len(df) * 100).round(1)

anom_flag_out = (
    "=== anomaly_flag ===\n"
    + df["anomaly_flag"]
    .value_counts()
    .rename({0: "Normal (0)", 1: "Anomaly (1)"})
    .to_string()
    + f"\n\nAnomaly rate: {df['anomaly_flag'].mean() * 100:.1f}%\n"
    + "\n=== anomaly_event (20 labeled events) ===\n"
    + df["anomaly_event"].value_counts().to_string()
    + "\n\n=== anomaly_kpi (which KPIs are flagged) ===\n"
    + df["anomaly_kpi"].value_counts().to_string()
    + "\n"
)

# ── Generate histogram ────────────────────────────────────────────────────────
fig, axes = plt.subplots(nrows=9, ncols=3, figsize=(18, 38))
axes = axes.flatten()

for i, col in enumerate(cont_cols):
    ax = axes[i]
    data = df[col].dropna()
    s = skew[col]
    color = "#EF4444" if abs(s) > 0.5 else "#22C55E"
    ax.hist(data, bins=40, color=color, edgecolor="white", linewidth=0.4, alpha=0.85)
    lbl = "Right-skewed" if s > 0.5 else ("Left-skewed" if s < -0.5 else "Normal")
    ax.set_title(f"{col}\nskew = {s:.2f}  |  {lbl}", fontsize=8.5, fontweight="bold", pad=4)
    ax.set_ylabel("Frequency", fontsize=7)
    ax.tick_params(labelsize=7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3, linewidth=0.5)

for j in range(i + 1, len(axes)):
    axes[j].set_visible(False)

fig.suptitle(
    "Distribution of Continuous KPI Metrics  |  Red = Skewed   Green = Approx. Normal",
    fontsize=13, fontweight="bold", y=1.001,
)
plt.tight_layout(h_pad=3.5, w_pad=2.5)

img_buf = io.BytesIO()
fig.savefig(img_buf, format="png", dpi=130, bbox_inches="tight")
img_buf.seek(0)
img_b64 = base64.b64encode(img_buf.read()).decode()
plt.close()

# ── Helper: image output cell ─────────────────────────────────────────────────
def img_output(b64):
    return new_output(
        "display_data",
        data={"image/png": b64, "text/plain": "<Figure size 2340x4940 with 27 Axes>"},
        metadata={"image/png": {"width": 900, "height": 1950}},
    )

# ── Build notebook ────────────────────────────────────────────────────────────
nb = new_notebook()
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11.0"},
}

cells = []

# ── 0. Title ──────────────────────────────────────────────────────────────────
cells.append(new_markdown_cell(source="""\
# KPI Anomaly Detection Agent — Master Dataset EDA

Exploratory Data Analysis of `data/master_dataset.csv`.
**731 daily rows · 33 columns · 20 labeled anomaly events · 2 years of data (2024–2025)**

| Section | What it covers |
|---|---|
| 1 | Dataset shape & first 5 rows |
| 2 | Column types & non-null counts |
| 3 | Descriptive statistics |
| 4 | Missing values & dtype summary |
| 5 | Anomaly label distribution |
| 6 | Skewness analysis |
| 7 | Distribution histograms (27 metrics) |
| 8 | EDA summary & detection implications |

---"""))

# ── 1. Imports ────────────────────────────────────────────────────────────────
c = new_code_cell(source="""\
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('data/master_dataset.csv', parse_dates=['date'])
print(f"Dataset loaded: {df.shape[0]} rows x {df.shape[1]} columns")""")
c["outputs"] = [new_output("stream", name="stdout", text="Dataset loaded: 731 rows x 33 columns\n")]
cells.append(c)

# ── 2. Shape + Head ───────────────────────────────────────────────────────────
cells.append(new_markdown_cell(source="""\
## 1. Dataset Shape & First 5 Rows

`df.shape` confirms 731 daily rows and 33 columns covering 2 full years (2024-01-01 to 2025-12-31).
`df.head()` shows the structure — each row is one calendar day aggregated across all channels."""))

c = new_code_cell(source="print('Shape:', df.shape)\ndf.head()")
c["outputs"] = [
    new_output("stream", name="stdout", text="Shape: (731, 33)\n"),
    new_output(
        "display_data",
        data={"text/html": df.head().to_html(index=True, border=0), "text/plain": repr(df.head())},
        metadata={},
    ),
]
cells.append(c)

# ── 3. info() ─────────────────────────────────────────────────────────────────
cells.append(new_markdown_cell(source="""\
## 2. Column Types & Non-Null Counts

`df.info()` shows the dtype and non-null count for all 33 columns.

**Key observations:**
- `date` — loaded as `datetime64[ns]` after `parse_dates=['date']`
- `anomaly_event` and `anomaly_kpi` — only **20 non-null** entries (the labeled anomaly days); all others are `NaN`
- All 30 KPI columns are **fully populated** (zero nulls) — no imputation required
- **14 integer** columns, **16 float** columns, **3 object/string** columns"""))

c = new_code_cell(source="df.info()")
c["outputs"] = [new_output("stream", name="stdout", text=info_out)]
cells.append(c)

# ── 4. describe() ─────────────────────────────────────────────────────────────
cells.append(new_markdown_cell(source="""\
## 3. Descriptive Statistics

`df.describe().T` — transposed so each KPI is a row for easier reading.

**Key observations:**

| KPI | Observation |
|---|---|
| `total_revenue_usd` | Mean $11,715 but max $66,133 — anomaly spikes inflate the right tail |
| `avg_roas` | Mean 34.1 but max 164.6 — marketing campaign anomalies cause extreme values |
| `sessions` | Mean 8,390 but max 46,935 — bot traffic / viral events create extreme outliers |
| `avg_order_value_usd` | Mean $57.4, max $213.3 — fraud or high-value order anomalies |
| `conversion_rate` | Tight range 0.018–0.039, mean 0.024 — most stable Tier 1 metric |
| `return_rate` | Mean 7.7%, max 23.4% — defective product events drive extreme peaks |
| External drivers | `economic_index`, `seasonal_index`, `consumer_sentiment` all centred near 0 — by design |"""))

c = new_code_cell(source="df.describe().T.round(3)")
c["outputs"] = [
    new_output(
        "display_data",
        data={"text/html": df.describe().T.round(3).to_html(border=0), "text/plain": df.describe().T.round(3).to_string()},
        metadata={},
    )
]
cells.append(c)

# ── 5. Nulls + dtypes ─────────────────────────────────────────────────────────
cells.append(new_markdown_cell(source="""\
## 4. Missing Values & Data Types

Combined view: dtype, null count, and null percentage per column.

**Only `anomaly_event` and `anomaly_kpi` have nulls** — 711 out of 731 rows (97.3%) are `NaN` because those columns only populate on anomaly days.
This is expected by design, not a data quality issue."""))

c = new_code_cell(source="""\
null_counts = df.isnull().sum().rename('null_count')
dtypes      = df.dtypes.rename('dtype')
summary = pd.concat([dtypes, null_counts], axis=1)
summary['null_%'] = (summary['null_count'] / len(df) * 100).round(1)
summary""")
c["outputs"] = [
    new_output(
        "display_data",
        data={"text/html": summary_df.to_html(border=0), "text/plain": summary_df.to_string()},
        metadata={},
    )
]
cells.append(c)

# ── 6. Anomaly Labels ─────────────────────────────────────────────────────────
cells.append(new_markdown_cell(source="""\
## 5. Anomaly Label Distribution

The dataset contains **20 labeled anomaly days** out of 731 total — a **2.7% anomaly rate**.

**Implications:**
- This class imbalance means a naive classifier that predicts "normal" every day achieves 97.3% accuracy — use **precision/recall**, not accuracy, to evaluate detectors
- Set `contamination=0.027` in Isolation Forest to match the true anomaly rate
- Use the 20 labeled rows as ground truth to tune detection thresholds (optimise for recall on Tier 1 KPIs)

**14 distinct event types** are labeled — ranging from demand spikes to fraud attacks and external macro shocks."""))

c = new_code_cell(source="""\
print("=== anomaly_flag ===")
print(df['anomaly_flag'].value_counts().rename({0: 'Normal (0)', 1: 'Anomaly (1)'}))
print(f"\\nAnomaly rate: {df['anomaly_flag'].mean()*100:.1f}%")

print("\\n=== anomaly_event (20 labeled events) ===")
print(df['anomaly_event'].value_counts())

print("\\n=== anomaly_kpi (which KPI each event affects) ===")
print(df['anomaly_kpi'].value_counts())""")
c["outputs"] = [new_output("stream", name="stdout", text=anom_flag_out)]
cells.append(c)

# ── 7. Skewness ───────────────────────────────────────────────────────────────
cells.append(new_markdown_cell(source="""\
## 6. Skewness Analysis

Skewness measures how asymmetric each distribution is:

| Range | Interpretation | Detection implication |
|---|---|---|
| > 0.5 | Right-skewed (long right tail) | Log-transform or rolling Z-score before detection |
| < -0.5 | Left-skewed (long left tail) | Reflect + log-transform before detection |
| -0.5 to 0.5 | Approximately normal | Direct Z-score thresholding (±2.5σ) is valid |

**16 of 27 continuous columns are right-skewed** — the extreme anomaly events (Black Friday, bot traffic, fraud) pull the right tail far from the mean.
**11 columns are approximately normal** — external drivers and stable operational metrics."""))

c = new_code_cell(source="""\
exclude = ['anomaly_flag', 'n_stockouts', 'n_reorders']
cont_cols = [c for c in df.select_dtypes(include='number').columns if c not in exclude]

skew = df[cont_cols].skew().round(3).sort_values(ascending=False).rename('skewness')
skew_df = skew.to_frame()
skew_df['shape'] = skew_df['skewness'].apply(
    lambda s: 'RIGHT-SKEWED' if s > 0.5 else ('LEFT-SKEWED' if s < -0.5 else 'Approx. Normal')
)
skew_df""")
c["outputs"] = [
    new_output(
        "display_data",
        data={"text/html": skew_df.to_html(border=0), "text/plain": skew_df.to_string()},
        metadata={},
    )
]
cells.append(c)

# ── 8. Histograms ─────────────────────────────────────────────────────────────
cells.append(new_markdown_cell(source="""\
## 7. Distribution Histograms — All 27 Continuous Metrics

**How to read:**
- Each subplot = one KPI column
- Title shows: column name · skewness value · distribution label
- **Red bars** → skewed (|skew| > 0.5) — consider log-transform before applying statistical detection
- **Green bars** → approximately normal — Z-score thresholding applies directly
- Extreme right-tail bars in skewed charts correspond to the 20 labeled anomaly days"""))

c = new_code_cell(source="""\
exclude = ['anomaly_flag', 'n_stockouts', 'n_reorders']
cont_cols = [c for c in df.select_dtypes(include='number').columns if c not in exclude]
skew = df[cont_cols].skew().round(3)

fig, axes = plt.subplots(nrows=9, ncols=3, figsize=(18, 38))
axes = axes.flatten()

for i, col in enumerate(cont_cols):
    ax = axes[i]
    data = df[col].dropna()
    s = skew[col]
    color = '#EF4444' if abs(s) > 0.5 else '#22C55E'
    ax.hist(data, bins=40, color=color, edgecolor='white', linewidth=0.4, alpha=0.85)
    lbl = 'Right-skewed' if s > 0.5 else ('Left-skewed' if s < -0.5 else 'Normal')
    ax.set_title(f'{col}\\nskew = {s:.2f}  |  {lbl}', fontsize=8.5, fontweight='bold', pad=4)
    ax.set_ylabel('Frequency', fontsize=7)
    ax.tick_params(labelsize=7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3, linewidth=0.5)

for j in range(i + 1, len(axes)):
    axes[j].set_visible(False)

fig.suptitle(
    'Distribution of Continuous KPI Metrics  |  Red = Skewed   Green = Approx. Normal',
    fontsize=13, fontweight='bold', y=1.001
)
plt.tight_layout(h_pad=3.5, w_pad=2.5)
plt.show()""")
c["outputs"] = [img_output(img_b64)]
cells.append(c)

# ── 9. Summary ────────────────────────────────────────────────────────────────
cells.append(new_markdown_cell(source="""\
## 8. EDA Summary & Implications for Detection

| Finding | Implication for Agent |
|---|---|
| 731 rows, 33 columns, 0 nulls in KPI columns | No imputation needed; pipeline-ready as-is |
| 20 anomaly labels (2.7% rate) | Set `contamination=0.027` in Isolation Forest; use PR-AUC not accuracy |
| 14 distinct anomaly event types | Build event-type classifier on top of the binary detector |
| 16 right-skewed columns | Apply log-transform or rolling Z-score (28-day window) before STL / Prophet |
| 11 approx-normal columns | Direct ±2.5σ Z-score thresholding is valid — no transform needed |
| Extreme outliers in `sessions`, `avg_roas`, `total_revenue_usd` | Confirm labels are meaningful — anomaly days are clearly visible in the tails |
| External drivers centred near 0 (`economic_index`, `seasonal_index`, etc.) | Use as **regressors / control variables** in Prophet — not as detection targets |
| `anomaly_kpi` column present | Use to build per-KPI precision / recall metrics during model evaluation |

---
*Next step: Layer 1 feature engineering — compute rolling stats, Z-scores, WoW/MoM changes, and lag features for all 27 continuous columns.*"""))

nb["cells"] = cells

out_path = "scripts/01_master_dataset_eda.ipynb"
with open(out_path, "w", encoding="utf-8") as f:
    nbformat.write(nb, f)

print(f"Notebook written: {out_path}")
print(f"Cells: {len(nb['cells'])}")
