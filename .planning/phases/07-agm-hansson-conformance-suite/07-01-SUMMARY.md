---
phase: 07-agm-hansson-conformance-suite
plan: 01
subsystem: formal-conformance
tags: [agm, hansson, hypothesis, stateful, conformance, back-05, formal-01, formal-02, formal-03]
requires:
  - tests/test_invariants.py (_SpineMachine keystone, Phase 3)
  - src/doxastica/core.py (query_scope, _order_key, _current, get_revision_chain)
  - tests/conftest.py (backend fixture)
provides:
  - "_current_tails(rows, allowed) pure rows->tails helper in core.py (D-01a single-source)"
  - "AGM K*2/K*3/K*5 @invariants + K*4/K*6 @given single-op tests on _SpineMachine"
  - "Hansson Success/Inclusion/Relevance/Core-Retainment @invariant assertions + Uniformity @given"
  - "_FORMAL_03_CONFORMANCE_SET named structural-invariant registry (D-08)"
affects:
  - 07-04 (irony/diverging-beliefs join consumes _current_tails)
tech-stack:
  added: []
  patterns:
    - "Single-op AGM/Hansson postulates as @given tests parametrized over backend KIND with a fresh per-example backend (not the function-scoped fixture — avoids the Hypothesis function_scoped_fixture health check + state bleed)"
    - "Hansson surgical-contraction postulates asserted inside the contract @rule over oracle-derived before/after bases"
key-files:
  created: []
  modified:
    - src/doxastica/core.py
    - tests/test_invariants.py
decisions:
  - "D-01a: extracted _current_tails into core.py (not a test-level helper) so query_scope and the Wave-2 join single-source the _order_key group-by-max"
  - "D-06a: K*4/K*6/Uniformity are @given single-op tests; sequence-sensitive postulates ride _SpineMachine @invariants"
  - "D-07: Relevance + Core-Retainment kept as two distinctly named methods though both collapse to the surgical symdiff-is-{p} claim"
metrics:
  duration: ~6m
  completed: 2026-06-19
  tasks: 3
  files: 2
---

# Phase 7 Plan 01: AGM/Hansson Conformance Postulate Suite Summary

The M0 exit-gate keystone now mechanically proves AGM revision postulates (K*2/K*3/K*5 as
`@invariant`s, K*4/K*6 as `@given` single-op tests), the five Hansson base-contraction postulates
(superseded-chain phrasing, D-07), and the named FORMAL-03 structural set — all comparing the core's
observed base against an independent shadow oracle and all running transversally on both backends
(BACK-05). A pure `_current_tails` rows->tails helper was extracted into `core.py` (D-01a),
single-sourcing the `_order_key` group-by-max that `query_scope` and the Wave-2 join share.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Extract `_current_tails` helper (D-01a) | `1f316da` | src/doxastica/core.py |
| 2 | AGM revision postulates (FORMAL-01, BACK-05) | `49bb764` | tests/test_invariants.py |
| 3 | Hansson postulates + FORMAL-03 registry (FORMAL-02/03, BACK-05) | `4d641a9` | tests/test_invariants.py |

## Extracted helper signature (for 07-04 to consume)

```python
def _current_tails(
    rows: list[dict[str, Any]],
    allowed: frozenset[Status],
) -> dict[str, dict[str, Any]]:
    """group already-scoped rows by belief_id -> per-belief _order_key MAX (over ALL statuses)
    -> status filter AFTER the max (Pitfall 2). Returns {belief_id: tail}."""
```

Module-level in `src/doxastica/core.py` (after `_is_active_tail`). Driver-blind: composes only
stdlib + `_order_key` / `Status` (no `ladybug` import; `test_import_purity.py` stays green).
`query_scope` steps 3-4 now delegate to it (behaviour-preserving — `test_query_scope.py` green).
The Wave-2 diverging-beliefs join (07-04) should call `_current_tails(rows, frozenset({Status.active}))`
per scope after one `match_nodes("BeliefState", {})` scan (D-01a — one round-trip).

## How the postulates are phrased (FORMAL-01 / FORMAL-02)

- **K*2 Success** (`agm_k2_success`, @invariant): every belief the oracle (`_shadow_base`) asserts
  is present in `query_scope` decoding to that value.
- **K*3 Inclusion** (`agm_k3_inclusion`, @invariant): `keys(observed) ⊆ keys(oracle)` (the ⊇
  direction is K*2; together they pin equality under `revise ≡ expand`).
