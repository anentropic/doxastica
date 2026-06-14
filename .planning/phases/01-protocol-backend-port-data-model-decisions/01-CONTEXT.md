# Phase 1 Context: Protocol, Backend Port & Data-Model Decisions

**Created:** 2026-06-14
**Phase goal:** A typed, basedpyright-strict foundation with TWO explicit seams — the
public `BeliefStore` Protocol and, below it, the internal **backend port** the
backend-agnostic `MemoryCore` writes against — plus the decision-grade data-model choices
settled before any storage code exists. Reversing any of these (including the port's
granularity) would be a rewrite.

---

## Domain

This phase delivers **decisions and typed surfaces, not behaviour** — zero DB contact.
Its output is: the public `BeliefStore` Protocol (imports `pydantic`/`typing` only), the
internal LPG-primitive backend port abstraction, the frozen `pydantic` v2 models
(`Scope`, `BeliefState`, `EdgeType`, `BeliefFilter`, `ImpactResult`), and the written
backend-port contract spec (BACK-04). The gray areas discussed here are the open
decision-grade choices flagged in PROJECT.md / STATE.md whose reversal would cost a
rewrite. Everything is the foundation Phases 2–8 build against.

**Requirements in scope:** DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, PKG-01,
BACK-01, BACK-04.

---

## Canonical References (MANDATORY — read before research/planning)

All in the sibling `narrative-vm` repo (read-only design inputs). Paths are relative to
the doxastica repo root.

| Ref | Path | Why it matters to Phase 1 |
|-----|------|---------------------------|
| Memory-core seam design | `../narrative-vm/_design/v2/05-nvm-memory-core.md` | **Primary spec.** §3 = the recovered `BeliefStore` Protocol (verbatim surface to refine); §4 = NVM-layer responsibilities (what is NOT core); §6 = world scope; §10 = the soft spots this phase resolves (§10.1 query, §10.3 get_impact, §10.4 world seed). |
| Paper analysis + structural patterns | `../narrative-vm/_design/v2/17-kumiho-nvm-recommendations.md` | §3 BeliefState/Belief model sketch (`id` + `event_id` as distinct fields → confirms synthesized state_id); §4 UUID7 lineage keys. **Caveat: this doc mixes paper-core with NVM specifics — read it knowing NVM fields (provenance, valid_from_turn) are NOT core.** |
| Component architecture (the boundary) | `../narrative-vm/_design/v2/21-nvm-component-architecture.md` | **Resolved the query_scope seam.** §4 = the M0 library boundary; §6 seam catalog (`BeliefStore` vs `KnowledgeQueries`); §7 the persistence-portability story (why the core declines a generic query engine). The decisive doc for what doxastica's query surface should NOT be. |
| Decision register (tenancy) | `../narrative-vm/_design/v2/16-nvm-decision-register.md` | R19 label-family tenancy (core owns `:Scope`/`:Belief`/`:BeliefState`, closed subgraph, injected connection never closed); R21 stance (an NVM extension, not core). |
| Milestones / M0 exit gate | `../narrative-vm/_design/v2/15-nvm-milestones.md` | M0 scope + exit gate (the AGM property suite as definition of done). |
| The paper | `../narrative-vm/_design/v1/kumiho Graph-Native Cognitive Memory for AI Agents.pdf` | The formal spec doxastica implements (arXiv 2603.17244). |

Project-local refs: `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`.

---

## Decisions

### 1. Backend port granularity — **LPG-primitive** (BACK-01)

The defining architectural fork of the phase. **Decided: LPG-primitive**, not Cypher-level.

- The internal backend port exposes **graph primitives**, not Cypher: `upsert_node` /
  `add_edge` / `match_nodes` / a generic bounded **`traverse`** / a **unit-of-work**
  transaction context. `MemoryCore` composes these; each backend translates to its native
  form.
- **Two seams are explicit and distinct in code:** the public `BeliefStore` Protocol
  (NVM↔core, unchanged) and the internal backend port below it. No Cypher / backend-specific
  code in the `MemoryCore` logic layer.
- **Traversal expressed via ONE generic primitive:** `traverse(start, edge_types, max_depth)
  → reachable nodes + frontier`. Both `get_impact` and `get_scope_at` compose from it
  (+ `match_nodes`). Keeps the port small and truly generic; the in-memory backend implements
  one BFS, zero Cypher.
- **Named tension (flag for Phase 2 spike):** under LPG-primitive, `get_impact` /
  `get_scope_at` may cost more round-trips than a single hand-written Cypher query. Phase 2
  SC4 confirms the port survives the real ladybug API and the round-trip budget is
  acceptable; **the port is adjusted then if the spike demands it.**

### 2. BeliefState identity & UUID7 ordering (DATA-03, DATA-06)

**PK model — synthesized core-minted `state_id`:**
- `state_id`: core-minted **UUID7**, PRIMARY KEY, the opaque public addressing handle.
- `source_event_id`: caller-supplied, **opaque, stored, indexed, NON-unique** — used only
  for ordering + lineage; the core never parses it.
