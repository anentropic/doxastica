---
phase: 03-append-only-revision-spine-keystone
plan: 04
subsystem: testing
tags: [hypothesis, stateful-testing, agm, belief-revision, ladybug, invariants, property-testing]

# Dependency graph
requires:
  - phase: 03-02
    provides: "MemoryCore op bodies (revise/expand/contract/get_revision_chain), _current derived-current selection, _encode_value/_decode_value (base64-over-JSON) value boundary"
  - phase: 03-01
    provides: "WORLD_SCOPE_ID, HAS_REVISION ladybug REL table, the append-only schema"
provides:
  - "tests/test_invariants.py — the SC3/D-01 keystone consistency check: a Hypothesis RuleBasedStateMachine proving derived-current is total + single-valued + ≡ the HAS_REVISION chain tail, and that chains are immutable (monotonic BeliefState count), on BOTH backends against a shadow oracle"
  - "DEF-02-01 closed: the brace-shaped-value round-trip regression flipped from xfail to a passing core-routed assertion on both backends"
  - "A corrected _current that clears the derived current after a contraction (retracted ordering-max tail ⇒ None)"
affects: [phase-04-query-scope, phase-05-get-impact, phase-07-agm-conformance-suite]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hypothesis RuleBasedStateMachine + shadow-dict oracle for AGM-grade invariants (CLAUDE.md stateful pattern, first concrete use in the repo)"
    - "Per-example backend construction mirroring conftest (importorskip + bounded ladybug max_db_size to cap the per-DB mmap reservation under many examples)"
    - "Shadow oracle that models the (source_event_id, state_id) ordering contract — not naive last-write — so colliding/out-of-order source_event_ids are checked faithfully"

key-files:
  created:
    - tests/test_invariants.py
  modified:
    - tests/test_backend_parity.py
    - src/doxastica/core.py

key-decisions:
  - "Shadow oracle mirrors the ordering contract (ordering-max over (source_event_id, append_seq), None when the winner is retracted) rather than assuming linear causal order — required so out-of-order/colliding source_event_ids are modelled correctly (Pitfall 6)"
  - "DEF-02-01 flip routed through MemoryCore.revise + get_revision_chain (the core encode boundary) with a brace-shaped value {\"x\": 2}, not the bare port where ladybug still coerces"
  - "[Rule 1] _current selects the ordering-max over ALL statuses and returns None on a retracted tail, instead of pre-filtering to active — the only way a contracted belief correctly reports no derived current"
  - "Bounded ladybug Database(max_db_size=1 GiB) per example to prevent the default ~8 TiB mmap reservation exhausting process address space across dozens of Hypothesis examples"

patterns-established:
  - "Stateful consistency check: drive the public op surface, mirror into a shadow oracle, assert @invariants after every step — the template the Phase-7 AGM/Hansson suite will extend"
  - "Two machine subclasses (MemorySpineMachine / LadybugSpineMachine) each exposing .TestCase, with settings attached at module scope — the both-backends idiom for stateful tests"

requirements-completed: [CHAIN-02, CHAIN-03]

# Metrics
duration: 11min
completed: 2026-06-16
---

# Phase 3 Plan 4: Append-Only Revision Spine Keystone Consistency Check Summary

**Hypothesis stateful machine proving derived-current is total + single-valued + ≡ the HAS_REVISION chain tail and chains are immutable on both backends, plus the DEF-02-01 brace-value regression flipped to passing — and a real `_current` defect (contracted beliefs still reporting a current) caught and fixed by the new invariant.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-06-15T23:53:34Z
- **Completed:** 2026-06-16T00:05:33Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- `tests/test_invariants.py`: a `RuleBasedStateMachine` (`_SpineMachine`) driving `revise`/`expand`/`contract` against a shadow-dict oracle, with the keystone `@invariant` (derived-current total + single-valued + chain-tail equivalence, SC3/D-01) and the chain-immutability `@invariant` (monotonic `BeliefState` count, CHAIN-02), run on BOTH backends via `MemorySpineMachine`/`LadybugSpineMachine` (importorskip skips ladybug when absent).
- Colliding `source_event_id`s (drawn from a fixed 3-element UUID7 pool) exercise the `state_id` tiebreak (Pitfall 6); world-scope contraction is routed to its own raising assertion (`WorldScopeContractionError`).
- DEF-02-01 closed: `test_value_string_round_trips_ladybug` flipped from `xfail` to a passing assertion routed through `MemoryCore.revise` + `get_revision_chain` with a brace-shaped value; the memory sibling now proves the same closed regression through the core.
- Caught and fixed a real `_current` semantic defect: a contracted belief still reported its (never-mutated) active state as current. Full suite green on both jobs (105 passed, 0 xfail); ruff + basedpyright-strict clean.

## Task Commits

Each task was committed atomically:

1. **Task 1: Hypothesis stateful consistency check on both backends (+ Rule 1 `_current` fix)** - `aac2530` (test)
2. **Task 2: Flip the DEF-02-01 xfail to a passing core-routed regression** - `738e47a` (test)

