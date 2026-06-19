---
phase: 07-agm-hansson-conformance-suite
plan: 02
subsystem: testing
tags: [hypothesis, stateful-testing, conformance-suite, get_scope_at, agm, formal-03, back-05]

# Dependency graph
requires:
  - phase: 06-temporal-reconstruction
    provides: "get_scope_at + the independent operational-fold replay oracle (scope_at_equals_fold_for_every_cut)"
  - phase: 07-agm-hansson-conformance-suite
    provides: "07-01 _FORMAL_03_CONFORMANCE_SET registry in tests/test_invariants.py (the canonical half)"
provides:
  - "get_scope_at ≡ replay registered as a named FORMAL-03 conformance member (D-08) in tests/test_scope_at.py"
  - "Reciprocal FORMAL-03 registry marker pairing test_scope_at.py with the canonical set in test_invariants.py"
affects: [07-03, 07-04, conformance-suite, m0-exit-gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FORMAL-03 conformance-set registration via paired registry markers across sibling test files (registration, not re-implementation)"

key-files:
  created: []
  modified:
    - tests/test_scope_at.py

key-decisions:
  - "07-02: registered the existing Phase-6 fold property into FORMAL-03 via a reciprocal registry comment block + a named _FORMAL_03_CONFORMANCE_MEMBER constant — NO new replay function, fold oracle left byte-unchanged (D-08)"

patterns-established:
  - "Paired conformance-set registry markers: test_invariants.py holds _FORMAL_03_CONFORMANCE_SET (members 1-3 + a pointer to member 4); test_scope_at.py holds the reciprocal member-4 marker. Registration only."

requirements-completed: [FORMAL-03, BACK-05]

# Metrics
duration: 4min
completed: 2026-06-19
---

# Phase 7 Plan 02: Register get_scope_at ≡ replay into FORMAL-03 Conformance Set Summary

**The Phase-6 operational-fold property `scope_at_equals_fold_for_every_cut` is now NAMED into the FORMAL-03 structural-invariant conformance set (D-08) via a reciprocal registry marker, still independent of the SUT and still green on both backends.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-19T13:35:30Z
- **Completed:** 2026-06-19T13:39:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added a FORMAL-03 conformance-set registry block to `tests/test_scope_at.py` that NAMES `scope_at_equals_fold_for_every_cut` as the `get_scope_at ≡ replay` member of the named structural-invariant set (D-08), reciprocal to the canonical `_FORMAL_03_CONFORMANCE_SET` registered in 07-01's `tests/test_invariants.py`.
- Added a `_FORMAL_03_CONFORMANCE_MEMBER` module constant pinning the member name (grep-discoverable, consistent with 07-01's `test_invariants.py` registry idiom).
- Confirmed the `fold` replay oracle remains INDEPENDENT of the system-under-test: its body selects the winner via `max(...)` over `self.entries` and never calls `get_scope_at` / `_current_tail` / `_current` / `query_scope` (anti-tautology, Pitfall 6 — the only `get_scope_at` mention inside `fold` is its docstring declaring that independence).
- Verified the property still rides BOTH backends via the `MemoryScopeAtFoldMachine` / `LadybugScopeAtFoldMachine` two-subclass `.TestCase` idiom (BACK-05); ladybug runs (not skipped) when the extra is installed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Register get_scope_at ≡ replay into the FORMAL-03 conformance set** - `a9f237f` (test)

## Files Created/Modified
- `tests/test_scope_at.py` - Added the reciprocal FORMAL-03 conformance-set registry block + `_FORMAL_03_CONFORMANCE_MEMBER` constant before the dual-backend `.TestCase` subclasses. The existing `fold` oracle, cut logic, `_make_backend`, and `teardown` are unchanged (registration, not re-implementation).

## Decisions Made
- Chose the "re-reference the existing dual-backend property" path (the cleaner, sufficient option D-08 explicitly permits) over re-expressing the property as a new `@invariant`. No new replay function and no production reconstruction helper is called from the oracle, so the equivalence stays a real cross-check rather than a restatement.

## Deviations from Plan

None - plan executed exactly as written. (One trivial in-task formatting fix to satisfy ruff E501 line-length on a comment line, made before the commit — not a behavior deviation.)

## Issues Encountered
- A comment line in the new registry block initially exceeded the 100-char ruff E501 limit. Re-wrapped the line within the same comment; `ruff check` and `basedpyright` both clean afterward. No logic affected.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- FORMAL-03 now has all four members named into the conformance set across the two sibling files (members 1-3 in `test_invariants.py`, member 4 — `get_scope_at ≡ replay` — in `test_scope_at.py`).
- Remaining FORMAL-03/Phase-7 work (FORMAL-01/02 postulates, FORMAL-04 Recovery xfail, FORMAL-05 irony join) continues in plans 07-03 / 07-04.

## Self-Check: PASSED

- FOUND: tests/test_scope_at.py (modified)
- FOUND: commit a9f237f
- Verification: `uv run --extra ladybug pytest tests/test_scope_at.py -q` → 16 passed (both backends); `ruff check` + `basedpyright` clean.

---
*Phase: 07-agm-hansson-conformance-suite*
*Completed: 2026-06-19*
