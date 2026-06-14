# Phase 2: Backend Adapters & Schema Bootstrap (De-risking Spike) - Research

**Researched:** 2026-06-15
**Domain:** Embedded graph-DB adapter engineering (LadybugDB/Kùzu-fork Cypher) + ports-and-adapters + uv packaging + Hypothesis/pytest harness
**Confidence:** HIGH — the SC4 spike was executed live against the **installed `ladybug` 0.17.1** on **Python 3.14.2** in this repo's venv, not inferred from docs.

## Summary

This phase has an unusual luxury: the `ladybug` package the SC4 spike must validate is **already installed and importable** in the repo venv (`0.17.1`, Python `3.14.2`). I ran the entire SC4 question list directly against it. Every open question is now answered with executable evidence, so planning can proceed with HIGH confidence and the spike can be a *confirmation* task rather than a discovery task.

The headline result resolves the named Phase-1 round-trip tension **in favour of keeping the LPG-primitive port**: ladybug expresses unbounded cycle-safe reachable-set traversal in **one** query, and the `(reached, frontier)` shape is computable in **one** query via `min(length(p))` + an `EXISTS{}` subquery — no extra round-trips. The single real surprise is a hard engine constraint: **variable-length patterns cap the upper hop bound at 30 by default**, and a literal bound above the configured cap is a *hard error* (not a silent truncation). This is configurable per-connection via `CALL var_length_extend_max_depth=N`. The consequence for the port: `max_depth=None` ("full closure") cannot compile to a truly-infinite traversal — it must compile to an explicit large literal bound with the connection cap raised to match. This is a documentable adapter-internal detail, **not** a port-signature change, so the Phase-1 contract survives intact.

The other risk flagged in CLAUDE.md — that `ladybug` might be untyped under basedpyright-strict — is **disproved**: ladybug ships `py.typed` and basedpyright reads it cleanly (0 errors), with `Connection.execute` returning the precise union `QueryResult | list[QueryResult]`. The only typing work in the adapter is narrowing that union, not suppressing `reportMissingTypeStubs`.

**Primary recommendation:** Treat SC4 as confirmed (evidence below). Build `LadybugBackend.traverse` to compile `max_depth=None` into `CALL var_length_extend_max_depth=<ceiling>` + `-[:<edges>* ACYCLIC 1..<ceiling>]->`, returning `(reached, frontier)` from one query; build `add_edge` on `MERGE` (idempotent) and `upsert_node` on `MERGE ... SET`; extract rows with `conn.execute(cypher, parameters=...).rows_as_dict().get_all()`. Keep the in-memory backend's visited-set BFS as the semantic oracle and lock parity via the parametrized conftest from day one.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: `MemoryCore` follows the SQLAlchemy Engine pattern — minus pool, two-tier, and registry.**
- Canonical constructor takes the port, never a raw connection: `MemoryCore(backend: BackendPort)`. `MemoryCore` is backend-agnostic and composes the port; it never holds an `lb.Connection` directly.
- Connection/path handling lives in named factory classmethods (maps to `create_engine`):
  - `MemoryCore.in_memory()` → wires an `InMemoryBackend` (always-works default).
  - `MemoryCore.open(path | ":memory:", *, namespace=...)` → builds a `LadybugBackend` that self-manages its connection (`owns_conn=True`).
  - `MemoryCore.from_connection(conn, *, namespace=...)` → wraps an injected `lb.Connection` it **never closes** (`owns_conn=False`; R19/CONN-01 tenancy).
- SC1's literal `MemoryCore(conn, namespace=...)` is the `from_connection` factory, NOT the canonical `__init__`. **Do not implement `__init__` to accept a raw connection.**
- DROPPED from SQLAlchemy: (a) the connection pool (ladybug is single-writer embedded); (b) the Engine-vs-Connection two-tier (collapse to one object; no `core.connect()`).
- **No URL/scheme registry (D-01a):** named classmethods only. `conftest` parametrization uses a plain `[LadybugBackend, InMemoryBackend]` list, not a registry lookup.

**D-02: Backend-driver import isolation — the core never imports a driver; only leaf backend modules do.**
- `backends/` subpackage: `backends/memory.py` (`InMemoryBackend`, stdlib + pydantic only, always importable); `backends/ladybug.py` (`LadybugBackend`, owns the guarded `import ladybug as lb`). Future `backends/neo4j.py` etc. slot in purely additively.
- The core stays driver-blind: `MemoryCore` (in `core.py`) uses **function-local imports** inside its factory classmethods, so importing `MemoryCore` never chain-loads a driver.
- `__init__.py` and `backends/__init__.py` never chain-import a driver (no `from .ladybug import *`). They may re-export the zero-dep `InMemoryBackend`.
- Each DB backend module guards its driver import and raises `errors.BackendDependencyError(ImportError)` with an actionable message (`pip install doxastica[ladybug]`).
- This is the single basedpyright boundary for the `ladybug` import — one module, one scope.
- Extend `tests/test_import_purity.py`: assert `doxastica`, `doxastica.core`, and `doxastica.backends.memory` import with `ladybug` genuinely absent, and that `MemoryCore.in_memory()` works driver-free.

**D-03: Option B packaging — `pydantic` is the only required runtime dep; `ladybug` is the reference-backend extra.** REVERSES a documented CLAUDE.md constraint.
- `[project.dependencies]` = `["pydantic>=2.11,<3"]` only. Remove `ladybug` from required deps.
- `[project.optional-dependencies]`: `ladybug = ["ladybug>=0.17,<0.18"]`; an `all` extra; placeholder note for future `neo4j`/`surrealdb` extras.
- Install surfaces: `pip install doxastica` → pydantic + in-memory backend; `pip install doxastica[ladybug]` → adds the reference backend.
- Two-environment CI: Job 1 base install (pydantic only) → in-memory subset + import-purity test with ladybug truly absent; Job 2 `doxastica[ladybug]` + dev group → full both-backend conftest suite.
- **[BLOCKING] CLAUDE.md update is part of this phase** (decision-grade reversal recorded, not a silent edit): the "exactly ladybug + pydantic" runtime-dep line and the "Storage: pinned to LadybugDB / no storage abstraction" framing.

