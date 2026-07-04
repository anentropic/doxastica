# Doc Writer Context

**Generated:** 2026-06-22
**Source:** /doc-writer:setup researcher
**Editable:** Yes -- manual edits are preserved until the next --refresh-context run. To make permanent changes, edit config.yaml and re-run setup.

## Project Summary

doxastica is a standalone Python library implementing the **Kumiho** architecture (arXiv 2603.17244): a graph-native, append-only **AGM belief-revision core** with zero game/narrative/LLM concepts inside it. It exposes a clean public `BeliefStore` Protocol and an internal `BackendPort` seam, ships a zero-dependency `InMemoryBackend` (also the AGM oracle) plus an optional `ladybug` reference backend (`pip install doxastica[ladybug]`), and is built primarily for the narrative-vm (NVM) project as its M0 milestone. Its defining promise is *provable correctness*: AGM/Hansson postulates and structural invariants are verified mechanically, with append-only revision spines, derived (never stored) current state, and a deliberate no-recovery (superseded-chain) model.

*Inferred from: README, pyproject.toml, src/doxastica/__init__.py public API, CLAUDE.md.*

## User Persona: Python developers integrating doxastica into a larger system (e.g. NVM)

### Profile
- **Skill level:** advanced
- **What they know:** Fluent in modern Python 3.14, pydantic v2 (frozen models, validation, `BaseModel`), `typing.Protocol`-based structural typing, dependency injection as a construction pattern, package extras (`pip install x[y]`), and the basics of graph databases / embedded data stores (nodes, edges, traversal). They do not need HTTP, REST, async, or web-framework hand-holding.
- **What to always explain:** The entire epistemic domain. Always spell out AGM belief revision (revise / expand / contract) and what each operation *means*; the AGM/Hansson postulates and why mechanical verification matters; the Kumiho architecture; the multi-scope extension and world-scope rules; the superseded-chain (no-recovery) model and how it replaces AGM *recovery*; the public `BeliefStore` vs internal `BackendPort` seam distinction and why the boundary exists; and the UUID7-ordering / derived-current contract (current state is a *theorem*, not a stored pointer). Never assume the reader has met any of these before -- they are graph/Python experts who are new to belief-revision theory.
- **Their world:** They are wiring an append-only belief / knowledge-state layer into a larger application -- typically NVM's epistemic layer. Their daily problem is keeping a knowledge base that changes over time *correct and auditable*: they need to record new information, supersede stale information without destroying history, reconstruct past states, and trace how one belief's change ripples through dependents. They already work with pydantic models and DI containers; they want a substrate whose correctness they can trust without auditing it themselves, and that leaks zero domain concepts (no narrative, no LLM) into their store.
- **How they found this library:** Either as NVM's declared M0 dependency, or by following the Kumiho paper (arXiv 2603.17244) while searching for a *reference* AGM belief-revision implementation they could cite or reuse. They likely weighed rolling their own over a graph DB, or adapting an academic AGM toolkit, and chose doxastica because it is provably correct, append-only by construction, and storage-pluggable.

### Common Tasks
- **Construct a MemoryCore with an injected backend:** Pure DI -- build the backend, then inject it: `MemoryCore(InMemoryBackend())`, or `MemoryCore(LadybugBackend.open(path))` / `LadybugBackend.from_connection(conn)`. There is NO `MemoryCore.in_memory()` factory and no factories layer; always show explicit construction.
- **revise / expand / contract beliefs in a scope:** Apply the three AGM operations against a scope; each appends to an immutable revision chain rather than mutating. `contract()` on the world scope is an error.
- **Read the current belief base via query_scope:** Query the derived current tail of a scope, narrowing with a closed `BeliefFilter`; results never include superseded states.
- **Inspect revision history with get_revision_chain:** Walk the immutable `HAS_REVISION` chain for a belief to see every prior state in order.
- **Reconstruct scope state at a point in time with get_scope_at:** Structural time-travel -- rebuild what a scope's current base was as of a given point, using chain ordering rather than a stored snapshot.
- **Trace dependency cascades with get_impact:** Bounded, cycle-safe cascade over `{DEPENDS_ON, DERIVED_FROM}` edges to see what a belief change affects.
- **Lease a shared ladybug connection under a namespace (tenant mode):** Inject an existing `Connection` via `LadybugBackend.from_connection(conn)` with a namespace prefix; the core is a tenant and never closes a connection it does not own.

