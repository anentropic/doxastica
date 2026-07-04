---
phase: 03-append-only-revision-spine-keystone
fixed_at: 2026-06-16T00:00:00Z
review_path: .planning/phases/03-append-only-revision-spine-keystone/03-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-06-16
**Source review:** .planning/phases/03-append-only-revision-spine-keystone/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (WR-01, WR-02, IN-01, IN-02, IN-03, IN-04)
- Fixed: 6
- Skipped: 0

All fixes were applied in an isolated git worktree on branch `gsd-reviewfix/03-22244`.
After all fixes the FULL suite is green on BOTH backends
(`uv run --extra ladybug pytest -q` → 106 passed), basedpyright-strict reports
0 errors/0 warnings, and `ruff check .` + `ruff format --check .` are clean.

## Fixed Issues

### WR-01: `traverse` hardcodes the `state_id` PK literal in the main traversal Cypher

**Files modified:** `src/doxastica/backends/ladybug.py`
**Commit:** ad2f33a
**Status:** fixed
**Applied fix:** Replaced the four hardcoded `state_id` occurrences in the main
(`max_depth>0`) traversal Cypher with `pk = _PK_BY_LABEL["BeliefState"]`, matching the
`max_depth=0` fast-path and the CR-01 single-source-of-truth discipline. The MATCH
start-node key, the `WHERE b.{pk} <> $start` filter, and the `RETURN b.{pk}` projection
all read the PK from `_PK_BY_LABEL`. The RETURN keeps `AS state_id` as the output column
alias so the downstream `r["state_id"]` unpacking is unchanged. Parameter-safe: the
interpolated identifier is a fixed internal constant; `$start` stays `$param`-bound.

### WR-02: `match_nodes` boolean `is_world` round-trip untested on the production write path

**Files modified:** `tests/test_backend_parity.py`
**Commit:** fe50029
**Status:** fixed
**Applied fix:** Took the NON-invasive option (a) from the guardrail. Added
`test_is_world_boolean_round_trips_production_write_path`, which writes a world scope
(`is_world=True`) and a non-world scope (`is_world=False`) through the PRODUCTION writer
`MemoryCore.get_or_create_scope` on BOTH backends (via the existing in-process
`_both_backends` helper), then filters `match_nodes("Scope", {"is_world": True})` AND
`{"is_world": False}` and asserts byte-identical results across backends. This pins the
`BOOLEAN` round-trip on the only production code path that writes `is_world`, so a future
`query_scope`/`get_scope_at` filtering on `is_world` inherits a TESTED parity rather than
the latent coercion surface the reviewer flagged.

Option (b) (drop the stored `is_world` column / change the `Scope` model) was deliberately
NOT taken: it would mutate the FROZEN Phase-1 taxonomy (`Scope(scope_id, is_world)`, D-02),
which is out of code-review scope. The reviewer's secondary suggestion in option (a) —
making `get_or_create_scope` read the stored column back — was also NOT applied, because it
would contradict the existing deliberate Pitfall-4 defense (`core.py`: "derive is_world, do
not trust col"): trusting a coerced column is exactly what that comment guards against. The
added test covers the stored-column parity without weakening the derive-don't-trust
contract, which is the behavior-preserving intersection of the guardrail's allowed options.

### IN-01: `add_edge` silently discards the `props` it accepts

**Files modified:** `src/doxastica/backends/ladybug.py`, `src/doxastica/backends/memory.py`
**Commit:** 50930fc
**Status:** fixed
**Applied fix:** Both adapters now `raise NotImplementedError` on a non-empty `props`
(`if props:`) instead of silently dropping it, and the `# noqa: ARG002` suppressions were
removed (the param is now used). Edge properties remain unimplemented (no Phase-3 edge
carries any), but the silent no-op that could mask a future consumer-facing edge is gone.
No existing caller passes `props` (`_append`/`contract`/`_append_state` call `add_edge`
without props), so no current behavior changes; the full suite stays green.

### IN-02: `contract` and `_append` duplicate the node + edge-laying body

**Files modified:** `src/doxastica/core.py`
**Commit:** bf8f1ff
**Status:** fixed: requires human verification
**Applied fix:** Extracted `_append_state(scope_id, belief_id, encoded_value,
source_event_id, status, prior)` composing the `BeliefState` props build + `upsert_node` +
`HAS_REVISION` hub edge + optional `SUPERSEDES new → prior` + hydrate-and-return. `_append`
now passes `_encode_value(value)`; `contract` passes the prior STORED token VERBATIM
(Pitfall 2). The caller still owns everything that genuinely differs (the enclosing
`unit_of_work`, the scope/`Belief` materialization order, the vacuity probe, how `prior` is
computed), so the helper is behavior-preserving for both sites — in particular `contract`
still does NOT upsert a `Belief` node (kept out of the helper) and still lays `SUPERSEDES`
(its `prior` is always non-`None` after the vacuity check, so the helper's
`if prior is not None` branch always fires there). Flagged for human verification because
it is a logic-touching refactor of the keystone write path; the full suite (106 tests,
both backends) passing is the primary evidence behavior is preserved.

### IN-03: `_current` and `get_revision_chain` duplicate the ordering key inline

**Files modified:** `src/doxastica/core.py`
**Commit:** ead691c
**Status:** fixed
**Applied fix:** Added a module-level
`_order_key(state) -> (str(state["source_event_id"]), str(state["state_id"]))` and use it
in both the `_current` `max(..., key=_order_key)` and the `get_revision_chain`
`states.sort(key=_order_key)`. The helper is byte-for-byte equivalent to the two inlined
lambdas, so the ordering contract is genuinely centralized in one place (matching the
docstrings' "the ONE place the ordering contract lives") without changing the selection
behavior.

### IN-04: `contract` ends with a redundant trailing `return None`

**Files modified:** `src/doxastica/core.py`
**Commit:** bf8f1ff
**Status:** fixed
**Applied fix:** Resolved as a byproduct of the IN-02 `contract` rewrite — the trailing
`return None` at the end of the `unit_of_work` block was removed when the body was replaced
by the `_append_state` delegation. The meaningful early `return None` on the vacuity branch
is retained. The docstring's "Always returns `None`" remains accurate (implicit `None`).
Committed together with IN-02 (same file, same atomic rewrite of the `contract` body).

---

_Fixed: 2026-06-16_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
