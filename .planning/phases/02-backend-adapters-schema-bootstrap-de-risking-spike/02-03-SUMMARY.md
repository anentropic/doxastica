---
phase: 02-backend-adapters-schema-bootstrap-de-risking-spike
plan: 03
subsystem: testing
tags: [pytest, hypothesis-adjacent, parity, oracle, conftest, importorskip, ast, import-isolation, ladybug]

# Dependency graph
requires:
  - phase: 02-backend-adapters-schema-bootstrap-de-risking-spike (plan 01)
    provides: InMemoryBackend oracle, MemoryCore engine + factories
  - phase: 02-backend-adapters-schema-bootstrap-de-risking-spike (plan 02)
    provides: LadybugBackend reference adapter, DEF-02-01 coercion finding
provides:
  - Parametrized `backend` fixture (conftest) — fresh throwaway :memory: per example over [memory, ladybug]; ladybug param importorskip-skipped when driver absent (FORMAL-06, D-03)
  - Oracle-parity suite — identical (reached, frontier) + match_nodes across both backends on diamond / cycle / over-bound chain (D-05, BACK-03)
  - In-process both-backends byte-identical comparison (compares the two adapters to EACH OTHER, not just to a literal)
  - DEF-02-01 value-round-trip regression — in-memory PASS, ladybug xfail (visible, not masked)
  - Module-level-only import-purity scan extended to core + backends/memory (D-02), plus a subprocess sys.meta_path-block runtime proof
affects: [02-04 CI base-install job, Phase 3 AGM operations, Phase 3 value-encoding contract, Phase 7 conformance-suite oracle]

# Tech tracking
tech-stack:
  added: []  # zero new packages this phase (RESEARCH audit: tests only)
  patterns:
    - Parametrized parity fixture (plain params list, D-01a) yielding a fresh throwaway :memory: backend per example
    - importorskip-gated optional-driver param (skip, never error, when ladybug is absent)
    - MODULE-LEVEL-only AST import scan (top-level + TYPE_CHECKING blocks; ignores sanctioned function-local imports)
    - subprocess sys.meta_path finder to simulate genuine driver absence in a dev env where ladybug IS installed

key-files:
  created:
    - tests/test_backend_parity.py
  modified:
    - tests/conftest.py
    - tests/test_import_purity.py
    - tests/test_backend_memory.py

key-decisions:
  - "Parity fixture is a plain params=['memory','ladybug'] list (D-01a) — no lookup indirection; backends named directly"
  - "Fresh lb.Database() (None path) constructed PER fixture call (FORMAL-06, Pitfall 5) — no shared-path lock errors, no cross-example state bleed"
  - "_node() helper omits the state_id PK from props for ladybug (ladybug forbids SET on a PRIMARY KEY) and mirrors it into props for the in-memory oracle, so match_nodes rows carry state_id on both for parity"
  - "DEF-02-01 ladybug value-round-trip is a standalone xfail test (not a dynamic per-param marker) to stay basedpyright-strict-clean; the in-memory oracle proves the same assertion passes"
  - "import-purity scan switched from ast.walk to module-level-only collection so MemoryCore's sanctioned function-local ladybug imports (D-02) are not mis-flagged; negative + positive controls assert both directions"

patterns-established:
  - "Cross-backend parity is asserted from day one (D-05), not deferred to Phase 7 — the parametrized fixture is the drift detector"
  - "Optional-driver isolation has two independent proofs: the module-level static scan AND a subprocess runtime-absence test (alongside CI Job 1)"
  - "Deferred backend hazards (DEF-02-01) are tracked as visible xfails, never silently masked"

requirements-completed: [BACK-03, FORMAL-06]

# Metrics
duration: 12min
completed: 2026-06-15
---

# Phase 2 Plan 3: Oracle Parity + Import Isolation Summary

A parametrized `backend` fixture and an oracle-parity suite that lock the D-05/BACK-03 cross-backend agreement from day one, plus a module-level-only import-purity scan proving `core` and `backends/memory` import driver-blind — built on a Rule-3 fix that unblocked the strict typecheck gate over `tests/`.

## What Was Built

