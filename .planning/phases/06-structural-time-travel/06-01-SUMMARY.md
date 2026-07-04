---
phase: 06-structural-time-travel
plan: 01
subsystem: api
tags: [time-travel, get_scope_at, query_scope, cqrs, event-sourcing, agm, hypothesis, pytest]

# Dependency graph
requires:
  - phase: 03-revision-spine
    provides: "_order_key (the ONE ordering contract), _current_tail / _current (retracted-tail collapse), _append_state write spine"
  - phase: 04-retrieval-observation-surface
    provides: "query_scope (the direct template), _hydrate value-decode boundary, pure-read surface (no _ensure_scope / unit_of_work), match_nodes-only composition"
provides:
  - "MemoryCore.get_scope_at — temporal cut-then-max reconstruction of a scope's active belief base AS OF an event (HIST-03), the last unimplemented BeliefStore method"
  - "tests/test_scope_at.py — 7 parametrized two-backend example tests (cut-rewind regression guard for the central trap; the operational-fold property machine is plan 06-02)"
affects: [06-02-operational-fold-oracle, 07-conformance-suite, nvm-cqrs-replay]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "cut-then-max (REWIND): an inclusive source_event_id <= as_of PRE-filter applied BEFORE the per-belief ordering-max, so an older value resurfaces — vs query_scope's max-then-filter DROP"
    - "retracted-as-of collapse: the _current retracted-tail→absent rule computed over the cut window, not 'now'"

key-files:
  created:
    - tests/test_scope_at.py
    - .planning/phases/06-structural-time-travel/deferred-items.md
  modified:
    - src/doxastica/core.py

key-decisions:
  - "Inline cut in the group-by loop (not an as_of param threaded through _current_tail) — Claude's discretion (D-06): mirrors query_scope's shape, touches no existing helper, so the Phase-3/4 keystone stays byte-for-byte behaviour-preserving"
  - "The cut is the ONLY structural divergence from query_scope: moved from a step-6 POST-filter on derived tails to a PRE-filter on candidate rows inside the group-by loop"
  - "No include_retracted flag / no status-set resolution — the as-of base is always active-as-of"

patterns-established:
  - "cut-then-max temporal reconstruction: PRE-filter candidates to <= as_of, THEN per-belief _order_key max — the placement is the whole phase"
  - "reuse the ONE _order_key for the cut str-form, the per-group max, AND the final sort (never a second ordering, D-05)"

requirements-completed: [HIST-03]

# Metrics
duration: 5min
completed: 2026-06-19
---

# Phase 6 Plan 01: get_scope_at Temporal Reconstruction Summary

**`MemoryCore.get_scope_at` implements as-of-event belief-base reconstruction via an inclusive cut-then-max over `match_nodes` — the cut REWINDS a since-revised belief to its older value rather than dropping it — guarded by 7 two-backend example tests.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-19T07:15:28Z
- **Completed:** 2026-06-19T07:20:28Z
- **Tasks:** 2
- **Files modified:** 3 (1 source, 1 test created, 1 deferred-items log)

## Accomplishments
- Implemented `MemoryCore.get_scope_at(scope_id, as_of_event_id)` — the last unimplemented `BeliefStore` method (HIST-03), composing ONLY `match_nodes` (no `traverse`, no edge walk, no new import).
- Landed the Wave-0 failing example tests FIRST (RED), then made them GREEN — the local spec / regression guard for the central trap of the phase (cut-then-max vs max-then-cut).
- The defining behaviour proven on BOTH backends: an inclusive `source_event_id <= as_of` cut applied as a PRE-filter BEFORE the per-belief ordering-max, so an OLDER value resurfaces for a since-revised belief (REWIND), in contrast to `query_scope`'s `event_id_max` POST-filter (DROP).
- Regression + purity suite stays green: `test_invariants`, `test_query_scope`, `test_revision_spine`, `test_import_purity` — the Phase-3/4 keystone is behaviour-preserving and `core.py` stays driver-blind. Full suite: 182 passed.

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Wave-0 failing example tests for get_scope_at** - `726ce39` (test) — RED
2. **Task 2: Implement MemoryCore.get_scope_at** - `1dbc56b` (feat) — GREEN