- `belief_id`: stable logical identity (the `Belief` node), one belief per `Belief` node.
- *Rationale:* multi-scope (doxastica's extension to single-agent Kumiho) means one
  `source_event_id` can produce states in multiple scopes → it cannot be the PK. The
  Protocol surface confirms a stable state handle is needed: `revise`/`expand` **return** a
  `BeliefState`; `add_edge(from_state_id, to_state_id, …)` and `get_impact(belief_state_id)`
  **consume** state ids. Grounded in `17 §3` (BeliefState has both `id` and `event_id`).

**Ordering contract for `get_scope_at` (DATA-03):**
- Order by **`(source_event_id` byte-order, `state_id` tiebreak)** → a **total deterministic
  order** even when caller `source_event_id`s collide intra-ms or arrive equal. **No
  monotonicity demanded of the caller** (RFC 9562 makes intra-ms UUID7 monotonicity
  optional). `state_id` (core-minted UUID7) is itself write-monotonic, so the tiebreak
  reflects true insertion order.

**`state_id` minting & Python floor — require Python 3.14, use stdlib `uuid.uuid7()`:**
- Core mints `state_id` via **stdlib `uuid.uuid7()`** (RFC 9562, write-monotonic, native in
  3.14+).
- **`requires-python` raised from `>=3.11` to `>=3.14`.** This keeps runtime deps at
  **exactly `ladybug` + `pydantic`** (no third dep, no vendored uuid7, no dev shim).
- **Ripples for the planner:**
  - PROJECT.md / CLAUDE.md "Floor: 3.11" → **3.14**.
  - **CI matrix drops 3.11 / 3.13; runs 3.14 only** (PKG-03, Phase 8). Single-version matrix.
  - The CLAUDE.md "UUID7 decision (the one genuine runtime gap)" section and the `uuid-utils`
    dev-group shim are **moot** — remove/annotate.
  - All deps support 3.14 (ladybug `<3.15`, pydantic, hypothesis). ✓
  - **Verify (research):** NVM, the primary consumer, is on Python 3.14. (User's call to
    raise the floor; flag for confirmation, not a blocker.)

### 3. Core-vs-extension property taxonomy (DATA-06 — the boundary discipline)

**Locked.** The core declares a **closed property set** it reads/writes/interprets
structurally. Everything else is a downstream extension.

| Node | Core properties (the frozen pydantic models) |
|------|----------------------------------------------|
| `Scope` | `scope_id`, `is_world` |
| `Belief` | `belief_id` |
| `BeliefState` | `state_id`, `belief_id`, `scope_id`, `source_event_id`, `value`, `status` |

- `value: Any` — **opaque**, JSON-encoded; core never inspects internals. (Considered
  constraining to JSON-string; chose `value: Any` with core-side encoding.)
- `source_event_id` — opaque, indexed, non-unique (see §2).
- `status` — **`active` | `retracted` ONLY.** The NVM sketch's `invalidated` /
  `under_revision` / `provenance` are **NVM concepts, NOT core.**
- Core edge types: structural `HAS_REVISION`, `CURRENT_STATE` + generic
  `SUPERSEDES` / `DEPENDS_ON` / `DERIVED_FROM` (no epistemic semantics).

**Extensions never become columns on core node tables.** Downstream meaning lives either
(a) **inside the opaque `value` blob**, or (b) on **downstream-owned labels/edges that
reference core states by `state_id`** (R19 inbound-edge tenancy — safe because the core is
append-only). Everything in the NVM sketch that isn't in the table above is an extension:
`provenance`, `valid_from_turn`/`valid_to_turn` (diegetic time), epistemic edge labels
(`WITNESSED_BY`/`TOLD_BY`/`INFERRED_FROM` = labelled specialisations of `DERIVED_FROM`),
`stance` (R21), edge metadata (`source_actor`, `tell_event_id`).

**Beliefs are finite explicit belief bases (Hansson), not deductively-closed sets** — no
DL/OWL inference in the core (DATA-05; Flouris impossibility).

### 4. `query_scope` closed typed filter — **belief-semantic only** (DATA-02 / §10.1)

**The seam was re-mapped before deciding** (this was the §10.1 soft spot, the flagged #1
retroactive-rewrite risk). Resolution grounded in `21 §4/§6/§7`:

