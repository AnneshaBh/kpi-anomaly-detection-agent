# Direction filter deletes positive anomalies instead of suppressing alerts

**Status:** Fixed
**Opened:** 2026-07-02 (found by Annesha, documented in `updates/update1/`)
**Fixed:** 2026-07-09
**Severity:** High — pipeline crash, silent data loss
**Files touched:** `scripts/detection/2.3_Ensemble_Voting.py`

---

## Symptom

Clicking "Refresh Pipeline" in the dashboard failed with:

```
File "scripts/rca/3.3_external_drivers.py", line 423, in main
    assert len(bf) > 0 and not bf.iloc[0]["escalation_suppressed"], \
AssertionError: FAIL: Black Friday revenue anomaly should NOT be suppressed
```

The pipeline crashed at Layer 3, Step 3.3, before reaching Layer 4/5. No alerts,
reports, or dashboard data were generated for that run.

---

## Root cause

`total_revenue_usd` on 2024-11-29 (Black Friday) wasn't suppressed and then
found — it wasn't in the dataset at all by the time Step 3.3 ran. Tracing it
back to Step 2.3 (`scripts/detection/2.3_Ensemble_Voting.py`) found the row
being deleted two layers upstream, at the anomaly-detection stage.

A prior change (commit `e8105f6`) added a `positive_is_good` flag per KPI in
`data/config/tier_config.json` (e.g. `total_revenue_usd: true`, `return_rate:
false`) and a new `apply_direction_filter()` step meant to stop the pipeline
from alerting on "good news" — e.g. revenue going *up* is not a problem, so
it shouldn't page anyone.

The intent was right, the wiring was wrong. `apply_direction_filter()`
computed a `direction_suppressed` audit flag correctly, but then this line
used it to physically remove the row from the confirmed-anomaly output:

```python
# scripts/detection/2.3_Ensemble_Voting.py (before fix)
confirmed = matrix[matrix["confirmed"] & ~matrix["direction_suppressed"]].copy()
```

`confirmed` is what gets written to `data/detection/anomaly_results.csv` —
the single source feeding every downstream layer (RCA, intelligence,
alerts, dashboard). So "don't alert on this" became "this anomaly no
longer exists anywhere in the system." Any UP-direction anomaly on a
`positive_is_good` KPI (revenue, orders, ROAS, sessions, clicks,
inventory health) was silently dropped before Layer 3 ever saw it —
including Black Friday, Cyber Monday, and the back-to-school revenue
spike.

**Measured impact:** `anomaly_results.csv` dropped from **182 rows to
51 rows** — a 72% data loss — well before the crash was ever surfaced by
the Step 3.3 assertion. The assertion didn't cause the problem; it was
just the first place in the pipeline that happened to check for a
specific row (`2024-11-29` / `total_revenue_usd`) and get nothing back.

This also silently broke the dashboard's "Captured Upside" metric, since
that number is computed from the same UP-direction anomalies that were
being deleted.

---

## Why this wasn't caught earlier

- No test checks that expected rows/events still exist in
  `anomaly_results.csv` after Step 2.3 — the only checks are on `matrix`
  shape (which stays 8,772 rows regardless, since `direction_suppressed`
  is a column on the full matrix, not a row filter) and on later files
  that only assert properties of whatever *does* make it through (e.g.
  "no HIGH anomaly is suppressed" — true, because it's not that HIGH
  anomalies were suppressed, they were deleted before that check ran).
- `3.3_external_drivers.py`'s own Black Friday assertion is what
  eventually surfaces this class of bug, but only for that one
  hard-coded date/KPI — any other deleted row fails silently.

---

## Fix

Kept `direction_suppressed` / `direction_suppression_reason` as audit-only
columns (still written to `ensemble_voting_matrix.csv` for visibility),
but stopped them from removing rows from the confirmed output:

```python
# scripts/detection/2.3_Ensemble_Voting.py (after fix, line 537)
confirmed = matrix[matrix["confirmed"]].copy()
```

This is a minimal, one-line behavioral change — nothing else about
voting, scoring, or severity logic was touched. It intentionally does
**not** implement "don't alert on good news" — that's a separate,
larger design change (see [Follow-up](#follow-up) below). This fix
only stops the pipeline from *deleting* data; alert routing is
unchanged from before commit `e8105f6`, i.e. Black Friday still
escalates as an alert, same as it always did.

---

## Verification (does not break the working pipeline)

Re-ran the full pipeline end-to-end from a clean state (all 17 scripts,
Layers 1 through 5) after the fix:

| Check | Result |
|---|---|
| All 17 pipeline scripts | Exit 0, no errors |
| `anomaly_results.csv` row count | Restored (was 51, back to full detection output) |
| Black Friday (`2024-11-29`, `total_revenue_usd`) | Present, `escalation_suppressed=False`, `layer4_priority_flag=ESCALATE` |
| `3.3_external_drivers.py` Black Friday assertion | PASS |
| `3.4_rca_assembly.py` — 12 quality tests | All PASS (incl. Test 6: Black Friday, Test 7: no HIGH suppressed, Test 8: no UP suppressed) |
| SQLite table row-count parity checks | PASS |
| Layer 4 priority flag distribution | ESCALATE / INVESTIGATE / MONITOR / SUPPRESSED counts match the pipeline's own documented targets |

No existing test, assertion, or downstream script needed to change to
apply this fix — confirming it doesn't break any currently-passing
pipeline behavior.

Note: exact anomaly counts vary slightly run-to-run (e.g. 181 vs 183
rows have both been observed) because Method B (Isolation Forest) and
Method C (Prophet) in Step 2.2 aren't seeded, so borderline votes can
flip between runs. This is a separate, pre-existing non-determinism
issue, unrelated to this bug — the fix behaves identically regardless
of which exact row count a given run produces.

---

## Follow-up

**Resolved 2026-07-09** — see
[2026-07-09-implement-good-news-never-alerts.md](2026-07-09-implement-good-news-never-alerts.md).
Annesha's original goal ("don't alert on good news") is now implemented
properly: good-direction anomalies are suppressed unconditionally
(including HIGH severity), using the polarity-corrected version of the
rule described there.

---

## Update log

- **2026-07-09** — Fixed. One-line change in `2.3_Ensemble_Voting.py`,
  full pipeline re-verified end-to-end, committed in `fef6bf4`.
- **2026-07-02** — Opened. Root cause independently documented by
  Annesha in `updates/update1/` (`update1.md`,
  `positive_changes_incorrectly_flagged.md`,
  `positive_changes_incorrectly_flagged_after_update.md`).