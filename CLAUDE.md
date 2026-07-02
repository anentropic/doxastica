<!-- GSD:project-start source:PROJECT.md -->
## Project

**doxastica**

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

**Core Value:** A correct, append-only belief-revision core behind a clean `BeliefStore` Protocol whose
correctness is *provable* — AGM postulate compliance and structural invariants verified
mechanically, with zero narrative semantics leaking into it. If everything else is
deferred, the formal core and its property-test suite must be right.

### Constraints

- **Tech stack**: Python (uv) — **`pydantic` v2 is the only REQUIRED runtime dep**; **`ladybug`
  (the LadybugDB PyPI package, a Kùzu fork, import `ladybug as lb`) is the reference-backend
  extra (`doxastica[ladybug]`)** behind the Phase-1 `BackendPort` seam; future backends are
  extras too. Keep the runtime footprint lean — prefer the stdlib for trivial needs — but a
  well-chosen dependency is a judgment call, not something to avoid on principle: there is no
  ban on adding one where it genuinely earns its place. Why lean: a small, easy-to-adopt
  reference implementation, and LadybugDB's single-writer/multi-reader embedded model enforces
  write serialization for free when the reference backend is in use. (The core stays
  domain-agnostic — no consumer-application concepts inside it — but that is the separate
  **Boundary** constraint below, not a dependency rule.)
  > **Phase 2 D-03 decision-grade reversal (recorded, not silent — sibling to the Phase 1 §2
  > 3.14-floor decision):** the original "runtime deps **exactly `ladybug` + `pydantic`**"
  > constraint is REVERSED. `pydantic` is the sole required dep; `ladybug` moved to
  > `[project.optional-dependencies]`. `pip install doxastica` ships a working in-memory AGM
  > core with zero ladybug install; `pip install doxastica[ladybug]` adds the reference backend.
- **Tooling**: `cookiecutter-python-uv-library` template — basedpyright strict typing,
  ruff lint/format, pytest + coverage, pre-commit, git-cliff changelog, GitHub Actions.