### Writing Guidance for This Persona
- When explaining an operation (e.g. `contract`), assume the reader knows Python and pydantic but spell out the AGM semantics: what *contraction* means epistemically, what the postulates require, and how doxastica's append-only/no-recovery model differs from textbook AGM.
- Use precise CS/graph vocabulary freely (nodes, edges, traversal, frozen model, Protocol, DI) but define every epistemic term (belief base, revision, supersession, scope, world scope, derived current) at first use.
- Examples should reflect their world: building a knowledge layer for a larger system. Prefer scenarios that show append-only history, time-travel, and impact cascades over toy "hello world" beliefs. Always construct via explicit DI, never an imagined factory.
- Lead with the seam distinction when relevant: most readers touch `BeliefStore` / `MemoryCore`; only backend authors touch `BackendPort`.

## Use Cases

### Append-only belief management with audit-safe history

**Problem:** A larger system (e.g. NVM) needs to track an evolving knowledge base where facts change over time, but it must never silently lose what was previously believed -- destroying history makes the system impossible to audit or debug, and ad-hoc "just overwrite the row" approaches lose the provenance that downstream reasoning depends on.
**What's possible:** doxastica records every change as a new `BeliefState` appended to an immutable `HAS_REVISION` chain via `revise` / `expand`. Superseded states stay on the chain forever; `query_scope` returns only the derived current tail (uniqueness is a theorem, not an enforced pointer). Show construction via `MemoryCore(InMemoryBackend())` and a revise-then-query round trip.
**Outcome:** The current belief base is always exactly the live tail (no duplicates, no stale rows), while the full history remains queryable -- correctness backed by mechanically verified AGM postulates.
**Relevant persona(s):** Python developers integrating doxastica.
**Source:** inferred

### Structural time-travel and dependency-impact analysis

**Problem:** When a belief changes, developers need to answer two hard questions cheaply: "what did the world look like before this change?" and "what else does this change affect?" Recomputing these by hand over a mutable store is error-prone and slow.
**What's possible:** `get_scope_at` reconstructs a scope's state at a point in time purely from chain structure (no stored snapshots), and `get_impact` runs a bounded, cycle-safe cascade over `{DEPENDS_ON, DERIVED_FROM}` edges returning an `ImpactResult`. Illustrate with `get_revision_chain` to show the underlying immutable spine first.
**Outcome:** Deterministic, reproducible reconstruction of past states and a finite, terminating set of impacted beliefs -- safe even in the presence of dependency cycles.
**Relevant persona(s):** Python developers integrating doxastica.
**Source:** inferred

### Pluggable storage behind one protocol (in-memory vs ladybug)

**Problem:** Teams want a zero-friction core for tests and local development but a durable graph backend in production -- without rewriting call sites or pulling a heavy dependency into every install.
**What's possible:** The same `BeliefStore` behaviour is available via `MemoryCore(InMemoryBackend())` (pydantic-only, zero extra deps, doubles as the AGM oracle) or the `[ladybug]` extra (`LadybugBackend.open(path)` / `.from_connection(conn)` for leased/tenant use). Content tabs are ideal for showing the two construction paths side by side.
**Outcome:** Identical AGM semantics across backends, verified by the in-memory oracle as a conformance baseline; production code swaps backends by changing one constructor argument.
**Relevant persona(s):** Python developers integrating doxastica.
**Source:** inferred

> These use cases were inferred from persona context and codebase analysis. To promote use cases to a documentation section, run `/doc-writer:setup` and provide explicit use cases.

## Tone: personality

