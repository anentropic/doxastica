---
phase: 04-retrieval-observation-surface
plan: 02
subsystem: core
tags: [agm, query_scope, belief-base, derived-current, order-key, two-backend, hist-01, chain-04]

# Dependency graph
requires:
  - phase: 03-append-only-revision-spine-keystone
    provides: MemoryCore revise/expand/contract/get_revision_chain, _order_key, _current, _hydrate, SUPERSEDES edges
  - phase: 04-retrieval-observation-surface
    plan: 01
    provides: D-03 include_retracted rename + 22 RED query_scope behavior tests (both backends)
provides:
  - "MemoryCore.query_scope — the AGM belief base B observed 'as of now' (HIST-01) on both backends"
  - "MemoryCore._current_tail — the status-agnostic ordering-max tail helper (factor of _current)"
  - "The retracted-vs-superseded four-cell matrix (CHAIN-04) provable via query_scope + get_revision_chain"
affects: [07-agm-postulate-conformance-suite, 05-consumer-edges-impact-cascade, 06-as-of-reconstruction]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Status-agnostic current-tail factor: _current_tail does the match_nodes + max(_order_key); _current applies the retracted->None collapse on top (behaviour-preserving)"
    - "Single scope-wide match_nodes scan + core-side group-by-belief per-group ordering-max (one backend round-trip; parity holds because grouping is core-side Python over raw dicts)"
    - "Event-range as an inclusive str-vs-str POST-filter on derived tails (never an as-of rewind)"

key-files:
  created: []
  modified:
    - src/doxastica/core.py

key-decisions:
  - "Moved the BeliefFilter runtime import from Task 1 to Task 2 (the commit that first uses it): an unused import fails the Task-1 pre-commit gate (ruff F401 + basedpyright reportUnusedImport strict). Each atomic commit stays self-consistent."
  - "query_scope reuses the ONE _order_key for BOTH the per-belief group-by max AND the result sort (D-07) — no second ordering function introduced (grep 'key=_order_key' = 3: _current_tail max, query_scope max-via-key, query_scope sort)."

patterns-established:
  - "Factor-then-specialise for derived selectors: a status-agnostic raw selector (_current_tail) that a status-collapsing wrapper (_current) delegates to — both bound to the single _order_key contract so the read surface cannot desync from the write spine."

requirements-completed: [CHAIN-04, HIST-01]

# Metrics
duration: 3min
completed: 2026-06-18
---

# Phase 4 Plan 02: query_scope Body + Status-Agnostic _current_tail Summary

**Implemented `MemoryCore.query_scope` as a single scope-wide `match_nodes` scan -> group-by-belief ordering-max -> status filter -> belief_ids narrow -> inclusive event-range post-filter -> `_order_key` sort -> `_hydrate`, and factored the status-agnostic `_current_tail` helper out of `_current` — turning the 22 Wave-1 RED tests GREEN on both backends with the Phase-3 keystone unbroken.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-06-18T15:32:22Z
- **Completed:** 2026-06-18T15:35:00Z
- **Tasks:** 2
- **Files modified:** 1 (0 created, 1 modified)

## Accomplishments
- `_current_tail(scope_id, belief_id)` added: the raw status-agnostic ordering-max tail over ALL statuses, reusing the ONE `_order_key` contract, BEFORE the retracted->None collapse. `_current` now delegates to it then applies only the retracted->None rule (D-05 write-side contract) — behaviour-preserving for every Phase-3 caller.
- `query_scope` implemented as the 8-step single-scan composition (PATTERNS.md / RESEARCH Pattern 2): status-set resolution with explicit-`status`-governs precedence (D-02/D-03), ONE scope-wide round-trip, core-side group-by-belief per-group max (status filter AFTER the max — Pitfall 2), `belief_ids` narrow, inclusive str-vs-str event-range post-filter (D-06/A1 — Pitfall 3), `_order_key` sort (D-07), `_hydrate`.
- Pure read (D-08): `query_scope` calls neither `_ensure_scope` nor `unit_of_work` and raises nothing; an absent/empty scope returns `[]` and creates no `Scope` node.
- The 22 Wave-1 `test_query_scope.py` tests (11 behaviors x 2 backends) are GREEN, including `test_retracted_superseded_matrix`, `test_query_scope_excludes_superseded`, `test_event_range_boundary_inclusive`, and `test_empty_scope_returns_empty`.
- Full suite GREEN: 128 passed (was 106 passed + 22 RED). The Phase-3 keystone `test_invariants.py` + `test_revision_spine.py` stay green (the `_current` refactor is behaviour-preserving).
- basedpyright strict clean, ruff lint + format clean on `core.py`; the `include_deprecated` grep gate remains empty.

## Task Commits