- **Storage**: LadybugDB / Cypher is the **reference** backend (PyPI package **`ladybug`**, a
  Kùzu fork — https://github.com/LadybugDB/ladybug), reached through the Phase-1 `BackendPort`.
  > **SUPERSEDED (Phase 1 BACK-01 + Phase 2 D-03):** the original "**pinned to LadybugDB** /
  > no storage abstraction" framing is superseded. The `BackendPort` *is* the seam; ladybug is
  > the *reference* backend behind it (with the zero-dep `InMemoryBackend` as the second
  > shipping backend and Phase-7 oracle), not the only substrate. `BackendPort` is a narrow
  > port, NOT a repository/storage-abstraction layer — that non-goal still holds.
  Ladybug API (still accurate for the reference backend): `lb.Database(path | ":memory:")` →
  `lb.Connection(db)` → `conn.execute(cypher, parameters=...)`; schema-first (CREATE
  NODE/REL TABLE), uniqueness only via PRIMARY KEY. **Flexible connection**: the ladybug backend
  accepts an injected `Connection` + namespace prefix (NVM leases it under label tenancy;
  the core never closes it) *and* can open/manage its own (`:memory:` or file) for
  standalone use. The DI seam stays NVM↔core (the `BackendPort`), not core↔database.
- **Discipline**: append-only — no operation removes or rewrites `BeliefState` nodes or
  `HAS_REVISION` edges; revision is forward-only. World-scope `contract()` is an error.
- **Boundary**: no game/narrative/LLM concepts in core code; each such appearance is the
  leak the seam exists to prevent.
- **License**: MIT (publishable as an OSS reference implementation).
- **Testing**: AGM-postulate compliance as property tests (Hypothesis), LLM-free.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## TL;DR for the roadmap
## Recommended Stack
### Core / Runtime Dependencies
| Technology | Version pin | Purpose | Why |
|------------|-------------|---------|-----|
| **ladybug** | `>=0.17,<0.18` | Embedded graph DB + Cypher; the pinned storage substrate | The project deliberately pins storage to LadybugDB/Cypher (no abstraction layer). Embedded single-writer model *enforces* write serialization for free (a stated design payoff). Verified PyPI name `ladybug` 0.17.1, `requires-python <3.15,>=3.10` — covers the whole 3.11–3.14 band. |
| **pydantic** | `>=2.11,<3` | Typed value/model layer at the API boundary (`Scope`, `BeliefState`, `EdgeType`) | v2 is the current line (2.13.4). Rust core, fast validation, frozen models for immutable `BeliefState`. `requires-python >=3.9` — no floor problem. |
### The UUID7 decision (RESOLVED — floor raised to 3.14)
- **Python 3.14** ships `uuid.uuid7()` natively (new in 3.14, RFC 9562 §5.7, monotonic — verified). The core mints `state_id` UUID7 keys from the stdlib — **no runtime dependency, no dev shim**.
- **Locked (CONTEXT decision #2, Phase 1):** `requires-python>=3.14`. The earlier 3.11–3.13 gap (no stdlib `uuid.uuid7()`) is moot — the floor was deliberately raised to 3.14 so UUID7 minting is native — the core has no runtime UUID dependency. (Per the Phase 2 D-03 reversal above, `pydantic` is the sole required runtime dep and `ladybug` is the reference-backend extra; UUID7 minting adds no third runtime dep regardless.) NVM is assumed to target 3.14.
### Development Tools (from cookiecutter — verified current, no re-litigation)
| Tool | Template pin | Current (2026-06) | Notes |
|------|--------------|-------------------|-------|
| **uv** (+ `uv_build`) | build `uv_build>=0.9.18`, pre-commit `uv-lock@0.10.3` | aligned | Build backend + env/lock manager. Keep. |
| **basedpyright** | `>=1.38.0` (strict) | 1.39.7 | Strict typing is ideal for a "provably correct" core. See config notes. |
| **ruff** | `>=0.15.1` | 0.15.17 | Lint + format. Rule set `E,F,W,I,UP,B,SIM,TCH,D` is good. |
| **pytest** | `>=8.0.0` | 9.0.3 | `>=8` happily resolves to 9.x. No change needed. |
| **pytest-cov** | `>=6.0.0` | 6.x line | Coverage. |
| **hypothesis** | *(not in template — ADD)* | **6.155.2** | The AGM property-test engine. **Add to dev group.** `requires-python>=3.10`. |
| pre-commit (`prek`) | configured | — | ruff + ruff-format + uv-lock + basedpyright (local) + blacken-docs. |
| git-cliff | `.cliff.toml` present | — | Conventional-commits changelog. |
| mkdocs-material | docs group pinned | 9.7.x | Chosen docs framework (the cookiecutter also offers sphinx-shibuya; PROJECT wants a docs site — mkdocs-material is the lower-friction pick and is already wired with mkdocstrings). |
## Installation
# Runtime: pydantic is the only REQUIRED dep; ladybug is the reference-backend extra (D-03)
#   pip install doxastica            -> pydantic + working in-memory backend
#   pip install doxastica[ladybug]   -> adds the ladybug reference backend
# Dev / test tooling (hypothesis is the addition over the template defaults)
# pytest, pytest-cov, basedpyright, ruff, ipython, pdbpp come from the template
# (No UUID7 shim — the floor is 3.14, so `uuid.uuid7()` is in the stdlib. See "Python version posture".)
## Ladybug — the high-value detail (verified against docs.ladybugdb.com)
### Connection API (verified)
# On-disk
# In-memory (use ":memory:" OR "")
# Parameterized Cypher (REQUIRED style — string interpolation "strongly discouraged")
# Also: res.get_all() -> list[tuple]; res.has_next()/res.get_next();
#       res.get_as_df() (Pandas) / get_as_pl() (Polars) / get_as_arrow()
### Transaction / concurrency model (verified)
- **One write transaction at a time; many concurrent reads.** WAL-backed, serializable. The embedded single-writer rule is exactly the property the design wants — write serialization "for free."
- **Auto-commit:** a bare statement is auto-wrapped in a serializable transaction.
- **Manual transactions** via Cypher statements: `BEGIN TRANSACTION;` / `BEGIN TRANSACTION READ ONLY;` / `COMMIT;` / `ROLLBACK;` — issued through `conn.execute(...)`. Useful for grouping a multi-statement `revise()` (deprecate old `CURRENT_STATE`, append new `BeliefState`, repoint pointer) atomically.
- `CHECKPOINT;` merges WAL → data files (also automatic).
### Async (verified)
### Schema / DDL note (Kùzu-lineage, MEDIUM confidence — verify in spike)
### Namespace / label-prefix support (design implication)
## The flexible-connection model (the core design seam) — concrete sketch
- **Ownership is explicit (`_owns_db`).** Injected mode must never close someone else's handle (R19: the core is a *tenant*).
- **Schema bootstrap runs in both modes**, idempotently (`IF NOT EXISTS`), because an injected connection's DB may be fresh or shared.
- The DI seam stays NVM↔core (a `Connection` object), never core↔storage-abstraction — matching the "no storage abstraction" non-goal.
## Testing stack — throwaway DBs + Hypothesis stateful (verified)
### Throwaway databases
### Hypothesis stateful testing for AGM postulates (verified API, 6.155.2)
# Pytest entrypoint:
- **`Bundle`** to track created scopes/beliefs so later rules draw real ids (not random misses).
- **`@initialize`** to spin up the throwaway in-memory DB exactly once per example run.
- **`@invariant`** for structural invariants checked after *every* step (`CURRENT_STATE` uniqueness, chain immutability).
- **`@precondition`** to gate `contract` on existing beliefs and to route world-scope-contract-is-an-error into its own assertion.
- **Shadow/oracle model** (the `self.model` dict) is the standard way to assert AGM postulates (success, inclusion, vacuity, consistency, extensionality) — compare the real store against the simple in-memory oracle.
- Drive it via `BeliefStoreMachine.TestCase` (pytest auto-collects) or `run_state_machine_as_test(BeliefStoreMachine)` for manual settings.
- Pair the stateful machine with ordinary `@given` property tests for single-operation postulates (extensionality, vacuity) where a full sequence is overkill.
## basedpyright / strict-typing notes for this library
- Template sets `typeCheckingMode = "strict"`, `pythonVersion = "3.14"`, `include = ["src","tests"]`. Good.
- **Ladybug ships types?** Unverified — likely partial. If `lb.Connection` / `lb.execute` return `Any`/untyped, strict mode will flag `reportUnknownMemberType` etc. Plan to wrap Ladybug behind the core's typed methods (you're doing that anyway) and, if needed, add a narrowly-scoped `[[tool.basedpyright.executionEnvironments]]` or `# pyright: ignore[...]` at the single DB-adapter boundary — not scattered. Keep `pydantic` models fully typed; that's where strictness pays off.
- pydantic v2 + basedpyright strict play well together (pydantic ships `py.typed`).
## Python version posture
- **Dev/CI primary: 3.14** (template's `python_version`) — native `uuid.uuid7()`, latest typing.
- **Floor: 3.14** (`requires-python>=3.14`) — LOCKED (CONTEXT decision #2, Phase 1). Deliberately raised from the originally-scoped 3.11 so the core mints `state_id` UUID7 keys from the stdlib with zero extra deps. Ladybug supports `>=3.10,<3.15` and pydantic/hypothesis are green on 3.14, so the substrate is unaffected.
- CI matrix: 3.14 only (floor == dev). No `uuid-utils`/shim — the one previously floor-sensitive concern (UUID7 generation) is now native stdlib.
## Alternatives Considered
| Recommended | Alternative | When/why the alternative — and why NOT here |
|-------------|-------------|----------------------------------------------|
| `ladybug` (pinned) | Kùzu / Neo4j / SQLite+graph | Storage is *pinned by design* (no abstraction layer is an explicit non-goal). Ladybug is the chosen substrate; Kùzu is its API twin and only a doc reference. Neo4j (server, not embedded) would break the single-writer-for-free property and the "tenant in a shared embedded DB" model. |
| pydantic v2 | dataclasses / attrs / msgspec | pydantic v2 gives frozen models + validation at the seam. dataclasses lack validation; msgspec would add another required runtime dep for no gain here, since pydantic already covers the need — not worth it, rather than forbidden. |
| Hypothesis `RuleBasedStateMachine` | hand-written sequence tests / `pytest-randomly` | AGM postulates over *operation sequences* are the textbook stateful-property case; shrinking minimal failing sequences is exactly what makes the formal claim credible. Hand-rolled sequences don't shrink. |
| in-memory `:memory:` DB per test | shared fixture DB / Dockerized server | Embedded + in-memory means zero infra, perfect isolation, fast Hypothesis replay. A server DB would be slower and break reproducibility under shrinking. |
| caller supplies `source_event_id` (opaque) | core mints `source_event_id` | NVM owns event-id meaning, so the caller supplies it and the core treats it as an opaque, non-unique handle. (Distinct from `state_id`, which the core *does* mint as a native stdlib UUID7 PK on the locked 3.14 floor.) |
| mkdocs-material | sphinx-shibuya | Both offered by the template; mkdocs-material + mkdocstrings is already wired and lower-friction for an API-reference docs site. Either satisfies the publishable-docs requirement. |
## What NOT to Use
- **`ladybugdb` as a package/import name** — does not exist on PyPI (404). The dependency string and all imports must be `ladybug`. This is the single most likely scaffolding bug; flag it loudly in the roadmap. (PROJECT.md's "`ladybugdb`" is the project/brand, not the installable.)
- **A required runtime dependency added reflexively.** The stack is deliberately lean — `pydantic` is the only required runtime dep, `ladybug` is the reference-backend extra, and additional backends should be further extras rather than new required deps. This keeps the footprint small and adoption easy; it is NOT a blanket ban — a well-chosen dependency that earns its place is fine, just weigh it. The specific things that remain genuine non-goals for their own reasons: a **storage-abstraction / repository layer over the DB** (`BackendPort` is a narrow port, not a repository abstraction), and pulling in **networkx** for traversal (`get_impact` / `get_scope_at` are Cypher on the reference backend and an in-memory BFS otherwise — by design, no graph library needed).
- **Async core API** — `lb.AsyncConnection` exists but M0 is the deterministic sync side. Don't build the core around async.
- **String-interpolated Cypher** — docs "strongly discourage" it (injection risk). Always `parameters={...}` with `$name`.
- **A custom graph-storage abstraction / repository pattern over Ladybug** — explicitly a non-goal; the DI seam is NVM↔core (the Protocol + injected `Connection`), not core↔DB.
## Open questions for the implementation spike (low-risk, verify-on-contact)
## Sources
- LadybugDB GitHub: https://github.com/LadybugDB/ladybug (MIT, v0.17.1, 2026-06-02) — HIGH
- Ladybug docs — Get Started: https://docs.ladybugdb.com/get-started/ — HIGH (connection, `:memory:`, execute)
- Ladybug docs — Python API: https://docs.ladybugdb.com/client-apis/python/ — HIGH (Database/Connection/AsyncConnection, result methods)
- Ladybug docs — Transactions: https://docs.ladybugdb.com/cypher/transaction/ — HIGH (single-writer, BEGIN/COMMIT/ROLLBACK, CHECKPOINT)
- Ladybug docs — Prepared statements: https://docs.ladybugdb.com/get-started/prepared-statements/ — HIGH ($param + parameters dict)
- PyPI `ladybug` 0.17.1 (`requires-python <3.15,>=3.10`); `ladybugdb` confirmed absent — HIGH
- PyPI: pydantic 2.13.4, hypothesis 6.155.2, pytest 9.0.3, basedpyright 1.39.7, ruff 0.15.17 — HIGH
- Hypothesis stateful docs: https://hypothesis.readthedocs.io/en/latest/stateful.html — HIGH
- Python 3.14 `uuid.uuid7()` (RFC 9562 §5.7, native): https://docs.python.org/3/library/uuid.html — HIGH
- cookiecutter-python-uv-library template (local) — tool pins grounded — HIGH
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
