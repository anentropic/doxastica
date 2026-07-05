---
phase: 10
slug: stance-formal-proof-docs
depth: standard
status: issues_found
files_reviewed: 5
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
reviewed: 2026-07-05
---

# Phase 10: Code Review Report — Stance Formal Proof & Docs

**Depth:** standard  **Files reviewed:** 5  **Status:** issues_found (no blockers)

## Summary

A strong, unusually self-aware submission. The new property tests largely *do* prove
what they claim, and the authors pre-empted the exact vacuity traps this review targets.
Verified against the source under test (`models.Stance`, `core.py`
revise/expand/contract/`_hydrate`/`_current`/`get_scope_at`/`get_impact`), with the full
suite run green (both backends, 0 skips — ladybug synced) and the tutorial's program
executed end-to-end:

- `test_totality_trichotomy` expresses the third term as the **primitive** `b < a`, not
  the derived `a > b` — a broken `__lt__` genuinely fails instead of passing vacuously.
- Persistence `is`-identity assertions are non-vacuous by construction: a
  `Stance(props["stance"])` value-lookup regression in `_hydrate` would **raise** on read.
- `test_widened_key_discriminates_stance` routes both scopes through the real `_base_of`
  helper, so reverting the widened key genuinely collapses `a != b`. Load-bearing, correct.
- `chain_is_immutable` uses exact equality (`total == self._state_count`).
- Tutorial Step 11 executes and prints `All checks passed.`; get_impact / get_scope_at /
  `WORLD_SCOPE_ID` semantics all described accurately; no process-ID/decision-ID leakage.

No BLOCKER-level correctness, security, or data-loss defects found.

## Warnings

### WR-01: `_FORMAL_03_CONFORMANCE_SET` is an unchecked string registry (drift risk)

**File:** `tests/test_invariants.py:826-831` (sibling `tests/test_scope_at.py:509`)
**Issue:** The FORMAL-03 conformance set is a module-level tuple of method-name **strings**,
never dereferenced programmatically — it appears only in comments/registry form, never in an
assertion. In a project whose ethos is "verified mechanically, not asserted by construction,"
a conformance registry that isn't mechanically checked can silently go stale if a method is
renamed. All four names currently resolve (verified) — this is drift-prevention, not a live
break. **Pre-existing** (predates Phase 10; also in `test_scope_at.py`), surfaced now.
**Fix:** Add a tiny resolver test that asserts each name in the set resolves to a callable on
its machine class, turning the comment-grade registry into a mechanically-verified one.

### WR-02: Imprecise reference anchor for `WORLD_SCOPE_ID` in the tutorial

**File:** `docs/src/tutorials/cluedo-detective.md:90`
**Issue:** Every other reference link uses a precise member anchor
(`#doxastica.models.EdgeType`, `#doxastica.core.MemoryCore.revise`, …), but the
`WORLD_SCOPE_ID` link targets the bare module anchor `#doxastica.models`. It resolves
(so `mkdocs build --strict` stays green) but lands the reader at the top of the models page
rather than the constant, inconsistent with the surrounding convention. Introduced in 10-04.
**Fix:** Point the target at the `WORLD_SCOPE_ID` member anchor; verify the generated anchor
id in the built site (mkdocstrings may slugify module constants) before committing so
`--strict` stays green.

## Notes (informational, no action required)

- N-01: The deliberate `Stance` export in `src/doxastica/__init__.py` (import + `__all__`) is
  correct and consistent — not flagged (in-scope decision D-13).
- N-02: `test_cross_type_comparison_raises` including the `Stance` class itself as an operand
  is valid: the metaclass defines no ordering → `NotImplemented` → `TypeError`.
- N-03: Guard-style parametrized laws (`test_antisymmetry`, `test_transitivity`) are per-case
  trivially-true when antecedents are false; non-vacuous in aggregate because other cases in
  the 16/64 enumeration exercise the body. Acceptable.

## Disposition

Both warnings are advisory maintainability items — no correctness/security/data-loss impact,
phase goal fully met. WR-02 is a trivial in-scope follow-up (docs anchor precision); WR-01 is
a pre-existing drift-risk improvement that embodies the project's mechanical-verification ethos.
Neither blocks phase completion. To act: `/gsd-code-review 10 --fix`.
