---
phase: 03-append-only-revision-spine-keystone
reviewed: 2026-06-16T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/doxastica/__init__.py
  - src/doxastica/backends/ladybug.py
  - src/doxastica/core.py
  - src/doxastica/models.py
  - tests/test_backend_parity.py
  - tests/test_invariants.py
  - tests/test_revision_spine.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-06-16
**Depth:** standard
**Status:** issues_found

## Summary

This is a RE-REVIEW of the Phase-3 append-only revision-spine keystone. All five prior
warnings (WR-01..WR-05) are confirmed FIXED:

- **WR-01** (vacuity no-op): `contract` now probes `_current` BEFORE `_ensure_scope`
  (`core.py:316-319`), so a vacuous contract leaks no `Scope` write. Confirmed.
- **WR-02** (exact-equality invariant): `chain_is_immutable` now asserts
  `total == self._state_count` (`test_invariants.py:311`). Confirmed.
- **WR-03** (`traverse` edge-type validation): empty-set + unknown-type guards added
  (`ladybug.py:353-357`). Confirmed.
- **WR-04** (key interpolation): `_validate_identifier` now guards every interpolated
  prop/where KEY in `upsert_node` (`ladybug.py:248`) and `match_nodes` (`ladybug.py:306`).
  Confirmed.
- **WR-05** (`var_length_extend_max_depth` restore): the cap is lifted only when
  `bound > _DEFAULT_HOP_CAP` and restored in a `finally` (`ladybug.py:389-397`). Confirmed.

The core correctness story holds up under fresh tracing: the derived-current ordering key
matches the documented big-endian byte-order contract (UUID string form is fixed-width
lowercase hex, so `str` lexicographic order == byte order); `_current` correctly takes the
max over ALL statuses and returns `None` on a retracted tail; the base64-over-JSON codec
defeats the ladybug brace-coercion hazard and `contract` copies the stored token verbatim;
and no edge/node delete primitive is composed anywhere (append-only by construction).

The adversarial re-pass surfaced **two new WARNINGs** the prior review missed — one a real
parity defect between the two shipping backends (`match_nodes` boolean coercion), one a
latent injection surface left behind precisely because WR-03's fix was applied unevenly. Of
the four prior INFO items, **all four remain open** (none were addressed by the WR fix
commits); they are re-stated below.

## Warnings

### WR-01 (new): `traverse`'s `max_depth=0` fast-path interpolates `rels` AFTER skipping the WR-03 guard order — but its own pattern is still unvalidated relative to the namespace-only discipline... and worse, the boolean `match_nodes` parity gap

(See WR-02 for the boolean issue — split out for clarity. This entry is the rel-pattern
hardcode.)

**File:** `src/doxastica/backends/ladybug.py:378`
**Issue:** The main traversal Cypher hardcodes the start-node PK column as the literal
`state_id`:

```python
f"MATCH p=(a:{node} {{state_id: $start}})-[:{rels}* ACYCLIC 1..{bound}]->(b:{node}) "
```

while the rest of the adapter (CR-01 discipline) is careful to read every PK column from
`_PK_BY_LABEL` so the DDL and the query keys cannot diverge. `traverse` is `BeliefState`-only
today (`node = f"{ns}_BeliefState"`), so the literal `state_id` happens to equal
`_PK_BY_LABEL["BeliefState"]` and the query is correct. But this is the one place in the
adapter that re-introduces the exact divergence hazard CR-01 was built to eliminate: if the
`BeliefState` PK column is ever renamed in `_PK_BY_LABEL` / the DDL, the `max_depth=0`
fast-path (`ladybug.py:367`, which DOES use `_PK_BY_LABEL['BeliefState']`) and the main
path (line 378, which hardcodes `state_id`) silently disagree. The `RETURN b.state_id`,
`WHERE b.state_id <> $start`, and the `min(length(p))` projection all share the same
hardcode. This is a latent correctness/maintainability defect, not yet a live bug.
**Fix:** Read the PK once and interpolate it, matching the fast-path and CR-01:
```python
pk = _PK_BY_LABEL["BeliefState"]
cypher = (
    f"MATCH p=(a:{node} {{{pk}: $start}})-[:{rels}* ACYCLIC 1..{bound}]->(b:{node}) "
    f"WHERE b.{pk} <> $start "
    f"WITH b, min(length(p)) AS d "
    f"RETURN b.{pk} AS state_id, d, "
    f"(d = {bound} AND EXISTS {{ MATCH (b)-[:{rels}]->() }}) AS at_frontier"
)
```

### WR-02 (new): `match_nodes` boolean predicates diverge between the two shipping backends

