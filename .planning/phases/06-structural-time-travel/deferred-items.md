# Phase 6 — Deferred Items (out-of-scope discoveries)

> Logged during execution per the executor scope-boundary rule. NOT fixed here — these are
> pre-existing conditions outside the current task's changes.

## 06-01

- **`ruff format` discrepancy at `src/doxastica/core.py:68`** (`_CASCADE_EDGE_TYPES` frozenset
  literal wrapped across 3 lines that `ruff format` would collapse to one line). Confirmed
  **pre-existing at HEAD** (`git show HEAD:src/doxastica/core.py | ruff format --check` flags it
  before this plan's changes). It is unrelated to the `get_scope_at` addition (far below line 68),
  so it was left untouched per the scope boundary. The pre-commit hooks accepted the Task-2 commit
  (exit 0), so it does not block. A future formatting sweep should reformat this line.
