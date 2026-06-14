# Phase 1: Protocol, Backend Port & Data-Model Decisions - Research

**Researched:** 2026-06-14
**Domain:** Python library API design — `typing.Protocol` seams, frozen `pydantic` v2 models, Ports & Adapters (LPG-primitive backend port), UUID7 ordering contracts, graph-traversal return-shape contracts. **Zero storage code; decision-grade.**
**Confidence:** HIGH (the design is exceptionally well-specified upstream; nearly every choice is already locked in CONTEXT.md and grounded in the NVM design docs). The one MEDIUM area is the LadybugDB traversal-bound behaviour that pressures the `get_impact` default — and that is *already* flagged for the Phase 2 spike, not for resolution here.

## Summary

This phase produces **decisions and typed surfaces, not behaviour** — no DB contact, no Cypher, no installed-package usage. Its deliverables are: the public `BeliefStore` Protocol (imports `pydantic`/`typing` only), an internal **LPG-primitive backend port** abstraction, the frozen `pydantic` v2 models (`Scope`, `Belief`/`BeliefState`, `EdgeType`, `BeliefFilter`, `ImpactResult`), the written UUID7 ordering contract, and the drafted backend-port contract spec (BACK-04). Phase 1 also runs the `cookiecutter-python-uv-library` scaffold under import name `doxastica` (PKG-01).

The research found that **CONTEXT.md has already settled every decision-grade fork** through `/gsd-discuss-phase`, and each is well-grounded in the sibling `narrative-vm` design docs (`05-nvm-memory-core.md`, `21-nvm-component-architecture.md`, `17-kumiho-nvm-recommendations.md`). The researcher's job here is therefore mostly *confirmation + risk-flagging*, not exploration. Two external facts were verified this session: **Python 3.14.2 ships `uuid.uuid7()` natively (monotonic, works)** `[VERIFIED: local 3.14.2 interpreter]`, and **LadybugDB/Kùzu variable-length Cypher traversal requires an upper bound (defaults to 30 if omitted)** `[CITED: docs.ladybugdb.com]` — the latter is the single load-bearing tension for the `get_impact(depth=None)` "unbounded full closure" default, and it confirms (does not change) the existing Phase 2 spike flag.

**Primary recommendation:** Encode every CONTEXT.md decision as typed stubs that **type-check under basedpyright strict** and as a written port-contract doc — do *not* implement any traversal, Cypher, or backend logic. Keep `protocol.py` `ladybug`-free (importable with zero runtime deps beyond `pydantic`/`typing`). Treat the `get_impact` unbounded-default and the LPG-primitive `traverse` round-trip budget as **explicit Phase-2-spike-confirmed** items: write the contract as decided, annotate the named tension inline, do not pre-optimize.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**1. Backend port granularity — LPG-primitive (BACK-01).** The internal backend port exposes **graph primitives, not Cypher**: `upsert_node` / `add_edge` / `match_nodes` / a generic bounded **`traverse`** / a **unit-of-work** transaction context. `MemoryCore` composes these; each backend translates to its native form. **Two seams explicit and distinct in code:** public `BeliefStore` Protocol (NVM↔core, unchanged) and the internal backend port below it. No Cypher/backend-specific code in the `MemoryCore` logic layer. **Traversal via ONE generic primitive:** `traverse(start, edge_types, max_depth) → reachable nodes + frontier`; both `get_impact` and `get_scope_at` compose from it (+ `match_nodes`). **Named tension (flag for Phase 2 spike):** under LPG-primitive, `get_impact`/`get_scope_at` may cost more round-trips than one hand-written Cypher query — Phase 2 SC4 confirms the port survives the real ladybug API and the round-trip budget is acceptable; the port adjusts then if the spike demands it.

**2. BeliefState identity & UUID7 ordering (DATA-03, DATA-06).** PK model — synthesized core-minted `state_id`:
- `state_id`: core-minted **UUID7**, PRIMARY KEY, opaque public addressing handle.
- `source_event_id`: caller-supplied, **opaque, stored, indexed, NON-unique** — ordering + lineage only; core never parses it.
- `belief_id`: stable logical identity (the `Belief` node), one belief per node.
- *Rationale:* multi-scope means one `source_event_id` can produce states in multiple scopes → cannot be PK.

Ordering contract for `get_scope_at`: order by **`(source_event_id` byte-order, `state_id` tiebreak)** → total deterministic order even when caller `source_event_id`s collide intra-ms. **No monotonicity demanded of the caller** (RFC 9562 makes intra-ms UUID7 monotonicity optional). `state_id` (core-minted UUID7) is write-monotonic, so the tiebreak reflects true insertion order.

`state_id` minting & Python floor: core mints `state_id` via **stdlib `uuid.uuid7()`** (native 3.14+, write-monotonic). **`requires-python` raised from `>=3.11` to `>=3.14`** — keeps runtime deps at exactly `ladybug` + `pydantic` (no third dep, no vendored uuid7, no dev shim). Ripples: CLAUDE.md/PROJECT.md "Floor: 3.11" → 3.14; **CI matrix drops 3.11/3.13, runs 3.14 only** (PKG-03, Phase 8); the CLAUDE.md "UUID7 decision" section + `uuid-utils` dev shim are **moot — remove/annotate**.

**3. Core-vs-extension property taxonomy (DATA-06).** Core declares a **closed property set** it reads/writes/interprets structurally; everything else is downstream extension.

| Node | Core properties (the frozen pydantic models) |
|------|----------------------------------------------|
| `Scope` | `scope_id`, `is_world` |
| `Belief` | `belief_id` |
| `BeliefState` | `state_id`, `belief_id`, `scope_id`, `source_event_id`, `value`, `status` |

- `value: Any` — **opaque**, JSON-encoded; core never inspects internals.
- `source_event_id` — opaque, indexed, non-unique.
- `status` — **`active` | `retracted` ONLY**. The NVM sketch's `invalidated`/`under_revision`/`provenance` are **NVM concepts, NOT core**.
- Core edge types: structural `HAS_REVISION`, `CURRENT_STATE` + generic `SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM` (no epistemic semantics).
- **Extensions never become columns on core node tables** — they live (a) inside the opaque `value` blob, or (b) on downstream-owned labels/edges referencing core states by `state_id` (R19 inbound-edge tenancy).
- **Beliefs are finite explicit belief bases (Hansson), not deductively-closed sets** — no DL/OWL inference in core (DATA-05; Flouris impossibility).

**4. `query_scope` closed typed filter — belief-semantic only (DATA-02).** `query_scope(scope_id, filter, include_deprecated=False)` with a closed, belief-semantic `BeliefFilter`:
```python
class BeliefFilter(BaseModel, frozen=True):
    belief_ids: frozenset[str] | None = None      # None = all
    status: frozenset[Status] | None = None
    event_id_min: UUID | None = None
    event_id_max: UUID | None = None
```
All fields AND-combined; **compiles to a backend query** (no Python post-filtering, no ORM/query-builder); never a free `str`; nothing interpolated into Cypher; no triple-structure leak. **No generic property filtering** — power-users read the backend directly (as NVM uses its own `KnowledgeQueries` port). `include_deprecated` is **ergonomic sugar over `status`**: `False` ≡ `status={active}`, `True` ≡ `status={active, retracted}`; explicit `status` governs if set.

