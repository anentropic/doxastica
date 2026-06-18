# Phase 5: Edge Model & Contraction Cascade - Pattern Map

**Mapped:** 2026-06-18
**Files analyzed:** 7 (5 MODIFY source/doc, 2 test targets — 1 NEW, 1 EXTEND)
**Analogs found:** 7 / 7 (every touched file has an in-repo analog — this phase composes/edits, it does not greenfield)

> **Framing for the planner.** This is an EDIT phase. Four of five source/doc targets already
> contain the exact pattern to mirror (the existing `traverse` impls, `_append_state`'s
> backend-call body, the `query_scope` compose-and-hydrate body). The "analog" for each modify
> target is, in most cases, *the file itself* (the surrounding method) plus a sibling method that
> already shows the convention. Cite the line ranges below directly in each PLAN action.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/doxastica/ports.py` (MODIFY: `traverse` `direction` kwarg + docstring) | port / protocol (interface) | transform (graph-walk contract) | self — `BackendPort.add_edge` props-default kwarg `ports.py:78-86` | exact (in-file sibling) |
| `src/doxastica/backends/memory.py` (MODIFY: `traverse` direction routing + `_in_edges`) | backend adapter | transform (BFS graph traversal) | self — `traverse` `memory.py:109-144` + `_out_edges` `memory.py:166-176` | exact (mirror existing) |
| `src/doxastica/backends/ladybug.py` (MODIFY: `traverse` arrow-flip ×3) | backend adapter | transform (Cypher var-length traversal) | self — `traverse` `ladybug.py:330-416` | exact (arrow-flip in place) |
| `src/doxastica/core.py` (MODIFY: new `add_edge` + `get_impact` bodies) | service / engine | event-driven (cascade) + request-response (edge write) | self — `_append` `core.py:286-314` (uow+backend write) + `query_scope` `core.py:404-467` (compose→hydrate) | exact (in-file siblings) |
| `docs/backend-contract.md` (MODIFY: BACK-04 §2 `direction`) | config / contract doc | n/a | self — §2 `traverse` bullet `backend-contract.md:42-51` | exact |
| `tests/test_backend_parity.py` (EXTEND: reverse-direction parity cases) | test (parity) | transform | self — diamond/cycle/chain parity `test_backend_parity.py:84-201` | exact (extend existing) |
| `tests/test_cascade.py` (NEW: `get_impact`/`add_edge` mechanism + property tests) | test (mechanism + property) | event-driven | `tests/test_backend_parity.py` (`_both_backends`/`_reached_ids`) + `tests/test_invariants.py` (Hypothesis stateful idiom) | role-match (compose two existing test idioms) |

## Pattern Assignments

### `src/doxastica/ports.py` (port, transform) — add `direction` kwarg

**Analog:** the file itself. The existing `add_edge` shows the convention for a defaulted
trailing kwarg on a port method (`props: dict[...] | None = None`, `ports.py:78-86`). The
`traverse` signature + docstring to edit is `ports.py:96-111`.

**Current signature to extend** (`ports.py:96-111`):
```python
def traverse(
    self,
    start: UUID | str,
    edge_types: frozenset[EdgeType | str],
    max_depth: int | None,
) -> tuple[list[dict[str, Any]], frozenset[UUID | str]]:
    """
    The single generic graph-walk primitive — returns ``(reached, frontier)``.

    Follows only ``edge_types`` from ``start`` ... ``max_depth=None`` ⇒ full transitive
    closure with an empty frontier. ``get_impact`` and ``get_scope_at`` compose from this
    primitive (Phases 3+) — there is no separate query method.
    """
    ...