Each task was committed atomically:

1. **Task 1: Factor `_current_tail` (status-agnostic); `_current` delegates to it** - `0f44698` (refactor)
2. **Task 2: Implement the `query_scope` body** - `3e42c35` (feat)

**Plan metadata:** see final docs commit.

## Files Created/Modified
- `src/doxastica/core.py` - Added `_current_tail` (status-agnostic ordering-max tail), refactored `_current` to delegate to it (retracted->None collapse on top), added the `query_scope` body, and added `BeliefFilter` to the runtime model import. No change to `_order_key`, `_hydrate`, `get_revision_chain`, or any write op.

## Decisions Made
- **`BeliefFilter` import landed in Task 2, not Task 1.** The plan's Task-1 action said to add `BeliefFilter` to the runtime model-import line in Task 1, but `BeliefFilter` is only referenced by the Task-2 `query_scope` signature. Adding it in Task 1 leaves an unused import that fails the Task-1 pre-commit gate (ruff `F401` + basedpyright strict `reportUnusedImport`). Since tasks commit atomically and pre-commit runs ruff + basedpyright on each commit, I moved the import into the Task-2 edit (the commit that first uses it). Net source state is identical to the plan; only the commit boundary differs. Tracked as a deviation below.
- **One ordering contract, three reuse sites.** `_current_tail`'s `max(..., key=_order_key)`, `query_scope`'s per-belief group-by max (`_order_key(row) > _order_key(current)`), and `query_scope`'s final `tails.sort(key=_order_key)` all reuse the single `_order_key` — no second ordering function anywhere (D-07).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `BeliefFilter` import moved from the Task-1 commit to the Task-2 commit**
- **Found during:** Task 1
- **Issue:** The plan instructed adding `BeliefFilter` to the runtime model import in Task 1, but it is first used only by the Task-2 `query_scope` signature. Committing Task 1 with the import present fails the per-commit pre-commit gate: ruff `F401 unused-import` and basedpyright strict `reportUnusedImport` (the same gate the plan's own Task-1 acceptance criterion — "basedpyright strict + ruff clean on core.py" — requires to pass).
- **Fix:** Reverted the import for the Task-1 commit; added it inside the Task-2 edit (the commit that first references it). The final source matches the plan exactly; only the commit at which the import appears changed.
- **Files modified:** src/doxastica/core.py
- **Verification:** ruff + basedpyright strict clean on `core.py` at BOTH commit boundaries; the import is used by `query_scope` after Task 2.
- **Committed in:** 3e42c35 (Task 2 commit)

**2. [Rule 1 - Bug] Two E501 (>100 char) step comments in `query_scope`**
- **Found during:** Task 2
- **Issue:** Two inline step comments (group-by and status-filter) were 101-102 chars; ruff (run by pre-commit on `src`) `E501` would block the Task-2 commit.
- **Fix:** Shortened both comments below 100 chars without changing meaning ("reuse _order_key" -> "reuse the key"; "matches hydrate" -> "like hydrate").
- **Files modified:** src/doxastica/core.py
- **Verification:** `ruff check` + `ruff format --check` clean; the 22 query_scope tests still GREEN after the comment edits.
- **Committed in:** 3e42c35 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both were necessary to satisfy the plan's own per-commit verification gate (ruff + basedpyright strict clean). No behavioural or scope change — the implemented logic is exactly the PATTERNS.md 8-step composition; net source matches the plan.

## Issues Encountered
None beyond the two auto-fixed gate items above. The 22 RED tests went GREEN on the first `query_scope` implementation; no logic iteration was needed.

## Known Stubs
None — `query_scope` is fully wired (no hardcoded empties, placeholders, or unwired data paths). It returns hydrated frozen `BeliefState` models from real backend reads.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- The observation surface HIST-01 + CHAIN-04 is complete and proven on both backends. The Phase-7 conformance suite and irony join can now read the belief base through `query_scope` (current cells) + `get_revision_chain` + `SUPERSEDES` (superseded cells).
- The event-range filter is deliberately a pure POST-filter (D-06); as-of/window reconstruction (`get_scope_at`, HIST-03) remains Phase 6. `add_edge`/`get_impact` (EDGE-01/02) remain Phase 5.
- No blockers.

## Self-Check: PASSED

- FOUND: src/doxastica/core.py (def query_scope, def _current_tail)
- FOUND commit: 0f44698 (Task 1 — _current_tail factor)
- FOUND commit: 3e42c35 (Task 2 — query_scope body)
- VERIFIED: full suite 128 passed; query_scope 22/22 GREEN both backends; basedpyright + ruff clean; include_deprecated grep gate empty

---
*Phase: 04-retrieval-observation-surface*
*Completed: 2026-06-18*
