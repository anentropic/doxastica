---
phase: 03-append-only-revision-spine-keystone
plan: 03
subsystem: testing
tags: [pytest, hypothesis-adjacent, parametrized-fixture, agm, belief-revision, ladybug, in-memory-oracle, nyquist-scaffold]

# Dependency graph
requires:
  - phase: 03-append-only-revision-spine-keystone (plan 03-01)
    provides: WORLD_SCOPE_ID constant + HAS_REVISION hub-edge schema decision; barrel re-export
  - phase: 01-foundation
    provides: BeliefStore Protocol signatures (protocol.py), WorldScopeContractionError (errors.py), closed model taxonomy (models.py)
  - phase: 02
    provides: parametrized `backend` fixture (conftest.py), MemoryCore constructor + factories, both backends behind BackendPort, test_backend_parity.py analog
provides:
  - tests/test_revision_spine.py — the Wave-0 behavior-test scaffold (Nyquist sampling target for plan 03-02)
  - one named test per Phase-3 behavior requirement (SCOPE-01/02/03, CHAIN-01, OPS-01/02/03, HIST-02) over BOTH backends
  - three integrity regressions: DEF-02-01 brace round-trip, Pitfall 2 retracted byte-identity, Pitfall 4 is_world bool
affects: [03-02 (op-body implementation — its verify commands target this file), 03-04 (Hypothesis stateful + xfail flip)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Behavior tests construct MemoryCore(backend) over the injected parametrized fixture port (NOT the in-memory factory) so the op bodies run on BOTH the memory oracle and the ladybug backend"
    - "Meaningful-RED Nyquist scaffold: tests written against the LOCKED public surface BEFORE the implementation they verify; expected to error (AttributeError) until 03-02 lands"
    - "uuid.uuid7() helper mints caller-side source_event_ids; a colliding pair exercises the (source_event_id, state_id) tiebreak (Pitfall 6)"

key-files:
  created:
    - tests/test_revision_spine.py
  modified: []

key-decisions:
  - "Constructed MemoryCore(backend) directly from the fixture port (the one deliberate deviation from the bare-port parity tests) so the parametrized ladybug backend is actually exercised by the spine behaviors"
  - "Verify command is collect-only (tests must COLLECT cleanly, not pass): the scaffold is correctly RED until plan 03-02 fills the op bodies"
  - "Reworded the module docstring to avoid the literal token `MemoryCore.in_memory()` so the acceptance grep (never the in-memory factory) is satisfied while still documenting the deviation"

patterns-established:
  - "Nyquist behavior scaffold: one test per requirement, parametrized over both backends, authored before the implementation"
  - "Integrity-regression-as-behavior-test: DEF-02-01 / Pitfall-2 / Pitfall-4 asserted THROUGH the core (revise + get_revision_chain), where the value-encoding contract applies"

requirements-completed: [SCOPE-01, SCOPE-02, SCOPE-03, CHAIN-01, OPS-01, OPS-02, OPS-03, HIST-02]

# Metrics
duration: 2min
completed: 2026-06-15
---

# Phase 3 Plan 03: Wave-0 Revision-Spine Behavior Scaffold Summary

**tests/test_revision_spine.py — 11 behavior tests (22 collected over the memory + ladybug fixture) covering SCOPE-01/02/03, CHAIN-01, OPS-01/02/03, HIST-02 plus the DEF-02-01 brace round-trip, Pitfall-2 retracted byte-identity, and Pitfall-4 is_world bool, all constructed over MemoryCore(backend) and meaningfully RED until 03-02 fills the op bodies.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-15T23:39:01Z
- **Completed:** 2026-06-15T23:41:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Authored the Wave-0 Nyquist scaffold `tests/test_revision_spine.py`: one named test per Phase-3 behavior requirement, each parametrized over both backends (22 tests collected).
- Wrote the three integrity regressions (DEF-02-01 brace round-trip, Pitfall 2 retracted-equals-superseded byte-identity, Pitfall 4 world-scope `is_world` as a real `bool`) — asserted THROUGH the core surface where the value-encoding contract applies.
- Confirmed the scaffold is meaningful RED: it collects cleanly (exit 0) and errors at run time with `AttributeError` because the `MemoryCore` op bodies do not exist yet — exactly the intended state for plan 03-02 to target.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write tests/test_revision_spine.py over both backends (the Nyquist scaffold)** - `90160fa` (test)

**Plan metadata:** committed with this SUMMARY (docs: complete plan)

## Files Created/Modified
- `tests/test_revision_spine.py` - The Wave-0 behavior-test scaffold: 11 tests (SCOPE-01/02/03, CHAIN-01, OPS-01/02/03, HIST-02 + 3 integrity regressions) parametrized over the `backend` fixture, constructing `MemoryCore(backend)` from the injected port.

## Decisions Made
- **Construct `MemoryCore(backend)` from the fixture port, not the in-memory factory** — the one deliberate deviation from `test_backend_parity.py` (which tests the bare port). The spine behaviors live on the core's op bodies, so the core must compose the *parametrized* port for the ladybug backend to be exercised. Confirmed `grep -c 'MemoryCore(backend)'` = 12 and zero references to the in-memory factory literal.
- **Verify is collect-only** — per the plan's acceptance criteria and the context note, the tests must COLLECT cleanly (well-formed, importable), not pass. They are correctly RED until 03-02.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ruff E501 (line too long) on the DEF-02-01 test docstring**
- **Found during:** Task 1 (acceptance-criteria lint check)
- **Issue:** The brace-round-trip test docstring was 106 chars (> 100), failing `ruff check` — an acceptance criterion.
- **Fix:** Shortened the docstring to fit the 100-char limit without losing the DEF-02-01 reference.
- **Files modified:** tests/test_revision_spine.py
- **Verification:** `UV_NO_SYNC=1 uv run ruff check tests/test_revision_spine.py` → "All checks passed!"
- **Committed in:** 90160fa (Task 1 commit)

**2. [Rule 3 - Blocking] Module docstring contained the literal `MemoryCore.in_memory()` token**
- **Found during:** Task 1 (acceptance-criteria grep)
- **Issue:** The acceptance criterion requires the file to *never* reference `MemoryCore.in_memory()`; the explanatory docstring mentioned the literal token ("NOT `MemoryCore.in_memory()`"), so `grep -c 'MemoryCore.in_memory'` returned 1 instead of 0.
- **Fix:** Reworded the docstring to say "the zero-dependency in-memory factory classmethod" — preserving the documented rationale for the deviation while removing the literal token.
- **Files modified:** tests/test_revision_spine.py
- **Verification:** `grep -c 'MemoryCore.in_memory' tests/test_revision_spine.py` → 0; collection still 22 tests.
- **Committed in:** 90160fa (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking lint/acceptance-criteria issues in my own new file)
**Impact on plan:** Both fixes were required to satisfy the plan's own acceptance criteria (ruff-clean + grep gate). No scope creep — no production code touched, no tests weakened.

## Issues Encountered
None - the scaffold collected and ran exactly as expected. The 22 RED failures at run time are intentional (op bodies absent until 03-02), not a problem to solve.

## Threat Surface
Per the plan threat model, this plan AUTHORS the regression tests that prove two integrity controls (it does not implement them — those land in 03-02):
- **T-03-07 (Tampering — value-encoding integrity):** `test_brace_value_round_trips` + `test_retracted_value_byte_identical_to_superseded` pin the DEF-02-01 brace round-trip and the no-double-encode invariant.
- **T-03-08 (Information disclosure — negative test):** `test_world_contract_raises` asserts the world-scope guard refuses contraction AND that no write leaked through before the raise (D-03), via a post-raise empty-chain assertion.

No new security surface introduced (test-only change; no installs — pytest already in the dev group).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The Nyquist sampling target is in place: plan 03-02 can now fill the `MemoryCore` op bodies (`get_or_create_scope`, `revise`/`expand`, `contract`, `_current`/`_append`/`_hydrate`/`_ensure_scope`, `get_revision_chain`) and verify against this file flipping RED → GREEN on both backends.
- Plan 03-04 (Hypothesis stateful consistency machine + DEF-02-01 xfail flip) is unblocked by this scaffold's both-backends idiom.
- No blockers.

## Self-Check: PASSED

- FOUND: tests/test_revision_spine.py
- FOUND: .planning/phases/03-append-only-revision-spine-keystone/03-03-SUMMARY.md
- FOUND: commit 90160fa (task 1)

---
*Phase: 03-append-only-revision-spine-keystone*
*Completed: 2026-06-15*
