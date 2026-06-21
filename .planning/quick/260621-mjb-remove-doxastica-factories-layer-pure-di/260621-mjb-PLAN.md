---
quick_id: 260621-mjb
title: "Remove doxastica.factories layer — pure DI construction"
date: 2026-06-21
status: ready
---

# Quick Task 260621-mjb: Remove the factories convenience layer

## Problem

The previous quick task (260621-m02) moved three convenience constructors into
`doxastica/factories.py` as free functions (`in_memory` / `open` / `from_connection`),
re-exported at the package root. User decision: drop that convenience layer entirely. Construction
should be **pure DI** with no top-level factory functions. The two ladybug constructors belong ON
`LadybugBackend` (where `open()` already lives); `in_memory` just goes away (`InMemoryBackend()` is
already a zero-arg constructor).

Final construction API:
```python
MemoryCore(InMemoryBackend())                      # was doxastica.in_memory()
MemoryCore(LadybugBackend.open("graph.db"))        # was doxastica.open("graph.db")
MemoryCore(LadybugBackend.from_connection(conn))   # was doxastica.from_connection(conn)
```

## Scope

Mechanical. **No behavior change.** `LadybugBackend.open()` already exists and is unchanged;
`from_connection` is a thin classmethod over the existing `__init__(conn, namespace=, owns_conn=)`.

## Tasks

### Task 1 — Add `LadybugBackend.from_connection` classmethod

- **files:** `src/doxastica/backends/ladybug.py`
- **action:** Add a classmethod directly after `open()` (around line 187):
  ```python
  @classmethod
  def from_connection(cls, conn: lb.Connection, *, namespace: str = "dx") -> LadybugBackend:
      """..."""
      return cls(conn, namespace=namespace, owns_conn=False)
  ```
  Docstring: this wraps an INJECTED tenant connection the backend must NEVER close (CONN-01 /
  R19, `owns_conn=False`) — the sibling of `open()` (which owns what it creates). Bootstrap still
  runs idempotently against the injected (possibly shared) DB. Also fix the two stale
  `doxastica.factories.from_connection` / `doxastica.factories.open` docstring references in this
  file (module docstring ~line 14, `open` docstring ~line 180) to point at
  `LadybugBackend.from_connection` / `LadybugBackend.open` instead.
- **verify:** `from_connection` constructs a backend with `_owns_conn is False`; basedpyright clean.
- **done:** `LadybugBackend.from_connection` exists as a sibling of `open`.

### Task 2 — Delete `src/doxastica/factories.py` and its re-exports

- **files:** `src/doxastica/factories.py` (delete), `src/doxastica/__init__.py`
- **action:** `git rm src/doxastica/factories.py`. In `__init__.py`, remove the
  `from doxastica.factories import ...` line and drop `"from_connection"`, `"in_memory"`, `"open"`
  from `__all__`. Leave `MemoryCore`, `InMemoryBackend`, and all model/error exports intact. Do NOT
  add a `LadybugBackend` export — it stays behind the optional extra, importable only from
  `doxastica.backends.ladybug` (keeping the package-root import driver-blind, D-02).
- **verify:** `python -c "import doxastica; doxastica.in_memory"` raises AttributeError;
  `python -c "import doxastica; doxastica.MemoryCore"` works.
- **done:** No `factories` module; package root exposes no factory functions.

### Task 3 — Scrub stale `factories` references in `core.py`

- **files:** `src/doxastica/core.py`
- **action:** The 260621-m02 task repointed core.py's construction docstrings at
  `doxastica.factories`. Update those mentions to describe the pure-DI story instead: construct
  `MemoryCore(backend)` directly; `InMemoryBackend()` for the zero-dep default,
  `LadybugBackend.open(...)` / `LadybugBackend.from_connection(...)` for the ladybug reference
  backend. `core.py` must remain driver-blind (no `ladybug` import, no backend import at module
  level — naming the backends in prose docstrings is fine).
