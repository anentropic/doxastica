# Stack Research — doxastica

**Domain:** Graph-native AGM belief-revision memory-core Python library (standalone Kumiho implementation)
**Researched:** 2026-06-13
**Confidence:** HIGH (all runtime/storage facts verified against live PyPI + official docs; one important name correction below)

---

## TL;DR for the roadmap

1. **The storage dependency is published on PyPI as `ladybug`, NOT `ladybugdb`.** Import name is `ladybug` (`import ladybug as lb`). `ladybugdb` does not exist on PyPI (verified — 404). `ladybugdb.com` / `github.com/LadybugDB/ladybug` is the project/org; the *package* is `ladybug`. **Pin `ladybug>=0.17,<0.18` and `import ladybug as lb`.** Do not let "ladybugdb" leak into `pyproject.toml` dependencies or import statements — it will fail to resolve.
2. **Runtime deps: `ladybug` + `pydantic` only**, exactly as the constraint demands. One caveat: UUID7 generation needs a decision (native on 3.14, not on the 3.11 floor — see below).
3. Ladybug is a Kùzu-lineage embedded graph DB (identical Python surface: `Database`/`Connection`/`execute`, `:memory:`, `CREATE NODE TABLE ... PRIMARY KEY`, single-writer WAL, `$param` prepared statements). Everything you know about Kùzu's Python API transfers. This is great for the flexible-connection design — see code sketches below.
4. The cookiecutter tool pins are current and appropriate. Pytest in the template is `>=8.0.0`; current is 9.0.3 — both fine, no action needed.

---

## Recommended Stack

### Core / Runtime Dependencies

| Technology | Version pin | Purpose | Why |
|------------|-------------|---------|-----|
| **ladybug** | `>=0.17,<0.18` | Embedded graph DB + Cypher; the pinned storage substrate | The project deliberately pins storage to LadybugDB/Cypher (no abstraction layer). Embedded single-writer model *enforces* write serialization for free (a stated design payoff). Verified PyPI name `ladybug` 0.17.1, `requires-python <3.15,>=3.10` — covers the whole 3.11–3.14 band. |
| **pydantic** | `>=2.11,<3` | Typed value/model layer at the API boundary (`Scope`, `BeliefState`, `EdgeType`) | v2 is the current line (2.13.4). Rust core, fast validation, frozen models for immutable `BeliefState`. `requires-python >=3.9` — no floor problem. |

**That is the entire runtime dependency set the constraint allows.** Resist adding more (see "What NOT to use").

### The UUID7 decision (the one genuine runtime gap)

The Protocol stores **UUID7 event ids** (`source_event_id: UUID`). The core *stores/orders* them but, for tests and standalone use, you need to *generate* them.

- **Python 3.14** ships `uuid.uuid7()` natively (new in 3.14, RFC 9562 §5.7, monotonic — verified). On the 3.14 dev interpreter, **no dependency needed**.
- **Python 3.11–3.13** (the supported floor, `requires-python>=3.11`) has **no** `uuid.uuid7()`.

Three options, in order of preference:

1. **Generation is the caller's job, not the core's.** Every Protocol write method *takes* `source_event_id: UUID` as a parameter — the core never mints one in production (NVM owns event ids). So the core has **zero** UUID7 generation dependency. Only the *test suite* needs to generate them. → Put the generator in the **dev group**, not runtime deps. **Recommended.**
2. For tests on 3.11–3.13, add `uuid-utils>=0.16` (Rust, fast, `requires-python>=3.10`, has `uuid7()`) to the **dev dependency group only**. On 3.14 you can prefer stdlib via a 2-line shim.
3. (Reject) Adding a UUID7 lib to *runtime* deps — violates the "ladybug + pydantic only" constraint for no benefit, since the core doesn't mint ids.

> Roadmap note: keep `source_event_id` strictly an input. This keeps the runtime dep set at exactly two and sidesteps the 3.11 stdlib gap entirely.

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

