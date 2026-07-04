---
phase: 9
slug: stance-value-layer-write-persistence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-04
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (+ pytest-cov 6.x, hypothesis 6.x) — already in dev group |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_stance.py tests/test_models_frozen.py -x -q` |
| **Full suite command** | `uv sync --locked --dev --extra ladybug && prek run --all-files` (CI parity) |
| **Estimated runtime** | ~30–60 seconds (quick ~5s) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_stance.py tests/test_models_frozen.py -x -q`
- **After every plan wave:** Run full parity suite incl. ladybug — `uv sync --locked --dev --extra ladybug && uv run pytest -q`
- **Before `/gsd-verify-work`:** `uv sync --locked --dev --extra ladybug && prek run --all-files` must be green
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 1 | STANCE-01 | — | N/A | unit | `uv run pytest tests/test_stance.py::test_stance_total_order -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | STANCE-06 | — | N/A | unit | `uv run pytest tests/test_stance.py::test_stance_arithmetic_and_cross_type_raise -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | STANCE-02 | — | N/A | unit | `uv run pytest tests/test_models_frozen.py -x` (six→seven field-set + `stance=` constructors) | ⚠️ retarget | ⬜ pending |
| TBD | 02 | 2 | STANCE-03 | — | N/A | parity | `uv run pytest tests/test_stance_persistence.py -x` (parametrized `backend` fixture) | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | STANCE-04 | — | N/A | parity | `uv run pytest tests/test_stance_persistence.py::test_contract_preserves_stance_verbatim -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | STANCE-05 | — | N/A | parity | `uv run pytest tests/test_stance_persistence.py::test_get_scope_at_reconstructs_stance -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task IDs finalized by the planner; this map tracks requirement → automated command coverage.*

---

## Wave 0 Requirements

- [ ] `tests/test_stance.py` — SC2 type-level total order + arithmetic/cross-type `TypeError` +
      `.name`/`Stance[...]` name-lookup guard (STANCE-01 / STANCE-06)
- [ ] `tests/test_stance_persistence.py` — SC4/SC5 byte-stable round-trip, optional-default,
      `contract`-verbatim, `get_scope_at` reconstruction (STANCE-03 / STANCE-04 / STANCE-05),
      parametrized on the existing dual-backend `backend` fixture
- [ ] Retarget `tests/test_models_frozen.py` closed-field-set assertion six → seven, and add
      `stance=` to the two direct `BeliefState(...)` constructors (D-01 fallout)
- [ ] No framework install needed — pytest / hypothesis / ladybug already in the dev + `[ladybug]`
      extra groups

*Discretion (per CONTEXT): the two new files may instead fold into `test_revision_spine.py` /
`test_backend_parity.py` alongside the sibling `value` round-trip tests — either satisfies SC4/SC5.
The full Hypothesis oracle-widening is STANCE-07, Phase 10, explicitly out of scope here.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
