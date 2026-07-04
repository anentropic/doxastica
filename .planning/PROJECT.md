# doxastica

## What This Is

doxastica is a standalone Python library implementing the **memory core** of the
narrative-vm (NVM) project — a general-purpose **AGM belief-revision engine** with no
game, narrative, or LLM concepts inside it. It is a faithful, independently buildable
implementation of the **Kumiho** architecture (arXiv 2603.17244) plus one deliberate
extension (multi-scope; Kumiho is single-agent) and one deliberate exclusion (AGM
*recovery*, replaced by superseded-chain semantics). It is NVM's **M0 milestone**: the
rare zero-LLM, shippable, de-risking infrastructure the whole epistemic layer stands on.

Built for: NVM itself (its first and primary consumer), and — as a welcome byproduct —
anyone who wants a clean, formally-tested reference implementation of graph-native
belief revision they can cite or reuse.

## Core Value

A correct, append-only belief-revision core behind a clean `BeliefStore` Protocol whose
correctness is *provable* — AGM postulate compliance and structural invariants verified
mechanically, with zero narrative semantics leaking into it. If everything else is
deferred, the formal core and its property-test suite must be right.

## Current Milestone: v0.2.0 Stance

**Goal:** Add `stance` — a comparison-only ordinal epistemic enum — as a first-class field
on `BeliefState`, closing the ratified NVM **R21** gap, with the canonical ordering owned by
the core, all stance *policy* left to NVM, and the docs updated to showcase it.

**Target features:**
- A canonical `Stance` `IntEnum` with a property-tested total order:
  `doubted < suspected < believed < certain`.
- `stance` on the frozen `BeliefState` (six fields → seven) — a decision-grade taxonomy edit.
- `stance` accepted on the write surface (`revise`/`expand`, optional, defaulting to
  `certain`); `contract` preserves the prior stance verbatim on its retracted tail; the value
  round-trips byte-stable on **both** backends.
- Ordinal **comparison** exposed as the only core operation over stance — no arithmetic path
  reachable (asserted negatively).
- STANCE-05 Hypothesis property suite (dual-backend, oracle-independent, `test_invariants.py`
  style).
- Docs: update the Cluedo detective tutorial to demonstrate stance (a within-scope epistemic
  gradient + reader-side ordinal comparison) and refresh `revise`/`expand` signature references
  across the docs site.

**Boundaries:** `IntEnum` (native total order, no rank map); **edge stance out of scope**
(core edges stay generic; R21's "edges carry stance" reconciled as NVM metadata, not silently
dropped); **no policy in core** (no assignment/propagation/contradiction/torn-mind logic;
`test_import_purity`-style boundary intact); **no numeric `confidence` field, ever**; the
closed `BeliefFilter` stays closed (no stance predicate).

## Requirements

### Validated

