---
phase: 01-protocol-backend-port-data-model-decisions
plan: 02
subsystem: database
tags: [pydantic, frozen-models, enum, agm, belief-revision, data-model]

# Dependency graph
requires:
  - phase: 01-01
    provides: cookiecutter scaffold, pinned ladybug+pydantic deps, hypothesis dev dep, src/doxastica package
provides:
  - "Frozen pydantic v2 value layer: Scope, Belief, BeliefState, BeliefFilter, ImpactResult"
  - "Closed taxonomy enums: Status (active, retracted), EdgeType (SUPERSEDES, DEPENDS_ON, DERIVED_FROM)"
  - "Typed exception surface: DoxasticaError base + WorldScopeContractionError"
  - "DATA-05/DATA-06 guard test suite (frozen-ness + closed field/enum sets)"
affects: [protocol-plan-03, backend-port-plan-04, phase-2-ladybug-spike, phase-3-core-operations, phase-7-conformance-suite]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pydantic v2 frozen=True class-kwarg models (immutable + hashable value objects)"
    - "Closed enum.StrEnum taxonomy as single source of truth"
    - "Closed typed filter (BeliefFilter) instead of free-str query — injection mitigation by construction"
    - "Never-under-report return shape (ImpactResult.frontier + truncated)"

key-files:
  created:
    - src/doxastica/models.py
    - src/doxastica/errors.py
    - tests/test_models_frozen.py
  modified: []

key-decisions:
  - "EdgeType excludes structural HAS_REVISION/CURRENT_STATE (Open Q1 resolved: separate structural constants)"
  - "Status is exactly {active, retracted}; invalidated/under_revision rejected as NVM extensions (DATA-06)"
  - "BeliefState carries the closed six-field set only — no provenance/temporal/epistemic fields (DATA-05)"
  - "Used enum.StrEnum instead of (str, Enum) to satisfy ruff UP042 on py3.14 — behaviorally equivalent"

patterns-established:
  - "pydantic v2 frozen-model convention: class X(BaseModel, frozen=True)"
  - "D213 docstring convention (summary on second line) per template ruff config"
  - "Test style: module docstring, top-level def test_*(), bare assert, no classes, no DB fixtures"

requirements-completed: [DATA-02, DATA-04, DATA-05, DATA-06]

# Metrics
duration: 12min
completed: 2026-06-14
---

# Phase 1 Plan 02: Frozen Data-Model Taxonomy Summary

**Frozen pydantic v2 value layer encoding the closed core taxonomy — Status/EdgeType enums, the six-field BeliefState, the closed BeliefFilter (DATA-02), the never-under-reporting ImpactResult (DATA-04), and the typed exception surface — mechanically guarded by a frozen-ness/closed-set test suite.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-14T19:20:00Z
- **Completed:** 2026-06-14T19:32:46Z
- **Tasks:** 2
- **Files modified:** 3 (all created)

## Accomplishments
- Authored `src/doxastica/models.py`: 5 frozen pydantic models + 2 closed StrEnum taxonomies, all type-checking strict under basedpyright and ruff-clean.
- Authored `src/doxastica/errors.py`: `DoxasticaError` base + `WorldScopeContractionError` (types the Phase-3 enforcement surface).
- Authored `tests/test_models_frozen.py`: 8 passing guard tests proving frozen-ness, exact enum membership, structural-edge exclusion, and the closed field sets for `BeliefState` (6) and `BeliefFilter` (4).

## Task Commits

Each task was committed atomically:

1. **Task 1: Author the frozen pydantic model taxonomy and exceptions** - `a4eac63` (feat)
2. **Task 2: Author the frozen-ness / closed-taxonomy guard tests** - `941493c` (test)

_Note: this `type: tdd` plan ordered implementation (Task 1) before tests (Task 2) per the plan's explicit task sequence. The GREEN gate is satisfied: the Task-2 test commit's suite passes against the Task-1 implementation._

## Files Created/Modified
- `src/doxastica/models.py` - Frozen pydantic v2 value layer: `Status`/`EdgeType` enums, `Scope`, `Belief`, `BeliefState`, `BeliefFilter`, `ImpactResult`.
- `src/doxastica/errors.py` - `DoxasticaError` base and `WorldScopeContractionError`.
- `tests/test_models_frozen.py` - DATA-05/DATA-06 guards: frozen mutation raises, exact enum membership, closed field sets, `ImpactResult` constructibility.

