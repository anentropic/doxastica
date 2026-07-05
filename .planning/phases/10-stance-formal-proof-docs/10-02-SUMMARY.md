---
phase: 10-stance-formal-proof-docs
plan: 02
subsystem: testing
tags: [hypothesis, pytest, enum, total-ordering, property-tests, itertools, operator]

# Dependency graph
requires:
  - phase: 09-stance-value-layer-write-persistence
    provides: "Stance type (plain Enum + @total_ordering), name-token serialization, write-spine threading"
provides:
  - "Exhaustive order-law proof over the 4-member Stance domain (irreflexivity, trichotomy/totality, antisymmetry, transitivity)"
  - "Reflected-operator-consistency law proving derived >/>=/<= match the primitive <"
  - "No-arithmetic CLOSURE guard: every arithmetic/bitwise op x every member pair raises TypeError"
  - "Cross-type ordering-raises + equality-does-not-raise (Pitfall 5) proofs"
affects: [stance-formal-proof-docs, verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Enumerate tiny domains exhaustively (itertools.product) rather than Hypothesis-sampling (D-05)"
    - "getattr(operator, name) typed seam to enumerate operators without per-line pyright ignores"
    - "Express order laws over the PRIMITIVE < (both directions) so a broken __lt__ genuinely fails"

key-files:
  created: []
  modified:
    - tests/test_stance.py

key-decisions:
  - "Trichotomy expressed as (a<b)+(a==b)+(b<a)==1 using the primitive < both directions, NOT the plan's literal a>b — the derived > is vacuous under @total_ordering against a broken __lt__ (Rule 1)"
  - "Added test_reflected_operators_consistent so the derived >/>=/<= are proven and the SC2 mutation is genuinely caught"
  - "Route operator.* through a single getattr _binop seam typed (object,object)->object, replacing the per-line reportOperatorIssue ignore wall"
  - "from __future__ import annotations so Callable is a TYPE_CHECKING-only import (satisfies ruff TC003)"

patterns-established:
  - "Order-law enumeration: assert axioms over the whole finite domain, not a hardcoded chain"
  - "No-arithmetic closure: operator.* x itertools.product, closure claim not three witnesses"

requirements-completed: [STANCE-07]

# Metrics
duration: 20min
completed: 2026-07-05
---

# Phase 10 Plan 02: Stance Order-Law & No-Arithmetic Proof Summary

**Turned the SC2 stance scaffold into a mechanical proof: the total order is enumerated exhaustively over all 4 members (irreflexivity, trichotomy/totality, antisymmetry, transitivity + reflected-operator consistency), and no arithmetic/bitwise operator is reachable via a closure over every op x every member pair — with a proven-non-vacuous broken-`__lt__` mutation check.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-05
- **Completed:** 2026-07-05
- **Tasks:** 2
- **Files modified:** 1 (`tests/test_stance.py`)

## Accomplishments
- **Antisymmetry is now asserted by name** (`test_antisymmetry`) — it was literally unasserted before (D-04).
- Order axioms proven **exhaustively** over `itertools.product(Stance, ...)`: 4 irreflexivity + 16 trichotomy + 16 antisymmetry + 64 transitivity cases (D-05), plus 16 reflected-operator-consistency cases.
- No-arithmetic strengthened from three witnesses to a **closure** over `_ARITH` (12 ops) x `_PAIRS` (16) = 192 cases (D-06); cross-type ordering raises (20 cases) while `==`/`!=` do not (Pitfall 5, 20 cases).
- The per-line `reportOperatorIssue` pyright-ignore wall is **gone**, replaced by a single typed `_binop` seam.
- `tests/test_stance.py` grew from 5 to **352** collected cases; full prek suite (CI-parity) and full test suite (555 passed, 1 xfailed) green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Exhaustive order-law enumeration (D-04, D-05)** - `d0053b4` (test)
2. **Task 2: No-arithmetic closure guard (D-06)** - `73896d5` (test)

## Files Created/Modified
- `tests/test_stance.py` - Added `_PAIRS`/`_TRIPLES`/`_ARITH`/`_ORDERINGS` module constants and the `_binop` typed seam; added `test_irreflexivity`, `test_totality_trichotomy`, `test_reflected_operators_consistent`, `test_antisymmetry`, `test_transitivity`, `test_no_arithmetic_operator_is_reachable`, `test_cross_type_comparison_raises`, `test_cross_type_equality_does_not_raise`; kept the four example-anchor tests. No `src/` change.

## Decisions Made
- **Primitive-`<` trichotomy over the plan's literal `a > b`.** `@total_ordering` synthesizes `a > b` as `not (a < b) and a != b`, so a broken `__lt__` (always `False`) leaves `a > b` reading `a != b` and the trichotomy sum still equals 1 — the law would pass **vacuously** against exactly the SC2 mutation it must catch. Expressing trichotomy over the primitive `<` in both directions (`(a<b)+(a==b)+(b<a)==1`) makes a broken order genuinely FAIL.
- **Added `test_reflected_operators_consistent`** (a fifth law beyond the four named in the plan) proving the derived `>`/`>=`/`<=` agree with the primitive `<`. It independently covers the `>` operator that the strengthened trichotomy no longer references, and also fails under the broken-`__lt__` mutation.
- **`getattr`-based `_binop` seam** typed `(object, object) -> object` to enumerate `operator.*` uniformly — several `operator` members are only partially typed in the stubs, so a literal `[operator.xor, ...]` list trips basedpyright-strict `reportUnknownMemberType`. One typed seam replaces the scattered per-line ignores (D-06).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's literal trichotomy formula is vacuous under the mandated SC2 mutation**
- **Found during:** Task 1 (exhaustive order-law enumeration)
- **Issue:** The plan/RESEARCH specify `test_totality_trichotomy` as `(a < b) + (a == b) + (a > b) == 1`. Because `@total_ordering` derives `>` from `__lt__`+`__eq__`, mutating `Stance.__lt__` to always return `False` (the VALIDATION SC2 vacuous-pass probe) leaves the sum equal to 1 for every pair — the test passes while proving nothing. Empirically confirmed: the literal `a>b` form passes the broken order; the primitive `b<a` form fails it.
- **Fix:** Expressed trichotomy over the primitive `<` in both directions (`(a<b)+(a==b)+(b<a)==1`) and added `test_reflected_operators_consistent` to separately prove the derived `>`/`>=`/`<=`. Both now FAIL under the broken `__lt__` (24 failures observed), so the guard genuinely guards.
- **Files modified:** `tests/test_stance.py`
- **Verification:** Patched `models.py::Stance.__lt__` to `return False`, ran the order-law tests → `test_totality_trichotomy` + `test_reflected_operators_consistent` FAILED (24 cases); restored `models.py` (untouched in git). With the correct order all 352 cases pass.
- **Committed in:** `d0053b4` (Task 1 commit)

**2. [Rule 3 - Blocking] `Callable` runtime annotation tripped ruff TC003 / basedpyright**
- **Found during:** Task 2 (no-arithmetic closure guard)
- **Issue:** `from collections.abc import Callable` used only in annotations tripped ruff `TC003`; without `from __future__ import annotations` the return annotation is evaluated at runtime, so TC003's suggested TYPE_CHECKING move would NameError.
- **Fix:** Added `from __future__ import annotations` (PEP 563) and moved `Callable` under `if TYPE_CHECKING:`. basedpyright and ruff both clean.
- **Files modified:** `tests/test_stance.py`
- **Verification:** `prek run --all-files` — ruff, ruff-format, basedpyright all Passed.
- **Committed in:** `73896d5` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** The trichotomy strengthening is the load-bearing correction — it is what makes SC2 a genuine proof rather than a rubber-stamp (the exact failure D-01 exists to kill). The four named order-law tests still collect exactly 4+16+16+64 = 100 cases as the acceptance criterion specifies; the reflected-operator law is additive. No scope creep; no `src/` change.

## Vacuous-Pass Detection (VALIDATION SC2)

Mandatory manual mutation check performed and reported:
- Mutated `Stance.__lt__` to `return False` (broken order).
- **Result:** `test_totality_trichotomy` and `test_reflected_operators_consistent` FAILED (24 parametrized cases). `test_antisymmetry` and `test_transitivity` are guarded implications (`if a < b: ...`) that pass vacuously on the now-empty `<` relation — this is mathematically correct (the empty relation *is* antisymmetric and transitive; it fails only **totality**), so totality/trichotomy is the discriminating law and it correctly fires. The suite is therefore **non-vacuous**: a broken `__lt__` is caught.
- `models.py` was restored (`git checkout`) and is unmodified in git; the plan is TESTS-only.

## Issues Encountered
- basedpyright-strict flagged `operator.and_/or_/xor/lshift/rshift` as partially-unknown members and rejected `object`-typed comparison args. Resolved with the `getattr` `_binop` seam typed `(object, object) -> object` (no scattered ignores).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SC2 (order laws + no-arithmetic) is proven. Remaining Phase 10 work: SC1 oracle widening (plan 10-01), SC3 persistence quantification, SC5 docs (plans 10-03/10-04).
- No blockers introduced. `src/` untouched; the `Stance` enum is proven ABOUT, not modified.

## Self-Check: PASSED

- `tests/test_stance.py` — FOUND
- `.planning/phases/10-stance-formal-proof-docs/10-02-SUMMARY.md` — FOUND
- Commit `d0053b4` (Task 1) — FOUND
- Commit `73896d5` (Task 2) — FOUND

---
*Phase: 10-stance-formal-proof-docs*
*Completed: 2026-07-05*
