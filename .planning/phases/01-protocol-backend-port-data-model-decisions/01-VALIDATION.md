---
phase: 1
slug: protocol-backend-port-data-model-decisions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-14
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (+ hypothesis 6.x, basedpyright strict, ruff) |
| **Config file** | none — Wave 0 installs from cookiecutter scaffold |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest && uv run basedpyright && uv run ruff check` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest && uv run basedpyright && uv run ruff check`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | PKG-01 | — | N/A | build | `uv run basedpyright` | ❌ W0 | ⬜ pending |

*Planner refines this table from the final PLAN.md task breakdown. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` + scaffold — cookiecutter-python-uv-library, import name `doxastica`
- [ ] `tests/conftest.py` — shared fixtures (throwaway `:memory:` DB factory, deferred to storage phases)
- [ ] hypothesis added to dev group — the AGM property-test engine

*Decision-grade phase: most verification is type-level (basedpyright strict) and structural (import-boundary asserts), not runtime behavior.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Backend-port granularity decision recorded | BACK-01 | Written design decision, not executable | Reviewer confirms ADR/decision record names LPG-primitive choice + Phase 2 spike tension |
| Backend-port contract drafted | BACK-04 | Written spec document | Reviewer confirms `docs/backend-contract.md` enumerates the constraints a third-party LPG backend must meet |
| UUID7 ordering contract written | DATA-05 | Written contract | Reviewer confirms the `source_event_id` ordering contract is documented |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