**D-04: Ladybug adapter ownership, schema bootstrap, namespace-identifier safety (CONN-02, CONN-03).**
- The ladybug backend is the sole writer of its namespaced closed subgraph: `:<ns>_Scope` / `:<ns>_Belief` / `:<ns>_BeliefState` node tables and edge types, no outbound graph references.
- Schema bootstrap runs idempotently on init: `CREATE NODE/REL TABLE IF NOT EXISTS <ns>_*`, safe against a fresh OR shared injected DB.
- Namespace-identifier safety: DDL table identifiers cannot be `$param`-bound, so the namespace must be string-interpolated. The namespace MUST be validated (`^[A-Za-z_][A-Za-z0-9_]*$`) before interpolation — explicit guard, not an exception to the always-parameterize rule.
- Adapters return raw `list[dict]` below the model layer; `MemoryCore` hydrates into frozen pydantic models and JSON-encodes the opaque `value`. Keep the port model-blind.

**D-05: In-memory backend is a first-class shipping product AND the Phase 7 oracle (BACK-03, FORMAL-06).**
- `InMemoryBackend` implements the SAME `BackendPort` with zero extra dependency; its `traverse` is the visited-set BFS the port doc names as the reference implementation.
- Oracle parity is a hard requirement: in-memory `traverse`/`match_nodes` semantics must match the ladybug backend exactly. The parametrized `conftest` is the mechanism that keeps them honest from day one.

### Claude's Discretion

CONTEXT.md does not carve out an explicit "Claude's Discretion" section. The decisions above are tight; the remaining freedom is *implementation detail within them* — the concrete Cypher templates, the in-memory data structures, the exact frontier-computation query, the conftest fixture shape, and the choice of traversal mode (`ACYCLIC` vs `SHORTEST`) for compiling `traverse`. This research recommends specifics for each below.

### Deferred Ideas (OUT OF SCOPE)

- **URL/scheme backend registry** — deferred unless backend count / a plugin model forces it (D-01a).
- **Keeping `ladybug` as a default-installed dep** — rejected in favour of Option B (D-03).
- **AGM operations, world-scope identity, retrieval, edge/impact *behaviour*** — Phases 3–6. Phase 2 builds the mechanism, not the operations. No `MemoryCore` AGM-operation bodies are written here — only constructors, port wiring, and `unit_of_work` exercise.
- (Out of scope, from the phase goal) `revise`/`expand`/`contract`, `query_scope`, `get_impact`/`get_scope_at` *behaviours* — Phases 3–6.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BACK-02 | `ladybug` reference backend adapter implements the port over LadybugDB | Live spike confirms all five primitives are expressible: `upsert_node`→`MERGE...SET`; `add_edge`→`MERGE` edge; `match_nodes`→`MATCH ... WHERE (props) RETURN ...rows_as_dict()`; `traverse`→`-[:* ACYCLIC 1..N]->`; `unit_of_work`→`BEGIN TRANSACTION`/`COMMIT`/`ROLLBACK` through `execute`. See Code Examples. |
| BACK-03 | In-memory backend adapter ships as the second backend, doubles as Phase 7 oracle, zero extra dependency | `traverse` is a visited-set BFS over plain dicts (stdlib only). Semantics must equal ladybug's `ACYCLIC` reachable-set; parity enforced by parametrized conftest. See Architecture Patterns §In-Memory Backend. |
| CONN-01 | Flexible connection: injected `lb.Connection` (never closed; R19) + self-managed `open(path/:memory:)` | Spike confirms `Connection.close()` is idempotent (double-close OK) and execute-after-close raises `RuntimeError("Connection is closed.")` — so `_owns_conn` ownership flag is the only guard needed. File-mode persistence and `:memory:` both verified. |
| CONN-02 | Label-family tenancy: ladybug backend sole writer of its namespaced tables; closed subgraph | Namespace prefixing verified: two namespaces coexist in one DB with isolated `MATCH (:a_S)` vs `(:b_S)`. No outbound graph references (entity mentions are opaque `value`). |
| CONN-03 | Idempotent schema bootstrap (`CREATE NODE/REL TABLE IF NOT EXISTS`); uniqueness via PRIMARY KEY | `CREATE NODE/REL TABLE IF NOT EXISTS` verified idempotent (re-run = no-op, no error). `PRIMARY KEY(state_id)` gives uniqueness (no UNIQUE constraint exists/needed). |
| FORMAL-06 | Throwaway `:memory:` LadybugDB per example; parametrized harness; no lock errors / state bleed | `lb.Database()` (None path) = fresh in-memory DB per call; perfect isolation. Multi-reader (two `Connection`s on one DB) works; single-writer enforced by engine. conftest design in Validation Architecture §. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Connection lifecycle / ownership (`_owns_conn`) | `backends/ladybug.py` | — | R19 tenancy is a backend concern; the core is driver-blind (D-02). |
| Schema DDL bootstrap (namespaced, idempotent) | `backends/ladybug.py` | — | DDL is ladybug-specific; in-memory has no schema. CONN-03. |
| Namespace identifier validation | `backends/ladybug.py` | `MemoryCore.open/from_connection` (passes the validated value) | The unsafe-interpolation guard lives where interpolation happens. D-04. |
| Five LPG primitives | both backends | — | Each backend translates the generic port to its native form. BACK-02/03. |
| `traverse` reachable-set + frontier | both backends | — | ladybug: one Cypher query; in-memory: visited-set BFS. Semantics must match (oracle parity, D-05). |
| Model hydration / JSON value encoding | `MemoryCore` (core.py) | — | Port returns raw `list[dict]`; core hydrates frozen pydantic + encodes opaque `value`. D-04. |
| Factory wiring (`in_memory`/`open`/`from_connection`) | `MemoryCore` (core.py) | leaf backend modules (function-local import) | Engine pattern; core stays import-blind. D-01/D-02. |
| Friendly missing-driver error | `backends/ladybug.py` (guarded import) → `errors.BackendDependencyError` | — | One import-guard site; raises actionable `pip install doxastica[ladybug]`. D-02. |
| Test isolation (throwaway DB per example) | `tests/conftest.py` | — | `lb.Database()` fresh per fixture; parametrized over both backends. FORMAL-06. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ladybug` | `>=0.17,<0.18` (installed: **0.17.1**) | Embedded LPG graph DB + Cypher; the **reference** backend (now an *extra*, D-03) | Single-writer embedded model gives write serialization "for free"; ships `py.typed`. `[VERIFIED: installed in repo venv, import ladybug as lb OK]` |
| `pydantic` | `>=2.11,<3` | The ONLY required runtime dep; frozen models hydrated by `MemoryCore` | Already in use (Phase 1 models). `[VERIFIED: pyproject.toml + Phase 1 models]` |

### Supporting (dev/test only — already in the dev group)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `hypothesis` | `>=6.155` | Stateful + `@given` property tests | Phase 7 mostly; Phase 2 uses ordinary pytest + the parametrized conftest. `[VERIFIED: pyproject.toml]` |
| `pytest` | `>=8.0.0` (resolves 9.x) | Test runner; `parametrize` for both-backend fixture | The conftest harness (FORMAL-06). `[VERIFIED: pyproject.toml + suite runs green]` |
| `pytest-cov` | `>=6.0.0` | Coverage (PR workflow) | Existing `pr.yml`. `[VERIFIED: .github/workflows/pr.yml]` |
| `basedpyright` | `>=1.38.0` (installed 1.39.x) | Strict typing gate | Confirms ladybug typing; narrows the `execute` union. `[VERIFIED: ran basedpyright on a ladybug probe — 0 errors]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `MERGE ... SET` for upsert | `CREATE` + catch duplicate-PK error | MERGE is idempotent by construction (verified: double-MERGE → 1 node); CREATE-and-catch is racy and noisier. |
| `-[:* ACYCLIC 1..N]->` for `traverse` | bare `-[:*]->` (WALK, default) | WALK can revisit nodes and **silently caps at 30 hops**; ACYCLIC guarantees node-distinct (true cycle-safety) and is the honest expression of the port's "de-duplicated, cycle-safe" contract. |
| Python-side BFS issuing many `match_nodes` | single var-length Cypher query | The whole point of the SC4 spike: the single-query form keeps the round-trip budget acceptable, so the LPG-primitive port survives. |