```

**Change (D-05):** add a keyword-only `direction: Literal["in", "out"] = "out"` after
`max_depth`. RESEARCH A3 recommends `Literal["in","out"]` (basedpyright-strict friendly,
self-documenting, lets backends `raise ValueError` at the type boundary for free). `Literal`
imports from `typing` (the module already imports `from typing import TYPE_CHECKING, Any,
Protocol` at `ports.py:47` — add `Literal`). Extend the docstring: `"out"` (default) follows
edges FROM `start`; `"in"` follows edges INTO `start` (the dependency cascade). Default MUST be
`"out"` — RESEARCH Runtime State Inventory confirms the Phase-6 `get_scope_at` caller and the 9
existing positional parity calls (`test_backend_parity.py:120` etc.) stay green only with the
`"out"` default.

**Module-import discipline to preserve** (`ports.py:37-40` docstring): this module imports only
`contextlib`, `typing`, `uuid`, `doxastica.models` — never `ladybug`. Adding `Literal` keeps that
invariant.

---

### `src/doxastica/backends/memory.py` (backend, transform) — reverse-adjacency walk

**Analog:** the file's own `traverse` (`memory.py:109-144`) and `_out_edges` (`memory.py:166-176`).
Mirror `_out_edges` to make `_in_edges`, then route the BFS neighbour function on `direction`.

**Existing BFS core to keep UNCHANGED except the neighbour selector** (`memory.py:129-144`):
```python
while layer:
    nxt: list[tuple[str, int]] = []
    for node_key, depth in layer:
        for to_key in self._out_edges(node_key, edge_types):   # <-- becomes `neighbours(...)`
            if max_depth is not None and depth + 1 > max_depth:
                frontier.add(node_key)            # node_key sits at the bound, unexpanded
                continue
            if to_key in seen:
                continue
            seen.add(to_key)
            reached[to_key] = dict(self._node_index.get(to_key, {}))
            nxt.append((to_key, depth + 1))
    layer = nxt
return list(reached.values()), frozenset(frontier)
```

**Existing `_out_edges` to mirror** (`memory.py:166-176`):
```python
def _out_edges(self, node_key: str, edge_types: frozenset[EdgeType | str]) -> list[str]:
    """Successor node keys reachable from ``node_key`` over any of ``edge_types``."""
    out: list[str] = []
    for edge_type in edge_types:
        adjacency = self._edges.get(str(edge_type), {})
        out.extend(adjacency.get(node_key, ()))
    return out
```

**New `_in_edges` (RESEARCH Pattern 3, scan factoring — discretion area D-05).** Scan adjacency for
edges INTO `node_key`. Note the edge store is `self._edges: dict[str, dict[str, list[str]]]` =
`edge_type → {src → [dst,...]}` (`memory.py:50`):
```python
def _in_edges(self, node_key: str, edge_types: frozenset[EdgeType | str]) -> list[str]:
    """Predecessor node keys with an edge INTO ``node_key`` over any of ``edge_types``."""
    out: list[str] = []
    for edge_type in edge_types:
        adjacency = self._edges.get(str(edge_type), {})
        for src, dsts in adjacency.items():
            if node_key in dsts:
                out.append(src)
    return out