_TDD RED→GREEN across two commits; no REFACTOR commit was needed (the GREEN body matched the planned shape)._

## Files Created/Modified
- `tests/test_scope_at.py` - NEW. 7 named parametrized example tests × 2 backends (14): `test_cut_rewinds_to_older_value`, `test_cut_is_inclusive_at_boundary`, `test_scope_at_latest_equals_query_scope_now`, `test_retracted_as_of_collapse`, `test_single_event_multi_belief_inclusive`, `test_empty_scope_and_world_read`, `test_scope_at_deterministic_order`, plus the `_event_id`/`_core`/`_ids` preamble copied from `test_query_scope.py`.
- `src/doxastica/core.py` - ADD the `get_scope_at` body after `query_scope`. Inclusive `<= as_of` cut PRE-filter inside the group-by loop → per-group `_order_key` max → retracted-as-of collapse → `_order_key` sort → `_hydrate`. No signature change, no new import, no `traverse`.
- `.planning/phases/06-structural-time-travel/deferred-items.md` - NEW. Logs one out-of-scope pre-existing `ruff format` discrepancy at `core.py:68` (`_CASCADE_EDGE_TYPES`), unrelated to this change.

## Decisions Made
- **Inline cut over a helper parameter (D-06 Claude's discretion):** applied the cut inline in `get_scope_at`'s own group-by loop rather than threading an `as_of` bound through the shared `_current_tail`. This mirrors `query_scope`'s shape exactly, touches no existing helper, and keeps `_current`/`query_scope` byte-for-byte behaviour-preserving — confirmed by the green regression suite.
- **No status-set machinery:** dropped `query_scope`'s `include_retracted`/`allowed`-set resolution entirely; the as-of base is always active-as-of, so the only status handling is the single retracted-tail collapse over the cut window (D-06).
- **`str`-vs-`str` cut normalized once** (`as_of = str(as_of_event_id)`) reusing the `_order_key` form (D-04) — never `str`-vs-`UUID`.

## Deviations from Plan

None — plan executed exactly as written. The two TDD tasks ran RED→GREEN as specified, the inline-cut factoring was the plan's recommended option, and no auto-fix (Rule 1-3) or architectural decision (Rule 4) was triggered.

## Issues Encountered
- **Ruff E501 on new docstring/comment/test lines:** several added lines exceeded the 100-char limit on first write. Wrapped them (test file and the `get_scope_at` docstring + one comment) until `ruff check` passed clean on both files. Routine formatting, not a behaviour change.
- **Pre-existing `ruff format` discrepancy at `core.py:68`** (`_CASCADE_EDGE_TYPES` frozenset literal): confirmed present at HEAD before this plan (`git show HEAD:... | ruff format --check` flags it), unrelated to the `get_scope_at` addition far below. Left untouched per the scope boundary; logged to `deferred-items.md`. The Task-2 commit passed pre-commit hooks (exit 0), so it does not block.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- HIST-03 is implemented and green on both backends; SC1 (`get_scope_at(latest) == query_scope(current)`), the inclusive-boundary, retracted-as-of, multi-belief-event, empty/world, and deterministic-order behaviours are all proven.
- **Plan 06-02** adds the operational-fold `RuleBasedStateMachine` (the `fold(ops, as_of)` oracle + `get_scope_at == fold` invariant, D-07/SC2/SC3) to the SAME `tests/test_scope_at.py` file — the example-test preamble (`_event_id`/`_core`/`_ids`) is already in place for it to extend.
- No blockers. The pre-existing `core.py:68` format nit is the only deferred item and is non-blocking.

## Self-Check: PASSED

- FOUND: `tests/test_scope_at.py`
- FOUND: `src/doxastica/core.py` (`def get_scope_at` body)
- FOUND: `.planning/phases/06-structural-time-travel/06-01-SUMMARY.md`
- FOUND: `.planning/phases/06-structural-time-travel/deferred-items.md`
- FOUND commit `726ce39` (test, Task 1 RED)
- FOUND commit `1dbc56b` (feat, Task 2 GREEN)

---
*Phase: 06-structural-time-travel*
*Completed: 2026-06-19*
