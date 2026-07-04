# Phase 2 Context: Backend Adapters & Schema Bootstrap (De-risking Spike)

**Created:** 2026-06-15
**Status:** Ready for planning
**Source:** `/gsd-discuss-phase 2 --assumptions` session (conversational; decisions transcribed here)
**Phase goal:** First real LadybugDB contact, verified before any belief logic stands on it.
BOTH backends standing behind the Phase 1 `BackendPort` — the `ladybug` reference adapter
(flexible connection, idempotent namespaced schema bootstrap) and the in-memory adapter
(which doubles as the Phase 7 oracle) — plus the `:memory:` test-harness scaffold every later
phase depends on. Confirms the LPG-primitive port survives contact with the real ladybug API.

**Requirements in scope:** BACK-02, BACK-03, CONN-01, CONN-02, CONN-03, FORMAL-06.

---

## Domain

This phase delivers the **storage substrate and the single traversal primitive**, not belief
*operations*. It builds two concrete `BackendPort` implementations + connection lifecycle +
idempotent namespaced DDL + the parametrized `conftest` harness, and it runs the SC4 spike that
confirms the Phase 1 port granularity survives the real `ladybug` API. The AGM operations
(`revise`/`expand`/`contract`), world-scope identity, `query_scope`, and the
`get_impact`/`get_scope_at` *behaviours* compose on this substrate in Phases 3–6 — they are
explicitly OUT of scope here.

**In scope:** both adapters; `MemoryCore` construction + connection ownership; idempotent
namespaced schema DDL; the `conftest` fixture parametrized over both backends; the SC4 spike
confirmation; just enough exercise of the five primitives to prove they work end-to-end.

**Out of scope (deferred to later phases):** all AGM logic (`revise`/`expand`/`contract` →
Phase 3); world-scope identity & bootstrap (Phase 3, SCOPE-01/02); `query_scope` (Phase 4);
`get_impact`/`get_scope_at` behaviour (Phases 5/6). Phase 2 builds the mechanism, not the
operations that compose on it. No `MemoryCore` AGM-operation bodies are written here — only
constructors, port wiring, and `unit_of_work` exercise.

---

## Canonical References (MANDATORY — read before research/planning)

| Ref | Path | Why it matters to Phase 2 |
|-----|------|---------------------------|
| Phase 1 backend port | `src/doxastica/ports.py` | **The contract both adapters implement.** The 5 LPG primitives (`upsert_node`/`add_edge`/`match_nodes`/`traverse`/`unit_of_work`), their exact signatures, and the `traverse → (reached, frontier)` shape with `max_depth=None ⇒ full closure`. Backend-blind by construction. |
| Phase 1 public protocol | `src/doxastica/protocol.py` | `BeliefStore` — what `MemoryCore` implements above the port. Not re-touched here beyond construction. |
| Phase 1 models | `src/doxastica/models.py` | Frozen pydantic models (`Scope`/`Belief`/`BeliefState`/`EdgeType`/`BeliefFilter`/`ImpactResult`). Adapters return raw `dict`s below the model layer; hydration is `MemoryCore`'s job. |
| Phase 1 errors | `src/doxastica/errors.py` | Where `BackendDependencyError` is added (D-02). |
| BACK-04 port contract | `docs/backend-contract.md` | The written constraints a conforming backend must satisfy (idempotency, append-only safety, cycle-safe traversal, atomic `unit_of_work`, value opacity). Both adapters must satisfy it. |
| Phase 1 decisions | `.planning/phases/01-protocol-backend-port-data-model-decisions/01-CONTEXT.md` | LPG-primitive rationale (§1), the named round-trip tension flagged for THIS spike, the closed property taxonomy (§3). |
| Phase 1 import-purity test | `tests/test_import_purity.py` | The discipline this phase EXTENDS (D-02): the core must stay driver-blind, now provably with ladybug absent. |
| Ladybug docs | https://docs.ladybugdb.com/ (Get Started, Python API, Transactions, Prepared statements) | The real API the SC4 spike validates: `IF NOT EXISTS` DDL, `BEGIN TRANSACTION`/`COMMIT`, `$param` binds, `$depth`/var-length patterns. |
| CLAUDE.md | `CLAUDE.md` | The Ladybug detail section + the runtime-dep constraint that **D-03 reverses** — must be updated by this phase. |

---

## Decisions

### D-01: `MemoryCore` follows the SQLAlchemy Engine pattern — minus pool, two-tier, and registry

The defining structural choice; it resolves the Phase 2 SC1 ambiguity (how `MemoryCore` relates
to the backends).

- **Canonical constructor takes the port, never a raw connection:** `MemoryCore(backend: BackendPort)`.
  `MemoryCore` is backend-agnostic and composes the port; it never holds an `lb.Connection`
  directly. (Maps to SQLAlchemy `Engine` holding a `Dialect`.)