```
Then in `traverse`: `neighbours = self._in_edges if direction == "in" else self._out_edges`, and
call `neighbours(node_key, edge_types)` in the loop. Scan is O(edges)/node — fine for in-scope
belief-graph sizes (RESEARCH Open Q2; an index in `add_edge`/`_reindex` is the allowed alternative
but NOT required). If an index IS added, extend `_reindex` (`memory.py:178-182`) and the
snapshot/restore in `unit_of_work` (`memory.py:146-164`) to cover it.

**Model-blind discipline (`memory.py:16` docstring):** every primitive returns raw `list[dict]`; no
pydantic hydration in the backend. `_in_edges` returns `list[str]` keys, identical to `_out_edges`.

---

### `src/doxastica/backends/ladybug.py` (backend, transform) — arrow-flip ×3

**Analog:** the file's own `traverse` (`ladybug.py:330-416`). RESEARCH Pattern 3: the arrow flips in
exactly THREE places; everything else (`_DEPTH_CEILING`=1_000_000 `ladybug.py:79`, `_DEFAULT_HOP_CAP`=30
`ladybug.py:85`, the `bound==0` fast-path structure, `_EDGE_ENDPOINTS` validation `ladybug.py:362-366`,
`var_length_extend_max_depth` cap-raise/`finally`-restore `ladybug.py:405-413`) is direction-agnostic
and carries over verbatim.

**Signature to extend** (`ladybug.py:330-335`) — same `direction: Literal["in","out"] = "out"` kwarg
as the port.

**Flip 1 — `bound==0` out-edge probe** (`ladybug.py:372-385`), currently:
```python
f"MATCH (a:{node} {{{_PK_BY_LABEL['BeliefState']}: $start}})"
f"-[:{rels}]->() RETURN a LIMIT 1",
```
For `direction="in"`: `<-[:{rels}]-()`.

**Flip 2 + 3 — main var-length query AND its EXISTS frontier subquery** (`ladybug.py:393-399`),
currently:
```python
cypher = (
    f"MATCH p=(a:{node} {{{pk}: $start}})-[:{rels}* ACYCLIC 1..{bound}]->(b:{node}) "
    f"WHERE b.{pk} <> $start "
    f"WITH b, min(length(p)) AS d "
    f"RETURN b.{pk} AS state_id, d, "
    f"(d = {bound} AND EXISTS {{ MATCH (b)-[:{rels}]->() }}) AS at_frontier"
)
```
For `direction="in"`: main pattern becomes `(a {{...}})<-[:{rels}* ACYCLIC 1..{bound}]-(b:{node})`
and the EXISTS becomes `EXISTS {{ MATCH (b)<-[:{rels}]-() }}`. RESEARCH-recommended factoring: derive
the arrow pair ONCE — `lhs, rhs = ("<-", "-") if direction == "in" else ("-", "->")` — and interpolate
it. [VERIFIED docs.ladybugdb.com: reverse `<-[:REL* ACYCLIC 1..N]-` and incoming-EXISTS arrows are
valid Kùzu/ladybug Cypher.]

**Injection-safety story to stay inside (CLAUDE.md + `ladybug.py:356-366` comments):** `direction` is a
closed `Literal`, never caller-free-text, never a `$param` position — it is a fixed internal token like
the namespace (the ONE sanctioned interpolation). `$start` stays `$param`-bound; `edge_types` stays
`_EDGE_ENDPOINTS`-validated; `bound` stays the runtime-guarded interpolated int. Do NOT add a second
unvalidated interpolation surface.

**`reached` row shape stays `state_id`-only** (`ladybug.py:414`):
`reached = [{"state_id": r["state_id"]} for r in rows]`. Do NOT widen it to full props (RESEARCH
Option B, rejected — breaks parity literals). This is the source of the hydration gap (see core, below).

---

### `src/doxastica/core.py` (service, edge-write + cascade) — new `add_edge` + `get_impact`

**Analog A (for `add_edge`):** `_append` `core.py:286-314` and `_append_state` `core.py:247-284` — both
already show the "wrap a backend write in ONE `unit_of_work`, stringify UUIDs" convention. The
`add_edge` body is strictly simpler (one passthrough call).

`_append`'s uow + backend-call shape to mirror (`core.py:303-314`):
```python
with self._backend.unit_of_work():            # exactly one (CHAIN-03)
    self._ensure_scope(scope_id)
    self._backend.upsert_node("Belief", belief_id, {"belief_id": belief_id})
    prior = self._current(scope_id, belief_id)
    return self._append_state(...)
