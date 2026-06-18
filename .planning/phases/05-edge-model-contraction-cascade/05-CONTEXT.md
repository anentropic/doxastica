# Phase 5: Edge Model & Contraction Cascade - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the two public `MemoryCore` methods that complete the edge/cascade surface:

- `add_edge(from_state_id, to_state_id, edge_type)` — lay a generic typed edge
  (`SUPERSEDES` / `DEPENDS_ON` / `DERIVED_FROM`) between two `BeliefState`s, no epistemic
  semantics in the core (EDGE-01).
- `get_impact(belief_state_id, depth=None)` — bounded, cycle-safe dependency-cascade
  traversal returning an `ImpactResult` with an accurate truncation/frontier signal
  (EDGE-02).

**Depends on:** Phase 3 only.

**Out of scope:** the AGM Relevance / Core-Retainment *postulate tests* — those are Phase 7's
conformance suite. Phase 5 builds the *mechanism* those postulates are tested against. Also
out: any cascade *policy* (auto-contract, mark `under_revision`, re-resolve) — that is NVM
consumer policy, not core mechanism (`05 §3`, `§4`).

**Key framing:** the hard substrate is already built. Both backends already implement the
port's `add_edge` and a cycle-safe bounded `traverse` returning the `(reached, frontier)`
shape (Phase 2 spike, SC4). `EdgeType` and `ImpactResult` already exist (Phase 1). Phase 5 is
thin composition over the port + the ONE port change in D-03 below + mechanism property tests.

</domain>

<decisions>
## Implementation Decisions

### What `get_impact(X)` returns — *dependents*, not dependencies
- **D-01:** `get_impact(X)` returns the transitive set of `BeliefState`s that **depend on X**
  (its downstream dependents) — the contraction-cascade impact set NVM marks for revision. It
  is called ON the retracted/contracted node and returns what is affected. It does NOT return
  "what X depends on." Grounded in `17 §2` (lines 43-46, 66-72) and `05 §3`/`§10.3`.