- **verify:** `grep -n factories src/doxastica/core.py` → no hits; `grep -n 'import ladybug'
  src/doxastica/core.py` → no hits.
- **done:** No dangling `doxastica.factories` references in core.

### Task 4 — Repoint `tests/test_import_purity.py`

- **files:** `tests/test_import_purity.py`
- **action:**
  - Remove `"factories"` from the `@pytest.mark.parametrize` module list on
    `test_seam_does_not_import_ladybug` (the module no longer exists). The list returns to
    `["protocol", "ports", "core", "backends/memory"]`.
  - DELETE `test_function_local_ladybug_import_is_not_flagged` entirely: with factories gone, NO
    backend-blind spine module has a function-local ladybug import, so the test has no real
    subject. The synthetic-source negative control `test_scan_flags_a_module_level_ladybug_import`
    already proves the scan distinguishes function-local from module-level imports, so coverage of
    that behavior is retained.
  - In `test_driver_free_spine_imports_with_ladybug_blocked`: change the subprocess body from
    `from doxastica import MemoryCore` / `MemoryCore.in_memory()` to
    `from doxastica import MemoryCore` + `from doxastica.backends.memory import InMemoryBackend`
    then `MemoryCore(InMemoryBackend())`. Remove the `import doxastica.factories` spine-import line
    if present.
  - Update the MODULE docstring + comments: drop the claim that `MemoryCore.open` /
    `from_connection` (or factories) place sanctioned function-local ladybug imports. The accurate
    statement now: the ONLY module importing ladybug is `backends/ladybug.py` (a module-level
    import inside the guarded driver boundary — NOT part of the backend-blind spine), and the spine
    modules (protocol/ports/core/backends.memory) carry no ladybug import at any level.
- **verify:** `pytest tests/test_import_purity.py -q` passes.
- **done:** Import-purity guard reflects the post-factories reality.

### Task 5 — Update `in_memory()` call sites in the remaining tests

- **files:** `tests/test_backend_memory.py`, `tests/test_cascade.py`, `tests/test_recovery_xfail.py`
- **action:** Replace `in_memory()` (or `MemoryCore.in_memory()` if any remain) with
  `MemoryCore(InMemoryBackend())`. Add `from doxastica.backends.memory import InMemoryBackend`
  (or `from doxastica import InMemoryBackend`, which is exported) where needed and drop the now-unused
  `in_memory` import. `test_backend_memory.py` ~lines 163-189 (note the test whose docstring/name
  references `MemoryCore.in_memory()` — update prose to `MemoryCore(InMemoryBackend())`);
  `test_cascade.py` ~lines 359/373; `test_recovery_xfail.py` ~line 75. Leave existing
  `MemoryCore(backend)` injected-port call sites untouched.
- **verify:** `pytest -q` → full suite green.
- **done:** No test references the removed factory functions.

## Verification (whole task)

1. `grep -rn -E '\b(in_memory|from_connection)\b' src/doxastica/__init__.py` → no hits.
2. `test -f src/doxastica/factories.py` → false (deleted).
3. `grep -rn 'doxastica.factories' src tests` → no hits.
4. `python -c "from doxastica import MemoryCore, InMemoryBackend; from doxastica.backends.ladybug import LadybugBackend; print(MemoryCore(InMemoryBackend()).__class__.__name__, hasattr(LadybugBackend, 'from_connection'))"`
   → `MemoryCore True` (run only if ladybug extra installed; otherwise verify the in-memory half).
5. Full test suite passes (basedpyright strict + ruff clean). Report passed/failed/skipped counts;
   surface any skipped tests explicitly — do not count skips as passes.

## Out of scope

- No change to `MemoryCore` operation-method bodies, `BackendPort`, or `BeliefStore`.
- No `LadybugBackend` export at the package root (stays behind the optional extra).
- No registry/plugin system.
