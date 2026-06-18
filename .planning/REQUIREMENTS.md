# Requirements: doxastica

**Defined:** 2026-06-13
**Core Value:** A correct, append-only belief-revision core behind a clean `BeliefStore`
Protocol whose correctness is *provable* — AGM/Hansson postulate compliance and structural
invariants verified mechanically, with zero narrative semantics leaking in.

> **Scoping note.** For this library, v1 = the M0 exit gate. Research found *no feature
> triage*: every Protocol operation and postulate is exit-gate-load-bearing. The roadmap's
> job is dependency ordering, not selection. There is no v2 (mechanism-wise) — post-M0 work
> is NVM-layer (consumes the Protocol) or fidelity refinement.

## v1 Requirements

### Data Model & Protocol Decisions

Foundational, decision-grade choices that must be settled before storage code exists
(reversing any of these is a rewrite).

- [x] **DATA-01**: `BeliefStore` Protocol (`typing.Protocol`) defines the seam — imports only
      `pydantic`/`typing`, never `ladybug`; consumers code against the interface

- [x] **DATA-02**: `query_scope` takes a **closed typed filter** over core-owned fields
      (e.g. `belief_id`, `status`, event-id range) — never a free `str` interpolated into
      Cypher (prevents triple-structure leak and injection)

- [x] **DATA-03**: An explicit **UUID7 ordering contract** for `source_event_id` (byte-order
      total order, or a core-owned sequence tie-breaker) so `get_scope_at` is well-defined
      under optional intra-ms monotonicity (RFC 9562)

- [x] **DATA-04**: `get_impact` return shape carries a **truncation/frontier signal** (so a
      depth-bounded cascade never silently under-reports); `depth` default ratified

- [x] **DATA-05**: Beliefs modelled as finite explicit **belief bases** (Hansson), not
      deductively-closed sets; no DL/OWL inference in the core (Flouris impossibility)

- [x] **DATA-06**: Frozen `pydantic` v2 models for `Scope`, `BeliefState`, and an `EdgeType`
      enum; opaque `value: Any` (JSON-encoded), opaque UUID7 `source_event_id`

### Scopes

- [x] **SCOPE-01**: `get_or_create_scope(scope_id)` creates/returns a named belief-holder
- [x] **SCOPE-02**: A privileged **world scope** exists; `contract()` on it raises
      (`WorldScopeContractionError`) — the no-retcon enforcement point

- [x] **SCOPE-03**: Multiple scopes are independent peers (multi-scope extension to Kumiho),
      enabling cross-scope divergence queries

### Revision Chains (the keystone)

- [x] **CHAIN-01**: `Belief` (stable identity) / `BeliefState` (immutable version) split, one
      belief per `Belief` node

- [x] **CHAIN-02**: Append-only `HAS_REVISION` chain — no operation deletes or mutates an
      existing `BeliefState` or `HAS_REVISION` edge

- [x] **CHAIN-03**: Exactly one mutable `CURRENT_STATE` pointer per belief, re-pointed
      atomically (single transaction) on each write

- [x] **CHAIN-04**: Retracted vs. superseded is a **structural/query** distinction
      (`include_retracted` flag + `SUPERSEDES` edge); meaning is left to consumers

### Core Belief Operations

- [x] **OPS-01**: `revise(scope, belief_id, value, source_event_id)` installs `value` as the
      current belief, superseding any prior current state

- [x] **OPS-02**: `expand(scope, belief_id, value, source_event_id)` adds a belief with no
      conflict check (the AGM expansion reference operation)

- [x] **OPS-03**: `contract(scope, belief_id, source_event_id)` marks the belief deprecated
      (creates a `status='retracted'` state) — never deletes; world-scope guarded

### Edges & Contraction Cascade

- [x] **EDGE-01**: `add_edge(from_state, to_state, edge_type)` for generic typed edges
      `SUPERSEDES` / `DEPENDS_ON` / `DERIVED_FROM` (no epistemic semantics in core)

