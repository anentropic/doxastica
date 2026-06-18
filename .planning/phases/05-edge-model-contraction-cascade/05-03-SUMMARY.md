---
phase: 05-edge-model-contraction-cascade
plan: 03
subsystem: core-cascade-read
tags: [EDGE-02, get_impact, contraction-cascade, D-01, D-02, D-03, D-04, D-05, hydration-gap, oracle-parity]
requires:
  - "BackendPort.traverse keyword-only direction='in'|'out' (Plan 05-01)"
  - "MemoryCore.add_edge public typed-edge write seam (Plan 05-02)"
  - "BackendPort.match_nodes (parity-tested exact-prop fetch, Phase 2)"
  - "MemoryCore._hydrate value-decode boundary + _order_key (Phase 3/4)"
  - "ImpactResult / BeliefState / EdgeType closed models (Phase 1)"
provides:
  - "MemoryCore.get_impact — the bounded, cycle-safe contraction-cascade read (EDGE-02)"
  - "_CASCADE_EDGE_TYPES = frozenset({DEPENDS_ON, DERIVED_FROM}) — the ONE place the cascade edge set is defined (D-03, SUPERSEDES excluded)"
  - "hydration-gap closure (Option A): re-fetch each reached state_id via match_nodes -> _hydrate, byte-identical on both backends"
  - "get_impact mechanism + property tests (dependents-only, excludes-start, cycle-termination, exact-reachable-within-depth, frontier/truncated, SUPERSEDES-excluded + DERIVED_FROM-included, full-hydration parity)"
affects:
  - "src/doxastica/core.py (MemoryCore.get_impact + _CASCADE_EDGE_TYPES added; ImpactResult import)"
  - "tests/test_cascade.py (EXTENDED with the get_impact suite alongside 05-02 add_edge tests)"
  - "07-conformance-suite (the AGM Relevance/Core-Retainment POSTULATE tests run against this mechanism)"
tech-stack:
  added: []
  patterns:
    - "Compose port primitive (traverse direction='in') -> re-fetch props via match_nodes -> _hydrate -> frozen ImpactResult (mirrors query_scope's compose->process->hydrate body)"
    - "Hydration-gap closure: NEVER hydrate ImpactResult.reached directly from traverse rows (ladybug returns state_id-only); re-fetch full props per reached state_id (Option A)"
    - "Pure read = NO unit_of_work (mirror query_scope); driver-blind = core passes literal direction='in', both backends own the arrow flip"
    - "Cross-backend parity over independently-minted state_ids: compare belief_id-normalized shape, not raw ids (the 05-02 parity lesson reapplied)"
key-files:
  created: []
  modified:
    - "src/doxastica/core.py"
    - "tests/test_cascade.py"
decisions:
  - "D-01 honored: get_impact(X) returns X's transitive DEPENDENTS (downstream), not what X depends on"
  - "D-02 honored: reached EXCLUDES start; truncated = len(frontier) > 0; depth=None => full closure, empty frontier, truncated=False"
  - "D-03 honored: cascade edge set is EXACTLY {DEPENDS_ON, DERIVED_FROM} — SUPERSEDES excluded by construction, DERIVED_FROM required (pinned by tests)"
  - "D-04/D-05 honored: walk runs AGAINST the arrows via the literal direction='in'; the core owns no direction logic"
  - "RESEARCH Option A adopted: hydration gap closed by re-fetching reached props via match_nodes (Option B — widening traverse return — rejected)"
metrics:
  duration_min: 9
  completed: 2026-06-18
  tasks: 2
  files: 2
  tests_total: 165
---

# Phase 5 Plan 03: MemoryCore.get_impact (EDGE-02) Summary

`MemoryCore.get_impact(belief_state_id, depth=None)` is the bounded, cycle-safe contraction-cascade read: it composes `traverse(direction="in")` over `_CASCADE_EDGE_TYPES = {DEPENDS_ON, DERIVED_FROM}` (D-03), re-fetches each reached `state_id`'s full props via `match_nodes` to close the hydration gap (RESEARCH Option A), and packages the result as the locked `ImpactResult(reached, frontier, truncated)` (D-02) — driver-blind, pure-read, and byte-identical across both backends.