- **`BeliefStore` Protocol + `BackendPort` seam, frozen taxonomy, UUID7 ordering contract** — landed and import-purity-guarded (Phase 1).
- **Ports & adapters / dual backends** — in-memory + ladybug reference backend run the same parity suite behind `BackendPort` (Phases 1–2).
- **Flexible connection (ladybug)** — injected-connection + namespace tenancy and self-managed modes, throwaway test DBs (Phase 2).
- **Scopes + privileged world scope** where `contract()` raises `WorldScopeContractionError` before any write (Phase 3, SCOPE-01/02/03).
- **`Belief`/`BeliefState` split + immutable append-only `HAS_REVISION` chain**, with the *current* per belief-in-scope **derived** (D-01: no stored `CURRENT_STATE` pointer) (Phase 3, CHAIN-01/02/03).
- **Core operations `revise`/`expand`/`contract`/`get_or_create_scope` + `get_revision_chain`** on both backends, each write atomic in one `unit_of_work` (Phase 3, OPS-01/02/03, HIST-02).
- **Structural-invariant test** reframed as a Hypothesis consistency check (derived-current total + single-valued ≡ chain tail) on both backends (Phase 3, SC3).
- **`query_scope` observation surface** — the read every postulate test sees the belief base through: closed typed `BeliefFilter`, one derived-current tail per `(scope, belief)`, `include_retracted` flag, deterministic `_order_key` order, empty-scope `[]`; plus the four-cell **retracted vs superseded** matrix (observed via `get_revision_chain` + `SUPERSEDES`, never `query_scope`) on both backends (Phase 4, CHAIN-04/HIST-01). D-03 reversal: public flag `include_deprecated` → `include_retracted`.
- **Generic typed edges + bounded contraction cascade** — `add_edge` lays closed-`EdgeType` (`SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM`) edges with no epistemic semantics; `get_impact` is the cycle-safe, depth-bounded cascade returning `ImpactResult(reached, frontier, truncated)` over `{DEPENDS_ON, DERIVED_FROM}` in the **dependent→source (`direction="in"`)** sense, the start excluded, hydration-gap closed via `match_nodes` re-fetch. Enabled by a new keyword-only `direction` parameter on the `BackendPort.traverse` primitive (default `"out"`, a cross-phase contract for Phase 6) — reverse-adjacency in-memory, 3-site arrow-flip in ladybug. Mechanism only; AGM Relevance/Core-Retainment postulate tests deferred to Phase 7 (Phase 5, EDGE-01/EDGE-02).
- **`get_scope_at` structural time-travel** — reconstructs a scope's active base *as of* an event purely structurally from immutable `source_event_id`-ordered states, composing only `match_nodes` (no `traverse`, core stays driver-blind). A temporal variant of `query_scope`: the one structural change is an inclusive `source_event_id <= as_of` **cut applied before** the per-belief ordering-max (cut-then-max = REWIND, not `event_id_max`'s max-then-filter DROP), with a cut-window retracted collapse. The "most complex query" weight is cashed in the proof: a pure-Python operational-fold oracle asserts `get_scope_at(scope, cut) == fold(ops, cut)` under Hypothesis on both backends, with intra-ms-colliding/out-of-order UUID7 ids (SC3) and `as_of` stepped across event ids (SC2). The last `BeliefStore` method to land (Phase 6, HIST-03).
- **M0 exit-gate conformance suite** — the mechanically-verified proof, parameterised over every registered backend (in-memory oracle + ladybug conforming identically, BACK-05). AGM revision postulates (Success K*2, Inclusion K*3, Vacuity K*4, Consistency K*5, Extensionality K*6; Closure K*1 dropped by construction) and the Hansson base-contraction postulates (Success, Inclusion, Relevance, Core-Retainment, Uniformity, phrased against append-only superseded-chain semantics, not classical partial-meet) assert against an **independent** shadow oracle that never calls the system-under-test. The named structural-invariant set (derived-current uniqueness, chain immutability, `get_scope_at ≡ replay`, world-scope no-contraction) is registered as a conformance set. AGM **Recovery** appears only as a loud `@pytest.mark.xfail(strict=True)` counterexample (the single deliberate exclusion — a strict-xfail drift guard, never asserted true), with positive superseded-chain replacement tests in its place. The irony/divergence join is demonstrated on synthetic data: two scopes diverging on `belief_id` in **one `match_nodes` round-trip** over the generic port, validated against a plain-Python oracle, no narrative naming in core. Suite green (194 passed, 1 xfailed) on both backends (Phase 7, FORMAL-01..05/BACK-05).
- **Publishable polish** — shipped as an OSS reference implementation: `pydantic`-only base install with `ladybug` demoted to the `doxastica[ladybug]` extra, split isolation/full CI, PEP 639 PyPI-ready `pyproject.toml` metadata, a `mkdocs-material` docs site (Diataxis) including the published backend-port contract, a tag-triggered PyPI `release.yml` pipeline, `py.typed`, and an MIT license (Phase 8, PKG-01..04).

### Active

<!-- Current scope. Building toward these. All hypotheses until shipped. -->

> **v0.2.0 — Stance (R21).** The v0.1.0 M0 core shipped (see Validated); its original scope
> hypotheses are archived in [milestones/v0.1.0-ROADMAP.md](milestones/v0.1.0-ROADMAP.md).
> Active scope below is the Stance feature only.

