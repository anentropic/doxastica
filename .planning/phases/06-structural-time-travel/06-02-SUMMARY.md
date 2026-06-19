---
phase: 06-structural-time-travel
plan: 02
subsystem: tests
tags: [time-travel, get_scope_at, operational-fold, oracle, hypothesis, stateful, agm, event-sourcing]

# Dependency graph
requires:
  - phase: 06-structural-time-travel
    plan: 01
    provides: "MemoryCore.get_scope_at body + tests/test_scope_at.py example-test preamble (_event_id/_core/_ids)"
  - phase: 03-revision-spine
    provides: "_order_key (the ONE (source_event_id, state_id) ordering contract the oracle mirrors), revise/expand/contract write spine"
provides:
  - "tests/test_scope_at.py operational-fold half — the fold(scope, as_of) pure-Python oracle, the _ScopeAtMachine RuleBasedStateMachine, the get_scope_at==fold @invariant, and two .TestCase subclasses (memory + ladybug)"
  - "The D-07 SPEC proven under Hypothesis on BOTH backends: SC1 (max-cut equivalence with query_scope), SC2 (cut stepped across the pool), SC3 (colliding/out-of-order source_event_ids)"
affects: [07-conformance-suite, nvm-cqrs-replay]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "independent operational-fold oracle: replays the recorded op-log with its OWN (source_event_id_str, append_seq) winner selection, NEVER calling get_scope_at/_current_tail/_current — the anti-tautology cross-check (Pitfall 6)"
    - "fixed 3-id UUID7 event pool forcing intra-ms collisions + out-of-order reuse (SC3) so the (source_event_id, append_seq) tiebreak is actually exercised"
    - "@invariant stepping the cut across (every pooled id + a maximal sentinel) — SC1 falls out at the maximal cut, SC2 is the stepping itself"

key-files:
  created: []
  modified:
    - tests/test_scope_at.py

key-decisions:
  - "The fold oracle drops a belief whose winning op is a contract by op_kind='contract' (not a copied retracted value) — the op-log carries op_kind so the retracted-as-of collapse (D-06) is decided by the SAME (source_event_id, append_seq) ordering the core uses, never assumed"
  - "contract @precondition gates on _active_keys() computed via fold(scope, MAX_CUT) — the oracle's own 'now' derivation, keeping the gate independent of the production surface (no _current call to pick a contract target)"
  - "Maximal sentinel cut = UUID('ffffffff-...') (UUID7 canonical max string) so the str-vs-str inclusive cut admits every pooled op; this is the SC1 case agreeing with query_scope's now"

patterns-established:
  - "operational-fold equivalence proof: drive the real ops, mirror each into an independent op-log, fold the LOG (not materialized states) up to a cut, assert get_scope_at(scope, cut) == fold(scope, cut) at every cut — both backends, via two .TestCase subclasses"

requirements-completed: [HIST-03]

# Metrics
duration: 4min
completed: 2026-06-19
---

# Phase 6 Plan 02: Operational-Fold Oracle Summary

**A pure-Python operational-fold oracle replays the recorded `revise`/`expand`/`contract` op-log independently and a Hypothesis `RuleBasedStateMachine` proves `get_scope_at(scope, cut) == fold(scope, cut)` at every cut on BOTH backends — the D-07 SPEC where SC1/SC2/SC3 all collapse into one property, with the oracle's own `(source_event_id, append_seq)` winner selection making it a real cross-check rather than a tautology.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-19T07:23:51Z
- **Completed:** 2026-06-19T07:28:00Z
- **Tasks:** 1
- **Files modified:** 1 (tests/test_scope_at.py — extended)

## Accomplishments
- Added the operational-fold half to `tests/test_scope_at.py` (Half B), extending the 06-01 example-test preamble without redefining `_event_id`/`_core`/`_ids`.
- Built `fold(scope_id, as_of)` — a PURE-PYTHON operational fold over the recorded op-log: keep ops with `source_event_id_str <= as_of` (the SAME inclusive str-vs-str cut), per `(scope, belief)` take the winner by `(source_event_id_str, append_seq)` (mirrors `_order_key`), and DROP a belief whose winning op is a `contract` (retracted-as-of, D-06). It NEVER calls `get_scope_at`/`_current_tail`/`_current` — the anti-tautology requirement (verified by inspection).
- Built `_ScopeAtMachine(RuleBasedStateMachine)` mirroring `tests/test_invariants.py`'s `_SpineMachine` idiom: `_make_backend` (bounded `lb.Database(max_db_size=2**30)` + `importorskip` for ladybug, `InMemoryBackend` for memory), `@initialize` op-log + `_seq`, `_record` (carries `op_kind`), `revise`/`expand`/`contract` `@rule`s (contract `@precondition`-gated on `_active_keys()`), the `scope_at_equals_fold_for_every_cut` `@invariant`, and `teardown`.
- SC3 is exercised by a fixed `_EVENT_POOL = tuple(uuid.uuid7() for _ in range(3))` — intra-ms collisions + out-of-order reuse force the `(source_event_id, append_seq)` tiebreak; SC2 is the cut stepped across `(*_EVENT_POOL, _MAX_CUT)`; SC1 is the maximal-cut case agreeing with `query_scope`'s "now".
- Two auto-collected `.TestCase`s (`MemoryScopeAtFoldMachine` / `LadybugScopeAtFoldMachine`) bounded `max_examples=50, stateful_step_count=20, deadline=None`, named so `-k Fold` selects exactly this property.
- Full suite green: 184 passed (up from 182 — the two new fold TestCases). `test_invariants`, `test_query_scope`, `test_revision_spine`, `test_import_purity` unchanged and green. basedpyright strict + ruff clean.

