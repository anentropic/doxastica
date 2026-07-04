# Phase 2: Backend Adapters & Schema Bootstrap (De-risking Spike) - Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 11 (3 new src modules, 1 new src package init, 2 modified src modules, 4 new/modified test files, pyproject + CI)
**Analogs found:** 11 / 11 (every new file has a strong same-repo analog; this is a mature Phase-1 codebase)

The repo has a single, consistent house style established across all Phase-1 modules:
a long module-level docstring tying the module to its decision IDs (DATA-xx / BACK-xx /
CONN-xx), `from __future__ import annotations` + `TYPE_CHECKING`-gated imports in the seam
modules, frozen pydantic models, NumPy-less Google-ish docstrings, and AST-based discipline
tests. New Phase-2 files copy that style directly. There is no "find a vaguely-similar file"
gap here — analogs are exact.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/doxastica/core.py` (NEW) | service / engine | request-response (composes port) | `src/doxastica/protocol.py` (module style) + `src/doxastica/ports.py` (the port it composes) | role-match |
| `src/doxastica/backends/__init__.py` (NEW) | package init | n/a | `src/doxastica/__init__.py` | exact |
| `src/doxastica/backends/memory.py` (NEW) | adapter (oracle) | CRUD + transform (BFS) | `src/doxastica/ports.py` (the contract) + `src/doxastica/models.py` (frozen/style) | role-match (implements the Protocol) |
| `src/doxastica/backends/ladybug.py` (NEW) | adapter (driver) | CRUD + transform (Cypher) | `src/doxastica/ports.py` (the contract) | role-match (implements the Protocol) |
| `src/doxastica/errors.py` (MODIFY) | error module | n/a | `src/doxastica/errors.py` itself (existing classes) | exact |
| `src/doxastica/__init__.py` (MODIFY) | package init | n/a | `src/doxastica/__init__.py` itself | exact |
| `tests/conftest.py` (MODIFY) | test fixture | n/a | (stub today) — style from `tests/test_import_purity.py` + RESEARCH conftest design | role-match |
| `tests/test_import_purity.py` (MODIFY) | test (AST/import) | n/a | `tests/test_import_purity.py` itself (parametrized AST scan) | exact |
| `tests/test_backend_*.py` (NEW: memory / ladybug / parity) | test (integration/unit) | n/a | `tests/test_port_distinct.py` (assertion style) | role-match |
| `pyproject.toml` (MODIFY) | config | n/a | `pyproject.toml` itself (`[project.dependencies]`, `[dependency-groups]`) | exact |
| `.github/workflows/quality.yml` (MODIFY) + CI | config | n/a | `.github/workflows/quality.yml` (matrix + `uv sync` steps) | exact |

## Pattern Assignments

### `src/doxastica/core.py` (service/engine, request-response) — NEW

**Analog:** `src/doxastica/protocol.py` (module-docstring + `__future__`/`TYPE_CHECKING` style), composing `src/doxastica/ports.py`.

**Module docstring + future-import + TYPE_CHECKING style** (`protocol.py:1-39`):
```python
"""
<long docstring tying the module to its decision IDs; explain the Engine pattern
(D-01), the driver-blind rule (D-02), and that NO AGM operation bodies are written
here — only constructors + factory wiring + unit_of_work exercise>.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from doxastica.ports import BackendPort
    # NOTE (D-02): do NOT import ladybug here, even under TYPE_CHECKING — function-local
    # imports inside the open()/from_connection() factories keep core.py driver-blind.
```

**Engine constructor + factory pattern** (D-01 — derived; no in-repo analog, follow SQLAlchemy-minus-pool shape from RESEARCH Pattern 1):
```python
class MemoryCore:
    """<docstring: backend-agnostic; composes a BackendPort; never holds an lb.Connection>."""

    def __init__(self, backend: BackendPort) -> None:
        # Canonical constructor takes the PORT, never a raw connection (D-01).
        self._backend = backend

    @classmethod
    def in_memory(cls) -> MemoryCore:
        from doxastica.backends.memory import InMemoryBackend   # function-local (D-02)
        return cls(InMemoryBackend())

    @classmethod
    def open(cls, path: str, *, namespace: str = "dx") -> MemoryCore:
        from doxastica.backends.ladybug import LadybugBackend   # function-local (D-02)
        return cls(LadybugBackend.open(path, namespace=namespace))  # owns_conn=True

    @classmethod
    def from_connection(cls, conn: object, *, namespace: str = "dx") -> MemoryCore:
        from doxastica.backends.ladybug import LadybugBackend   # function-local (D-02)
        return cls(LadybugBackend(conn, namespace=namespace, owns_conn=False))  # R19
```
**Load-bearing constraint:** the `from ...ladybug import` statements MUST be inside method
bodies, not at module top. The extended `test_import_purity.py` proves this by scanning
MODULE-LEVEL imports only — a top-level (or `TYPE_CHECKING`-block) ladybug import is a build
failure, while these sanctioned function-local imports are explicitly permitted and MUST NOT
be flagged.

**Do NOT** implement `__init__` to accept a raw connection (D-01 — `from_connection` is the
factory for that). **Do NOT** write `revise`/`expand`/`contract`/`query_scope`/`get_impact`
bodies (Phases 3-6). Model hydration (raw `dict` → frozen pydantic, JSON-encode `value`)
is core.py's job per D-04, but only the wiring needed for the `unit_of_work` exercise.

---

### `src/doxastica/backends/__init__.py` (package init) — NEW

**Analog:** `src/doxastica/__init__.py` (`__init__.py:1-26`).

**Pattern** — short docstring, explicit imports, `__all__` sorted:
```python
"""Backend adapters behind the BackendPort seam (Phase 2)."""

from doxastica.backends.memory import InMemoryBackend

__all__ = ["InMemoryBackend"]
```
**Load-bearing (D-02):** re-export ONLY the zero-dep `InMemoryBackend`. NEVER
`from .ladybug import ...` here — that would chain-load the driver and break isolation.

---

### `src/doxastica/backends/memory.py` (adapter/oracle, CRUD+transform) — NEW

**Analog:** `src/doxastica/ports.py` (the five-primitive contract, `ports.py:69-115`) for the
exact method signatures it must implement; `src/doxastica/models.py` for docstring/frozen style.

**The five signatures to implement verbatim** (copy from `ports.py:69-115`):
```python
def upsert_node(self, label: str, node_id: UUID | str, props: dict[str, Any]) -> None: ...
def add_edge(self, edge_type: EdgeType | str, from_id: UUID | str, to_id: UUID | str,
             props: dict[str, Any] | None = None) -> None: ...
def match_nodes(self, label: str, where: dict[str, Any]) -> list[dict[str, Any]]: ...
def traverse(self, start: UUID | str, edge_types: frozenset[EdgeType | str],
             max_depth: int | None,
             ) -> tuple[list[dict[str, Any]], frozenset[UUID | str]]: ...
def unit_of_work(self) -> AbstractContextManager[None]: ...
```

**Core BFS pattern (the oracle, D-05)** — from RESEARCH "In-Memory Backend" §:
```python
def traverse(self, start, edge_types, max_depth):
    reached, frontier, seen, layer = {}, set(), {start}, [(start, 0)]
    while layer:
        nxt = []
        for nid, depth in layer:
            for to in self._out_edges(nid, edge_types):
                if to in seen:
                    continue
                if max_depth is not None and depth + 1 > max_depth:
                    frontier.add(nid)        # node at the bound with an unexpanded successor
                    continue
                seen.add(to); reached[to] = self._nodes[to]; nxt.append((to, depth + 1))
        layer = nxt
    return list(reached.values()), frozenset(frontier)
```
**Load-bearing parity note (D-05):** frontier = "node at exactly `max_depth` with an
unexpanded successor"; `max_depth=None` ⇒ empty frontier. This MUST match `ladybug.py`
exactly — `test_backend_parity.py` asserts identical `(reached, frontier)`.
**Data structures:** stdlib `dict[id, props]` for nodes + adjacency lists for edges; stdlib +
pydantic only (no third dep). `unit_of_work` is a `contextlib.contextmanager` over a snapshot
or no-op-on-success / restore-on-error (atomic semantics; the in-memory tx is logical).

---

### `src/doxastica/backends/ladybug.py` (adapter/driver, CRUD+transform) — NEW

**Analog:** `src/doxastica/ports.py` (same five signatures as memory.py). This is the SINGLE
basedpyright + driver-import boundary (D-02).

**Guarded driver import** (RESEARCH Pattern 2 — top of module):
```python
from doxastica import errors

try:
    import ladybug as lb
except ImportError as exc:  # pragma: no cover - exercised in base-install CI (Job 1)
    raise errors.BackendDependencyError(
        "The ladybug backend requires the 'ladybug' package. "
        "Install it with:  pip install doxastica[ladybug]"
    ) from exc
```
**Load-bearing (Pitfall 4):** ladybug ships `py.typed` — do NOT add
`# pyright: ignore[reportMissingTypeStubs]`. The only typing task is narrowing
`Connection.execute`'s `QueryResult | list[QueryResult]` return (one `isinstance`/helper).

**Ownership flag + namespace guard + idempotent bootstrap** (RESEARCH Patterns 1, 3, 4):
```python
import re
_NS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def __init__(self, conn, *, namespace: str, owns_conn: bool) -> None:
    if not _NS_RE.match(namespace):                       # D-04: the ONE interpolation guard
        raise ValueError(f"namespace must match {_NS_RE.pattern!r}; got {namespace!r}")
    self._conn, self._ns, self._owns_conn = conn, namespace, owns_conn
    self._bootstrap_schema()                              # CONN-03 idempotent DDL

def close(self) -> None:
    if self._owns_conn:                                  # R19: never close an injected handle
        self._conn.close()
```
Schema DDL: `CREATE NODE/REL TABLE IF NOT EXISTS {ns}_*` (RESEARCH Pattern 4, verified
idempotent). `{self._ns}` is the ONLY interpolated identifier; all data uses `$param`.

**traverse — the SC4 resolution** (RESEARCH Pattern 5): `CALL var_length_extend_max_depth=<bound>`
then `-[:{rels}* ACYCLIC 1..{bound}]->`, `max_depth=None ⇒ _DEPTH_CEILING = 1_000_000`,
`(reached, frontier)` from one query via `min(length(p))` + `EXISTS{}`. The depth bound is an
interpolated validated `int` (`$param` is rejected inside `*1..` — Pitfall 2), NOT a string.
Row extraction: `conn.execute(cy, parameters={...}).rows_as_dict().get_all()`.
`upsert_node`→`MERGE ... SET`; `add_edge`→`MERGE` (NOT `CREATE` — Pitfall/anti-pattern).
`unit_of_work`→`BEGIN TRANSACTION`/`COMMIT`/`ROLLBACK` via `execute` (RESEARCH Code Examples).

---

### `src/doxastica/errors.py` (error module) — MODIFY

**Analog:** the existing classes in the same file (`errors.py:9-14`).

**Existing pattern** (one-line class, one-line docstring, subclass the right base):
```python
class DoxasticaError(Exception):
    """Base class for all doxastica errors."""

class WorldScopeContractionError(DoxasticaError):
    """Raised when ``contract()`` is attempted on a privileged world scope."""
```

**Add (D-02)** — note the DOUBLE base so callers can catch either `DoxasticaError` or `ImportError`:
```python
class BackendDependencyError(DoxasticaError, ImportError):
    """Raised when a backend's optional driver is not installed (e.g. ``doxastica[ladybug]``)."""