- [ ] **EDGE-02**: `get_impact(belief_state_id, depth)` performs bounded-depth, cycle-safe
      dependency traversal (the contraction cascade *mechanism*; policy is the consumer's)

### History & Retrieval

- [x] **HIST-01**: `query_scope(scope, filter, include_retracted=False)` returns active (or,
      with the flag, retracted) belief states — the observation surface

- [x] **HIST-02**: `get_revision_chain(belief_id)` returns the full immutable version chain
- [ ] **HIST-03**: `get_scope_at(scope, as_of_event_id)` reconstructs the active base as of an
      event, purely structurally from immutable event-id-ordered states (time-travel)

### Backends & Ports (Ports & Adapters)

- [x] **BACK-01**: The belief-revision discipline lives in a **backend-agnostic core**
      (`MemoryCore`) above a defined **backend port**; no backend/Cypher-specific code in the
      core logic layer. Port *granularity* (Cypher-level vs. LPG-primitive) decided in Phase 1

- [x] **BACK-02**: **`ladybug` reference backend adapter** implements the port over LadybugDB
- [x] **BACK-03**: **In-memory backend adapter** ships as the second backend — proves the port
      is real and doubles as the Phase 7 shadow-model test oracle (zero extra dependency)

- [x] **BACK-04**: The backend port contract is **documented** so a third party can write an
      alternative backend for any labelled property graph meeting the documented constraint

- [ ] **BACK-05**: The AGM/Hansson property suite runs as a **backend conformance suite** —
      parameterised so every registered backend must pass the same postulate + invariant tests

### Connection & Tenancy (ladybug backend)

- [x] **CONN-01**: **Flexible connection** — the ladybug backend accepts an injected
      `ladybug.Connection` + namespace (never closed by the core; tenancy R19) *and* can
      self-manage its own (`open(path | ":memory:", namespace=...)`)

- [x] **CONN-02**: **Label-family tenancy** — the ladybug backend owns and is the only writer
      of its namespaced `:Scope` / `:Belief` / `:BeliefState` tables and edge types; closed
      subgraph (no outbound graph references — entity mentions are opaque values)

- [x] **CONN-03**: Idempotent schema bootstrap (`CREATE NODE/REL TABLE IF NOT EXISTS`) on init;
      uniqueness enforced structurally (LadybugDB/Kùzu has no UNIQUE constraint)

### Formal Correctness (the differentiator — the M0 exit gate)

- [ ] **FORMAL-01**: AGM revision postulate suite green via Hypothesis stateful tests over
      operation sequences: **Success (K*2), Inclusion (K*3), Vacuity (K*4), Consistency (K*5),
      Extensionality (K*6)** — Closure (K*1) dropped by construction (bases)

- [ ] **FORMAL-02**: Hansson belief-base postulate suite green: **Contraction Success,
      Inclusion, Relevance, Core-Retainment, Uniformity**

- [ ] **FORMAL-03**: Structural-invariant suite green: `CURRENT_STATE` uniqueness, chain
      immutability, `get_scope_at ≡ replay`, world-scope no-contraction

- [ ] **FORMAL-04**: AGM **Recovery deliberately excluded** — a loud, named `xfail` with
      rationale, plus positive superseded-chain replacement tests (no Recovery assertion)

- [ ] **FORMAL-05**: The **irony join** demonstrated on synthetic data — actor-scope vs.
      world-scope divergence on `belief_id` computed as one query

- [x] **FORMAL-06**: Test harness uses throwaway `:memory:` LadybugDB per example,
      `@precondition` (not `assume()`), with a parallel shadow model for the AGM oracle

### Packaging & Publication

- [x] **PKG-01**: Scaffolded from `cookiecutter-python-uv-library` (uv, basedpyright strict,
      ruff, pytest + coverage, pre-commit, git-cliff); import name `doxastica`

- [ ] **PKG-02**: Runtime deps **`ladybug` + `pydantic` v2 only**, zero NVM imports;
      `hypothesis` added to the dev group; CI matrix Python 3.11 (floor) and 3.14

- [ ] **PKG-03**: **MIT** license; README leads with "standalone reference implementation of
      Kumiho (arXiv 2603.17244), multi-scope extension, no recovery"

- [ ] **PKG-04**: mkdocs-material docs site (including the published backend port "how to write
      a backend" contract — the consumer-facing form of BACK-04), GitHub Actions CI + release
      pipeline, PyPI-ready packaging, CHANGELOG via git-cliff

## v2 Requirements

None (mechanism-wise). Post-M0 work is NVM-layer (consumes the Protocol) or fidelity
refinement of soft spots, and is out of this library's scope.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| AGM Recovery postulate | False for belief bases (theorem); incompatible with immutable observable history; superseded-chain semantics is the better replacement |
| Any narrative / game / LLM concept (actors, turns, scenes, plausibility, diegetic time, GM assembly) | Each appearance is the leak the Protocol seam exists to prevent; meaning lives in the NVM layer above |
| Non-LPG / config-style storage abstraction | A graph **backend port** IS now in scope (BACK-01..05); but backends that don't model a labelled property graph (relational/document, unless emulating an LPG) and ORM/config-style indirection stay out. The port sits below the unchanged NVM↔core seam |
| Epistemic edge labels (`WITNESSED_BY`, `TOLD_BY`, `INFERRED_FROM`) | NVM *specialisations* of generic edges; epistemic meaning is narrative semantics |
| Stance / entrenchment policy (confidence arithmetic, ordering, contradiction resolution) | NVM-layer policy (R21); the core stores opaque values and traverses edges only |
| Deductive closure / OWL / DL inference in the graph | Flouris impossibility: no AGM-compliant operator exists for DLs; voids the correctness story |
| The Chronicle / prospective indexing | RAG/document concern; NVM-side add-on outside the core boundary |
| LLM semantic merge of revisions | Non-deterministic; breaks formal guarantees (paper rejects it). One-belief-per-node makes partial updates trivial |
| Owning the database / entity nodes / topology / planner cache | Forces game concepts into the API; the core is a *tenant* (R19), subgraph closed |
| K*7 / K*8 supplementary (iterated-revision) postulates | Paper flags as open questions; iterated-revision entrenchment is NVM policy; not in the exit gate |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| DATA-05 | Phase 1 | Complete |
| DATA-06 | Phase 1 | Complete |
| PKG-01 | Phase 1 | Complete |
| BACK-01 | Phase 1 | Complete |
| BACK-04 | Phase 1 | Complete |
| BACK-02 | Phase 2 | Complete |
| BACK-03 | Phase 2 | Complete |
| CONN-01 | Phase 2 | Complete |
| CONN-02 | Phase 2 | Complete |
| CONN-03 | Phase 2 | Complete |
| FORMAL-06 | Phase 2 | Complete |
| SCOPE-01 | Phase 3 | Complete |
| SCOPE-02 | Phase 3 | Complete |
| SCOPE-03 | Phase 3 | Complete |
| CHAIN-01 | Phase 3 | Complete |
| CHAIN-02 | Phase 3 | Complete |
| CHAIN-03 | Phase 3 | Complete |
| OPS-01 | Phase 3 | Complete |
| OPS-02 | Phase 3 | Complete |
| OPS-03 | Phase 3 | Complete |
| HIST-02 | Phase 3 | Complete |
| CHAIN-04 | Phase 4 | Complete |
| HIST-01 | Phase 4 | Complete |
| EDGE-01 | Phase 5 | Complete |
| EDGE-02 | Phase 5 | Pending |
| HIST-03 | Phase 6 | Pending |
| FORMAL-01 | Phase 7 | Pending |
| FORMAL-02 | Phase 7 | Pending |
| FORMAL-03 | Phase 7 | Pending |
| FORMAL-04 | Phase 7 | Pending |
| FORMAL-05 | Phase 7 | Pending |
| BACK-05 | Phase 7 | Pending |
| PKG-02 | Phase 8 | Pending |
| PKG-03 | Phase 8 | Pending |
| PKG-04 | Phase 8 | Pending |

**Coverage:**

- v1 requirements: 39 total (34 prior + 5 new BACK-01..05; CONN-01..03 reframed to the ladybug backend, not added)
- Mapped to phases: 39 ✓
- Unmapped: 0 ✓
- Double-mapped: 0 ✓ (BACK-04's documented contract is drafted in Phase 1 and published via PKG-04 in Phase 8 — primary home is Phase 1; Phase 8 references it through PKG-04, not a second mapping)

---
*Requirements defined: 2026-06-13*
*Last updated: 2026-06-13 after backend-port revision (BACK-01..05 added, CONN-01..03 reframed, traceability re-validated at 39/39)*