## Files Created/Modified
- `tests/test_invariants.py` (created) - The SC3/D-01 keystone stateful consistency machine + shadow oracle; the two `@invariant`s; world-scope contraction routing; colliding-event tiebreak; both-backends `.TestCase` exposure.
- `tests/test_backend_parity.py` (modified) - DEF-02-01 regression flipped from `xfail` to a passing core-routed assertion (both backends); module docstring updated to "CLOSED".
- `src/doxastica/core.py` (modified) - `_current` now takes the ordering-max over all statuses and returns `None` on a retracted tail (the contraction-clears-current fix).

## Decisions Made
- The shadow oracle models the `(source_event_id, state_id)` ordering contract directly (max over `(source_event_id_str, append_seq)`, `None` when the winner is retracted) rather than assuming each write is the new current. This was necessary because the fixed event pool produces out-of-order/colliding `source_event_id`s, and under the documented ordering contract a contraction recorded against an *earlier* event legitimately does NOT clear a later assertion.
- The DEF-02-01 flip asserts through the core boundary (`revise`/`get_revision_chain`), not the bare port — the encoding contract lives in `core.py`, so that is where the regression is meaningful (PATTERNS Flag 3).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_current` did not clear the derived current after a contraction**
- **Found during:** Task 1 (the keystone consistency `@invariant` immediately falsified it)
- **Issue:** `_current` matched `status="active"` and then took the ordering-max. A `contract` appends a *retracted* copy but never mutates the prior active state (append-only), so `_current` kept returning the still-active state — a contracted belief incorrectly reported a current. This violates D-04 ("current = the state with no incoming SUPERSEDES = the ordering-max") and D-05 (a contraction clears the current). It was latent because no existing test asserted `_current is None` after a contraction; the new invariant is the first to do so.
- **Fix:** `_current` now matches ALL statuses, takes the ordering-max tail, and returns `None` when that tail is `retracted`. Correct under both the normal monotonic case (retracted tail wins ⇒ None) and the out-of-order case (an earlier-event retraction does not win ⇒ the assertion stays current).
- **Files modified:** `src/doxastica/core.py`
- **Verification:** All 22 `test_revision_spine.py` tests stay green; the keystone invariant passes on both backends; full suite 105 passed.
- **Committed in:** `aac2530` (Task 1 commit)

**2. [Rule 3 - Blocking] Ladybug per-example mmap exhaustion under Hypothesis**
- **Found during:** Task 1 (the `LadybugSpineMachine` failed with `FlakyStrategyDefinition` wrapping `RuntimeError: Buffer manager exception: Mmap for size 8796093022208 failed`)
- **Issue:** Each in-memory `lb.Database()` reserves ~8 TiB of virtual address space; the stateful machine creates one DB per Hypothesis example (~50), exhausting the process address space. The conftest fixture never hits this (one DB per test).
- **Fix:** Construct the per-example ladybug DB with `lb.Database(max_db_size=2**30)` (1 GiB cap) — a test-harness concern only; plus a `teardown()` that closes the owning backend each example.
- **Files modified:** `tests/test_invariants.py`
- **Verification:** `LadybugSpineMachine.TestCase` passes; both backends green.
- **Committed in:** `aac2530` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** The Rule 1 fix is the substantive correctness win — the keystone invariant did exactly its job, catching a derived-current defect that all prior tests missed. The Rule 3 fix is a test-harness robustness change. No scope creep; no public-surface change.

## Issues Encountered
- The first oracle draft used naive last-write semantics and was correctly falsified by out-of-order/colliding `source_event_id`s; rewriting it to model the ordering contract resolved this and made the colliding-event tiebreak (Pitfall 6) a genuine cross-check rather than an accident.

## Threat Flags

None. The plan's threat register (T-03-09 chain immutability, T-03-10 derived-current consistency + DEF-02-01 integrity) is now mechanically verified; no new security surface was introduced (test-only + a read-path correctness fix).

## Next Phase Readiness
- The spine keystone is proven: Phases 4 (`query_scope`), 5 (`add_edge`/`get_impact`), and 6 (`get_scope_at`) compose on a derived-current that is now consistency-verified on both backends.
- Note for Phase 4/7: the `_current` semantics are "ordering-max over all statuses, None if retracted" — query-current and the deprecated/superseded matrix should align with this (not the old active-filter behavior).
- The stateful-machine + shadow-oracle template is in place for the Phase-7 AGM/Hansson conformance suite to extend.

## Self-Check: PASSED

- `tests/test_invariants.py` — FOUND
- `.planning/phases/03-append-only-revision-spine-keystone/03-04-SUMMARY.md` — FOUND
- Commit `aac2530` — FOUND
- Commit `738e47a` — FOUND

---
*Phase: 03-append-only-revision-spine-keystone*
*Completed: 2026-06-16*