**Installation:**
```bash
# Dev / spike work (full both-backend suite)
uv sync --dev --extra ladybug
# Base install (proves import isolation — pydantic only, ladybug ABSENT)
uv sync --no-default-groups        # or: pip install .   (no [ladybug] extra)
```

**Version verification:** `ladybug` confirmed present at **0.17.1** via `uv pip show ladybug` and `import ladybug; ladybug.__version__`; Python **3.14.2** via `uv run python --version`. `requires-python` of ladybug is `>=3.10,<3.15` — covers the locked 3.14 floor. `[VERIFIED: uv pip show + runtime import]`

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `ladybug` | PyPI | est. >1yr (0.17.1) | n/a (niche) | github.com/LadybugDB/ladybug | OK | Approved (moves to `[ladybug]` extra per D-03) |
| `pydantic` | PyPI | 8+ yrs | very high | github.com/pydantic/pydantic | OK | Approved (sole required dep) |

**Packages removed due to [SLOP] verdict:** none — but note the standing slopsquat hazard from CLAUDE.md: **`ladybugdb` is NOT the installable** (404 on PyPI); the package and import name is `ladybug`. The repo already pins `ladybug` correctly. No new packages are introduced in this phase.
**Packages flagged as suspicious [SUS]:** none.

*No external package-legitimacy seam was run because Phase 2 introduces **zero new packages** — it only relocates the already-installed, already-verified `ladybug` from required deps to an extra. The one live hazard (cross-name `ladybugdb`) is a known constraint, already correctly handled in `pyproject.toml`.*

## Architecture Patterns

### System Architecture Diagram

```
                         consumer code / tests
                                  │
                                  ▼  MemoryCore.in_memory()
                         ┌──────────────────────┐         .open(path, namespace=)
                         │      MemoryCore       │◀── .from_connection(conn, namespace=)
                         │  (core.py, DRIVER-    │
                         │   BLIND; composes a   │   factory classmethods do
                         │   BackendPort)        │   FUNCTION-LOCAL imports
                         └───────────┬──────────┘   (no driver chain-load)
                                     │ calls 5 LPG primitives
                 ┌───────────────────┴────────────────────┐
                 ▼                                          ▼
   ┌─────────────────────────┐               ┌──────────────────────────────┐
   │  InMemoryBackend        │               │  LadybugBackend              │
   │  backends/memory.py     │               │  backends/ladybug.py         │
   │  stdlib + pydantic only │               │  guarded `import ladybug`    │
   │  ALWAYS IMPORTABLE       │               │  raises BackendDependencyError│
   │                         │               │  on missing driver           │
   │  nodes: dict[id,props]  │               │  _owns_conn flag (R19)       │
   │  edges: adjacency lists  │               │  namespace-validated DDL     │
   │  traverse = visited-set  │               │  traverse = ACYCLIC var-len  │
   │  BFS  ◀── ORACLE         │  must equal → │  Cypher (one query)          │
   └─────────────────────────┘               └───────────────┬──────────────┘
                 ▲                                            │ conn.execute(cypher, parameters=)
                 │   parity enforced by                       ▼
                 │   parametrized conftest          ┌──────────────────────┐
                 └──────────────────────────────────│  lb.Database / lb.   │
                                                     │  Connection (Kùzu-   │
                                                     │  fork embedded LPG)  │
                                                     │  namespaced closed   │
                                                     │  subgraph: <ns>_*    │
                                                     └──────────────────────┘
```