```
UUID-stringification precedent (`core.py:273-283`): every backend call stringifies — `str(state_id)`,
`str(source_event_id)`, `self._backend.add_edge("SUPERSEDES", str(state_id), prior["state_id"])`. The
new public `add_edge` MUST do the same so ids match the stored STRING PKs on ladybug.

**`MemoryCore.add_edge` body (Pattern 1, D-06/D-07).** Signature MUST match `protocol.py:101-108`
EXACTLY (do not change it): `(self, from_state_id: UUID, to_state_id: UUID, edge_type: EdgeType) -> None`.
```python
with self._backend.unit_of_work():  # exactly one atomic scope (D-06)
    # passthrough — port MERGE is idempotent + silently no-ops on a missing endpoint (D-07:
    # mechanism, not policy — the core adds NO endpoint-existence raise).
    self._backend.add_edge(edge_type, str(from_state_id), str(to_state_id))
```
Note: backend `add_edge` arg order is `(edge_type, from_id, to_id)` — see port `ports.py:78-86` and
the in-memory impl `memory.py:71-94`. The public method takes the closed `EdgeType` enum (only the
three generic types are layable; structural `HAS_REVISION`/`SUPERSEDES` stay internal in
`_append_state`).

**Analog B (for `get_impact`):** `query_scope` `core.py:404-467` — the canonical "compose a port
primitive → group/filter core-side → `_hydrate` → return frozen models" body. And `get_revision_chain`
`core.py:391-401` for the `[self._hydrate(s) for s in states]` final step.

`_hydrate` (the value-decode boundary, `core.py:229-244`) — reuse verbatim; needs ALL six fields:
```python
return BeliefState(
    state_id=props["state_id"], belief_id=props["belief_id"], scope_id=props["scope_id"],
    source_event_id=props["source_event_id"], value=self._decode_value(props["value"]),
    status=Status(props["status"]),
)
```

**`MemoryCore.get_impact` body (Pattern 2, D-01..D-05).** Signature MUST match `protocol.py:131-135`
EXACTLY: `(self, belief_state_id: UUID, depth: int | None = None) -> ImpactResult`. Add a
module-level constant:
```python
_CASCADE_EDGE_TYPES: frozenset[EdgeType] = frozenset(
    {EdgeType.DEPENDS_ON, EdgeType.DERIVED_FROM}  # D-03 — SUPERSEDES EXCLUDED by construction
)
```
(`EdgeType` import: `core.py:52` currently imports from `doxastica.models` — add `EdgeType`;
`ImpactResult` likewise.)
```python
reached_rows, frontier = self._backend.traverse(
    str(belief_state_id),     # stringify to match stored STRING PKs (core.py:273-283 precedent)
    _CASCADE_EDGE_TYPES,      # D-03
    depth,                    # depth=None ⇒ full closure, empty frontier (D-02)
    direction="in",           # D-04/D-05: walk AGAINST the arrows (X's dependents)
)
# ... hydrate reached (SEE HYDRATION GAP below) ...
return ImpactResult(
    reached=reached,                  # excludes start X (D-02)
    frontier=frozenset(frontier),
    truncated=len(frontier) > 0,      # D-02 derivation
)
```

**⚠ HYDRATION GAP — DECISION REQUIRED FROM PLANNER (RESEARCH Pitfall 1 / Open Q1).** The two backends'
`reached` rows DIFFER: ladybug returns `[{"state_id": ...}]` only (`ladybug.py:414`); in-memory
returns full props (`memory.py:140`: `dict(self._node_index.get(to_key, {}))`). `_hydrate` needs all
six fields, so `get_impact` CANNOT hydrate directly from `reached` on ladybug. **RESEARCH-recommended
Option A (driver-blind, parity-clean):** take the `state_id`s from `reached_rows`, then re-fetch full
props per id via `self._backend.match_nodes("BeliefState", {"state_id": sid})` (already parity-tested,
identical on both backends) and `_hydrate` those. Option B (widen ladybug `traverse` return) is
rejected (breaks parity literals). Confirm `reached` order is not contractually significant
(`backend-contract.md:70-77` §5: the core orders results itself) — RESEARCH suggests sorting the
hydrated tuple by `_order_key` (`core.py:63-73`) for determinism, mirroring `query_scope`'s final
`tails.sort(key=_order_key)` (`core.py:466`).

**Driver-blind discipline (D-02, `core.py:18-22` docstring):** `add_edge`/`get_impact` compose ONLY port
primitives — NO Cypher, NO `ladybug` import, NO `direction` logic. The core passes the literal
`direction="in"`; both backends own the flip.

---

### `docs/backend-contract.md` (config/contract, BACK-04 §2) — document `direction`

**Analog:** the existing §2 `traverse` bullet (`backend-contract.md:42-51`):
```markdown
- **`traverse(start, edge_types, max_depth) -> (reached, frontier)`** — the **single**
  graph-walk primitive. Following only edges in `edge_types` from `start`, it returns:
  - `reached`: the **de-duplicated, cycle-safe** set of reachable nodes ...
  - `frontier`: the set of node ids left **unexpanded** when `max_depth` is reached.
  `max_depth=None` ⇒ **full transitive closure** with an **empty frontier**. ...
