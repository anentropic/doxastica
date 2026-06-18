---
phase: 05-edge-model-contraction-cascade
plan: 01
subsystem: api
tags: [traverse, graph-traversal, cypher, ladybug, in-memory-backend, direction, cascade]

# Dependency graph
requires:
  - phase: 02-ladybug-backend-port
    provides: "cycle-safe bounded traverse (reached, frontier) on both backends + parametrized parity fixture"
  - phase: 01-protocol-backend-port-data-model-decisions
    provides: "BackendPort Protocol, EdgeType/ImpactResult models, BACK-04 contract"
provides:
  - "BackendPort.traverse keyword-only direction: Literal['in','out']='out' (the one genuine Phase-5 port change, D-05)"
  - "in-memory reverse-adjacency walk via _in_edges (predecessor scan, mirror of _out_edges)"
  - "ladybug direction-aware traverse via a 3-arrow flip (main query, EXISTS frontier subquery, bound==0 probe)"
  - "byte-identical reverse-direction (direction='in') parity across both backends, incl max_depth=0"
  - "BACK-04 §2 documents the direction parameter"
affects: [05-03-get_impact, 06-get_scope_at, 07-conformance-suite]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "closed-Literal direction token derives an (lhs, rhs) Cypher arrow pair — inside the one sanctioned-interpolation story (no new $param/free-text surface)"
    - "direction-routed BFS: select neighbour fn (_in_edges/_out_edges) once, leave layer/frontier/seen logic direction-agnostic"

key-files:
  created: []
  modified:
    - src/doxastica/ports.py
    - src/doxastica/backends/memory.py
    - src/doxastica/backends/ladybug.py
    - docs/backend-contract.md
    - tests/test_backend_parity.py

key-decisions:
  - "direction is keyword-only with default 'out' — a cross-phase contract keeping the 27 existing positional traverse parity calls AND the future Phase-6 get_scope_at green unchanged"
  - "in-memory reverse walk uses an O(edges) predecessor SCAN (not a reverse index) per D-05 discretion — so _reindex/unit_of_work need no extension"
  - "ladybug flips ALL THREE arrows from one (lhs, rhs) pair; cap-raise/restore stays direction-agnostic wrapping both directions (T-05-02 mitigated)"

patterns-established:
  - "Pattern: derive Cypher arrow pair from a closed Literal — lhs, rhs = ('<-', '-') if direction == 'in' else ('-', '->')"
  - "Pattern: neighbour-fn selection for direction-routed BFS in the in-memory backend"

requirements-completed: [EDGE-02]

# Metrics
duration: 4min
completed: 2026-06-18
---

# Phase 5 Plan 01: traverse direction parameter Summary

**Keyword-only `direction: Literal["in","out"]="out"` added to `BackendPort.traverse` and implemented on both backends — an in-memory `_in_edges` predecessor scan and a ladybug 3-arrow Cypher flip — producing byte-identical reverse-direction parity while keeping every existing positional caller green.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-18T23:08:25+01:00
- **Completed:** 2026-06-18T23:11:47+01:00
- **Tasks:** 4
- **Files modified:** 5

