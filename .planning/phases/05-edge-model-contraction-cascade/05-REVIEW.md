---
phase: 05-edge-model-contraction-cascade
reviewed: 2026-06-18T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/doxastica/ports.py
  - src/doxastica/backends/memory.py
  - src/doxastica/backends/ladybug.py
  - src/doxastica/core.py
  - tests/test_backend_parity.py
  - tests/test_cascade.py
  - docs/backend-contract.md
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-06-18T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 5 adds a keyword-only `direction: Literal["in","out"]="out"` parameter to the
`BackendPort.traverse` primitive (in-memory reverse adjacency `_in_edges`, a 3-site arrow flip
in the ladybug Cypher), the public `MemoryCore.add_edge` passthrough (EDGE-01), and
`MemoryCore.get_impact` (EDGE-02) which composes `traverse(direction="in")` over
`{DEPENDS_ON, DERIVED_FROM}` and closes a hydration gap by re-fetching reached `state_id`s via
`match_nodes`.

The four flagged-priority concerns all hold up under tracing:

1. **Injection surface (CLEAN).** No untrusted text reaches the reverse-traversal Cypher. The
   `(lhs, rhs)` arrow pair is derived from fixed tuples keyed by the closed `Literal`; `rels` is
   validated member-by-member against `_EDGE_ENDPOINTS`; `bound` is a runtime-guarded `int`;
   `$start` stays `$param`-bound. The new direction interpolation stays inside the sanctioned-
   interpolation story.
2. **`direction` default (CLEAN).** All three sites (`ports.py:101`, `memory.py:123`,
   `ladybug.py:335`) default to `"out"`; the cross-phase contract is intact and every existing
   positional caller is untouched.
3. **Hydration re-fetch (CLEAN, correctness-wise).** `get_impact` re-fetches each reached
   `state_id` via the already-parity-tested `match_nodes` then `_hydrate`s, so both backends
   agree (the ladybug `{"state_id": ...}`-only rows and the in-memory full-prop rows converge).
4. **Cycle-safety (CLEAN).** In-memory uses the `seen` visited-set; ladybug uses `ACYCLIC`
   node-distinct + `min(length(p))`, which equals BFS min-depth for simple paths. The
   `test_get_impact_terminates_on_cycle` property test guards termination.

The frontier semantics were traced for the diamond, cycle, over-bound chain, and reverse-chain
graphs against the in-memory oracle and found byte-identical. No BLOCKER-class defects found.
The findings below are robustness/maintainability concerns plus one genuine cross-tenant config
hazard.

## Warnings

### WR-01: Reverse-traversal cap restore clobbers a tenant's non-default `var_length` ceiling

**File:** `src/doxastica/backends/ladybug.py:426-434`
**Issue:** `traverse` restores the connection-global `var_length_extend_max_depth` to the
literal `_DEFAULT_HOP_CAP` (30) in the `finally` block, not to whatever value the connection
held before the call. For an INJECTED tenant connection (`owns_conn=False`, R19) that had
deliberately set its own non-default cap (say 100), a single deep/full-closure `get_impact`
silently resets that tenant's cap to 30 — a side effect the port is supposed to be invisible
behind. Because `max_depth=None` compiles to `_DEPTH_CEILING` (1,000,000) which is always
`> 30`, the `lifted` branch fires on EVERY full-closure traverse, so this is the common path,
not an edge case. The docstring (WR-05) claims the tenant connection "is never left with a
changed ceiling," but it can be left with a *different* ceiling than it started with.
**Fix:** Read the prior value before raising and restore that, rather than the literal:
```python
# read the tenant's current cap, raise, restore the SAVED value (not the literal 30)
if lifted:
    prior_cap = self._read_var_length_cap()  # SHOW/CALL current_setting equivalent
    self._exec(f"CALL var_length_extend_max_depth={bound}")
try:
    rows = self._rows(self._exec(cypher, {"start": str(start)}))
finally:
    if lifted:
        self._exec(f"CALL var_length_extend_max_depth={prior_cap}")
```
If reading the current setting is not feasible on ladybug 0.17.1, document the contract that the
backend assumes the 30-hop default and require tenants not to mutate it — but the current code
silently assumes 30 without saying so at the seam.

### WR-02: `get_impact` re-fetch issues N+1 unbatched `match_nodes` round-trips with no atomic read scope