### Recommended Project Structure
```
src/doxastica/
├── __init__.py            # may re-export InMemoryBackend; NEVER chain-imports ladybug
├── core.py                # NEW: MemoryCore + factory classmethods (no AGM bodies)
├── ports.py               # Phase 1 (unchanged — backend-blind BackendPort)
├── protocol.py            # Phase 1 (unchanged)
├── models.py              # Phase 1 (unchanged — frozen models)
├── errors.py              # ADD: BackendDependencyError(ImportError)
└── backends/
    ├── __init__.py        # NEW: may re-export InMemoryBackend; never imports ladybug
    ├── memory.py          # NEW: InMemoryBackend (stdlib + pydantic only)
    └── ladybug.py         # NEW: LadybugBackend (guarded import ladybug)
tests/
├── conftest.py            # FILL: throwaway-DB fixtures parametrized over both backends
├── test_import_purity.py  # EXTEND: prove core + memory import with ladybug absent
└── test_backends_*.py     # NEW: per-primitive exercise of both backends
docs/backend-contract.md   # Phase 1 (unchanged)
```

### Pattern 1: Flexible connection with ownership flag (CONN-01 / R19)
**What:** The backend distinguishes a connection it *owns* (opened itself) from one *injected* (a tenant's). It closes only what it owns.
**When to use:** All three `MemoryCore` factories funnel into `LadybugBackend.__init__(conn, *, namespace, owns_conn)`.
**Example:**
```python
# Source: SQLAlchemy Engine/creator analog (D-01) + verified ladybug close() semantics
class LadybugBackend:
    def __init__(self, conn: "lb.Connection", *, namespace: str, owns_conn: bool) -> None:
        _validate_namespace(namespace)          # D-04 guard, see Pattern 3
        self._conn = conn
        self._ns = namespace
        self._owns_conn = owns_conn
        self._bootstrap_schema()                # CONN-03 idempotent DDL

    def close(self) -> None:
        if self._owns_conn:                     # R19: never close an injected handle
            self._conn.close()                  # idempotent — double-close is a no-op (verified)
```
`MemoryCore.from_connection(conn, ...)` builds it with `owns_conn=False`; `MemoryCore.open(path, ...)` opens `lb.Database`/`lb.Connection` itself and passes `owns_conn=True`.

### Pattern 2: Guarded driver import → friendly error (D-02)
```python
# Source: D-02; only backends/ladybug.py touches the driver
try:
    import ladybug as lb
except ImportError as exc:  # pragma: no cover - exercised in the base-install CI job
    raise errors.BackendDependencyError(
        "The ladybug backend requires the 'ladybug' package. "
        "Install it with:  pip install doxastica[ladybug]"
    ) from exc
```
`BackendDependencyError` subclasses `ImportError` (D-02) so callers can catch either. This is also the single basedpyright boundary — but note ladybug ships `py.typed`, so **no `# pyright: ignore` is required** for the import itself (see Pitfall 4).

### Pattern 3: Namespace-identifier validation before interpolation (D-04)
```python
# Source: D-04 — DDL identifiers cannot be $param-bound, so they MUST be guarded
import re
_NS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def _validate_namespace(ns: str) -> None:
    if not _NS_RE.match(ns):
        raise ValueError(f"namespace must match {_NS_RE.pattern!r}; got {ns!r}")
```
Every DDL string interpolates `{self._ns}` only AFTER this guard. All *data* still uses `$param` binds — the namespace is the single sanctioned interpolation point.

### Pattern 4: Idempotent namespaced bootstrap (CONN-02 / CONN-03)
```python
# Source: verified live — CREATE ... IF NOT EXISTS is idempotent on ladybug 0.17.1
def _bootstrap_schema(self) -> None:
    ns = self._ns
    self._conn.execute(
        f"CREATE NODE TABLE IF NOT EXISTS {ns}_Scope"
        f"(scope_id STRING, is_world BOOLEAN, PRIMARY KEY(scope_id))")
    self._conn.execute(
        f"CREATE NODE TABLE IF NOT EXISTS {ns}_Belief"
        f"(belief_id STRING, PRIMARY KEY(belief_id))")
    self._conn.execute(
        f"CREATE NODE TABLE IF NOT EXISTS {ns}_BeliefState"
        f"(state_id STRING, belief_id STRING, scope_id STRING, "
        f" source_event_id STRING, value STRING, status STRING, PRIMARY KEY(state_id))")
    # structural + generic edge tables (HAS_REVISION/CURRENT_STATE come in Phase 3)
    for et in ("SUPERSEDES", "DEPENDS_ON", "DERIVED_FROM"):
        self._conn.execute(
            f"CREATE REL TABLE IF NOT EXISTS {ns}_{et}"
            f"(FROM {ns}_BeliefState TO {ns}_BeliefState)")
```
Re-running against a fresh OR shared injected DB is safe (verified: re-run = silent no-op, no error). `state_id` is a `STRING` column holding the UUID7 text form (ladybug has no native UUID type in this schema posture; the core mints `uuid.uuid7()` and stringifies).

### Pattern 5: `traverse` compiled to one cycle-safe query (the SC4 resolution)
```python
# Source: verified live — ACYCLIC var-length, cap raised for unbounded, frontier in one query
_DEPTH_CEILING = 1_000_000  # the literal compiled in for max_depth=None ("full closure")

def traverse(self, start, edge_types, max_depth):
    ns = self._ns
    bound = max_depth if max_depth is not None else _DEPTH_CEILING
    self._conn.execute(f"CALL var_length_extend_max_depth={bound}")   # lift the 30 cap
    rels = "|".join(f"{ns}_{e}" for e in edge_types)                  # multi-edge-type union
    # reached set + min depth, plus frontier (at-bound nodes with an unexpanded successor)
    cy = (
        f"MATCH p=(a:{ns}_BeliefState {{state_id:$start}})"
        f"-[:{rels}* ACYCLIC 1..{bound}]->(b:{ns}_BeliefState) "
        f"WITH b, min(length(p)) AS d "
        f"RETURN b.state_id AS state_id, d, "
        f"(d = {bound} AND EXISTS {{ MATCH (b)-[:{rels}]->() }}) AS at_frontier"
    )
    rows = self._conn.execute(cy, parameters={"start": str(start)}).rows_as_dict().get_all()
    reached = [r for r in rows]                       # core hydrates these
    frontier = frozenset(r["state_id"] for r in rows if r["at_frontier"])
    return reached, frontier
```
- **`bound` is interpolated, not `$param`-bound** — ladybug rejects `$param` inside the `*1..$d` pattern (verified). `bound` is an `int` guaranteed by the port signature (`int | None`); validate `>= 0` before interpolation as belt-and-braces.
- `max_depth=None` ⇒ the literal `_DEPTH_CEILING` ⇒ empty frontier in practice (no real graph is a million deep). The port contract's "empty frontier when unbounded" holds.
- The reachable set is **cycle-safe** because `ACYCLIC` forces node-distinct paths; the engine never loops (verified on a 3-node cycle, completes in <1ms).

### In-Memory Backend (the oracle, D-05/BACK-03)
```python
# Source: D-05 — visited-set BFS, the reference implementation named in the port doc
def traverse(self, start, edge_types, max_depth):
    reached: dict = {}
    frontier: set = set()
    seen = {start}
    layer = [(start, 0)]
    while layer:
        nxt = []
        for nid, depth in layer:
            for to in self._out_edges(nid, edge_types):
                if to in seen:
                    continue
                if max_depth is not None and depth + 1 > max_depth:
                    frontier.add(nid)          # nid had an unexpanded successor at the bound
                    continue
                seen.add(to); reached[to] = self._nodes[to]; nxt.append((to, depth + 1))
        layer = nxt
    return list(reached.values()), frozenset(frontier)
```
**Parity note:** the frontier semantics must match ladybug's "node at exactly `max_depth` that has an unexpanded successor." This is subtle — bake it into the parametrized conftest so both backends are asserted identical on the *same* graphs, including the empty-frontier-when-unbounded case.

### Anti-Patterns to Avoid
- **Bare `-[:*]->` for unbounded traverse:** silently caps at 30 hops AND uses WALK mode (node-revisiting). Use `ACYCLIC 1..<bound>` with the cap raised.
- **`$param` inside the var-length bound (`*1..$d`):** a hard parser error on ladybug. Interpolate a validated int.
- **`CREATE` for edges that may be re-added:** duplicates (verified). Use `MERGE`.
- **Closing an injected connection:** R19 violation. Gate `close()` on `_owns_conn`.
- **`import ladybug` anywhere but `backends/ladybug.py`:** breaks D-02 isolation; the extended import-purity test will fail the build.
- **String-interpolating data values into Cypher:** docs strongly discourage it. Only the validated namespace and the validated int depth bound are interpolated.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Idempotent node insert | manual "exists? then update else insert" round-trips | `MERGE (n {pk:$id}) SET ...` | One round-trip, race-free, verified idempotent. |
| Idempotent edge insert | dedup tracking | `MERGE (a)-[:T]->(b)` | Verified: double-MERGE = 1 edge; double-CREATE = 2. |
| Cycle-safe reachable set | Python BFS issuing N `match_nodes` calls (ladybug side) | one `ACYCLIC` var-length query | Keeps the round-trip budget acceptable — the entire SC4 point. (In-memory side DOES hand-roll BFS — that's the oracle.) |
| Transaction atomicity | manual compensating writes | `BEGIN TRANSACTION`/`COMMIT`/`ROLLBACK` via `execute` | Verified: ROLLBACK discards the write; serializable WAL. |
| Dict-row extraction | manual `zip(get_column_names(), row)` | `result.rows_as_dict().get_all()` | Returns `list[dict[str, Any]]` directly — exactly the port's return type. |
| UUID7 minting | a uuid7 lib | stdlib `uuid.uuid7()` | Native in 3.14 (locked floor); zero deps. |

**Key insight:** The temptation in a backend-agnostic port is to push graph-walk logic up into Python (so both backends share it). Resist on the ladybug side — its single-query var-length traversal is what makes the LPG-primitive port viable. Only the in-memory backend hand-rolls BFS, and only because it IS the oracle.

## Runtime State Inventory

> Phase 2 is greenfield code creation plus ONE documented constraint reversal (D-03). The reversal touches stored prose/config, so the relevant categories are inventoried below.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no databases store the renamed constraint; the `ladybug` *package* stays, only its dependency *classification* changes. | None. |
| Live service config | CI workflows reference dep install. `.github/workflows/quality.yml` and `pr.yml` run `uv sync --locked --dev` (no extra). Job 2 (both-backend) needs `--extra ladybug`; Job 1 (isolation) must run with ladybug ABSENT. | Edit workflows: add the `[ladybug]` extra to the full-suite job; add/confirm a base-install job. (D-03 two-env CI.) |
| OS-registered state | None. | None — verified: no OS-level registration involves the dep classification. |
| Secrets/env vars | `UV_NO_SYNC=1` workaround noted in user memory (uv sandbox panic) — code-only, unaffected. | None. |
| Build artifacts | `uv.lock` pins `ladybug` as a project dependency; moving it to `[project.optional-dependencies]` will re-resolve the lock. | `uv lock` after the `pyproject.toml` edit; commit the updated `uv.lock`. The `pre-commit`/`prek` `uv-lock` hook will enforce this. |

**The canonical question:** after `pyproject.toml` reclassifies `ladybug` as an extra, what still assumes it is always installed? Answer: (1) `uv.lock` (re-lock), (2) the CI quality job (must split into two), (3) CLAUDE.md prose (the [BLOCKING] update). All three are in-scope tasks.

## Common Pitfalls

### Pitfall 1: The 30-hop variable-length cap (THE de-risking finding)
**What goes wrong:** A bare `-[:*]->` traversal silently returns only nodes within 30 hops; a literal bound `*1..40` raises `Binder exception: Upper bound of rel exceeds maximum: 30`. Either way, `max_depth=None`/"full closure" is quietly or loudly broken if you ignore it.
**Why it happens:** Kùzu/ladybug enforces a configurable per-connection ceiling (`var_length_extend_max_depth`, default 30) on variable-length patterns to bound recursive-join cost.
**How to avoid:** Issue `CALL var_length_extend_max_depth=<bound>` before the traversal, compiling `max_depth=None` to a large literal ceiling. Verified: after raising the cap, `*1..100 ACYCLIC` returns the full 39-node reachable set from a 40-node chain+cycle.
**Warning signs:** A traversal that returns suspiciously round counts (exactly 30), or a `Binder exception` on a deep graph.

### Pitfall 2: `$param` rejected inside the var-length bound
**What goes wrong:** `MATCH (a)-[:DEP*1..$d]->(b)` is a hard parser error (`expected rule oC_SingleQuery`).
**Why it happens:** Kùzu-lineage grammar requires literal integers in the hop range; the bind-parameter slot doesn't exist there.
**How to avoid:** Interpolate a validated `int` (the port signature guarantees `int | None`; assert `>= 0`). This is the pre-authorized workaround from the CONTEXT spike list — and it lives entirely inside `LadybugBackend.traverse`, invisible to `MemoryCore`. All *data* binds still use `$param`.
**Warning signs:** Parser exception pointing at the `$` in the pattern.

### Pitfall 3: WALK vs ACYCLIC — apparent cycle-safety that isn't
**What goes wrong:** Default traversal mode is WALK (nodes/relationships can repeat). It *looks* cycle-safe only because a `RETURN DISTINCT` deduplicates the output — the engine still does the redundant walking, and on a true cycle without a bound this is wasteful/incorrect for a "node set."
**How to avoid:** Use `ACYCLIC` (all nodes distinct) for `traverse` — it is the honest expression of the port's "de-duplicated, cycle-safe set of reachable nodes." Verified to terminate instantly on a 3-node cycle.
**Warning signs:** Reasoning about correctness from `DISTINCT` rather than from the traversal mode.

### Pitfall 4: Assuming ladybug is untyped (it isn't)
**What goes wrong:** CLAUDE.md anticipates a `# pyright: ignore` boundary for an untyped `ladybug`. Adding blanket ignores would hide real type errors.
**Why it happens:** Stale assumption. ladybug **ships `py.typed`**; basedpyright reads it cleanly (verified: 0 errors on a probe).
**How to avoid:** Do NOT add `reportMissingTypeStubs` suppressions. The one genuine typing task is narrowing `Connection.execute`'s return — it is typed `QueryResult | list[QueryResult]`. A single statement (`assert isinstance(result, lb.QueryResult)` or a typed helper) narrows it; no module-wide ignore needed.
**Warning signs:** A reviewer adding `# pyright: ignore[reportUnknownMemberType]` — almost certainly unnecessary here.

### Pitfall 5: State bleed / lock errors across tests (FORMAL-06)
**What goes wrong:** Sharing one `lb.Database` across examples leaks state; opening two writers risks lock contention.
**How to avoid:** Construct a fresh `lb.Database()` (None path = in-memory) per fixture invocation — verified perfectly isolated. Single-writer is enforced by the engine; multi-reader works. For Hypothesis (Phase 7), spin up the throwaway DB in `@initialize`/the fixture per example.
**Warning signs:** Tests passing in isolation but failing in suite order; "active transaction" or lock errors.

## Code Examples

Verified live against `ladybug` 0.17.1 / Python 3.14.2 in this repo's venv.

### Connection construction (both modes)
```python
import ladybug as lb
# In-memory (None path; ":memory:" / "" also accepted)
db = lb.Database()
conn = lb.Connection(db)
# On-disk (persists across reopen — verified)
db = lb.Database("/path/to/kdb")
conn = lb.Connection(db)
```

### Parameterized query → list[dict] (the canonical extraction)
```python
rows: list[dict] = (
    conn.execute(
        "MATCH (s:ns_Scope {scope_id: $sid}) RETURN s.scope_id AS scope_id, s.is_world AS is_world",
        parameters={"sid": "world"},
    )
    .rows_as_dict()        # toggles dict mode; returns the SAME QueryResult (Self)
    .get_all()             # -> [{'scope_id': 'world', 'is_world': True}]
)
# NOTE: rows_as_dict() is a mode toggle, not a row iterator. Call get_all() (or iterate
# has_next()/get_next()) AFTER it.
```

### Atomic multi-statement unit_of_work
```python
# Source: verified — ROLLBACK discards the write; COMMIT persists it
import contextlib
@contextlib.contextmanager
def unit_of_work(conn):
    conn.execute("BEGIN TRANSACTION")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
```

### Idempotent upsert / edge
```python
conn.execute("MERGE (b:ns_BeliefState {state_id:$id}) SET b.value=$v",
             parameters={"id": "s1", "v": '{"x":1}'})   # re-run = still 1 node (verified)
conn.execute("MATCH (x:ns_BeliefState{state_id:$f}),(y:ns_BeliefState{state_id:$t}) "
             "MERGE (x)-[:ns_DEPENDS_ON]->(y)",
             parameters={"f": "s1", "t": "s2"})          # re-run = still 1 edge (verified)
```

### Reading/raising the var-length cap
```python
conn.execute("CALL var_length_extend_max_depth=1000")                       # set
conn.execute("CALL current_setting('var_length_extend_max_depth') RETURN *")  # read back -> '1000'
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| "Runtime deps = exactly `ladybug` + `pydantic`" (CLAUDE.md) | `pydantic` required; `ladybug` is the reference-backend *extra* | Phase 2 D-03 (this phase) | [BLOCKING] CLAUDE.md + pyproject.toml + uv.lock + CI all change. |
| "Storage pinned to LadybugDB / no storage abstraction" framing | Superseded by the Phase-1 `BackendPort`; ladybug is the *reference* backend, not the only one | Phase 1 BACK-01 + Phase 2 D-03 | CLAUDE.md prose update; the port (not a storage-abstraction) is the seam. |
| Floor 3.11, possible uuid7 shim | Floor 3.14, native `uuid.uuid7()` | Phase 1 decision #2 (locked) | Already reflected in pyproject/CI; no shim. |
| Spike treated as risky unknown | Spike confirmed live (this research) | 2026-06-15 | SC4 is a confirmation task, not discovery. |

**Deprecated/outdated:**
- The CLAUDE.md "Ladybug might be untyped → plan a `# pyright: ignore` boundary" note: ladybug ships `py.typed`; no blanket ignore needed.
- Any expectation that bare `-[:*]->` means truly-unbounded: it caps at 30.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_DEPTH_CEILING = 1_000_000` is a safe stand-in for "full closure" (no real belief graph approaches it) | Pattern 5 | If a pathological graph exceeds it, traverse under-reports without `truncated`. Mitigation: pick a ceiling, document it; revisit only if a real graph nears it. Engine accepts arbitrarily large bounds (verified 1000+). |
| A2 | `MERGE`-based `upsert_node`/`add_edge` interact correctly with manual `BEGIN/COMMIT` transactions | Patterns, Code Examples | Low — both verified independently; their composition (MERGE inside an explicit tx) is standard Cypher but was not separately exercised. Plan a confirmation assertion. |
| A3 | NVM (the primary consumer) targets Python 3.14 | (carried from Phase 1) | The locked 3.14 floor assumes this. Out of this phase's reach to verify; flagged for user confirmation. Floor already locked regardless. |
| A4 | `state_id`/`source_event_id` stored as `STRING` (UUID7 text) is acceptable vs a native type | Pattern 4 | Low — ladybug schema here uses STRING PKs; byte-order ordering (DATA-03) is computed by the core, not the DB. If a native UUID type is later wanted it's a schema migration, but Phase 2 only needs round-trip + uniqueness, both met. |

## Open Questions (RESOLVED)

1. **Exact frontier semantics parity between backends under partial bounds.**
   - What we know: both can compute "node at exactly `max_depth` with an unexpanded successor"; ladybug via `EXISTS{}` subquery, in-memory via BFS layering.
   - What's unclear: edge cases (diamond graphs where a node is reachable at two depths) may differ in which depth "wins" for the frontier test.
   - RESOLVED: covered by plan 02-03's parametrized parity suite (diamond/cycle/over-bound graphs) in THIS phase — `tests/test_backend_parity.py` asserts identical `(reached, frontier)` from both backends. This is the BACK-03/D-05 parity guarantee, made a first-class Phase 2 test, not deferred to Phase 7.

2. **Does the port need *any* adjustment after the spike?**
   - What we know: the signature survives unchanged — the 30-cap and `$param` issues are adapter-internal.
   - What's unclear: nothing material. CONTEXT explicitly authorizes adjusting the port now if needed; the spike says it isn't.
   - RESOLVED: port unchanged; SC4 confirmed live against ladybug 0.17.1. The `_DEPTH_CEILING` and traversal-mode (ACYCLIC var-length + raised `var_length_extend_max_depth`) choices are documented adapter details, not port changes; plan 02-02 records "port unchanged, SC4 confirmed" in its SUMMARY.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | everything | ✓ | 3.14.2 | — (3.14 is the locked floor) |
| `ladybug` | LadybugBackend, full conftest suite, SC4 spike | ✓ | 0.17.1 | in-memory backend covers the dependency-light path (D-03 base install) |
| `pydantic` | models / hydration | ✓ | (>=2.11 pinned) | — |
| `uv` | build, lock, two-env CI | ✓ | (installed) | — |
| `basedpyright` | strict typing gate | ✓ | 1.39.x | — |
| `pytest` / `hypothesis` | test harness | ✓ | 9.x / 6.155+ | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — but note the *deliberate* absence regime: CI Job 1 must run with `ladybug` UNINSTALLED to prove D-02 import isolation. That is a feature, not a gap.

## Validation Architecture

> `nyquist_validation` not found disabled in config → section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (>=8, resolves 9.0.3) + parametrize; hypothesis available for later |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`addopts = "-v"`) |
| Quick run command | `uv run pytest -q` |
| Full suite command | `uv sync --dev --extra ladybug && uv run pytest` |
| Isolation run (ladybug absent) | `uv sync --no-default-groups && uv run pytest tests/test_import_purity.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-02 | ladybug backend satisfies all 5 primitives | integration | `uv run pytest tests/test_backend_ladybug.py -x` | ❌ Wave 0 |
| BACK-03 | in-memory backend satisfies all 5 primitives | unit | `uv run pytest tests/test_backend_memory.py -x` | ❌ Wave 0 |
| BACK-02/03 parity | both backends return identical `(reached,frontier)` & `match_nodes` | parametrized | `uv run pytest tests/test_backend_parity.py -x` | ❌ Wave 0 |
| CONN-01 | injected conn never closed; self-managed closes | unit | `uv run pytest tests/test_backend_ladybug.py::test_ownership -x` | ❌ Wave 0 |
| CONN-02 | namespace isolation; sole-writer subgraph | unit | `uv run pytest tests/test_backend_ladybug.py::test_namespace_isolation -x` | ❌ Wave 0 |
| CONN-03 | idempotent bootstrap (re-run safe); PK uniqueness | unit | `uv run pytest tests/test_backend_ladybug.py::test_bootstrap_idempotent -x` | ❌ Wave 0 |
| FORMAL-06 | throwaway `:memory:` per example; no bleed/locks | fixture | `uv run pytest -p no:randomly tests/test_backend_parity.py` | ❌ Wave 0 |
| D-02 | core + memory import with ladybug ABSENT | unit (AST + import) | `uv run pytest tests/test_import_purity.py -x` (extended) | ⚠️ EXTEND existing |
| SC4 | spike confirmations (DDL/tx/binds/traverse) | integration | `uv run pytest tests/test_ladybug_spike.py -x` | ❌ Wave 0 (optional — can be folded into backend tests) |

### Sampling Rate
- **Per task commit:** `uv run pytest -q` (full suite is fast — 17 existing tests in 0.17s)
- **Per wave merge:** `uv sync --dev --extra ladybug && uv run pytest` (both backends)
- **Phase gate:** full suite green in BOTH CI environments (base-isolation + ladybug) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` — parametrized `backend` fixture over `[InMemoryBackend, LadybugBackend]`; throwaway `lb.Database()` per example; skip the ladybug param when the driver is absent (`pytest.importorskip("ladybug")`).
- [ ] `tests/test_backend_parity.py` — the oracle-parity suite (diamond + cycle + over-bound chain), the BACK-03/D-05 guarantee.
- [ ] `tests/test_backend_ladybug.py` — ownership, namespace isolation, idempotent bootstrap, SC4 confirmations.
- [ ] `tests/test_backend_memory.py` — in-memory primitives standalone.
- [ ] `tests/test_import_purity.py` — EXTEND with import-isolation assertions (D-02): import `doxastica`, `doxastica.core`, `doxastica.backends.memory` and run `MemoryCore.in_memory()` with `ladybug` absent from `sys.modules` (use `monkeypatch`/subprocess to simulate absence, since ladybug IS installed in dev).

*Note on simulating absence:* ladybug is installed in dev, so the import-purity test cannot rely on a real `ImportError`. Use a subprocess with `ladybug` blocked (e.g. a `sys.meta_path` finder that raises for `ladybug`, or `python -c` with a stub), OR rely on the CI base-install job (Job 1) where ladybug is genuinely uninstalled. Recommend BOTH: an AST/import-graph assertion locally + the real base-install job in CI.

## Security Domain

> `security_enforcement` not disabled in config → included. Scope is narrow: this is an embedded, in-process library with no network/auth surface.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface (embedded library). |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | In-process; tenancy is logical (namespace), not a security boundary. |
| V5 Input Validation | **yes** | Namespace identifier regex guard (D-04); parameterized Cypher for ALL data; opaque `value` never interpreted (BACK-04 §6). |
| V6 Cryptography | no | No crypto in core. |

### Known Threat Patterns for {embedded Cypher adapter}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via interpolated data | Tampering | `parameters={...}` `$param` binds for all data (verified working); never interpolate values. |
| Cypher injection via namespace (the one interpolation point) | Tampering | `^[A-Za-z_][A-Za-z0-9_]*$` validation before interpolation (D-04); reject otherwise. |
| Injection via interpolated depth bound | Tampering | The bound is an `int` from the typed port signature; assert `>= 0`; never a string. |
| Opaque `value` as execution surface | Tampering/Elevation | Stored verbatim, JSON-encoded by the core, never eval'd or used to build queries (BACK-04 §6). |
| DoS via unbounded traversal cost | DoS | `traverse` returns the node SET (visited-set / ACYCLIC), not enumerated paths — avoids combinatorial blow-up; `max_depth` caps cost; `var_length_extend_max_depth` bounds engine recursion. |

## Sources

### Primary (HIGH confidence)
- **Live spike against installed `ladybug` 0.17.1 / Python 3.14.2** (this repo venv) — DDL `IF NOT EXISTS` idempotency, `$param` binds, `MERGE` upsert/edge idempotency, `BEGIN/COMMIT/ROLLBACK`, var-length traversal incl. the 30-hop cap + `var_length_extend_max_depth` config + ACYCLIC/SHORTEST modes, one-query frontier, connection close/double-close/persistence/multi-reader semantics, `py.typed` + basedpyright clean. (All `[VERIFIED]` claims trace here.)
- `src/doxastica/ports.py`, `protocol.py`, `models.py`, `errors.py`, `docs/backend-contract.md` — the Phase 1 contracts the adapters serve.
- `.planning/phases/02-.../02-CONTEXT.md` — the locked D-01..D-05 decisions.
- `pyproject.toml`, `.github/workflows/{ci,quality,pr}.yml`, `.python-version` — current packaging/CI baseline.

### Secondary (MEDIUM confidence)
- `https://docs.ladybugdb.com/cypher/query-clauses/match/` [CITED] — variable-length syntax, WALK/TRAIL/ACYCLIC modes, SHORTEST/ALL SHORTEST, the documented default 30-hop cap. Corroborated by the live spike.
- CLAUDE.md Ladybug section — connection API, transaction model, parameterized-Cypher discipline (some claims now superseded: typing, dep classification).

### Tertiary (LOW confidence)
- None relied upon — every load-bearing claim was verified live.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — ladybug installed & exercised; versions confirmed.
- Architecture: HIGH — patterns derived from locked D-01..D-05 + verified API behavior.
- Pitfalls: HIGH — each pitfall (30-cap, `$param` rejection, WALK vs ACYCLIC, typing, isolation) was triggered/observed directly.
- Packaging mechanics: MEDIUM-HIGH — uv extras + two-env CI are standard and grounded in the existing workflows; the exact CI YAML is a planning task.

**Research date:** 2026-06-15
**Valid until:** ~2026-07-15 (stable; re-verify only if `ladybug` minor version bumps — the 30-cap default and var-length grammar are the things most likely to shift).
</content>
</invoke>
