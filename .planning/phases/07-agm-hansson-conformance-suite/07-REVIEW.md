---
phase: 07-agm-hansson-conformance-suite
reviewed: 2026-06-19T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/doxastica/core.py
  - tests/test_invariants.py
  - tests/test_irony_join.py
  - tests/test_recovery_xfail.py
  - tests/test_scope_at.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-06-19
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found (info only — no blocker, no warning)

## Summary

Phase 7 is the M0 exit-gate conformance/proof suite. The only production change is the
extraction of the pure `_current_tails(rows, allowed)` helper in `src/doxastica/core.py`,
with `query_scope` delegating to it. The remaining four files are test code.

I reviewed against the phase-specific risk surface: the `_current_tails` refactor
correctness, the anti-tautology discipline of the oracles, the strict-xfail Recovery
guard, and the core boundary (no narrative naming, no string-Cypher, no `ladybug`
import). I also re-ran the full affected suite.

**Assessment: the implementation is sound.** No blockers and no warnings. Two minor
INFO items only (stale docstrings). Verified facts:

- **Refactor is behavior-preserving.** The diff (`git diff c05b86b..HEAD -- core.py`)
  shows `_current_tails` is a byte-identical lift of the prior inline group-by-max +
  status-filter-after-max block; `query_scope` now calls
  `list(_current_tails(rows, allowed).values())`. The Pitfall-2 ordering contract
  (status filter strictly AFTER the per-belief `_order_key` MAX) is preserved and
  single-sourced. `tests/test_query_scope.py` (22) + `tests/test_revision_spine.py` (22)
  all pass — no regression.
- **Ordering contract single-sourced.** `_current_tails`, `_current_tail`, `_current`,
  `get_revision_chain`, `query_scope`, and `get_scope_at` all route through the one
  `_order_key` definition and the one `_is_active_tail` predicate. No second ordering.
- **Anti-tautology discipline holds.** `_shadow_current` / `_shadow_base`
  (test_invariants.py) and `fold` (test_scope_at.py) compute expected results purely
  from `self.entries` and NEVER call `query_scope` / `get_scope_at` / `_current` /
  `_current_tail` / `get_revision_chain`. Grep-confirmed: SUT names appear only in
  docstrings or in the assertion (checked) side, never as the expected source. The
  oracle's `(source_event_id_str, append_seq)` winner faithfully mirrors the core's
  `(str(source_event_id), str(state_id))` because uuid7 is string-monotonic with append
  order (verified empirically), so `append_seq` is a valid `state_id` tiebreak stand-in.
- **Recovery strict-xfail is genuine.** `strict=True` is on the mark itself
  (pyproject has `addopts = "-v"` only, no global `xfail_strict` — confirmed). The
  counterexample genuinely fails (`base == {"p":"v"}` is `False`; observed is
  `{"p":"vprime"}`), so it reports `xfailed`, not an erroneous XPASS — confirmed by both
  a direct repro and a full run (`x..` for the file).
- **Core boundary intact.** No `irony`/`actor`/`dramatic`/narrative naming in core
  (the divergence-join helper stays test-level in `test_irony_join.py`). No module-level
  `ladybug` import. No string-interpolated/f-string Cypher (the only f-strings are error
  messages). No debug artifacts.
- **Full Phase-7 run:** 28 passed, 1 xfailed.

## Info

### IN-01: Stale module docstring claims `get_scope_at` is unimplemented (RED)

**File:** `tests/test_scope_at.py:24-27`
**Issue:** The top-of-file docstring still reads "`MemoryCore.get_scope_at` has no body
yet (the protocol stub returns `...`)" and "RED-until-06-02-impl is the correct,
intended state." This is no longer true: `get_scope_at` is fully implemented
(`src/doxastica/core.py:655-719`) and every test in this file now passes GREEN. The
stale wording could mislead a future reader into thinking RED is expected here and
weakening a test that legitimately fails for a real reason.
**Fix:** Update the docstring to reflect that the body has landed and the file is now a
GREEN conformance/regression suite. For example, replace the "RED-until-06-02-impl"
paragraph with a note that Task 2 landed the body and these are the held regression
guards plus the operational-fold conformance member.

### IN-02: Stale "Wave 0 / Half B added by plan 06-02" framing in `test_scope_at.py`

**File:** `tests/test_scope_at.py:1, 21-22, 247`
**Issue:** The header calls this the "Wave-0 example-test scaffold" and says the
operational-fold machine "are added to THIS file by plan 06-02" / "HALF B ... The
correctness deliverable" — future-tense phrasing for work that is already present in the
same file (`_ScopeAtMachine`, `fold`, and the `.TestCase` subclasses at lines 303-536).
Not a correctness defect, but the tense/provenance comments describe a build order that
has already completed and should be reconciled so the file documents its current state.
**Fix:** Adjust the header/section comments to present tense (the fold machine and the
example regression guards both live here now); keep the design rationale, drop the
"added by plan 06-02 / RED-until" temporal framing.

---

_Reviewed: 2026-06-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
