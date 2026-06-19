---
phase: 07-agm-hansson-conformance-suite
verified: 2026-06-19T00:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
re_verification: null
gaps: []
deferred: []
human_verification: []
---

# Phase 7: AGM/Hansson Backend Conformance Suite Verification Report

**Phase Goal:** Assemble the M0 exit gate — the mechanically-verified proof that is the library's reason to exist — parameterised as a backend conformance suite: every registered backend must pass the same postulate + invariant tests, with the in-memory backend as the AGM oracle and ladybug conforming identically.
**Verified:** 2026-06-19
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The full suite is parameterised over every registered backend (BACK-05): in-memory oracle and ladybug pass identical postulate + invariant tests with no per-backend assertions | VERIFIED | `_SpineMachine` / `_ScopeAtMachine` expose dual `.TestCase` subclasses (Memory*/Ladybug*); `@given` single-op tests parametrized over `backend_kind`; `conftest.py` fixture params `["memory","ladybug"]` with `importorskip`; all 28 Phase 7 tests pass on both backends (15.31s, 0 failures) |
| 2 | AGM revision postulates K*2 Success, K*3 Inclusion, K*4 Vacuity, K*5 Consistency, K*6 Extensionality pass; Hansson Success, Inclusion, Relevance, Core-Retainment, Uniformity pass; all compared against an INDEPENDENT shadow oracle (anti-tautology) | VERIFIED | `agm_k2_success`, `agm_k3_inclusion`, `agm_k5_consistency` as `@invariant`s on `_SpineMachine`; `test_vacuity_k4`, `test_extensionality_k6` as `@given` tests; `_assert_hansson_success_inclusion`, `_assert_hansson_relevance`, `_assert_hansson_core_retainment` in `contract` rule; `test_uniformity` as `@given`; oracle (`_shadow_base`/`_shadow_current`) computes from `self.entries` only — never calls `query_scope` or `_current` (verified by code inspection) |
| 3 | Structural-invariant suite passes: `CURRENT_STATE` uniqueness, chain immutability, `get_scope_at ≡ replay`, world-scope no-contraction — named into the FORMAL-03 conformance set | VERIFIED | `current_is_total_single_valued_and_chain_tail`, `chain_is_immutable`, `world_contract_raises` as `@invariant`/`@rule` on `_SpineMachine`; `scope_at_equals_fold_for_every_cut` as `@invariant` on `_ScopeAtMachine`; `_FORMAL_03_CONFORMANCE_SET` tuple in `test_invariants.py` registers all 4 members; `_FORMAL_03_CONFORMANCE_MEMBER` constant in `test_scope_at.py` registers member 4 |
| 4 | AGM Recovery is present ONLY as a loud strict xfail with rationale; positive superseded-chain replacement tests pass on both backends | VERIFIED | `test_recovery_does_not_hold_for_belief_bases` marked `@pytest.mark.xfail(strict=True, reason=...)` — `strict=True` is on the mark itself (no global `xfail_strict` in `pyproject.toml`, only `addopts = "-v"`); reports `xfailed` not `xpassed`/`failed` (suite run confirms); `test_superseded_chain_replaces_recovery(backend)` passes on both backends asserting `["active","retracted","active"]` chain, `current == "vprime"`, retracted state retained, base not restored; `grep -c 'get_scope_at'` returns 0 |
| 5 | Irony/divergence join demonstrated on synthetic data: two scopes diverging on `belief_id` computed as ONE port round-trip, validated against an independent plain-Python oracle; no narrative naming in core | VERIFIED | `tests/test_irony_join.py::diverging_beliefs` performs exactly 1 `match_nodes("BeliefState", {})` call (`grep -c 'match_nodes'` returns 1); reuses `_current_tails` helper (D-01a); inner-joins on `belief_id`; expected oracle computed in plain Python from known writes (not by re-running the join); 4 edge cases covered (diverge, agree, single-scope, retracted); no `import ladybug`, no `query_scope` in test; `irony`/`actor`/`dramatic`/`world_truth` appear only in comments/docstrings/test names — no core symbols |
| 6 | The suite exits green with EXACTLY ONE xfail; no failures; suite is runnable on both backends | VERIFIED | `uv run pytest -q -rxX` → 194 passed, 1 xfailed, exit 0; Phase 7 files alone: 28 passed, 1 xfailed; ladybug backend cases all passed (ladybug is installed) |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_invariants.py` | AGM+Hansson postulate assertions on `_SpineMachine`; `_FORMAL_03_CONFORMANCE_SET` registry | VERIFIED | Contains `agm_k2_success`, `agm_k3_inclusion`, `agm_k5_consistency` @invariants; `test_vacuity_k4`, `test_extensionality_k6`, `test_uniformity` @given tests; `_assert_hansson_relevance`, `_assert_hansson_core_retainment` as two distinct named methods; `_FORMAL_03_CONFORMANCE_SET` tuple at line 704 |
| `tests/test_scope_at.py` | `scope_at_equals_fold_for_every_cut` registered as FORMAL-03 member | VERIFIED | `_FORMAL_03_CONFORMANCE_MEMBER = "scope_at_equals_fold_for_every_cut"` constant; registry comment block at lines 490-509; `fold` oracle reads only `self.entries` (verified body at lines 379-390) |
| `tests/test_recovery_xfail.py` | Strict-xfail Recovery counterexample + D-05 superseded-chain positives | VERIFIED | Created in commit b9bee7e; `@pytest.mark.xfail(strict=True, reason=...)` at line 43-47; `test_superseded_chain_replaces_recovery(backend)` asserts 4-part superseded-chain behaviour |
| `tests/test_irony_join.py` | Two-scope divergence demo: one `match_nodes` scan, plain-Python oracle, both backends | VERIFIED | Created in commit 3fd0fbc; `diverging_beliefs()` function; exactly 1 `match_nodes` call; 4 edge cases; independent expected oracle; `test_irony_join_two_scopes_diverge(backend)` parametrized via fixture |
| `src/doxastica/core.py` | `_current_tails(rows, allowed)` extracted helper; `query_scope` delegates to it | VERIFIED | `_current_tails` at line 115 with correct signature; `query_scope` at line 639 calls `_current_tails`; driver-blind (no `ladybug` import); `test_import_purity.py` green |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `test_invariants.py` postulate assertions | `_shadow_base` / `self.entries` (independent oracle) | Expected computed from oracle; SUT read via `_observed_base` (single call) | VERIFIED | `_shadow_base` body reads only `self.entries` + `_shadow_current`; `_shadow_current` reads only `self.entries`; no `query_scope` or `_current` call in oracle methods |
| `test_scope_at.py` `scope_at_equals_fold_for_every_cut` | `fold` oracle | `fold` uses `self.entries` winner selection; `get_scope_at` is compared against it, never called by it | VERIFIED | `fold` body (lines 379-390): pure Python `max(eligible, ...)` over `self.entries`; no `get_scope_at`/`_current_tail`/`query_scope` in body |
| `test_irony_join.py` `diverging_beliefs` | `_current_tails` helper + `MemoryCore._decode_value` | One `match_nodes` scan; `_current_tails` per scope; inner-join on `belief_id`; `_decode_value` on stored values | VERIFIED | `from doxastica.core import _current_tails` at line 43; call at lines 86-87; `MemoryCore._decode_value` at lines 90-91 |
| `src/doxastica/core.py` `query_scope` | `_current_tails` helper | Steps 3-4 of `query_scope` delegate to `_current_tails` | VERIFIED | `tails = list(_current_tails(rows, allowed).values())` at line 639 |
| `test_recovery_xfail.py` Recovery xfail | strict=True mark (no global xfail_strict) | `@pytest.mark.xfail(strict=True, ...)` on the mark; `pyproject.toml` has only `addopts = "-v"` | VERIFIED | `strict=True` confirmed at line 44; `pyproject.toml` grep shows only `addopts = "-v"`, no `xfail_strict` |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces test code and a pure Python helper, not a component that renders dynamic data from an external source. The postulate assertions flow data from the shadow oracle (self.entries) and compare it to SUT output (query_scope). This data-flow is verified via anti-tautology checks in the Key Link section above.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite green with exactly 1 xfailed | `uv run pytest -q -rxX` | 194 passed, 1 xfailed, exit 0 | PASS |
| Phase 7 files: 28 passed, 1 xfailed (both backends) | `uv run pytest tests/test_invariants.py tests/test_scope_at.py tests/test_recovery_xfail.py tests/test_irony_join.py -v -rxX` | 28 passed, 1 xfailed, exit 0 | PASS |
| Recovery reports xfailed (not xpassed) | Visible in suite output | `XFAIL tests/test_recovery_xfail.py::test_recovery_does_not_hold_for_belief_bases` | PASS |
| match_nodes called exactly once in irony join | `grep -c 'match_nodes' tests/test_irony_join.py` | 1 | PASS |
| No narrative naming in core | `grep -rniE 'irony\|actor\|dramatic\|world_truth' src/` | Only appears in comments/docstrings — no Python symbol names | PASS |

### Probe Execution

No probe scripts declared or conventional probe paths found for this phase. Phase 7 is a test-only phase; the test suite IS the probe, run directly via pytest above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FORMAL-01 | 07-01-PLAN.md | AGM revision postulate suite (K*2–K*6) via Hypothesis stateful tests against shadow oracle | SATISFIED | `agm_k2_success`, `agm_k3_inclusion`, `agm_k5_consistency` @invariants; `test_vacuity_k4`, `test_extensionality_k6` @given tests; all green |
| FORMAL-02 | 07-01-PLAN.md | Hansson base-contraction postulate suite (Success, Inclusion, Relevance, Core-Retainment, Uniformity) | SATISFIED | `_assert_hansson_success_inclusion`, `_assert_hansson_relevance`, `_assert_hansson_core_retainment` in contract rule; `test_uniformity` @given; phrased as superseded-chain (D-07) |
| FORMAL-03 | 07-01-PLAN.md + 07-02-PLAN.md | Structural-invariant suite: CURRENT_STATE uniqueness, chain immutability, get_scope_at ≡ replay, world-scope no-contraction | SATISFIED | `_FORMAL_03_CONFORMANCE_SET` tuple with 4 members; members 1-3 in `test_invariants.py`; member 4 in `test_scope_at.py` |
| FORMAL-04 | 07-03-PLAN.md | Recovery as strict xfail with rationale + positive superseded-chain replacement tests | SATISFIED | `@pytest.mark.xfail(strict=True)` at line 43; reports `xfailed`; `test_superseded_chain_replaces_recovery` passes on both backends |
| FORMAL-05 | 07-04-PLAN.md | Irony join on synthetic data — two scopes diverging on belief_id as one query | SATISFIED | `tests/test_irony_join.py`; 1 match_nodes call; plain-Python oracle; 4 edge cases; passes on both backends |
| BACK-05 | 07-01 through 07-04-PLAN.md | Backend conformance suite parametrized over every registered backend | SATISFIED | Transversal across all Phase 7 tests: stateful machines via dual TestCase subclasses; @given tests via `backend_kind` parametrize; fixture tests via `conftest.py` backend fixture; ladybug passes when present, SKIPS (not fails) when absent |

All 6 requirements mapped to Phase 7 in REQUIREMENTS.md are satisfied. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No `TBD`, `FIXME`, or `XXX` markers found in any phase-modified file. No stub/placeholder patterns. No hardcoded empty returns in meaningful code paths.

### Human Verification Required

None. All truths are mechanically verifiable and were verified. The suite itself IS the mechanically-verified proof — running it on both backends with a green result is the goal, and that was confirmed by direct pytest execution.

### Gaps Summary

No gaps. All 6 must-haves are verified against the actual codebase:

- Anti-tautology discipline confirmed: oracle methods operate on `self.entries` only, never calling `query_scope` or `_current`.
- The fold oracle in `test_scope_at.py` is independently confirmed free of SUT calls.
- Recovery xfail uses `strict=True` on the mark itself; no global override exists.
- The irony join uses exactly 1 `match_nodes` call; the expected oracle is independent.
- All 4 FORMAL-03 members are named in conformance set registries across the two files.
- The extracted `_current_tails` helper is wired into `query_scope` and the irony join (D-01a single-source).

---

_Verified: 2026-06-19_
_Verifier: Claude (gsd-verifier)_
