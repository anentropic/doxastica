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

## Requirements

### Validated

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. All hypotheses until shipped. -->

- [ ] `BeliefStore` Protocol implemented against LadybugDB with a **flexible connection
      model**: accept an **injected** connection + namespace prefix (NVM's primary need —
      it owns the handle and leases it under label tenancy), *and* be able to open/manage
      its own connection for standalone and other usages. Tests use private throwaway
      databases.
- [ ] **Scopes** as named belief-holders, including a privileged **world scope** where
      `contract()` is an error (append-only / no-retcon enforcement point)
- [ ] **`Belief` / `BeliefState` split** — stable identity + immutable, append-only
      revision chain; single mutable `CURRENT_STATE` pointer; one belief per `Belief` node
- [ ] Core belief operations: `revise`, `expand`, `contract`, `get_or_create_scope`
- [ ] **Generic typed edges** — `SUPERSEDES`, `DEPENDS_ON`, `DERIVED_FROM` (no epistemic
      semantics; NVM layers meaning on top) via `add_edge`
- [ ] **`get_impact`** — bounded-depth contraction-cascade traversal over dependency edges
      (mechanism only; policy is NVM's)
- [ ] **`get_scope_at`** — structural time-travel query ("what did this scope hold as of
      event E"), answerable from immutable event-id-ordered states
- [ ] `get_revision_chain` and `query_scope` (with `include_deprecated` flag) retrieval
- [ ] **Opaque values + opaque event ids** — the core stores `value: Any` and UUID7
      event ids it never interprets (no triple structure, no provenance semantics inside)
- [ ] **Deprecated vs. superseded** as a structural/query distinction (core), with meaning
      left to NVM
- [ ] **AGM postulate property-test suite** (Hypothesis over operation sequences): success,
      inclusion, vacuity, consistency, extensionality — recovery deliberately excluded
- [ ] **Structural-invariant tests**: `CURRENT_STATE` uniqueness per belief, chain
      immutability, `get_scope_at` ≡ event replay
- [ ] **Irony-join demonstration** on synthetic data: actor-scope vs. world-scope
      divergence computed as a single query
- [ ] Packaged from the `cookiecutter-python-uv-library` template (uv, basedpyright strict,
      ruff, pytest) depending on **`ladybugdb` + `pydantic` only**, zero NVM imports
- [ ] **Publication-ready**: MIT license, docs site, GitHub Actions CI + release config,
      PyPI-ready packaging; README leads with "standalone reference implementation of
      Kumiho (arXiv 2603.17244), multi-scope extension, no recovery"

### Out of Scope

<!-- Explicit boundaries with reasoning, to prevent re-adding. -->

- **Any NVM / game / narrative concept** (actors, turns, scenes, plausibility, diegetic
  time, GM context assembly) — the seam exists precisely to keep these out; their meaning
  lives in the NVM interface layer above the Protocol
- **AGM recovery postulate** — incompatible with immutable versioning; superseded-chain
  semantics is the deliberate, better behaviour (per the Kumiho analysis)
- **LLM / inference of any kind** — M0 is the zero-LLM milestone; NL→triple mapping and
  entrenchment policy are NVM-layer prompt-engineering concerns
- **Storage abstraction over the database** — a non-goal; the DI seam is NVM↔core, not
  core↔database. The core is pinned to LadybugDB/Cypher on purpose
- **Entity nodes, topology, sheet/mechanical state, the Chronicle, prospective indexing,
  the planner cache** — all NVM-owned; the core subgraph is closed (no outbound graph refs)
- **Epistemic edge labels** (`WITNESSED_BY`, `TOLD_BY`, `INFERRED_FROM`) and **stance
  policy** — these are NVM specialisations of generic edges / NVM rules; the core only
  stores and compares
- **Owning the database** — the core is a label-family *tenant* in a shared embedded DB,
  not its owner

## Context

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

- **Tech stack**: Python (uv) — runtime deps **`ladybugdb` + `pydantic` only**, zero NVM
  imports. Why: the repo boundary keeps the implementation faithful to the paper's
  domain-agnostic model and the single-writer embedded constraint enforces write
  serialization for free.
- **Tooling**: `cookiecutter-python-uv-library` template — basedpyright strict typing,
  ruff lint/format, pytest + coverage, pre-commit, git-cliff changelog, GitHub Actions.
- **Storage**: pinned to LadybugDB / Cypher (`ladybugdb`, https://github.com/LadybugDB/ladybug,
  a uv dependency). **Flexible connection**: `MemoryCore` accepts an injected connection +
  namespace prefix (NVM leases it under label tenancy) *and* can open/manage its own
  connection for standalone use. The DI seam stays NVM↔core, not core↔database (no storage
  abstraction over the DB).
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

### Open questions to resolve during planning

- **`query_scope(query: str)` semantics** — what does `query` mean without leaking triple
  structure into the core? (memory-core §10.1)
- **Type-dependent entrenchment storage** — NVM policy wants edge in-degree; verify the
  Protocol surface (`get_impact`-style traversal) suffices without core changes (§10.2)
- **`get_impact` cascade truncation** — depth default and truncation-boundary behaviour
  (§10.3)
- **Seed authored invariants into the world scope at build?** — lean yes, for uniform
  querying (§6 residual / §10.4)
- **`ladybugdb` connection surface** — `ladybugdb` is real (https://github.com/LadybugDB/ladybug,
  installed via uv). Confirm its connection/Cypher API and design the flexible model
  (accept-injected vs. open-own) cleanly around it (research target)

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

---
*Last updated: 2026-06-13 after initialization*