```
The header docstring (`errors.py:1-6`) currently says "Phase 1 only *types* the surface" —
update that prose to note Phase 2 adds the backend-dependency error.

---

### `src/doxastica/__init__.py` (package init) — MODIFY

**Analog:** the file itself (`__init__.py:1-26`) — alphabetically-sorted explicit imports + `__all__`.

**Add** (keep driver-blind — D-02): export `MemoryCore` (from `doxastica.core`) and
`InMemoryBackend` (from `doxastica.backends.memory`), plus `BackendDependencyError`. Insert
each into the existing import block and the sorted `__all__` list. NEVER import `LadybugBackend`
or `ladybug` here — `core.py` and `backends/memory.py` are both driver-free, so this stays clean.

---

### `tests/conftest.py` (test fixture) — MODIFY (fill the stub)

**Analog:** style from `tests/test_import_purity.py` (parametrize usage) + RESEARCH Validation
Architecture / Wave-0 Gaps.

**Pattern** — parametrized `backend` fixture over both backends, throwaway DB per example,
skip ladybug when driver absent:
```python
import pytest

@pytest.fixture(params=["memory", "ladybug"])
def backend(request):
    if request.param == "ladybug":
        lb = pytest.importorskip("ladybug")          # skip param when driver absent (Job 1)
        from doxastica.backends.ladybug import LadybugBackend
        conn = lb.Connection(lb.Database())          # fresh :memory: DB per example (FORMAL-06)
        be = LadybugBackend(conn, namespace="dx", owns_conn=True)
        yield be
        be.close()
    else:
        from doxastica.backends.memory import InMemoryBackend
        yield InMemoryBackend()
