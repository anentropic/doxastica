---
phase: 10-stance-formal-proof-docs
plan: 01
subsystem: testing
tags: [hypothesis, stateful-testing, agm, stance, property-tests, basedpyright]

# Dependency graph
requires:
  - phase: 09-stance-persistence
    provides: Stance ordinal taxonomy, revise/expand stance params, verbatim-copy contract (STANCE-04)
  - phase: 03-append-only-revision-spine-keystone
    provides: _SpineMachine stateful oracle + keystone derived-current invariant
  - phase: 07-agm-hansson-conformance-suite
    provides: dual-backend @given AGM postulate tests (_base_of, K*4/K*6)
provides:
  - Stance-carrying stateful shadow oracle (Entry 5-tuple, {belief_id: (value, stance)} base key)
  - Deterministic non-vacuity proof test_widened_key_discriminates_stance (both backends)
  - hypothesis.event() stance-flip observability label on the stateful revise/expand rules
  - K*6 Extensionality parity now compares stance, not only value
affects: [stance formal proof, agm conformance, phase-10 remaining plans]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Widened base key {belief_id: (value, stance)} routed through a SINGLE _base_of projection so a value-only revert genuinely breaks the discrimination proof (VALIDATION SC1 vacuous-pass detection)"
    - "hypothesis.event() coverage label proving a discriminating path is actually generated, distinct from the deterministic guard"

key-files:
  created: []
  modified:
    - tests/test_invariants.py

key-decisions:
  - "The deterministic _base_of / K*6 guard and the stateful-oracle event() guard are kept as two DISTINCT surfaces, not conflated"
  - "Discrimination flows through the real widened _base_of (never an inline dict literal) so reverting the widening collapses a != b"

patterns-established:
  - "Non-vacuity proof: prove the guard guards by demonstrating the assertion fails when the widening is reverted"
  - "event() stance-flip label surfaces in --hypothesis-show-statistics to document the stateful discriminating path is exercised"

requirements-completed: [STANCE-07]

# Metrics
duration: 35min
completed: 2026-07-05
---

# Phase 10 Plan 01: Stance Formal-Proof Widening Summary

**The dual-backend AGM property suite now carries `stance` per belief-in-scope, with a deterministic non-vacuity proof and a `hypothesis.event()` flip label that make the stance widening mechanically proven rather than vacuously green.**

## Performance

- **Duration:** ~35 min (Task 2 completion of an interrupted session; Task 1 pre-committed)
- **Completed:** 2026-07-05
- **Tasks:** 2 (Task 1 pre-committed by prior executor; Task 2 completed this session)
- **Files modified:** 1

## Accomplishments
- Completed Task 2: the deterministic `test_widened_key_discriminates_stance` proof, parametrized over both backends, routing both scopes through the actual widened `_base_of` so a value-only revert collapses `a != b`.
- Emitted `event("write flips the current stance of an existing belief")` in the stateful `revise`/`expand` rules (computed BEFORE mirroring) — the stateful-oracle observability guard, distinct from the deterministic `_base_of` guard.
- Updated `test_extensionality_k6` to draw a `stance` and compare the `(value, stance)` base, proving `revise ≡ expand` agrees on stance too.
- Adjusted `test_vacuity_k4` and `test_uniformity` base expectations to the widened `(value, stance)` shape (default stance `certain`).
- **Verified the vacuous-pass detection manually:** temporarily reverting `_base_of` to `{belief_id: value}` made `test_widened_key_discriminates_stance` FAIL on both backends (`assert {'b1': 'v'} != {'b1': 'v'}`), then restored the widening. The guard is genuinely non-vacuous (VALIDATION SC1).

## Task Commits

1. **Task 1: Widen the stateful oracle to carry the Stance member** - `5d1bfa6` (test) — pre-committed by the prior (interrupted) executor; verified intact this session.
2. **Task 2: Prove the widening is non-vacuous (D-03)** - `4e3af13` (test)

## Files Created/Modified
- `tests/test_invariants.py` - Added `test_widened_key_discriminates_stance`; stance-flip `event()` in `revise`/`expand`; K*6 stance parity; widened `_base_of` expectations in `test_vacuity_k4`/`test_uniformity`.

## Decisions Made
- Kept the deterministic `_base_of`/K*6 guard and the stateful-oracle `event()` guard as two distinct surfaces (per plan D-03) — the deterministic test guards the standalone path; the `event()` label documents the stateful path.
- Routed both scopes in the discrimination proof through the real widened `_base_of` rather than an inline literal, so the revert genuinely breaks the test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_uniformity` value-only base literal broke under the widened `_base_of`**
- **Found during:** Task 2 (making the full file green)
- **Issue:** The already-widened `_base_of` (uncommitted from the interrupted session) made `test_uniformity`'s `assert base_after_first == {"q": "kept"}` false — the projection now returns `(value, stance)` tuples. The plan's Task 2 action listed `test_vacuity_k4` but not `test_uniformity`, which shares the same helper.
- **Fix:** Updated the literal to `{"q": ("kept", Stance.certain)}` (default stance).
- **Files modified:** tests/test_invariants.py
- **Verification:** `uv run pytest tests/test_invariants.py -q` → 10 passed.
- **Committed in:** 4e3af13 (Task 2 commit)

**2. [Rule 3 - Blocking] E501 line-length + D205 docstring-summary violations under the prek gate**
- **Found during:** Task 2 (CI-parity prek run)
- **Issue:** New and pre-existing (Task 1) docstring/comment prose exceeded 100 cols (ruff E501); wrapping a docstring summary onto two lines then tripped D205. ruff-format does not reflow prose.
- **Fix:** Manually reflowed the flagged comments/docstrings and shortened two docstring summary lines to single physical lines.
- **Files modified:** tests/test_invariants.py
- **Verification:** `uv run ruff check` → all checks passed; full `prek run --all-files` green.
- **Committed in:** 4e3af13 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both required to satisfy the CI-parity prek gate and keep the full file green. No scope creep — test-only changes, no `src/` edits.

## Issues Encountered
- The prek run surfaced E501 violations on Task-1 lines as well as Task-2 lines (the phase-gate prek is deferred until all Wave-1 plans land, so Task 1's `--no-verify` worktree commit was not prek-clean). All were reflowed as part of making this plan's file green.

## Verification Results
- `uv run pytest tests/test_invariants.py -q` → 10 passed (both backends; ladybug present, no skips).
- `uv run pytest tests/test_invariants.py::test_widened_key_discriminates_stance -q` → 2 passed (memory + ladybug).
- `event("write flips the current stance of an existing belief")` appears in `--hypothesis-show-statistics` (~10-40% of the stateful run).
- Vacuous-pass detection CONFIRMED: reverting `_base_of` to value-only makes the discrimination test FAIL, then restored.
- CI-parity gate `uv sync --locked --dev --extra ladybug && prek run --all-files` → green (ruff, ruff-format, uv-lock, basedpyright-strict, blacken-docs all pass).

## Next Phase Readiness
- SC1 (stance widening non-vacuity) is proven. The remaining Phase-10 plans (order-law suite, tutorial/docs) can proceed.

## Self-Check: PASSED
- `tests/test_invariants.py` present and modified.
- Task commits `5d1bfa6` (Task 1) and `4e3af13` (Task 2) both in the git log.
- `test_widened_key_discriminates_stance` present (2 grep hits: def + docstring ref).

---
*Phase: 10-stance-formal-proof-docs*
*Completed: 2026-07-05*
