---
phase: 7
slug: agm-hansson-conformance-suite
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-19
validated: 2026-06-19
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> This phase **is** validation: it ships essentially no production code; every
> requirement is discharged by a test artifact. The map below is the proof.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + Hypothesis 6.x (stateful `RuleBasedStateMachine`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`addopts = "-v"` — note: NO `xfail_strict`, so D-04 strict must be on the mark) |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~30–90 seconds (Hypothesis examples + dual-backend parametrization) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q <touched test file>`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green (Recovery xfail counts as expected-fail, not red)
- **Max feedback latency:** ~90 seconds

---

## Per-Task Verification Map

> Each phase requirement maps to a concrete green test artifact. The suite
> parametrization over `params=["memory","ladybug"]` (conftest `backend` fixture)
> + the `Memory*`/`Ladybug*` `.TestCase` idiom satisfies BACK-05 transversally.
> Validated 2026-06-19: full suite `uv run pytest -q -rxX` → 194 passed, 1 xfailed
> on both backends (ladybug driver present).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-02 | 07-01 | 1 | FORMAL-01 | T-07-01/IV | AGM revision postulates (K*2/K*3/K*5 `@invariant`, K*4/K*6 `@given`) hold vs the independent shadow oracle | stateful/property | `uv run pytest tests/test_invariants.py -q` | ✅ | ✅ green |
| 07-01-03 | 07-01 | 1 | FORMAL-02 | — | Hansson base-contraction postulates (Success, Inclusion, Relevance, Core-Retainment, Uniformity) hold vs superseded-chain semantics | stateful/property | `uv run pytest tests/test_invariants.py -q` | ✅ | ✅ green |
| 07-01-03 / 07-02-01 | 07-01, 07-02 | 1 | FORMAL-03 | — | Named structural-invariant set (`CURRENT_STATE` uniqueness, chain immutability, `get_scope_at ≡ replay`, world-scope no-contraction) holds per backend | invariant | `uv run pytest tests/test_invariants.py tests/test_scope_at.py -q` | ✅ | ✅ green |
| 07-03-01/02 | 07-03 | 1 | FORMAL-04 | T-07-04 | Recovery is a strict `xfail` (`strict=True` on mark) reporting `xfailed`; superseded-chain positives pass | xfail+unit | `uv run pytest tests/test_recovery_xfail.py -q -rxX` | ✅ | ✅ green (1 xfailed) |
| 07-04-01 | 07-04 | 2 | FORMAL-05 | T-07-01/IV | Two scopes diverge on `belief_id` in ONE `match_nodes` round-trip vs a plain-Python oracle | unit | `uv run pytest tests/test_irony_join.py -q` | ✅ | ✅ green |
| (transversal) | 07-01..04 | 1–2 | BACK-05 | T-07-02 | Suite parameterised over every registered backend (memory oracle + ladybug); ladybug SKIPs when driver absent | parametrized | `uv run pytest -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_recovery_xfail.py` — Recovery strict-xfail counterexample + superseded-chain positives (FORMAL-04) — shipped 07-03
- [x] `tests/test_irony_join.py` — two-scope divergence on `belief_id` (FORMAL-05) — shipped 07-04
- [x] Extensions in/alongside `tests/test_invariants.py` — AGM + Hansson postulate assertions + D-08 named invariant set (FORMAL-01/02/03) — shipped 07-01; fold member registered in `tests/test_scope_at.py` (07-02)

*Existing infrastructure (`_SpineMachine`, conftest `backend` fixture, `test_scope_at.py` fold oracle) covered the harness and parametrization — this phase extended, not installed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification — the suite is the proof.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified 2026-06-19

---

## Validation Audit 2026-06-19

| Metric | Count |
|--------|-------|
| Requirements audited | 6 (FORMAL-01..05, BACK-05) |
| Covered (green automated) | 6 |
| Partial | 0 |
| Missing | 0 |
| Gaps found | 0 |
| Resolved | 0 (none needed) |
| Escalated to manual-only | 0 |

**State A audit (no auditor spawn needed):** every requirement already maps to a
green test artifact and the full suite is green on both backends — there were no
MISSING or PARTIAL gaps to fill. Verified directly: `uv run pytest -q -rxX` →
194 passed, 1 xfailed (the Recovery strict-xfail, expected). No new tests
generated; the conformance suite delivered in Phase 7 IS the validation.