**5. `get_impact` shape & depth (DATA-04).** Cycle-safety comes from **visited-set / reachable-node-SET semantics, NOT from depth**. `traverse()` returns the de-duplicated set of reachable nodes (terminates on cyclic graphs, returns complete transitive closure); path-enumeration is avoided. **`depth` is an OPTIONAL cost cap, default unbounded (full closure):**
```python
def get_impact(self, belief_state_id: UUID,
               depth: int | None = None) -> ImpactResult: ...
```
`None` → full transitive closure (`truncated=False`, empty `frontier`). An int caps cost and activates the truncation signal. Return shape — frozen `ImpactResult`:
```python
class ImpactResult(BaseModel, frozen=True):
    reached: list[BeliefState]
    frontier: frozenset[UUID]   # boundary state_ids left unexpanded; empty when unbounded
    truncated: bool             # False when unbounded
```
Never silently under-reports. **Phase 2 spike must confirm** ladybug/Kùzu can express unbounded cycle-safe reachable-set in one efficient query (Kùzu variable-length wants an upper bound; recursive-join cycle behaviour needs verifying). `get_impact` is **mechanism, not policy**. The old `depth=5` sketch number is retired.

### Claude's Discretion

- **EdgeType enum exact membership** falls out of the taxonomy: generic `SUPERSEDES`, `DEPENDS_ON`, `DERIVED_FROM`, **plus** the structural `HAS_REVISION`/`CURRENT_STATE` which *may or may not* belong in the same enum (planner decides — see Open Questions Q1).
- **`Scope`/`Belief` field finalisation** and **BACK-04 port-contract spec format** are in scope for Phase 1 *planning*; they fall out of the locked decisions above.

### Deferred Ideas (OUT OF SCOPE)