### Writing Rules
- Same depth and structure as warm-but-businesslike: 1-2 sentence intros, multiple examples per concept, troubleshooting/common-mistakes where relevant, transition sentences between major sections.
- Occasional light humour is welcome in admonitions and transitions -- but never in code examples, API descriptions, or correctness-critical instructions (postulates, world-scope rules, append-only contract).
- First person is allowed sparingly ("We'll start by building the backend..."); keep it rare and purposeful.
- Put personality in analogies and explanations of the *epistemic* concepts (where it genuinely helps a Python expert grok AGM), not in signatures or parameter docs.
- **Never sacrifice correctness for a joke.** This library's whole value proposition is provable correctness; if a quip risks obscuring a postulate, a seam boundary, or the no-recovery model, cut it.
- Technical precision is non-negotiable: explain every AGM/Kumiho concept fully (never assume it), while assuming strong Python/pydantic/DI fluency.

## Framework Preferences: mkdocs-material

### Navigation Strategy
- Strategy: **Sidebar only.** All pages appear in the left sidebar with no top tabs (`navigation.tabs` is NOT enabled; `navigation.sections` IS, so sections render as expandable groups).
- The authored page count is small; do not add a tabs layer or invent dropdown hierarchies.
- Section index pages: with `mkdocs-section-index` enabled, a section's index page is clickable directly; where a section groups children, the index should give a one-sentence abstract per child.
- Front page (`index.md`) is linked as "Overview"-style landing at the top of the sidebar. The current nav labels it "Home" -- prefer "Overview" for new top-level landing entries.
- Navigation is driven by `nav:` in `mkdocs.yml` plus `literate-nav` (`SUMMARY.md`) for the generated API reference; do not hand-maintain the `reference/` tree.

### Features to Use
- **Admonitions** (`admonition` + `pymdownx.details`): use `!!! warning` for the no-recovery / superseded-chain caveat and the world-scope-`contract()`-is-an-error rule; `!!! info` / `!!! note` for AGM/Kumiho background; `!!! tip` for ergonomic DI hints. Collapsible `???` for long asides. Do not stack admonitions back-to-back.
- **Mermaid diagrams** (`pymdownx.superfences` custom fence): diagram the two seams (`BeliefStore` vs `BackendPort`), the immutable `HAS_REVISION` revision chain, and the `get_impact` cascade over `{DEPENDS_ON, DERIVED_FROM}`. Prefer a diagram over prose for structure.
- **Content tabs** (`pymdownx.tabbed`, `alternate_style: true`): show multi-construction examples side by side -- in-memory (`MemoryCore(InMemoryBackend())`) vs ladybug (`LadybugBackend.open(path)` / `.from_connection(conn)`).
- **Code annotations** (`content.code.annotate` + `attr_list`): annotate the DI construction line and revise/query examples to call out the derived-current and append-only behaviour inline.
- **mkdocstrings (Google style)**: API reference is auto-generated via `docs/scripts/gen_ref_pages.py` + `literate-nav` `SUMMARY.md` + `section-index`. Write Google-style docstrings in source; do NOT hand-author API reference pages. `merge_init_into_class` is on, so document constructor params in the class docstring.
- **Code copy + highlight** (`content.code.copy`, `pymdownx.highlight`): always give fenced code blocks a language identifier (`python`, `bash`).
- **Snippets** (`pymdownx.snippets`): may embed shared snippet files; keep runnable examples accurate (the Quick Start uses `from uuid import uuid7`, requiring the 3.14 floor).

### Features NOT to Use
- **`navigation.tabs` / top tabs / dropdowns:** not enabled; the project is sidebar-only.
- **Hand-authored API reference pages:** the `reference/` tree is generated -- never write Cypher- or signature-level reference Markdown by hand.
- **Async API examples:** M0 is the deterministic sync core; do not show `AsyncConnection` or async usage.
- **String-interpolated Cypher in examples:** if backend internals appear, use parameterized `$name` form -- never f-string interpolation.
- **An imagined `MemoryCore.in_memory()` factory or factories layer:** does not exist; always show pure DI construction.
- **Game / narrative / LLM framing:** zero such concepts belong in any example; keep illustrations to scopes, beliefs, and revisions.
