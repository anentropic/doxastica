---
quick_id: 260622-h2l
slug: backends-init-stale-factories-docstring
date: 2026-06-22
status: complete
type: docs
---

# Summary: Fix stale "factories" docstring in backends/__init__.py

Replaced the stale module-docstring sentence in
`src/doxastica/backends/__init__.py` that referenced "`MemoryCore`'s factories"
(a layer removed in the pure-DI refactor be64fe8) with the current construction
story: the caller imports `LadybugBackend.open(...)` / `.from_connection(...)`
directly from `doxastica.backends.ladybug` and injects it into `MemoryCore`.

Doc-only change, no behavior impact. The re-export discipline (this `__init__`
never imports `.ladybug`) is unchanged.

## Verification
- `ruff check src/doxastica/backends/__init__.py` → clean.
- `import doxastica.backends` → OK, `__all__ == ['InMemoryBackend']` unchanged.

## Files changed
- `src/doxastica/backends/__init__.py` (docstring only)
</content>
