---
quick_id: 260621-mjb
title: "Remove doxastica.factories layer — pure DI construction"
date: 2026-06-21
status: complete
tasks_completed: 5
files_created: 0
files_modified: 6
files_deleted: 1
---

# Quick Task 260621-mjb: Remove the factories convenience layer — Summary

Removed the `doxastica.factories` convenience layer entirely and made construction pure DI:
deleted `factories.py` and its package-root re-exports, and relocated the injected-connection
constructor onto `LadybugBackend.from_connection()` as a sibling of the existing `open()`. No
behavior change — verbatim relocation/removal.

## Final construction API

```python
MemoryCore(InMemoryBackend())                      # was doxastica.in_memory()
MemoryCore(LadybugBackend.open("graph.db"))        # unchanged
MemoryCore(LadybugBackend.from_connection(conn))   # was doxastica.from_connection(conn)
```

## Tasks completed

1. **Add `LadybugBackend.from_connection`** — thin classmethod after `open()` returning
   `cls(conn, namespace=namespace, owns_conn=False)` with a real R19/CONN-01 tenant-never-closed
   docstring (sibling of `open()`). Fixed the two stale `doxastica.factories.*` docstring
   references in `ladybug.py` (module docstring + `open` docstring) to point at the classmethods.
2. **Delete `factories.py` + re-exports** — `git rm src/doxastica/factories.py`; removed the
   `from doxastica.factories import ...` line and dropped `from_connection`/`in_memory`/`open`
   from `__init__.__all__`. `LadybugBackend` is deliberately NOT exported from the root (stays
   behind the optional extra, importable only from `doxastica.backends.ladybug`).
3. **Scrub `factories` refs in `core.py`** — rewrote the module docstring and `MemoryCore` class
   docstring to describe the pure-DI story (caller builds the backend and injects it). `core.py`
   remains driver-blind (no ladybug import at any level; backends named only in prose).
4. **Repoint `tests/test_import_purity.py`** — removed `"factories"` from the parametrized scan;
   DELETED `test_function_local_ladybug_import_is_not_flagged` (its premise no longer exists);
   repointed the driver-blocked subprocess to `MemoryCore(InMemoryBackend())`; updated the module
   docstring so the only ladybug import is the guarded module-level one in `backends/ladybug.py`.
5. **Update `in_memory()` call sites** — replaced `in_memory()` with `MemoryCore(InMemoryBackend())`
   in `test_backend_memory.py`, `test_cascade.py`, `test_recovery_xfail.py`; adjusted imports
   (dropped now-unused `in_memory`, added/kept `InMemoryBackend`).

## Critical constraints honored

- **D-02 driver-blindness preserved.** `grep -rn 'import ladybug' src/doxastica/core.py
  src/doxastica/__init__.py` → no hits. The only ladybug import is the guarded module-level one
  in `backends/ladybug.py`. `LadybugBackend` is NOT exported from the package root, so
  `import doxastica` never chain-loads the optional driver. `InMemoryBackend` IS exported (kept).
- **`from_connection` is a thin classmethod** (`return cls(conn, namespace=namespace,
  owns_conn=False)`); `__init__` and `open()` unchanged.
- No back-compat shims, no registry/plugin system, no changes to operation-method bodies,
  `BackendPort`, or the `BeliefStore` protocol.

## Deviations from Plan

None — plan executed exactly as written. (One non-deviation adjustment: shortened a one-line test
docstring by one word to stay under the ruff E501 100-char limit; no semantic change.)

## Files modified

- `src/doxastica/backends/ladybug.py` — added `from_connection` classmethod; fixed 2 stale docstrings
- `src/doxastica/__init__.py` — removed factories import + 3 `__all__` entries
- `src/doxastica/core.py` — scrubbed 3 `factories` docstring references → pure-DI prose
- `tests/test_import_purity.py` — repointed scan + subprocess; deleted obsolete test; updated docstrings
- `tests/test_backend_memory.py` — 2 call sites → `MemoryCore(InMemoryBackend())`
- `tests/test_cascade.py` — 2 call sites + import + docstring
- `tests/test_recovery_xfail.py` — 1 call site + import

## Files deleted

- `src/doxastica/factories.py`

## Verification

- `uv run python -c "from doxastica import MemoryCore, InMemoryBackend; MemoryCore(InMemoryBackend())"` → `MemoryCore`
- `uv run python -c "import doxastica; hasattr(doxastica, 'in_memory')"` → `False`
- `LadybugBackend.from_connection` present → `True` (ladybug extra installed)
- `test -f src/doxastica/factories.py` → GONE
- `grep -rn 'doxastica.factories' src tests` → no hits
- `grep -rn 'import ladybug' src/doxastica/core.py src/doxastica/__init__.py` → no hits
- `uv run ruff check src tests && uv run ruff format --check src tests` → All checks passed; 25 files formatted
- `uv run basedpyright src tests` → 0 errors, 0 warnings, 0 notes
- `uv run pytest -q` → **193 passed, 1 xfailed in 28.11s** (0 skipped)

### Skip / xfail note

ZERO skipped tests. The single `xfailed` is `test_recovery_does_not_hold_for_belief_bases`
(`tests/test_recovery_xfail.py`) — a deliberate `strict=True` xfail that is the AGM-Recovery
drift guard (Recovery is excluded by design; the test asserts the Recovery conclusion so it
correctly FAILS → xfails GREEN). This is an expected pass, not a skip. The ladybug/parity tests
RAN and passed (`test_backend_ladybug` 19, `test_backend_parity` 40) — the extra is installed and
exercised, not skipped.

## Commits

- `be64fe8` refactor(260621-mjb): remove factories layer for pure-DI construction
- `ee969c8` test(260621-mjb): repoint tests off removed factories layer

## Self-Check: PASSED

- factories.py confirmed deleted (GONE)
- both commits present in git log
- full suite green, ruff + basedpyright clean
