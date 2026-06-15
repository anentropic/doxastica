# Phase 3: Append-Only Revision Spine (Keystone) - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the **AGM write spine** the entire postulate suite stands on:
scopes (including the privileged world scope), the `Belief`/`BeliefState` split with
immutable `HAS_REVISION` chains, the single (derived) current per belief-in-scope, and the
three core write operations `revise` / `expand` / `contract` — implemented against the
Phase-1 `BackendPort` so they run identically on both backends (in-memory + ladybug) from
the start.

**Requirements in scope:** SCOPE-01, SCOPE-02, SCOPE-03, CHAIN-01, CHAIN-02, CHAIN-03,
OPS-01, OPS-02, OPS-03, HIST-02.

**In scope:** `get_or_create_scope`; world-scope identity + `contract()` guard; `Belief`/
`BeliefState` creation; `HAS_REVISION` chain + `SUPERSEDES` edges; `revise`/`expand`/
`contract` bodies on `MemoryCore`; `get_revision_chain`; the per-op atomic `unit_of_work`;
the structural-invariant test (now a consistency check — see D-01); extending each backend's
schema/edge handling for the new structural edges (`HAS_REVISION`; `SUPERSEDES` already has a
ladybug REL table).

**Out of scope (later phases):** `query_scope` + the deprecated/superseded **query matrix**
(Phase 4); `add_edge` consumer edges + `get_impact` cascade (Phase 5); `get_scope_at`
time-travel reconstruction (Phase 6 — though "current" is defined as `get_scope_at(latest)`,
its full as-of machinery is Phase 6); the assembled AGM/Hansson conformance suite (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### D-01 — Current state is DERIVED, not a stored pointer (the keystone modelling choice)

`current(scope, belief)` is **computed**, never stored: it is the maximal `BeliefState` for a
given `(scope_id, belief_id)` under the UUID7 ordering contract
(`source_event_id` byte-order, `state_id` tiebreak). There is **no `CURRENT_STATE` edge or
pointer**; every write is a pure append. The store has **zero mutable elements** — even more
append-only than the design's "`CURRENT_STATE` is the only mutable element."

- **Why current is per-`(scope, belief)`, not per-`belief`:** multi-scope's whole point is
  value *divergence* — the same `belief_id` holds different current values in different
  scopes (the Phase 7 irony join: actor-scope vs world-scope on `belief_id`). The global
  `Belief` node (keyed by `belief_id` alone, Phase 1 §3) cannot host a scope-specific
  pointer — which is exactly why the design's single-`(:Belief)-[:CURRENT_STATE]` edge does
  not transplant.
- **This is a deliberate, recorded CHAIN-03 mechanism-deviation** (sibling to the Phase 1
  floor-raise and Phase 2 D-03 reversal — recorded, not silent). CHAIN-03's *functional
  guarantee* ("exactly one current per belief-in-scope, established atomically per write") is
  **fully preserved**; only the *mechanism* changes from "a stored pointer that is mutated"
  to "a derived selection over immutable data."
- **Invariant-test impact (SC3 / FORMAL-03):** the `CURRENT_STATE`-uniqueness `@invariant`
  shifts from "count `CURRENT_STATE` edges == 1" to a **consistency check**:
  current-selection is total + single-valued per `(scope, belief)`, AND `query_scope`-current
  ≡ `get_scope_at(latest)` ≡ `HAS_REVISION` chain tail. Uniqueness becomes a *theorem*
  (unique max under a unique `state_id` tiebreak), not a maintained invariant a buggy write
  could corrupt. The test still runs on both backends.
- **Grounding:** `05-nvm-memory-core.md §6` cl.3 — the world scope's canonical subgraph is
  "entities + `CURRENT_STATE` facts — **materialized as plain edges only if traversal
  profiling demands**." The design itself treats current-state as derived, with edge/pointer
  an *optional* optimization. A stored pointer remains a future profiling-driven optimization
  addable **without changing the public `BeliefStore` surface** (see Deferred Ideas).

### D-02 — World scope identity: reserved constant `WORLD_SCOPE_ID = "__world__"`

- doxastica **exports a module constant `WORLD_SCOPE_ID = "__world__"`** (NVM imports it).
  `get_or_create_scope("__world__")` returns a `Scope` with `is_world=True`; every other
  `scope_id` is an ordinary independent peer (`is_world=False`). **Singleton by
  construction** — only the reserved id is ever world.
- **Value is `"__world__"`** (dunder-wrapped), deliberately chosen over a bare `"world"` to
  avoid collision with a caller-chosen `scope_id` (an actor/location literally named "world"
  is plausible; `"__world__"` is unmistakably reserved).
- The locked public signature `get_or_create_scope(scope_id: str) -> Scope` is **unchanged**
  (no `is_world` parameter; no caller-configured world id threaded through the core).
- **Grounding:** `05 §6` — world scope is canonical truth "held by no one in particular,"
  singular + privileged; NVM seeds its *content* at genesis via ordinary `expand`/`revise`
  (seeding is NVM's job, not a doxastica API — Phase 1 settled this).

### D-03 — World scope creation is LAZY; the `contract()` guard is STRUCTURAL

- No auto-creation. The `"__world__"` node is created on first `get_or_create_scope`
  (`is_world=True`) **or** on first write that auto-creates it (see D-06) — same create-on-
  demand idiom as any scope.
- `contract("__world__", …)` raises `WorldScopeContractionError` by checking
  `scope_id == WORLD_SCOPE_ID` **structurally, before any backend read/write** (SCOPE-02 /
  SC1 "raises before any write"). The guard holds even if the world node was never created,
  and cannot be bypassed by operation ordering.

### D-04 — `revise` ≡ `expand` are MECHANICALLY IDENTICAL at the core

Both operations execute the same steps, inside one `unit_of_work`:
1. mint `state_id` via stdlib `uuid.uuid7()`;
2. append a `BeliefState{state_id, belief_id, scope_id, source_event_id, value,
   status=active}`;
3. link `HAS_REVISION` (the full immutable version chain);
4. lay a `SUPERSEDES` edge `new → prior-current` **when a prior current exists**;
5. return the new `BeliefState`.

`current` stays **derived** (= the unique state with no incoming `SUPERSEDES` = the
ordering-max), so there is no second, disagreeing notion of current.

- **Why identical:** the "consistency check" classical revision does and expansion skips is
  the *propositional contradiction* check — which **neither** performs here (no inference,
  DATA-05), and the only structural inconsistency (two values per key) is **unrepresentable**
  under the keyed/derived-current model. The names persist for NVM's declared intent
  (consumed in the **stance layer above the seam**, `06 §3` / R21 — "revision has inertia;
  expansion of a novel proposition takes its assignment level directly") and for Phase 7
  exercising both AGM families (revision K*2–6 *and* expansion).
- **Grounding (the Kumiho paper, read directly, pp. 1–8):** the formal results hold over "a
  **deliberately simple propositional logic over ground triples** … that avoids the Flouris
  et al. impossibility results for description logics" (abstract). Conflict resolution is the
  **`SUPERSEDES`** edge ("creates a new revision with formal guarantees — Success,
  Consistency, minimal change via Relevance"; Table 1 "Conflict = AGM Supersedes"); the
  cascade is `AnalyzeImpact` over `Depends_On` (= doxastica `get_impact`, Phase 5). The
  NL→triple mapping is **pre-formal** ("the consistency of the mapping is a prompt-engineering
  concern, **not a formal one**," §7.1/§8). **There is no value-semantic consistency engine in
  the paper to port** — `revise`-as-append-and-supersede *is* the paper's revision operator,
  not an under-implementation; opaque `value: Any` (DATA-05) is the faithful representation.

### D-05 — `contract` semantics: vacuous on absent; appends one retracted state when it acts

- **Vacuity (AGM-required):** `contract` on a belief with **no active current** (never
  asserted, or already `retracted`) is a **silent no-op returning `None`** — no state
  appended, active set unchanged. Required for the Hansson **Vacuity** postulate (Phase 7) to
  hold (`if φ ∉ B, then B−φ = B`); also keeps contraction idempotent.
- **When it acts** (belief has an active current): append **exactly one** `status=retracted`
  `BeliefState` whose `value` **copies the prior current value** (records *what* was retracted,
  for history / `get_scope_at`), plus `HAS_REVISION` and `SUPERSEDES new(retracted) →
  prior-current`, in one `unit_of_work`.
- **Ordering of guards in `contract`:** the world-scope structural guard (D-03) fires
  **first** (before the absent/no-op check and before any backend access).

### D-06 — Auto-create scope + Belief node on write; permissive preconditions

- **Auto-create on write:** `revise`/`expand`/`contract` create the scope if absent (applying
  the reserved-id rule: `scope_id == "__world__"` → `is_world=True`) and auto-create the
  `Belief` node for a novel `belief_id`. Consistent with the `get_or_create` idiom and the
  lazy-world-scope decision (D-03).
- **Permissive (no novel-vs-update preconditions):** both `revise` and `expand` always
  succeed on a valid scope. `revise` on a novel `belief_id` = first assertion (nothing to
  supersede). `expand` on an existing `belief_id` = append + supersede (identical to
  `revise`). The novel-vs-update meaning lives in NVM's stance layer above the seam. This is
  AGM-faithful (classical ops carry no such precondition) and keeps the Phase 7 oracle
  trivial.

### D-07 — Structural-edge model laid in this phase

- **`HAS_REVISION`** = the structural append-only version chain → feeds `get_revision_chain`
  (HIST-02) and the ordering-based derived current. Direction/hub-vs-link shape is a planner
  call (the design sketch is `(:Belief)-[:HAS_REVISION]->(:BeliefState)`, hub form).
- **`SUPERSEDES`** (already a Phase-1 `EdgeType` + a ladybug REL table) is **laid by the core**
  on every displacement (`revise`/`expand`/`contract`) — this is the paper's named conflict
  operator and is exactly what **Phase 4's** deprecated-vs-superseded matrix (SC2: "observable
  via `SUPERSEDES` edge") reads and **Phase 5's** `get_impact` traverses. Phase 3 must
  therefore add the `HAS_REVISION` REL table to the ladybug bootstrap (the `SUPERSEDES` /
  `DEPENDS_ON` / `DERIVED_FROM` tables already exist; `CURRENT_STATE` is **not** created —
  D-01).
- Structural edges (`HAS_REVISION`, and the core's structural use of `SUPERSEDES`) are passed
  to `add_edge` as raw strings; they are not added to the `EdgeType` enum membership decision
  from Phase 1 (HAS_REVISION stays a structural constant, not an `add_edge`-able consumer
  type).

### Claude's Discretion
- `HAS_REVISION` hub (`Belief→state`) vs chain-link (`state→state`) shape, and edge direction
  conventions — planner/researcher call, constrained only by: `get_revision_chain(belief_id)`
  works, and derived current/superseded are computable from it + the ordering contract.
- Exactly how `value` is stored below the model layer (the ladybug adapter JSON-encodes the
  opaque `value` into the `value STRING` column; the in-memory adapter holds it verbatim) —
  established Phase-2 pattern, no new decision.
- Per-op transaction boundaries beyond "one `unit_of_work` per public write" (the unit-of-work
  primitive already exists on both backends).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The formal spec (sibling `narrative-vm` repo; read-only design inputs)
- `../narrative-vm/_design/v1/kumiho Graph-Native Cognitive Memory for AI Agents.pdf` —
  **the paper (arXiv 2603.17244).** Abstract = "simple propositional logic over ground
  triples"; §2.2 + Table 1 = `SUPERSEDES` is the conflict operator; §7 = the AGM/Hansson
  correspondence + Recovery rejection; §7.1/§8 = NL→triple mapping is pre-formal. Grounds D-04.
- `../narrative-vm/_design/v2/05-nvm-memory-core.md` — **PRIMARY spec.** §2 core taxonomy;
  **§6 scopes** (independent peers, world scope = canonical truth, world-scope `contract()`
  forbidden, `CURRENT_STATE` "materialized only if profiling demands"); §8 structural
  invariants (`CURRENT_STATE` uniqueness, chain immutability, `get_scope_at` ≡ replay).
  Grounds D-01, D-02, D-03.
- `../narrative-vm/_design/v2/01-nvm-glossary.md` — §AGM/Hansson: the three operations
  (expansion/contraction/revision) as **Hansson-style base operations**; recovery excluded.
- `../narrative-vm/_design/v2/06-nvm-knowledge-inference-design.md` — §1 "abduction on demand,
  not deduction to fixpoint"; §3 belief states behind `BeliefStore`, stance/inertia (R21) is
  the NVM layer ABOVE the seam. Confirms revise/expand difference lives above the core (D-04).
- `../narrative-vm/_design/v2/17-kumiho-nvm-recommendations.md` — §2 superseded≠deprecated
  (paper §8.6); **NOTE: §6's shared-`Belief`/`BELIEVES`/confidence multi-actor sketch is
  SUPERSEDED by `05 §6`** on the scope model — read with that precedence.
- `../narrative-vm/_design/v2/16-nvm-decision-register.md` — R12 world-scope unification, R19
  label-family tenancy, R21 stance (a non-core NVM extension).
- `../narrative-vm/_design/v2/15-nvm-milestones.md` — M0 exit gate; the irony join
  (actor-scope vs world-scope divergence) Phase 3's spine must enable.

### Phase 1 / Phase 2 code seams (this repo)
- `src/doxastica/protocol.py` — the locked public `BeliefStore` surface this phase implements
  (`get_or_create_scope`, `revise`, `expand`, `contract`, `get_revision_chain`; UUID7 ordering
  contract docstring).
- `src/doxastica/ports.py` — `BackendPort`: the 5 LPG primitives (`upsert_node`/`add_edge`/
  `match_nodes`/`traverse`/`unit_of_work`). **No edge-delete primitive** — the constraint that
  drives D-01.
- `src/doxastica/models.py` — frozen taxonomy: `Scope(scope_id, is_world)`, `Belief`,
  `BeliefState` (closed six-field set, `status ∈ {active, retracted}`), `EdgeType`
  (`SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM`).
- `src/doxastica/core.py` — `MemoryCore`: holds the constructors/factories; **the AGM op
  bodies land here in Phase 3** (Phase 2 left them unwritten).
- `src/doxastica/backends/memory.py` / `backends/ladybug.py` — the two adapters; ladybug
  `_bootstrap_schema` is where the `HAS_REVISION` REL table is added (D-07); the node tables +
  `SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM` REL tables already exist.
- `src/doxastica/errors.py` — `WorldScopeContractionError` (typed Phase 1; enforcement lands
  here in Phase 3, D-03).
- `.planning/phases/01-…/01-CONTEXT.md`, `.planning/phases/02-…/02-CONTEXT.md` — locked
  upstream decisions (LPG-primitive port, UUID7 ids, closed taxonomy, SQLAlchemy-Engine
  `MemoryCore`, D-02/D-03/D-04/D-05 packaging + adapters).
- `.planning/research/PITFALLS.md`, `.planning/research/ARCHITECTURE.md` — GSD research layer.
  **Caveat:** both model `CURRENT_STATE` as a stored, delete-then-create edge — that is
  **superseded by D-01 (derived current)**; read their `revise`/`contract` Cypher as the
  *rejected* pointer-form alternative, not the plan.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **The 5 LPG primitives on both backends** are complete and parity-tested (`test_backend_
  parity.py`). Phase 3 composes them; it writes no new storage primitives — except adding the
  `HAS_REVISION` REL table to the ladybug bootstrap (D-07).
- **`unit_of_work`** exists on both backends (ladybug `BEGIN`/`COMMIT`/`ROLLBACK`; in-memory
  snapshot/restore) — the atomic boundary for each write (CHAIN-03 / SC3).
- **`MemoryCore` factories** (`in_memory()` / `open()` / `from_connection()`) are done; Phase 3
  fills the operation bodies on the existing class.
- **Parametrized `conftest`** runs every test over both backends — the mechanism that keeps the
  in-memory oracle and ladybug identical from day one (and the home of the new
  structural-invariant consistency test, D-01).

### Established Patterns
- **Adapters return raw `list[dict]` below the model layer; `MemoryCore` hydrates frozen
  pydantic models and JSON-encodes opaque `value`** (Phase 2 D-04). Phase 3's op bodies follow
  this: compose primitives, hydrate `BeliefState` above the port.
- **`_PK_BY_LABEL`** in the ladybug adapter is the single source of truth for each node table's
  PK / MERGE key — `BeliefState` keys on `state_id`.
- **Driver-blind core / function-local imports** (Phase 2 D-02) — Phase 3 op bodies stay in
  `core.py` against the port; no driver import.

### Integration Points
- Phase 3 is the keystone: Phases 4 (`query_scope`), 5 (`add_edge`/`get_impact`), 6
  (`get_scope_at`) all compose on the spine and can proceed in parallel once it exists.
- `SUPERSEDES` edges laid here (D-07) are read by Phase 4 (deprecated/superseded matrix) and
  traversed by Phase 5 (`get_impact`) — flagged forward.

</code_context>

<specifics>
## Specific Ideas

- The reserved world-scope constant is specifically `"__world__"` (dunder-wrapped), per the
  user's call (D-02).
- A retracted state copies the prior current `value` (not null/sentinel) — "record what was
  retracted" (D-05).
- The structural-invariant test is to be written as a **consistency** assertion
  (`query_scope`-current ≡ `get_scope_at(latest)` ≡ chain tail), not an edge count (D-01) —
  meaningful under the derived-current model.

</specifics>

<deferred>
## Deferred Ideas

- **Materialize a stored current pointer (head-node via `upsert_node`, or an edge with a new
  delete/replace port primitive) ONLY if `query_scope` profiling later demands it** —
  addable without changing the public `BeliefStore` surface, per `05 §6` cl.3. Not now (D-01).
- **`get_scope_at` full as-of reconstruction** — Phase 6 (HIST-03). Phase 3 only needs
  "current = as-of latest"; the general as-of cut + same-millisecond UUID7 resolution is
  Phase 6.
- **`query_scope` + the four-cell deprecated/superseded query matrix** — Phase 4 (CHAIN-04 /
  HIST-01). Phase 3 lays the `SUPERSEDES` edges + `status` it reads, but not the query surface.
- **`add_edge` consumer edges + `get_impact` cascade** — Phase 5 (EDGE-01/02). The core's
  structural use of `SUPERSEDES` in Phase 3 is distinct from consumer-added
  `SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM` edges.
- **Optional `CONTRADICTS` edges** (paper mentions explicit conflict-detection edges) — a
  potential future consumer-declared generic edge; not core, not this phase.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.

</deferred>

---

*Phase: 3-append-only-revision-spine-keystone*
*Context gathered: 2026-06-15*
