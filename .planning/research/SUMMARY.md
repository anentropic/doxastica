# Project Research Summary

**Project:** doxastica
**Domain:** Graph-native AGM/Hansson belief-revision Python library (standalone Kumiho implementation, arXiv 2603.17244) — NVM's M0 milestone
**Researched:** 2026-06-13
**Confidence:** HIGH

---

## Executive Summary

doxastica is a formally-grounded, append-only belief-revision library implementing the Kumiho architecture (arXiv 2603.17244) with two deliberate extensions — multi-scope support (Kumiho is single-agent) and structural time-travel (`get_scope_at`) — and one deliberate exclusion (AGM recovery, incompatible with immutable versioning). The library's reason to exist is not the API, but the mechanically-verified proof: a Hypothesis property suite over operation sequences demonstrating AGM/Hansson postulate compliance on finite belief bases. That suite, together with structural invariants, is the M0 exit gate and the formal grounding that makes the library citable. All nine Protocol operations are exit-gate-load-bearing; there is no triage, only dependency ordering.

The recommended approach is to build in strict dependency order: typed models and the `BeliefStore` Protocol first (no DB contact), then the LadybugDB connection model and idempotent schema bootstrap (the de-risking spike — verify the actual Kùzu-lineage API before any belief logic stands on it), then the append-only revision spine (`revise`/`expand` + chains + `CURRENT_STATE` pointer), then contraction and retrieval (`contract`, `query_scope`, `get_revision_chain`), then edge traversal (`add_edge`, `get_impact`), then time-travel (`get_scope_at`), and finally the full property-test suite and publishable polish. The Hypothesis test harness (`:memory:` per example, `@precondition` not `assume()`, parallel model) must be scaffolded before the first postulate test.

The critical risk cluster has four members that must be settled before any storage code exists: (1) the `query_scope(query: str)` parameter is underspecified and risks leaking triple structure into a domain-agnostic core — define it as a closed typed filter on core-owned fields only; (2) AGM recovery must be explicitly excluded from the property suite with a loud named xfail, because it is false for bases and its presence would cause correct code to "fail"; (3) the `get_scope_at` time-travel invariant requires an explicit UUID7 ordering contract (intra-ms monotonicity is optional per RFC 9562, but the core receives ids as opaque caller inputs); (4) the library depends on `ladybug` (PyPI package, import `ladybug as lb`, v0.17.x) — NOT `ladybugdb`, which does not exist on PyPI and will fail to resolve.

---

## Key Findings

### Recommended Stack