**Action for scaffolding:** add `hypothesis>=6.155` to `[dependency-groups].dev`. Everything else the template provides is current.

---

## Installation

```bash
# Runtime (the ONLY two runtime deps)
uv add "ladybug>=0.17,<0.18" "pydantic>=2.11,<3"

# Dev / test tooling (hypothesis is the addition over the template defaults)
uv add --dev "hypothesis>=6.155"
# pytest, pytest-cov, basedpyright, ruff, ipython, pdbpp come from the template

# (Optional, dev-only) UUID7 generation for the 3.11–3.13 test matrix:
uv add --dev "uuid-utils>=0.16"
```

`pyproject.toml` deltas from the cookiecutter template:

```toml
[project]
dependencies = [
    "ladybug>=0.17,<0.18",
    "pydantic>=2.11,<3",
]

[dependency-groups]
dev = [
    # ...template defaults (basedpyright, ruff, pytest, pytest-cov, ipython, pdbpp)...
    "hypothesis>=6.155",
    "uuid-utils>=0.16",  # only if you target the 3.11–3.13 floor for UUID7 generation in tests
]
```

---

## Ladybug — the high-value detail (verified against docs.ladybugdb.com)

**Lineage:** Ladybug is API-identical to **Kùzu** (same `Database`/`Connection`/`execute` surface, `:memory:` databases, columnar storage, `CREATE NODE TABLE ... PRIMARY KEY`, `COPY`, WAL + checkpoint, single-writer concurrency, `$`-parameterized prepared statements). Treat Kùzu docs/experience as a reliable secondary reference where Ladybug's own docs are thin. **Confidence HIGH** on the surface below — all of it is quoted from the official docs.

### Connection API (verified)

```python
import ladybug as lb

# On-disk
db = lb.Database("example.lbug")
conn = lb.Connection(db)

# In-memory (use ":memory:" OR "")
db = lb.Database(":memory:")
conn = lb.Connection(db)

# Parameterized Cypher (REQUIRED style — string interpolation "strongly discouraged")
res = conn.execute(
    "MATCH (b:Belief) WHERE b.belief_id = $bid RETURN b.*",
    parameters={"bid": belief_id},
)
for row in res:        # iterable
    ...
# Also: res.get_all() -> list[tuple]; res.has_next()/res.get_next();
#       res.get_as_df() (Pandas) / get_as_pl() (Polars) / get_as_arrow()
```

### Transaction / concurrency model (verified)

- **One write transaction at a time; many concurrent reads.** WAL-backed, serializable. The embedded single-writer rule is exactly the property the design wants — write serialization "for free."
- **Auto-commit:** a bare statement is auto-wrapped in a serializable transaction.
- **Manual transactions** via Cypher statements: `BEGIN TRANSACTION;` / `BEGIN TRANSACTION READ ONLY;` / `COMMIT;` / `ROLLBACK;` — issued through `conn.execute(...)`. Useful for grouping a multi-statement `revise()` (deprecate old `CURRENT_STATE`, append new `BeliefState`, repoint pointer) atomically.
- `CHECKPOINT;` merges WAL → data files (also automatic).

### Async (verified)

```python
conn = lb.AsyncConnection(db, max_concurrent_queries=4)
```