- **Connection/path handling lives in named factory classmethods** (maps to `create_engine`):
  - `MemoryCore.in_memory()` → wires an `InMemoryBackend` (always-works default path).
  - `MemoryCore.open(path | ":memory:", *, namespace=...)` → builds a `LadybugBackend` that
    **self-manages** its connection (`owns_conn=True`).
  - `MemoryCore.from_connection(conn, *, namespace=...)` → wraps an **injected**
    `lb.Connection` it **never closes** (`owns_conn=False`; R19/CONN-01 tenancy). This is the
    SQLAlchemy `creator`/external-pool analog.
- **SC1's literal `MemoryCore(conn, namespace=...)` is the `from_connection` factory, NOT the
  canonical `__init__`.** The roadmap signature conflated factory with constructor; the Engine
  pattern un-conflates it. Planner: do not implement `__init__` to accept a raw connection.
- **Deliberately DROPPED from the SQLAlchemy pattern:** (a) the **connection pool** — ladybug is
  single-writer embedded; pooling is meaningless and counter to the "write-serialization for
  free" payoff; (b) the **Engine-vs-Connection two-tier** — that split exists only because of
  pooling; collapse to one object (`MemoryCore` is both factory home-base and operation surface;
  no `core.connect()`).
- **No URL/scheme registry (D-01a):** named classmethods only. The SQLAlchemy dialect registry
  earns its keep with N first/third-party dialects + plugins; we have 2 first-party backends.
  **Defer the registry unless it becomes unavoidable** (e.g. a backend count or plugin model
  that forces it). `conftest` parametrization (SC5) uses a plain
  `[LadybugBackend, InMemoryBackend]` list, not a registry lookup.

### D-02: Backend-driver import isolation — the core never imports a driver; only leaf backend modules do

The structural guarantee that future backends (Neo4j, SurrealDB) never inflict an `ImportError`
or an unwanted install on users who don't use them. Independent of the dependency table (D-03);
this is about the import graph.

- **`backends/` subpackage:**
  - `backends/memory.py` — `InMemoryBackend`, stdlib + pydantic only, **always importable**.
  - `backends/ladybug.py` — `LadybugBackend`, owns the **guarded** `import ladybug as lb`.
  - future `backends/neo4j.py`, `backends/surrealdb.py` slot in **purely additively** — zero
    blast radius on existing installs.
- **The core stays driver-blind:** `MemoryCore` (in `core.py`) uses **function-local imports**
  inside its factory classmethods, so importing `MemoryCore` never chain-loads a driver.
- **`__init__.py` and `backends/__init__.py` never chain-import a driver** (no
  `from .ladybug import *`). They may re-export the zero-dep `InMemoryBackend`.
- **Friendly failure:** each DB backend module guards its driver import and raises
  `errors.BackendDependencyError(ImportError)` with an actionable message
  (`pip install doxastica[ladybug]`) instead of a raw `ModuleNotFoundError`.
- **This is also the single basedpyright boundary** for the (likely-untyped) `ladybug` import —
  one module, one `# pyright: ignore` scope, as CLAUDE.md anticipated.
- **Extend `tests/test_import_purity.py`:** assert `doxastica`, `doxastica.core`, and
  `doxastica.backends.memory` import with **`ladybug` genuinely absent** from their module
  graph, and that `MemoryCore.in_memory()` works driver-free.

### D-03: Option B packaging — `pydantic` is the only required runtime dep; `ladybug` is the reference-backend extra

Aligns the dependency table with the Phase 1 seam: ladybug is the *reference* backend behind
`BackendPort`, not *the* substrate. **This REVERSES a documented CLAUDE.md constraint** — flagged
loudly below for the planner.

- **`[project.dependencies]` = `["pydantic>=2.11,<3"]` only.** Remove `ladybug` from required deps.
- **`[project.optional-dependencies]`:** `ladybug = ["ladybug>=0.17,<0.18"]`; an `all` extra; a
  placeholder note that future `neo4j`/`surrealdb` extras slot in here. (`ladybug` stays a
  *required* dep is NOT chosen — extras are opt-in only, so demoting it now avoids a future
  one-time break.)
- **Install surfaces:** `pip install doxastica` → pydantic + working in-memory backend (a usable,
  dependency-light AGM core); `pip install doxastica[ladybug]` → adds the reference backend.
- **No third *required* runtime dep** is introduced — extras are not required deps, so the
  original "only two libraries" spirit holds.
- **Two-environment CI (the payoff that gives D-02 teeth):**
  - Job 1: base install (pydantic only) → in-memory test subset **+ the import-purity test**,
    proving isolation with ladybug truly absent in CI.
  - Job 2: `doxastica[ladybug]` + dev group → full `conftest` suite parametrized over both
    backends.
  - Dev/spike work installs `[ladybug]` + dev group — no friction.