- [ ] **Canonical `Stance` `IntEnum`** with a property-tested **total order**
      (`doubted < suspected < believed < certain`); comparison is the only permitted operation
      (no arithmetic path reachable)
- [ ] **`stance` on `BeliefState`** — the frozen value model grows from six fields to seven; a
      decision-grade edit to the closed taxonomy
- [ ] **Write surface accepts stance** — `revise`/`expand` take an optional `stance` defaulting
      to `certain` ("core default, NVM overrides"); the value round-trips byte-stable on **both**
      backends (same encode/hydrate discipline as `value`)
- [ ] **`contract` preserves prior stance** — the retracted tail carries the prior stance
      verbatim (mirrors the existing verbatim-value copy)
- [ ] **`get_scope_at` reconstructs stance** — time-travel round-trips stance unchanged
- [ ] **STANCE-05 property suite** — dual-backend, oracle-independent (`test_invariants.py`
      style): order is total and antisymmetric; stance survives revise→query and `get_scope_at`
      round-trips; `contract` preserves it; no arithmetic operator is reachable on the type
- [ ] **Docs: Cluedo tutorial demonstrates stance** — a within-scope epistemic gradient plus
      reader-side ordinal comparison (policy stays the reader's, per R21); `revise`/`expand`
      signature references refreshed across the docs site

### Out of Scope

<!-- Explicit boundaries with reasoning, to prevent re-adding. -->

- **Any NVM / game / narrative concept** (actors, turns, scenes, plausibility, diegetic
  time, GM context assembly) — the seam exists precisely to keep these out; their meaning
  lives in the NVM interface layer above the Protocol
- **AGM recovery postulate** — incompatible with immutable versioning; superseded-chain
  semantics is the deliberate, better behaviour (per the Kumiho analysis)
- **LLM / inference of any kind** — M0 is the zero-LLM milestone; NL→triple mapping and
  entrenchment policy are NVM-layer prompt-engineering concerns
- **Non-LPG / config-style storage abstraction** — the backend port's data model is a
  labelled property graph (nodes, typed edges, properties); backends that don't model an
  LPG (relational/document stores, unless they emulate an LPG), and ORM/config-style
  indirection, stay out. *(Note: a graph **backend port** itself is now IN scope — see
  Active + Key Decisions. This reverses the earlier NVM "no storage abstraction" stance for
  the standalone-library context; the backend port sits **below** the NVM↔core seam, which
  is unchanged.)*
- **Entity nodes, topology, sheet/mechanical state, the Chronicle, prospective indexing,
  the planner cache** — all NVM-owned; the core subgraph is closed (no outbound graph refs)
- **Epistemic edge labels** (`WITNESSED_BY`, `TOLD_BY`, `INFERRED_FROM`) and **stance
  policy** — these are NVM specialisations of generic edges / NVM rules; the core only
  stores and compares
- **Owning the database** — the core is a label-family *tenant* in a shared embedded DB,
  not its owner

## Context

- **Current state (v0.1.0 shipped 2026-07-04).** All eight phases complete (26 plans);
  ~1,970 LOC `src` / ~3,800 LOC `tests`; conformance suite green on both backends
  (194 passed, 1 strict xfail). Pipeline-ready for PyPI at `0.1.0` (tag `v0.1.0` triggers
  `release.yml`); not yet published.
- **This is NVM's M0.** The library extracts the "memory core seam" designed in
  `narrative-vm/_design/v2/05-nvm-memory-core.md` and scoped as the M0 milestone in
  `15-nvm-milestones.md`. The downstream consumer (NVM's `ladybug` adapter) implements
  *against the Protocol*, never the implementation.
- **The paper is the spec.** API tie-breakers resolve against *paper fidelity + NVM's
  actual needs*, never hypothetical reuse flexibility (which is how clean libraries bloat).
- **Tenancy discipline (R19).** The core owns label families `:Scope` / `:Belief` /
  `:BeliefState` and its edge types — only the core writes them; everyone reads. Connection
  is injected; in production NVM owns the handle and leases it. Inbound edges from external
  subsystems are safe because the core is append-only (contraction marks, never deletes).
- **Formal grounding is the payoff.** The core is the one NVM component whose correctness
  is a formal question — its specification *is* the forty-year-old AGM belief-revision
  literature, tested against it mechanically (not Lean proofs over the whole engine).
- **Reference design files** (read-only inputs, in the sibling `narrative-vm` repo):
  `_design/v2/05-nvm-memory-core.md` (the Protocol + world scope + testing),
  `_design/v2/17-kumiho-nvm-recommendations.md` (paper analysis + structural patterns),
  `_design/v2/15-nvm-milestones.md` (M0 scope + exit gate),
  `_design/v2/16-nvm-decision-register.md` (R19 tenancy, R21 stance),
  `_design/v2/21-nvm-component-architecture.md` (repo boundary),
  `_design/v1/kumiho Graph-Native Cognitive Memory for AI Agents.pdf` (the paper).

## Constraints

- **Tech stack**: Python (uv) — runtime deps **`ladybug` (the LadybugDB PyPI package, a
  Kùzu fork, import `ladybug as lb`) + `pydantic` v2 only**, zero NVM imports. Why: the
  repo boundary keeps the implementation faithful to the paper's domain-agnostic model and
  LadybugDB's single-writer/multi-reader embedded model enforces write serialization for free.
- **Tooling**: `cookiecutter-python-uv-library` template — basedpyright strict typing,
  ruff lint/format, pytest + coverage, pre-commit, git-cliff changelog, GitHub Actions.
- **Storage**: behind a **backend port** (Ports & Adapters). The belief-revision discipline
  is backend-agnostic; backends implement the port for a given labelled property graph. The
  **reference backend** is LadybugDB (PyPI package **`ladybug`**, a Kùzu fork —
  https://github.com/LadybugDB/ladybug; API: `lb.Database(path | ":memory:")` →
  `lb.Connection(db)` → `conn.execute(cypher, parameters=...)`; schema-first, uniqueness
  only via PRIMARY KEY). The ladybug backend supports a **flexible connection** (injected
  `Connection` + namespace prefix, never closed by the core, for NVM's R19 tenancy / shared
  DB; *and* self-managed `:memory:`/file). A second **in-memory backend** ships to prove the
  port and serve as the test oracle. Backend port granularity (Cypher-level vs. LPG-primitive)
  is an open Phase-1 decision — see Open questions.
- **Discipline**: append-only — no operation removes or rewrites `BeliefState` nodes or
  `HAS_REVISION` edges; revision is forward-only. World-scope `contract()` is an error.
- **Boundary**: no game/narrative/LLM concepts in core code; each such appearance is the
  leak the seam exists to prevent.
- **License**: MIT (publishable as an OSS reference implementation).
- **Testing**: AGM-postulate compliance as property tests (Hypothesis), LLM-free.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Package name `doxastica` (repo + import) | "Doxastic" = relating to belief; distinct from the paper's "Kumiho" system name while README still credits it | — Pending |
| MIT license | Maximally reusable for a reference implementation others may cite | — Pending |
| Scope = M0 exit gate **+ publishable polish** | Treat as a publishable OSS reference impl from day one (docs, CI/release, PyPI), not just a green test suite | — Pending |
| Multi-scope extension to Kumiho | Kumiho is single-agent; NVM needs per-holder belief states (actor scopes + world scope) as independent peers, not views | — Pending |
| Exclude AGM recovery | Incompatible with immutable versioning; superseded chains are the better semantics | — Pending |
| Opaque `value: Any` + opaque event ids | Triple structure and provenance meaning belong to NVM; keeps the core domain-agnostic | ⚠️ Revisit — `query_scope(query: str)` semantics underspecified (soft spot §10.1) |
| Injected connection, label-family tenancy (R19) | Core is a tenant in a shared embedded DB, not its owner; DI seam is NVM↔core | — Pending |
| `get_impact` default `depth=5` | Sketch number from the recovered Protocol; truncation policy undesigned | ⚠️ Revisit (soft spot §10.3) |
| **Pluggable backends via a port (Ports & Adapters)** — reverses NVM's "no storage abstraction" stance | Justified by the new context: doxastica is a *publishable standalone* library, so backend pluggability is a real product goal, not speculative generality. The port sits **below** the unchanged NVM↔core seam, so NVM and R19 tenancy are unaffected; the property suite becomes a backend conformance suite proving every backend correct | ⚠️ Revisit — port *granularity* (Cypher-level vs. LPG-primitive) undecided (Phase 1) |
| Ship a second (in-memory) backend in M0 | Proves the port is real *and* is the shadow oracle Phase 7 needs anyway — nearly free, load-bearing, not speculative | — Pending |
| **Stance is a core `IntEnum`** (v0.2.0, R21) | The reason stance exists is its *total order*; `IntEnum` makes that native and un-fakeable (`certain > believed` is `3 > 2`) with no auxiliary rank map to drift. Cost: persists as `0..3`, less legible than the StrEnum tokens of `Status`/`EdgeType` (neither of which is ordered today) | — v0.2.0 |
| **Edge stance is out of scope** (v0.2.0) | Belief-state stance is core; core edges are generic (`SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM`) and the epistemic edges are NVM specialisations that don't exist in core. R21's "edges carry stance" reconciled as NVM edge metadata, not silently dropped; avoids adding a property payload to `add_edge` (a bigger port change) | — v0.2.0 |
| **`revise`/`expand` default `stance=certain`** (v0.2.0) | Assignment is an NVM concern, so the core needs a neutral default; `certain` matches world-scope authored-canon and observed facts (common M0 synthetic case). Optional param → existing callers/tests unchanged. Documented "core default, NVM overrides" | — v0.2.0 |

### Open questions to resolve during planning

- **`query_scope(query: str)` semantics** — what does `query` mean without leaking triple
  structure into the core? (memory-core §10.1)
- **Type-dependent entrenchment storage** — NVM policy wants edge in-degree; verify the
  Protocol surface (`get_impact`-style traversal) suffices without core changes (§10.2)
- **`get_impact` cascade truncation** — depth default and truncation-boundary behaviour
  (§10.3)
- **Seed authored invariants into the world scope at build?** — lean yes, for uniform
  querying (§6 residual / §10.4)
- **UUID7 ordering contract for `get_scope_at`** — intra-ms monotonicity is *optional* per
  RFC 9562; the core takes event ids as opaque caller inputs, so time-travel needs an
  explicit ordering contract (or a core-owned tie-breaker). Resolve in the data-model phase.
- **BeliefState primary key** — research proposes PK = caller-supplied `source_event_id`
  (free uniqueness; turns `get_scope_at` into a `state_id <= $as_of` scan); multi-scope
  needs a synthesized PK + logical `belief_id`. Ratify in the data-model / schema phase.
- **Backend port granularity** — where the port's contract sits: **Cypher-level** (run
  Cypher + params + manage tx; portable to any Cypher-speaking LPG; couples core to Cypher)
  vs. **LPG-primitive** (upsert node / add edge / match / bounded var-length traversal /
  unit-of-work tx; portable to any LPG incl. in-memory; but `get_impact`/`get_scope_at` may
  cost more round-trips than one Cypher query). Lean LPG-primitive; resolve the traversal
  performance tension in the Phase 2 ladybug spike.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

**Phase history:**
- **Phase 1 — Protocol, Backend Port & Data-Model Decisions** (complete 2026-06-14): typed `basedpyright`-strict foundation landed. Public `BeliefStore` Protocol (pydantic/typing-only, import-purity-guarded), a distinct internal LPG-primitive `BackendPort`, frozen pydantic v2 taxonomy (`extra="forbid"`, opaque `value`/UUID7), closed `BeliefFilter`, `ImpactResult` truncation contract, the UUID7 ordering contract, and the drafted `docs/backend-contract.md`. Decision-grade only — zero storage code; runtime behavior begins Phase 2 (backend adapters & schema-bootstrap spike).
- **Phase 2 — Backend Adapters, Schema Bootstrap & De-risking Spike** (complete 2026-06-15): the two backends behind `BackendPort` landed and run a shared parity suite — the zero-dep `InMemoryBackend` (oracle) and the ladybug reference backend (idempotent schema bootstrap, injected-connection + namespace tenancy, self-managed modes). D-03 reversal recorded: `pydantic` is the sole required runtime dep; `ladybug` moved to the `[ladybug]` extra. The 5 LPG primitives + `unit_of_work` are parity-tested; op bodies left for Phase 3.
- **Phase 3 — Append-Only Revision Spine (Keystone)** (complete 2026-06-16): the AGM write spine. `WORLD_SCOPE_ID="__world__"` + structural world-scope `contract()` guard; `Belief`/`BeliefState` split with immutable `HAS_REVISION` hub chains; **derived current** (D-01 — no stored `CURRENT_STATE` pointer; uniqueness is a theorem, SC3 verified as a Hypothesis consistency check on both backends); `revise`≡`expand` and vacuity-aware `contract`, plus `get_revision_chain`, each atomic in one `unit_of_work`. Closed the inherited DEF-02-01 value-corruption defect via a base64-over-JSON codec at the core↔port boundary. Suite green (105 passed) on both backends. Advisory code review left 5 warnings (no blockers) for follow-up.

---
- **Phase 4 — Retrieval & Observation Surface** (complete 2026-06-18): `query_scope` — the read the whole AGM postulate suite observes the belief base through — landed driver-blind in `MemoryCore` on both backends. Single scope-wide `match_nodes` scan + core-side group-by-belief per-group `_order_key` max → closed `BeliefFilter` post-filters (status precedence, `belief_ids`, inclusive event-range — a post-filter, NOT an as-of cut) → `_order_key` sort → hydrate; pure read (no `_ensure_scope`/`unit_of_work`, empty scope → `[]`). Factored a status-agnostic `_current_tail` (the `include_retracted=True` path) without breaking `_current`'s retracted-tail→`None` write-side contract. D-03 reversal: public flag `include_deprecated` → `include_retracted` (status taxonomy unchanged). Four-cell retracted-vs-superseded matrix proven on both backends (superseded cells via `get_revision_chain` + `SUPERSEDES`, never `query_scope`). Suite green (128 passed) on both backends; advisory code review left 2 warnings (test-coverage gaps: cross-scope isolation + multi-axis filter combos — no blockers).
- **Phase 5 — Edge Model & Contraction Cascade** (complete 2026-06-18): the generic edge surface and the cascade *mechanism* the Phase-7 Relevance/Core-Retainment postulates will be tested against. `MemoryCore.add_edge` (EDGE-01) is a closed-`EdgeType` passthrough inside one `unit_of_work` (idempotent; D-07 silent no-op on a missing endpoint, pinned by tests). `get_impact` (EDGE-02) composes a new keyword-only `direction="in"` traversal over `{DEPENDS_ON, DERIVED_FROM}` (SUPERSEDES excluded), returning `ImpactResult(reached, frontier, truncated=len(frontier)>0)` with the start excluded; the ladybug `state_id`-only-rows **hydration gap** is closed by a `match_nodes` re-fetch (RESEARCH Option A). The one genuine port change: `BackendPort.traverse` grew a `direction: Literal["in","out"]="out"` parameter (default `"out"` is a cross-phase contract for Phase 6 `get_scope_at`) — reverse-adjacency `_in_edges` in-memory, 3-site arrow-flip in ladybug, both injection-safe and cycle-safe. Direction grounded in narrative-vm `17 §2` (cascade = dependents of the contracted belief). Suite green (165 passed) on both backends, basedpyright strict clean; advisory code review left 3 warnings (WR-01 tenant `var_length_extend_max_depth` cap-restore clobber; WR-02 unbatched `get_impact` re-fetch lacks an atomic read scope; WR-03 `_DEPTH_CEILING` magic literal — all non-blocking, future hardening).

- **Phase 6 — Structural Time-Travel (`get_scope_at`)** (complete 2026-06-18): the last `BeliefStore` method. `get_scope_at` reconstructs a scope's active base *as of* an event, purely structurally from immutable `source_event_id`-ordered states, composing only `match_nodes` (core stays driver-blind). The one structural change vs `query_scope` is an inclusive `source_event_id <= as_of` cut applied BEFORE the per-belief ordering-max (cut-then-max = REWIND), with a cut-window retracted collapse. Proven by a pure-Python operational-fold oracle (`get_scope_at(scope, cut) == fold(ops, cut)`) under Hypothesis on both backends, with intra-ms-colliding/out-of-order UUID7 ids and `as_of` stepped across event ids (Phase 6, HIST-03).
- **Phase 7 — AGM/Hansson Backend Conformance Suite & Irony Join (M0 Exit Gate)** (complete 2026-06-19): the mechanically-verified proof that is the library's reason to exist, assembled as a backend conformance suite (BACK-05) — every registered backend passes the same postulate + invariant tests, in-memory as the AGM oracle, ladybug conforming identically (SKIP-not-fail when the driver is absent). Essentially no production code: the only change is extracting a pure `_current_tails(rows, allowed)` helper in `core.py` (a byte-identical lift of the `query_scope` derived-current pipeline, now single-sourced and reused by the divergence join). The Phase-3 `_SpineMachine` was extended in place with AGM revision postulates (K*2/K*3/K*5 as `@invariant`s, K*4/K*6 as `@given`) and the five Hansson base-contraction postulates against superseded-chain semantics (D-07, not partial-meet); FORMAL-03's named structural set registered (incl. lifting the Phase-6 `get_scope_at ≡ replay` fold property); AGM Recovery encoded as a strict `xfail` drift guard (`strict=True` on the mark — pyproject has no global `xfail_strict`) with passing superseded-chain positives in its slot; and the irony/divergence join (two scopes diverging on `belief_id` in one `match_nodes` round-trip vs a plain-Python oracle, no narrative naming in core). Anti-tautology held throughout — the shadow/fold oracles never call the SUT. Suite green (194 passed, 1 xfailed) on both backends, basedpyright strict clean; advisory code review clean (2 INFO: stale docstrings in `test_scope_at.py`). **M0 milestone formal core complete** — only Phase 8 publishable-polish (license, docs, CI/release, runtime-dep audit) remains.

- **Phase 8 — Publishable Polish** (complete 2026-06-19): the green-suite core made citable and shippable as a standalone OSS reference implementation. Overwhelmingly verification + wiring + content over an infrastructure base the cookiecutter and earlier phases had already front-loaded (mkdocs-material, CI/release/docs workflows, MIT LICENSE, `.cliff.toml`, `py.typed`, D-03 packaging). Closed the genuine gaps: PyPI-ready `pyproject.toml` metadata (PEP 639 SPDX `license`, `classifiers`, `keywords`, `[project.urls]`) — fresh wheel METADATA proves `pydantic` is the sole required dep with `ladybug` only under `extra == 'ladybug'`/`'all'`, `Requires-Python >=3.14` (PKG-02); README rewritten to lead with the Kumiho reference-implementation framing ("multi-scope extension, no recovery") + a runnable `docs/src/index.md` Quick Start that executes against the base install (PKG-03); the backend port contract relocated into `docs_dir` and wired into the mkdocs nav so `mkdocs build --strict` publishes `site/backend-contract/index.html`, git-cliff pinned to `.cliff.toml` in both `docs.yml` and `release.yml` (the dot-config was silently ignored), and the fresh-wheel `py.typed`/import gate confirmed (PKG-04). Also reconciled the phase's own stale acceptance prose (REQUIREMENTS PKG-02 + ROADMAP SC1) to the decided D-03 + 3.14-floor bar. No core logic touched; no PyPI tag pushed (pipeline-ready ≠ published, by design). Verification 13/13 must-haves; Phase-7 conformance suite unchanged (102 passed, 74 ladybug-extra skips, 1 strict xfail). **M0 / v0.1.0 milestone complete.**

*Last updated: 2026-07-04 — v0.2.0 Stance (R21) milestone scoped (`/gsd-new-milestone`)*