## Task Commits

1. **Task 1: Operational-fold oracle + Hypothesis stateful property (get_scope_at == fold, both backends)** — `c752673` (test)

_This is a test-only plan (no production `<files>`): `get_scope_at` already landed in 06-01, so the property passed immediately on first write — the GREEN signal IS the D-07 equivalence holding. A single `test(...)` commit captures it; no separate RED/feat split applies because there is no new production code._

## Files Created/Modified
- `tests/test_scope_at.py` — EXTENDED with Half B (the operational-fold property). Added: the Hypothesis imports; `_EVENT_POOL`/`_MAX_CUT`/`_SCOPE_POOL`/`_BELIEF_POOL`/`_values`/sampled strategies; `_ScopeAtMachine` (the `Entry` op-log type, `_make_backend`, `_setup`, `_record`, the independent `fold` oracle, `add_scope`/`add_belief` feeders, `revise`/`expand`/`contract` rules, `_active_keys`, the `scope_at_equals_fold_for_every_cut` invariant, `teardown`); `_SETTINGS`; the two `.TestCase` subclasses + `# pyright: ignore` re-exports.

## Decisions Made
- **`op_kind` carried in the op-log over a copied retracted value:** the `_record` entry stores `(source_event_id_str, append_seq, value, op_kind)` and `fold` drops the belief when the winning op's `op_kind == "contract"`. This decides the retracted-as-of collapse (D-06) by the SAME `(source_event_id, append_seq)` ordering the core's `_order_key` uses, never by assumption — a contraction recorded against an earlier event than a later assertion correctly does NOT win the cut.
- **`contract` precondition uses `fold(scope, MAX_CUT)`:** the gate's `_active_keys()` derives "currently active" from the oracle's OWN maximal-cut fold, not from `core._current` — keeping even the rule-gating independent of the production reconstruction surface (the anti-tautology discipline extends to choosing a contract target).
- **Maximal sentinel `_MAX_CUT = UUID('ffffffff-...')`:** the canonical UUID7 max string, so the inclusive str-vs-str cut admits every pooled op and the maximal-cut invariant check IS the SC1 equivalence with `query_scope`'s "now".

## Deviations from Plan
None — plan executed exactly as written. The independent-fold oracle, the fixed collision pool, the cut-stepping invariant, and the two-backend `.TestCase` idiom all landed per the `<behavior>`/`<action>` spec. No auto-fix (Rule 1-3) or architectural decision (Rule 4) was triggered. The plan's `tdd="true"` collapses to a single `test(...)` commit because the task adds no production code (the body shipped in 06-01); this is the expected shape for a pure-oracle/property plan, not a deviation.

## Issues Encountered
- **Ruff E501 on five docstring/comment lines** (102/101 > 100): wrapped the anti-tautology comment block and the `fold` docstring until `ruff check` passed clean. Comment/docstring-only — re-ran `-k Fold` after wrapping to confirm still green (2 passed). No behaviour change.

## Anti-Tautology Verification (the whole point of D-07)
Confirmed by inspection: `fold` folds the recorded OP-LOG (`self.entries`) with its own `max(..., key=lambda e: (e[0], e[1]))` winner selection and an `op_kind`-based retracted drop. It calls NO production reconstruction helper (`get_scope_at`, `_current_tail`, `_current`, `_order_key`, `match_nodes`, `get_revision_chain`). The equivalence asserted by `scope_at_equals_fold_for_every_cut` is therefore a genuine cross-check between two independent implementations (event-log fold vs. materialized-state fold), not a restatement.

## User Setup Required
None — no external service configuration required. `hypothesis` + `pytest` were already in the dev group; no new dependency was added.

## Next Phase Readiness
- The D-07 SPEC holds on both backends; HIST-03 is now proven by both the 06-01 example tests AND the 06-02 operational-fold property. SC1/SC2/SC3 are all green.
- No production code was added this plan — `core.py` is unchanged and stays driver-blind (`test_import_purity` green). No blockers.
- The pre-existing `core.py:68` `ruff format` nit (logged to `deferred-items.md` in 06-01) remains the only deferred item and is non-blocking.

## Self-Check: PASSED

- FOUND: `tests/test_scope_at.py` (contains `class _ScopeAtMachine`, `def fold`, `MemoryScopeAtFoldMachine`, `LadybugScopeAtFoldMachine`)
- FOUND: `.planning/phases/06-structural-time-travel/06-02-SUMMARY.md`
- FOUND commit `c752673` (test, Task 1)

---
*Phase: 06-structural-time-travel*
*Completed: 2026-06-19*
