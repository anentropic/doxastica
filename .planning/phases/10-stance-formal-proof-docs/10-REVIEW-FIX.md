---
phase: 10
fixed_at: 2026-07-05T10:20:00Z
review_path: .planning/phases/10-stance-formal-proof-docs/10-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 1
skipped: 4
status: partial
---

# Phase 10: Code Review Fix Report

**Fixed at:** 2026-07-05T10:20:00Z
**Source review:** .planning/phases/10-stance-formal-proof-docs/10-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5
- Fixed: 1
- Skipped: 4

## Fixed Issues

### WR-01: `_FORMAL_03_CONFORMANCE_SET` is an unchecked string registry (drift risk)

**Files modified:** `tests/test_invariants.py`
**Commit:** bb486be
**Applied fix:** Added `_FORMAL_03_OWNERS`, a name→owning-machine map, and a new
`test_formal_03_conformance_set_resolves` test. It asserts the owner map covers exactly
`_FORMAL_03_CONFORMANCE_SET`, then dereferences every registered name via `getattr` and
asserts each resolves to a `callable` on its owning `RuleBasedStateMachine`. The three
spine members resolve on `_SpineMachine` (this file); `scope_at_equals_fold_for_every_cut`
resolves on `tests.test_scope_at._ScopeAtMachine` (imported for the check). A renamed machine
method now fails the suite instead of leaving the registry silently stale. Test PASSES (all
four names resolve).

## Skipped Issues

### WR-02: Imprecise reference anchor for `WORLD_SCOPE_ID` in the tutorial

**File:** `docs/src/tutorials/cluedo-detective.md:90`
**Reason:** No stable member anchor emitted. `WORLD_SCOPE_ID` in `src/doxastica/models.py`
is an undocumented module constant (no attribute docstring), so mkdocstrings renders no
member anchor for it — a strict build (`uv run mkdocs build --strict`, exit 0) produces no
`id="...WORLD_SCOPE_ID..."` anchor anywhere in `site/`. The only anchors on the models page
are documented classes (`Belief`, `BeliefFilter`, `BeliefState`, `EdgeType`, `Scope`,
`Stance`, `Status`) plus the bare module anchor `#doxastica.models`. Pointing the link at a
precise member anchor would break the `--strict` docs gate. Per the fix guidance, the original
bare-module target `#doxastica.models` is retained (no edit made).
**Original issue:** The `WORLD_SCOPE_ID` link targets `#doxastica.models` rather than a
precise member anchor like the surrounding links, landing the reader at the top of the models
page rather than the constant.

### N-01: Deliberate `Stance` export in `src/doxastica/__init__.py`

**File:** `src/doxastica/__init__.py`
**Reason:** Informational validation, no action required (correct and consistent, in-scope
decision D-13). Per review disposition, no change invented.
**Original issue:** Confirms the `Stance` import + `__all__` export is correct — not flagged.

### N-02: `test_cross_type_comparison_raises` including the `Stance` class as an operand

**File:** `tests/test_stance.py`
**Reason:** Informational validation, no action required. The metaclass defines no ordering →
`NotImplemented` → `TypeError`, so the test is valid. No change invented.
**Original issue:** Confirms using the `Stance` class itself as a comparison operand is a
valid negative case.

### N-03: Guard-style parametrized laws (`test_antisymmetry`, `test_transitivity`)

**File:** `tests/test_stance.py`
**Reason:** Informational validation, no action required. Per-case trivially-true when
antecedents are false, but non-vacuous in aggregate (other cases in the 16/64 enumeration
exercise the body). Acceptable. No change invented.
**Original issue:** Confirms the guard-style parametrized laws are acceptable despite
per-case vacuity.

---

_Fixed: 2026-07-05T10:20:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