An async connection type exists. **The core API should stay synchronous** (the design's "sync side of the clock"; M0 is LLM-free and deterministic). Note async exists for future NVM-side use, but do **not** build the core around it.

### Schema / DDL note (Kùzu-lineage, MEDIUM confidence — verify in spike)

Ladybug is a **schema-ful** property graph: node/rel tables are declared with `CREATE NODE TABLE ... (id ... PRIMARY KEY)` / `CREATE REL TABLE ...` before inserting. This matters for the label-tenancy design (R19): the core owns `:Scope` / `:Belief` / `:BeliefState` *tables* and its rel tables. On a self-managed/throwaway DB the core must run idempotent `CREATE NODE TABLE IF NOT EXISTS ...` DDL on first connect. On an injected connection it must do the same defensively (the tables may or may not already exist). Confirm `IF NOT EXISTS` support and the exact rel-table syntax in the first implementation spike — these are the only Ladybug specifics not fully pinned from the docs pages fetched.

### Namespace / label-prefix support (design implication)

Ladybug/Kùzu has no built-in schema-namespacing primitive. The design's `namespace_prefix` is therefore **a doxastica convention layered on table/label names** (e.g. prefix node-table names or carry a `namespace` property + index), not a DB feature. Roadmap should treat "namespace prefixing" as core-implemented string discipline, and the property-graph DDL is where it lands.

---

## The flexible-connection model (the core design seam) — concrete sketch

The design needs **both** injected and self-managed connections. With Ladybug's `Database`/`Connection` split this is clean: the core operates on a **`Connection`**, and only *optionally* owns the `Database`.

```python
from __future__ import annotations
import ladybug as lb

class MemoryCore:
    def __init__(self, connection: lb.Connection, *, namespace_prefix: str = "") -> None:
        """INJECTED mode (NVM's primary need / R19 tenancy).

        The core never opened this connection and must never close it or the
        underlying Database. It runs idempotent CREATE ... IF NOT EXISTS DDL
        for its owned label families, scoped by namespace_prefix.
        """
        self._conn = connection
        self._ns = namespace_prefix
        self._owns_db = False
        self._db: lb.Database | None = None
        self._ensure_schema()

    @classmethod
    def open(cls, path: str = ":memory:", *, namespace_prefix: str = "") -> "MemoryCore":
        """SELF-MANAGED mode (standalone / tests).

        The core opens and OWNS the Database + Connection and is responsible
        for closing them (context manager / close()).
        """
        db = lb.Database(path)
        conn = lb.Connection(db)
        self = cls(conn, namespace_prefix=namespace_prefix)
        self._owns_db = True
        self._db = db
        return self

    def close(self) -> None:
        if self._owns_db:
            # close the connection/db the core opened; no-op in injected mode
            ...

    def __enter__(self) -> "MemoryCore": return self
    def __exit__(self, *exc: object) -> None: self.close()
```

Key correctness rules this encodes:
- **Ownership is explicit (`_owns_db`).** Injected mode must never close someone else's handle (R19: the core is a *tenant*).
- **Schema bootstrap runs in both modes**, idempotently (`IF NOT EXISTS`), because an injected connection's DB may be fresh or shared.
- The DI seam stays NVM↔core (a `Connection` object), never core↔storage-abstraction — matching the "no storage abstraction" non-goal.

---

## Testing stack — throwaway DBs + Hypothesis stateful (verified)

### Throwaway databases

Use **in-memory Ladybug per test** — fastest, zero filesystem, perfectly private:

```python
import ladybug as lb
import pytest
from doxastica import MemoryCore

@pytest.fixture
def core() -> MemoryCore:
    # ":memory:" (or "") => private throwaway DB, torn down with the process/fixture
    return MemoryCore.open(":memory:")
```

If a test needs persistence/restart semantics (e.g. checkpoint/WAL behaviour, `get_scope_at` across reopen), use `tmp_path`:

```python
@pytest.fixture
def disk_core(tmp_path) -> MemoryCore:
    return MemoryCore.open(str(tmp_path / "test.lbug"))
```

Inject-mode tests construct `lb.Connection(lb.Database(":memory:"))` themselves and pass it in, exercising the tenancy path.

### Hypothesis stateful testing for AGM postulates (verified API, 6.155.2)

The AGM property suite generates **operation sequences** and asserts postulates hold. `RuleBasedStateMachine` is exactly the tool. Concrete sketch:

```python
import string
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine, rule, initialize, invariant, precondition, Bundle,
)
from doxastica import MemoryCore

scope_ids  = st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=6)
belief_ids = st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=6)
values     = st.text(max_size=20)   # opaque to the core

class BeliefStoreMachine(RuleBasedStateMachine):
    scopes = Bundle("scopes")

    @initialize()
    def setup(self) -> None:
        self.core = MemoryCore.open(":memory:")   # fresh throwaway DB per run
        self.model: dict[tuple[str, str], str] = {}  # oracle / shadow model

    @rule(target=scopes, sid=scope_ids)
    def make_scope(self, sid: str) -> str:
        self.core.get_or_create_scope(sid)
        return sid

    @rule(scope=scopes, bid=belief_ids, value=values)
    def revise(self, scope: str, bid: str, value: str) -> None:
        eid = _new_event_id()                      # UUID7, monotonic
        self.core.revise(scope, bid, value, eid)
        self.model[(scope, bid)] = value          # AGM 'success': new belief is in

    @rule(scope=scopes, bid=belief_ids, value=values)
    def expand(self, scope: str, bid: str, value: str) -> None:
        ...

    @precondition(lambda self: bool(self.model))
    @rule(scope=scopes, bid=belief_ids)
    def contract(self, scope: str, bid: str) -> None:
        # world-scope contract() must raise — assert that as a separate property
        ...

    @invariant()
    def current_state_unique(self) -> None:
        # structural invariant: exactly one CURRENT_STATE per (scope, belief)
        ...

    @invariant()
    def success_postulate(self) -> None:
        # AGM success: after revise(p), p is believed (== current value)
        for (scope, bid), v in self.model.items():
            assert self.core.current_value(scope, bid) == v

# Pytest entrypoint:
TestBeliefStore = BeliefStoreMachine.TestCase
```

Patterns to use (all current in 6.155):
- **`Bundle`** to track created scopes/beliefs so later rules draw real ids (not random misses).
- **`@initialize`** to spin up the throwaway in-memory DB exactly once per example run.
- **`@invariant`** for structural invariants checked after *every* step (`CURRENT_STATE` uniqueness, chain immutability).
- **`@precondition`** to gate `contract` on existing beliefs and to route world-scope-contract-is-an-error into its own assertion.
- **Shadow/oracle model** (the `self.model` dict) is the standard way to assert AGM postulates (success, inclusion, vacuity, consistency, extensionality) — compare the real store against the simple in-memory oracle.
- Drive it via `BeliefStoreMachine.TestCase` (pytest auto-collects) or `run_state_machine_as_test(BeliefStoreMachine)` for manual settings.
- Pair the stateful machine with ordinary `@given` property tests for single-operation postulates (extensionality, vacuity) where a full sequence is overkill.

> Note on Hypothesis + a real embedded DB: the in-memory Ladybug DB is cheap enough to recreate per example, which is the clean approach (full isolation, no shrinking-corrupts-state hazards). Avoid sharing one DB across examples; Hypothesis replays/shrinks aggressively and a shared mutable DB breaks reproducibility.

---

## basedpyright / strict-typing notes for this library

- Template sets `typeCheckingMode = "strict"`, `pythonVersion = "3.14"`, `include = ["src","tests"]`. Good.
- **Ladybug ships types?** Unverified — likely partial. If `lb.Connection` / `lb.execute` return `Any`/untyped, strict mode will flag `reportUnknownMemberType` etc. Plan to wrap Ladybug behind the core's typed methods (you're doing that anyway) and, if needed, add a narrowly-scoped `[[tool.basedpyright.executionEnvironments]]` or `# pyright: ignore[...]` at the single DB-adapter boundary — not scattered. Keep `pydantic` models fully typed; that's where strictness pays off.
- pydantic v2 + basedpyright strict play well together (pydantic ships `py.typed`).

