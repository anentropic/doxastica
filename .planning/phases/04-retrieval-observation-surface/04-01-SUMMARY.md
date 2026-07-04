---
phase: 04-retrieval-observation-surface
plan: 01
subsystem: testing
tags: [agm, query_scope, belief-filter, hypothesis, pytest, parametrized-backend, protocol]

# Dependency graph
requires:
  - phase: 01-protocol-backend-port-data-model-decisions
    provides: BeliefStore Protocol, closed BeliefFilter, BackendPort, parametrized two-backend conftest
  - phase: 03-append-only-revision-spine-keystone
    provides: MemoryCore revise/expand/contract/get_revision_chain, _order_key, derived current, SUPERSEDES edges
provides:
  - "D-03 public-flag rename include_deprecated -> include_retracted on the BeliefStore Protocol + the two planning doc sites"
  - "tests/test_query_scope.py — failing (RED) Wave-0 behavior scaffold encoding every HIST-01 + CHAIN-04 VALIDATION.md row, parametrized over both backends"
affects: [04-02 query_scope implementation, 07-agm-postulate-conformance-suite]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RED test-first scaffold typed via typing.cast(BeliefStore, MemoryCore(backend)) so query_scope type-checks while failing at runtime"
    - "One named test per VALIDATION.md row; superseded cells observed only through get_revision_chain[:-1], never query_scope"

key-files:
  created:
    - tests/test_query_scope.py
  modified:
    - src/doxastica/protocol.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "Annotate test cores via a _core() helper returning cast('BeliefStore', MemoryCore(backend)) — MemoryCore does not yet satisfy the full Protocol (add_edge/get_impact/get_scope_at land later), so a direct annotated assignment would fail strict typing; cast narrows only the query_scope surface and is a runtime no-op, preserving the RED AttributeError."
  - "ROADMAP grep-gate compliance required clearing the include_deprecated token from line 147 (the plan-listing line) too, plus aligning the Phase-4 'deprecated' matrix vocabulary to 'retracted vs superseded' for internal consistency."

patterns-established:
  - "Test-first RED scaffold: cast to the typed public Protocol so basedpyright strict + ruff stay clean while the body is genuinely absent (runtime AttributeError is the RED signal)."
  - "Four-cell retracted-vs-superseded matrix read through TWO surfaces: query_scope for the current row, get_revision_chain[:-1] split by .status for the two superseded cells."

requirements-completed: [CHAIN-04, HIST-01]

# Metrics
duration: 9min
completed: 2026-06-18
---

# Phase 4 Plan 01: D-03 Rename + Wave-0 query_scope RED Scaffold Summary

**Landed the include_deprecated -> include_retracted public-flag rename (D-03) on the BeliefStore Protocol + both planning doc sites, and created the 22-test (11 behaviors x 2 backends) failing query_scope scaffold encoding every HIST-01 + CHAIN-04 VALIDATION.md row.**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-06-18T15:20:28Z
- **Completed:** 2026-06-18T15:29:34Z
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- D-03 rename applied at all four in-scope sites: protocol.py signature + 2 docstring mentions, REQUIREMENTS.md (CHAIN-04 + HIST-01), ROADMAP.md (Phase-4 success criteria + description + plan-listing line). The `include_deprecated` grep gate (`src tests .planning/REQUIREMENTS.md .planning/ROADMAP.md`) is empty.
- `tests/test_query_scope.py` created: 11 named test functions x {memory, ladybug} = 22 parametrized tests, one per HIST-01 + CHAIN-04 row from 04-VALIDATION.md, RED by design (`AttributeError: 'MemoryCore' object has no attribute 'query_scope'`).
- The four-cell retracted-vs-superseded matrix (CHAIN-04) is encoded reading the current row through `query_scope` and the two superseded cells through `get_revision_chain[:-1]` — never asking `query_scope` for superseded history (D-05).
- `models.py` / `Status` untouched (DATA-06 frozen `{active, retracted}`); no runtime import added to `protocol.py` (import-purity gate intact).
- Phase-3 keystone (`test_invariants.py` + `test_revision_spine.py`) stays GREEN; full suite is 106 passed / 22 RED (only the new scaffold red).

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename include_deprecated -> include_retracted (Protocol + 2 doc sites, D-03)** - `d03f6eb` (refactor)
2. **Task 2: Create failing Wave-0 tests/test_query_scope.py (parametrized, both backends)** - `2bb0d6a` (test)

**Plan metadata:** see final docs commit.