The runtime dependency set is exactly two packages: `ladybug>=0.17,<0.18` (the pinned storage substrate, a Kuzu fork with identical Python API) and `pydantic>=2.11,<3` (typed boundary models, frozen for immutable `BeliefState`). This is a hard constraint from the project, not a recommendation. The dev group adds `hypothesis>=6.155` (the AGM property-test engine — not in the cookiecutter template by default and must be added explicitly) and optionally `uuid-utils>=0.16` for UUID7 generation on Python 3.11–3.13 (the core never mints event ids at runtime; generation is the caller's responsibility, so this is test-only). Primary CI matrix: Python 3.11 (floor) and 3.14 (gets native `uuid.uuid7()`).

**Core technologies:**
- `ladybug` (PyPI) v0.17.x: embedded graph DB + Cypher, storage substrate — pinned by design; Kuzu-lineage single-writer model enforces write serialization for free. Import as `import ladybug as lb`. CRITICAL: NOT `ladybugdb` (that is the org/brand, not the PyPI package).
- `pydantic` v2: typed API boundary models (`Scope`, `BeliefState`) — frozen models for immutable states; constraint says pydantic.
- `hypothesis` v6.155 (dev): AGM property-test engine — `RuleBasedStateMachine` for stateful postulate verification over operation sequences; must be added to the dev dependency group explicitly.
- `uuid-utils` v0.16 (dev, optional): UUID7 generation for Python 3.11–3.13 test matrix — runtime UUID7 generation is not needed (caller supplies event ids).
- cookiecutter-python-uv-library toolchain: uv + basedpyright strict + ruff + pytest + pytest-cov + mkdocs-material — all pins current, no re-litigation needed.

### Expected Features (= the M0 exit gate)

For this library "features" are formal correctness obligations and the structural mechanisms that make them testable. There is no triage: all nine Protocol operations are exit-gate-load-bearing.

**Must have — all nine Protocol operations:**
- `get_or_create_scope` (including privileged world scope where `contract()` raises) — precondition for everything
- `revise`, `expand`, `contract` — the operations the AGM/Hansson postulates are about
- `add_edge` (SUPERSEDES / DEPENDS_ON / DERIVED_FROM) — substrate for Relevance/Core-Retainment
- `query_scope(scope, query, include_deprecated)` — the observation surface; `query` semantics is the #1 open question
- `get_revision_chain` — observes chain immutability
- `get_scope_at` — structural time-travel; the `equiv replay` invariant
- `get_impact(belief_state_id, depth)` — bounded contraction-cascade traversal; truncation must be signalled

**Must have — formal correctness obligations (the differentiator):**
- AGM revision postulates K*2–K*6 (Success, Inclusion, Vacuity, Consistency, Extensionality) as Hypothesis property tests
- Hansson base contraction postulates (Contraction Success, Inclusion, Relevance, Core-Retainment, Uniformity)
- Structural invariants: `CURRENT_STATE` uniqueness, chain immutability, `get_scope_at equiv replay`, world-scope no-contraction
- Recovery postulate explicitly EXCLUDED with a named xfail; superseded-chain replacement tests asserted instead
- Irony join demonstrated on synthetic data: actor-scope vs. world-scope divergence as one Cypher query

**Differentiators beyond Kumiho paper:**
- Multi-scope extension (Kumiho is single-agent) enabling the irony join
- Structural time-travel (`get_scope_at`) as a first-class Protocol operation
- Superseded-chain semantics replacing Recovery — honest observable history rather than the recovery fiction
- Publishable polish: MIT license, mkdocs-material docs site, GitHub Actions CI/release, PyPI-ready

**Defer (permanently out of scope):**
- K*7/K*8 iterated-revision postulates (NVM-policy territory)
- AGM Recovery postulate
- Any NVM/game/narrative/LLM concept
- Storage abstraction over LadybugDB
- The Chronicle, prospective indexing, epistemic edge labels, stance/entrenchment policy

### Architecture Approach

The architecture is a thin, strongly-seamed library: a `BeliefStore` `typing.Protocol` (imports `pydantic`/`typing` only, never `ladybug`) as the public seam, one concrete implementation `MemoryCore`, and the LadybugDB/Cypher layer accessed through a connection-provider that abstracts only ownership (injected vs. self-managed), not storage. All Cypher lives in `queries.py`; schema DDL lives in `schema.py`; connection lifecycle in `connection.py`. The connection model is: `MemoryCore.__init__(conn: lb.Connection, *, namespace: str)` for NVM's injected path (core never closes it — tenancy R19), and `MemoryCore.open(path | ":memory:", *, namespace: str)` for standalone/test use.

**Major components:**
1. `protocol.py` — `BeliefStore(Protocol)` + `EdgeType` enum; no `ladybug` import; the seam NVM codes against
2. `models.py` + `ids.py` + `errors.py` — `Scope`/`BeliefState` pydantic models (frozen), UUID7 helper, typed errors
3. `connection.py` — `InjectedConnection` / `ManagedConnection`; lifecycle ownership only, not a storage abstraction
4. `schema.py` — idempotent DDL bootstrap (`CREATE NODE/REL TABLE IF NOT EXISTS <ns>_*`); runs on every `MemoryCore` init
5. `queries.py` — all Cypher templates, namespace-parameterised; table names via f-strings, values via `$param`
6. `core.py` — `MemoryCore`: orchestrates schema bootstrap, query execution, row-to-model mapping, invariant enforcement
7. `tests/` — Hypothesis stateful suite + structural invariant tests + irony-join demo; all use throwaway `:memory:` DBs

**Key schema decisions (load-bearing):**
- `BeliefState.state_id` PRIMARY KEY = the caller-supplied `source_event_id` (UUID7) — free uniqueness + makes `get_scope_at` a `WHERE state_id <= $as_of` scan
- `Belief.belief_id` PK = synthesized `f"{scope_id}::{belief_id}"` (LadybugDB has no composite PK) with a `belief_id_logical` property for cross-scope irony joins
- `CURRENT_STATE` uniqueness enforced by construction (transactional delete-old + create-new) + Hypothesis `@invariant`, NOT by a DB constraint (LadybugDB has no UNIQUE — only PRIMARY KEY)
- One rel table per edge type for named-rel traversal in `get_impact` (`-[:<ns>_DEPENDS_ON*1..5]->`)
- `value: STRING` holding JSON — opaque encoding; core does `json.dumps`/`json.loads` at the boundary and never inspects structure

### Critical Pitfalls

1. **`ladybug` vs `ladybugdb` package name** — `ladybugdb` returns 404 on PyPI. Every `pyproject.toml` entry and import must be `ladybug`. First task in scaffolding.

2. **`query_scope(query: str)` leaks triple structure** — the free `str` parameter invites Cypher-fragment injection and value-content inspection, both of which violate the domain-agnostic seam. Define `query` as a closed typed filter over core-owned fields before any implementation. Never interpolate `query` into a Cypher string.

3. **Recovery postulate in the test suite** — Recovery is false for belief bases (theorem). Including it in the Hypothesis suite causes correct code to fail; someone "fixes" it by reintroducing retcon. Mitigation: named xfail with rationale comment; assert the positive superseded-chain replacement instead.

4. **`get_scope_at` UUID7 ordering contract** — intra-millisecond UUID7 monotonicity is optional per RFC 9562; the core receives event ids as opaque caller inputs. Define the byte-order ordering contract explicitly or add a core-owned sequence tie-breaker. Validate with same-millisecond Hypothesis-generated ids.

5. **`CURRENT_STATE` uniqueness violated** — the re-point (delete old edge, create new) must be one atomic transaction. Use `BEGIN TRANSACTION`/`COMMIT` for every multi-statement write. Add `@invariant` check after every Hypothesis step.

6. **Append-only discipline broken / world-scope `contract()` silent** — contraction must mark (create `status='retracted'` state) never delete. World-scope `contract()` must raise `WorldScopeContractionError` before any write. Add a CI lint that fails if `DELETE`/`SET` appears against `BeliefState`/`HAS_REVISION`.

7. **Hypothesis `assume()` starvation + flaky stateful tests** — use `@precondition` not `assume()`. Ensure fresh `:memory:` DB per example, event ids drawn from Hypothesis strategies, parallel shadow model for shrinking.

8. **LadybugDB test isolation** — single-writer + file-lock means tests sharing an on-disk DB path hit lock errors or silent state bleed. Use `:memory:` per test (fastest, auto-isolated, no cleanup).

---

## Implications for Roadmap

### Phase 1: Protocol, Models, and Data-Model Decisions

**Rationale:** Three foundational decisions must be settled before any DB contact: (a) `query_scope` filter semantics — the #1 open question and the single biggest retroactive-rewrite risk; (b) UUID7 ordering contract — determines whether `get_scope_at` needs a core sequence tie-breaker; (c) recovery exclusion rationale documented. Building `protocol.py`, `models.py`, `ids.py`, and `errors.py` in the same phase gives a typed, basedpyright-strict foundation with zero DB contact. Belief-bases-not-sets framing and the deprecated-vs-superseded status model are also settled here.

**Delivers:** `BeliefStore` Protocol, `EdgeType` enum, `Scope`/`BeliefState` pydantic models, UUID7 helper, typed error classes, settled `query_scope` filter signature (closed typed `ScopeQuery` or equivalent), documented ordering contract, recovery exclusion documented.

**Avoids:** Triple-structure leak into core; recovery trap; UUID7 ordering ambiguity.

**Research flag:** `query_scope` filter semantics needs a brief design session against `05-nvm-memory-core.md §10.1` before the signature is locked. No full research phase needed.

---

### Phase 2: LadybugDB Connection Model and Schema Bootstrap (De-risking Spike)

**Rationale:** First real LadybugDB contact. Every subsequent phase builds on assumptions about DDL idempotency (`IF NOT EXISTS` syntax), transaction semantics (`BEGIN TRANSACTION`/`COMMIT` over multiple statements), parameter passing (`$param` bind dicts), and in-memory mode. Verify them here before any belief logic stands on them. Also establishes the test harness scaffold (`:memory:` fixture, `conftest.py`) that every subsequent phase depends on.

**Delivers:** `connection.py` (`InjectedConnection` + `ManagedConnection`), `schema.py` (idempotent DDL for all `<ns>_*` node/rel tables), `MemoryCore.__init__` and `MemoryCore.open()` shells, namespace-prefix validation. Test harness fixture scaffold. Spike confirming: `IF NOT EXISTS` DDL syntax, multi-statement transactions, `$param` in queries, `$depth` in variable-length patterns (if not supported, note the validated-int workaround).

**Avoids:** Double-opening a `Database` in injected mode; test bleed from shared DB paths; building belief logic on unverified API assumptions.

**Research flag:** Standard patterns — LadybugDB API verified. The spike IS the research. No separate research phase.

---

### Phase 3: Core Write Operations — Append-Only Revision Spine

**Rationale:** The `Belief`/`BeliefState` split with immutable `HAS_REVISION` chains and the single mutable `CURRENT_STATE` pointer is the keystone the entire postulate suite assumes. `CURRENT_STATE` uniqueness invariant and the world-scope guard on `contract()` must be wired in this same phase — not deferred.

**Delivers:** `get_or_create_scope` (including world scope flag), `revise`, `expand`, `contract` (world-scope error path + `status='retracted'` marking), `get_revision_chain`. Structural invariant tests: `CURRENT_STATE` uniqueness after every op, chain immutability (no DELETE/SET on chain nodes/edges), world-scope contract raises.

**Avoids:** Non-atomic re-point; silent world-scope contraction; history rewriting.

**Research flag:** Standard patterns — transaction wrapping and CURRENT_STATE pointer semantics fully designed in ARCHITECTURE.md.

---

### Phase 4: Retrieval and Observation Surface

**Rationale:** `query_scope` (with `include_deprecated`) and `get_revision_chain` are the observation surface every postulate test reads through. Implement and test the deprecated-vs-superseded query matrix (four-cell: current/superseded x deprecated/active) before building the Hypothesis suite that relies on these queries.

**Delivers:** `query_scope` (with closed `ScopeQuery` filter, `include_deprecated` flag), full `get_revision_chain`. Four-cell status matrix tests; no duplicates under correctly-maintained invariants.

**Avoids:** `query_scope` triple-structure leak (filter type already decided in Phase 1).

**Research flag:** No research needed if Phase 1 resolved filter semantics.

---

### Phase 5: Edge Model and Contraction Cascade

**Rationale:** `add_edge` and `get_impact` depend on Phase 3 chains. The Relevance and Core-Retainment postulates cannot be tested until `get_impact` exists. The truncation-signalling question (return shape of `get_impact`) must be resolved here — it is a Protocol return-type decision.

**Delivers:** `add_edge`, `get_impact` (bounded traversal, cycle-safe, truncation signal in return type). Tests: terminates on cyclic graphs; returns exactly reachable-within-depth set; truncation flag accurate.

**Avoids:** Unbounded `*` patterns; silent truncation; cycle-induced runaway.

**Research flag:** Verify `$depth` as bind param in variable-length Cypher — should be confirmed in Phase 2 spike.

---

### Phase 6: Structural Time-Travel (`get_scope_at`)

**Rationale:** Most complex single query; depends on complete chain from Phase 3 and retracted-state semantics from Phase 4. The `get_scope_at equiv replay` invariant requires UUID7 ordering boundary tests (same-millisecond ids, out-of-order ids).

**Delivers:** `get_scope_at` (with retracted-state handling). Structural invariant tests: `get_scope_at(latest) == query_scope(current)`; stepping `as_of` through event ids reconstructs fold-over-operations replay; same-millisecond Hypothesis id boundary cases pass.

**Avoids:** Timestamp-resolution dependency in ordering.

**Research flag:** Standard patterns — Cypher fully sketched in ARCHITECTURE.md.

---

### Phase 7: AGM/Hansson Property Suite, Structural Invariants, and Irony Join

**Rationale:** All nine Protocol operations are now implemented. Assemble the M0 exit gate. The irony join adds no new operation — it is a query pattern over existing scopes and `CURRENT_STATE` pointers and is cheap once multi-scope + `query_scope` exist.

**Delivers:** Full AGM K*2–K*6 postulate tests (Recovery conspicuously absent + named xfail + rationale), Hansson base tests (Contraction Success/Inclusion/Relevance/Core-Retainment/Uniformity), structural-invariant tests as `@invariant` in the state machine, irony-join demo on synthetic data. M0 exit gate is green.

**Avoids:** Recovery assertion against correct code; `assume()` starvation; flaky non-deterministic test runs.

**Research flag:** Hypothesis stateful API fully documented and verified in STACK.md. No research phase.

---

### Phase 8: Publishable Polish

**Rationale:** M0 exit gate is green. Make the library citable and shippable.

**Delivers:** mkdocs-material docs site, GitHub Actions CI/release pipeline, PyPI-ready packaging, CHANGELOG via git-cliff, README leading with "standalone reference implementation of Kumiho (arXiv 2603.17244), multi-scope extension, no recovery", MIT license file.

**Research flag:** Standard patterns — cookiecutter template covers all tooling.

---

### Phase Ordering Rationale

- **Decision-before-implementation:** `query_scope` semantics, UUID7 ordering contract, and recovery exclusion are signature/modeling choices whose reversal is a rewrite. They land in Phase 1 before any DB contact.
- **Data-structure keystone:** The `Belief`/`BeliefState` + `CURRENT_STATE` chain (Phase 3) is the prerequisite for contraction + retrieval (Phase 4), edge traversal (Phase 5), and time-travel (Phase 6). Phases 4/5/6 can proceed in parallel from Phase 3.
- **De-risking before building:** Phase 2 validates LadybugDB API assumptions and establishes the test harness scaffold before any belief logic is built on them.
- **Property suite last:** Phase 7 assembles the exit gate only after all operations are implemented and individually tested — it is a verification phase, not a construction phase.

### Research Flags

Phases needing attention during planning:
- **Phase 1:** `query_scope` filter semantics is the #1 unresolved API question. Requires a design decision (not research) against `05-nvm-memory-core.md §10.1` before Phase 1 exits. Also resolve `get_impact` return-type shape (truncation signal) since it is a Protocol signature.
- **Phase 2:** The LadybugDB spike IS the research — verify `IF NOT EXISTS` DDL, multi-statement transaction syntax, and `$depth` bind param in variable-length patterns against the actual installed package.

Phases with standard patterns:
- **Phases 3–6:** Fully designed in ARCHITECTURE.md. Individual spikes sufficient; no research phases.
- **Phase 7:** Hypothesis API verified in STACK.md.
- **Phase 8:** cookiecutter template covers all tooling.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All runtime facts verified against live PyPI + official docs. Package name correction (`ladybug` not `ladybugdb`) is confirmed. UUID7 generation strategy settled. |
| Features | HIGH | AGM/Hansson postulates verified against Stanford Encyclopedia + Flouris impossibility result. API surface taken verbatim from authoritative design `05-nvm-memory-core.md`. All nine operations confirmed exit-gate-load-bearing. |
| Architecture | HIGH | LadybugDB verified as Kuzu fork with compatible API. Schema-first constraint, PRIMARY-KEY-only uniqueness, and single-writer concurrency all confirmed. Cypher sketches for all complex operations provided. |
| Pitfalls | HIGH | Concurrency, UUID7 RFC, and Hypothesis facts verified against docs. AGM/Hansson formal facts grounded in design docs + Flouris result. Design-judgement items (query semantics, truncation signalling) flagged as gaps rather than stated as facts. |

**Overall confidence:** HIGH

### Gaps to Address

- **`query_scope(query: str)` semantics (PROJECT.md §10.1):** Replace free `str` with a closed typed filter on core-owned fields (`belief_id`, `status`, event-id range). Decide the signature before Phase 1 exits — it is the one API shape that has downstream Cypher implications everywhere.

- **`get_impact` return type — truncation signal (PROJECT.md §10.3):** The `depth=5` default is a sketch. Return shape must include a truncation/frontier signal. Decide in Phase 1 (Protocol signature); implement in Phase 5.

- **`$depth` bind parameter in variable-length Cypher patterns:** Kuzu historically required a literal integer bound, not a `$param`. Verify in Phase 2 spike; if unsupported, inline a validated int.

- **`belief_id` synthesized PK vs. composite key:** Schema uses `f"{scope_id}::{belief_id}"` because LadybugDB appears to lack composite-PK-with-uniqueness. Confirm in Phase 2 spike; prefer a true composite key if available.

- **`ladybug` type stubs / `py.typed`:** Unverified. If `lb.Connection`/`lb.execute` return untyped results, add narrowly-scoped basedpyright suppression at the DB-adapter boundary (`queries.py`/`core.py`) — not scattered.

---

## Sources

### Primary (HIGH confidence)
- LadybugDB GitHub: https://github.com/LadybugDB/ladybug (MIT, v0.17.1)
- LadybugDB docs: https://docs.ladybugdb.com/ (Python API, transactions, prepared statements, get-started)
- Kuzu DDL / concurrency / transactions / data types: https://kuzudb.github.io/docs/ (authoritative for the engine; LadybugDB is a Kuzu fork)
- PyPI: `ladybug` 0.17.1 confirmed present; `ladybugdb` confirmed absent (404)
- Hypothesis stateful docs: https://hypothesis.readthedocs.io/en/latest/stateful.html
- Python 3.14 `uuid.uuid7()` + RFC 9562 §6.2 monotonicity: https://docs.python.org/3/library/uuid.html
- Stanford Encyclopedia — Logic of Belief Revision (AGM K*1–K*6, Recovery, Hansson base postulates): https://plato.stanford.edu/entries/logic-belief-revision/
- Flouris et al., Generalizing the AGM postulates (impossibility result for DLs): https://arxiv.org/html/2409.09171
- NVM design (read-only authoritative inputs): `05-nvm-memory-core.md`, `17-kumiho-nvm-recommendations.md`, `15-nvm-milestones.md`, `16-nvm-decision-register.md`, `21-nvm-component-architecture.md`

### Secondary (MEDIUM confidence)
- gdotv.com / dbdb.io: LadybugDB as Kuzu fork, kuzu-compatible Python API
- PyPI version confirmations: pydantic 2.13.4, hypothesis 6.155.2, pytest 9.0.3, basedpyright 1.39.7, ruff 0.15.17, uuid-utils 0.16.0

---
*Research completed: 2026-06-13*
*Ready for roadmap: yes*
