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

- [ ] **DATA-01**: `BeliefStore` Protocol (`typing.Protocol`) defines the seam — imports only
      `pydantic`/`typing`, never `ladybug`; consumers code against the interface
- [ ] **DATA-02**: `query_scope` takes a **closed typed filter** over core-owned fields
      (e.g. `belief_id`, `status`, event-id range) — never a free `str` interpolated into
      Cypher (prevents triple-structure leak and injection)
- [ ] **DATA-03**: An explicit **UUID7 ordering contract** for `source_event_id` (byte-order
      total order, or a core-owned sequence tie-breaker) so `get_scope_at` is well-defined
      under optional intra-ms monotonicity (RFC 9562)
- [ ] **DATA-04**: `get_impact` return shape carries a **truncation/frontier signal** (so a
      depth-bounded cascade never silently under-reports); `depth` default ratified
- [ ] **DATA-05**: Beliefs modelled as finite explicit **belief bases** (Hansson), not
      deductively-closed sets; no DL/OWL inference in the core (Flouris impossibility)
- [ ] **DATA-06**: Frozen `pydantic` v2 models for `Scope`, `BeliefState`, and an `EdgeType`
      enum; opaque `value: Any` (JSON-encoded), opaque UUID7 `source_event_id`

### Scopes

- [ ] **SCOPE-01**: `get_or_create_scope(scope_id)` creates/returns a named belief-holder
- [ ] **SCOPE-02**: A privileged **world scope** exists; `contract()` on it raises
      (`WorldScopeContractionError`) — the no-retcon enforcement point
- [ ] **SCOPE-03**: Multiple scopes are independent peers (multi-scope extension to Kumiho),
      enabling cross-scope divergence queries

### Revision Chains (the keystone)

- [ ] **CHAIN-01**: `Belief` (stable identity) / `BeliefState` (immutable version) split, one
      belief per `Belief` node
- [ ] **CHAIN-02**: Append-only `HAS_REVISION` chain — no operation deletes or mutates an
      existing `BeliefState` or `HAS_REVISION` edge
- [ ] **CHAIN-03**: Exactly one mutable `CURRENT_STATE` pointer per belief, re-pointed
      atomically (single transaction) on each write
- [ ] **CHAIN-04**: Deprecated vs. superseded is a **structural/query** distinction
      (`include_deprecated` flag + `SUPERSEDES` edge); meaning is left to consumers

### Core Belief Operations

- [ ] **OPS-01**: `revise(scope, belief_id, value, source_event_id)` installs `value` as the
      current belief, superseding any prior current state
- [ ] **OPS-02**: `expand(scope, belief_id, value, source_event_id)` adds a belief with no
      conflict check (the AGM expansion reference operation)
- [ ] **OPS-03**: `contract(scope, belief_id, source_event_id)` marks the belief deprecated
      (creates a `status='retracted'` state) — never deletes; world-scope guarded

### Edges & Contraction Cascade

- [ ] **EDGE-01**: `add_edge(from_state, to_state, edge_type)` for generic typed edges
      `SUPERSEDES` / `DEPENDS_ON` / `DERIVED_FROM` (no epistemic semantics in core)
- [ ] **EDGE-02**: `get_impact(belief_state_id, depth)` performs bounded-depth, cycle-safe
      dependency traversal (the contraction cascade *mechanism*; policy is the consumer's)

### History & Retrieval

- [ ] **HIST-01**: `query_scope(scope, filter, include_deprecated=False)` returns active (or,
      with the flag, deprecated) belief states — the observation surface
- [ ] **HIST-02**: `get_revision_chain(belief_id)` returns the full immutable version chain
- [ ] **HIST-03**: `get_scope_at(scope, as_of_event_id)` reconstructs the active base as of an
      event, purely structurally from immutable event-id-ordered states (time-travel)

### Connection & Tenancy

- [ ] **CONN-01**: **Flexible connection** — `MemoryCore(conn, namespace=...)` accepts an
      injected `ladybug.Connection` (never closed by the core; tenancy R19) *and*
      `MemoryCore.open(path | ":memory:", namespace=...)` self-manages its own
- [ ] **CONN-02**: **Label-family tenancy** — the core owns and is the only writer of its
      namespaced `:Scope` / `:Belief` / `:BeliefState` tables and edge types; closed subgraph
      (no outbound graph references — entity mentions are opaque values)
- [ ] **CONN-03**: Idempotent schema bootstrap (`CREATE NODE/REL TABLE IF NOT EXISTS`) on init;
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
- [ ] **FORMAL-06**: Test harness uses throwaway `:memory:` LadybugDB per example,
      `@precondition` (not `assume()`), with a parallel shadow model for the AGM oracle

### Packaging & Publication

- [ ] **PKG-01**: Scaffolded from `cookiecutter-python-uv-library` (uv, basedpyright strict,
      ruff, pytest + coverage, pre-commit, git-cliff); import name `doxastica`
- [ ] **PKG-02**: Runtime deps **`ladybug` + `pydantic` v2 only**, zero NVM imports;
      `hypothesis` added to the dev group; CI matrix Python 3.11 (floor) and 3.14
- [ ] **PKG-03**: **MIT** license; README leads with "standalone reference implementation of
      Kumiho (arXiv 2603.17244), multi-scope extension, no recovery"
- [ ] **PKG-04**: mkdocs-material docs site, GitHub Actions CI + release pipeline, PyPI-ready
      packaging, CHANGELOG via git-cliff

## v2 Requirements

None (mechanism-wise). Post-M0 work is NVM-layer (consumes the Protocol) or fidelity
refinement of soft spots, and is out of this library's scope.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| AGM Recovery postulate | False for belief bases (theorem); incompatible with immutable observable history; superseded-chain semantics is the better replacement |
| Any narrative / game / LLM concept (actors, turns, scenes, plausibility, diegetic time, GM assembly) | Each appearance is the leak the Protocol seam exists to prevent; meaning lives in the NVM layer above |
| Storage abstraction over the database | Non-goal; the DI seam is NVM↔core, not core↔DB. Pinned to LadybugDB/Cypher; only the *connection* is flexible |
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
| (pending roadmap) | — | Pending |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 30 ⚠️

---
*Requirements defined: 2026-06-13*
*Last updated: 2026-06-13 after initial definition*
