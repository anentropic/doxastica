---
phase: 05-edge-model-contraction-cascade
plan: 02
subsystem: core-edge-write
tags: [EDGE-01, add_edge, D-06, D-07, oracle-parity]
requires:
  - "BackendPort.add_edge (idempotent MERGE — both backends, Phase 2)"
  - "MemoryCore.unit_of_work / backend.unit_of_work (Phase 2)"
  - "EdgeType closed enum (Phase 1, models.py)"
provides:
  - "MemoryCore.add_edge — public typed-edge write seam (EDGE-01)"
  - "D-07 silent-no-op-on-missing-endpoint pinned by test on BOTH backends"
  - "InMemoryBackend.add_edge MATCH-MERGE endpoint-existence parity with ladybug"
affects:
  - "src/doxastica/core.py (MemoryCore.add_edge added; get_impact still pending in 05-03)"
  - "src/doxastica/backends/memory.py (add_edge endpoint-existence guard)"
  - "tests/test_cascade.py (NEW — add_edge mechanism suite; 05-03 will extend)"
tech-stack:
  added: []
  patterns:
    - "Near-passthrough public method wrapping one backend primitive in exactly one unit_of_work (D-06)"
    - "Closed-EdgeType public seam; basedpyright-strict rejects raw strings at the boundary (T-05-04)"
    - "UUID stringification at the backend boundary (str(...)) to match stored STRING PKs"
key-files:
  created:
    - "tests/test_cascade.py"
  modified:
    - "src/doxastica/core.py"
    - "src/doxastica/backends/memory.py"
decisions:
  - "D-06 honored: add_edge is one backend call inside exactly one unit_of_work; idempotency left to the backend"
  - "D-07 honored: NO endpoint-existence raise in the core; missing endpoint is a SILENT NO-OP pinned by test"
  - "Rule 1: InMemoryBackend.add_edge now MATCH-MERGEs (silent no-op on missing endpoint) to stay a faithful oracle vs ladybug"
metrics:
  duration_min: 5
  completed: 2026-06-18
  tasks: 2
  files: 3
  tests_total: 152
---

# Phase 5 Plan 02: MemoryCore.add_edge (EDGE-01) Summary

`MemoryCore.add_edge(from_state_id, to_state_id, edge_type)` lays a generic typed edge as a one-call passthrough to the backend's idempotent `add_edge` inside exactly one `unit_of_work` (D-06), taking the closed `EdgeType` enum, with no endpoint-existence raise (D-07 silent no-op) — pinned by a mechanism suite green on both backends.

## What Was Built

- **`MemoryCore.add_edge` (core.py):** the public edge-creation seam. Body is a single `with self._backend.unit_of_work():` wrapping `self._backend.add_edge(edge_type, str(from_state_id), str(to_state_id))`. Signature matches `protocol.py:101-108` exactly. Driver-blind (no Cypher, no `ladybug` import). The closed `EdgeType` enum is the only layable type via this seam; `HAS_REVISION`/internal-`SUPERSEDES` wiring stays inside `_append_state`. `EdgeType` was added to the `doxastica.models` import.
- **`tests/test_cascade.py` (NEW):** add_edge mechanism suite — lays a typed edge (observed via `direction="out"` traverse from the dependent, plus a `direction="in"` cross-check that holds because 05-01 already landed the kwarg), idempotency (double-add ⇒ one edge), one positive case per generic `EdgeType` (SUPERSEDES/DEPENDS_ON/DERIVED_FROM), the D-07 silent-no-op pin, and an in-process both-backends structural-parity case. Parametrized across both backends via the `backend` fixture and the `_both_backends` loop.

## How It Works