## Decisions Made
- **EdgeType excludes structural edges:** `HAS_REVISION`/`CURRENT_STATE` kept out of the enum (Open Q1, planner's-discretion resolution per RESEARCH.md) so `add_edge` cannot accept a structural edge. Asserted negatively in the test suite.
- **StrEnum over `(str, Enum)`:** the plan/research wrote `class Status(str, Enum)`, but ruff's `UP042` (selected `UP` ruleset) flags mixed `str`+`Enum` inheritance on py3.14 and recommends `enum.StrEnum`. `StrEnum` is behaviorally equivalent (members are `str` subclass instances; `Status.active == "active"`), and the guard tests assert membership, not the base class. Adopted `StrEnum` to keep the lint gate green.
- **D213 docstring format:** template ruff config ignores `D212` and selects `D213`, requiring multi-line docstring summaries to begin on the second line; all module/class docstrings follow this.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adjusted enum base to `enum.StrEnum`**
- **Found during:** Task 1 (model authoring)
- **Issue:** `class Status(str, Enum)` / `class EdgeType(str, Enum)` (as written verbatim in the plan and RESEARCH.md) trip ruff `UP042` on the py3.14 target, blocking the lint acceptance gate.
- **Fix:** Switched both enums to `class X(StrEnum)`. Behaviorally equivalent — members remain `str`-comparable; the closed-membership and value semantics the tests assert are unchanged.
- **Files modified:** `src/doxastica/models.py`
- **Verification:** `uv run ruff check` clean; `uv run basedpyright` 0 errors; runtime check confirms `set(Status)`/`set(EdgeType)` membership and `Status.active == "active"`.
- **Committed in:** `a4eac63` (Task 1 commit)

**2. [Rule 3 - Blocking] Suppressed `TC003` on the `uuid.UUID` import**
- **Found during:** Task 1 (model authoring)
- **Issue:** ruff `TC003` (flake8-type-checking) wants `from uuid import UUID` moved into a `TYPE_CHECKING` block; doing so would break pydantic, which resolves field annotations at runtime.
- **Fix:** Added a targeted `# noqa: TC003` with an inline rationale on the import line (kept the import at runtime scope).
- **Files modified:** `src/doxastica/models.py`
- **Verification:** `uv run ruff check` clean; models instantiate at runtime (sanity check + 8 passing tests).
- **Committed in:** `a4eac63` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking lint/runtime issues)
**Impact on plan:** Both are mechanical tooling-compatibility fixes that preserve the exact typed surface the plan specified. No semantic change to the taxonomy, no scope creep. DATA-02/04/05/06 are encoded as written.

## Issues Encountered
- **`uv` sandbox panic:** every `uv run ...` command panicked under the command sandbox (the documented macOS system-configuration panic noted in the prompt). Re-ran each verification with the sandbox disabled; all are genuine tool runs, not misreported sandbox errors. No code failures.

## Threat Flags
None — no new security-relevant surface beyond the plan's threat model. The closed `BeliefFilter` (T-01-IV mitigation) and opaque `value: Any` (T-01-OPAQUE, accept-by-design) are implemented exactly as the threat register specifies; the closed filter makes a triple-structure/injection leak unrepresentable by construction.

## Known Stubs
None — `WorldScopeContractionError` is an intentionally-unraised typed surface this phase (enforcement is Phase 3, SCOPE-02), per the plan. No placeholder data or unwired components.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The shared model layer is ready for plan 03 (public `BeliefStore` Protocol) and plan 04 (internal backend port), which both import from `doxastica.models`.
- `__init__.py` re-exports were NOT touched this plan (still `__all__ = []`); the barrel population is owned by a later plan/task. Note for plan 03/04 if they expect public re-exports.
- No blockers.

## Self-Check: PASSED

All created files exist on disk; both task commits (`a4eac63`, `941493c`) present in git history.

---
*Phase: 01-protocol-backend-port-data-model-decisions*
*Completed: 2026-06-14*
