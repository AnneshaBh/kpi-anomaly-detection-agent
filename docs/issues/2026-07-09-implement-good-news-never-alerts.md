# Implement "don't alert on good news" (direction-aware alert suppression)

**Status:** Fixed
**Opened:** 2026-07-09
**Fixed:** 2026-07-09
**Severity:** Feature (not a bug) — implements Annesha's original intent from
`updates/update1/`, which was reverted to old behavior by
[2026-07-02-direction-filter-deletes-positive-anomalies.md](2026-07-02-direction-filter-deletes-positive-anomalies.md)
**Files touched:** `scripts/rca/3.3_external_drivers.py`,
`scripts/rca/3.4_rca_assembly.py`,
`scripts/intelligence/4.1-4.4_*.py`,
`scripts/communication/5.1-5.4_*.py`

---

## Context

The previous fix (see linked issue above) stopped the pipeline from
**deleting** positive-direction anomalies (e.g. Black Friday), but
deliberately left the actual alerting behavior unchanged — Black Friday
went back to sending an alert, exactly like before Annesha's original
change. That was intentional at the time: the crash needed a fix now,
and "should good news alert?" was a separate product decision.

This issue implements that decision: **a KPI moving in its objectively
good direction (e.g. revenue up, return_rate down) should never
generate an alert, regardless of severity.** It should still appear in
the data and dashboard (e.g. the "Captured Upside" metric), just not
page anyone.

---

## Design

**Single source of truth:** `positive_is_good` per KPI in
`data/config/tier_config.json` (already existed, added by Annesha).

**New rule, added to `scripts/rca/3.3_external_drivers.py`:**

```python
good_direction_change = (
    (positive_is_good and direction == "UP")
    or (not positive_is_good and direction == "DOWN")
)
escalation_suppressed = good_direction_change or bad_direction_suppressed
```

`bad_direction_suppressed` is the original, untouched external-driver
logic (externally explained + DOWN + non-HIGH + low actionability) —
this still only applies to genuinely bad-direction anomalies and still
never suppresses an unexplained or HIGH-severity problem. The new
`good_direction_change` clause is unconditional: it does not check
severity, so it overrides the old "never suppress HIGH" rule for
positive changes specifically.

A new `good_direction_change` boolean column was added to the Step 3.3
output (and propagated through Layer 3/4/5) so downstream tests can
verify this directly instead of parsing text.

---

## The tradeoff that was flagged and confirmed before implementing

All 15 of the dataset's current HIGH-severity anomalies are positive
spikes (Black Friday, Cyber Monday, back-to-school — big, obvious
revenue/order/ROAS jumps that all 3 detection methods agree on). Real
problem events (fraud, outages, stockouts) only ever get caught by 1 of
the 3 methods, so they never reach HIGH severity in this dataset.

**Consequence:** implementing this rule empties the ESCALATE tier
entirely — 0 rows, for this dataset. This was surfaced and confirmed
before implementation (not discovered after the fact): the alternative
("HIGH severity always alerts regardless of direction") was offered and
explicitly declined in favor of "good news never alerts, even HIGH."

---

## What changed, concretely

| | Before this change | After |
|---|---|---|
| Black Friday (`ANO-20241129-REV`) | `escalation_suppressed=False`, `layer4_priority_flag=ESCALATE`, alert sent | `escalation_suppressed=True`, `layer4_priority_flag=SUPPRESSED`, dashboard only |
| ESCALATE tier | 15 rows (all positive spikes) | 0 rows |
| SUPPRESSED tier | 6 rows | 119 rows |
| `priority_band` / `priority_rank` | Unchanged | Unchanged — priority scoring is independent of escalation routing, so Black Friday is still ranked as high-impact, it just doesn't escalate as an alert |

---

## Every place this rippled through, and how it was verified safe

Suppressing an anomaly that used to always escalate touches every layer
downstream. Each was checked individually before being called done:

- **`3.3_external_drivers.py`** — rewrote the 3 validation assertions
  (previously: "Black Friday never suppressed", "no HIGH suppressed",
  "no UP suppressed") to their inverse-safe equivalents: Black Friday
  *is* suppressed, every good-direction anomaly is suppressed
  unconditionally, and — the safety net — every *bad*-direction
  suppression must still meet the original external-driver criteria (so
  a real, unexplained, or HIGH-severity problem can never be silently
  hidden).
- **`3.4_rca_assembly.py`** Tests 6/7/8/10 — same rewrite, independently
  re-checked via a second `positive_is_good` lookup rather than trusting
  3.3's derived columns blindly.
- **New column (`good_direction_change`)** added 1 column to the Step
  3.3 output (52→53 cols). This ripples as a fixed +1 through every
  downstream file that carries all columns forward instead of
  whitelisting a subset: `rca_assembly.csv` (45→46),
  `impact_results.csv` (51→52), `priority_results.csv` (59→60),
  `recommendations.csv`/`intelligence_results.csv` (59/68→60/69),
  `alert_payloads.csv` (73→74), `communication_results.csv` (78→79).
  Every hardcoded `shape[1] ==` assertion at each of those steps was
  updated to match. (`fact_anomalies.csv` for the dashboard was **not**
  affected — it uses an explicit column whitelist, not "carry
  everything forward.")
- **Four `len(esc) > 0` assertions** (Layer 4 Test 4, Layer 5.1 Test 05,
  5.3 Test 03, 5.4 Test 05) required at least one ESCALATE row to exist.
  Changed to allow zero — an empty ESCALATE tier is a valid outcome now,
  not a bug.
- **Two summary-printing loops** (`5.1_alert_formatter.py`,
  `5.4_communication_assembly.py`) called `.iloc[0]` on an "ESCALATE"
  group expecting it to be non-empty, which would `IndexError` on an
  empty dataframe. Fixed to skip gracefully / rely on
  `value_counts()` (which naturally omits zero-count groups).
- **Report narrative text** (`5.2_report_generator.py`) had static
  strings hardcoding "All 15 ESCALATE anomalies are HIGH-severity
  positive deviations" and similar — these were factually asserting the
  *opposite* of the new design. Made dynamic / conditional on whether
  ESCALATE has any rows.
- **Alert subject/body text** (`5.1_alert_formatter.py`) — a suppressed
  Black Friday alert used to read "External: none," which is confusing
  (it's not externally driven, it's just good news). Now reads
  "Positive change, no alert needed" when `good_direction_change` is
  set, vs. the original external-driver text otherwise.

---

## Verification

Ran the full 14-script chain (Step 2.3 through 5.5) sequentially from a
clean state:

| Check | Result |
|---|---|
| All 14 scripts (2.3 → 5.5) | Exit 0, no errors |
| `3.3_external_drivers.py` — Black Friday suppressed, all good-direction suppressed, all bad-direction suppressions externally justified | PASS |
| `3.4_rca_assembly.py` — 12 quality tests (Tests 6/7/8/10 rewritten) | All PASS |
| `4.4_intelligence_assembly.py` — 12 quality assertions | All PASS |
| `5.1/5.3/5.4` — routing, delivery, and assembly assertions | All PASS |
| Black Friday final state | `escalation_suppressed=True`, `layer4_priority_flag=SUPPRESSED`, `priority_band=HIGH` (still ranked as high business impact, just not alerted) |
| `revenue_at_risk` / "Captured Upside" dashboard numbers | Unaffected — still computed from the full anomaly set regardless of alert routing |

No test was deleted to make this pass — every changed assertion still
enforces an invariant, just the corrected one (e.g. "every suppressed
row is either good-direction or meets the original external-driver
criteria" replaces "nothing HIGH/UP is ever suppressed").

---

## Update log

- **2026-07-09** — Implemented and verified. Confirmed with the user
  beforehand that (a) HIGH severity should not override good-direction
  suppression, and (b) an empty ESCALATE tier for this dataset is an
  accepted, understood consequence rather than a bug to work around.