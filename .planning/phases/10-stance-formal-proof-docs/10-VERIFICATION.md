---
phase: 10-stance-formal-proof-docs
verified: 2026-07-05T02:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 10: Stance Formal Proof & Docs — Verification Report

**Phase Goal:** Stance is mechanically *proven* correct, not vacuously green — the
dual-backend property suite tracks stance in its oracle and widens the base-comparison
key so K*6 Extensionality parity actually compares stance — and the docs showcase stance
as a within-scope epistemic gradient with reader-side comparison.
**Verified:** 2026-07-05
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Oracle records stance per entry; base key is `{belief_id: (value, stance)}`; non-vacuity proven | VERIFIED | `Entry = tuple[str, int, Any, str, Stance]` at line 144; `_shadow_base` / `_observed_base` / `_base_of` all return `(value, stance)` tuples; `test_widened_key_discriminates_stance` passes both backends; `event()` fires at 21–26% |
| SC2 | Order axioms exhaustively enumerated; no-arithmetic closure guard present | VERIFIED | `_PAIRS` (16), `_TRIPLES` (64); `test_totality_trichotomy` uses primitive `b<a`; `test_antisymmetry`; `test_transitivity`; `_ARITH` × `_PAIRS` = 192-case closure; all 388 cases pass |
| SC3 | Persistence holds for all 4 stance members × both backends | VERIFIED | `@pytest.mark.parametrize("stance", list(Stance))` on all 3 tests (8 cases per property); `is`-identity assertions retained; zero `@given` on fixture-based tests |
| SC4 | M0 conformance green on both backends; SKIP-not-fail without ladybug | VERIFIED | WITH extra: `573 passed, 1 xfailed`; WITHOUT extra: `467 passed, 88 skipped, 1 xfailed, 0 failures` |
| SC5 | Tutorial has gradient + reader-side decision + reconciliation; `mkdocs build --strict` green; no process-ID leakage | VERIFIED | `Stance.suspected/believed/certain` in tutorial; `stance >= Stance.believed` gate; `!!! warning` reconciliation callout; zero matches for `D-0\|STANCE-\|DOCS-\|Phase [0-9]\|SC[0-9]`; `mkdocs build --strict` exits 0 |

**Score:** 5/5 truths verified

---

### Non-Vacuity Verification (the load-bearing phase constraint)

The phase goal explicitly requires the tests to be NON-VACUOUS. Each SC was
checked against its vacuous-pass detection probe.

**SC1 — discrimination guard is not decorative:**
Both scopes in `test_widened_key_discriminates_stance` route through the actual
`_base_of` helper (lines 695–696 of `test_invariants.py`), not an inline
`{belief_id: (value, stance)}` literal. Because the discriminating assertion
`a != b` depends entirely on `_base_of`'s projection, reverting `_base_of` to
`{belief_id: value}` collapses both dicts to `{"b1": "v"}` and makes `a != b`
FALSE. The SUMMARY documents this revert was tested manually: the test failed with
`assert {'b1': 'v'} != {'b1': 'v'}`, then the widening was restored.

The `event()` label fires at **21.05% (memory)** and **26.32% (ladybug)** in
`--hypothesis-show-statistics`, confirming the stateful-oracle discriminating
path is actually generated, not merely reachable.

**SC2 — trichotomy form is not vacuous under the SC2 mutation probe:**
`test_totality_trichotomy` expresses the third term as `b < a` (primitive), not
`a > b` (derived). `@total_ordering` synthesizes `>` as `not (a < b) and a != b`,
so a broken `__lt__` (always `False`) leaves `a > b` reading `a != b` — the sum
stays 1 and the law passes vacuously on the plan's literal form. The executor
caught this and switched to `b < a`. The SUMMARY documents the mutation check:
24 failures under broken `__lt__`. VERIFIED non-vacuous.

**SC3 — exhaustive parametrize, not single-witness:**
Three `@pytest.mark.parametrize("stance", list(Stance))` decorators (one per
persistence property); `is`-identity assertions mean a `doubted`-only hydrate
bug raises for that member only. The SUMMARY documents the injection check:
exactly the 4 `doubted` cases raised while 20 other cases passed. VERIFIED.

**SC4 — SKIP not fail, not silent pass:**
`uv run pytest -q -rs` (without extra) observed: `467 passed, 88 skipped,
1 xfailed`, exit 0. Skip reasons visible in `-rs` output (`importorskip('ladybug'):
No module named 'ladybug'`). Zero ladybug failures. Zero silent passes. VERIFIED.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_invariants.py` | Stance-carrying oracle + non-vacuity proof | VERIFIED | `Entry` 5-tuple; `_shadow_base/observed_base/_base_of` all `(value, stance)`; `test_widened_key_discriminates_stance`; `event()` in revise/expand rules; `Stance[current["stance"]]` name-lookup |
| `tests/test_stance.py` | Exhaustive order-law enumeration + closure guard | VERIFIED | `_PAIRS`/`_TRIPLES`/`_ARITH`; 8 test functions; 388 collected cases total |
| `tests/test_stance_persistence.py` | Stance-quantified persistence proofs | VERIFIED | 3 × `@parametrize("stance", list(Stance))`; `is`-identity assertions; no `@given` |
| `src/doxastica/__init__.py` | `Stance` exported from package root | VERIFIED | `Stance` in import block and `__all__`; `uv run python -c "from doxastica import Stance"` exits 0 |
| `docs/src/tutorials/cluedo-detective.md` | Gradient + decision + reconciliation | VERIFIED | All three stance members; `stance >= Stance.believed`; `!!! warning` callout; package-root import |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_SpineMachine._shadow_base` | `_SpineMachine._observed_base` | tuple-equality on `(value, stance)` | WIRED | Both methods return `dict[str, tuple[Any, Stance]]`; compared in invariants |
| `revise`/`expand` rules | `hypothesis.event()` | stance-flip observability label | WIRED | Lines 241, 265 — emitted BEFORE oracle mirror; confirmed in statistics |
| `test_widened_key_discriminates_stance` | `_base_of` | both scopes projected through widened helper | WIRED | Lines 695–696 route through `_base_of`, not inline literal |
| `docs/src/tutorials/cluedo-detective.md` | `doxastica.Stance` | `from doxastica import Stance` | WIRED | Lines 77 and 364 (two code blocks) |
| reader-side comparison | `Stance.believed` | `culprit.stance >= Stance.believed` | WIRED | Line 207 of tutorial |

