---
phase: 10-stance-formal-proof-docs
plan: 03
subsystem: testing
tags: [stance, hypothesis, pytest, parametrize, agm, belief-revision, ladybug, memory-backend]

# Dependency graph
requires:
  - phase: 09-stance
    provides: "BeliefState.stance field, name-token serialize/hydrate, contract verbatim-copy, revise/expand stance threading"
  - phase: 10-stance-formal-proof-docs (10-01)
    provides: "backend fixture params=[memory,ladybug] with importorskip SKIP-not-fail (conftest)"
provides:
  - "Stance-quantified persistence proofs: round-trip, contract-verbatim, get_scope_at over list(Stance) × backend"
  - "SC3 exhaustive quantification — every stance member proven on both backends (8 cases/property)"
affects: [10-04-docs, verification, code-review]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Exhaustive @pytest.mark.parametrize over tiny enum domains (list(Stance)) instead of Hypothesis sampling (D-05)"
    - "parametrize NOT @given on function-scoped-fixture tests (avoids function_scoped_fixture health check, RESEARCH Pitfall 2)"
    - "is-identity assertions against the true member so a name-vs-value hydrate regression raises loud (D-07)"

key-files:
  created: []
  modified:
    - "tests/test_stance_persistence.py"

key-decisions:
  - "Used exhaustive parametrize over list(Stance) (4 members) rather than @given(st.sampled_from) — a complete enumeration is a proof; sampling is an anecdote (D-05)"
  - "Kept the existing backbone verbatim: backend-parametrized fixture, is-identity, driven through MemoryCore(backend) not the bare port (D-07)"
  - "Kept test_stance_defaults_to_certain unparametrized — it proves the omitted default, orthogonal to member-quantification"

patterns-established:
  - "Pattern: tiny-domain exhaustive parametrize composes with the backend fixture → members × backends case matrix"
  - "Pattern: vacuous-pass detection proven by injecting a member-specific hydrate bug and confirming only that member's parametrization raises"

requirements-completed: [STANCE-07]

# Metrics
duration: 20min
completed: 2026-07-05
---

# Phase 10 Plan 03: Stance Persistence Quantification Summary

**Widened the three stance-persistence proofs (round-trip, contract-verbatim, get_scope_at) from one pinned witness each to exhaustive `@pytest.mark.parametrize("stance", list(Stance))` — every member proven byte-stable on both the memory and ladybug backends (24 cases, D-08/SC3).**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-05T00:28:00Z
- **Completed:** 2026-07-05T00:48:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- `test_stance_round_trips_byte_stable` now quantified over `list(Stance)` × `backend` — 8 cases (4 members × 2 backends), member-identity (`state.stance is stance`) retained.
- `test_contract_preserves_stance_verbatim` and `test_get_scope_at_reconstructs_stance` likewise quantified — 3 properties × exhaustive members, all `is`-identity assertions intact (D-07).
- Vacuous-pass detection (VALIDATION SC3) proven empirically: a `doubted`-only wrong-member hydrate bug makes exactly the 4 `doubted` parametrizations (round-trip + get_scope_at × 2 backends) RAISE while all 20 other cases pass — a single pinned witness would have missed it.
- Full CI-parity gate green: `uv sync --locked --dev --extra ladybug && prek run --all-files` passes; full suite `uv run pytest -q` = 573 passed, 1 xfailed, no skips (ladybug ran, not skipped).

## Task Commits

Each task was committed atomically:

1. **Task 1: Quantify round-trip over list(Stance) × backend (D-08)** - `fd2a195` (test)
2. **Task 2: Quantify contract-verbatim + get_scope_at over list(Stance) × backend (STANCE-04/05)** - `3b35c73` (test)
3. **Ruff E501 wrap of new comment/docstring lines** - `6730c73` (style)

**Plan metadata:** _(this commit)_ (docs: complete plan)

## Files Created/Modified
- `tests/test_stance_persistence.py` - Added `import pytest`; applied `@pytest.mark.parametrize("stance", list(Stance))` to the three persistence tests with a `stance: Stance` param; retained the `is`-identity assertions and the `MemoryCore(backend)` drive-through shape; left `test_stance_defaults_to_certain` unparametrized (orthogonal default proof).

## Decisions Made
- **Exhaustive parametrize over Hypothesis sampling (D-05):** the domain is 4 members — enumeration is a proof, not an anecdote. Also sidesteps the `function_scoped_fixture` health check that `@given` on the `backend` fixture would trip (RESEARCH Pitfall 2).
- **`is`-identity against the true member (D-07):** `assert state.stance is stance` (round-trip, get_scope_at) makes a name-vs-value hydrate regression raise loud rather than silently pass.
- **`contract` test asserts `retracted.stance is active.stance`** (per plan) — note this compares two values from the same hydrate path, so the SC3 vacuous-pass proof rests on the round-trip and get_scope_at tests (which compare hydrated output against the true `stance` member); those two catch the member-specific hydrate bug, confirmed empirically.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff E501 line-length on new comment/docstring lines**
- **Found during:** Phase verification (`prek run --all-files`)
- **Issue:** The added D-08 quantification comment blocks and the round-trip docstring exceeded the 100-char ruff limit (5 lines); the prek gate is a hard success criterion.
- **Fix:** Reflowed the comment blocks and shortened the docstring to ≤100 chars; no assertion or test-logic change.
- **Files modified:** tests/test_stance_persistence.py
- **Verification:** `prek run --all-files` green; test count and outcomes unchanged (26 in-file cases pass).
- **Committed in:** `6730c73` (separate style commit, cleanly isolated from the test logic)

---

**Total deviations:** 1 auto-fixed (1 blocking/style)
**Impact on plan:** Cosmetic line-wrap only to satisfy the prek gate; no behavioral or assertion change. No scope creep.

## Issues Encountered
- Initial acceptance-grep tripwire: my explanatory comment literally contained the token `@given`, making `grep -c "@given"` return 1 (criterion requires 0). Reworded the comment to "a Hypothesis `given` decorator" so the literal `@given` count is truly 0 while preserving the guidance. No `@given` decorator exists in the file.
- First vacuous-pass injection used `Stance(0)`, which correctly resolves to `Stance.doubted` (value 0) and was therefore not a real bug. Reworked the injection to return a wrong member (`Stance.certain`) for the `doubted` token; only the `doubted` parametrizations then raised, proving the exhaustive quantification catches a member-specific hydrate regression that a pinned witness would miss.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SC3 (stance persistence quantified) complete on both backends. Plan 10-04 (Cluedo tutorial + `Stance` export + docs strict build) is the remaining Wave-1 work.
- No `src/` change; the frozen Phase-9 core is unchanged.

---
*Phase: 10-stance-formal-proof-docs*
*Completed: 2026-07-05*

## Self-Check: PASSED
- FOUND: tests/test_stance_persistence.py
- FOUND: 10-03-SUMMARY.md
- FOUND commits: fd2a195, 3b35c73, 6730c73