```
**Change:** document the new `direction: "out" | "in"` parameter — `"out"` (default) follows edges
FROM `start` (preserves current `get_scope_at` behaviour); `"in"` follows edges INTO `start` (the
`get_impact` dependency cascade). State that BOTH directions on BOTH backends must agree
(Phase-7 conformance exercises both). Keep §5 "ordering left to the core" (`backend-contract.md:70-77`)
intact — `reached` order is non-contractual either way.

---

## Shared Patterns

### Atomic write grouping (`unit_of_work`)
**Source:** `MemoryCore._append` `core.py:303` / `contract` `core.py:371`; backend impls
`memory.py:146-164` (snapshot/restore), `ladybug.py:418-434` (`BEGIN`/`COMMIT`/`ROLLBACK`).
**Apply to:** the new `MemoryCore.add_edge` — exactly ONE `with self._backend.unit_of_work():`.
`get_impact` is a pure read — NO `unit_of_work` (mirror `query_scope`, which has none).

### UUID stringification at the backend boundary
**Source:** `_append_state` `core.py:273-283` (`str(state_id)`, `str(source_event_id)`).
**Apply to:** `add_edge` (`str(from_state_id)`, `str(to_state_id)`) and `get_impact`
(`str(belief_state_id)`) — ladybug binds against STRING-typed PK columns.

### Compose-port-primitive → core-side process → `_hydrate` → frozen model
**Source:** `query_scope` `core.py:444-467`; `get_revision_chain` `core.py:399-401`; `_hydrate`
`core.py:229-244`.
**Apply to:** `get_impact` (`reached_rows` → re-fetch props → `_hydrate` → `ImpactResult`).

### Driver-blind core (D-02)
**Source:** `core.py:18-22, 44-60` (function-local ladybug imports only; module-top forbids `ladybug`).
**Apply to:** both new methods — pinned by `tests/test_import_purity.py` (no new module-level driver import).

### Injection-safe interpolation (the ONE sanctioned interpolation)
**Source:** `ladybug.py:356-399` (`edge_types` validated against `_EDGE_ENDPOINTS`, `bound`
runtime-guarded interpolated int, namespace the sole interpolation; `$start` stays `$param`-bound).
**Apply to:** the `direction` arrow-flip — derive `lhs/rhs` from the closed `Literal`, never a
`$param` position, never caller free-text.

### Parametrized backend fixture + both-backends parity
**Source:** `tests/conftest.py` `backend` fixture (`params=["memory","ladybug"]` + `importorskip`);
`tests/test_backend_parity.py` `_both_backends` `:240-250`, `_reached_ids` `:74-76`, `_frontier_ids`
`:79-81`, graph builders `_build_diamond/_build_cycle/_build_chain` `:84-109`.
**Apply to:** the new reverse-direction parity cases AND `tests/test_cascade.py`.

---

## Test Patterns

### `tests/test_backend_parity.py` (EXTEND — reverse-direction `direction="in"` parity)
**Analog (in-file):** the 9 existing `traverse` parity cases `:117-201`. Each calls
`backend.traverse(start, frozenset({_DEPENDS_ON}), max_depth)` and asserts `_reached_ids` /
`_frontier_ids` literals. Mirror them with `direction="in"`:
- On an ASYMMETRIC graph (e.g. reuse `_build_chain` A→B→C→D): `traverse("D", {DEPENDS_ON}, None,
  direction="in")` must reach `{A,B,C}` (predecessors), and `traverse("A", ..., direction="in")`
  must reach `{}` — the asymmetric probe catches a successor/predecessor swap (RESEARCH Pitfall 2).
- Add a `direction="in", max_depth=0` case (RESEARCH Pitfall 3 — the `bound==0` IN-edge probe).
- Keep ALL existing positional `traverse(..., max_depth)` calls UNCHANGED — they must stay green on
  the `direction="out"` default (RESEARCH Runtime State Inventory; regression gate).
- Add a `_both_backends` byte-identical reverse case mirroring `test_both_backends_diamond_byte_identical`
  `:253-262`.

### `tests/test_cascade.py` (NEW — `get_impact`/`add_edge` mechanism + property)
**Analog (idioms to combine):**
- `tests/test_backend_parity.py` for the `_both_backends()` parity loop + `_reached_ids` normalization
  + asymmetric-graph construction (RESEARCH "Code Examples" gives a ready `get_impact` parity test
  using `core.revise(...)` + `core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)`).
- `tests/test_invariants.py:40-60` for the Hypothesis imports/idiom (`from hypothesis import given,
  strategies as st` — the cycle-termination property test in RESEARCH "Code Examples" uses
  `@given(depth=st.one_of(st.none(), st.integers(min_value=0, max_value=10)))`).
- `MemoryCore.in_memory()` (`core.py:89-94`) for the zero-dep property-test construction.

**Required coverage (RESEARCH Validation Architecture → Test Map):**
| Behavior | Type | Source pattern |
|----------|------|----------------|
| `add_edge` lays typed edge, idempotent, closed `EdgeType` | unit + parity | parity loop + `core.get_impact` assertion |
| `add_edge` silent no-op on missing endpoint (D-07 PIN) | unit + parity | RESEARCH Code Examples `test_add_edge_missing_endpoint_is_silent_no_op` |
| `get_impact` returns DEPENDENTS only (asymmetric) | parity | RESEARCH `test_get_impact_dependents_only_parity` (`get_impact(A)=={B}`, `get_impact(B)=={}`) |
| `get_impact` terminates + de-dupes on cycles | property (Hypothesis) | RESEARCH `test_get_impact_terminates_on_cycle` |
| `get_impact` exact reachable-within-depth set | property | derive from the depth-bounded parity literals |
| `get_impact` frontier/truncated at the bound (incl. depth=0) | parity | mirror `test_max_depth_zero_frontier_parity` `:182-191` |
| `get_impact` hydrates full `BeliefState` on BOTH backends (hydration-gap guard) | parity | assert `s.value`/`s.status` etc. populated, not just `state_id` |

## No Analog Found

None. Every touched file has an in-repo analog (the file itself or a documented sibling test idiom).
The closest thing to "new" is `tests/test_cascade.py`, but it composes two existing test idioms
(`test_backend_parity.py` parity loop + `test_invariants.py` Hypothesis imports), and RESEARCH already
supplies the exact test bodies under "Code Examples".

## Metadata

**Analog search scope:** `src/doxastica/{ports,protocol,models,core}.py`,
`src/doxastica/backends/{memory,ladybug}.py`, `tests/{conftest,test_backend_parity,test_invariants}.py`,
`docs/backend-contract.md`.
**Files scanned:** 11.
**Pattern extraction date:** 2026-06-18.
</content>
</invoke>
