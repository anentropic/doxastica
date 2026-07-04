---
phase: 07-agm-hansson-conformance-suite
plan: 03
subsystem: testing
tags: [pytest, xfail, agm, recovery, belief-base, hansson, superseded-chain, dual-backend]

# Dependency graph
requires:
  - phase: 03-spine-and-invariants
    provides: "MemoryCore.in_memory(), revise/contract, _order_key ordering contract"
  - phase: 04-history-and-queries
    provides: "query_scope (observed belief base), get_revision_chain (append-only history)"
  - phase: 02-backend-port-and-fixtures
    provides: "conftest.py backend fixture (params=[memory, ladybug], importorskip skip-not-fail)"
provides:
  - "tests/test_recovery_xfail.py — the single deliberate AGM exclusion as a loud, named strict xfail"
  - "Recovery counterexample (re-assert-p-at-new-value base) reporting xfailed with a strict drift guard"
  - "D-05 superseded-chain replacement positives passing on both backends (BACK-05)"
affects: [verifier, ship, formal-conformance-suite, m0-exit-gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Strict-xfail-as-documented-negative-result: @pytest.mark.xfail(strict=True) on the mark itself (no global xfail_strict) so engine drift toward the excluded postulate XPASSes and reddens the suite"
    - "Recovery counterexample base: single belief re-asserted at a NEW value (revise->contract->revise) — avoids the naive {p,q} erroneous-XPASS trap"
    - "Recovery (postulate) kept lexically and behaviourally distinct from temporal history recoverability (no get_scope_at)"

key-files:
  created:
    - "tests/test_recovery_xfail.py"
  modified: []

key-decisions:
  - "Ratified the re-assert-p-at-new-value counterexample base (D-04/Open Q1): the superseded chain denies the closed-set Recovery conclusion, so the assertion genuinely FAILS -> xfailed GREEN, not an erroneous XPASS"
  - "strict=True placed on the mark itself (verified pyproject has only addopts='-v', NO global xfail_strict) — the drift guard would silently disarm otherwise (Pitfall 3)"
  - "Reworded docstrings to describe temporal recoverability without the bare token 'get_scope_at' so the literal acceptance check grep -c 'get_scope_at' == 0 holds while preserving the D-05 documented distinction"

patterns-established:
  - "Pattern 1: deterministic strict-xfail counterexample over MemoryCore.in_memory() (the AGM oracle) — a single negative result, not a Hypothesis sweep"
  - "Pattern 2: superseded-chain positives over the conftest backend fixture asserting active->retracted->active + current==v' + retained-retracted + base-not-restored"

requirements-completed: [FORMAL-04, BACK-05]

# Metrics
duration: 9min
completed: 2026-06-19
---

# Phase 7 Plan 03: Recovery Strict-Xfail & Superseded-Chain Positives Summary

**AGM Recovery encoded as a loud, named `xfail(strict=True)` counterexample reporting `xfailed` against the correct superseded-chain engine (drift-guard reddens on XPASS), plus the D-05 replacement positives passing on both backends.**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-06-19
- **Completed:** 2026-06-19
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- `test_recovery_does_not_hold_for_belief_bases`: a deterministic Recovery counterexample marked `@pytest.mark.xfail(strict=True, reason=...)`. It asserts the closed-set Recovery conclusion (`base == {"p": "v"}`) which the superseded chain correctly denies (`base == {"p": "vprime"}`), so it reports `xfailed`. The strict flag is the drift guard — if the engine ever satisfied Recovery it would XPASS and redden the suite.
- `test_superseded_chain_replaces_recovery(backend)`: the D-05 PASSING positives over the `conftest` `backend` fixture (both backends; ladybug skips when absent). Asserts the chain reads `["active","retracted","active"]`, current resolves to `vprime`, a retracted state is retained (append-only), and the observed base maps `p -> "vprime"` (old value not restored).
- Recovery (the postulate, excluded) kept distinct from temporal history recoverability — no `get_scope_at` call (literal count 0).

## Task Commits

Both tasks deliver a single new file (the file is the atomic artifact for both the xfail and the positives), committed together:

1. **Task 1 + Task 2: Recovery strict-xfail + superseded-chain positives** - `b9bee7e` (test)

**Plan metadata:** see final docs commit.

## Files Created/Modified
- `tests/test_recovery_xfail.py` - The strict-xfail Recovery counterexample (FORMAL-04, D-04) + the D-05 superseded-chain replacement positives over the dual-backend fixture (BACK-05).

## Decisions Made
- **Ratified counterexample base (D-04 / Open Q1):** used a single belief `p` re-asserted at a new value (`revise -> contract -> revise`) rather than the naive `{p, q}` base. With `{p,q}` the independent `q` survives contraction and the closed-set conclusion can XPASS erroneously (red against correct code); the re-assert base makes the superseded chain genuinely deny Recovery.
- **`strict=True` on the mark:** verified `pyproject.toml` has only `addopts = "-v"` and NO global `xfail_strict`, so the strict flag must live on the mark or the drift guard silently disarms.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking acceptance-criterion conflict] Reworded docstrings to remove the bare `get_scope_at` token**
- **Found during:** Task 2 (superseded-chain positives)
- **Issue:** The PATTERNS/action text says to "state the distinction from temporal recoverability in docstrings" naming `get_scope_at`, but the literal acceptance criterion requires `grep -c 'get_scope_at' == 0`. Initial docstrings named the symbol four times -> count was 4.
- **Fix:** Reworded the boundary notes to describe "as-of/time-travel scope reconstruction / revision-chain history replay" without the bare `get_scope_at` token. The documented D-05 distinction is preserved; no test ever called `get_scope_at()` (verified `grep '\bget_scope_at('` returns no calls).
- **Files modified:** tests/test_recovery_xfail.py
- **Verification:** `grep -c 'get_scope_at'` returns 0; full suite still xfailed+passed; ruff and basedpyright clean.
- **Committed in:** b9bee7e (Task commit)

---

**Total deviations:** 1 auto-fixed (1 blocking acceptance-criterion conflict)
**Impact on plan:** Cosmetic docstring wording only; semantics, behaviour, and the documented distinction unchanged. No scope creep.

## Issues Encountered
None — both tasks executed as planned; all acceptance criteria pass.

## Verification Evidence
- `uv run pytest tests/test_recovery_xfail.py -q -rxX` -> `2 passed, 1 xfailed` (exit 0); Recovery shows `x` (xfailed), NOT `X`/`failed`.
- `uv run --extra ladybug pytest tests/test_recovery_xfail.py -q -rxX` -> same result on both backends.
- `grep -nE 'xfail\(\s*strict=True' ...` -> mark present (line 44); `grep -c 'get_scope_at'` -> 0.
- `uv run ruff check ...` -> All checks passed; `uv run basedpyright ...` -> 0 errors, 0 warnings, 0 notes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- FORMAL-04 (Recovery strict xfail + superseded-chain positives) and BACK-05 (dual-backend parametrization, transversal) satisfied for this plan.
- Remaining Phase-7 plans (postulate/invariant suite extension, irony join) are unaffected by this additive test file.

## Self-Check: PASSED
- FOUND: tests/test_recovery_xfail.py
- FOUND: .planning/phases/07-agm-hansson-conformance-suite/07-03-SUMMARY.md
- FOUND: commit b9bee7e

---
*Phase: 07-agm-hansson-conformance-suite*
*Completed: 2026-06-19*
