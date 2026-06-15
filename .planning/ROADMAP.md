# Roadmap: doxastica

## Overview

doxastica is a standalone, zero-LLM Python library implementing the Kumiho AGM
belief-revision core (NVM's M0 milestone). Its definition of done is not a running app
but a **green property-test suite** — mechanically verified AGM/Hansson postulate
compliance and structural invariants — now run as a **backend conformance suite** over
every registered backend. The architecture has TWO distinct seams: the public
`BeliefStore` Protocol (the unchanged NVM↔core seam consumers code against) and, *below*
it, an internal **backend port** that a backend-agnostic `MemoryCore` writes against
(Ports & Adapters). The journey is strict dependency ordering: settle decision-grade
data-model choices AND define the backend port (deciding its granularity) with zero DB
contact (Phase 1), de-risk the first real LadybugDB contact by standing up BOTH the
`ladybug` reference backend and the in-memory backend behind the port plus the `:memory:`
test harness (Phase 2), build the append-only revision keystone (Phase 3), then layer
retrieval (Phase 4), edges + contraction cascade (Phase 5), and structural time-travel
(Phase 6) — all written against the port so they run on both backends from the start, and
all of which can proceed in parallel once the Phase 3 keystone exists. Phase 7 assembles
the M0 exit gate (the full property suite + irony join) parameterised as a conformance
suite the in-memory oracle and ladybug must pass identically. Phase 8 makes it citable and
shippable (docs including the "how to write a backend" port contract, CI/release, PyPI,
MIT). Every Protocol operation is exit-gate-load-bearing; there is no feature triage, only
dependency ordering.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Protocol, Backend Port & Data-Model Decisions** - Two seams (public `BeliefStore` Protocol + internal backend port), backend port granularity decided, frozen models, and the decision-grade choices (no DB contact) that a rewrite would otherwise cost (completed 2026-06-14)
- [x] **Phase 2: Backend Adapters & Schema Bootstrap (De-risking Spike)** - First real LadybugDB contact: the `ladybug` reference backend (flexible connection, idempotent DDL) AND the in-memory backend, both behind the port, plus the `:memory:` test harness (completed 2026-06-15)
- [ ] **Phase 3: Append-Only Revision Spine (Keystone)** - Scopes, `Belief`/`BeliefState` split, immutable chains, `CURRENT_STATE` pointer, and `revise`/`expand`/`contract` — written against the port, running on both backends
- [ ] **Phase 4: Retrieval & Observation Surface** - `query_scope` with closed typed filter + deprecated/superseded matrix; full `get_revision_chain`
- [ ] **Phase 5: Edge Model & Contraction Cascade** - `add_edge` and bounded, cycle-safe `get_impact` with a truncation signal
- [ ] **Phase 6: Structural Time-Travel** - `get_scope_at` reconstruction under an explicit UUID7 ordering contract
- [ ] **Phase 7: AGM/Hansson Backend Conformance Suite & Irony Join (M0 Exit Gate)** - Assembled, green property suite + structural invariants + recovery xfail + irony join, parameterised over every registered backend (in-memory oracle vs. ladybug)
- [ ] **Phase 8: Publishable Polish** - Docs site (incl. published backend port contract), CI/release pipeline, PyPI-ready packaging, MIT license, README

## Phase Details

### Phase 1: Protocol, Backend Port & Data-Model Decisions

**Goal**: A typed, basedpyright-strict foundation with TWO explicit seams — the public `BeliefStore` Protocol and, below it, the internal backend port the backend-agnostic core writes against — plus the decision-grade data-model choices settled before any storage code exists. Reversing any of these (including the port's granularity) would be a rewrite.
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, PKG-01, BACK-01, BACK-04
**Success Criteria** (what must be TRUE):

  1. The package builds and type-checks (basedpyright strict, ruff clean) from the `cookiecutter-python-uv-library` scaffold under import name `doxastica`, with the public `BeliefStore` Protocol importing only `pydantic`/`typing` and no `ladybug` import anywhere in `protocol.py`
  2. Two seams are explicit and distinct in code: the public `BeliefStore` Protocol (NVM↔core, unchanged) and a separate internal **backend port** abstraction; the `MemoryCore` belief-revision logic is written against the port with NO backend/Cypher-specific code in the core logic layer (BACK-01)
  3. The **backend port granularity is DECIDED and recorded** (Cypher-level vs. LPG-primitive — leaning LPG-primitive), with the named `get_impact`/`get_scope_at` traversal round-trip tension flagged for confirmation in the Phase 2 spike
  4. `query_scope`'s parameter is a closed typed filter over core-owned fields (e.g. `belief_id`, `status`, event-id range) — never a free `str` — so triple structure cannot leak and no value is interpolated into Cypher
  5. The `get_impact` return shape carries a truncation/frontier signal and a ratified `depth` default; a written UUID7 ordering contract for `source_event_id` exists; and frozen `pydantic` v2 models (`Scope`, `BeliefState`, `EdgeType` enum) treat `value: Any` and the UUID7 `source_event_id` as opaque, with beliefs modelled as finite explicit belief bases (no deductive closure / DL inference)
  6. The **backend port contract is drafted** as a written spec (the constraints a third-party LPG backend must meet) — authored here; publication of the consumer-facing docs is finished in Phase 8 (BACK-04, port contract)

**Plans**: 4 plansPlans:
**Wave 1**

- [x] 01-01-PLAN.md — Scaffold the doxastica package (PKG-01): cookiecutter render, deps pinned to ladybug+pydantic, 3.14 floor, hypothesis in dev

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Frozen pydantic taxonomy + errors (DATA-02/04/05/06): Scope, Belief, BeliefState, BeliefFilter, ImpactResult, Status/EdgeType enums

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Public BeliefStore Protocol + import-purity guard + UUID7 ordering contract (DATA-01/02/03/04/05)
- [x] 01-04-PLAN.md — Internal LPG-primitive BackendPort + drafted backend-contract spec (BACK-01/04)

### Phase 2: Backend Adapters & Schema Bootstrap (De-risking Spike)

**Goal**: First real LadybugDB contact, verified before any belief logic stands on it: BOTH backends standing behind the Phase 1 port — the `ladybug` reference backend (flexible connection, idempotent namespaced schema bootstrap) and the in-memory backend (which doubles as the Phase 7 oracle) — plus the `:memory:` test harness scaffold every later phase depends on. Confirms the port survives contact with the real ladybug API.
**Depends on**: Phase 1
**Requirements**: BACK-02, BACK-03, CONN-01, CONN-02, CONN-03, FORMAL-06
**Success Criteria** (what must be TRUE):

  1. The `ladybug` reference backend adapter implements the Phase 1 port over LadybugDB (BACK-02): `MemoryCore(conn, namespace=...)` accepts an injected `ladybug.Connection` it never closes (tenancy R19, CONN-01), and `MemoryCore.open(path | ":memory:", namespace=...)` self-manages its own connection lifecycle
  2. The ladybug backend owns and is the sole writer of its namespaced `:Scope`/`:Belief`/`:BeliefState` tables and edge types as a closed subgraph (no outbound graph references; CONN-02), and schema bootstrap runs idempotently on init (`CREATE NODE/REL TABLE IF NOT EXISTS <ns>_*`; CONN-03)
  3. The in-memory backend adapter implements the SAME port (BACK-03), shipping as the second backend with zero extra dependency — proving the port is real and serving as the Phase 7 shadow-model oracle; it composes naturally with the `:memory:` test harness (FORMAL-06)
  4. The spike confirms against the installed `ladybug` package that the chosen port granularity survives the real API: `IF NOT EXISTS` DDL syntax, multi-statement `BEGIN TRANSACTION`/`COMMIT`, `$param` binds, and `$depth` in variable-length patterns (validated-int workaround documented if unsupported) — AND that `get_impact`/`get_scope_at` do not force an unacceptable number of round-trips under an LPG-primitive port (the named performance tension); the port abstraction is adjusted now if the spike demands it
  5. A `conftest.py` fixture provides a throwaway `:memory:` backend per example (parameterisable across both registered backends) with no shared-path lock errors or state bleed across tests

**Plans**: 4 plans

**Wave 1**

- [x] 02-01-PLAN.md — Driver-free spine: InMemoryBackend oracle + MemoryCore engine/factories + BackendDependencyError (BACK-03)

**Wave 2** *(blocked on Wave 1)*

- [x] 02-02-PLAN.md — LadybugBackend: guarded import, ownership (R19), idempotent namespaced bootstrap, 5 primitives + SC4 traverse (BACK-02/CONN-01/02/03)

**Wave 3** *(blocked on Wave 2)*

- [x] 02-03-PLAN.md — Parametrized conftest + oracle-parity suite (diamond/cycle/over-bound) + import-purity extension (BACK-03/FORMAL-06)

**Wave 4** *(blocked on Wave 3)*

- [x] 02-04-PLAN.md — Option B packaging: pydantic-required/ladybug-extra, uv.lock, two-env CI, [BLOCKING] CLAUDE.md reversal (D-03)

### Phase 3: Append-Only Revision Spine (Keystone)

**Goal**: The keystone the entire postulate suite assumes — scopes (including the privileged world scope), the `Belief`/`BeliefState` split with immutable chains, the single atomic `CURRENT_STATE` pointer, and the three core write operations — implemented against the backend port so it runs on both backends from the start.
**Depends on**: Phase 2
**Requirements**: SCOPE-01, SCOPE-02, SCOPE-03, CHAIN-01, CHAIN-02, CHAIN-03, OPS-01, OPS-02, OPS-03, HIST-02
**Success Criteria** (what must be TRUE):

  1. `get_or_create_scope` creates/returns named belief-holders; multiple scopes exist as independent peers, and a privileged world scope exists where `contract()` raises `WorldScopeContractionError` before any write
  2. `revise` installs a value as the current belief superseding the prior current state; `expand` adds a belief with no conflict check; `contract` marks a belief deprecated (`status='retracted'` state) and never deletes
  3. Each write re-points exactly one `CURRENT_STATE` pointer per belief atomically in a single transaction (a port unit-of-work), and a structural-invariant test confirms `CURRENT_STATE` uniqueness holds after every operation on both backends
  4. No operation deletes or mutates an existing `BeliefState` node or `HAS_REVISION` edge — chain immutability is verified, and `get_revision_chain(belief_id)` returns the full immutable version chain

**Plans**: 4 plans

**Wave 1**

- [x] 03-01-PLAN.md — Structural foundation: WORLD_SCOPE_ID constant + barrel export; HAS_REVISION REL table (hub) + generalized ladybug add_edge endpoints
- [ ] 03-03-PLAN.md — Wave-0 behavior test scaffold (tests/test_revision_spine.py) over both backends

**Wave 2** *(blocked on Wave 1)*

- [ ] 03-02-PLAN.md — MemoryCore op bodies: get_or_create_scope/_current/_append, revise≡expand, contract (D-05), get_revision_chain, value-encoding contract (DEF-02-01)

**Wave 3** *(blocked on Wave 2)*

- [ ] 03-04-PLAN.md — Hypothesis stateful SC3 consistency check + chain-immutability invariants (both backends) + flip the DEF-02-01 xfail

### Phase 4: Retrieval & Observation Surface

**Goal**: The observation surface every postulate test reads through — `query_scope` with the closed typed filter and the deprecated-vs-superseded query matrix — implemented against the port.
**Depends on**: Phase 3
**Requirements**: CHAIN-04, HIST-01
**Success Criteria** (what must be TRUE):

  1. `query_scope(scope, filter, include_deprecated=False)` returns active belief states, and with `include_deprecated=True` also returns deprecated ones, using the Phase 1 closed typed filter (no triple-structure leak)
  2. Deprecated vs. superseded is observable as a structural/query distinction (`include_deprecated` flag + `SUPERSEDES` edge), with the four-cell status matrix (current/superseded x deprecated/active) tested
  3. Under correctly-maintained `CURRENT_STATE` invariants, `query_scope` returns no duplicate beliefs

**Plans**: TBD

### Phase 5: Edge Model & Contraction Cascade

**Goal**: Generic typed edges and the bounded contraction-cascade mechanism that the Relevance and Core-Retainment postulates are tested against — implemented against the port (the bounded var-length traversal primitive confirmed in the Phase 2 spike).
**Depends on**: Phase 3
**Requirements**: EDGE-01, EDGE-02
**Success Criteria** (what must be TRUE):

  1. `add_edge(from_state, to_state, edge_type)` creates generic typed edges (`SUPERSEDES` / `DEPENDS_ON` / `DERIVED_FROM`) with no epistemic semantics in the core
  2. `get_impact(belief_state_id, depth)` performs bounded-depth dependency traversal that terminates on cyclic graphs and returns exactly the reachable-within-depth set
  3. `get_impact` returns the accurate truncation/frontier signal (from the Phase 1 return shape) whenever the cascade is cut off at the depth bound

**Plans**: TBD

### Phase 6: Structural Time-Travel

**Goal**: `get_scope_at` — the most complex single query — reconstructing the active base as of an event, purely structurally from immutable event-id-ordered states under the explicit UUID7 ordering contract, via the port.
**Depends on**: Phase 3, Phase 4
**Requirements**: HIST-03
**Success Criteria** (what must be TRUE):

  1. `get_scope_at(scope, as_of_event_id)` reconstructs the active base as of an event purely from immutable event-id-ordered states (including correct retracted-state handling), with no dependency on timestamp resolution
  2. `get_scope_at(latest) == query_scope(current)` and stepping `as_of` through event ids reconstructs the same result as a fold-over-operations replay
  3. Same-millisecond and out-of-order UUID7 ids generated by Hypothesis resolve correctly under the Phase 1 ordering contract

**Plans**: TBD

### Phase 7: AGM/Hansson Backend Conformance Suite & Irony Join (M0 Exit Gate)

**Goal**: Assemble the M0 exit gate — the mechanically-verified proof that is the library's reason to exist — now parameterised as a **backend conformance suite**: every registered backend must pass the same postulate + invariant tests, with the in-memory backend as the AGM oracle and ladybug conforming identically.
**Depends on**: Phase 4, Phase 5, Phase 6
**Requirements**: FORMAL-01, FORMAL-02, FORMAL-03, FORMAL-04, FORMAL-05, BACK-05
**Success Criteria** (what must be TRUE):

  1. The full suite is **parameterised over every registered backend** (BACK-05): the in-memory backend is the shadow-model oracle, and the ladybug backend must pass the identical postulate + invariant tests with no per-backend assertions
  2. The AGM revision postulate suite (Success K*2, Inclusion K*3, Vacuity K*4, Consistency K*5, Extensionality K*6) passes as Hypothesis stateful tests over operation sequences against the parallel shadow-model oracle (Closure K*1 dropped by construction), and the Hansson base-contraction suite (Contraction Success, Inclusion, Relevance, Core-Retainment, Uniformity) passes
  3. The structural-invariant suite passes as `@invariant` checks on each backend: `CURRENT_STATE` uniqueness, chain immutability, `get_scope_at ≡ replay`, world-scope no-contraction
  4. AGM Recovery is conspicuously absent — present only as a loud named `xfail` with rationale — and positive superseded-chain replacement tests pass in its place
  5. The irony join is demonstrated on synthetic data: actor-scope vs. world-scope divergence on `belief_id` computed as a single query

**Plans**: TBD

### Phase 8: Publishable Polish

**Goal**: Make the green-suite library citable and shippable as a standalone OSS reference implementation, including published documentation of the backend port contract so third parties can write alternative backends.
**Depends on**: Phase 7
**Requirements**: PKG-02, PKG-03, PKG-04
**Success Criteria** (what must be TRUE):

  1. Runtime dependencies are exactly `ladybug` + `pydantic` v2 with zero NVM imports (the in-memory backend adds no dependency), `hypothesis` is in the dev group, and CI runs the green conformance suite on a Python 3.11 (floor) and 3.14 matrix
  2. An MIT license file exists and the README leads with "standalone reference implementation of Kumiho (arXiv 2603.17244), multi-scope extension, no recovery"
  3. A mkdocs-material docs site builds and **publishes the "how to write a backend" port contract** (the consumer-facing form of the BACK-04 spec drafted in Phase 1, via PKG-04 docs), a GitHub Actions CI + release pipeline is configured, packaging is PyPI-ready, and a CHANGELOG is generated via git-cliff

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
(Phases 4, 5, and 6 may proceed in parallel once Phase 3's keystone exists.)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Protocol, Backend Port & Data-Model Decisions | 4/4 | Complete    | 2026-06-14 |
| 2. Backend Adapters & Schema Bootstrap | 4/4 | Complete    | 2026-06-15 |
| 3. Append-Only Revision Spine | 1/4 | In Progress|  |
| 4. Retrieval & Observation Surface | 0/TBD | Not started | - |
| 5. Edge Model & Contraction Cascade | 0/TBD | Not started | - |
| 6. Structural Time-Travel | 0/TBD | Not started | - |
| 7. AGM/Hansson Backend Conformance Suite & Irony Join | 0/TBD | Not started | - |
| 8. Publishable Polish | 0/TBD | Not started | - |