```
**Load-bearing (D-01a):** plain `params=[...]` list, NOT a registry lookup.
**Load-bearing (FORMAL-06):** construct a fresh `lb.Database()` (None path) PER fixture call —
do not share one across examples (Pitfall 5: state bleed / lock errors).

---

### `tests/test_import_purity.py` (test, AST/import) — EXTEND

**Analog:** the file itself (`test_import_purity.py:14-34`) — parse each module, collect
`ast.Import`/`ast.ImportFrom`, assert no offender whose first dotted component is `ladybug`.

**CRITICAL — the scan must become MODULE-LEVEL only (do NOT reuse `ast.walk` as-is):**
The existing scan uses `ast.walk`, which recurses into function bodies. For `protocol`/`ports`
that is harmless (they have no function-local imports). But `core.py`'s `open`/`from_connection`
factories DELIBERATELY place `from doxastica.backends.ladybug import LadybugBackend` INSIDE the
method bodies (D-02 — function-local imports keep the module driver-blind). An `ast.walk` scan
would flag those legitimate function-local imports as offenders and fail the test. So when adding
`core` and `backends/memory` to the scan, the collection logic MUST inspect MODULE-LEVEL imports
only.

**Module-level collection pattern to use** (replaces the `ast.walk` loop):
```python
def _module_level_imports(tree: ast.Module) -> list[str]:
    """Collect imports at module scope only: top-level + TYPE_CHECKING-block imports.

    Deliberately ignores imports nested inside function/method bodies — core.py's
    factories use sanctioned function-local ladybug imports (D-02) that the contract
    PERMITS, so the driver-blind scan must not see them.
    """
    nodes: list[ast.stmt] = list(tree.body)
    # Descend into module-level `if TYPE_CHECKING:` blocks (and their else), but NOT
    # into FunctionDef / AsyncFunctionDef / ClassDef-method bodies.
    for stmt in tree.body:
        if isinstance(stmt, ast.If) and _is_type_checking_test(stmt.test):
            nodes += [*stmt.body, *stmt.orelse]

    imported: list[str] = []
    for node in nodes:
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported
```
(`_is_type_checking_test` matches a bare `TYPE_CHECKING` name or a `typing.TYPE_CHECKING`
attribute. An equivalent acceptable approach is to keep `ast.walk` but skip any import node
nested under a `FunctionDef`/`AsyncFunctionDef`.) The offender assertion is unchanged:
```python
offenders = [name for name in imported if name.split(".")[0] == "ladybug"]
assert not offenders, f"{module}.py must not import ladybug; found: {offenders}"
```

**Extend (D-02)** two ways:
1. **Static module-level scan** — add `core` and `backends/memory` to the
   `@pytest.mark.parametrize` module list (they join `protocol`, `ports`), and switch the scan to
   the module-level collection above. The assertion then catches a top-level OR
   `TYPE_CHECKING`-block ladybug import in `core.py` / `backends.memory` (the real violations),
   while NOT flagging `MemoryCore`'s deliberate function-local ladybug imports. Update the module
   docstring accordingly: it inspects MODULE-LEVEL imports only and intentionally ignores
   function-local imports (REMOVE the prior claim that function-body imports are caught — that is
   no longer true and would mis-describe the contract).
2. **Runtime absence** — assert `import doxastica`, `import doxastica.core`,
   `import doxastica.backends.memory` and `MemoryCore.in_memory()` succeed with `ladybug`
   genuinely absent from `sys.modules`. Per RESEARCH §"simulating absence": ladybug IS
   installed in dev, so use a subprocess with a `sys.meta_path` finder that raises for
   `ladybug` (or `python -c` stub), AND rely on the CI base-install Job 1. Recommend BOTH; this
   subprocess test plus CI Job 1 are the independent proofs of D-02 isolation.

---

### `tests/test_backend_memory.py` / `test_backend_ladybug.py` / `test_backend_parity.py` (tests) — NEW

**Analog:** `tests/test_port_distinct.py` (`test_port_distinct.py:19-37`) — small, focused
functions, docstring naming the requirement ID, direct `assert` with an actionable message.

**Assertion + docstring style to copy** (`test_port_distinct.py:33-36`):
```python
def test_backend_port_exposes_the_five_primitives() -> None:
    """The port surface is exactly the five decided LPG primitives."""
    for primitive in ("upsert_node", "add_edge", "match_nodes", "traverse", "unit_of_work"):
        assert hasattr(BackendPort, primitive), f"missing primitive: {primitive}"
