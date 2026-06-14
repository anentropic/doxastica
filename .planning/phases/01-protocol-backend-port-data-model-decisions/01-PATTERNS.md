# Phase 1: Protocol, Backend Port & Data-Model Decisions - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 10 (8 new source/doc files + 2 scaffold-config edit targets)
**Analogs found:** 0 in-repo / 10 — **this is a greenfield phase.** No `src/`, no `.py`, no `pyproject.toml` exist in the doxastica repo. The closest real reference is the locally-present `cookiecutter-python-uv-library` template (the PKG-01 scaffold source) plus the RESEARCH.md Code Examples (grounded verbatim in the sibling `narrative-vm` design docs). Where no analog exists, this document says so explicitly and points at the legitimate reference instead.

---

## Greenfield Notice (read first)

There is **nothing in the doxastica repo to copy patterns from** — verified: only `.planning/`, `CLAUDE.md`, `LICENSE`, `README.md` exist; no `src/`, no test files, no `pyproject.toml`. Do not expect in-repo analogs for `protocol.py`, `models.py`, `ports.py`, etc. — they do not exist yet and this phase creates them.

Two legitimate, locally-verified references exist and are used throughout this map:

1. **The cookiecutter template** at `/Users/paul/Documents/Dev/Personal/cookiecutter-python-uv-library/` — the actual PKG-01 scaffold source. Its rendered files (`pyproject.toml`, `__init__.py`, `tests/`, CI workflows, pre-commit) are the *structural/config* analog for the scaffold and tooling tasks. **These are Jinja templates** (`{{ cookiecutter.* }}`); the planner reads them to know what the rendered output and its defaults will be, then patches the post-render output per CONTEXT decisions.
2. **RESEARCH.md "Code Examples"** (lines 313–443) — the typed-surface reference for `protocol.py`, `models.py`, `ports.py`, and the import-purity test. These are not in-repo analogs; they are the design-doc-grounded target surfaces (sourced from `05-nvm-memory-core.md §3` / `21-nvm-component-architecture.md §4`, refined per CONTEXT decisions #4 and #5). Treat them as the canonical shape to implement.

A short, honest map is the goal. No analogs were fabricated.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `pyproject.toml` (+ scaffold tree) | config / scaffold | n/a | `cookiecutter.../{{ ... }}/pyproject.toml` | template (rendered, then patched) |
| `src/doxastica/__init__.py` | package init / re-export barrel | n/a | `cookiecutter.../src/{{ package_name }}/__init__.py` | template (skeleton only — empty `__all__`) |
| `src/doxastica/models.py` | model (typed value layer) | transform (validation at seam) | RESEARCH.md Code Examples (frozen pydantic block) | reference-surface (no in-repo analog) |
| `src/doxastica/protocol.py` | protocol (public seam) | request-response (interface contract) | RESEARCH.md Code Examples (`BeliefStore` block) | reference-surface (no in-repo analog) |
| `src/doxastica/ports.py` (name TBD) | port (internal seam Protocol) | CRUD + traversal primitives | RESEARCH.md Code Examples (`BackendPort` block) | reference-surface (no in-repo analog) |
| `src/doxastica/errors.py` | utility (typed exception surface) | n/a | none — standard Python exception-class idiom | no analog (use idiom) |
| `src/doxastica/py.typed` | config (type marker) | n/a | `cookiecutter.../src/{{ package_name }}/py.typed` | template (copied verbatim, `_copy_without_render`) |
| `docs/backend-contract.md` | doc (BACK-04 spec) | n/a | RESEARCH.md "Backend Port Contract" (7 constraints) | reference-content (no in-repo analog) |
| `tests/test_import_purity.py` | test (DATA-01 guard) | n/a | RESEARCH.md import-purity example + `cookiecutter.../tests/test_*.py` skeleton | reference-surface + template |
| `tests/test_models_frozen.py` | test (DATA-06 guard) | n/a | `cookiecutter.../tests/test_*.py` skeleton (style only) | template (style) |

**Scaffold-config edit targets** (rendered by the template, then patched per CONTEXT — see "Scaffold Patch List"):
- `pyproject.toml` (`requires-python`, `dependencies`, `[tool.basedpyright]` block, dev-group `hypothesis`)
- `.github/workflows/quality.yml` + `release.yml` (drop the matrix floor → 3.14-only)
- `.python-version`

---

## Pattern Assignments

### `pyproject.toml` (config / scaffold) — and the whole scaffold tree

**Analog:** `/Users/paul/Documents/Dev/Personal/cookiecutter-python-uv-library/{{ cookiecutter.project_slug }}/pyproject.toml` (rendered output of the PKG-01 scaffold).

**Scaffold prompt answers** (from `cookiecutter.json`, lines 1–30) — the planner runs cookiecutter with these:
- `project_name` → "doxastica" (so `project_slug` = `doxastica`, `package_name` = `doxastica`)
- `author_name`/`author_email` defaults already match the user (`Anentropic` / `ego@anentropic.com`)
- `python_version` default `3.14` (correct); `minimum_python_version` default **`3.11` — MUST override to `3.14`** per CONTEXT decision #2
- `license` → `MIT`
- `docs_framework` → `mkdocs-material` (CLAUDE.md chose this)

**Rendered template structure** (template lines 1–71) — note these template-vs-target deltas:

```toml
[project]
name = "{{ cookiecutter.project_slug }}"          # → doxastica
requires-python = ">={{ cookiecutter.minimum_python_version }}"   # → ">=3.14"  (decision #2)
dependencies = []                                  # → ["pydantic>=2.11,<3", "ladybug>=0.17,<0.18"]

[build-system]
requires = ["uv_build>=0.9.18,<1.0.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [ "basedpyright>=1.38.0", "ipython>=9.10.0", "pdbpp>=0.12.0.post1",
        "pytest>=8.0.0", "pytest-cov>=6.0.0", "ruff>=0.15.1" ]
#   → ADD "hypothesis>=6.155" to dev (declared now, exercised Phase 7)
```

**IMPORTANT typing-config gotcha** (template line 47): the template emits **`[tool.pyright]`**, not `[tool.basedpyright]`:
```toml
[tool.pyright]
pythonVersion = "{{ cookiecutter.python_version }}"   # → "3.14"
typeCheckingMode = "strict"
include = ["src", "tests"]
reportPrivateUsage = false
```
basedpyright reads the `[tool.pyright]` table, so this works as-is for strict checking. CLAUDE.md mentions a possible narrowly-scoped `[[tool.basedpyright.executionEnvironments]]` — that is a **Phase 2** concern (the `ladybug` adapter boundary), **not Phase 1** (Phase 1 imports no `ladybug`, so strict passes clean). Do not add it now.

**Ruff config** (template lines 53–67): rule set `["E","F","W","I","UP","B","SIM","TCH","D"]`, `line-length = 100`, `target-version = py{{ minimum_python_version | replace('.','') }}` → becomes `py314` after the floor override. Keep the template's `D1`/`D2xx` ignores.

---

### `src/doxastica/__init__.py` (package init / re-export barrel)

**Analog:** `cookiecutter.../src/{{ package_name }}/__init__.py` — this is a **skeleton only**:
```python
"""{{ cookiecutter.project_short_description }}."""

__all__ = []
```
Pattern to copy: module docstring + an `__all__` list. Phase 1 populates `__all__` with the public re-exports (`BeliefStore`, the models, `EdgeType`, `Status`, errors). The smoke test (`test_import`) asserts `hasattr(pkg, "__all__")` — keep that contract.

---

### `src/doxastica/models.py` (model, transform — validation at seam)

**No in-repo analog.** Reference surface: RESEARCH.md lines 357–400 (grounded in CONTEXT decisions #2/#3/#4/#5). Implement exactly this closed taxonomy:

- `Status(str, Enum)` = `active`, `retracted` **ONLY** (DATA-06; reject `invalidated`/`under_revision` — those are NVM, not core).
- `EdgeType(str, Enum)` = `SUPERSEDES`, `DEPENDS_ON`, `DERIVED_FROM`. **Open Q1 (planner's call):** keep structural `HAS_REVISION`/`CURRENT_STATE` *out* of this enum (RESEARCH.md recommendation, Open Questions Q1) so `add_edge` cannot accept a structural edge.
- `Scope(BaseModel, frozen=True)`: `scope_id: str`, `is_world: bool = False`.
- `Belief(BaseModel, frozen=True)`: `belief_id: str`.
- `BeliefState(BaseModel, frozen=True)`: `state_id: UUID`, `belief_id: str`, `scope_id: str`, `source_event_id: UUID`, `value: Any`, `status: Status`. (Closed set — `model_fields` must equal exactly this for the DATA-05 negative test.)
- `BeliefFilter(BaseModel, frozen=True)`: `belief_ids: frozenset[str] | None = None`, `status: frozenset[Status] | None = None`, `event_id_min: UUID | None = None`, `event_id_max: UUID | None = None`.
- `ImpactResult(BaseModel, frozen=True)`: `reached: list[BeliefState]`, `frontier: frozenset[UUID]`, `truncated: bool`.

**Convention pattern (pydantic v2 frozen):** `class X(BaseModel, frozen=True):` — the `frozen=True` class-arg form (matches RESEARCH.md). Do NOT use `model_config = ConfigDict(frozen=True)` unless the planner prefers it for consistency; the class-kwarg form is what the design docs use. `frozen=True` gives immutability + hashability (needed because `frontier`/`belief_ids` are `frozenset` members elsewhere).

**Anti-patterns (RESEARCH.md lines 255–263, 301–305):** no `provenance`/`valid_from_turn`/epistemic fields; no mutable models; no deductive-closure machinery; `value` stays `Any` (opaque).

---

### `src/doxastica/protocol.py` (protocol, request-response — the public seam)

**No in-repo analog.** Reference surface: RESEARCH.md lines 316–354 (recovered verbatim from `05 §3` / `21 §4`, refined per CONTEXT #4 and #5).

**Import-purity pattern (DATA-01 — load-bearing):** imports `typing`/`uuid`/`pydantic` and `doxastica.models` ONLY. **Never `import ladybug`.** This is enforced by `tests/test_import_purity.py` (below).

```python
from typing import Any, Protocol
from uuid import UUID
from doxastica.models import Scope, BeliefState, EdgeType, BeliefFilter, ImpactResult

class BeliefStore(Protocol):
    def get_or_create_scope(self, scope_id: str) -> Scope: ...
    def revise(self, scope_id: str, belief_id: str, value: Any, source_event_id: UUID) -> BeliefState: ...
    def expand(self, scope_id: str, belief_id: str, value: Any, source_event_id: UUID) -> BeliefState: ...
    def contract(self, scope_id: str, belief_id: str, source_event_id: UUID) -> None: ...
    def add_edge(self, from_state_id: UUID, to_state_id: UUID, edge_type: EdgeType) -> None: ...
    def query_scope(self, scope_id: str, filter: BeliefFilter, include_deprecated: bool = False) -> list[BeliefState]: ...
    def get_impact(self, belief_state_id: UUID, depth: int | None = None) -> ImpactResult: ...
    def get_revision_chain(self, belief_id: str) -> list[BeliefState]: ...
    def get_scope_at(self, scope_id: str, as_of_event_id: UUID) -> list[BeliefState]: ...
```

**Refinements applied vs the recovered sketch (do not regress):** `query_scope(query: str)` → `BeliefFilter` (DATA-02); `get_impact(...) -> list` + `depth=5` → `-> ImpactResult` + `depth: int | None = None` (DATA-04). Document the DATA-03 ordering contract (`(source_event_id byte-order, state_id tiebreak)`) as a docstring on `get_scope_at` (or a module-level contract note) — the DATA-03 test asserts the contract text is present.

---

### `src/doxastica/ports.py` (port, CRUD + traversal — the internal LPG-primitive seam)

**No in-repo analog.** Reference surface: RESEARCH.md lines 403–427 (CONTEXT decision #1, LPG-primitive). Module name is planner's discretion (`ports.py` vs `backend.py`).

**Pattern — a second `Protocol`, primitives only, NO query-string method:**
```python
from contextlib import AbstractContextManager
from typing import Any, Protocol
from uuid import UUID
from doxastica.models import EdgeType

class BackendPort(Protocol):
    def upsert_node(self, label: str, node_id: UUID | str, props: dict[str, Any]) -> None: ...
    def add_edge(self, edge_type: EdgeType | str, from_id: UUID | str, to_id: UUID | str,
                 props: dict[str, Any] | None = None) -> None: ...
    def match_nodes(self, label: str, where: dict[str, Any]) -> list[dict[str, Any]]: ...
    def traverse(self, start: UUID | str, edge_types: frozenset[EdgeType | str],
                 max_depth: int | None) -> tuple[list[dict[str, Any]], frozenset[UUID]]: ...
    def unit_of_work(self) -> AbstractContextManager[None]: ...
```

**Anti-patterns to avoid (RESEARCH.md lines 256, 295–299):** no `run`/`query`/`execute(str)` method; no arbitrary-property-predicate method; no Cypher; `traverse` is the *single* graph-walk primitive (`get_impact`/`get_scope_at` compose from it — but those compositions are Phase 3+, not Phase 1). Distinct from `BeliefStore`: the BACK-01 test asserts the two Protocols are separate and the port has no query-string method.

---

### `src/doxastica/errors.py` (utility — typed exception surface)

**No analog (use the standard idiom).** Plain Python exception classes deriving from `Exception` (or a small base like `DoxasticaError(Exception)`). RESEARCH.md names `WorldScopeContractionError` (the world-scope `contract()`-is-an-error surface). Phase 1 only *types* the surface; **enforcement is Phase 3** (SCOPE-02). Pattern: one base class + named subclasses, docstring each, re-export from `__init__.py`.

---

### `src/doxastica/py.typed` (config — type marker)

**Analog:** `cookiecutter.../src/{{ package_name }}/py.typed`. Empty marker file, copied verbatim by the scaffold (`cookiecutter.json` line 27–29: `_copy_without_render: ["*/py.typed"]`). Nothing to author — the scaffold produces it. Confirms strict-typing consumers see `doxastica` as typed.

---

### `docs/backend-contract.md` (doc — BACK-04 spec)

**No in-repo analog.** Reference content: RESEARCH.md "Backend Port Contract" (lines 488–503) — the **7 constraints** a third-party LPG backend must satisfy: (1) LPG data model, (2) primitive op semantics (`upsert_node` idempotent / `add_edge` append-only / `match_nodes` exact-AND / `traverse` cycle-safe visited-set + `max_depth=None` ⇒ full closure / `unit_of_work` atomic), (3) PK uniqueness, (4) append-only safety, (5) ordering left to core, (6) value opacity, (7) conformance via the Phase 7 suite. Format = prose Markdown keyed to the port methods (RESEARCH.md Open Q3 recommendation). The BACK-04 test just asserts the file exists and enumerates the constraints.

---

### `tests/test_import_purity.py` (test — DATA-01 guard)

**Reference surface:** RESEARCH.md lines 430–443 (AST-scan example) — copy it nearly verbatim. **Style analog:** `cookiecutter.../tests/test_{{ package_name }}.py` (module docstring + plain `def test_*()` + bare `assert`, no class). Pattern: parse `src/doxastica/protocol.py` with `ast`, collect `Import`/`ImportFrom` module names, assert none start with `ladybug`.

---

### `tests/test_models_frozen.py` (test — DATA-06 guard)

**No reference example; style analog** = `cookiecutter.../tests/test_{{ package_name }}.py` (plain functions, bare asserts, module docstring). Cover: (a) frozen-ness — constructing then mutating a model raises `ValidationError`/`FrozenInstanceError`; (b) `Status` membership == exactly `{active, retracted}`; (c) `EdgeType` membership; (d) DATA-05 negative — `BeliefState.model_fields.keys()` == the closed 6-field set. `conftest.py` stays minimal (no DB fixtures — zero storage code this phase); the template `conftest.py` is already an empty "add fixtures here" stub.

---

## Shared Patterns

### Module docstring + ruff `D` rules
**Source:** every template `.py` file (e.g. `__init__.py` line 1, `conftest.py` line 1) + `pyproject.toml` lines 58–67.
**Apply to:** all new `.py` files.
Every module starts with a one-line `"""docstring."""`. Ruff `D` (pydocstyle) is enabled but `D1` (require-everywhere) is ignored, so module/class docstrings are encouraged, per-function docstrings optional. `line-length = 100`.

### pydantic v2 frozen-model convention
**Source:** RESEARCH.md models block (lines 357–400).
**Apply to:** all of `models.py`.
`class X(BaseModel, frozen=True):` — class-kwarg form. Gives immutability + hashability + seam validation for free (RESEARCH.md "Don't Hand-Roll", lines 270).

### `typing.Protocol` structural-interface convention
**Source:** RESEARCH.md `BeliefStore` + `BackendPort` blocks.
**Apply to:** `protocol.py`, `ports.py`.
Methods are `def name(...) -> T: ...` (ellipsis body, no implementation). Structural typing — implementers need not inherit. Two distinct Protocols (public `BeliefStore`, internal `BackendPort`).

### Test style
**Source:** `cookiecutter.../tests/test_{{ package_name }}.py`.
**Apply to:** both new test files.
Module docstring, top-level `def test_*()` functions, bare `assert`. No test classes. `pytest addopts = "-v"` (pyproject line 70).

### basedpyright-strict as primary verification
**Source:** `pyproject.toml` `[tool.pyright]` (lines 47–51) + pre-commit local hook (`.pre-commit-config.yaml` lines 24–31).
**Apply to:** all source files.
`typeCheckingMode = "strict"`, `pythonVersion = "3.14"`, `include = ["src","tests"]`. For a decision-grade phase, "basedpyright strict passes" IS the main test. Run via `uv run basedpyright`.

---

## Scaffold Patch List (post-render edits the planner must schedule)

The cookiecutter output needs these CONTEXT-driven edits **after** rendering (the template defaults do not match the decisions):

| File | Template default | Required value | Source decision |
|------|------------------|----------------|-----------------|
| `pyproject.toml` `requires-python` | `>=3.11` (via `minimum_python_version`) | `>=3.14` | CONTEXT #2 |
| `pyproject.toml` `dependencies` | `[]` | `["pydantic>=2.11,<3", "ladybug>=0.17,<0.18"]` | RESEARCH Standard Stack |
| `pyproject.toml` dev group | no hypothesis | add `hypothesis>=6.155` | RESEARCH Wave 0 gaps |
| `.github/workflows/quality.yml` line 16 | matrix `["3.11", "3.14"]` | `["3.14"]` only | CONTEXT #2 (CI drops 3.11/3.13) |
| `.github/workflows/release.yml` line 53 | matrix `["3.11", "3.14"]` | `["3.14"]` only | CONTEXT #2 |
| `.github/workflows/weekly.yml` line 34 | `"3.11"` | `"3.14"` | CONTEXT #2 |
| ruff `target-version` (pyproject line 54) | `py311` (derived) | `py314` | follows the floor raise |

Best path: set `minimum_python_version = "3.14"` at the **cookiecutter prompt** so most of these (`requires-python`, both matrices, `weekly.yml`, ruff `target-version`, `.python-version` already uses `python_version`=3.14) resolve correctly at render time — leaving only `dependencies` and the `hypothesis` dev entry as manual edits. Confirm `ladybug` (NOT `ladybugdb`) and re-verify PyPI pins before committing (RESEARCH A2, Pitfall 1, Env Availability: PyPI was proxy-blocked).

---

## No Analog Found

Files/content with **no in-repo or template analog** — the planner uses the cited reference instead of a code analog:

| File | Role | Data Flow | Reason / Reference |
|------|------|-----------|--------------------|
| `src/doxastica/models.py` | model | transform | Greenfield. Use RESEARCH.md frozen-pydantic block (CONTEXT #2/#3/#4/#5). |
| `src/doxastica/protocol.py` | protocol | request-response | Greenfield. Use RESEARCH.md `BeliefStore` block (verbatim from `05 §3`/`21 §4`). |
| `src/doxastica/ports.py` | port | CRUD + traversal | Greenfield. Use RESEARCH.md `BackendPort` block (CONTEXT #1). No prior LPG-port pattern anywhere local. |
| `src/doxastica/errors.py` | utility | n/a | No analog; standard Python exception-class idiom. |
| `docs/backend-contract.md` | doc | n/a | No analog; use RESEARCH.md 7-constraint list. |

---

## Metadata

**Analog search scope:** doxastica repo root (`/Users/paul/Documents/Dev/Personal/doxastica` — confirmed no `src/`, no `.py`, no `pyproject.toml`); the local cookiecutter template (`/Users/paul/Documents/Dev/Personal/cookiecutter-python-uv-library`); sibling `narrative-vm` confirmed present at `/Users/paul/Documents/Dev/Personal/narrative-vm` (design-doc source, not code analog).
**Files scanned:** cookiecutter `cookiecutter.json`, rendered `pyproject.toml`, `__init__.py`, `test_*.py`, `conftest.py`, `.pre-commit-config.yaml`, `quality.yml`, `ci.yml`, `.python-version`; doxastica `01-CONTEXT.md`, `01-RESEARCH.md`, `CLAUDE.md`.
**Pattern extraction date:** 2026-06-14
