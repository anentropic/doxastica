---
phase: 03-append-only-revision-spine-keystone
plan: 01
subsystem: revision-spine-foundation
tags: [models, ladybug-backend, schema, world-scope, has-revision]
requires:
  - "Phase 1 models.py closed taxonomy (Status/EdgeType/Scope/Belief/BeliefState)"
  - "Phase 2 LadybugBackend (_bootstrap_schema, add_edge, _PK_BY_LABEL)"
provides:
  - "WORLD_SCOPE_ID = '__world__' module constant + package-barrel re-export"
  - "HAS_REVISION hub-form REL table (FROM Belief TO BeliefState) on the ladybug backend"
  - "Endpoint-label-aware ladybug add_edge (_EDGE_ENDPOINTS map)"
affects:
  - "src/doxastica/models.py"
  - "src/doxastica/__init__.py"
  - "src/doxastica/backends/ladybug.py"
tech-stack:
  added: []
  patterns:
    - "Closed endpoint-label map (_EDGE_ENDPOINTS) parallel to _PK_BY_LABEL — per-edge-type FROM/TO label + PK lookup, no hardcoded BeliefState endpoints"
    - "Hub-form structural edge (Belief -> BeliefState) created as its own DDL statement outside the BeliefState->BeliefState loop"
key-files:
  created: []
  modified:
    - "src/doxastica/models.py"
    - "src/doxastica/__init__.py"
    - "src/doxastica/backends/ladybug.py"
decisions:
  - "D-02: WORLD_SCOPE_ID is the dunder-wrapped literal '__world__' (collision-safe vs a caller scope named 'world'); lives in models.py, NOT a separate constants.py (PATTERNS flag 2); get_or_create_scope signature unchanged"
  - "D-07: HAS_REVISION is hub form FROM Belief TO BeliefState; passed to add_edge as a RAW STRING, never an EdgeType enum member"
  - "D-01: no CURRENT_STATE REL table — current state is derived, not a stored edge"
metrics:
  duration: 3min
  completed: 2026-06-15
  tasks: 2
  files: 3
---

# Phase 3 Plan 01: Append-Only Revision Spine Foundation Summary

Interface-first structural plumbing for the Phase-3 op bodies: the reserved
`WORLD_SCOPE_ID = "__world__"` constant (exported from the package barrel because NVM imports
it), the hub-form `HAS_REVISION` REL table (`FROM Belief TO BeliefState`) on the ladybug
backend, and a generalized `add_edge` that resolves per-edge-type endpoint labels + PK columns
instead of hardcoding both endpoints to `BeliefState`/`state_id` — all with zero AGM logic.

## What Was Built

### Task 1: WORLD_SCOPE_ID constant (D-02)
- Added module-level `WORLD_SCOPE_ID: str = "__world__"` to `src/doxastica/models.py`,
  near the top after imports, with a comment citing D-02 (dunder-wrapped to avoid colliding
  with a caller scope literally named "world"; it is the single id whose `get_or_create_scope`
  yields `Scope(is_world=True)`).
- Re-exported from `src/doxastica/__init__.py` (added to the `from doxastica.models import (...)`
  block and to `__all__`).
- `get_or_create_scope(scope_id: str) -> Scope` in `protocol.py` is unchanged (no `is_world`
  parameter added).
- Importable as `from doxastica import WORLD_SCOPE_ID`, equals `"__world__"`.
- Commit: `5b78b23`

### Task 2: HAS_REVISION REL table + endpoint-aware add_edge (D-07, PATTERNS flag 1)
- `_bootstrap_schema` now creates `{ns}_HAS_REVISION(FROM {ns}_Belief TO {ns}_BeliefState)`
  with `IF NOT EXISTS`, as its own statement (NOT inside the `SUPERSEDES/DEPENDS_ON/DERIVED_FROM`
  BeliefState->BeliefState loop). No `CURRENT_STATE` table created (D-01). Method docstring
  updated to reflect that only HAS_REVISION lands and current is derived.
- Introduced module-level `_EDGE_ENDPOINTS` (parallel to `_PK_BY_LABEL`) mapping each edge-type
  string to a `(from_label, to_label)` pair: `HAS_REVISION -> (Belief, BeliefState)` and the
  three `EdgeType` members `-> (BeliefState, BeliefState)`.
- `add_edge` resolves `from_label, to_label` from `_EDGE_ENDPOINTS[str(edge_type)]`, then builds
  the MATCH using each endpoint's own label and PK column (from `_PK_BY_LABEL`): the FROM clause
  matches `(a:{ns}_Belief {belief_id: $from})` for HAS_REVISION and
  `(a:{ns}_BeliefState {state_id: $from})` for the structural family. Endpoint ids stay `$param`
  binds; `MERGE` idempotency preserved; `edge_type: EdgeType | str` signature unchanged.
- `memory.py` add_edge left untouched (already label-agnostic — keys on raw `str(from_id)`;
  confirmed by inspection).
- Commit: `b0c403b`

## Verification Evidence

- `from doxastica import WORLD_SCOPE_ID` exits 0, equals `"__world__"`.
- Hub-edge probe (`add_edge('HAS_REVISION', belief_id, state_id)` after upserting a Belief and a
  BeliefState) prints `hub edge ok` — a Belief->BeliefState edge is laid without error.
- `grep -v '^[[:space:]]*#' ... | grep 'CREATE REL TABLE' | grep -c CURRENT_STATE` returns `0`.
- `ladybug.py` contains both `HAS_REVISION` and `_EDGE_ENDPOINTS`.
- `UV_NO_SYNC=1 uv run --extra ladybug pytest`: 80 passed, 1 xfailed (the expected AGM Recovery
  xfail) — no regression to the structural-edge family or bootstrap idempotency.
- `UV_NO_SYNC=1 uv run --extra ladybug basedpyright src`: 0 errors, 0 warnings, 0 notes.
- `UV_NO_SYNC=1 uv run ruff check src`: all checks passed.

## Deviations from Plan

None - plan executed exactly as written. (One mechanical adjustment: `ruff check --fix`
reordered the `__init__.py` import to place `WORLD_SCOPE_ID` first in the `doxastica.models`
block per isort's uppercase-before-lowercase ordering — this is the formatter's canonical output,
not a logic change.)

## Threat Surface

No new threat surface beyond the plan's `<threat_model>`. The namespace remains the only
interpolated identifier (`_NS_RE`-validated in `__init__`); the new HAS_REVISION DDL is fixed
structural text; `add_edge` keeps `from_id`/`to_id` as `$param` binds while interpolating only
the validated namespace, the closed `_EDGE_ENDPOINTS` labels, and the edge-type label
(T-03-01 / T-03-02 mitigations hold). No edge-delete/replace primitive added (append-only
invariant intact, T-03-AO). No package installs (T-03-SC).

## Known Stubs

None. This plan deliberately ships no `core.py` op bodies (those are plan 03-02); that is the
planned interface-first ordering, not a stub.

## Self-Check: PASSED
- FOUND: src/doxastica/models.py (WORLD_SCOPE_ID)
- FOUND: src/doxastica/__init__.py ("WORLD_SCOPE_ID" in __all__)
- FOUND: src/doxastica/backends/ladybug.py (HAS_REVISION, _EDGE_ENDPOINTS)
- FOUND: commit 5b78b23
- FOUND: commit b0c403b