## What Was Built

- **`MemoryCore.get_impact` (core.py):** the EDGE-02 cascade read. Body:
  1. `traverse(str(belief_state_id), _CASCADE_EDGE_TYPES, depth, direction="in")` — walks AGAINST the stored arrows (X's dependents, D-01/D-04/D-05); `depth=None` ⇒ full closure (D-02).
  2. **Hydration-gap closure (RESEARCH Option A / Pitfall 1):** for each reached row, re-fetch full props via `self._backend.match_nodes("BeliefState", {"state_id": <sid>})`, then `_hydrate`. This is the ONLY robust path because the ladybug `traverse` returns `state_id`-only rows while in-memory returns full props — direct hydration would `KeyError` on ladybug and diverge across backends. A re-fetch returning empty is skipped defensively (no raise).
  3. Sort the hydrated props by the ONE `_order_key` contract for deterministic `reached` ordering (mirrors `query_scope`'s final sort; `reached` order is non-contractual per BACK-04 §5, but determinism keeps parity stable).
  4. Return `ImpactResult(reached=tuple(...), frontier=frozenset(UUID(...) for ...), truncated=len(frontier) > 0)`. `reached` excludes the start by construction (the port `traverse` contract already excludes it, D-02). The frontier handles are coerced str→`UUID` for the typed `frozenset[UUID]` field.
  Pure read: NO `unit_of_work` (mirrors `query_scope`). Driver-blind (D-02): no Cypher, no `ladybug` import, no `direction` logic — the core passes the literal `direction="in"`; both backends own the flip.
- **`_CASCADE_EDGE_TYPES` (core.py, module-level):** `frozenset({EdgeType.DEPENDS_ON, EdgeType.DERIVED_FROM})` — the ONE place the cascade edge set is defined. `SUPERSEDES` is excluded by construction (it is the internal revision-spine edge); `DERIVED_FROM` is required (NVM invalidation edges are its specialisations). `ImpactResult` was added to the `doxastica.models` import.
- **`tests/test_cascade.py` (EXTENDED):** the `get_impact` mechanism + property suite, added alongside the 05-02 `add_edge` tests (no clobber). 13 cases spanning: dependents-only/asymmetric parity (the direction guard), DERIVED_FROM-included, excludes-start, SUPERSEDES-excluded, full-closure parity, depth-bounded frontier/truncated parity, depth=0 parity, Hypothesis cycle-termination, Hypothesis exact-reachable-within-depth, and full-hydration cross-backend parity (the hydration-gap guard asserting all six BeliefState fields are populated and identical).

## How It Works

The cascade is pure composition over already-built substrate. The single non-obvious move is the hydration gap: the two backends' `traverse` return shapes differ (ladybug `state_id`-only vs in-memory full props), so `reached` is re-hydrated by re-fetching props per `state_id` through the already-parity-tested `match_nodes` — making the hydrated `reached` byte-identical on both backends regardless of what `traverse` itself returns. The `frontier` (boundary `state_id` handles, str on both backends) drives `truncated = len(frontier) > 0` directly, and is empty exactly when the walk ran to closure (`depth=None`), satisfying D-02 without recomputation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cross-backend parity tests compared independently-minted state_ids**
- **Found during:** Task 2 (GREEN). Four `_both_backends()` comparison tests (`dependents_only`, `full_closure`, `depth_bounded_frontier`, `depth_zero`) failed their final `results["memory"] == results["ladybug"]` assertion.
- **Issue:** each backend mints its own UUID7 `state_id`s for the same logical graph (the core mints them per construction), so comparing RAW reached/frontier `state_id`s across two independently-built backends is meaningless by construction — exactly the parity lesson the 05-02 SUMMARY already recorded (its Deviation 2). The per-backend raw-id assertions were correct; only the cross-backend literal comparison was wrong.
- **Fix:** added a `_impact_belief_ids` helper that normalizes `reached` to sorted `belief_id`s (each belief has a stable literal id `ba`/`bb`/`b0`/`b1`/…), and rewrote the four cross-backend assertions to compare the belief_id-normalized shape (plus `truncated` and `len(frontier)`). Each test KEEPS its per-backend raw-`state_id` literal assertions (which correctly pin the exact mechanism on each backend). No production code changed for this fix — it was a test-authoring correction.
- **Files modified:** `tests/test_cascade.py`
- **Commit:** `a7f016e`

**2. [Rule 1 - Bug] `frontier=frozenset(frontier)` was `frozenset[UUID | str]`, not `frozenset[UUID]`**
- **Found during:** Task 2 (GREEN). basedpyright strict flagged the `ImpactResult(frontier=...)` argument: the port `traverse` returns `frozenset[UUID | str]` (the frontier carries opaque `state_id` handles, str on both backends), but `ImpactResult.frontier` is `frozenset[UUID]`.
- **Fix:** coerce each frontier handle str→`UUID` at the boundary: `frozenset(uuid.UUID(str(f)) for f in frontier)` — the same str→UUID seam pydantic applies to the hydrated reached states. (`uuid` already imported at module top.)
- **Files modified:** `src/doxastica/core.py`
- **Commit:** `a7f016e`

## TDD Gate Compliance

- **RED:** `bba41be` — `test(05-03): add failing get_impact mechanism + property tests`. 13 `get_impact` cases failed with `AttributeError: 'MemoryCore' object has no attribute 'get_impact'` (the unimplemented method), exactly the expected RED signal — no test passed unexpectedly.
- **GREEN:** `a7f016e` — `feat(05-03): implement MemoryCore.get_impact (EDGE-02 cascade)`. All 26 `tests/test_cascade.py` cases pass on both backends; full suite 165 passed; basedpyright strict 0 errors; ruff clean.
- No REFACTOR commit needed.

## Verification

- `uv run pytest tests/test_cascade.py -q` — 26 passed (13 add_edge from 05-02 + 13 get_impact, both backends).
- `uv run pytest -q` — 165 passed (no regression; Plan-01 `traverse` callers + all prior phases unbroken).
- `uv run basedpyright src tests` — 0 errors, 0 warnings, 0 notes.
- `uv run ruff check src/doxastica tests` — All checks passed.
- `uv run pytest tests/test_import_purity.py -q` — 7 passed (driver-blindness preserved; no `ladybug` leaked into `core.py`).

## Threat Model Compliance

- **T-05-05 (cascade walks the WRONG direction, mitigate):** `get_impact` passes `direction="in"` explicitly; the asymmetric dependents-only parity test (`get_impact(A) == {B}`, `get_impact(B) == {}` where B depends on A) catches a successor/predecessor swap — under-reaching is the guarded failure mode (RESEARCH Pitfall 2). PASS.
- **T-05-06 (reverse traverse leaking a changed hop cap, mitigate):** inherited from Plan 01 — the ladybug cap-raise/restore is direction-agnostic and wraps both directions; `get_impact` adds no new state-leak surface. No new code here touches the cap. PASS.
- **T-05-SC (installs, accept):** no package installs this phase.

## Known Stubs

None. `get_impact` is fully wired (composes `traverse` + `match_nodes` + `_hydrate`); the AGM Relevance/Core-Retainment POSTULATE tests are deliberately Phase 7, not a stub — Phase 5 builds the MECHANISM those postulates are tested against (per CONTEXT/PLAN scope).

## Threat Flags

None. `get_impact` is a deterministic read over an embedded, LLM-free core; the only interpolation surface (`direction`) is a closed `Literal` owned by the backends (Plan 01), unchanged here. No new network endpoint, auth path, file access, or schema surface.

## Self-Check: PASSED

- FOUND: src/doxastica/core.py (MemoryCore.get_impact + _CASCADE_EDGE_TYPES)
- FOUND: tests/test_cascade.py (get_impact suite)
- FOUND commit: bba41be (RED)
- FOUND commit: a7f016e (GREEN)
