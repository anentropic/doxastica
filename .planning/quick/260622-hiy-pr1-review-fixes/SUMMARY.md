---
quick_id: 260622-hiy
slug: pr1-review-fixes
date: 2026-06-22
status: complete
type: docs+test
---

# Summary: PR #1 Copilot review fixes (4 findings)

Addressed the 4 actionable Copilot comments on PR #1.

1. Replaced non-existent `MemoryCore.in_memory()` with `MemoryCore(InMemoryBackend())`
   in `README.md` and `docs/src/index.md` (import line updated) — fixes a broken,
   AttributeError-raising Quick Start.
2. Rewrote the `unit_of_work` `revise` example in `docs/src/backend-contract.md` to drop
   the non-existent stored `CURRENT_STATE` pointer; describes the real multi-write and
   states current is derived (D-01).
3. Added `-> None` to the unannotated zero-arg tests in `tests/test_doxastica.py` and
   `tests/test_models_frozen.py` (suite-consistency; not a strict-mode violation —
   basedpyright already passed).
4. Tightened `tests/test_port_distinct.py` to assert the protocol surface is EXACTLY the
   five primitives via the public `typing.get_protocol_members`, so a sixth method on the
   port now fails the test.

3 of the original 7 Copilot comments were non-bugs (the `reportMissingReturnType` claim
was false under this config); they were folded into fix 3 for consistency only.

## Verification
- `ruff check src tests` → clean.
- `basedpyright src tests` (strict) → 0 errors.
- `pytest` → 193 passed, 1 xfailed.
- Quick Start snippet runs end-to-end and prints `{'sky-colour': 'blue'}`.

## Files changed
- `README.md`
- `docs/src/index.md`
- `docs/src/backend-contract.md`
- `tests/test_doxastica.py`
- `tests/test_models_frozen.py`
- `tests/test_port_distinct.py`
