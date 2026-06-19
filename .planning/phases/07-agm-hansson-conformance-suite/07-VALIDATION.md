---
phase: 7
slug: agm-hansson-conformance-suite
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-19
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

> Filled per-plan during planning. Each phase requirement maps to a concrete
> test artifact; the suite parametrization over `params=["memory","ladybug"]`
> (conftest `backend` fixture) satisfies BACK-05 transversally.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | FORMAL-01 | — | AGM revision postulates hold vs shadow oracle | stateful/property | `uv run pytest tests/test_invariants.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FORMAL-02 | — | Hansson base-contraction postulates hold | stateful/property | `uv run pytest tests/test_invariants.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FORMAL-03 | — | Structural invariants hold per backend | invariant | `uv run pytest tests/test_invariants.py` | ✅ (extends) | ⬜ pending |
| TBD | TBD | TBD | FORMAL-04 | — | Recovery is strict xfail; superseded-chain positives pass | xfail+unit | `uv run pytest tests/test_recovery_xfail.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | FORMAL-05 | — | Two scopes diverge on belief_id, one round-trip | unit | `uv run pytest tests/test_irony_join.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | BACK-05 | — | Suite parameterised over every registered backend | parametrized | `uv run pytest` | ✅ (conftest) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_recovery_xfail.py` — Recovery strict-xfail counterexample + superseded-chain positives (FORMAL-04)
- [ ] `tests/test_irony_join.py` — two-scope divergence on `belief_id` (FORMAL-05)
- [ ] Extensions in/alongside `tests/test_invariants.py` — AGM + Hansson postulate assertions + D-08 named invariant set (FORMAL-01/02/03)

*Existing infrastructure (`_SpineMachine`, conftest `backend` fixture, `test_scope_at.py` fold oracle) covers the harness and parametrization — this phase extends, not installs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification — the suite is the proof.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