## Accomplishments
- Extended the `BackendPort.traverse` port signature + docstring with a keyword-only `direction` parameter (default `"out"`), the ONE genuine new capability in Phase 5 (D-05), without breaking any existing positional caller.
- Implemented the reverse walk on the in-memory oracle via a new `_in_edges` predecessor scan, routed by selecting the neighbour function once and leaving the BFS layer/frontier/seen logic untouched.
- Implemented the reverse walk on the ladybug reference backend by deriving an `(lhs, rhs)` arrow pair from the closed `Literal` and flipping the arrow in all three sites (main var-length query, its `EXISTS{}` frontier subquery, and the `bound==0` probe), with the `var_length_extend_max_depth` cap-raise/restore left direction-agnostic.
- Added 11 reverse-direction parity cases (asymmetric chain probe, flipped `bound==0` IN-edge probe + no-in-edge mirror, depth-bounded reached+frontier, both-backends byte-identical) — all green on both backends; documented `direction` in BACK-04 §2.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave-0 failing reverse-direction parity tests** - `aeeed28` (test)
2. **Task 2: direction param on the port signature + docstring + BACK-04** - `a753bf5` (feat)
3. **Task 3: in-memory reverse-adjacency direction routing** - `ebde20b` (feat)
4. **Task 4: ladybug 3-arrow flip + full parity regression** - `ce16f5d` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `src/doxastica/ports.py` - Added `Literal` import; `BackendPort.traverse` gains keyword-only `direction: Literal["in","out"]="out"` + extended docstring (out=successors/get_scope_at, in=predecessors/get_impact cascade). No `ladybug` import (import-purity preserved).
- `src/doxastica/backends/memory.py` - Added `Literal` import; `traverse` routes on `direction` via `neighbours = self._in_edges if direction == "in" else self._out_edges`; new `_in_edges` predecessor scan mirroring `_out_edges`.
- `src/doxastica/backends/ladybug.py` - Added `Literal` import; `traverse` derives `(lhs, rhs)` from `direction` and flips all three arrows; `$start` $param-bind, `_EDGE_ENDPOINTS` validation, guarded `bound` int, and cap-raise/restore all unchanged.
- `docs/backend-contract.md` - BACK-04 §2 traverse bullet documents the `direction` parameter (both directions on both backends must agree; ordering still non-contractual per §5).
- `tests/test_backend_parity.py` - 11 new reverse-direction (`direction="in"`) parity cases across the parametrized fixture + a both-backends byte-identical reverse case.

## Decisions Made
None - followed plan as specified. The three plan-locked choices (keyword-only `"out"` default as cross-phase contract; scan-based reverse adjacency per D-05 discretion; direction-agnostic cap-raise/restore) were implemented exactly as written.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Minor ruff `D213`/`E501` lint findings on the new test/docstring lines (multi-line summary placement, line length). Resolved inline during the task (summaries moved to the second line, long assert messages shortened) before each commit — not a deviation, just lint compliance within the task's own changes.

## User Setup Required
None - no external service configuration required.

## Verification Evidence
- `uv run pytest tests/test_backend_parity.py -q` — 45 passed (27 positional regression + 11 reverse + 7 other parity), both backends.
- `uv run pytest -q` — 139 passed (full suite; Phase 6 `traverse` callers and all prior phases unbroken by the signature change).
- `uv run basedpyright src/doxastica/ports.py src/doxastica/backends/memory.py src/doxastica/backends/ladybug.py` — 0 errors, 0 warnings.
- `uv run ruff check src/doxastica docs tests` — all checks passed.
- `uv run pytest tests/test_import_purity.py -q` — 7 passed (no `ladybug` leaked into `ports.py`).

## Threat Model Compliance
- **T-05-01 (reverse-arrow interpolation, mitigate):** `direction` is a closed `Literal`, never caller-free-text, never a `$param` position; the arrow pair is a derived internal token. `$start` stays `$param`-bound, `edge_types` stays `_EDGE_ENDPOINTS`-validated, `bound` stays the runtime-guarded int. No new untrusted-input surface.
- **T-05-02 (`var_length_extend_max_depth` leak, mitigate):** the `try/finally` cap-restore stays direction-agnostic, wrapping both directions identically; no branch skips the `finally`.
- **T-05-SC (installs, accept):** no package installs this phase.

## Next Phase Readiness
- The `direction="in"` traverse primitive is now available on both backends — Plan 05-03's `get_impact` cascade can compose it (note the documented hydration gap: ladybug `traverse` still returns `state_id`-only rows, so `get_impact` must re-fetch props via `match_nodes`, Option A).
- Phase 6 `get_scope_at` is unaffected: the `"out"` default preserves the outgoing walk it expects.
- Phase 7 conformance must exercise BOTH directions on BOTH backends (already true for these parity cases; extend to the AGM postulate suite there).

## Self-Check: PASSED

- All 5 modified files exist on disk.
- All 4 task commits found in git history (`aeeed28`, `a753bf5`, `ebde20b`, `ce16f5d`).
- SUMMARY.md created at the plan directory.

---
*Phase: 05-edge-model-contraction-cascade*
*Completed: 2026-06-18*
