---
phase: 02-backend-adapters-schema-bootstrap-de-risking-spike
plan: 01
subsystem: database
tags: [backend-port, in-memory-backend, bfs-traversal, ports-and-adapters, pydantic, driver-isolation]

# Dependency graph
requires:
  - phase: 01-protocol-backend-port-data-model-decisions
    provides: BackendPort protocol (five LPG primitives), DoxasticaError base, frozen models, EdgeType
provides:
  - InMemoryBackend — the zero-dependency BackendPort oracle (idempotent upsert/edge, AND-exact match_nodes, cycle-safe visited-set traverse, snapshot/restore unit_of_work)
  - MemoryCore engine with in_memory/open/from_connection factory classmethods (D-01 Engine pattern)
  - BackendDependencyError(DoxasticaError, ImportError) — dual-catchable optional-driver error (D-02)
  - backends/ subpackage that re-exports only the zero-dep InMemoryBackend
  - Top-level doxastica exports for MemoryCore / InMemoryBackend / BackendDependencyError
affects:
  - 02-02 (ladybug adapter — must match InMemoryBackend traverse (reached, frontier) semantics; provides backends/ladybug.py the core factories forward-reference)
  - 02-03 (import-purity extension — proves core.py + backends/memory.py import with ladybug absent)
  - Phase 3-6 (AGM operations compose on these primitives; MemoryCore gains operation bodies)
  - Phase 7 (InMemoryBackend is the shadow-model oracle)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ports-and-adapters: InMemoryBackend structurally satisfies BackendPort (no inheritance)"
    - "Engine pattern (SQLAlchemy minus pool/two-tier/registry): canonical __init__ takes the port; named factory classmethods own connection/path handling"
    - "Driver-blind core via function-local imports: open/from_connection import the ladybug adapter inside the method body, never at module top or under TYPE_CHECKING"
    - "Visited-set BFS traverse returning (reached, frontier) with max_depth=None ⇒ full closure / empty frontier"
    - "Snapshot/restore logical transaction for in-memory unit_of_work (rollback on exception)"

key-files:
  created:
    - src/doxastica/core.py
    - src/doxastica/backends/__init__.py
    - src/doxastica/backends/memory.py
    - tests/test_backend_memory.py
  modified:
    - src/doxastica/errors.py
    - src/doxastica/__init__.py

key-decisions:
  - "Function-local ladybug imports in core.py factories forward-reference the wave-2 backends/ladybug.py; the not-yet-existing module is suppressed with narrowly-scoped per-line pyright ignores (reportAttributeAccessIssue/reportUnknownVariableType/reportUnknownMemberType) plus a cast to BackendPort — keeps strict basedpyright at 0 errors without a module-level driver import"
  - "InMemoryBackend keeps a label-agnostic _node_index so traverse can resolve reached node props without knowing the label; rebuilt on snapshot restore"
  - "traverse excludes the start node from reached (only successors are returned), matching the port's reachable-set contract"

patterns-established:
  - "Pattern: driver-blind engine — composes BackendPort, never holds a connection, factories do function-local backend imports"
  - "Pattern: in-memory oracle — stdlib dict node store + per-edge-type adjacency lists; the reference implementation later backends are checked against"

requirements-completed: [BACK-03]

# Metrics
duration: ~20min
completed: 2026-06-15
---

# Phase 2 Plan 01: In-Memory Backend Oracle + MemoryCore Engine Summary

**Zero-dependency InMemoryBackend (idempotent upsert/edge, AND-exact match, cycle-safe visited-set traverse with (reached, frontier), snapshot/restore unit_of_work) plus the driver-blind MemoryCore engine and its in_memory/open/from_connection factories.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-06-15T00:35:00Z (approx)
- **Completed:** 2026-06-15T00:55:00Z
- **Tasks:** 2
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments
- `InMemoryBackend` implements all five `BackendPort` primitives with stdlib + pydantic only (BACK-03 / D-05) — the Phase 7 oracle baseline.
- `traverse` is a cycle-safe visited-set BFS returning `(reached, frontier)`: `max_depth=None` ⇒ full closure with empty frontier; finite `max_depth` ⇒ boundary frontier (node at exactly the bound with an unexpanded successor).
- `MemoryCore` engine (D-01): canonical `__init__(backend: BackendPort)` + `in_memory()` / `open(path, ...)` / `from_connection(conn, ...)` factory classmethods; `unit_of_work` passthrough; NO AGM operation bodies.
- Driver isolation (D-02): `core.py`, `__init__.py`, and `backends/__init__.py` chain-load no driver; `open`/`from_connection` use function-local ladybug imports; `BackendDependencyError(DoxasticaError, ImportError)` is dual-catchable.
- Top-level `doxastica` now exports `MemoryCore`, `InMemoryBackend`, `BackendDependencyError`.

## Task Commits

Each task was committed atomically:

1. **Task 1: BackendDependencyError + InMemoryBackend oracle** - `a61ead2` (feat)
2. **Task 2: MemoryCore engine + driver-blind factories + package exports** - `4645531` (feat)