**Task 1 — Parametrized backend fixture + oracle-parity suite** (`tests/conftest.py`, `tests/test_backend_parity.py`)
- `conftest.backend`: a `@pytest.fixture(params=["memory", "ladybug"])` yielding a fresh throwaway backend per example. The ladybug param uses `pytest.importorskip("ladybug")` (skips, never errors, when the driver is absent) and constructs a brand-new in-memory `lb.Database()` + `Connection` per call (FORMAL-06, no state bleed / lock errors), wrapped in a self-owning `LadybugBackend` closed on teardown. Plain params list — no lookup indirection (D-01a; `grep -c registry` == 0).
- Parity suite over diamond (A→B,A→C,B→D,C→D), cycle (A→B→C→A), and over-bound chain (A→B→C→D): asserts identical `(reached, frontier)` and `match_nodes` across both backends. Includes the diamond frontier edge cases (depth-1 frontier = {B,C}; depth-2 D found at its MIN depth and NOT on frontier), cycle termination/de-dup, and the over-bound boundary frontier vs. empty full-closure frontier.
- An in-process both-backends test builds memory AND ladybug and asserts byte-identical sorted results — comparing the adapters to EACH OTHER, not only to a literal.

**Task 2 — Driver-blind import isolation extended** (`tests/test_import_purity.py`)
- Replaced the `ast.walk` scan with a MODULE-LEVEL-only collection (`_module_level_imports`): top-level statements + module-scoped `if TYPE_CHECKING:` blocks, deliberately NOT descending into function/method bodies.
- Added `core` and `backends/memory` to the parametrized module list (joining `protocol`, `ports`).
- Added a negative-control test (the scan catches a top-level AND a `TYPE_CHECKING`-block ladybug import, but NOT a function-local one) and a positive control on the real `core.py` (its sanctioned function-local imports pass).
- Added a subprocess test installing a `sys.meta_path` finder that raises `ModuleNotFoundError` for any `ladybug` import, then imports the driver-free spine and runs `MemoryCore.in_memory()` — the runtime proof of D-02 alongside CI base-install Job 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking typecheck] Fixed pre-existing basedpyright-strict errors in test_backend_memory.py (DEF-02-02)**
- **Found during:** pre-flight (authorized blocking deviation)
- **Issue:** Plan 01 ran basedpyright over `src/` only; `tests/` is in strict scope too. `_value()` returned `object`, so `sorted(_value(r) for r in reached)` produced a `Generator[object, ...]` that basedpyright rejected (`reportArgumentType`, not `SupportsRichComparison`) at 3 sites. The strict typecheck acceptance gate could not pass until fixed.
- **Fix:** Annotated `_value` to return `str` (asserting the id is a `str`, true for every fixture node), so `sorted()` receives a `SupportsRichComparison` iterable.
- **Files modified:** tests/test_backend_memory.py
- **Commit:** 8f26a31

### Additions

**2. [DEF-02-01 regression] Value-round-trip case added to the parity suite**
- **Added:** a JSON-object-shaped STRING value (`'{"x": 2}'`) round-trip through `upsert_node` → `match_nodes`. The in-memory oracle PASSES it byte-identically; the ladybug case is a standalone `xfail` (reason: "DEF-02-01: ladybug STRUCT/LIST coercion, deferred to Phase 3 value-encoding contract") confirming the 02-02 finding that ladybug 0.17.1 coerces brace/bracket-shaped string params. Tracked and visible, not masked.
- **Files:** tests/test_backend_parity.py
- **Commit:** e89031f

## Implementation Notes

- **PK-in-props gotcha:** ladybug raises `Binder exception: Cannot set property state_id ... because it is used as primary key`. The `_node()` helper therefore omits `state_id` from the props passed to the ladybug `upsert_node` (the PK is set from the MERGE key) and mirrors it into props for the in-memory oracle (which stores props verbatim), so `match_nodes` rows carry `state_id` on both backends for parity.
- **xfail shape:** the ladybug DEF-02-01 case is a separate top-level `@pytest.mark.xfail` test rather than a dynamic `request.node.add_marker`, because the dynamic approach tripped `reportUnknownMemberType` under basedpyright strict.

## Verification

- `uv run --extra ladybug basedpyright` — 0 errors over src AND tests.
- `uv run --extra ladybug ruff check` — clean (conftest, parity, import-purity, backend-memory).
- `uv run --extra ladybug pytest -p no:randomly` — 68 passed, 1 xfailed (the DEF-02-01 ladybug case).
- `pytest --collect-only` — each parity test parametrized over [memory, ladybug]; import-purity lists core + backends/memory.

## Threat Surface

T-02-PAR-01 (parity drift) and T-02-PAR-02 (hidden ladybug coupling) are both `mitigate` in the plan's threat register and are now realized: the parity suite catches drift from day one, and the module-level scan + subprocess-absence test prove the driver-free spine carries no module-level ladybug import and runs with ladybug blocked. No new security surface introduced (tests only; T-02-SC `accept` — zero packages installed).

## Self-Check: PASSED

- All created/modified files exist on disk (conftest.py, test_backend_parity.py, test_import_purity.py, test_backend_memory.py, 02-03-SUMMARY.md).
- All three task commits exist in git history (8f26a31, e89031f, d0a3df8).
