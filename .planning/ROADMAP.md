# Roadmap: doxastica

## Overview

doxastica is a standalone, zero-LLM Python library implementing the Kumiho AGM
belief-revision core (NVM's M0 milestone). Its definition of done is not a running app
but a **green property-test suite** — mechanically verified AGM/Hansson postulate
compliance and structural invariants over a clean `BeliefStore` Protocol. The journey is
strict dependency ordering: settle decision-grade data-model choices with zero DB contact
(Phase 1), de-risk the first real LadybugDB contact and stand up the test harness
(Phase 2), build the append-only revision keystone (Phase 3), then layer retrieval
(Phase 4), edges + contraction cascade (Phase 5), and structural time-travel (Phase 6) —
all of which can proceed in parallel once the Phase 3 keystone exists. Phase 7 assembles
the M0 exit gate (the full property suite + irony join). Phase 8 makes it citable and
shippable (docs, CI/release, PyPI, MIT). Every Protocol operation is exit-gate-load-bearing;
there is no feature triage, only dependency ordering.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Protocol, Models & Data-Model Decisions** - Typed seam, frozen models, and the decision-grade choices (no DB contact) that a rewrite would otherwise cost
- [ ] **Phase 2: Connection Model & Schema Bootstrap (De-risking Spike)** - First real LadybugDB contact: flexible connection, idempotent DDL, and the `:memory:` test harness
- [ ] **Phase 3: Append-Only Revision Spine (Keystone)** - Scopes, `Belief`/`BeliefState` split, immutable chains, `CURRENT_STATE` pointer, and `revise`/`expand`/`contract`
- [ ] **Phase 4: Retrieval & Observation Surface** - `query_scope` with closed typed filter + deprecated/superseded matrix; full `get_revision_chain`
- [ ] **Phase 5: Edge Model & Contraction Cascade** - `add_edge` and bounded, cycle-safe `get_impact` with a truncation signal
- [ ] **Phase 6: Structural Time-Travel** - `get_scope_at` reconstruction under an explicit UUID7 ordering contract
- [ ] **Phase 7: AGM/Hansson Property Suite & Irony Join (M0 Exit Gate)** - Assembled, green property suite + structural invariants + recovery xfail + irony join
- [ ] **Phase 8: Publishable Polish** - Docs site, CI/release pipeline, PyPI-ready packaging, MIT license, README

## Phase Details

### Phase 1: Protocol, Models & Data-Model Decisions
**Goal**: A typed, basedpyright-strict foundation with the decision-grade data-model choices settled before any storage code exists — reversing any of these would be a rewrite.
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, PKG-01
**Success Criteria** (what must be TRUE):
  1. The package builds and type-checks (basedpyright strict, ruff clean) from the `cookiecutter-python-uv-library` scaffold under import name `doxastica`, with no `ladybug` import anywhere in `protocol.py`
  2. `query_scope`'s parameter is a closed typed filter over core-owned fields (e.g. `belief_id`, `status`, event-id range) — never a free `str` — so triple structure cannot leak and no value is interpolated into Cypher
  3. The `get_impact` return shape carries a truncation/frontier signal and a ratified `depth` default, so a depth-bounded cascade can never silently under-report
  4. A written UUID7 ordering contract for `source_event_id` exists (byte-order total order or a core-owned sequence tie-breaker), making `get_scope_at` well-defined under optional intra-ms monotonicity
  5. Frozen `pydantic` v2 models (`Scope`, `BeliefState`, `EdgeType` enum) treat `value: Any` and the UUID7 `source_event_id` as opaque, and beliefs are modelled as finite explicit belief bases (no deductive closure / DL inference)
**Plans**: TBD

### Phase 2: Connection Model & Schema Bootstrap (De-risking Spike)
**Goal**: First real LadybugDB contact, verified before any belief logic stands on it: a flexible connection model, idempotent namespaced schema bootstrap, and the `:memory:` test harness scaffold every later phase depends on.
**Depends on**: Phase 1
**Requirements**: CONN-01, CONN-02, CONN-03, FORMAL-06
**Success Criteria** (what must be TRUE):
  1. `MemoryCore(conn, namespace=...)` accepts an injected `ladybug.Connection` it never closes (tenancy R19), and `MemoryCore.open(path | ":memory:", namespace=...)` self-manages its own connection lifecycle
  2. Schema bootstrap runs idempotently on init (`CREATE NODE/REL TABLE IF NOT EXISTS <ns>_*`), creating only the core's namespaced `:Scope`/`:Belief`/`:BeliefState` tables and edge types as a closed subgraph (no outbound graph references)
  3. The spike confirms against the installed `ladybug` package: `IF NOT EXISTS` DDL syntax, multi-statement `BEGIN TRANSACTION`/`COMMIT`, `$param` binds, and `$depth` in variable-length patterns (with the validated-int workaround documented if unsupported)
  4. A `conftest.py` fixture provides a throwaway `:memory:` LadybugDB per example with no shared-path lock errors or state bleed across tests
**Plans**: TBD

### Phase 3: Append-Only Revision Spine (Keystone)
**Goal**: The keystone the entire postulate suite assumes — scopes (including the privileged world scope), the `Belief`/`BeliefState` split with immutable chains, the single atomic `CURRENT_STATE` pointer, and the three core write operations.
**Depends on**: Phase 2
**Requirements**: SCOPE-01, SCOPE-02, SCOPE-03, CHAIN-01, CHAIN-02, CHAIN-03, OPS-01, OPS-02, OPS-03, HIST-02
**Success Criteria** (what must be TRUE):
  1. `get_or_create_scope` creates/returns named belief-holders; multiple scopes exist as independent peers, and a privileged world scope exists where `contract()` raises `WorldScopeContractionError` before any write
  2. `revise` installs a value as the current belief superseding the prior current state; `expand` adds a belief with no conflict check; `contract` marks a belief deprecated (`status='retracted'` state) and never deletes
  3. Each write re-points exactly one `CURRENT_STATE` pointer per belief atomically in a single transaction, and a structural-invariant test confirms `CURRENT_STATE` uniqueness holds after every operation
  4. No operation deletes or mutates an existing `BeliefState` node or `HAS_REVISION` edge — chain immutability is verified, and `get_revision_chain(belief_id)` returns the full immutable version chain
**Plans**: TBD

### Phase 4: Retrieval & Observation Surface
**Goal**: The observation surface every postulate test reads through — `query_scope` with the closed typed filter and the deprecated-vs-superseded query matrix.
**Depends on**: Phase 3
**Requirements**: CHAIN-04, HIST-01
**Success Criteria** (what must be TRUE):
  1. `query_scope(scope, filter, include_deprecated=False)` returns active belief states, and with `include_deprecated=True` also returns deprecated ones, using the Phase 1 closed typed filter (no triple-structure leak)
  2. Deprecated vs. superseded is observable as a structural/query distinction (`include_deprecated` flag + `SUPERSEDES` edge), with the four-cell status matrix (current/superseded x deprecated/active) tested
  3. Under correctly-maintained `CURRENT_STATE` invariants, `query_scope` returns no duplicate beliefs
**Plans**: TBD

### Phase 5: Edge Model & Contraction Cascade
**Goal**: Generic typed edges and the bounded contraction-cascade mechanism that the Relevance and Core-Retainment postulates are tested against.
**Depends on**: Phase 3
**Requirements**: EDGE-01, EDGE-02
**Success Criteria** (what must be TRUE):
  1. `add_edge(from_state, to_state, edge_type)` creates generic typed edges (`SUPERSEDES` / `DEPENDS_ON` / `DERIVED_FROM`) with no epistemic semantics in the core
  2. `get_impact(belief_state_id, depth)` performs bounded-depth dependency traversal that terminates on cyclic graphs and returns exactly the reachable-within-depth set
  3. `get_impact` returns the accurate truncation/frontier signal (from the Phase 1 return shape) whenever the cascade is cut off at the depth bound
**Plans**: TBD

### Phase 6: Structural Time-Travel
**Goal**: `get_scope_at` — the most complex single query — reconstructing the active base as of an event, purely structurally from immutable event-id-ordered states under the explicit UUID7 ordering contract.
**Depends on**: Phase 3, Phase 4
**Requirements**: HIST-03
**Success Criteria** (what must be TRUE):
  1. `get_scope_at(scope, as_of_event_id)` reconstructs the active base as of an event purely from immutable event-id-ordered states (including correct retracted-state handling), with no dependency on timestamp resolution
  2. `get_scope_at(latest) == query_scope(current)` and stepping `as_of` through event ids reconstructs the same result as a fold-over-operations replay
  3. Same-millisecond and out-of-order UUID7 ids generated by Hypothesis resolve correctly under the Phase 1 ordering contract
**Plans**: TBD

### Phase 7: AGM/Hansson Property Suite & Irony Join (M0 Exit Gate)
**Goal**: Assemble the M0 exit gate — the mechanically-verified proof that is the library's reason to exist — now that all nine Protocol operations are implemented and individually tested.
**Depends on**: Phase 4, Phase 5, Phase 6
**Requirements**: FORMAL-01, FORMAL-02, FORMAL-03, FORMAL-04, FORMAL-05
**Success Criteria** (what must be TRUE):
  1. The AGM revision postulate suite (Success K*2, Inclusion K*3, Vacuity K*4, Consistency K*5, Extensionality K*6) passes as Hypothesis stateful tests over operation sequences with a parallel shadow-model oracle (Closure K*1 dropped by construction)
  2. The Hansson base-contraction suite (Contraction Success, Inclusion, Relevance, Core-Retainment, Uniformity) passes
  3. The structural-invariant suite passes as `@invariant` checks: `CURRENT_STATE` uniqueness, chain immutability, `get_scope_at ≡ replay`, world-scope no-contraction
  4. AGM Recovery is conspicuously absent — present only as a loud named `xfail` with rationale — and positive superseded-chain replacement tests pass in its place
  5. The irony join is demonstrated on synthetic data: actor-scope vs. world-scope divergence on `belief_id` computed as a single query
**Plans**: TBD

### Phase 8: Publishable Polish
**Goal**: Make the green-suite library citable and shippable as a standalone OSS reference implementation.
**Depends on**: Phase 7
**Requirements**: PKG-02, PKG-03, PKG-04
**Success Criteria** (what must be TRUE):
  1. Runtime dependencies are exactly `ladybug` + `pydantic` v2 with zero NVM imports, `hypothesis` is in the dev group, and CI runs the green suite on a Python 3.11 (floor) and 3.14 matrix
  2. An MIT license file exists and the README leads with "standalone reference implementation of Kumiho (arXiv 2603.17244), multi-scope extension, no recovery"
  3. A mkdocs-material docs site builds, a GitHub Actions CI + release pipeline is configured, packaging is PyPI-ready, and a CHANGELOG is generated via git-cliff
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
(Phases 4, 5, and 6 may proceed in parallel once Phase 3's keystone exists.)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Protocol, Models & Data-Model Decisions | 0/TBD | Not started | - |
| 2. Connection Model & Schema Bootstrap | 0/TBD | Not started | - |
| 3. Append-Only Revision Spine | 0/TBD | Not started | - |
| 4. Retrieval & Observation Surface | 0/TBD | Not started | - |
| 5. Edge Model & Contraction Cascade | 0/TBD | Not started | - |
| 6. Structural Time-Travel | 0/TBD | Not started | - |
| 7. AGM/Hansson Property Suite & Irony Join | 0/TBD | Not started | - |
| 8. Publishable Polish | 0/TBD | Not started | - |