- **[BLOCKING] CLAUDE.md update is part of this phase.** Update at minimum:
  - "Runtime deps **exactly `ladybug` + `pydantic`**" → "**pydantic** required; **ladybug** is the
    reference-backend extra (`doxastica[ladybug]`); future backends are extras."
  - "**Storage: pinned to LadybugDB**" / "no storage abstraction" framing → note it is superseded
    by the Phase 1 `BackendPort` decision; ladybug is the **reference** backend, not the only one.
  - Treat this as a decision-grade reversal recorded here (sibling to the Phase 1 §2 3.14-floor
    decision), not a silent edit.

### D-04: Ladybug adapter ownership, schema bootstrap, and namespace-identifier safety (CONN-02, CONN-03)

- **The ladybug backend is the sole writer of its namespaced closed subgraph** (CONN-02): its
  `:<ns>_Scope` / `:<ns>_Belief` / `:<ns>_BeliefState` node tables and edge types, with no
  outbound graph references.
- **Schema bootstrap runs idempotently on init** (CONN-03): `CREATE NODE/REL TABLE IF NOT EXISTS
  <ns>_*`, safe to re-run against a fresh OR shared injected DB.
- **Namespace-identifier safety:** DDL table *identifiers* cannot be `$param`-bound, so the
  namespace must be string-interpolated into the DDL. The namespace MUST be validated as a safe
  identifier (e.g. `^[A-Za-z_][A-Za-z0-9_]*$`) before interpolation — this is the one place the
  "always parameterize" rule cannot apply, so it gets an explicit guard, not an exception.
- **Adapters return raw `list[dict]` below the model layer**; `MemoryCore` hydrates into frozen
  pydantic models and JSON-encodes the opaque `value`. Keep the port model-blind.

### D-05: In-memory backend is a first-class shipping product AND the Phase 7 oracle (BACK-03, FORMAL-06)

- `InMemoryBackend` implements the SAME `BackendPort` with zero extra dependency; its `traverse`
  is the visited-set BFS the port doc names as the reference implementation.
- **Oracle parity is a hard requirement:** in-memory `traverse`/`match_nodes` semantics must match
  the ladybug backend exactly, or Phase 7's shadow-model comparison is built on sand. The
  parametrized `conftest` (SC5) is the mechanism that keeps them honest from day one.

---

## Code Context

Phase 1 shipped: `ports.py` (BackendPort), `protocol.py` (BeliefStore), `models.py` (frozen
models), `errors.py`, `docs/backend-contract.md`, and `tests/test_import_purity.py` /
`tests/test_port_distinct.py`. `pyproject.toml` currently lists `ladybug` as a **required** dep
(line 12) — D-03 moves it to `[project.optional-dependencies]`. `tests/conftest.py` is a stub —
this phase fills it (SC5). No `backends/` subpackage yet — this phase creates it (D-02). No
`core.py`/`MemoryCore` yet — this phase creates the constructors + factories (D-01), no AGM ops.

---

## Deferred Ideas

- **URL/scheme backend registry** — deferred unless the backend count or a plugin model forces it
  (D-01a). Named classmethods suffice for 2 first-party backends.
- **Keeping `ladybug` as a default-installed dep** — rejected in favour of Option B (D-03); the
  in-memory backend covers the dependency-light path.
- **AGM operations, world-scope identity, retrieval, edge/impact behaviour** — Phases 3–6, per
  the roadmap dependency graph.

---

## Open Questions Carried into Planning (the SC4 spike)

The spike must confirm, against the **installed `ladybug` package**, and document any workaround:

1. `CREATE ... IF NOT EXISTS` DDL syntax (idempotent bootstrap, CONN-03).
2. Multi-statement `BEGIN TRANSACTION` / `COMMIT` issued through `conn.execute` (atomic
   `unit_of_work`).
3. `$param` binds for data (the required, non-interpolated style).
4. `$depth` inside variable-length traversal patterns — **prior: Kùzu lineage likely wants a
   literal int bound, not a `$param`**, so the pre-authorized validated-int workaround is probably
   needed; the workaround, if used, lives inside `LadybugBackend.traverse`, invisible to
   `MemoryCore`.
5. **Unbounded cycle-safe reachable-set** (`max_depth=None ⇒ full closure`) expressible in ONE
   efficient query — Kùzu var-length patterns historically want an upper bound. In-memory does
   this trivially. **If ladybug cannot, the port default/abstraction adjusts NOW** (the named
   round-trip tension; SC4 is where it resolves).
6. Confirm `get_impact`/`get_scope_at` do not force an unacceptable number of round-trips under
   the LPG-primitive port. The port is adjusted in this phase if the spike demands it.

---

*Phase: 02-backend-adapters-schema-bootstrap-de-risking-spike*
*Context captured: 2026-06-15 via /gsd-discuss-phase 2 --assumptions (transcribed)*