- **World-scope identity & bootstrap → Phase 3** (SCOPE-01/02). Phase 1's only obligation: ensure `Scope` carries `is_world` and the models do not preclude a privileged world scope. The §10.4 "seed authored invariants" is an NVM genesis concern, not a doxastica API.
- World-scope `contract()`-raises *enforcement* is Phase 3 (SCOPE-02); Phase 1 only types the surface.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | `BeliefStore` Protocol (`typing.Protocol`); imports only `pydantic`/`typing`, never `ladybug`; consumers code against the interface | Recovered Protocol surface reproduced verbatim from `05 §3` / `21 §4` (see Code Examples). Refinements: `query_scope(query:str)`→`BeliefFilter`; `get_impact(...)→list`→`ImpactResult`; `depth=5`→`depth:int\|None=None`. Import-purity is an enforceable lint contract (`21 §5` rule 5: ports import only `pydantic`/`typing`). |
| DATA-02 | `query_scope` closed typed filter, never free `str` | `BeliefFilter` model defined (locked decision #4). Grounded in `21 §6/§7`: doxastica carries belief *semantics*; arbitrary property-querying is the NVM-owned `KnowledgeQueries` port's job, declined in the core to avoid the Repository/generic-GraphStore anti-pattern (`21 §2`). |
| DATA-03 | UUID7 ordering contract for `source_event_id` so `get_scope_at` is well-defined | `(source_event_id byte-order, state_id tiebreak)` total order (locked decision #2). RFC 9562 §5.7 intra-ms monotonicity is optional — verified `uuid.uuid7()` is write-monotonic on 3.14. |
| DATA-04 | `get_impact` return shape carries truncation/frontier signal; `depth` default ratified | `ImpactResult{reached, frontier, truncated}`, `depth:int\|None=None` default unbounded (locked decision #5). |
| DATA-05 | Beliefs as finite explicit belief bases (Hansson), no DL/OWL inference | Taxonomy decision #3; grounded `17 §3` (one-belief-per-node, strategy ii) + Flouris impossibility. Models carry no closure/inference machinery. |
| DATA-06 | Frozen `pydantic` v2 models `Scope`/`BeliefState`/`EdgeType`; opaque `value: Any`, opaque UUID7 `source_event_id` | All models defined frozen (locked decisions #2,#3). `value: Any` opaque; `source_event_id` opaque/indexed/non-unique. |
| PKG-01 | Scaffold from `cookiecutter-python-uv-library`, import name `doxastica` | Greenfield — scaffold not yet run (verified: only `.planning/`, `CLAUDE.md`, `LICENSE`, `README.md`). uv 0.9.18 + Python 3.14.2 present locally. CLAUDE.md records template tool pins. |
| BACK-01 | Backend-agnostic `MemoryCore` above a defined backend port; port granularity decided | **LPG-primitive** (locked decision #1). Two distinct seams in code. |
| BACK-04 | Backend port contract **drafted** as a written spec (authored here; published Phase 8 via PKG-04) | Port-contract spec format is planner's discretion; constraints enumerated in "Backend Port Contract" section below. |
</phase_requirements>

## Architectural Responsibility Map

This is a single-tier embedded library (no client/server/CDN tiers). The relevant "tiers" are the **layered seams within the package** — the load-bearing architectural distinction this phase exists to establish.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Public API contract (NVM↔core) | `BeliefStore` Protocol (`protocol.py`) | — | The seam consumers code against; `pydantic`/`typing` only, zero `ladybug`. Unchanged from NVM design. |
| Belief-revision discipline (revise/expand/contract/cascade/time-travel) | `MemoryCore` logic layer | backend port | Backend-agnostic; composes port primitives. NO Cypher here (BACK-01). *(Logic is Phases 3–6; Phase 1 only fixes the seam it writes against.)* |
| Graph storage primitives (upsert/add_edge/match/traverse/unit-of-work) | Backend port (Protocol) | concrete adapters (Phase 2) | LPG-primitive granularity; each backend translates to native form. Phase 1 defines the port; adapters are Phase 2 (BACK-02/03). |
| Typed value/identity layer | Frozen `pydantic` v2 models | — | `Scope`/`Belief`/`BeliefState`/`EdgeType`/`BeliefFilter`/`ImpactResult`. The opaque-value ACL boundary. |
| ID minting (`state_id` UUID7) | Core (`MemoryCore`) | stdlib `uuid.uuid7()` | Core mints; caller supplies opaque `source_event_id`. *(Minting is behaviour — Phase 3; Phase 1 fixes the contract.)* |
| Arbitrary app-property filtering | **OUT — belongs to consumer** (NVM's `KnowledgeQueries`) | — | Explicitly declined in the core (`21 §7`); prevents triple-structure leak. |

**Why this matters:** the #1 retroactive-rewrite risk for this phase is misassigning a capability *into* the core that belongs *above* the seam (arbitrary querying) or *below* it (Cypher in `MemoryCore`). The map fixes the three-way cut: Protocol (public) / core logic (port-composing) / backend port (primitive). The plan-checker should verify no task puts Cypher in the core-logic layer and no task adds free-string/arbitrary-property query surface to `BeliefStore`.

## Standard Stack

This phase **writes zero storage code and installs/uses no runtime package** — it scaffolds the project (PKG-01) and authors typed stubs + a contract doc. The stack below is what the scaffold *declares* and what the typed surfaces depend on at author-time. Actual `ladybug` usage is Phase 2.

### Core / Runtime Dependencies (declared by scaffold; not exercised this phase)
| Library | Version pin | Purpose | Why Standard |
|---------|-------------|---------|--------------|
| **pydantic** | `>=2.11,<3` | Frozen typed models at the API boundary (`Scope`, `BeliefState`, `EdgeType`, `BeliefFilter`, `ImpactResult`) | v2 current line; Rust core, `frozen=True` immutable models, ships `py.typed` — plays well with basedpyright strict. The ONLY model dep. `[CITED: CLAUDE.md verified record, PyPI 2.13.4 dated 2026-06]` |
| **ladybug** | `>=0.17,<0.18` | Reference backend's embedded graph DB + Cypher | **Declared in scaffold metadata only this phase.** No import in `protocol.py` (DATA-01). PyPI name is **`ladybug`**, import `ladybug as lb` — NOT `ladybugdb`. `[CITED: CLAUDE.md verified record, PyPI 0.17.1 dated 2026-06-02]` |

### Supporting (dev group; not exercised this phase beyond scaffold)
| Library | Version pin | Purpose | When to Use |
|---------|-------------|---------|-------------|
| **basedpyright** | `>=1.38` (strict) | Static type-check the Protocol + models | Phase 1 success criterion: stubs type-check strict. `[CITED: CLAUDE.md, current 1.39.7]` |
| **ruff** | `>=0.15.1` | Lint + format | Phase 1 success criterion: ruff clean. `[CITED: CLAUDE.md, current 0.15.17]` |
| **pytest** | `>=8` | Test runner (resolves to 9.x) | A few smoke tests this phase (import-purity, model frozen-ness). `[CITED: CLAUDE.md, current 9.0.3]` |
| **hypothesis** | `>=6.155` | AGM property-test engine | **Add to dev group** (not in template). Not exercised in Phase 1 (Phase 7), but declared at scaffold time. `[CITED: CLAUDE.md, 6.155.2]` |
| **uv** (+ `uv_build`) | build `uv_build>=0.9.18` | Env/lock + build backend | `[VERIFIED: local uv 0.9.18]` |

### Standard library (runtime, not a dependency)
| Module | Purpose | Why |
|--------|---------|-----|
| **`uuid` (`uuid.uuid7`)** | Core mints `state_id`; opaque `source_event_id: UUID` typing | **Native in Python 3.14**, RFC 9562 §5.7, monotonic. `[VERIFIED: local 3.14.2 — hasattr(uuid,'uuid7')==True, sample 019ec775-198b-76ab-…]` Avoids a third runtime dep. |
| **`typing` (`Protocol`, `Any`)** | The `BeliefStore` Protocol | Structural typing — consumers implement against interface. |
| **`enum`** | `EdgeType`, `Status` enums | Closed membership. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LPG-primitive port | Cypher-level port (`run(cypher, params)` + tx) | Cypher-level is fewer round-trips for `get_impact`/`get_scope_at` (one query) and trivially portable to any Cypher-speaking LPG — but couples the core to Cypher (a backend dialect leaks into the "backend-agnostic" layer) and excludes the in-memory backend from sharing logic. **CONTEXT locked LPG-primitive**; round-trip cost is the named Phase-2-spike tension. |
| Synthesized `state_id` PK | `source_event_id` as PK | `source_event_id`-as-PK gives free uniqueness + turns `get_scope_at` into a `state_id <= $as_of` scan — but **breaks under multi-scope** (one event → states in multiple scopes). CONTEXT locked synthesized PK. |
| `pydantic` frozen models | dataclasses / attrs / msgspec | dataclasses lack validation at the seam; msgspec = forbidden third runtime dep. Constraint says pydantic v2. |
| `value: Any` opaque | constrain to JSON-string | CONTEXT chose `value: Any` with core-side JSON encoding — keeps the seam ergonomic while staying opaque. |

**Installation (scaffold output; PKG-01):**
```bash
# Phase 1 runs the cookiecutter template, then declares deps in pyproject.toml.
# Runtime deps (declared; ladybug NOT imported anywhere in protocol.py):
#   pydantic>=2.11,<3 ; ladybug>=0.17,<0.18
# Dev group adds: hypothesis>=6.155 (over template defaults)
# requires-python = ">=3.14"   # raised from >=3.11 per CONTEXT decision #2
uv sync
```

**Version verification note:** PyPI re-verification was **blocked this session** (sandbox proxy denies `pypi.org`; `pip index versions` timed out). The version pins above are `[CITED]` from CLAUDE.md's prior in-session verification record (dated 2026-06). The planner should add a `checkpoint:human-verify` or a network-enabled `npm/pip`-equivalent check before *pinning* in `pyproject.toml`. `ladybug` 0.17.1 and the absence of `ladybugdb` were verified in the CLAUDE.md research session, not re-verified here.

## Package Legitimacy Audit

> This phase **declares** runtime deps in scaffold metadata but **installs/exercises nothing** beyond the dev toolchain (PKG-01 scaffold). The two runtime deps are pre-decided project constraints, not freshly-discovered packages. Registry re-verification was blocked by the sandbox proxy this session.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `pydantic` | PyPI | mature (10k+ stars, years) | very high | github.com/pydantic/pydantic | OK | Approved (project constraint) |
| `ladybug` | PyPI | LadybugDB fork of Kùzu, v0.17.1 (2026-06-02) | n/a (niche) | github.com/LadybugDB/ladybug (MIT) | OK | Approved (project constraint) — **import `ladybug`, NOT `ladybugdb`** |
| `ladybugdb` | PyPI | — | — | — | SLOP | **REMOVED — does not exist on PyPI (404).** Brand name, not the installable. The single most likely scaffolding bug. |
| `hypothesis` | PyPI | mature | very high | github.com/HypothesisWorks/hypothesis | OK | Approved (dev group) |
| `basedpyright`, `ruff`, `pytest`, `uv` | PyPI | mature | high | known orgs | OK | Approved (template defaults) |

**Packages removed due to [SLOP] verdict:** `ladybugdb` (the package/import name) — does not exist on PyPI. Dependency string and ALL imports must be `ladybug`. Flag loudly in the scaffold: `import ladybug as lb`, `dependencies = ["ladybug>=0.17,<0.18", ...]`.

**Packages flagged as suspicious [SUS]:** none.

**Planner note:** because PyPI re-verification was proxy-blocked this session, treat the version *pins* as `[CITED]` (CLAUDE.md record) rather than freshly `[VERIFIED]`. A network-enabled verification of `ladybug` and `ladybugdb`-absence should precede committing pins to `pyproject.toml`.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────────┐
   NVM / any        │   public seam (NVM↔core, UNCHANGED)          │
   consumer  ──────▶│   BeliefStore (typing.Protocol)             │  protocol.py
                    │   pydantic/typing ONLY — zero ladybug        │  (DATA-01)
                    └───────────────────┬─────────────────────────┘
                                        │ implemented by
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │   MemoryCore  (belief-revision discipline)   │  core logic
                    │   composes port primitives; NO Cypher here   │  (Phases 3–6;
                    │   mints state_id via uuid.uuid7()            │   seam fixed now)
                    └───────────────────┬─────────────────────────┘
                                        │ writes against (internal seam)
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │   Backend Port (Protocol) — LPG-primitive    │  the BACK-01
                    │   upsert_node · add_edge · match_nodes ·     │  decision
                    │   traverse(start,edge_types,max_depth)→      │  (BACK-04 spec
                    │     (reached, frontier) · unit_of_work() tx  │   drafted here)
                    └──────────┬───────────────────────┬──────────┘
                               │ implemented by         │ implemented by
                               ▼                        ▼
                    ┌──────────────────┐    ┌──────────────────────┐
                    │ in-memory backend│    │ ladybug backend      │   adapters
                    │ (BFS, zero Cypher│    │ (Cypher + params)    │   (PHASE 2 —
                    │  — Phase 2)      │    │  — Phase 2)          │    not now)
                    └──────────────────┘    └──────────────────────┘

  Data flow (e.g. get_impact): consumer → BeliefStore.get_impact(state_id, depth)
    → MemoryCore composes backend.traverse(start, {DEPENDS_ON,DERIVED_FROM,...}, max_depth)
    → port returns (reached set, frontier set) → MemoryCore wraps as ImpactResult.
  Phase 1 fixes EVERY box's TYPE; only the two top boxes get authored code this phase.
```

The file-to-module mapping lives in Recommended Project Structure below; the diagram shows the seam topology the phase must make real in types.

### Recommended Project Structure
```
src/doxastica/
├── __init__.py          # public re-exports (BeliefStore, models, EdgeType, errors)
├── protocol.py          # BeliefStore Protocol — pydantic/typing ONLY, zero ladybug (DATA-01)
├── models.py            # frozen pydantic v2: Scope, Belief, BeliefState, BeliefFilter,
│                        #   ImpactResult; Status + EdgeType enums (DATA-02,04,06)
├── ports.py             # internal backend port Protocol — LPG primitives (BACK-01)
│                        #   (name TBD: ports.py / backend.py — planner's call)
├── errors.py            # WorldScopeContractionError etc. (typed exception surface)
└── py.typed             # ship type marker (strict-typing consumers)
docs/
└── backend-contract.md  # the drafted port-contract spec (BACK-04; published Phase 8)
tests/
├── test_import_purity.py   # asserts protocol.py imports no ladybug (DATA-01 guard)
└── test_models_frozen.py   # asserts models are frozen / reject mutation
```
*(The `MemoryCore` implementation module(s) are introduced in Phase 3; Phase 1 may stub an empty `core.py` or defer it. The in-memory/ladybug adapter modules are Phase 2.)*

### Pattern 1: Public Protocol seam, import-pure
**What:** `BeliefStore` is a `typing.Protocol`. It defines the contract; implementations are structural (no inheritance required).
**When to use:** the NVM↔core boundary — consumers type-annotate against `BeliefStore`, never a concrete class.
**Example:** see Code Examples below.
**Enforce import purity as a test** (`05 §1`/`21 §5` rule 5 made executable): a test that imports `doxastica.protocol` and asserts `ladybug` is not in `sys.modules` after import, or uses AST/`importlib` to scan the module's imports. This turns the "no leak" rule into a build-time check.

### Pattern 2: LPG-primitive backend port (the internal seam)
**What:** a second `Protocol` exposing **graph primitives**: `upsert_node`, `add_edge`, `match_nodes`, a single generic `traverse(start, edge_types, max_depth) → (reached, frontier)`, and a `unit_of_work()` transaction context manager.
**When to use:** `MemoryCore` composes these; never writes Cypher. The in-memory backend implements `traverse` as one visited-set BFS; the ladybug backend translates to Cypher.
**Key:** `traverse` is the *single* traversal primitive — `get_impact` and `get_scope_at` both reduce to it (+ `match_nodes`). Keeps the port small and genuinely backend-portable.
**Round-trip tension (Phase 2 spike):** composing higher-level ops from primitives may cost more round-trips than one hand-written Cypher query. Write the port as decided; do not pre-optimize; the spike confirms or adjusts.

### Pattern 3: Closed typed filter compiled to a query (no Python post-filter)
**What:** `BeliefFilter` is a frozen pydantic model of core-owned fields, AND-combined, that the backend *compiles to a query* — never a free `str`, never Python-side filtering after fetch.
**Why:** prevents triple-structure leak and Cypher injection; keeps the core subgraph closed; declines the Repository/generic-GraphStore anti-pattern (`21 §2`).

### Pattern 4: Never-silently-under-report return shapes
**What:** any bounded operation returns a structured result carrying the boundary signal. `ImpactResult` carries `frontier` + `truncated`; when unbounded, `truncated=False` and `frontier` empty.
**Why:** a depth-bounded cascade that returns a bare `list` cannot tell the consumer it stopped early — the exact failure DATA-04 exists to prevent.

### Anti-Patterns to Avoid
- **Cypher in `MemoryCore`:** any backend dialect in the core-logic layer voids BACK-01. (Phase 1 has no core logic yet, but the *port shape* must make this impossible — primitives only, no `run(cypher)` method.)
- **`ladybug` import in `protocol.py`:** voids DATA-01. Guard with a test.
- **Free-`str` / arbitrary-property `query_scope`:** the original `query_scope(query: str)` is the #1 rewrite risk — replaced by `BeliefFilter`.
- **`source_event_id` as PRIMARY KEY:** breaks under multi-scope. Use synthesized `state_id`.
- **`status` beyond `active|retracted`:** `invalidated`/`under_revision` are NVM extensions, not core (DATA-06).
- **Deductive closure / inference in models:** beliefs are finite explicit bases (DATA-05).
- **Mutable models:** all pydantic models must be `frozen=True` (immutable `BeliefState`).
- **A generic `GraphStore`/Repository over the DB:** declined (`21 §2`); the LPG-primitive port is *not* a thin Cypher wrapper — it is a small fixed primitive set with `traverse` as the only graph-walk.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Monotonic UUID7 minting | A custom timestamp+random UUID generator | stdlib `uuid.uuid7()` (3.14+) | RFC 9562 §5.7 compliant, write-monotonic, zero deps. Hand-rolled UUID7 risks non-monotonic intra-ms ordering — the exact property the `state_id` tiebreak relies on. |
| Frozen/validated value models | Hand-written `__init__`/`__eq__`/`__hash__`/immutability | `pydantic` v2 `frozen=True` models | Validation at the seam + immutability + hashability for `frozenset[UUID]` members, for free. |
| Closed enum membership | String constants / `Literal` unions scattered across files | `enum.Enum` (`EdgeType`, `Status`) | Single source of truth; serializes cleanly; basedpyright-exhaustive. |
| Structural interface | ABC + inheritance the consumer must subclass | `typing.Protocol` | Structural typing — NVM's adapter need not import a doxastica base class; the seam stays a pure contract. |
| Import-purity enforcement | Manual code review | A pytest test scanning `protocol.py` imports | Makes "no `ladybug` leak" a build error, not a review note (`21 §1` rule 5 made executable). |

**Key insight:** this phase's "don't hand-roll" is mostly about **not inventing identity/immutability machinery** — the stdlib and pydantic already give exactly the opaque-handle + frozen-model + closed-enum surface the design needs. The temptation to hand-roll appears most at UUID7 (avoided by the 3.14 floor) and at "a little query helper" (avoided by `BeliefFilter` compiling to a backend query).

## Runtime State Inventory

> **Greenfield phase — not a rename/refactor/migration.** No stored data, live services, OS-registered state, secrets, or build artifacts exist yet (repo holds only `.planning/`, `CLAUDE.md`, `LICENSE`, `README.md`). One forward-looking note: the CONTEXT decision to raise `requires-python` 3.11→3.14 means CLAUDE.md/PROJECT.md text ("Floor: 3.11", the "UUID7 decision" section, the `uuid-utils` dev shim) is now **stale documentation** the planner should annotate or update — but that is doc drift, not runtime state. **Nothing found in any runtime-state category — verified: no `src/`, no DB files, no installed package, no CI registered.**

## Common Pitfalls

### Pitfall 1: The `ladybugdb` package/import name
**What goes wrong:** scaffold declares `dependencies = ["ladybugdb"]` or code does `import ladybugdb` — fails (404 on PyPI / ImportError).
**Why it happens:** "LadybugDB" is the *brand/project* name; the *installable* is `ladybug` (a Kùzu fork). PROJECT.md historically wrote "ladybugdb".
**How to avoid:** dependency string `ladybug>=0.17,<0.18`; import `ladybug as lb`. (Phase 1 only *declares* it; no import in `protocol.py` regardless.)
**Warning signs:** any `ladybugdb` token anywhere in `pyproject.toml` or source.

### Pitfall 2: Letting `get_impact` default to a silently-bounded traversal
**What goes wrong:** the `depth=None` "full closure" default is implemented later as a Cypher variable-length query — which **requires an upper bound and defaults to 30 if omitted** in LadybugDB/Kùzu. The "unbounded" default then silently caps at 30 hops without setting `truncated=True`.
**Why it happens:** Cypher variable-length syntax (`-[:REL*1..max]-`) mandates a max; omitting it does not mean "unbounded" — it means "30". `[CITED: docs.ladybugdb.com — "Max number of hop will be set to 30 if omitted"]`
**How to avoid:** **Phase 1's job is only to fix the contract** (`depth:int|None=None`, `truncated`/`frontier` in the return shape) so the *interface* can never silently under-report. The actual unbounded-cycle-safe implementation is the **Phase 2 spike** — confirm whether ladybug can express it (recursive-join / `ACYCLIC` reachable-set) in one query, or whether the in-memory backend's visited-set BFS is the canonical reference and ladybug needs a loop. The port/default **adjusts in Phase 2 if the spike demands it** (CONTEXT decision #5). Do NOT resolve this in Phase 1.
**Warning signs:** any Phase-1 text that *commits* to a single-Cypher-query implementation of unbounded closure, or that drops the `truncated` field as "always False".

### Pitfall 3: Conflating "no storage abstraction" with "no backend port"
**What goes wrong:** a planner reads CLAUDE.md's "no storage abstraction over the DB" / `05 §0` "storage abstraction is a non-goal" and concludes the BACK-01 port violates project constraints — or, inversely, builds a thick generic `GraphStore`.
**Why it happens:** the NVM design doc (`21 §7`) *declines* a storage abstraction **for NVM's embedded core context**; doxastica's PROJECT.md/REQUIREMENTS.md **deliberately reverse this for the standalone-library context** (BACK-01..05). The two are consistent: the port sits *below* the unchanged NVM↔core `BeliefStore` seam, and "no storage abstraction" specifically forbade the *Repository/generic-GraphStore/ORM* pattern, not a thin LPG-primitive port.
**How to avoid:** the LPG-primitive port is **not** a generic query engine — it is a small fixed primitive set (`upsert_node`/`add_edge`/`match_nodes`/`traverse`/`unit_of_work`). It is allowed precisely because doxastica is a publishable standalone library where backend pluggability is a real product goal (PROJECT.md Key Decisions). The line: **primitives that any LPG can implement = OK; a Cypher-passthrough or arbitrary-query-builder = the declined anti-pattern.**
**Warning signs:** a port method named `run`/`query`/`execute` taking a query string; a port method that takes arbitrary property predicates.

### Pitfall 4: Treating the NVM-sketch BeliefState fields as core
**What goes wrong:** modelling `provenance`, `valid_from_turn`/`valid_to_turn`, `status: invalidated`, or epistemic edge labels (`WITNESSED_BY`/`TOLD_BY`/`INFERRED_FROM`) on the core models.
**Why it happens:** `17 §3`'s Cypher sketch shows all of these — but `17` "mixes paper-core with NVM specifics" (CONTEXT caveat); `05 §4` assigns them to the NVM layer.
**How to avoid:** core models carry ONLY the closed taxonomy (decision #3). `status` is `active|retracted`. Everything else lives in the opaque `value` or on downstream labels.
**Warning signs:** any narrative/temporal/epistemic word appearing in `models.py`.

### Pitfall 5: basedpyright strict on a partially-typed `ladybug`
**What goes wrong:** strict mode flags `reportUnknownMemberType`/`reportUnknownVariableType` on `lb.Connection`/`conn.execute(...)` returns (the docs don't confirm `py.typed`).
**Why it happens:** `ladybug` typing completeness is unverified `[CITED: docs.ladybugdb.com — typing status not documented]`.
**How to avoid (Phase 1 is safe; note for Phase 2):** Phase 1 imports no `ladybug`, so strict passes cleanly. In Phase 2, confine `ladybug` behind the typed backend-adapter boundary; if needed, a narrowly-scoped `[[tool.basedpyright.executionEnvironments]]` or single `# pyright: ignore[...]` at the adapter — never scattered. Keep models/Protocol fully typed.
**Warning signs:** `Any` leaking out of the adapter into `MemoryCore` or the Protocol.

## Code Examples

### The recovered `BeliefStore` Protocol — with Phase-1 refinements applied
```python
# Source: 05-nvm-memory-core.md §3 / 21-nvm-component-architecture.md §4 (verbatim),
#         refined per CONTEXT.md decisions #4 (BeliefFilter), #5 (ImpactResult/depth).
# protocol.py — imports pydantic/typing ONLY; NO ladybug (DATA-01).
from typing import Any, Protocol
from uuid import UUID
from doxastica.models import (
    Scope, BeliefState, EdgeType, BeliefFilter, ImpactResult,
)

class BeliefStore(Protocol):
    # Scope management
    def get_or_create_scope(self, scope_id: str) -> Scope: ...

    # Core belief operations
    def revise(self, scope_id: str, belief_id: str,
               value: Any, source_event_id: UUID) -> BeliefState: ...
    def expand(self, scope_id: str, belief_id: str,
               value: Any, source_event_id: UUID) -> BeliefState: ...
    def contract(self, scope_id: str, belief_id: str,
                 source_event_id: UUID) -> None: ...

    # Edge operations
    def add_edge(self, from_state_id: UUID, to_state_id: UUID,
                 edge_type: EdgeType) -> None: ...

    # Retrieval — query is now a CLOSED typed filter, not a free str (DATA-02)
    def query_scope(self, scope_id: str, filter: BeliefFilter,
                    include_deprecated: bool = False) -> list[BeliefState]: ...

    # Cascade — returns a structured result, depth optional/unbounded (DATA-04)
    def get_impact(self, belief_state_id: UUID,
                   depth: int | None = None) -> ImpactResult: ...

    # History
    def get_revision_chain(self, belief_id: str) -> list[BeliefState]: ...
    def get_scope_at(self, scope_id: str,
                     as_of_event_id: UUID) -> list[BeliefState]: ...
```

### Frozen pydantic v2 models (the closed taxonomy)
```python
# Source: CONTEXT.md decisions #2, #3, #4, #5. models.py
from enum import Enum
from typing import Any
from uuid import UUID
from pydantic import BaseModel

class Status(str, Enum):
    active = "active"
    retracted = "retracted"          # ONLY these two (DATA-06)

class EdgeType(str, Enum):
    SUPERSEDES = "SUPERSEDES"
    DEPENDS_ON = "DEPENDS_ON"
    DERIVED_FROM = "DERIVED_FROM"
    # Open Q1: whether structural HAS_REVISION / CURRENT_STATE join this enum
    # or live as separate structural constants. (planner's discretion)

class Scope(BaseModel, frozen=True):
    scope_id: str
    is_world: bool = False           # privileged world scope flag (enforcement = Phase 3)

class Belief(BaseModel, frozen=True):
    belief_id: str                   # stable logical identity, one per Belief node

class BeliefState(BaseModel, frozen=True):
    state_id: UUID                   # core-minted UUID7, PRIMARY KEY, opaque handle
    belief_id: str
    scope_id: str
    source_event_id: UUID            # caller-supplied, opaque, indexed, NON-unique
    value: Any                       # opaque, JSON-encoded; core never inspects
    status: Status

class BeliefFilter(BaseModel, frozen=True):   # DATA-02 closed filter
    belief_ids: frozenset[str] | None = None  # None = all
    status: frozenset[Status] | None = None
    event_id_min: UUID | None = None
    event_id_max: UUID | None = None

class ImpactResult(BaseModel, frozen=True):   # DATA-04 never-under-report
    reached: list[BeliefState]
    frontier: frozenset[UUID]        # boundary state_ids unexpanded; empty if unbounded
    truncated: bool                  # False when unbounded
```

### LPG-primitive backend port (the BACK-01 internal seam) — illustrative shape
```python
# Source: CONTEXT.md decision #1 (LPG-primitive). ports.py / backend.py
# Illustrative — exact node/edge value types are planner's discretion; the point
# is PRIMITIVES, not Cypher. No method takes a query string.
from contextlib import AbstractContextManager
from typing import Any, Protocol
from uuid import UUID
from doxastica.models import EdgeType

class BackendPort(Protocol):
    def upsert_node(self, label: str, node_id: UUID | str,
                    props: dict[str, Any]) -> None: ...
    def add_edge(self, edge_type: EdgeType | str,
                 from_id: UUID | str, to_id: UUID | str,
                 props: dict[str, Any] | None = None) -> None: ...
    def match_nodes(self, label: str,
                    where: dict[str, Any]) -> list[dict[str, Any]]: ...
    # THE single traversal primitive — get_impact & get_scope_at compose from this:
    def traverse(self, start: UUID | str,
                 edge_types: frozenset[EdgeType | str],
                 max_depth: int | None,
                 ) -> tuple[list[dict[str, Any]], frozenset[UUID]]:  # (reached, frontier)
        ...
    def unit_of_work(self) -> AbstractContextManager[None]: ...   # atomic tx
```

### Import-purity guard (DATA-01 made executable)
```python
# tests/test_import_purity.py
import ast, pathlib
def test_protocol_does_not_import_ladybug():
    src = pathlib.Path("src/doxastica/protocol.py").read_text()
    tree = ast.parse(src)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [n.name for n in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    assert not any(n.split(".")[0] == "ladybug" for n in names), names
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `requires-python >=3.11` + `uuid-utils` dev shim for UUID7 | `requires-python >=3.14`, stdlib `uuid.uuid7()` | CONTEXT decision #2 (2026-06-14) | Removes a dev dep + the 3.11–3.13 test matrix; CI runs 3.14 only. CLAUDE.md "UUID7 decision" section now moot. |
| `query_scope(query: str)` (recovered sketch) | `query_scope(scope_id, filter: BeliefFilter, …)` | CONTEXT decision #4 | Closes the #1 rewrite-risk soft spot (`05 §10.1`). |
| `get_impact(..., depth=5) -> list[BeliefState]` | `get_impact(..., depth: int\|None=None) -> ImpactResult` | CONTEXT decision #5 | Truncation signal + unbounded default; retires the magic `5`. |
| "Storage abstraction is a non-goal" (NVM core, `05 §0`/`21 §7`) | LPG-primitive backend port IS in scope (BACK-01..05) | PROJECT.md Key Decisions / REQUIREMENTS | Reversed *for the standalone-library context only*; port sits below the unchanged NVM↔core seam. |
| `source_event_id` as candidate PK | Synthesized core-minted `state_id` PK | CONTEXT decision #2 | Multi-scope requires it. |

**Deprecated/outdated (in project docs — planner should annotate):**
- CLAUDE.md "Python version posture: Floor 3.11" and the "UUID7 decision (the one genuine runtime gap)" section + `uuid-utils` shim — superseded by the 3.14 floor.
- PROJECT.md/REQUIREMENTS spelling "`ladybugdb`" where the *installable* is meant — use `ladybug`.
- REQUIREMENTS PKG-02 "CI matrix Python 3.11 (floor) and 3.14" — now 3.14-only per CONTEXT decision #2 (resolved in Phase 8).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | NVM (the primary consumer) targets Python 3.14, validating the raised floor | User Constraints #2 | If NVM is pinned <3.14, raising doxastica's floor to 3.14 forces a vendored/shim UUID7 after all (re-introducing the avoided third-dep tension) OR NVM cannot consume doxastica. CONTEXT explicitly flags this for confirmation (user's call, not a blocker). **Planner: surface as a checkpoint.** |
| A2 | `ladybug` 0.17.1 exists on PyPI and `ladybugdb` does not | Standard Stack / Legitimacy Audit | If pins are wrong, scaffold's declared deps fail to resolve. PyPI re-verification was proxy-blocked this session; relying on CLAUDE.md's prior in-session verification (2026-06). Low risk (recently verified) but not re-confirmed today. |
| A3 | The version pins (pydantic 2.13.4, hypothesis 6.155.2, basedpyright 1.39.7, ruff 0.15.17, pytest 9.0.3) are still current | Standard Stack | Stale pins cause lock/resolve friction, not correctness failure. `[CITED: CLAUDE.md, dated 2026-06]`, not re-verified (proxy block). |
| A4 | LadybugDB still being a Kùzu fork, Kùzu's recursive/projected-graph features (for unbounded cycle-safe reachable-set) carry over | Pitfall 2 / Open Q2 | If ladybug lacks an efficient unbounded reachable-set, the `get_impact(depth=None)` default needs a multi-query loop in the ladybug adapter. **Already the Phase 2 spike's job** — not a Phase 1 risk. |

**This table is non-empty:** A1 (NVM 3.14) is the one assumption with real downstream cost and is explicitly carried into planning for user confirmation.

## Open Questions

1. **EdgeType enum membership: do structural `HAS_REVISION`/`CURRENT_STATE` belong in `EdgeType`?**
   - What we know: generic `SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM` are definitely in scope; `HAS_REVISION`/`CURRENT_STATE` are *structural* (the revision-chain plumbing), not consumer-facing edge types passed to `add_edge`.
   - What's unclear: whether they share one enum (simpler, one vocabulary) or live as separate structural constants (cleaner — `add_edge`'s `edge_type` param then can't accept a structural edge).
   - Recommendation: **separate** — `add_edge` should only accept the three generic types; structural edges are written by `MemoryCore` internals, never by a consumer. Planner decides; flagged as discretion in CONTEXT.

2. **Can ladybug express an unbounded cycle-safe reachable-set in one query? (Phase 2 spike — NOT Phase 1)**
   - What we know: LadybugDB/Kùzu variable-length `-[:REL*min..max]-` **requires an upper bound (defaults to 30)** and offers `WALK`/`TRAIL`/`ACYCLIC` semantics + shortest-path variants, all max-bounded `[CITED: docs.ladybugdb.com]`.
   - What's unclear: whether a recursive-join / projected-graph construct gives a genuinely unbounded, cycle-safe *reachable-node-set* (not path-enumeration) efficiently.
   - Recommendation: **do not resolve in Phase 1.** Write `get_impact(depth=None)` + `ImpactResult` as the contract; the in-memory backend's visited-set BFS is the trivial reference; Phase 2 SC4 confirms the ladybug expression or the port/default adjusts. This is already a locked carry-forward.

3. **BACK-04 port-contract spec format.**
   - What we know: it must enumerate the constraints a third-party LPG backend must meet (see Backend Port Contract below); authored as a doc this phase, published Phase 8 (PKG-04).
   - What's unclear: Markdown prose vs. a `Protocol` docstring vs. a conformance-checklist format.
   - Recommendation: a `docs/backend-contract.md` prose spec keyed to the port Protocol's methods + the invariants list below; the Phase 7 conformance suite (BACK-05) becomes its executable form.

## Backend Port Contract (BACK-04 — constraints draft for the planner)

The written spec a third-party LPG backend must satisfy. The planner turns this into `docs/backend-contract.md`. Constraints:

1. **Data model:** a labelled property graph — nodes with a label + property map keyed by an id; typed directed edges with optional property maps. No relational/document semantics required beyond emulating this.
2. **Primitive operations** (must implement, with these semantics):
   - `upsert_node` — idempotent on node id; never duplicates.
   - `add_edge` — append-only in practice (the core never asks to delete edges).
   - `match_nodes` — exact-match on the provided property predicate (AND-combined); no query language exposed.
   - `traverse(start, edge_types, max_depth)` — returns the **set** of reachable nodes (de-duplicated, visited-set / cycle-safe) following only `edge_types`, plus the `frontier` (nodes left unexpanded when `max_depth` is reached). `max_depth=None` ⇒ full transitive closure, empty frontier. **Must terminate on cyclic graphs.**
   - `unit_of_work()` — a context manager providing an **atomic** (all-or-nothing) write transaction; the core groups a multi-write `revise` (append state + re-point `CURRENT_STATE`) inside one.
3. **Uniqueness:** enforced by the backend on node primary id (the core relies on `state_id` uniqueness; LadybugDB does this via PRIMARY KEY — no UNIQUE constraint needed/available).
4. **Append-only safety:** the core never deletes nodes/edges; contraction *marks* (`status='retracted'`). A backend may assume no deletions.
5. **Ordering:** `match_nodes`/traverse results the core orders itself by `(source_event_id byte-order, state_id tiebreak)` — the backend need not order, but must return all matches.
6. **Opacity:** node `value` properties are opaque blobs (JSON-encoded by the core); the backend stores/returns them verbatim and never interprets them.
7. **Conformance:** the backend passes the parameterised AGM/Hansson + structural-invariant suite (BACK-05, Phase 7) — the executable form of this contract.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | UUID7 native, the raised floor, the whole phase | ✓ | 3.14.2 (`uuid.uuid7()` confirmed) | none needed |
| uv | scaffold (PKG-01), env/lock | ✓ | 0.9.18 | none needed |
| cookiecutter-python-uv-library template | PKG-01 scaffold | ? (not probed — external template) | — | manual scaffold from CLAUDE.md tool pins |
| PyPI access (`pip`/`uv` resolve) | declaring/pinning deps | ✗ (sandbox proxy blocks pypi.org) | — | use CLAUDE.md verified pins; re-verify on a network-enabled run before committing pins |
| ladybug / pydantic *installed* | NOT needed Phase 1 (no import in protocol.py; no storage code) | n/a | — | — |

**Missing dependencies with no fallback:** none blocking — Phase 1 writes typed stubs + docs + scaffold; it does not import `ladybug` or run storage code.
**Missing dependencies with fallback:** PyPI re-verification (use CLAUDE.md pins; gate pin-commit behind a network-enabled check or human checkpoint). The cookiecutter template availability was not probed this session — planner should confirm it resolves, else scaffold manually per CLAUDE.md's recorded tool pins.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest `>=8` (resolves 9.x) + basedpyright strict (type-level) + ruff (lint) |
| Config file | none yet — created by the cookiecutter scaffold (PKG-01), Wave 0 |
| Quick run command | `uv run pytest -q` (after scaffold) |
| Full suite command | `uv run pytest && uv run basedpyright && uv run ruff check .` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | `protocol.py` imports no `ladybug`; Protocol type-checks | unit + type | `uv run pytest tests/test_import_purity.py -x` ; `uv run basedpyright` | ❌ Wave 0 |
| DATA-02 | `query_scope` accepts `BeliefFilter`, rejects a free `str` (type error) | type (basedpyright) + unit | `uv run basedpyright` ; construct a `BeliefFilter` in a test | ❌ Wave 0 |
| DATA-03 | UUID7 ordering contract documented + `state_id`/`source_event_id` typed `UUID` | type + doc-assert | `uv run basedpyright` ; assert docstring/contract present | ❌ Wave 0 |
| DATA-04 | `get_impact` returns `ImpactResult` (has `frontier`+`truncated`); `depth:int\|None` | type + unit | `uv run basedpyright` ; instantiate `ImpactResult` | ❌ Wave 0 |
| DATA-05 | models carry no closure/inference fields (negative) | review + unit | assert `BeliefState.model_fields` == the closed set | ❌ Wave 0 |
| DATA-06 | models are `frozen=True`; `Status` is exactly `{active,retracted}`; `EdgeType` membership | unit | `uv run pytest tests/test_models_frozen.py -x` | ❌ Wave 0 |
| PKG-01 | package builds + type-checks + ruff clean from scaffold under `doxastica` | build + type + lint | `uv build` ; `uv run basedpyright` ; `uv run ruff check .` | ❌ Wave 0 |
| BACK-01 | backend port Protocol exists, distinct from `BeliefStore`, primitives-only (no query-string method) | type + review | `uv run basedpyright` ; assert no `run`/`query`/`execute(str)` method | ❌ Wave 0 |
| BACK-04 | `docs/backend-contract.md` exists and enumerates the 7 constraints | doc-exists | `test -f docs/backend-contract.md` (+ section assertions) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest -q && uv run ruff check .`
- **Per wave merge:** `uv run pytest && uv run basedpyright && uv run ruff check .`
- **Phase gate:** full suite green (incl. basedpyright strict) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] Framework install + config: the `cookiecutter-python-uv-library` scaffold itself (PKG-01) — produces `pyproject.toml`, pytest/ruff/basedpyright config, `src/doxastica/`, `tests/`. **This is the first Wave-0 task; everything else depends on it.**
- [ ] `tests/test_import_purity.py` — covers DATA-01 (AST scan for `ladybug` import)
- [ ] `tests/test_models_frozen.py` — covers DATA-06 (frozen-ness + enum membership + closed field set for DATA-05)
- [ ] `tests/conftest.py` — minimal; no DB fixtures this phase (no storage code)
- [ ] Add `hypothesis>=6.155` to the dev group (declared now, exercised Phase 7)
- [ ] Set `requires-python = ">=3.14"` in the scaffolded `pyproject.toml` (decision #2)

*(Most "tests" here are type-level — basedpyright strict passing IS the primary verification for a decision-grade phase that ships typed stubs. Runtime tests are thin: import-purity, frozen-ness, enum membership, doc existence.)*

## Security Domain

> `security_enforcement` not explicitly `false` in config → included. This is a zero-network, zero-auth, embedded-library, decision-grade phase. Most ASVS categories do not apply; one input-validation principle is load-bearing.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | no auth surface (embedded library) |
| V3 Session Management | no | no sessions |
| V4 Access Control | no | in-process library; tenancy (R19) is a discipline, not an auth boundary |
| V5 Input Validation | **yes** | `pydantic` v2 frozen models validate at the seam; `BeliefFilter` is a **closed typed filter** — no free string compiled into a query (the injection-prevention design, DATA-02) |
| V6 Cryptography | no | `state_id` UUID7 is an identifier, not a secret; not security-bearing |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher/query injection via `query_scope(query: str)` | Tampering / Info disclosure | **Designed out by `BeliefFilter`** — closed typed filter compiled to a parameterised backend query; nothing interpolated into Cypher (DATA-02). Phase 1's typed surface IS the mitigation; Phase 2's adapter must use `parameters={...}` binds (CLAUDE.md: string interpolation "strongly discouraged"). |
| Opaque-value blob carrying executable/injection payload | Tampering | Core treats `value: Any` as an opaque JSON-encoded blob it never interprets/executes — no eval, no query-construction from value content. The opacity boundary is itself the control. |
| Slopsquat dependency (`ladybugdb` vs `ladybug`) | Spoofing (supply chain) | Pin/import the verified `ladybug`; `ladybugdb` does not exist on PyPI (SLOP). See Legitimacy Audit. |

## Sources

### Primary (HIGH confidence)
- `/Users/paul/Documents/Dev/Personal/doxastica/.planning/phases/01-protocol-backend-port-data-model-decisions/01-CONTEXT.md` — every locked decision (the authoritative input for this phase).
- `../narrative-vm/_design/v2/05-nvm-memory-core.md` — §3 recovered Protocol surface, §2 core vocabulary, §4 NVM-layer responsibilities (what is NOT core), §6 world scope, §9a R19 tenancy, §10 soft spots.
- `../narrative-vm/_design/v2/21-nvm-component-architecture.md` — §4 M0 library boundary + Protocol verbatim, §6 seam catalog (`BeliefStore` vs `KnowledgeQueries`), §7/§7a persistence-portability + enumerable query surface (the query_scope resolution).
- `../narrative-vm/_design/v2/17-kumiho-nvm-recommendations.md` — §3 Belief/BeliefState split + one-belief-per-node, §4 UUID7 lineage keys (read with the CONTEXT caveat that it mixes NVM specifics).
- Local interpreter — `python3.14 -c "import uuid; uuid.uuid7()"` → works, monotonic. `[VERIFIED: Python 3.14.2]`
- Local — `uv 0.9.18` present. `[VERIFIED]`
- `./CLAUDE.md` — recorded tech-stack verification (PyPI pins dated 2026-06), Ladybug API notes, constraints.

### Secondary (MEDIUM confidence — official vendor docs, this session)
- docs.ladybugdb.com/cypher/query-clauses/match — variable-length traversal **requires upper bound (defaults to 30)**, `WALK`/`TRAIL`/`ACYCLIC`, shortest-path variants all max-bounded. `[CITED]`
- docs.ladybugdb.com/cypher/transaction — single-writer/multi-reader, serializable, manual `BEGIN TRANSACTION [READ ONLY]`/`COMMIT`/`ROLLBACK`, auto-commit. `[CITED]`
- docs.ladybugdb.com/client-apis/python — `Database`/`Connection`/`AsyncConnection`, `execute`, `get_all`/`has_next`/`get_next`/`get_as_df`; `py.typed` status **not documented**. `[CITED]`

### Tertiary (LOW confidence — could not verify this session)
- PyPI version currency (pydantic/ladybug/hypothesis/etc.) — proxy-blocked; relying on CLAUDE.md's prior in-session verification. Re-verify before committing pins.
- cookiecutter-python-uv-library template availability — not probed.

## Metadata

**Confidence breakdown:**
- User constraints / decisions: HIGH — fully specified in CONTEXT.md, each grounded in a cited design doc.
- Standard stack (versions): MEDIUM — pins are CITED from CLAUDE.md (dated 2026-06) but PyPI re-verification was proxy-blocked this session.
- Architecture / seams: HIGH — the three-way cut (Protocol / core / LPG-primitive port) is directly grounded in `21 §4/§6/§7` and locked in CONTEXT.
- Pitfalls: HIGH — Pitfall 2 (traversal bound) and Pitfall 3 (no-storage-abstraction reconciliation) are the two load-bearing ones, both verified against official docs / the design corpus.
- Python 3.14 / UUID7: HIGH — verified on the local 3.14.2 interpreter.

**Research date:** 2026-06-14
**Valid until:** ~2026-07-14 (30 days — stable design; the only volatile items are PyPI pins, re-verify before committing `pyproject.toml`). The `get_impact`/`traverse` ladybug-expression question is intentionally deferred to the Phase 2 spike and does not affect Phase 1 validity.