- **K*5 Consistency** (`agm_k5_consistency`, @invariant): `query_scope` is single-valued — no
  `belief_id` appears twice.
- **K*4 Vacuity** (`test_vacuity_k4`, @given): revising a fresh `belief_id` == prior base ∪ {(p,v)},
  expected computed in plain Python.
- **K*6 Extensionality** (`test_extensionality_k6`, @given): `revise(s,p,v)` and `expand(s,p,v)`
  yield byte-identical bases.
- **Hansson Success/Inclusion** (`_assert_hansson_success_inclusion`): in the `contract` @rule,
  `keys(after) ⊆ keys(before)`, and the belief is dropped exactly when the oracle's ordering-max
  tail is retracted (handles colliding-event no-win contractions, Pitfall 6).
- **Hansson Relevance** (`_assert_hansson_relevance`): `symdiff(before, after) ⊆ {p}`.
- **Hansson Core-Retainment** (`_assert_hansson_core_retainment`): ∀ `belief_id ≠ p` the tail is
  byte-identical before/after. Kept as a distinct named method from Relevance (RESEARCH A2) though
  both collapse to the surgical claim under D-07.
- **Hansson Uniformity** (`test_uniformity`, @given): re-contracting the same key is idempotent at
  the base level (second contract is a D-05 vacuous no-op).

## FORMAL-03 named conformance set (D-08)

`_FORMAL_03_CONFORMANCE_SET` registry block names the three members already implemented on
`_SpineMachine` — `current_is_total_single_valued_and_chain_tail` (the CURRENT_STATE-uniqueness
THEOREM; no pointer edge), `chain_is_immutable`, `world_contract_raises` — plus the sibling
`scope_at_equals_fold_for_every_cut` (`tests/test_scope_at.py`, the lifted Phase-6 fold property).
Registered, not re-implemented, per D-08.

## Anti-tautology discipline (D-06 / Pitfall 2)

Every AGM/Hansson assertion computes its expected side ONLY from the independent oracle
(`_shadow_base` / `_shadow_current` / `self.entries`) or from plain-Python known writes — never a
second `query_scope` / `_current` read used as the source of truth. The `contract` rule confirms the
SUT agrees with the oracle on BOTH the before and after base, then asserts the surgical Hansson
claims over the oracle-derived bases.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `@given` single-op tests cannot consume the function-scoped `backend` fixture**
- **Found during:** Task 2
- **Issue:** Combining `@given` with the `conftest.py` function-scoped `backend` fixture trips
  Hypothesis's `function_scoped_fixture` health check (the fixture is not reset between generated
  inputs, and reusing one backend across examples would bleed state).
- **Fix:** Parametrized the single-op tests over `backend_kind` (`["memory", "ladybug"]`) and build a
  FRESH throwaway backend per Hypothesis example via a new `_build_backend(kind)` helper (mirrors
  `_make_backend` / `conftest.py`, with `importorskip` SKIP-not-fail + the 1 GiB ladybug cap +
  per-example close). This preserves BACK-05 (both backends) and fixes the state-bleed correctness
  risk the health check warns about.
- **Files modified:** tests/test_invariants.py
- **Commit:** `49bb764`

## Verification

- `uv run pytest -q` — 190 passed (both backends present).
- `uv run pytest tests/test_invariants.py -q` — 8 passed (2 stateful machines × invariants + 6 from
  the 3 `@given` tests × 2 backend kinds).
- ladybug-blocked run of `tests/test_invariants.py` — 4 passed, 4 SKIPPED (Ladybug cases SKIP, not
  fail, confirming BACK-05 skip-not-fail for the new `@given` tests).
- `uv run pytest tests/test_query_scope.py tests/test_import_purity.py -q` — green (helper extraction
  behaviour-preserving + driver-blind).
- `uv run basedpyright src tests` — 0 errors. `uv run ruff check .` — all checks passed.

## Known Stubs

None. All assertions are wired to the independent oracle / known writes; no placeholder data.

## Self-Check: PASSED

- FOUND: src/doxastica/core.py (`_current_tails` at line 115)
- FOUND: tests/test_invariants.py (`agm_k2_success`, `agm_k3_inclusion`, `agm_k5_consistency`,
  `_assert_hansson_relevance`, `_assert_hansson_core_retainment`, `test_vacuity_k4`,
  `test_extensionality_k6`, `test_uniformity`, `_FORMAL_03_CONFORMANCE_SET`)
- FOUND commit: 1f316da
- FOUND commit: 49bb764
- FOUND commit: 4d641a9