`add_edge` adds nothing beyond the passthrough: idempotency (double-add ⇒ one edge) is already guaranteed by both backends, and there is no endpoint validation. Both UUIDs are stringified so they match the stored STRING PKs on the ladybug side (the established `_append_state` convention). `get_impact` (the cascade read surface) is deliberately NOT in this plan — 05-03 extends `core.py` and `tests/test_cascade.py` in the next wave; the additions here are scoped to a dedicated `# --- Edge operations` section so 05-03 slots in cleanly with no conflict.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] InMemoryBackend.add_edge diverged from ladybug on a missing endpoint**
- **Found during:** Task 2 (the D-07 silent-no-op test failed only on the in-memory backend).
- **Issue:** `InMemoryBackend.add_edge` unconditionally appended `dst` to its adjacency dict regardless of whether the endpoint nodes existed. `add_edge(real, ghost)` therefore laid a dangling edge to a phantom key; an out-traverse from `real` reached a propless `{}` row (`KeyError: 'state_id'`). Ladybug's `MATCH ... MERGE` matches nothing on a missing endpoint and lays no edge — so the in-memory oracle was UNfaithful to the reference backend on the documented D-07 behaviour, breaking the parity contract the conftest/parity suite exists to enforce.
- **Fix:** `InMemoryBackend.add_edge` now returns early (silent no-op) when either endpoint is absent from `_node_index`, mirroring ladybug's MATCH-MERGE. No raise is added (D-07 is preserved — the core adds no validation; the backend simply MERGEs nothing).
- **Scope note:** `memory.py` was not in this plan's declared `<files>` (`core.py` + `test_cascade.py`), but the divergence was newly exposed by this plan's D-07 pin and is required for the plan's acceptance criterion (D-07 green on BOTH backends). All pre-existing `add_edge` tests pre-create their endpoints via `upsert_node`, so the guard is non-regressive (verified: full suite 152 passed).
- **Files modified:** `src/doxastica/backends/memory.py`
- **Commit:** `2f5d960`

**2. [Rule 1 - Bug] Both-backends parity test compared independently-minted state_ids**
- **Found during:** Task 2 (`test_add_edge_idempotency_both_backends_agree` failed comparing raw ids).
- **Issue:** the case built real beliefs on each backend with core-minted UUID7 `state_id`s, so the raw reached-id literals differ by construction — comparing them across the two independently-built graphs is wrong (the existing parity tests use shared literal ids like `"A"`/`"B"` precisely to avoid this).
- **Fix:** the case now compares the edge STRUCTURE (the dependent reaches exactly its single dependency) rather than raw ids.
- **Files modified:** `tests/test_cascade.py`
- **Commit:** `2f5d960`

## TDD Gate Compliance

- RED: `60b3cee` — `test(05-02): add failing add_edge mechanism tests` (13 failing, `AttributeError: 'MemoryCore' object has no attribute 'add_edge'`).
- GREEN: `2f5d960` — `feat(05-02): implement MemoryCore.add_edge passthrough`. All 13 add_edge tests pass on both backends; full suite 152 passed; basedpyright strict 0 errors; ruff clean.
- No REFACTOR commit needed.

## Verification

- `uv run pytest tests/test_cascade.py -q -k add_edge` — 13 passed (both backends).
- `uv run pytest -q` — 152 passed (no regression).
- `uv run basedpyright src tests` — 0 errors, 0 warnings.
- `uv run ruff check src/doxastica tests` — All checks passed.
- `uv run pytest tests/test_import_purity.py -q` — 7 passed (driver-blindness preserved).

## Known Stubs

None. `get_impact` is intentionally deferred to plan 05-03 (not a stub — it is out of this plan's scope per CONTEXT/PLAN; the `protocol.py` signature already exists and 05-03 implements the body).

## Self-Check: PASSED
- FOUND: src/doxastica/core.py (MemoryCore.add_edge)
- FOUND: src/doxastica/backends/memory.py (endpoint-existence guard)
- FOUND: tests/test_cascade.py
- FOUND commit: 60b3cee (RED)
- FOUND commit: 2f5d960 (GREEN)
