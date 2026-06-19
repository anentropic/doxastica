---
phase: 05-edge-model-contraction-cascade
fixed_at: 2026-06-19T00:00:00Z
review_path: .planning/phases/05-edge-model-contraction-cascade/05-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 5: Code Review Fix Report

**Fixed at:** 2026-06-19T00:00:00Z
**Source review:** .planning/phases/05-edge-model-contraction-cascade/05-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (WR-01, WR-02, WR-03 — `critical_warning` scope; 0 critical, 3 info out of scope)
- Fixed: 3
- Skipped: 0

All fixes verified against the full suite (165 passed, unchanged) and basedpyright STRICT
(0 errors) after each commit. WR-01 and WR-03 were additionally probed empirically against an
in-memory ladybug 0.17.1 connection before committing.

## Fixed Issues

### WR-01: Reverse-traversal cap restore clobbers a tenant's non-default `var_length` ceiling

**Files modified:** `src/doxastica/backends/ladybug.py`
**Commit:** 956a5e9
**Applied fix:** Empirically verified that ladybug 0.17.1 DOES expose the live cap via
`CALL current_setting('var_length_extend_max_depth') RETURN *` (single row
`{'var_length_extend_max_depth': '<n>'}`, value as STRING; default `'30'`). Added a
`_read_var_length_cap()` helper that reads the connection's CURRENT cap and coerces to `int`
(falling back to `_DEFAULT_HOP_CAP` if ever unreadable). `traverse` now lifts the cap only when
the bound exceeds the connection's *current* value and restores that *saved prior value* in the
`finally` block — instead of the literal default `30`. An injected tenant (R19) that set its own
cap (e.g. 100) is now left EXACTLY as it started after a deep/full-closure traverse. Verified
empirically: tenant cap of 100 survives a `max_depth=None` traverse (previously clobbered to 30).
Updated the `_DEFAULT_HOP_CAP` comment to reflect restore-to-prior semantics. Stayed
`$param`-bound everywhere except the existing sanctioned int/identifier interpolation; no new
interpolation surface, public signatures unchanged.

### WR-02: `get_impact` re-fetch issues N+1 unbatched `match_nodes` round-trips with no atomic read scope

**Files modified:** `src/doxastica/core.py`
**Commit:** 94c2f00
**Applied fix:** Wrapped the `traverse` call and the per-reached-node `match_nodes` re-fetch loop
in a single `with self._backend.unit_of_work():` read scope so they share one serializable
snapshot (the minimum-viable fix from REVIEW.md). On ladybug this is one `BEGIN`/`COMMIT` with no
writes; the in-memory adapter snapshots on entry and (absent an exception) leaves state untouched
on exit, so a read-only block is safe on both backends (verified by reading `memory.py`'s
`unit_of_work`). Stayed fully driver-blind — composes only the existing `BackendPort` primitives
(`unit_of_work`, `traverse`, `match_nodes`), no `ladybug` import, no Cypher. `reached` still
excludes the start node and `truncated = len(frontier) > 0` is unchanged. `ImpactResult` shape and
the `direction="in"` literal are untouched.

### WR-03: `_DEPTH_CEILING = 1_000_000` compiles into a literal `*1..1000000` var-length pattern

**Files modified:** `src/doxastica/backends/ladybug.py`
**Commit:** 9e9d08f
**Applied fix:** Made the full-closure truncation honest per DATA-04. The traverse query already
returns per-node min depth `d`; added a guard that, when `max_depth is None` (full closure) and any
reached node's `d >= _DEPTH_CEILING`, raises `RuntimeError` rather than returning a million-hop
truncated set as if it were a complete closure. A FINITE `max_depth` continues to surface
truncation through the existing `at_frontier`/`frontier` channel (unchanged), so the guard is
scoped to the unbounded case only. Updated the `_DEPTH_CEILING` module comment and the `traverse`
docstring to document the ceiling as a hard truncation limit (not a true infinity). Verified
empirically the guard does NOT false-fire on normal graphs (full closure returns the complete set
with an empty frontier; `depth=1` still surfaces its frontier).

## Notes

- All three fixes are local to the reference backend / core composition and preserve every
  hard constraint: driver-blind core (no module-level `ladybug` import in `core.py`/`ports.py`),
  `$param`-bound Cypher except the sanctioned namespace/edge-type/int interpolation, pydantic as
  the only required runtime dep, basedpyright STRICT at 0 errors, append-only discipline, and the
  locked `direction` default / `ImpactResult` shape.
- The 3 Info findings (IN-01, IN-02, IN-03) were out of the `critical_warning` scope of this pass.

## Follow-up: Info findings (user-directed, 2026-06-19)

After the warning pass, IN-01 and IN-02 were fixed on explicit user request; IN-03 is deferred.

- **IN-01 — FIXED** (`src/doxastica/core.py`): `get_impact`'s re-fetch loop now RAISES
  `RuntimeError("… reached/store divergence")` when a reached `state_id` re-fetches empty, instead
  of the silent `if fetched:` skip — an empty re-fetch is an invariant breach (traverse only
  reaches real nodes), so it fails loud. Pinned by `test_get_impact_reached_store_divergence_raises`
  (monkeypatched `match_nodes`).
- **IN-02 — FIXED** (`src/doxastica/backends/memory.py`, `src/doxastica/backends/ladybug.py`): both
  `traverse` bodies now guard `if direction not in ("in","out"): raise ValueError(...)`, making the
  port's advertised MAY-raise validation surface real rather than silently falling through to the
  outgoing walk. Pinned by `test_traverse_rejects_unknown_direction` (both backends).
- **IN-03 — DEFERRED**: `_in_edges` O(nodes×edges) reverse scan on the in-memory oracle. Perf is
  out of v1 scope; the in-memory backend is the test oracle, not a production hot path. Logged for
  a future reverse-index pass.

Suite green at 168 passed (165 + 3 new tests), basedpyright STRICT 0 errors, ruff clean.

---

_Fixed: 2026-06-19T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
