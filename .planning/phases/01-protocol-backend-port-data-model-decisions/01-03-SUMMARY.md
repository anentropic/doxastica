---
phase: 01-protocol-backend-port-data-model-decisions
plan: 03
subsystem: api
tags: [typing-protocol, pydantic, ast, uuid7, import-purity, agm]

# Dependency graph
requires:
  - phase: 01-02
    provides: "Frozen typed value layer (Scope, Belief, BeliefState, BeliefFilter, ImpactResult, Status, EdgeType) in src/doxastica/models.py and the typed error surface in src/doxastica/errors.py"
provides:
  - "Public BeliefStore typing.Protocol — the ladybug-free NVM-core seam (9 methods)"
  - "DATA-02 closed-filter query signature (query_scope takes BeliefFilter, never a free str)"
  - "DATA-04 ImpactResult return with depth: int | None = None unbounded default on get_impact"
  - "DATA-03 UUID7 ordering contract written into protocol.py source as a docstring"
  - "DATA-01 executable import-purity guard (AST scan asserting protocol.py imports no ladybug)"
  - "Populated public re-export barrel in src/doxastica/__init__.py __all__"
affects: [phase-02-backend-port, phase-03-memory-core-implementation, phase-07-property-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "typing.Protocol structural-interface convention (ellipsis-body methods, no implementation)"
    - "from __future__ import annotations + TYPE_CHECKING-guarded model imports to keep the public seam runtime-light and ruff-clean while remaining AST-scannable"
    - "AST-scan executable guard turning a design rule (DATA-01 import purity) into a build failure"

key-files:
  created:
    - "src/doxastica/protocol.py"
    - "tests/test_import_purity.py"
  modified:
    - "src/doxastica/__init__.py"

key-decisions:
  - "Imported the public Protocol's annotation types under TYPE_CHECKING (with `from __future__ import annotations`) instead of `# noqa: TC003`, satisfying ruff TC001/TC003 cleanly; the AST import-purity scan still descends into the TYPE_CHECKING block so DATA-01 remains mechanically enforced"
  - "Wrote the DATA-03 UUID7 ordering contract on both the BeliefStore class docstring and the get_scope_at method docstring so the doc-assertion finds the (source_event_id byte-order, state_id tiebreak) text"

patterns-established:
  - "Pattern 1: Public seam keeps its annotation imports in a TYPE_CHECKING block; AST guards still see them"
  - "Pattern 2: Design-rule-as-build-failure — DATA-01 leak is a failing pytest, not a review note"

requirements-completed: [DATA-01, DATA-02, DATA-03, DATA-04, DATA-05]

# Metrics
duration: 3min
completed: 2026-06-14
---

# Phase 01 Plan 03: Public BeliefStore Protocol & Import-Purity Guard Summary

**Ladybug-free `BeliefStore` `typing.Protocol` with DATA-02 closed `BeliefFilter` query, DATA-04 `ImpactResult`/unbounded `depth`, the written DATA-03 UUID7 ordering contract, an AST import-purity test, and the populated public re-export barrel**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-14T19:44:22Z
- **Completed:** 2026-06-14T19:47:35Z
- **Tasks:** 2
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- Authored `src/doxastica/protocol.py`: the public `BeliefStore` `Protocol` with all nine methods, importing only `typing`/`uuid`/`doxastica.models` — zero `ladybug` import (DATA-01).
- Applied the locked refinements: `query_scope(scope_id, filter: BeliefFilter, include_deprecated=False)` (DATA-02) and `get_impact(belief_state_id, depth: int | None = None) -> ImpactResult` (DATA-04).
- Wrote the DATA-03 UUID7 ordering contract `(source_event_id byte-order, state_id tiebreak)` into the source as class- and method-level docstrings, noting intra-ms monotonicity is not demanded of the caller.
- Made DATA-01 a build failure via `tests/test_import_purity.py` (an `ast` scan of `protocol.py`).
- Populated `src/doxastica/__init__.py` `__all__` re-exporting `BeliefStore`, `Belief`, `Scope`, `BeliefState`, `BeliefFilter`, `ImpactResult`, `Status`, `EdgeType`, `DoxasticaError`, `WorldScopeContractionError`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Author the public BeliefStore Protocol with the UUID7 ordering contract** - `747c51e` (feat)
2. **Task 2: Author the import-purity AST guard and populate the re-export barrel** - `ad4dd71` (feat)

## Files Created/Modified
- `src/doxastica/protocol.py` - Public `BeliefStore` `typing.Protocol` (NVM-core seam); imports only typing/uuid/models; carries the DATA-03 ordering contract.
- `tests/test_import_purity.py` - DATA-01 guard: `test_protocol_does_not_import_ladybug` AST-scans `protocol.py` and fails the build on any `ladybug` import.
- `src/doxastica/__init__.py` - Populated `__all__` re-export barrel for the public surface.

## Decisions Made
- **TYPE_CHECKING-guarded annotation imports** instead of scattered `# noqa`. Ruff's TC001/TC003 wanted the annotation-only model imports moved into a type-checking block; pairing that with `from __future__ import annotations` keeps the public Protocol module runtime-light and ruff-clean. The DATA-01 AST scan walks the whole tree (`ast.walk`), so it still inspects imports inside the `if TYPE_CHECKING:` block — import purity stays mechanically enforced. (models.py used `# noqa: TC003` because pydantic resolves field annotations at runtime; the Protocol has no such constraint, so the guarded-import form is strictly cleaner here.)
- **Ordering contract written twice** (class docstring + `get_scope_at` docstring) so the DATA-03 doc-assertion finds the `(source_event_id byte-order, state_id tiebreak)` text regardless of where it looks.

## Deviations from Plan

None - plan executed exactly as written. (Ruff's TC001/TC003/D205 hints were resolved within Task 1's normal acceptance-gate loop — the plan calls for clean ruff, so satisfying it is not a deviation.)

## Issues Encountered
- Ruff initially flagged TC001/TC003 (move annotation-only imports into a TYPE_CHECKING block) and D205 (blank line after summary). Resolved by adding `from __future__ import annotations`, guarding the model/`UUID` imports under `TYPE_CHECKING`, and restructuring the module docstring. basedpyright strict stayed at 0 errors throughout; full `uv run pytest`, `uv run basedpyright`, and `uv run ruff check .` all pass.

## Known Stubs
None. `protocol.py` is a pure interface (ellipsis-body Protocol methods by design — this is the intended Phase-1 artifact, not an unfinished implementation; behavior lands in Phase 3). No empty data sources, placeholder text, or unwired components.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The public `BeliefStore` seam is frozen and importable from the package root; Phase 2 (backend port) and Phase 3 (MemoryCore implementation) can code against it.
- DATA-01 purity is now self-guarding: any future `ladybug` import into `protocol.py` fails the test suite.
- No blockers.

## Self-Check: PASSED

All created/modified files exist on disk and both task commits (`747c51e`, `ad4dd71`) are present in git history.

---
*Phase: 01-protocol-backend-port-data-model-decisions*
*Completed: 2026-06-14*