## Files Created/Modified
- `tests/test_query_scope.py` - NEW: 22-test RED behavior scaffold for query_scope (HIST-01 + CHAIN-04), parametrized over both backends; closed BeliefFilter only.
- `src/doxastica/protocol.py` - query_scope keyword renamed to `include_retracted` (signature + 2 docstring mentions); precedence wording kept verbatim.
- `.planning/REQUIREMENTS.md` - CHAIN-04 + HIST-01 text carry the `include_retracted` / "retracted" rename.
- `.planning/ROADMAP.md` - Phase-4 success criteria, goal/description, and plan-listing line carry the rename; matrix vocabulary aligned to "retracted vs superseded".

## Decisions Made
- **Typed the RED scaffold via `cast('BeliefStore', MemoryCore(backend))`** in a `_core()` helper. `MemoryCore` does not yet satisfy the full `BeliefStore` Protocol (`add_edge` / `get_impact` / `get_scope_at` are Phase 5/6), so a plain `core: BeliefStore = MemoryCore(backend)` annotation fails basedpyright strict (`reportAssignmentType`). `cast` narrows only the `query_scope` surface this scaffold exercises and is a runtime no-op, so the call still raises `AttributeError` at runtime (the intended RED signal) while keeping basedpyright strict + ruff clean — satisfying the phase verification gate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ROADMAP plan-listing line cleared of the include_deprecated token**
- **Found during:** Task 1 (D-03 rename)
- **Issue:** The plan task narrative focused on ROADMAP lines 139-140 (success criteria), but the D-03 grep gate `! grep -rn include_deprecated ... .planning/ROADMAP.md` must be empty; ROADMAP line 147 (the 04-01 plan-listing entry) also contained the literal `include_deprecated→include_retracted` token, which would have kept the gate non-empty.
- **Fix:** Reworded line 147 to "D-03 public-flag rename to `include_retracted`" (token removed) and aligned the Phase-4 "deprecated" matrix vocabulary (lines 38, 134) to "retracted/superseded" for internal consistency.
- **Files modified:** .planning/ROADMAP.md
- **Verification:** `grep -rn include_deprecated src tests .planning/REQUIREMENTS.md .planning/ROADMAP.md` returns no hits (exit 1).
- **Committed in:** d03f6eb (Task 1 commit)

**2. [Rule 1 - Bug] E501 line-length + basedpyright-strict cleanliness on the new test file**
- **Found during:** Task 2 (test scaffold creation)
- **Issue:** Initial draft had 11 E501 (>100 char) lines and, before the cast approach, flooded basedpyright with reportUnknown*/reportAttributeAccessIssue (89 errors) from calling a not-yet-existing `query_scope`. Pre-commit runs ruff + basedpyright on tests, so the commit would fail.
- **Fix:** Wrapped/shortened the long docstrings + assert messages; introduced the `_core()` cast helper to type the call surface (see Decisions). Result: 0 ruff errors, 0 basedpyright errors, file still RED at runtime.
- **Files modified:** tests/test_query_scope.py
- **Verification:** `ruff check` + `ruff format --check` + `basedpyright` all clean; `pytest` still 22 RED via AttributeError.
- **Committed in:** 2bb0d6a (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes were necessary to satisfy the plan's own verification gate (empty grep gate; basedpyright strict + ruff clean on the new file). No scope creep — no `query_scope` body was implemented (that is plan 04-02).

## Issues Encountered
- The `core: BeliefStore = MemoryCore(backend)` annotation initially seemed viable (an isolated probe passed) but failed in the test file because `MemoryCore` is an incomplete Protocol implementor until Phase 6. Resolved with `typing.cast` (runtime-transparent), which keeps the RED runtime semantics while type-checking cleanly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 04-02 (Wave 2) can now implement `MemoryCore.query_scope` GREEN-driven: every required behavior is pinned as a parametrized two-backend test. Recommended implementation per RESEARCH/PATTERNS: add a status-agnostic `_current_tail` helper (factor of `_current`, reuse `_order_key`), then `query_scope` = single scope-wide `match_nodes` scan -> group-by-belief max -> status filter -> belief_ids narrow -> event-range post-filter -> `_order_key` sort -> `_hydrate`.
- No blockers. The 22 tests are RED for exactly one reason (missing `query_scope` body); once the body lands they should go GREEN on both backends.

## Self-Check: PASSED

- FOUND: tests/test_query_scope.py
- FOUND: .planning/phases/04-retrieval-observation-surface/04-01-SUMMARY.md
- FOUND commit: d03f6eb (Task 1 — D-03 rename)
- FOUND commit: 2bb0d6a (Task 2 — RED query_scope scaffold)

---
*Phase: 04-retrieval-observation-surface*
*Completed: 2026-06-18*
