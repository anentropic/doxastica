---
phase: 06-structural-time-travel
reviewed: 2026-06-19T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/doxastica/core.py
  - tests/test_scope_at.py
findings:
  critical: 0
  warning: 0
  info: 1
  total: 1
status: issues_found
---

# Phase 6: Code Review Report (Re-review / Pass 2)

**Reviewed:** 2026-06-19T00:00:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found (Info-only)

## Summary

Second adversarial pass over Phase 6 (HIST-03), re-assessing the CURRENT state of
`src/doxastica/core.py` (`MemoryCore.get_scope_at`) and `tests/test_scope_at.py` after the prior
pass's fixes. The production surface is the temporal sibling of `query_scope`: an inclusive
`source_event_id <= as_of` cut applied as a PRE-filter inside the group-by loop, then a per-belief
`_order_key` ordering-max (cut-then-max = rewind), a retracted-as-of collapse, sort, and hydrate.

**Correctness verdict on the central trap: correct.** The `<= as_of` test runs BEFORE the
per-belief max (line 665, inside the `for row in rows` loop), so a since-revised belief REWINDS to
its older as-of value rather than dropping — distinct from `query_scope`'s `event_id_max`
POST-filter on already-derived tails (max-then-filter = DROP). Confirmed against
`test_cut_rewinds_to_older_value` and `test_cut_is_inclusive_at_boundary`.

**Retracted-as-of collapse (line 671)** is equivalent to `_current`'s collapse: both take the
status-agnostic ordering-max and treat a `retracted` winner as absent, so SC1
(`get_scope_at(latest) == query_scope(current)`) holds for the retracted case too.

**CLAUDE.md guideline compliance: confirmed.** No `ladybug` import (module-top imports are
`base64`/`json`/`uuid`/stdlib + first-party only); no Cypher and no `traverse` in `get_scope_at`
(composes only the `match_nodes` port primitive); append-only / pure read (no `_ensure_scope`, no
`unit_of_work`, no world-scope guard — pinned by `test_empty_scope_and_world_read`); no
narrative/LLM concepts; pydantic-only required dep untouched.

### Prior-pass disposition

- **WR-01 — RESOLVED.** The single-call snapshot invariant is now documented at core.py:652-658,
  immediately above the single `match_nodes` call (line 659). It explains why no `unit_of_work`
  wrap is needed (one auto-committed snapshot) and instructs a future maintainer to wrap BOTH
  calls per WR-02 if a second backend call is ever added here. Correct and defensible.
- **IN-01 (prior: raw-string vs enum retracted check) — re-carried below as IN-01**, downgraded in
  emphasis: the current `t["status"] != Status.retracted.value` (line 671) is correct and matches
  `_current`'s own idiom (line 230). Still a maintenance-symmetry note, not a defect.
- **IN-02 (prior: `_active_keys` recomputes `fold` per entry) — NOT re-raised.** It is a
  test-helper micro-inefficiency (performance is out of v1 scope) and the bounded op sequence keeps
  it cheap; the helper is correct. Churning it adds risk without correctness value.
- **IN-03 (prior: redundant expand-via-`get_scope_at` example) — NOT re-raised / resolved.** No
  such redundant example is present in the current test file; `expand` coverage is supplied by the
  fold machine (lines 422-425), which is sufficient for correctness.

No Critical or Warning findings remain. One Info item below.

## Info

### IN-01: Retracted-as-of collapse restates the `_current` rule inline rather than through a shared predicate

**File:** `src/doxastica/core.py:671` (cf. `_current` at `src/doxastica/core.py:230`,
`query_scope` at `src/doxastica/core.py:594`)
**Issue:** `get_scope_at` collapses retracted winners with a raw value compare
`t["status"] != Status.retracted.value`. This is correct and deliberately consistent with
`_current`'s own `tail["status"] == Status.retracted.value` collapse, so it is NOT a defect — both
implement the same "retracted tail clears the belief" rule. The residual observation is
maintenance symmetry: the ordering contract is centralized in `_order_key` ("the ONE ordering
contract"), but the logically-paired "retracted tail ⇒ absent" rule is restated inline in three
sites (`_current`, `query_scope`, `get_scope_at`) with two different idioms (raw `!= .value`
here and in `_current`; enum-membership `Status(...) in allowed` in `query_scope`). Under the
closed `{active, retracted}` taxonomy (DATA-06, models.py:45-46) all three agree exactly. A
hypothetical third `Status` would diverge — the two `!= retracted` sites would INCLUDE it,
`query_scope`'s allow-set would EXCLUDE it — but adding a third status is a deliberate,
reviewed change to a closed taxonomy, so this is a future-proofing nicety, not a live risk.
**Fix:** Optional. Extract a tiny `_is_active_tail(row: dict[str, Any]) -> bool` predicate
(`row["status"] != Status.retracted.value`) and call it from both `_current` and the
`get_scope_at` collapse so the active-tail definition has one home alongside `_order_key`.
Behavior-preserving. Skip if the closed-taxonomy assumption is considered a sufficient guard.

---

_Reviewed: 2026-06-19T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
