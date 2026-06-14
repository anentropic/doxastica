---
phase: 2
slug: backend-adapters-schema-bootstrap-de-risking-spike
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-15
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + hypothesis 6.x (via uv) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~10–30 seconds (in-memory `:memory:` backends; no disk/network) |

**Two-environment note (D-03):** validation runs in BOTH dependency environments:
- **base** (`uv sync` without the `ladybug` extra) → in-memory backend subset + the import-purity
  test must pass with `ladybug` genuinely absent. This is what proves D-02 isolation.
- **`[ladybug]`** (`uv sync --extra ladybug` + dev group) → full suite parametrized over BOTH
  backends.

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest` (both env jobs where the wave touches packaging/isolation)
- **Before `/gsd-verify-work`:** Full suite green in both the base and `[ladybug]` environments
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Populated by the planner/executor as tasks are created. Every task must map to an automated
> command or a Wave 0 dependency.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | BACK-03 | — | in-memory backend satisfies BackendPort | unit | `uv run pytest tests/backends -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | FORMAL-06 | — | parametrized `:memory:` fixture, no state bleed | unit | `uv run pytest tests/conftest_smoke -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | BACK-02, CONN-01 | — | ladybug adapter; injected conn never closed | unit | `uv run pytest tests/backends -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | CONN-02, CONN-03 | T-02-01 | namespaced sole-writer subgraph; idempotent DDL | unit | `uv run pytest tests/backends -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/backends/` — test package for backend conformance (both adapters)
- [ ] `tests/conftest.py` — parametrized `backend` fixture over `[InMemoryBackend, LadybugBackend]`, throwaway `:memory:` per example
- [ ] Extend `tests/test_import_purity.py` — assert `doxastica`, `doxastica.core`, `doxastica.backends.memory` import with `ladybug` absent; `MemoryCore.in_memory()` works driver-free
- [ ] A backend-conformance/parity suite (oracle parity, D-05) including frontier semantics on diamond/cycle/over-bound graphs (research Open Question 1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SC4 spike confirmations are documented (30-hop cap, `$param`-in-bound rejection, ACYCLIC unbounded traversal) | BACK-02 | The spike is a *confirmation that the port is unchanged* — its evidence lives in RESEARCH.md and a spike note, not a runtime assertion | Verify RESEARCH.md SC4 findings are reflected in `LadybugBackend.traverse` (validated-int bound, raised `var_length_extend_max_depth`) and that a decision "port unchanged, SC4 confirmed" is recorded |
| Two-env CI runs a job WITHOUT the ladybug extra | BACK-03 | CI YAML executes in GitHub Actions, not pytest | Confirm CI matrix has a base-install job that runs import-purity with ladybug absent |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