**File:** `src/doxastica/core.py:495-502`
**Issue:** The hydration-gap fix loops over every reached row and issues one
`match_nodes("BeliefState", {"state_id": ...})` per node, each a separate backend round-trip,
outside any `unit_of_work`. On the ladybug backend a wide cascade therefore reads each node in
its own auto-committed transaction. Because there is no read snapshot, a concurrent writer
(the single-writer model still permits a write between two of these reads) can make the
re-fetched set inconsistent with the `traverse` result the frontier was derived from — a node
present in `reached` (from `traverse`) could be re-fetched after an unrelated append, yielding a
`reached`/`frontier` pair that never existed at a single instant. This is a consistency gap, not
just a perf note (perf is out of v1 scope).
**Fix:** Either wrap the traverse + all re-fetches in a single read `unit_of_work` so they share
one serializable snapshot, or have `traverse` return enough props to hydrate directly (closing
the gap at the port rather than via N re-reads). Minimum viable fix:
```python
with self._backend.unit_of_work():
    reached_rows, frontier = self._backend.traverse(...)
    props = [m[0] for row in reached_rows
             if (m := self._backend.match_nodes("BeliefState", {"state_id": str(row["state_id"])}))]
```

### WR-03: `_DEPTH_CEILING = 1_000_000` compiles into a literal `*1..1000000` var-length pattern

**File:** `src/doxastica/backends/ladybug.py:79`, `:415`
**Issue:** `max_depth=None` ("full closure") is implemented by interpolating `_DEPTH_CEILING`
(1,000,000) into `[:{rels}* ACYCLIC 1..{bound}]`. The semantic result is correct (ACYCLIC caps
real path length at the node count), but it leans on the query planner to not pre-allocate or
pre-validate the literal upper bound, and it couples "full closure" to a magic constant that is
also fed to `var_length_extend_max_depth=1000000` (WR-01's always-lifted path). The comment
asserts "no real belief graph approaches a million deep" — that is an assumption about the
*caller's* graph baked into the storage adapter, and a graph that does approach it would silently
truncate at 1,000,000 hops with NO frontier entry (the `d = {bound}` frontier test would fire at
depth 1,000,000, not at the true graph boundary), i.e. silent under-report — the exact DATA-04
failure `frontier`/`truncated` exists to prevent.
**Fix:** Document the ceiling as a hard truncation limit and surface it: when `max_depth is None`
and any node is reached at exactly `_DEPTH_CEILING`, the result is NOT a true full closure and
should set `truncated`-equivalent semantics. Alternatively, raise `_DEPTH_CEILING` checking to an
explicit assertion, or use ladybug's genuine unbounded `*` form if available rather than a magic
literal that conflates "unbounded" with "a million."

## Info

### IN-01: `get_impact` silently drops a reached node that fails re-fetch, masking an invariant breach

**File:** `src/doxastica/core.py:500-501`
**Issue:** `if fetched:` skips a reached `state_id` whose `match_nodes` re-fetch returns nothing.
The comment calls this "defensive," but a reached node always exists as a graph node (traverse
only reaches real nodes via real edges), so an empty re-fetch is an *invariant violation*
(reached/store divergence) — silently dropping it hides the very parity bug the hydration-gap
guard exists to catch. A reviewer cannot tell a benign skip from a real backend divergence.
**Fix:** Replace the silent skip with an assertion (or raise) so a missing re-fetch fails loudly:
```python
if not fetched:
    raise RuntimeError(f"reached state_id {row['state_id']!r} has no stored node (store divergence)")
props.append(fetched[0])
```

### IN-02: Unknown `direction` value silently treated as `"out"` on both backends (MAY-raise never exercised)

**File:** `src/doxastica/backends/memory.py:143`, `src/doxastica/backends/ladybug.py:364`
**Issue:** Both backends use `... if direction == "in" else <out-form>`, so any runtime value
outside `{"in","out"}` (the `Literal` is only statically enforced) silently falls through to the
outgoing walk rather than raising. The port doc (`ports.py:122-124`, `backend-contract.md:60`)
says a backend MAY raise `ValueError` on out-of-set input; neither does. Parity is preserved
(both default to `"out"`), so this is not a bug, but the "validation surface" the docstring
advertises is not actually present, and a typo'd internal caller would get a wrong-direction walk
with no signal.
**Fix:** If the MAY-raise contract is intended as defense-in-depth, add an explicit guard at the
top of both `traverse` bodies:
```python
if direction not in ("in", "out"):
    raise ValueError(f"direction must be 'in' or 'out'; got {direction!r}")
```
Otherwise, soften the docstring claim so it does not advertise a guard that is not implemented.

### IN-03: `_in_edges` rescans every adjacency list per node (no reverse index) — documented, but unbounded

**File:** `src/doxastica/backends/memory.py:195-215`
**Issue:** `_in_edges` does an O(edges) linear scan of every `src -> [dst...]` adjacency for each
visited node, so a reverse `traverse` is O(nodes x edges). The docstring acknowledges this as
"acceptable per the D-05 discretion area for in-scope belief-graph sizes." Flagged as INFO only
(performance is out of v1 scope and the in-memory backend is the oracle, not the production hot
path), but recorded because it interacts with WR-02: the reverse cascade is quadratic on the
oracle and N+1 on ladybug, so neither backend has an efficient reverse walk. No fix required for
v1; note for a future reverse-index pass if cascade sizes grow.

---

_Reviewed: 2026-06-18T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