- NVM has **two** belief-reading ports, not one. **`BeliefStore`** (doxastica) carries
  belief *semantics* with opaque values — "the core never learns NVM's meanings."
  **`KnowledgeQueries`** (owned by NVM's `adapters/ladybug`, **not** doxastica) does the
  app-specific filtering via named finders + a `raw(cypher, params)` escape, reading the
  core's append-only subgraph by `state_id`.
- Therefore **doxastica's `query_scope` does NOT need arbitrary-property filtering.** NVM
  filters its app properties through its own port. doxastica's subgraph stays closed.
  Abstracting a generic property-query into the belief core is the bloat `05 §1` / `21 §2`
  deliberately decline (the Repository / generic-GraphStore anti-pattern).

**Decision — `query_scope(scope_id, filter, include_deprecated=False)` with a closed,
belief-semantic `BeliefFilter`:**
```python
class BeliefFilter(BaseModel, frozen=True):
    belief_ids: frozenset[str] | None = None      # None = all
    status: frozenset[Status] | None = None
    event_id_min: UUID | None = None
    event_id_max: UUID | None = None
```
- All fields AND-combined; **compiles to a backend query** (no Python post-filtering, no
  ORM/query-builder — the user's explicit instinct, confirmed). Never a free `str`; nothing
  interpolated into Cypher; no triple-structure leak.
- **No generic property filtering.** Standalone (non-NVM) power-users who need richer
  queries read the backend directly — exactly as NVM uses `KnowledgeQueries` — outside the
  portable port.
- **Planner note:** `include_deprecated` (kept in the signature per HIST-01) is **ergonomic
  sugar over `status`**: `False` ≡ `status={active}`, `True` ≡ `status={active, retracted}`;
  if `status` is set explicitly it governs. Removes flag/filter redundancy.

### 5. `get_impact` shape & depth (DATA-04 / §10.3)

**Reframed during discussion** — depth was conflating *termination* with *cost control*.
- **Cycle-safety comes from visited-set / reachable-node-SET semantics, NOT from depth.**
  `traverse()` returns the set of reachable nodes (de-duplicated, visited-set), which
  terminates on cyclic graphs and returns the complete transitive closure. Path-enumeration
  (the combinatorial blow-up) is explicitly avoided.
- **`depth` is an OPTIONAL cost cap, default unbounded (full closure):**
  ```python
  def get_impact(self, belief_state_id: UUID,
                 depth: int | None = None) -> ImpactResult: ...
  ```
  `None` → full transitive closure (`truncated=False`, empty `frontier`). An int caps cost
  on pathological graphs and activates the truncation signal. Principled (the mechanism
  returns the complete fact), matches "consumer usually wants everything," no magic number.
- **Return shape — frozen `ImpactResult`:**
  ```python
  class ImpactResult(BaseModel, frozen=True):
      reached: list[BeliefState]
      frontier: frozenset[UUID]   # boundary state_ids left unexpanded; empty when unbounded
      truncated: bool             # False when unbounded
  ```
  Never silently under-reports (the whole reason DATA-04 exists).
- **Phase 2 spike must confirm** ladybug/Kùzu can express **unbounded cycle-safe
  reachable-set** in one efficient query (Kùzu variable-length sometimes wants an upper
  bound; recursive-join cycle behaviour needs verifying). In-memory backend does unbounded
  visited-set BFS trivially. If ladybug can't, the port/default adjusts in Phase 2 (SC4).
- **`get_impact` is mechanism, not policy** — it returns the impact set; what NVM does with
  it (cascade-contract, mark `under_revision`, re-resolve) is consumer policy. The old
  `depth=5` sketch number is retired.

---

## Code Context

**Greenfield.** The `cookiecutter-python-uv-library` scaffold has **not** been run yet —
repo currently holds only `.planning/`, `CLAUDE.md`, `LICENSE`, `README.md`. No `src/`, no
prior patterns to reuse. PKG-01 (run the scaffold under import name `doxastica`) is part of
this phase.

Reusable assets: none in-repo. The canonical refs above are the design inputs. The recovered
Protocol surface (`05 §3`, reproduced in `21 §4`) is the starting point to refine — note
its `query_scope(query: str)` becomes the typed `BeliefFilter`, and `get_impact(...)→list`
becomes `→ImpactResult`.

---

## Deferred Ideas

- **World-scope identity & bootstrap → Phase 3.** How the privileged world scope is
  identified and created (reserved constant `scope_id` vs caller-configured; auto-create at
  init vs lazy) is deferred to Phase 3 with SCOPE-01/SCOPE-02. Phase 1's only obligation:
  ensure `Scope` carries `is_world` and the models do not preclude a privileged world scope.
  The §10.4 "seed authored invariants — lean yes" is an NVM genesis concern (seeding =
  caller's `expand`/`revise`), not a doxastica API.
- **EdgeType enum exact membership, Scope/Belief field finalisation, BACK-04 port-contract
  spec format** — in scope for Phase 1 *planning* (they fall out of the decisions above);
  not separately discussed as gray areas because the taxonomy (§3) and port granularity (§1)
  already fix them. Planner: the EdgeType enum = `SUPERSEDES`, `DEPENDS_ON`, `DERIVED_FROM`
  (generic), plus the structural `HAS_REVISION`/`CURRENT_STATE` which may or may not belong
  in the same enum.

---

## Open Questions Carried into Planning / Later Phases

- **[Phase 2 spike]** Confirm under the installed `ladybug` package: `IF NOT EXISTS` DDL,
  multi-statement `BEGIN TRANSACTION`/`COMMIT`, `$param` binds, `$depth` in variable-length
  patterns, AND unbounded cycle-safe reachable-set traversal; confirm the LPG-primitive port
  granularity survives and the `get_impact`/`get_scope_at` round-trip budget is acceptable.
- **[Research]** Confirm NVM (primary consumer) targets Python 3.14, validating the raised
  floor.
