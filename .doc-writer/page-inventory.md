# Proposed Documentation

Based on a scan of `src/doxastica/` (public `__all__`: `MemoryCore`, `BeliefStore`,
`InMemoryBackend`, the value layer `Belief` / `BeliefFilter` / `BeliefState` /
`ImpactResult` / `Scope` / `EdgeType` / `Status` / `WORLD_SCOPE_ID`, the errors
`DoxasticaError` / `WorldScopeContractionError` / `BackendDependencyError`, plus the
out-of-root `LadybugBackend`) and `.doc-writer/gap-report.md`, here is the proposed
**prose-layer** page inventory.

This inventory deliberately covers **only the undocumented prose gaps**. It does NOT
re-document:

- the `index.md` quick-start (in-memory construction + basic `revise` + `query_scope`),
- the `backend-contract.md` backend-author `BackendPort` contract, or
- the auto-generated per-symbol mkdocstrings API reference (`reference/`).

The persona is a single advanced integrator (Python/pydantic/DI-fluent, new to
belief-revision theory). Their `never_assume` list is almost entirely conceptual, so the
**Explanation** section is the largest and highest-value block; the **How-To** guides map
one-to-one onto the configured `user_tasks` not already shown in the quick-start; one
**Tutorial** stitches the whole operation surface into a single learn-by-doing lesson.

## Page Inventory

| # | Type | Title | Key Sections | File Path |
|---|------|-------|--------------|-----------|
| 1 | tutorial | Your First Belief Store: Revise, Supersede, Time-Travel | Prerequisites; build the core (DI); revise then read; expand vs revise; contract a belief; walk the revision chain; reconstruct an earlier state; what you learned | docs/src/tutorials/first-belief-store.md |
| 2 | (section-index) | Tutorials | 1-sentence abstract per tutorial | docs/src/tutorials/index.md |
| 3 | how-to | How to Use the LadybugDB Backend | Requirements (`doxastica[ladybug]`); open a file/`:memory:` backend; inject into `MemoryCore`; close + ownership; troubleshooting `BackendDependencyError` | docs/src/how-to/ladybug-backend.md |
| 4 | how-to | How to Lease a Shared Ladybug Connection (Tenant Mode) | Requirements; `from_connection` + namespace; why the core never closes a leased handle; namespace rules; verification; troubleshooting | docs/src/how-to/lease-shared-connection.md |
| 5 | how-to | How to Retract a Belief with `contract` | Requirements; call `contract`; vacuity no-op; the world-scope guard; observing the retracted tail via `include_retracted`; troubleshooting `WorldScopeContractionError` | docs/src/how-to/contract-a-belief.md |
| 6 | how-to | How to Query the Current Belief Base with `BeliefFilter` | Requirements; the four closed fields; narrow by `belief_ids`; filter by `status`; `event_id_min`/`event_id_max`; `include_retracted` precedence; verification | docs/src/how-to/query-with-belief-filter.md |
| 7 | how-to | How to Inspect Revision History with `get_revision_chain` | Requirements; call it; read the ordered chain; cross-scope behaviour; pair with `query_scope`; verification | docs/src/how-to/inspect-revision-history.md |
| 8 | how-to | How to Reconstruct a Scope's State at a Point in Time | Requirements; call `get_scope_at` with an `as_of` event id; inclusive-cut semantics; contrast with `query_scope` event-range; verification | docs/src/how-to/reconstruct-scope-at.md |
| 9 | how-to | How to Trace a Dependency Cascade with `get_impact` | Requirements; lay `DEPENDS_ON` / `DERIVED_FROM` edges with `add_edge`; call `get_impact`; read `ImpactResult` (`reached` / `frontier` / `truncated`); bound the walk with `depth`; verification | docs/src/how-to/trace-dependency-cascade.md |
| 10 | (section-index) | How-To Guides | 1-sentence abstract per guide | docs/src/how-to/index.md |
| 11 | explanation | What Is AGM Belief Revision? Revise, Expand, Contract | The epistemic problem; belief base vs belief set; the three operations; what doxastica keeps vs drops (recovery); postulates and why mechanical verification matters | docs/src/explanation/agm-belief-revision.md |
| 12 | explanation | The Kumiho Architecture | What Kumiho is (arXiv 2603.17244); graph-native ground triples; append-only spine; doxastica's two deliberate departures (multi-scope, no-recovery); the zero-narrative boundary | docs/src/explanation/kumiho-architecture.md |
| 13 | explanation | Scopes and the World Scope | What a scope is; multi-scope as a Kumiho extension; the reserved `WORLD_SCOPE_ID`; why world-scope `contract()` is forbidden; `get_or_create_scope` semantics | docs/src/explanation/scopes-and-world-scope.md |
| 14 | explanation | The Superseded Chain: Append-Only, No Recovery | Append-only revision spine; `SUPERSEDES` / `HAS_REVISION` structure; why nothing is ever deleted; how superseded-chains replace AGM recovery; the audit-history payoff | docs/src/explanation/superseded-chain-no-recovery.md |
| 15 | explanation | The Two Seams: `BeliefStore` vs `BackendPort` | The public structural `BeliefStore` Protocol; the internal `BackendPort`; why two seams; what each audience touches; driver-blind core / pluggable backends | docs/src/explanation/beliefstore-vs-backendport.md |
| 16 | explanation | Derived Current State and the UUID7 Ordering Contract | "Current is a theorem, not a stored pointer"; the `(source_event_id, state_id)` order; UUID7 and intra-ms collisions; how current is computed; why no `CURRENT_STATE` edge | docs/src/explanation/derived-current-uuid7-ordering.md |
| 17 | (section-index) | Explanation | 1-sentence abstract per page | docs/src/explanation/index.md |

