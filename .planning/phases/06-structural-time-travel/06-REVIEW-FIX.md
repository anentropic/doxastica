---
phase: 06-structural-time-travel
fixed_at: 2026-06-19T00:00:00Z
review_path: .planning/phases/06-structural-time-travel/06-REVIEW.md
iteration: 1
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-06-19T00:00:00Z
**Source review:** .planning/phases/06-structural-time-travel/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 1 (critical + warning only; the 3 Info findings IN-01/IN-02/IN-03 were out of scope and intentionally untouched)
- Fixed: 1
- Skipped: 0

## Fixed Issues

### WR-01: `get_scope_at` reads outside a `unit_of_work` while `query_scope`'s sibling `get_impact` wraps its multi-call read in one

**Files modified:** `src/doxastica/core.py`
**Commit:** c8d6dd5
**Applied fix:** Took option (a) from the review — added a documented snapshot
invariant rather than restructuring the read (the guardrails forbid changing
`get_scope_at` signature or observable behavior). Inserted a multi-line comment at
the single `match_nodes` call (the `# 1. ONE scope-wide round-trip` block) making the
single-call snapshot assumption explicit and mirroring `get_impact`'s WR-02 note:
one `match_nodes` ⇒ one auto-committed snapshot, so no `unit_of_work` is needed today;
if a second backend call is ever added here, both must be wrapped in
`self._backend.unit_of_work()` per WR-02, otherwise a concurrent append on the ladybug
single-writer model can land between two auto-committed reads with no compile-time
signal. Comment-only change — no logic, signature, or observable behavior altered.

**Verification:**
- Tier 1: re-read the edited region; fix text present, surrounding code intact.
- Tier 2: `python -c "import ast; ast.parse(...)"` passed.
- Project guardrails (all green): `ruff check` on `core.py` → all checks passed;
  `ruff format --check` → the ONLY would-reformat diff is the pre-existing,
  out-of-scope line-68 `_CASCADE_EDGE_TYPES` discrepancy (documented in
  deferred-items.md), not introduced by this edit; `basedpyright` strict → 0 errors,
  0 warnings, 0 notes; full suite `pytest -q` → **184 passed** (matches the required
  count), including `test_import_purity.py` (core.py stays ladybug-free) and the
  HIST-03 `test_scope_at.py` cases on both backends.

## Skipped Issues

None — the single in-scope finding was fixed. (IN-01, IN-02, IN-03 were Info-tier and
excluded by `fix_scope: critical_warning`; they were not attempted.)

---

_Fixed: 2026-06-19T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