**File:** `src/doxastica/backends/ladybug.py:303-309`, `src/doxastica/core.py:134`, `tests/test_backend_parity.py:209`
**Issue:** `get_or_create_scope` / `_ensure_scope` write `is_world` as a real Python `bool`
into the `Scope` node (`core.py:137,152`). The ladybug `Scope` table declares `is_world
BOOLEAN` (`ladybug.py:192`). The in-memory oracle stores the props dict verbatim, so its
`match_nodes("Scope", {"is_world": True})` compares Python `True == True`. On ladybug,
`is_world` round-trips through a `BOOLEAN` column and is `$param`-bound as a Python `bool` —
this happens to work for `bool`, but the contract is unverified: `match_nodes`'s `where`
values are documented as "exact-match," and the parity suite only proves boolean matching
with the directly-inserted literal in `test_scope_upsert_parity` (`test_backend_parity.py:209`),
NOT through the `MemoryCore.get_or_create_scope` path that is the only production writer of
`is_world`. More importantly, `get_or_create_scope` NEVER round-trips the stored `is_world`
back — it re-derives `is_world = scope_id == WORLD_SCOPE_ID` (`core.py:133,139`) and ignores
the column. So the stored `is_world` column is **write-only dead data**: nothing in the core
ever reads it back, and the only consumer that filters on it is the parity test. If a backend
coerced the boolean on store/retrieve (the very Pitfall-4 hazard the codec defends for
`value`), the core would not notice because it never reads the column — but a future
`query_scope`/`get_scope_at` that DOES filter `match_nodes("Scope", {"is_world": ...})` would
inherit an untested boolean-coercion parity risk.
**Fix:** Either (a) add a parity test that filters `match_nodes("Scope", {"is_world": False})`
AND `{"is_world": True}` through both backends after writing via `MemoryCore.get_or_create_scope`
(not the bare `_scope` helper), pinning the boolean round-trip on the production write path; or
(b) since `is_world` is re-derived and never read, drop it from the stored props entirely and
document `is_world` as a pure function of `scope_id` — removing the dead column and the latent
coercion surface at once. Option (b) is the stronger fix and aligns with the existing
"derive `is_world`, do not trust col" comment (`core.py:139`).

## Info

### IN-01: `add_edge` accepts `props` it silently discards (UNRESOLVED from prior review)

**File:** `src/doxastica/backends/ladybug.py:262` and `src/doxastica/backends/memory.py:76`
**Issue:** Both adapters accept `props: dict[str, Any] | None` (with `# noqa: ARG002`) and
discard it entirely. A caller passing edge properties gets no error and no stored data — a
silent no-op that could mask a future bug when consumer-facing edges (Phase 4+) start
carrying properties. Still open after the WR fix commits.
**Fix:** Until edge props are implemented, reject non-empty `props` (`raise
NotImplementedError` or assert falsy) rather than dropping them silently.

### IN-02: `contract` and `_append` duplicate the node + edge-laying body (UNRESOLVED)

**File:** `src/doxastica/core.py:243-254` and `src/doxastica/core.py:321-331`
**Issue:** The `props` construction, `upsert_node("BeliefState", ...)`,
`add_edge("HAS_REVISION", ...)`, and `add_edge("SUPERSEDES", new, prior)` sequence is
duplicated between `_append` and `contract`, differing only in `status` and whether the value
is re-encoded (`_append`: `_encode_value(value)`) vs copied verbatim (`contract`:
`prior["value"]`). The two copies can drift — e.g. a future fix to the `HAS_REVISION` wiring
applied to only one. Still open.
**Fix:** Extract a shared `_append_state(scope_id, belief_id, encoded_value,
source_event_id, status, prior)` helper composing the node + `HAS_REVISION` + optional
`SUPERSEDES`; `_append` passes the encoded value, `contract` passes the verbatim stored token.

### IN-03: `_current` and `get_revision_chain` duplicate the ordering key inline (UNRESOLVED)

**File:** `src/doxastica/core.py:178` and `src/doxastica/core.py:344`
**Issue:** The ordering contract
`lambda s: (str(s["source_event_id"]), str(s["state_id"]))` is written out in two places (the
`max` in `_current` and the `sort` in `get_revision_chain`). The docstrings repeatedly stress
this is "the ONE place the ordering contract lives," yet it lives in two. A change to the
tiebreak in one and not the other would silently desynchronise `_current` from
`get_revision_chain` — the exact agreement the keystone invariant relies on. Still open.
**Fix:** Define a module-level
`def _order_key(s): return (str(s["source_event_id"]), str(s["state_id"]))` and use it in both
call sites.

### IN-04: `contract` ends with a redundant trailing `return None` (UNRESOLVED)

**File:** `src/doxastica/core.py:332`
**Issue:** The trailing `return None` at the end of the `unit_of_work` block is redundant (the
function returns `None` implicitly). Purely stylistic — the explicit returns do document the
always-`None` contract, so this is borderline. Still open; no behavioral impact.
**Fix:** Optional — drop the trailing `return None` or keep for documentation symmetry.

---

_Reviewed: 2026-06-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