```

**Test map (RESEARCH Validation Architecture):**
- `test_backend_memory.py` — each of the 5 primitives standalone (BACK-03).
- `test_backend_ladybug.py` — `test_ownership` (CONN-01: injected never closed; self-managed
  closes), `test_namespace_isolation` (CONN-02), `test_bootstrap_idempotent` (CONN-03: re-run
  safe), SC4 confirmations (DDL/tx/binds/traverse). Gate the whole module on
  `pytest.importorskip("ladybug")`.
- `test_backend_parity.py` — the oracle-parity suite (D-05/BACK-03): use the parametrized
  `backend` fixture; assert identical `(reached, frontier)` and `match_nodes` from both
  backends on a **diamond + cycle + over-bound chain** (RESEARCH Open Question 1). This is the
  hard parity guarantee — a first-class Phase-2 test, NOT deferred to Phase 7.

---

### `pyproject.toml` (config) — MODIFY (D-03, Option B)

**Analog:** the file itself (`pyproject.toml:10-13` dependencies; `:19-28` dependency-groups).

**Current** (`pyproject.toml:10-13`):
```toml
dependencies = [
    "pydantic>=2.11,<3",
    "ladybug>=0.17,<0.18",
]
```
**Change to** (D-03): `dependencies = ["pydantic>=2.11,<3"]` only; add:
```toml
[project.optional-dependencies]
ladybug = ["ladybug>=0.17,<0.18"]
all = ["doxastica[ladybug]"]
# future: neo4j = [...], surrealdb = [...]
```
**Follow-on (RESEARCH Runtime State Inventory):** re-run `uv lock` and commit `uv.lock`
(the prek `uv-lock` hook enforces it). The `[tool.pyright]`/`[tool.ruff]` blocks are unchanged.

---

### `.github/workflows/quality.yml` (+ CI) (config) — MODIFY (D-03 two-env CI)

**Analog:** `quality.yml:9-44` — `matrix.python-version: ["3.14"]`, `astral-sh/setup-uv@v7`,
`uv sync --locked --dev`, `uv run pytest`, cache-prune-on-`always()`.

**Existing sync+test steps to copy** (`quality.yml:30-44`):
```yaml
      - name: Sync dependencies
        run: uv sync --locked --dev
      - name: Tests
        run: uv run pytest
      - name: Cache pruning
        if: always()
        run: uv cache prune --ci
