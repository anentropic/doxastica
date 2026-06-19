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
- Findings in scope: 1 (fix_scope = all: critical + warning + info)
- Fixed: 1
- Skipped: 0

## Fixed Issues

### IN-01: Retracted-as-of collapse restates the `_current` rule inline rather than through a shared predicate

**Files modified:** `src/doxastica/core.py`
**Commit:** cba988c
**Applied fix:** Extracted a module-level `_is_active_tail(tail: dict[str, Any]) -> bool`
predicate (`tail["status"] != Status.retracted.value`) as a sibling to `_order_key`, giving the
"retracted tail ⇒ absent" rule a single home alongside the ONE ordering contract. Reused it from
both `_current` (line 230: `if tail is None or not _is_active_tail(tail)`) and the `get_scope_at`
retracted-as-of collapse (line 671: `[t for t in by_belief.values() if _is_active_tail(t)]`).

**Behavior preservation:** Byte-identical. The predicate keeps the exact `!= Status.retracted.value`
comparison form already in use at both sites — no second ordering, no changed comparison idiom, no
signature change to `get_scope_at` / `query_scope` / `_current` / `_current_tail`. `query_scope`'s
own `Status(...) in allowed` allow-set was intentionally left untouched (it serves the
`include_retracted` / explicit-status-set path, a different contract than the always-active-as-of
collapse); the helper is shared only between the two sites that implement the identical
active-tail-only rule, exactly as the review recommended.

**Verification:**
- Tier 1: re-read all three edited regions; helper present, call sites intact, surrounding code
  unchanged.
- Tier 2: `python -m ast` parse OK; `ruff check src/doxastica/core.py` clean; `basedpyright
  src/doxastica/core.py` → 0 errors, 0 warnings, 0 notes.
- Full suite: `uv run pytest -q` → **184 passed** (unchanged), confirming the retracted-tail
  collapse semantics are byte-identical (incl. `test_scope_at.py` SC1 cases and the
  `query_scope`/`_current` suites).
- `ruff format --check` reports a single diff at the pre-existing `_CASCADE_EDGE_TYPES` definition
  (core.py:68), which is documented in deferred-items.md and explicitly OUT OF SCOPE — the newly
  added helper is format-clean and was not touched by that diff.

## Prior-pass dispositions (not re-applied)

- **WR-01 — already RESOLVED** before this run (single-call snapshot invariant documented at
  core.py:652-658). Not re-applied; recorded as out-of-scope / already-fixed per the review's
  prior-pass disposition.

---

_Fixed: 2026-06-19T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