_Task 1 was a TDD task; the tests and implementation were committed together after the RED→GREEN cycle (single verify command, single commit per the plan's task boundary)._

## Files Created/Modified
- `src/doxastica/errors.py` - Added `BackendDependencyError(DoxasticaError, ImportError)`; updated header docstring for Phase 2.
- `src/doxastica/backends/__init__.py` - New subpackage init; re-exports only the zero-dep `InMemoryBackend` (never imports ladybug).
- `src/doxastica/backends/memory.py` - New `InMemoryBackend`: dict node store + per-edge-type adjacency + label-agnostic index; the five primitives; visited-set BFS traverse; snapshot/restore unit_of_work.
- `src/doxastica/core.py` - New `MemoryCore` engine + three factory classmethods (driver-blind via function-local imports) + unit_of_work passthrough.
- `src/doxastica/__init__.py` - Added `MemoryCore` / `InMemoryBackend` / `BackendDependencyError` to imports and sorted `__all__` (stays driver-blind).
- `tests/test_backend_memory.py` - New: 14 focused tests covering each primitive (idempotency, AND-match, label-scoping, cycle-safety, unbounded-empty-frontier, bounded-frontier, edge-type filtering, unit_of_work rollback/persist), error dual-catch, and the MemoryCore factory + exports.

## Decisions Made
- **Forward-reference to the wave-2 ladybug adapter under strict typing:** `backends/ladybug.py` does not exist until plan 02-02, but `MemoryCore.open`/`from_connection` must wire it by name (per plan + PATTERNS). Resolved with function-local `from doxastica.backends import ladybug` plus narrowly-scoped per-line `# pyright: ignore[...]` and a `cast("BackendPort", ...)`. This keeps `core.py` driver-blind (no module-level/TYPE_CHECKING ladybug import), keeps basedpyright strict at 0 errors, and the suppressions naturally fall away when 02-02 lands the real module.
- **`_node_index` (label-agnostic):** `traverse` resolves successor props without knowing their label; rebuilt after a `unit_of_work` rollback restore.
- **`traverse` returns successors only** (start excluded from `reached`) — matches the reachable-set contract; the parity suite (02-03) asserts this against ladybug.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `@contextmanager` return type `Iterator` → `Generator` (basedpyright strict)**
- **Found during:** Task 1 (InMemoryBackend.unit_of_work)
- **Issue:** basedpyright strict flagged `reportDeprecated` — annotating a `@contextmanager` function as `-> Iterator[...]` is deprecated; it wants `-> Generator[...]`.
- **Fix:** Changed the type-only import and the `unit_of_work` return annotation to `Generator[None]`.
- **Files modified:** src/doxastica/backends/memory.py
- **Verification:** `uv run basedpyright src/doxastica/backends/memory.py` → 0 errors.
- **Committed in:** a61ead2 (Task 1 commit)

**2. [Rule 3 - Blocking] Strict-typing the function-local forward import of the wave-2 ladybug adapter**
- **Found during:** Task 2 (MemoryCore.open / from_connection)
- **Issue:** The plan's acceptance criterion requires basedpyright strict 0 errors on `core.py`, but the factories reference `backends/ladybug.py` which is not built until plan 02-02 — producing `reportMissingImports`/`reportAttributeAccessIssue` and cascading `reportUnknown*` errors.
- **Fix:** Function-local `from doxastica.backends import ladybug` with per-line `# pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType]` on the import and `# pyright: ignore[reportUnknownMemberType]` on the member access, plus `cast("BackendPort", ...)` to pin the constructor argument type. No module-level or TYPE_CHECKING ladybug import was introduced (D-02 preserved).
- **Files modified:** src/doxastica/core.py
- **Verification:** `uv run basedpyright src/doxastica/` → 0 errors; `grep -v '^#' core.py | grep -c "import ladybug"` → 0; `uv run python -c "from doxastica import MemoryCore; MemoryCore.in_memory()"` → ok.
- **Committed in:** 4645531 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking typing issues)
**Impact on plan:** Both were required to satisfy the plan's own strict-typing acceptance criteria under the deliberate wave-1-before-wave-2 ordering. No scope creep; no behavior changes; D-01/D-02 contracts preserved exactly.

## Issues Encountered
- ruff's import formatter repeatedly re-wrapped the long function-local import to a parenthesized multiline form, which shifted where the per-line pyright comment landed. Resolved by switching to `from doxastica.backends import ladybug` (a submodule import whose error code attaches to the `ladybug` symbol line the comment ends up on after autofix), then matching the suppression codes to the actual diagnostics.

## User Setup Required
None - no external service configuration required. (D-03 packaging/CLAUDE.md reversal and the ladybug adapter are later plans in this phase.)

## Verification Results
- `uv run pytest -q` → 31 passed (14 new in test_backend_memory.py).
- `uv run python -c "import doxastica, doxastica.core, doxastica.backends.memory"` → clean.
- `uv run python -c "from doxastica import MemoryCore; MemoryCore.in_memory()"` → ok.
- `uv run basedpyright src/doxastica/` → 0 errors, 0 warnings.
- `uv run ruff check src/doxastica/ tests/` → all checks passed; `ruff format --check` → all formatted.
- Acceptance greps: `import ladybug` count in `backends/memory.py`, `backends/__init__.py`, and `core.py` (excl. comments) all 0.

## Next Phase Readiness
- The `BackendPort` contract is now proven driver-free; the in-memory oracle's `(reached, frontier)` semantics are the baseline the wave-2 ladybug adapter (02-02) must match exactly.
- `MemoryCore.open`/`from_connection` already wire `backends/ladybug.py` by name — plan 02-02 only needs to land that module for the factories to resolve (the per-line pyright suppressions then become removable).
- Plan 02-03 can extend `tests/test_import_purity.py` to add `core` and `backends/memory` to the module-level scan and the runtime-absence proof.

## Self-Check: PASSED

All created files exist on disk; both task commits (`a61ead2`, `4645531`) are present in git history.

---
*Phase: 02-backend-adapters-schema-bootstrap-de-risking-spike*
*Completed: 2026-06-15*