- **D-02:** `reached` EXCLUDES the start node X itself (matches the existing port `traverse`
  contract on both backends). Shape is the locked `ImpactResult(reached: tuple[BeliefState, ...],
  frontier: frozenset[UUID], truncated: bool)` from Phase 1 / DATA-04. `truncated = len(frontier)
  > 0`; `depth=None` ⇒ full transitive closure, empty frontier, `truncated=False`. The old
  `depth=5` sketch number is retired (`05 §10.3` soft-spot #3).

### Cascade edge-type set
- **D-03:** `get_impact` traverses **`{DEPENDS_ON, DERIVED_FROM}`**. `DERIVED_FROM` is REQUIRED:
  NVM's invalidation edges (`INFERRED_FROM`, `TOLD_BY`, `WITNESSED_BY`) are all specialisations
  of the generic `DERIVED_FROM` (`05 §4`, lines 141-145), so omitting it makes NVM's real
  cascade structurally invisible at the core level. `SUPERSEDES` is EXCLUDED by construction —
  it is the revision-spine edge the core lays automatically on every `revise`/`expand`/`contract`
  (`_append_state`); following it would report a belief's own version history as "impact" for
  every belief. The genuine failure mode for this surface is *under*-reaching, not over-reaching
  (over-breadth is fine — `get_impact` is mechanism; NVM policy decides what to actually retract).

### Traversal direction — the one real port change
- **D-04:** The cascade walks edges INTO X (X's dependents). The core's edge-storage convention
  is dependent→source (NVM lays `(derived)-[:INFERRED_FROM]->(premise)`; the core's own
  `SUPERSEDES` is `new→prior`). So the impact walk runs AGAINST the arrows. The port's current
  `traverse` follows OUTGOING edges only — it cannot express `get_impact` as built.
- **D-05:** RESOLUTION (chosen over reversing the edge-storage convention or parameterising
  `get_impact`): **add a direction to the port `traverse` primitive** (e.g.
  `traverse(start, edge_types, max_depth, direction='in'|'out')`, default preserving current
  outgoing behaviour for `get_scope_at` in Phase 6). `get_impact` calls it with `direction='in'`.
  - Ladybug: a one-token Cypher change — `MATCH (x)<-[:{rels}*1..N]-(d)` instead of `-[...]->`.
    All existing injection-safety / `_EDGE_ENDPOINTS` validation / `_DEPTH_CEILING` / `bound==0`
    frontier logic carries over unchanged; only the arrow flips.
  - In-memory: walk a reverse adjacency index (the mirror of the existing `_out_edges`).
  - The port contract (`ports.py` docstring) + `docs/backend-contract.md` (BACK-04) must document
    the new `direction` parameter, and the Phase 7 conformance suite must exercise BOTH directions
    on BOTH backends for parity.

### `add_edge` (public `MemoryCore` method)
- **D-06:** Near-passthrough to `self._backend.add_edge(edge_type, from_id, to_id)` wrapped in
  ONE `self._backend.unit_of_work()`. Idempotency (double-add ⇒ one edge) is ALREADY guaranteed
  by both backends — the core adds nothing there. Public signature takes the closed `EdgeType`
  enum (not a raw string), so only the three generic types are layable via the public seam; the
  structural `HAS_REVISION`/`SUPERSEDES` wiring stays internal (D-07 from Phase 3).
- **D-07:** No endpoint-existence validation in the core (mechanism, not policy). The port's
  `MATCH ... MERGE` silently no-ops if an endpoint is missing; the core does not add a raise.
  Flag for the planner to confirm a test pins this behaviour rather than leaving it incidental.

### Claude's Discretion
- Whether `depth` bounds *hops* vs *unique nodes* — the existing `traverse` already defines this
  (hop-bounded BFS layers); `get_impact` inherits it. No new decision needed unless the planner
  finds an inconsistency.
- Internal helper factoring for the reverse-adjacency index in the in-memory backend.

</decisions>

<specifics>
## Specific Ideas

- Entrenchment corollary (confirms direction, not a Phase-5 deliverable): a belief's
  entrenchment is its `DERIVED_FROM` **in-degree** (`17 §11` line 282; `16` ratified — "the AGM
  dependency weight"). `get_impact(X, depth=1)` therefore doubles as the direct-dependent /
  in-degree probe NVM uses for entrenchment hints. This is downstream NVM policy, but it
  independently confirms the incoming-edge direction chosen in D-04/D-05.
- Mechanism property tests this phase should cover: termination on cyclic dependency graphs;
  `reached` == exactly the reachable-within-`depth` dependent set; accurate `frontier`/`truncated`
  at the depth bound (including `depth=0`); cross-backend parity (in-memory oracle vs ladybug).

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Contraction-cascade semantics (the primary spec for this phase)
- `../narrative-vm/_design/v2/17-kumiho-nvm-recommendations.md` §2 — the canonical cascade:
  "when a belief is contracted, only beliefs that depend on it are affected" (lines 43-46) and
  the belief-contraction workflow traversing `INFERRED_FROM`/`TOLD_BY` (lines 66-72). §11
  (line 282) = entrenchment as `DERIVED_FROM` in-degree.
- `../narrative-vm/_design/v2/05-nvm-memory-core.md` §3 (`get_impact` is "the contraction
  cascade … mechanism; what to do with the result is NVM policy", lines 124-129), §4 (epistemic
  edges `WITNESSED_BY`/`TOLD_BY`/`INFERRED_FROM` are `DERIVED_FROM` specialisations, lines
  141-145; invalidation workflow is NVM policy, lines 159-161), §10.3 (depth/truncation
  soft-spot — `depth=5` retired).
- `../narrative-vm/_design/v2/16-nvm-decision-register.md` (RATIFIED entry, lines 314-319) —
  `get_impact` carries "the AGM dependency weight"; DC formulas stay adapter-side.

### In-repo design lineage (decisions already locked upstream)
- `.planning/phases/01-protocol-backend-port-data-model-decisions/01-CONTEXT.md` §5 — the
  `get_impact` shape & depth decision (cycle-safety from visited-set not depth; `depth=None`
  default; frozen `ImpactResult`).
- `src/doxastica/ports.py` — `BackendPort` (the `traverse` primitive + `(reached, frontier)`
  contract this phase extends with `direction`).
- `src/doxastica/models.py` — `EdgeType`, `ImpactResult`, `BeliefState` (all exist, unchanged).
- `src/doxastica/core.py` — `MemoryCore` (`_hydrate`, `unit_of_work` plumbing, the internal
  `SUPERSEDES`/`HAS_REVISION` edge-laying in `_append_state` — the direction precedent).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BackendPort.add_edge` / `traverse` (both backends, Phase 2): the full primitives. `add_edge`
  is idempotent; `traverse` is cycle-safe, bounded, returns `(reached, frontier)`. `get_impact`
  and the public `add_edge` compose directly on these.
- `MemoryCore._hydrate` (core.py): raw port dict → frozen `BeliefState`; reuse to build
  `ImpactResult.reached`.
- `MemoryCore.unit_of_work` / `self._backend.unit_of_work()`: wrap the public `add_edge` write.

### Established Patterns
- Driver-blind core (D-02): `get_impact`/`add_edge` bodies compose ONLY port primitives; no
  Cypher, no `ladybug` import. The direction change lives in the BACKENDS, not the core.
- Injection-safety on interpolated traversal (ladybug.py): `edge_types` validated against
  `_EDGE_ENDPOINTS`, depth interpolated (not `$param`-bound) with a runtime guard, namespace
  the only sanctioned interpolation. The `direction='in'` change must stay inside this story.

### Integration Points
- `protocol.py` `BeliefStore.add_edge` / `get_impact` signatures are already the public contract
  — Phase 5 implements them on `MemoryCore`; no signature change there.
- `docs/backend-contract.md` (BACK-04) + `ports.py` docstring — must document the new `traverse`
  `direction` parameter.

</code_context>

<deferred>
## Deferred Ideas

- Edge *properties* on `add_edge` — both backends currently `raise NotImplementedError` on
  non-empty `props` (IN-01). Storing edge props (e.g. NVM's `tell_event_id` on `TOLD_BY`) is a
  future port extension, not Phase 5.
- `get_scope_at` reuse of the new `direction` parameter — Phase 6 uses `traverse` (outgoing);
  the default must preserve current behaviour so Phase 6 is unaffected.
- Phase 7 conformance: Relevance / Core-Retainment postulate tests, and parameterising the
  full suite over both backends — exercises `get_impact` but is its own phase.

</deferred>

---

*Phase: 05-edge-model-contraction-cascade*
*Context gathered: 2026-06-18*
