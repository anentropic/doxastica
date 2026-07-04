# Architecture Research

**Domain:** Graph-native AGM belief-revision library (standalone Kumiho impl, arXiv 2603.17244)
**Researched:** 2026-06-13
**Confidence:** HIGH (LadybugDB API verified as a Kùzu fork with kuzu-compatible Python API; Cypher idioms verified against Kùzu docs; schema model and concurrency confirmed)

> **The one fact that shapes everything below:** LadybugDB is a **community fork of Kùzu**
> ([gdotv](https://gdotv.com/blog/kuzu-legacy-embedded-graph-database-landscape/), [dbdb.io](https://dbdb.io/db/ladybugdb)),
> whose Python API is "intentionally compatible with kuzu's at the surface." That means three
> things the design must respect, none of which a Neo4j mental model would predict:
> 1. **Schema-first.** You must `CREATE NODE TABLE` / `CREATE REL TABLE` before inserting. No
>    ad-hoc labels. ([Kùzu DDL](https://kuzudb.github.io/docs/cypher/data-definition/create-table/))
> 2. **Uniqueness only via PRIMARY KEY.** There is no `CREATE CONSTRAINT ... IS UNIQUE`. The
>    `CURRENT_STATE`-uniqueness invariant must be *modelled structurally*, not declared.
> 3. **One `READ_WRITE` Database object per file; many Connections share it.**
>    ([Kùzu concurrency](https://kuzudb.github.io/docs/concurrency/)) — this is exactly what makes the
>    injected-connection model correct, and it hands us write-serialization for free.

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  CONSUMER (NVM, or standalone user)                                    │
│      depends on the Protocol type, never the concrete class            │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │  doxastica.BeliefStore (Protocol)
                                 │  + pydantic boundary models
┌────────────────────────────────▼─────────────────────────────────────┐
│  doxastica  (the library — ladybugdb + pydantic only)                  │
│                                                                        │
│  ┌──────────────┐   ┌──────────────────┐   ┌───────────────────────┐ │
│  │  protocol.py │   │   models.py      │   │   ids.py              │ │
│  │  BeliefStore │   │ Scope            │   │  new_event_id()       │ │
│  │  (Protocol)  │   │ BeliefState      │   │  (UUID7)              │ │
│  │  EdgeType    │   │ EdgeType (enum)  │   │                       │ │
│  └──────┬───────┘   └────────┬─────────┘   └───────────┬───────────┘ │
│         │                    │                         │             │
│  ┌──────▼────────────────────▼─────────────────────────▼──────────┐  │
│  │  core.py — MemoryCore (the ONE concrete impl)                   │  │
│  │    revise/expand/contract/add_edge/query_scope/get_impact/...   │  │
│  │    holds: a Connection + a namespace prefix                     │  │
│  └──────┬───────────────────────────────┬─────────────────────────┘  │
│         │  parameterised Cypher          │  schema bootstrap          │
│  ┌──────▼────────────┐         ┌─────────▼────────────────────────┐   │
│  │  queries.py        │         │  connection.py                   │   │
│  │  templated Cypher  │         │  ConnectionProvider:             │   │
│  │  (namespace-aware) │         │   - InjectedConnection           │   │
│  │                    │         │   - ManagedConnection (own file) │   │
│  └──────┬─────────────┘         └─────────┬────────────────────────┘   │
│         │                                 │                            │
│  ┌──────▼────────────┐                    │ schema.py — DDL (CREATE    │
│  │  rows → models     │                    │  NODE/REL TABLE, idempotent│
│  │  (parsing/mapping) │                    │  per-namespace bootstrap)  │
│  └────────────────────┘                    └────────────────────────── │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │  ladybug.Connection / Database
┌────────────────────────────────▼─────────────────────────────────────┐
│  LadybugDB  (embedded, single .lbug file, columnar, Cypher, Kùzu fork) │
│   label families owned by the core: <ns>_Scope / <ns>_Belief /         │
│   <ns>_BeliefState  +  <ns>_CURRENT_STATE / HAS_REVISION / SUPERSEDES / │
│   DEPENDS_ON / DERIVED_FROM                                            │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `protocol.py` | The `BeliefStore` Protocol + `EdgeType` enum — the seam. Imports `pydantic`/`typing` only; **does not import `ladybugdb`** | `typing.Protocol`, `runtime_checkable` optional |
| `models.py` | `Scope`, `BeliefState` pydantic models at the boundary. Frozen (immutable) for `BeliefState` | `pydantic.BaseModel(frozen=True)` |
| `ids.py` | UUID7 generation + (optional) timestamp extraction for ordering | wraps `uuid_utils` (or `uuid.uuid7` on 3.14+) |
| `connection.py` | The **connection-provider** abstraction (injected vs. managed). NOT a storage abstraction — just resolves "where does my `Connection` come from and who owns its lifecycle" | small protocol + two impls |
| `schema.py` | Idempotent DDL bootstrap: `CREATE NODE TABLE IF NOT EXISTS <ns>_Scope ...` etc. Runs once per namespace | parameterised DDL strings |
| `queries.py` | Namespace-aware Cypher templates. The only place Cypher text lives | f-string table names + `$param` bind values |
| `core.py` | `MemoryCore` — the concrete `BeliefStore`. Orchestrates schema bootstrap, query execution, row→model mapping, invariant enforcement | the bulk of the library |
| `tests/` | AGM property suite (Hypothesis) + structural-invariant tests + irony-join demo | uses `ManagedConnection` against throwaway in-memory DBs |

---

## Recommended Project Structure

```
doxastica/
├── pyproject.toml              # uv; deps: ladybugdb, pydantic, uuid_utils
├── src/doxastica/
│   ├── __init__.py             # re-exports: BeliefStore, MemoryCore, Scope,
│   │                           #   BeliefState, EdgeType, new_event_id
│   ├── protocol.py             # BeliefStore(Protocol), EdgeType(StrEnum)
│   ├── models.py               # Scope, BeliefState (pydantic, frozen)
│   ├── ids.py                  # new_event_id() -> UUID, event_ts(uuid) ordering helper
│   ├── connection.py           # ConnectionProvider protocol + Injected/Managed impls
│   ├── schema.py               # SCHEMA_DDL templates + bootstrap(conn, ns)
│   ├── queries.py              # Cypher template functions, namespace-parameterised
│   ├── core.py                 # MemoryCore: the concrete BeliefStore
│   ├── errors.py               # WorldScopeContractionError, UnknownScopeError, ...
│   └── py.typed                # ship type info (basedpyright strict)
└── tests/
    ├── conftest.py             # fixtures: throwaway managed in-memory MemoryCore
    ├── strategies.py           # Hypothesis strategies over operation sequences
    ├── test_agm_postulates.py  # success / inclusion / vacuity / consistency / extensionality
    ├── test_invariants.py      # CURRENT_STATE uniqueness, chain immutability, replay≡get_scope_at
    ├── test_operations.py      # unit tests of revise/expand/contract/edges
    ├── test_irony_join.py      # actor-vs-world divergence as one query
    └── test_connection.py      # injected vs managed lifecycle, namespace isolation
```

### Structure Rationale

- **`protocol.py` is dependency-free of `ladybugdb`.** This is the seam's whole point: a
  consumer can type-check against `BeliefStore` without importing the DB. (Mirrors NVM's
  `ports/` rule: ports import only `pydantic`/`typing`.)
- **One concrete impl, named `MemoryCore`.** PROJECT.md and the NVM design both name it
  `MemoryCore(db_connection, namespace_prefix)`. Resist a base-class hierarchy — there is
  exactly one implementation by design (paper-fidelity over speculative reuse).
- **`queries.py` is the single Cypher home.** Two-part parameterisation: table/label names
  come from the namespace prefix via f-strings (they cannot be bind parameters in Cypher);
  *values* are always `$`-bind parameters. Keeping all Cypher in one module makes the
  schema⇄query coupling auditable and the namespace-injection one-pass-greppable.
- **`connection.py` is a connection-provider, explicitly NOT a storage abstraction.** The
  non-goal (PROJECT.md, memory-core §0/§34) is abstracting *Cypher/the DB*. Abstracting
  *connection ownership* is a different, legitimate axis and the only way "injected (NVM)
  AND self-managed (standalone)" both hold.

---

## The LadybugDB Graph Schema

LadybugDB is schema-first, so the core **owns a DDL bootstrap**. All tables are
namespace-prefixed; only the core writes them (R19 tenancy). Below, `<ns>` is the injected
`namespace_prefix` (e.g. `bel`); standalone use defaults it to `dox`.

### Node tables

```cypher
CREATE NODE TABLE IF NOT EXISTS <ns>_Scope (
    scope_id     STRING,
    is_world     BOOLEAN DEFAULT false,
    PRIMARY KEY (scope_id)
);

CREATE NODE TABLE IF NOT EXISTS <ns>_Belief (
    belief_id    STRING,         -- stable identity; one belief per node
    scope_id     STRING,         -- denormalised owner (lets queries filter without a hop)
    PRIMARY KEY (belief_id)
);

CREATE NODE TABLE IF NOT EXISTS <ns>_BeliefState (
    state_id        UUID,        -- == the source_event_id (UUID7), PK and time-order key
    belief_id       STRING,      -- denormalised for fast scope/chain queries
    value           STRING,      -- opaque; JSON-encoded by the core, never interpreted
    status          STRING,      -- 'active' | 'retracted'  (contraction marks, never deletes)
    PRIMARY KEY (state_id)
);
```

Notes that fall out of the Kùzu data model:
- **`belief_id` is per-scope-unique, not globally unique.** The same proposition held by two
  scopes is two `Belief` nodes. The core's public identity is therefore the `(scope_id,
  belief_id)` pair (matching the Protocol signatures). To make `belief_id` a usable PRIMARY
  KEY, the core stores it **namespaced as `f"{scope_id}::{belief_id}"`** internally and
  splits on the way out. (LadybugDB has no composite-PK-with-uniqueness across two columns
  that the API exposes cleanly; a synthesized PK is the idiom.)
- **`state_id == source_event_id`.** The Protocol already passes a UUID7 `source_event_id`
  into `revise/expand`. Using it directly as the `BeliefState` PRIMARY KEY (a) gives free
  uniqueness, (b) makes `get_scope_at(as_of_event_id)` a pure `WHERE state_id <= $as_of`
  comparison on time-ordered UUID7s, and (c) needs no second id. This is the single most
  load-bearing modelling decision. (Confirmed: LadybugDB/Kùzu has a native `UUID` type —
  [Kùzu data types](https://docs.kuzudb.com/cypher/data-types/).)
- **`value STRING` holding JSON** is the recommended opacity encoding. Kùzu's `BLOB` caps at
  4KB and is awkward to inspect; a JSON-serialised `STRING` keeps `value: Any` truly opaque
  while remaining debuggable. The core does `json.dumps`/`json.loads` at the boundary and
  never inspects structure. (`BLOB`/JSON-extension are alternatives — see Alternatives.)
- **`status` not a separate `deprecated` flag.** PROJECT.md wants deprecated-vs-superseded as
  a *structural* distinction. Superseded = "a newer state exists in the `HAS_REVISION` chain"
  (structural, no flag). Deprecated/retracted = `status='retracted'` set by `contract()`.
  `query_scope(include_deprecated=False)` filters `status='active'`.

### Relationship tables

Kùzu rel tables are typed and can declare multiple `FROM..TO` pairs in one table
([verified](https://kuzudb.github.io/docs/cypher/data-definition/create-table/)).

```cypher
-- the ONLY mutable element in the whole schema
CREATE REL TABLE IF NOT EXISTS <ns>_CURRENT_STATE (
    FROM <ns>_Belief TO <ns>_BeliefState
);

-- append-only revision chain
CREATE REL TABLE IF NOT EXISTS <ns>_HAS_REVISION (
    FROM <ns>_Belief TO <ns>_BeliefState
);

-- scope membership
CREATE REL TABLE IF NOT EXISTS <ns>_HOLDS (
    FROM <ns>_Scope TO <ns>_Belief
);

-- generic typed edges between states (NVM layers meaning on these)
CREATE REL TABLE IF NOT EXISTS <ns>_SUPERSEDES   ( FROM <ns>_BeliefState TO <ns>_BeliefState );
CREATE REL TABLE IF NOT EXISTS <ns>_DEPENDS_ON   ( FROM <ns>_BeliefState TO <ns>_BeliefState );
CREATE REL TABLE IF NOT EXISTS <ns>_DERIVED_FROM ( FROM <ns>_BeliefState TO <ns>_BeliefState );
```

A modelling choice to flag for the roadmap: **one rel table per edge type** (above) vs. **one
`<ns>_EDGE` table with a `type STRING` property**. Recommend **one table per type** — Kùzu
traversal can name the rel table directly (`-[:<ns>_DEPENDS_ON*1..5]->`), which is exactly
what `get_impact` needs and is faster than a property filter on a columnar store. The
`EdgeType` enum maps 1:1 to table names. (`SUPERSEDES` is auto-created by `revise`, not via
`add_edge`; `add_edge` writes the three dependency/derivation types.)

### Namespace / tenancy strategy

- **Prefix every table name**, not just node properties. `<ns>_Scope`, `<ns>_BeliefState`,
  `<ns>_DEPENDS_ON`. Because LadybugDB is schema-first and tables are global to the file, the
  prefix is what isolates the core's label families inside a shared DB (R19). NVM's other
  tenants (`Entity`, topology, spine, cache) live in *their own* tables and never collide.
- **Only the core issues DDL/DML against `<ns>_*` tables.** Everyone else reads. Inbound edges
  from external tables to `<ns>_BeliefState` are safe because contraction marks (`status`),
  never deletes — no dangling edges (memory-core §9a).
- **Default `<ns>` for standalone use** (e.g. `dox`); NVM injects its own.

---

## Concrete Cypher Sketches (the hard operations)

All use parameterised values (`$x`); table names are f-string-substituted from `<ns>`.

### `revise` — append a state, re-point CURRENT_STATE, link supersession

`revise` is the AGM heavy hitter: create the new immutable state, find the old current state
(if any), move the single mutable pointer, record the supersession, append to the chain.
Kùzu has no native upsert across this many steps, so the core does it as ordered statements
inside one manual transaction (`BEGIN TRANSACTION` / `COMMIT` —
[verified](https://kuzudb.github.io/docs/cypher/transaction/)).

```cypher
-- (precondition: scope + belief exist; ensured by get_or_create + a MERGE-style upsert)
-- 1. capture the outgoing current state id (may be null on first revise)
MATCH (b:<ns>_Belief {belief_id: $bkey})-[c:<ns>_CURRENT_STATE]->(old:<ns>_BeliefState)
RETURN old.state_id AS old_id;

-- 2. create the new immutable state and chain it
MATCH (b:<ns>_Belief {belief_id: $bkey})
CREATE (s:<ns>_BeliefState {state_id: $event_id, belief_id: $bkey,
                            value: $value_json, status: 'active'})
CREATE (b)-[:<ns>_HAS_REVISION]->(s);

-- 3. supersession edge (only if there was an old current state)
MATCH (s:<ns>_BeliefState {state_id: $event_id}),
      (old:<ns>_BeliefState {state_id: $old_id})
CREATE (s)-[:<ns>_SUPERSEDES]->(old);

-- 4. move the single mutable pointer: delete old CURRENT_STATE rel, create new
MATCH (b:<ns>_Belief {belief_id: $bkey})-[c:<ns>_CURRENT_STATE]->(:<ns>_BeliefState)
DELETE c;
MATCH (b:<ns>_Belief {belief_id: $bkey}), (s:<ns>_BeliefState {state_id: $event_id})
CREATE (b)-[:<ns>_CURRENT_STATE]->(s);
```

`expand` is the same minus step 3's semantics if you treat expansion as "first assertion"; in
this opaque core `expand` ≡ `revise` when no current state exists, and the AGM distinction
(expand never checks consistency) is a *caller* concern. Keep them as separate methods on the
Protocol but let `expand` skip the supersede edge when `old_id` is null.

### `contract` + cascade discovery via `get_impact`

`contract` marks the current state retracted and drops the `CURRENT_STATE` pointer (append-only:
the state node and chain survive). **World-scope contraction raises** before any write.

```cypher
-- guard (in Python): if scope.is_world -> raise WorldScopeContractionError

-- mark retracted (a NEW state, per recovery-rejection invariant) + unhook current pointer
MATCH (b:<ns>_Belief {belief_id: $bkey})-[c:<ns>_CURRENT_STATE]->(old:<ns>_BeliefState)
CREATE (r:<ns>_BeliefState {state_id: $event_id, belief_id: $bkey,
                            value: old.value, status: 'retracted'})
CREATE (b)-[:<ns>_HAS_REVISION]->(r)
CREATE (r)-[:<ns>_SUPERSEDES]->(old)
DELETE c;
-- (no new CURRENT_STATE rel: a contracted belief has no active current state)
```

`get_impact` is the cascade *mechanism* (bounded traversal; policy is the caller's). Kùzu
supports variable-length rel patterns with bounds:

```cypher
MATCH (start:<ns>_BeliefState {state_id: $state_id})
MATCH (start)<-[:<ns>_DEPENDS_ON|<ns>_DERIVED_FROM*1..$depth]-(dependent:<ns>_BeliefState)
RETURN DISTINCT dependent.state_id, dependent.belief_id, dependent.value, dependent.status;
```

Direction note: dependents are the states that point *at* the contracted one via
`DEPENDS_ON`/`DERIVED_FROM`, hence the incoming arrow. (If LadybugDB's parser rejects a bind
param in the bound `*1..$depth`, inline the integer after validating it is a small int — a
known Kùzu idiom.)

### `get_scope_at` — structural time-travel

Because `state_id` is a time-ordered UUID7 *and* the supersede chain is immutable, "what did
this scope hold as of event E" is "for each belief, the latest non-retracted state whose
`state_id <= E`." No replay engine needed.

```cypher
MATCH (sc:<ns>_Scope {scope_id: $scope_id})-[:<ns>_HOLDS]->(b:<ns>_Belief)
MATCH (b)-[:<ns>_HAS_REVISION]->(s:<ns>_BeliefState)
WHERE s.state_id <= $as_of_event_id
WITH b, s ORDER BY s.state_id DESC
WITH b, collect(s)[0] AS state_at        -- newest state at-or-before the cutoff
WHERE state_at.status = 'active'
RETURN b.belief_id, state_at.state_id, state_at.value;
```

This is *the* invariant the test suite checks: `get_scope_at(scope, latest)` must equal the
current live `query_scope(scope)`, and stepping `as_of` through the event ids must reconstruct
the same sequence a fold over operations would. (UUID7 monotonic ordering makes `<=` on the
PK a valid temporal cut — [RFC 9562 UUIDv7](https://discuss.python.org/t/add-uuid7-in-uuid-module-in-standard-library/44390).)

### Irony join — actor scope vs. world scope divergence, one query

```cypher
MATCH (a:<ns>_Scope {scope_id: $actor_id})-[:<ns>_HOLDS]->(ba:<ns>_Belief)
      -[:<ns>_CURRENT_STATE]->(sa:<ns>_BeliefState),
      (w:<ns>_Scope {scope_id: $world_id})-[:<ns>_HOLDS]->(bw:<ns>_Belief)
      -[:<ns>_CURRENT_STATE]->(sw:<ns>_BeliefState)
WHERE ba.belief_id_logical = bw.belief_id_logical   -- same proposition, different holders
  AND sa.value <> sw.value                           -- and they disagree
RETURN ba.belief_id_logical, sa.value AS actor_believes, sw.value AS world_truth;
```

(`belief_id_logical` is the un-prefixed belief id stored as a property alongside the
synthesized PK, so the join is on the proposition, not the scope-qualified key.) This is the
M0-gate demonstration: dramatic irony is *computed*, not remembered.

### `CURRENT_STATE` uniqueness — enforced structurally, not declared

LadybugDB has **no `CREATE CONSTRAINT ... IS UNIQUE`** (only PRIMARY KEY). So "exactly one
`CURRENT_STATE` per belief" is enforced by *construction + verification*, not declaration:

1. **By construction:** `revise`/`contract` always `DELETE` the existing `CURRENT_STATE` rel
   before `CREATE`-ing a new one, inside one transaction. The single-writer model
   ([one READ_WRITE Database](https://kuzudb.github.io/docs/concurrency/)) means no interleaving can violate it.
2. **By verification (test):** an invariant query that must always return zero rows:

```cypher
MATCH (b:<ns>_Belief)-[c:<ns>_CURRENT_STATE]->()
WITH b, count(c) AS n
WHERE n > 1
RETURN b.belief_id, n;   -- MUST be empty
```

This pairing (construct-then-assert) is the honest substitute for a DB-level unique constraint
and is exactly what the Hypothesis invariant suite checks after every operation sequence.

---

## The Flexible-Connection Design

The requirement: accept an **injected** connection + namespace (NVM owns the handle and leases
it) **and** open/manage its own (standalone / tests). Verified constraint: LadybugDB allows
**one `READ_WRITE` Database object per file, many Connections from it**
([Kùzu concurrency](https://kuzudb.github.io/docs/concurrency/)). So the unit NVM owns is the
**`Database`**; the core can hold its own `Connection` derived from it, or own the whole
`Database` in standalone mode.

```python
class ConnectionProvider(Protocol):
    def connection(self) -> "ladybug.Connection": ...
    def close(self) -> None: ...          # no-op for injected; real for managed
    @property
    def owns_lifecycle(self) -> bool: ...  # managed=True, injected=False

class InjectedConnection:
    """NVM's path: NVM owns the Database; it leases us a Connection (or the Database
    handle to make our own). We NEVER close it."""
    def __init__(self, conn: "ladybug.Connection") -> None: ...
    # owns_lifecycle = False; close() is a no-op

class ManagedConnection:
    """Standalone/tests: we open the Database (file path or in-memory "") and a
    Connection, and we own teardown."""
    def __init__(self, db_path: str | None = None) -> None:
        self._db = ladybug.Database(db_path or "")   # "" == in-memory
        self._conn = ladybug.Connection(self._db)
    # owns_lifecycle = True; close() closes both
```

`MemoryCore` accepts either, plus the namespace:

```python
class MemoryCore:                      # implements BeliefStore
    def __init__(self, conn: "ladybug.Connection", *, namespace: str = "dox") -> None:
        self._provider = InjectedConnection(conn)
        self._ns = namespace
        schema.bootstrap(conn, namespace)     # idempotent CREATE ... IF NOT EXISTS

    @classmethod
    def open(cls, db_path: str | None = None, *, namespace: str = "dox") -> "MemoryCore":
        provider = ManagedConnection(db_path)
        core = cls(provider.connection(), namespace=namespace)
        core._provider = provider             # so close() tears the DB down
        return core

    def close(self) -> None: self._provider.close()
    def __enter__(self): return self
    def __exit__(self, *exc): self.close()
```

Why this is the right shape, not over-engineering:
- It is a **connection-provider**, not a storage abstraction. There is no `query()` method
  hiding Cypher behind it — Cypher stays in `queries.py`, pinned to LadybugDB on purpose. The
  only thing abstracted is *who created the handle and who closes it*. (Satisfies the explicit
  non-goal in PROJECT.md / memory-core §34.)
- **Injection is primary** (`__init__` takes a live `Connection`); `MemoryCore.open(...)` is
  the convenience constructor for standalone use. This matches `MemoryCore(db_connection,
  namespace_prefix)` from the design while adding the self-managed path.
- **Tests use `MemoryCore.open()` with in-memory `""`** for a throwaway DB per test — no files,
  full isolation, fast Hypothesis runs. (memory-core §9a: "test suite instantiates private
  throwaway databases.")

---

## Architectural Patterns

### Pattern 1: Protocol-as-seam, single concrete impl

**What:** Public type is `BeliefStore` (a `typing.Protocol`); consumers depend on it. Exactly
one implementation (`MemoryCore`) ships.
**When:** Always, here — it is the project's reason to exist.
**Trade-offs:** Adds an indirection with no second implementation today. Worth it: it is the
ACL that keeps NVM concepts out (the core never sees an actor/turn), and it makes the library
publishable as a reference impl. Avoid an ABC base class — `Protocol` is structural and
needs no inheritance from the impl.

### Pattern 2: UUID7-as-primary-key for immutable states

**What:** The `source_event_id` *is* the `BeliefState` PK and the temporal sort key.
**When:** Whenever the chain is append-only and time-ordered (the whole design).
**Trade-offs:** Couples identity to the caller-supplied event id — but that is desired (the
core stores the id it is given and never mints a competing one). Enables `get_scope_at` as a
`<=` scan with zero extra machinery. Requires UUID7 monotonicity (RFC 9562); generate via
`uuid_utils.uuid7()` (Rust-backed, fast) or `uuid.uuid7()` on Python 3.14+
([uuid_utils](https://pypi.org/project/uuid_utils/)).

### Pattern 3: One-transaction multi-statement mutation

**What:** `revise`/`contract` wrap their ordered statements in `BEGIN TRANSACTION` … `COMMIT`.
**When:** Any operation that touches >1 statement (re-point pointer + append + supersede).
**Trade-offs:** LadybugDB auto-wraps single statements; manual transactions are needed for
atomicity across the pointer move. Single-writer model means no concurrency hazard, only
all-or-nothing crash safety. ([Kùzu transactions](https://kuzudb.github.io/docs/cypher/transaction/))

### Pattern 4: Namespace as table-name prefix (schema-first tenancy)

**What:** Every owned table is `<ns>_Name`; the core is a label-family tenant.
**When:** Shared-DB deployment (NVM). Harmless in standalone (default prefix).
**Trade-offs:** Table names interpolated into Cypher via f-strings (cannot be bind params).
Mitigate by validating the namespace against `^[a-z][a-z0-9_]*$` once at construction — the
only place untrusted-ish text reaches a query string.

## Anti-Patterns

### Anti-Pattern 1: Treating LadybugDB like Neo4j

**What people do:** Assume ad-hoc labels, `MERGE` everywhere, `CREATE CONSTRAINT ... UNIQUE`,
multi-statement implicit transactions.
**Why it's wrong:** LadybugDB is schema-first (Kùzu lineage); none of those exist as written.
Uniqueness is PRIMARY-KEY-only.
**Instead:** DDL bootstrap up front; structural uniqueness + verification; explicit
transactions for multi-step writes.

### Anti-Pattern 2: A storage abstraction "to swap the DB later"

**What people do:** Wrap Cypher behind a generic `GraphStore`/repository interface.
**Why it's wrong:** Explicit non-goal (PROJECT.md, memory-core §34). The swap seam is
`BeliefStore` (rewrite the whole adapter), not a Cypher abstraction; a thin wrapper buys
nothing and a thick one becomes its own query engine.
**Instead:** Pin to LadybugDB/Cypher in `core.py`+`queries.py`; abstract only connection
ownership.

### Anti-Pattern 3: Interpreting `value` or `source_event_id`

**What people do:** Parse the JSON value to "help", or derive meaning from event ids.
**Why it's wrong:** Every such line is the leak the seam exists to prevent (memory-core §2).
**Instead:** `json.dumps`/`loads` at the boundary only; sort by event id, never decode it.

### Anti-Pattern 4: A global `belief_id` PRIMARY KEY

**What people do:** Make `belief_id` globally unique, so two scopes can't hold the same
proposition.
**Why it's wrong:** Multi-scope is the deliberate extension; the irony join needs the *same*
logical belief in two scopes.
**Instead:** PK = synthesized `f"{scope_id}::{belief_id}"`; keep `belief_id_logical` as a
property for cross-scope joins.

## Scaling Considerations

| Scale | Adjustments |
|-------|-------------|
| tens–hundreds of beliefs/scope (NVM's actual case) | No tuning. One-belief-per-node granularity is fine (Kumiho §7.1). |
| 10k+ states | `get_impact` bound depth matters; UUID7-PK scans stay indexed. Consider a secondary index on `BeliefState.belief_id` if chain queries slow. |
| 1M+ states | Beyond NVM's M0 scope. Columnar storage helps analytical traversal; revisit whether `get_scope_at`'s per-belief `collect()[0]` needs a materialized "current-at-event" projection. Do not pre-build this. |

### Scaling Priorities

1. **First bottleneck:** `get_scope_at` over many beliefs (per-belief sort+collect). Fix only
   if profiled: add an index on `(belief_id, state_id)`.
2. **Second bottleneck:** deep `get_impact` cascades. The `depth` bound is the governor;
   truncation policy is the *caller's* (a known soft spot — memory-core §10.3).

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| LadybugDB | `import ladybug as lb`; `lb.Database(path)`; `lb.Connection(db)`; `conn.execute(cypher, params_dict)` | Kùzu-compatible API. `""`/`":memory:"` for in-memory. Result is iterable / `.get_as_df()`. ([docs.ladybugdb.com](https://docs.ladybugdb.com/get-started/)) |
| `pydantic` | Boundary models (`Scope`, `BeliefState`), `frozen=True` for state immutability | v2 |
| `uuid_utils` | `uuid7()` generation (or stdlib `uuid.uuid7` on 3.14+) | Rust-backed; RFC 9562 ([uuid_utils](https://pypi.org/project/uuid_utils/)) |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| consumer ↔ `protocol.py` | type-only (Protocol + pydantic models) | no `ladybugdb` import crosses here |
| `core.py` ↔ `queries.py` | function calls returning Cypher text + param dicts | all Cypher localised |
| `core.py` ↔ `connection.py` | `ConnectionProvider.connection()` | lifecycle ownership only |
| `core.py` ↔ LadybugDB | `conn.execute()` | the one pinned dependency |

---

## Suggested Build Order

Dependencies are explicit; each step is independently testable before the next.

1. **`ids.py` + `models.py` + `protocol.py`** (no DB). UUID7 helper, pydantic `Scope`/
   `BeliefState`, the `BeliefStore` Protocol and `EdgeType` enum. *Gate:* `basedpyright
   strict` passes; a no-op stub satisfies the Protocol. **Depends on nothing.**
2. **`connection.py` + `schema.py`** — the flexible connection model and idempotent DDL
   bootstrap. *Gate:* `MemoryCore.open("")` creates all `<ns>_*` tables in an in-memory DB;
   injected path reuses an external `Connection`; namespace isolation verified. **Depends on
   1 (models for nothing yet; mostly standalone).** *This is the first real LadybugDB
   contact — validate the actual API here before building on it.*
3. **`get_or_create_scope` + `expand`/`revise` + `get_revision_chain`** in `core.py`/
   `queries.py`. The append-only spine and the single mutable pointer. *Gate:* round-trip a
   revise; `CURRENT_STATE`-uniqueness verification query returns empty; chain grows
   append-only. **Depends on 2.**
4. **`contract` + world-scope guard + `query_scope(include_deprecated)`**. *Gate:* world-scope
   `contract` raises; deprecated states hidden by default, visible with the flag. **Depends on
   3.**
5. **`add_edge` + `get_impact`**. The generic typed edges and the bounded cascade traversal.
   *Gate:* `get_impact` returns dependents to depth N, excludes beyond. **Depends on 3.**
6. **`get_scope_at`**. Structural time-travel. *Gate:* `get_scope_at(latest) == query_scope`;
   stepping event ids reconstructs the fold. **Depends on 3 (and 4 for retracted handling).**
7. **AGM property suite + structural-invariant tests + irony-join demo**. Hypothesis over
   operation sequences (success/inclusion/vacuity/consistency/extensionality; recovery
   excluded); invariant checks after each sequence; the actor-vs-world divergence query on
   synthetic data. *Gate:* the M0 exit gate. **Depends on 3–6.**
8. **Packaging/polish** (already scaffolded by the cookiecutter): docs site, CI/release, PyPI.
   **Depends on 7 being green.**

**Critical path:** 1 → 2 → 3 is the spine; 4/5/6 fan out in parallel from 3; 7 gates the
milestone. Step 2 is the **de-risking step** — it is where assumptions about the real
LadybugDB API (DDL idempotency, parameter passing, transaction syntax, in-memory mode) get
tested before any belief logic is built on them.

---

## Open Questions / Flags for Phase Research

- **`query_scope(query: str)` semantics** (memory-core §10.1, PROJECT.md soft spot). What does
  `query` mean without leaking triple structure? *Likely resolution:* `query` is an opaque
  belief-id prefix or exact id filter (string match against `belief_id_logical`), NOT a
  query language. Flag for the phase that implements `query_scope`.
- **`get_impact` depth default + truncation** (memory-core §10.3). `depth=5` is a sketch
  number; what the result means at the truncation boundary is the caller's policy. The core
  should return enough to let the caller detect truncation (e.g. whether the frontier was cut).
- **`$depth` as a bind parameter** in `*1..$depth`. Kùzu historically required the bound to be
  a literal; verify against the installed LadybugDB and inline a validated int if so.
- **JSON value encoding vs. Kùzu JSON extension.** Default to `STRING`+`json.dumps`. If
  LadybugDB ships the JSON extension and NVM ever wants to *index* into values (it should not,
  per the opacity rule), that is a deliberate later decision, not M0.
- **`belief_id` synthesized-PK vs. a real composite key.** Confirm LadybugDB has no usable
  composite PRIMARY KEY across `(scope_id, belief_id)`; if it does, prefer it over the
  `::`-joined string.

---

## Sources

- [LadybugDB GitHub](https://github.com/LadybugDB/ladybug) — "a graph database," embedded/serverless, "Serializable ACID transactions"
- [LadybugDB docs — Getting Started](https://docs.ladybugdb.com/get-started/) — Python API: `import ladybug as lb`, `lb.Database(path)`, `lb.Connection(db)`, `conn.execute(...)`, result iteration / `get_as_df`
- [Kùzu legacy / embedded landscape (gdotv)](https://gdotv.com/blog/kuzu-legacy-embedded-graph-database-landscape/) — LadybugDB is a Kùzu fork; kuzu-compatible Python API; multi-label nodes added
- [Database of Databases — LadybugDB](https://dbdb.io/db/ladybugdb) — fork lineage, columnar property-graph model
- [Kùzu CREATE TABLE](https://kuzudb.github.io/docs/cypher/data-definition/create-table/) — schema-first DDL; PRIMARY KEY; multiple FROM-TO pairs per rel table
- [Kùzu concurrency](https://kuzudb.github.io/docs/concurrency/) — one READ_WRITE Database per file, many Connections share it
- [Kùzu transactions](https://kuzudb.github.io/docs/cypher/transaction/) — BEGIN TRANSACTION / COMMIT / ROLLBACK; DDL is transactional
- [Kùzu data types](https://docs.kuzudb.com/cypher/data-types/) — native UUID, BLOB (≤4KB), LIST/STRUCT/MAP, JSON via STRUCT
- [uuid_utils (PyPI)](https://pypi.org/project/uuid_utils/) — Rust-backed UUID7
- [Python 3.14 uuid.uuid7 discussion](https://discuss.python.org/t/add-uuid7-in-uuid-module-in-standard-library/44390) — stdlib UUID7, RFC 9562 monotonic ordering
- NVM design (read-only inputs): `05-nvm-memory-core.md` (the seam, world scope, R19 tenancy), `21-nvm-component-architecture.md` (port/adapter framing, §7 persistence), `17-kumiho-nvm-recommendations.md` (revision-chain Cypher patterns, get_impact)

---
*Architecture research for: graph-native AGM belief-revision library (doxastica / Kumiho ref impl)*
*Researched: 2026-06-13*
