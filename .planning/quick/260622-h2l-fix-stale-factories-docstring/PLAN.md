---
quick_id: 260622-h2l
slug: backends-init-stale-factories-docstring
date: 2026-06-22
type: docs
---

# Quick Task: Fix stale "factories" docstring in backends/__init__.py

## Problem

`src/doxastica/backends/__init__.py` module docstring claimed the ladybug adapter
"is imported lazily, function-locally, by `MemoryCore`'s factories instead." The
factories layer was removed in the pure-DI refactor (be64fe8); there is no
`factories.py`. Surfaced during PR #1 review.

## Change

Single docstring edit: replace the stale "factories" sentence with the current
construction story — the caller imports `LadybugBackend.open(...)` /
`.from_connection(...)` directly from `doxastica.backends.ladybug` and injects the
backend into `MemoryCore` (pure DI; `MemoryCore` stays driver-blind).

Doc-only. No behavior change. The re-export rule (never `from .ladybug import ...`
here) is unchanged.

## Verification

- `ruff check` clean.
- `import doxastica.backends` succeeds, `__all__ == ['InMemoryBackend']` unchanged.
