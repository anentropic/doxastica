---
phase: 09-stance-value-layer-write-persistence
plan: 02
subsystem: testing
tags: [stance, agm, belief-revision, dual-backend, ladybug, in-memory, time-travel, pytest]

# Dependency graph
requires:
  - phase: 09-stance-value-layer-write-persistence (plan 01)
    provides: "Stance enum, required BeliefState.stance field, revise/expand/contract write-spine threading, ladybug name-token DDL, _hydrate Stance[name] name-lookup"
provides:
  - "Executable dual-backend proof that stance survives write -> persist -> read byte-stable (SC4/SC5)"
  - "Member-identity (is) regression guard against a value-vs-name hydrate bug (Pitfall 1 / T-09-02)"
  - "STANCE-03/04/05 requirement coverage: round-trip + optional default, contract-verbatim, get_scope_at reconstruction"
affects: [phase-10, stance-oracle-widening, STANCE-07, extensionality-property-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stance persistence proofs parametrized over the conftest memory + ladybug backend fixture"
    - "Member-identity (is) assertions on hydrated enums so a name-vs-value regression raises on read"

key-files:
  created:
    - "tests/test_stance_persistence.py - four parametrized parity tests (STANCE-03/04/05)"
  modified: []

key-decisions:
  - "Drove every assertion through MemoryCore(backend), not the bare BackendPort, so the serialize/hydrate discipline in core.py is what is proven"
  - "Member-identity (is) over ==: a value-vs-name hydrate regression raises on read rather than silently passing"
  - "No Hypothesis/oracle machinery — the K*6 Extensionality oracle widening is STANCE-07 (Phase 10), out of scope here"

patterns-established:
  - "Stance round-trip/preservation/reconstruction tests mirror the sibling value round-trip tests (test_revision_spine.py, test_backend_parity.py) with .value swapped for .stance"

requirements-completed: [STANCE-03, STANCE-04, STANCE-05]

# Metrics
duration: 8min
completed: 2026-07-04
---

# Phase 9 Plan 02: Stance Persistence Proof Summary

**Four dual-backend parity tests proving a written stance round-trips byte-stable through query_scope, defaults to certain when omitted, is copied verbatim by contract onto the retracted tail, and is reconstructed by get_scope_at — all via member-identity assertions on both the in-memory and ladybug backends.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-07-04
- **Completed:** 2026-07-04
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- STANCE-03 proven: a non-default `Stance.suspected` survives `revise -> query_scope` unchanged (member identity + `.name == "suspected"` wire token), and an omitted stance hydrates as `Stance.certain` — on both backends.
- STANCE-04 proven: `contract` copies the active state's stance verbatim onto the retracted tail (`retracted.stance is active.stance`, `retracted.status is Status.retracted`).
- STANCE-05 proven: `get_scope_at` reconstructs `Stance.suspected` via `_hydrate`'s name-lookup, with no dedicated production code.
- All four tests run once per backend (`memory` + `ladybug`) — 8 passing cases; the ladybug param is skipped, never failed, when the driver is absent.

## Task Commits

Each task was committed atomically:

1. **Task 1: Byte-stable round-trip + optional-default (STANCE-03)** - `1487c07` (test)
2. **Task 2: Contract-verbatim + get_scope_at reconstruction (STANCE-04/05)** - `a13c800` (test)

_Note: this is a test-only plan; production plumbing landed in 09-01, so both tasks are `test(...)` commits proving existing code rather than a RED->GREEN pair._

## Files Created/Modified
- `tests/test_stance_persistence.py` - Four parametrized parity tests (102 lines) asserting stance survives the full write -> persist -> read loop on both backends, driven through `MemoryCore(backend)` with member-identity (`is`) assertions.

## Decisions Made
- Assertions driven through `MemoryCore(backend)` (not the bare port) so the core's serialize (`_append` writes `stance.name`) / hydrate (`Stance[name]` name-lookup) discipline is what is under test.
- Member-identity (`is`) chosen over `==` so a value-vs-name hydrate regression (Pitfall 1 / T-09-02) surfaces as a read-time raise.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed three E501 line-length violations in the new test file**
- **Found during:** Task 2 (phase gate `prek run --all-files`)
- **Issue:** Three lines in `tests/test_stance_persistence.py` (a module-docstring line and two test-docstring/assert-message lines) exceeded the 100-char ruff limit, failing the CI-parity gate.
- **Fix:** Reworded the three lines to stay within 100 chars without changing test semantics.
- **Files modified:** tests/test_stance_persistence.py
- **Verification:** `prek run --all-files` green (ruff, ruff-format, basedpyright, blacken-docs all pass).
- **Committed in:** a13c800 (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking lint)
**Impact on plan:** Cosmetic line-length fix only; no scope creep, no semantic change.

## Issues Encountered
- `uv` commands panic (exit 101) under the command sandbox on this macOS host (known workaround: run outside the sandbox). Tests and the prek gate were run with the sandbox disabled; no effect on results.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 9's headline SC4/SC5 guarantee is now mechanically proven on both backends; the phase can exit with the full CI-parity suite green.
- Phase 10 (STANCE-07) can now widen the Hypothesis oracle / K*6 Extensionality on top of this proven persistence foundation.

## Self-Check: PASSED

- FOUND: tests/test_stance_persistence.py
- FOUND commit 1487c07 (Task 1)
- FOUND commit a13c800 (Task 2)

---
*Phase: 09-stance-value-layer-write-persistence*
*Completed: 2026-07-04*