> Note: `(section-index)` entries (#2, #10, #17) are the MkDocs-Material section landing
> pages required by the sidebar-only nav with `section-index`. They are not Diataxis
> content pages; each lists its section's children with a one-sentence inline abstract.

## API Reference status

**Detected — auto-generated.** `mkdocstrings` (Google-style) + `gen-files`
(`docs/scripts/gen_ref_pages.py`) + `literate-nav` (`SUMMARY.md`) + `section-index`
generate the per-symbol `reference/` tree at build time from source docstrings. Every
symbol in `doxastica.__all__` (plus the out-of-root `LadybugBackend`) therefore already has
symbol-level reference coverage.

Consequences for Phase 2:

- **Do NOT hand-author any `reference/` Markdown.** The tree is generated.
- Inline `code` mentions of public symbols in the prose pages above MUST link to their
  generated reference entry (Quality Rule 4), using the mkdocstrings link form pointing at
  the generated `reference/` path (e.g. `MemoryCore.contract`, `BeliefFilter`,
  `ImpactResult`, `WorldScopeContractionError`).
- `LadybugBackend` lives at `doxastica.backends.ladybug` and is NOT re-exported from the
  package root — link its reference entry under that module path and always show the
  explicit `from doxastica.backends.ladybug import LadybugBackend` import in examples.
- `BackendPort` (`doxastica.ports`) is INTERNAL (the backend-author seam). Reference it
  only in pages #14/#15 and only as the internal counterpart to `BeliefStore`; do not
  steer the integrator persona toward implementing it.

## Audience targeting

A single persona is configured — **"Python developers integrating doxastica into a larger
system (e.g. NVM)"**, advanced, Python/pydantic/DI-fluent but new to belief-revision
theory. Every page targets this persona. Calibration notes per type:

- **Tutorial (#1)** and **How-To (#3–#9)**: assume Python/pydantic/DI/extras/graph-DB
  fluency freely; define every epistemic term (revision, supersession, contraction, scope,
  world scope, derived current) at first use, or link to its Explanation page.
- **Explanation (#11–#16)**: these EXIST to discharge the `never_assume` list. They carry
  the conceptual load (AGM, Kumiho, multi-scope/world-scope, superseded-chain/no-recovery,
  the two seams, UUID7/derived-current) so the task pages can stay terse and link out.
- Tone is `personality`: light humour permitted in admonitions/analogies that help a Python
  expert grok AGM — never in code, signatures, postulates, world-scope rules, or the
  append-only contract. Never sacrifice correctness for a joke.

## Coverage mapping (gap-report → pages)

- `expand` → #1 (tutorial), #11 (explanation: revise≡expand at the core)
- `contract` + world-scope guard + vacuity → #5 (how-to), #13 + #11 (explanation)
- `get_revision_chain` → #1, #7
- `get_scope_at` → #1, #8, #16 (ordering/cut semantics)
- `get_impact` + `ImpactResult` → #9
- `add_edge` (`DEPENDS_ON` / `DERIVED_FROM` / `SUPERSEDES`) → #9, #14
- `get_or_create_scope` → #13
- `LadybugBackend.open` → #3
- `LadybugBackend.from_connection` (tenant) → #4
- `LadybugBackend.close` / `owns_conn` → #3, #4
- `BeliefFilter` (four closed fields + status precedence) → #6
- `BeliefState` (six-field closed set) → #1, #11, #16
- `EdgeType` / `Status` (closed taxonomies) → #6 (Status), #9 (EdgeType), #14
- `Scope` / `WORLD_SCOPE_ID` → #13
- `BeliefStore` Protocol (vs internal `BackendPort`) → #15
- `DoxasticaError` / `WorldScopeContractionError` / `BackendDependencyError` → #5, #3
  (raised-when context), reference for full signatures

## Coverage gaps / notes

- **`Belief`** (the bare `belief_id` identity model) is in `__all__` but is an internal
  structural node the integrator never constructs directly (the core auto-materialises it on
  write). No dedicated prose page is proposed; it is mentioned only where it clarifies the
  `HAS_REVISION` hub in #14. Its API-reference entry is auto-generated.
- **README.md / MAINTAINER.md** are intentionally NOT proposed: this run is scoped to
  closing the prose gaps in `docs/src`, and a README already exists. If you want either
  refreshed or created, say so and they can be added to the inventory.
- **No Use Cases section** is proposed (`use_cases_section: false` in config); the three
  inferred use cases in `context.md` are used to enrich the tutorial and explanation pages
  rather than becoming their own section.
- **Async** is deliberately out of scope (M0 is the sync deterministic core); no async pages
  or examples are proposed.
- **`unit_of_work`** is exposed on `MemoryCore` but is a low-level atomicity primitive; it
  is mentioned in passing in #14 (multi-edge atomicity) rather than given its own page.
