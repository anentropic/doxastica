---
quick_id: 260622-hiy
slug: pr1-review-fixes
date: 2026-06-22
type: docs+test
---

# Quick Task: PR #1 Copilot review fixes (4 findings)

Triaged 7 Copilot inline comments on PR #1; 4 were actionable (2 HIGH/MEDIUM
substantive, 2 LOW cosmetic). The other 3 were false (missing-`-> None` claimed to
trigger `reportMissingReturnType` — basedpyright strict already passes; addressed for
consistency only).

## Changes

1. **HIGH — broken Quick Start.** `MemoryCore.in_memory()` does not exist (pure DI, no
   factories). Replaced with `MemoryCore(InMemoryBackend())` in `README.md:41` and
   `docs/src/index.md` (added `InMemoryBackend` to the import line).
2. **MEDIUM — stale internal contract.** `docs/src/backend-contract.md` described
   `revise` as re-pointing a stored `CURRENT_STATE` pointer; D-01 has no such pointer
   (current is derived). Rewrote the `unit_of_work` example to the real multi-write
   (append `BeliefState` + `HAS_REVISION` + `SUPERSEDES`) and stated current is derived.
3. **LOW — consistency.** Added `-> None` to the zero-arg test functions in
   `tests/test_doxastica.py` and `tests/test_models_frozen.py`.
4. **LOW — assertion strength.** `tests/test_port_distinct.py` claimed "exactly five
   primitives" but only checked presence. Now asserts the full declared protocol surface
   equals the five via the public `typing.get_protocol_members(BackendPort)`.

## Verification

- `ruff check src tests` clean; `basedpyright src tests` (strict) 0 errors.
- Full suite: 193 passed, 1 xfailed.
- Quick Start snippet executed end-to-end (`MemoryCore(InMemoryBackend())` →
  `revise` → `query_scope` → `{'sky-colour': 'blue'}`).