```
**Change (D-03):** split into two jobs / matrix legs reusing the same step skeleton:
- **Job 1 (isolation):** `uv sync --no-default-groups` (or base install — ladybug ABSENT) →
  run `tests/test_import_purity.py` + the in-memory subset. Proves D-02 with ladybug truly gone.
- **Job 2 (full):** `uv sync --locked --dev --extra ladybug` → full both-backend conftest suite.
Keep `runs-on: ubuntu-latest`, `setup-uv@v7` (`enable-cache`, `cache-dependency-glob: uv.lock`),
`permissions: contents: read`, `fail-fast: false`. `pr.yml` coverage job also needs `--extra
ladybug` to exercise both backends.

## Shared Patterns

### Module docstring + decision-ID provenance
**Source:** every Phase-1 module (`ports.py:1-43`, `protocol.py:1-24`, `models.py:1-22`,
`errors.py:1-6`).
**Apply to:** all new src modules (`core.py`, `backends/*.py`).
Each module opens with a docstring naming the decision IDs it realizes (D-01..D-05 / CONN-xx /
BACK-xx) and what it deliberately does NOT do (e.g. "no AGM operation bodies — Phases 3-6").

### Backend-blind / driver-blind import discipline
**Source:** `protocol.py:6-11` (the prose contract) + `tests/test_import_purity.py` (the AST gate).
**Apply to:** `core.py`, `__init__.py`, `backends/__init__.py`, `backends/memory.py`.
NEVER place a MODULE-LEVEL `import ladybug` (top-level or under `TYPE_CHECKING`) outside
`backends/ladybug.py`. core.py uses sanctioned FUNCTION-LOCAL imports in its factories — those
are PERMITTED and the gate must not flag them. Mechanically enforced by the extended
MODULE-LEVEL AST scan (which inspects top-level + TYPE_CHECKING-block imports only) plus the
runtime-absence subprocess test.

### `from __future__ import annotations` + `TYPE_CHECKING`-gated imports
**Source:** `ports.py:45-53`, `protocol.py:26-39`.
**Apply to:** `core.py` (and any new typed module under strict basedpyright). Keep runtime
imports minimal; push type-only imports under `if TYPE_CHECKING:`.

### Frozen pydantic + closed taxonomy (when modeling)
**Source:** `models.py:58-123` (`BaseModel, frozen=True, extra="forbid"`).
**Apply to:** any value object the backends emit/consume — but note D-04: backends return raw
`list[dict]` BELOW the model layer; hydration into frozen models is `MemoryCore`'s job, not the
adapters'. Keep the port model-blind.

### Discipline tests (AST scan + `hasattr` surface assertions)
**Source:** `test_import_purity.py:20-34`, `test_port_distinct.py:19-37`.
**Apply to:** `test_import_purity.py` extension and the new backend tests — small functions,
requirement-ID docstrings, `assert ..., f"actionable message"`. NOTE: the import-purity scan
must be MODULE-LEVEL (not `ast.walk` into function bodies) once `core` joins it — see the EXTEND
section above.

### Parameterized-Cypher / single-interpolation-point discipline (ladybug only)
**Source:** RESEARCH Pattern 3 + Security Domain; CLAUDE.md "string-interpolated Cypher
strongly discouraged".
**Apply to:** `backends/ladybug.py` ONLY. All data → `$param`. The ONLY two sanctioned
interpolations are the regex-validated `{namespace}` identifier and the validated `int` depth
bound (both impossible to `$param`-bind in Kùzu-lineage Cypher).

## No Analog Found

None. Every Phase-2 file maps to a same-repo analog for style and (for the adapters) to
`ports.py` for the contract. The only genuinely new *shapes* are the `MemoryCore` Engine/factory
class (no class-with-classmethod-factories exists yet in the repo) and the parametrized backend
fixture (conftest is currently a stub) — both fully specified by the locked decisions + the live
SC4 spike results in RESEARCH (Patterns 1-5, Code Examples), so the planner has concrete
templates rather than a gap to invent into.

## Metadata

**Analog search scope:** `src/doxastica/` (all modules), `tests/` (all test files + conftest),
`.github/workflows/`, `docs/backend-contract.md`, `pyproject.toml`.
**Files scanned:** 13 (5 src modules, 4 test files, 3 CI workflows, pyproject, backend-contract).
**Pattern extraction date:** 2026-06-15
