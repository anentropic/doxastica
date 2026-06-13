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

- **Tech stack**: Python (uv) — runtime deps **`ladybug` (the LadybugDB PyPI package, a
  Kùzu fork, import `ladybug as lb`) + `pydantic` v2 only**, zero NVM imports. Why: the
  repo boundary keeps the implementation faithful to the paper's domain-agnostic model and
  LadybugDB's single-writer/multi-reader embedded model enforces write serialization for free.
- **Tooling**: `cookiecutter-python-uv-library` template — basedpyright strict typing,
  ruff lint/format, pytest + coverage, pre-commit, git-cliff changelog, GitHub Actions.
- **Storage**: pinned to LadybugDB / Cypher (PyPI package **`ladybug`**, a Kùzu fork —
  https://github.com/LadybugDB/ladybug). API: `lb.Database(path | ":memory:")` →
  `lb.Connection(db)` → `conn.execute(cypher, parameters=...)`; schema-first (CREATE
  NODE/REL TABLE), uniqueness only via PRIMARY KEY. **Flexible connection**: `MemoryCore`
  accepts an injected `Connection` + namespace prefix (NVM leases it under label tenancy;
  the core never closes it) *and* can open/manage its own (`:memory:` or file) for
  standalone use. The DI seam stays NVM↔core, not core↔database (no storage abstraction).
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
### The UUID7 decision (the one genuine runtime gap)
- **Python 3.14** ships `uuid.uuid7()` natively (new in 3.14, RFC 9562 §5.7, monotonic — verified). On the 3.14 dev interpreter, **no dependency needed**.
- **Python 3.11–3.13** (the supported floor, `requires-python>=3.11`) has **no** `uuid.uuid7()`.
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
# Runtime (the ONLY two runtime deps)
# Dev / test tooling (hypothesis is the addition over the template defaults)
# pytest, pytest-cov, basedpyright, ruff, ipython, pdbpp come from the template
# (Optional, dev-only) UUID7 generation for the 3.11–3.13 test matrix:
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
- **Dev/CI primary: 3.14** (template's `python_version`) — gets native `uuid.uuid7()`, latest typing.
- **Floor: 3.11** (`requires-python>=3.11`). Ladybug supports `>=3.10,<3.15`; pydantic `>=3.9`; hypothesis `>=3.10` — **all green across 3.11–3.14**. No dependency forces raising the floor.
- CI matrix recommendation: test 3.11 and 3.14 at minimum (floor + dev). The only floor-sensitive code is UUID7 *generation in tests* — handled by the dev-group `uuid-utils` shim.
## Alternatives Considered
| Recommended | Alternative | When/why the alternative — and why NOT here |
|-------------|-------------|----------------------------------------------|
| `ladybug` (pinned) | Kùzu / Neo4j / SQLite+graph | Storage is *pinned by design* (no abstraction layer is an explicit non-goal). Ladybug is the chosen substrate; Kùzu is its API twin and only a doc reference. Neo4j (server, not embedded) would break the single-writer-for-free property and the "tenant in a shared embedded DB" model. |
| pydantic v2 | dataclasses / attrs / msgspec | Constraint says pydantic. v2 gives frozen models + validation at the seam. dataclasses lack validation; msgspec would be a third runtime dep (forbidden). |
| Hypothesis `RuleBasedStateMachine` | hand-written sequence tests / `pytest-randomly` | AGM postulates over *operation sequences* are the textbook stateful-property case; shrinking minimal failing sequences is exactly what makes the formal claim credible. Hand-rolled sequences don't shrink. |
| in-memory `:memory:` DB per test | shared fixture DB / Dockerized server | Embedded + in-memory means zero infra, perfect isolation, fast Hypothesis replay. A server DB would be slower and break reproducibility under shrinking. |
| caller supplies `source_event_id` | core mints UUID7 | Keeps runtime deps at exactly two and dodges the 3.11 stdlib `uuid7` gap; matches the design (NVM owns event-id meaning). |
| mkdocs-material | sphinx-shibuya | Both offered by the template; mkdocs-material + mkdocstrings is already wired and lower-friction for an API-reference docs site. Either satisfies the publishable-docs requirement. |
## What NOT to Use
- **`ladybugdb` as a package/import name** — does not exist on PyPI (404). The dependency string and all imports must be `ladybug`. This is the single most likely scaffolding bug; flag it loudly in the roadmap. (PROJECT.md's "`ladybugdb`" is the project/brand, not the installable.)
- **Any third runtime dependency** (orjson, msgspec, networkx, a UUID lib at runtime, an ORM/graph-OGM, a storage-abstraction layer). The constraint is `ladybug` + `pydantic` only, and the "no storage abstraction over the DB" non-goal is explicit. Graph traversal (`get_impact`, `get_scope_at`) is **Cypher**, not networkx.
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
- PyPI: pydantic 2.13.4, hypothesis 6.155.2, pytest 9.0.3, basedpyright 1.39.7, ruff 0.15.17, uuid-utils 0.16.0 — HIGH
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
