---
phase: 5
slug: edge-model-contraction-cascade
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-18
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + Hypothesis 6.x (stateful + `@given`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest --cov` |
| **Estimated runtime** | ~30 seconds (in-memory backend default; ladybug parity via `:memory:`) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest --cov`
- **Before `/gsd-verify-work`:** Full suite must be green, including cross-backend parity tests
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

> Filled during planning. Every EDGE-01 / EDGE-02 task maps to an automated pytest/Hypothesis test.
> Cross-backend parity (in-memory oracle vs ladybug) is a MANDATORY verification dimension for
> every `traverse`/`get_impact` behavior (per CONTEXT + RESEARCH parity findings).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | EDGE-01 / EDGE-02 | — | N/A (no untrusted input; Cypher is `$param`-bound) | unit + property | `uv run pytest -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test module(s) for `traverse(direction=...)` port extension — parity across both backends
- [ ] Test module(s) for `MemoryCore.add_edge` (EDGE-01) and `get_impact` (EDGE-02)
- [ ] Reuse existing conftest fixtures / backend-parametrization (do not re-scaffold infra)

*Existing pytest + Hypothesis infrastructure covers the framework; only new test modules are needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|

*All phase behaviors have automated verification — the cascade mechanism is deterministic and LLM-free.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