---

## Python version posture

- **Dev/CI primary: 3.14** (template's `python_version`) — gets native `uuid.uuid7()`, latest typing.
- **Floor: 3.11** (`requires-python>=3.11`). Ladybug supports `>=3.10,<3.15`; pydantic `>=3.9`; hypothesis `>=3.10` — **all green across 3.11–3.14**. No dependency forces raising the floor.
- CI matrix recommendation: test 3.11 and 3.14 at minimum (floor + dev). The only floor-sensitive code is UUID7 *generation in tests* — handled by the dev-group `uuid-utils` shim.

---

## Alternatives Considered

| Recommended | Alternative | When/why the alternative — and why NOT here |
|-------------|-------------|----------------------------------------------|
| `ladybug` (pinned) | Kùzu / Neo4j / SQLite+graph | Storage is *pinned by design* (no abstraction layer is an explicit non-goal). Ladybug is the chosen substrate; Kùzu is its API twin and only a doc reference. Neo4j (server, not embedded) would break the single-writer-for-free property and the "tenant in a shared embedded DB" model. |
| pydantic v2 | dataclasses / attrs / msgspec | Constraint says pydantic. v2 gives frozen models + validation at the seam. dataclasses lack validation; msgspec would be a third runtime dep (forbidden). |
| Hypothesis `RuleBasedStateMachine` | hand-written sequence tests / `pytest-randomly` | AGM postulates over *operation sequences* are the textbook stateful-property case; shrinking minimal failing sequences is exactly what makes the formal claim credible. Hand-rolled sequences don't shrink. |
| in-memory `:memory:` DB per test | shared fixture DB / Dockerized server | Embedded + in-memory means zero infra, perfect isolation, fast Hypothesis replay. A server DB would be slower and break reproducibility under shrinking. |
| caller supplies `source_event_id` | core mints UUID7 | Keeps runtime deps at exactly two and dodges the 3.11 stdlib `uuid7` gap; matches the design (NVM owns event-id meaning). |
| mkdocs-material | sphinx-shibuya | Both offered by the template; mkdocs-material + mkdocstrings is already wired and lower-friction for an API-reference docs site. Either satisfies the publishable-docs requirement. |

---

## What NOT to Use

- **`ladybugdb` as a package/import name** — does not exist on PyPI (404). The dependency string and all imports must be `ladybug`. This is the single most likely scaffolding bug; flag it loudly in the roadmap. (PROJECT.md's "`ladybugdb`" is the project/brand, not the installable.)
- **Any third runtime dependency** (orjson, msgspec, networkx, a UUID lib at runtime, an ORM/graph-OGM, a storage-abstraction layer). The constraint is `ladybug` + `pydantic` only, and the "no storage abstraction over the DB" non-goal is explicit. Graph traversal (`get_impact`, `get_scope_at`) is **Cypher**, not networkx.
- **Async core API** — `lb.AsyncConnection` exists but M0 is the deterministic sync side. Don't build the core around async.
- **String-interpolated Cypher** — docs "strongly discourage" it (injection risk). Always `parameters={...}` with `$name`.
- **A custom graph-storage abstraction / repository pattern over Ladybug** — explicitly a non-goal; the DI seam is NVM↔core (the Protocol + injected `Connection`), not core↔DB.

---

## Open questions for the implementation spike (low-risk, verify-on-contact)

1. Exact `CREATE REL TABLE` syntax and `IF NOT EXISTS` support in Ladybug 0.17 (Kùzu-shaped, but confirm). Affects the schema-bootstrap method.
2. Does `ladybug` ship `py.typed` / type stubs? Determines how much basedpyright-strict suppression is needed at the DB-adapter boundary.
3. `lb.Connection` close/lifecycle methods (explicit `.close()`? context manager?) for the self-managed mode's `close()`.
4. Whether `namespace_prefix` is best realized as table-name prefixing vs. a `namespace` node property + secondary index (perf vs. simplicity) — a core-level convention either way, no DB feature exists.

---

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