---

### Data-Flow Trace (Level 4)

Not applicable — all modified artifacts are test files and documentation. No dynamic-data rendering components. The tutorial code blocks execute against the real core and produce correct output (verified by SUMMARY's documented end-to-end run; `prek run --all-files` includes `blacken-docs` which would fail on non-executable code blocks).

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `Stance` importable from package root | `uv run python -c "from doxastica import Stance; assert Stance.certain.name == 'certain'; print('ok')"` | `ok` | PASS |
| Discrimination test passes both backends | `uv run pytest tests/test_invariants.py::test_widened_key_discriminates_stance -v` | `2 passed in 0.18s` | PASS |
| Full test suite with ladybug | `uv run pytest -q` | `573 passed, 1 xfailed` | PASS |
| Full test suite without ladybug | `uv sync --locked --dev && uv run pytest -q -rs` | `467 passed, 88 skipped, 1 xfailed` | PASS |
| `mkdocs build --strict` | `uv sync --locked --dev --group docs --extra ladybug && uv run mkdocs build --strict` | `Documentation built in 1.54 seconds` (exit 0) | PASS |
| `event()` stance-flip label appears | `uv run pytest tests/test_invariants.py -q --hypothesis-show-statistics` | `21.05%` (memory), `26.32%` (ladybug) | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| STANCE-07 | 10-01, 10-02, 10-03, 10-04 | Hypothesis property suite carrying stance non-vacuously | SATISFIED | Oracle widened (10-01); order laws enumerated (10-02); persistence quantified (10-03); K*6 compares stance (10-01) |
| DOCS-01 | 10-04 | Cluedo tutorial demonstrates within-scope gradient + reader-side comparison | SATISFIED | Tutorial Step 6 + reconciliation callout; `Stance` exported from root |

No orphaned requirements — only STANCE-07 and DOCS-01 are assigned to Phase 10 in REQUIREMENTS.md, and both are covered.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_invariants.py` | 623-627 | `# pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]` | Info | Legitimate — Hypothesis `.TestCase` is dynamically generated; these are the single boundary where the dynamic attribute must be touched |

No `TBD`/`FIXME`/`XXX` markers. No stubs. No empty implementations. No placeholder prose.

The code review (10-REVIEW.md, `status: issues_found`) identified two advisory warnings:
- **WR-01** (`_FORMAL_03_CONFORMANCE_SET` unchecked string registry): pre-existing drift risk in `test_invariants.py` and `test_scope_at.py`; all four names currently resolve; not a live break; not introduced by Phase 10.
- **WR-02** (imprecise `WORLD_SCOPE_ID` doc anchor): link resolves, `mkdocs build --strict` green; cosmetic inconsistency introduced in 10-04. Neither is a blocker.

---

### Human Verification Required

None. The VALIDATION.md listed one manual-only check (process-ID leakage grep on built tutorial). That check was performed programmatically during this verification:

```
grep -n "D-0\|STANCE-\|DOCS-\|Phase [0-9]\|\bSC[0-9]\b" docs/src/tutorials/cluedo-detective.md
```

Result: zero matches. All other checks were fully automated.

---

### Deviations Noted (not failures)

**SC3 quantification tool — `parametrize` vs `@given`:**
The roadmap SC3 says "hold under Hypothesis" but the implementation uses
`@pytest.mark.parametrize("stance", list(Stance))` (exhaustive over 4 members). This
is a deliberate pre-approved deviation documented in CONTEXT.md D-05 ("enumerate tiny
domains, Hypothesis for large ones") and D-08 ("and/or a sequence of revises").
Exhaustive parametrize over a 4-member domain is a complete proof; `@given` sampling
is weaker. The PLAN 10-03 `must_haves.truths` explicitly specifies parametrize, not
`@given`. Not flagged as a gap — the implementation is strictly stronger.

---

### Gaps Summary

No gaps. All five roadmap success criteria are verified. Both requirements (STANCE-07,
DOCS-01) are satisfied. The test suite is green on both backends. The docs build is
strict-clean. No process-ID leakage. All commit hashes documented in SUMMARYs confirmed
present in git history (`5d1bfa6`, `4e3af13`, `d0053b4`, `73896d5`, `fd2a195`, `3b35c73`,
`6730c73`, `562fb8a`, `b84f5f5`).

---

_Verified: 2026-07-05T02:00:00Z_
_Verifier: Claude (gsd-verifier)_
