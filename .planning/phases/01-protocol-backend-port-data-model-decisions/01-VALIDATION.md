---
phase: 1
slug: protocol-backend-port-data-model-decisions
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-14
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Retroactively audited 2026-06-19 (`/gsd-validate-phase 1`): the pre-execution draft
> Per-Task Map was replaced with the as-built requirement→test mapping. Every behavioral
> and structural requirement has automated verification; BACK-04 is a written-spec
> deliverable whose executable form is the Phase-7 BACK-05 conformance suite (green).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (+ hypothesis 6.x, basedpyright strict, ruff) |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` / `[tool.pyright]` / `[tool.ruff]` |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest && uv run basedpyright && uv run ruff check` |
| **Estimated runtime** | ~30 seconds (Phase-1 subset: ~0.3s, 22 tests) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest && uv run basedpyright && uv run ruff check`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task / Req | Plan | Requirement | Test Type | Automated Command | File Exists | Status |
|------------|------|-------------|-----------|-------------------|-------------|--------|
| scaffold | 01-01 | PKG-01 | build/type/lint | `uv run basedpyright && uv run ruff check && uv run pytest tests/test_doxastica.py -q` | ✅ | ✅ green |
| frozen taxonomy | 01-02 | DATA-05 | unit | `uv run pytest tests/test_models_frozen.py -q` (frozen + closed six-field BeliefState) | ✅ | ✅ green |
| frozen taxonomy | 01-02 | DATA-06 | unit | `uv run pytest tests/test_models_frozen.py -q` (exact Status/EdgeType membership + structural-edge exclusion) | ✅ | ✅ green |
| ImpactResult | 01-02 | DATA-04 | unit | `uv run pytest tests/test_models_frozen.py -q` (3-field + `reached` immutable tuple) | ✅ | ✅ green |
| closed filter | 01-02/03 | DATA-02 | unit | `uv run pytest tests/test_models_frozen.py tests/test_query_scope.py -q` (closed-four BeliefFilter; never a free str) | ✅ | ✅ green |
| import purity | 01-03 | DATA-01 | unit (AST scan) | `uv run pytest tests/test_import_purity.py -q` (backend-blind seam imports no `ladybug`) | ✅ | ✅ green |
| UUID7 ordering | 01-03 | DATA-03 | contract + behavior | source contract in `protocol.py`; behavior in `uv run pytest tests/test_revision_spine.py::test_revision_chain_order tests/test_scope_at.py::test_scope_at_deterministic_order tests/test_query_scope.py::test_query_scope_deterministic_order -q` | ✅ | ✅ green |
| backend port | 01-04 | BACK-01 | unit | `uv run pytest tests/test_port_distinct.py -q` (distinct Protocol; no run/query/execute; exactly 5 LPG primitives) | ✅ | ✅ green |
| port contract | 01-04 | BACK-04 | manual + downstream | `test -f docs/src/backend-contract.md` (relocated/published in Phase 8); executable form = Phase-7 BACK-05 conformance suite (green) | ✅ | ✅ manual-only |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `pyproject.toml` + scaffold — cookiecutter-python-uv-library, import name `doxastica` (PKG-01)
- [x] `tests/conftest.py` — shared fixtures (throwaway `:memory:` DB factory landed Phase 2)
- [x] hypothesis added to dev group — the AGM property-test engine

*Decision-grade phase: most verification is type-level (basedpyright strict), structural
(import-boundary + port-distinctness AST/Protocol asserts), and closed-set guards — all
automated. Only the BACK-04 prose contract is reviewer-confirmed (with an executable
conformance counterpart in Phase 7).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Backend-port contract drafted | BACK-04 | Written spec document (prose) | Reviewer confirms `docs/src/backend-contract.md` enumerates the constraints a third-party LPG backend must meet (7 constraints keyed to the port methods); its executable form is the Phase-7 BACK-05 conformance suite, which is green |

*Previously-listed manual items BACK-01 and DATA-05 are now AUTOMATED post-execution
(`test_port_distinct.py`, `test_models_frozen.py`) and moved into the Per-Task Map above.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-19

---

## Validation Audit 2026-06-19

| Metric | Count |
|--------|-------|
| Requirements audited | 9 (DATA-01..06, PKG-01, BACK-01, BACK-04) |
| Automated (COVERED) | 8 |
| Manual-only | 1 (BACK-04 — prose spec; executable form = BACK-05/Phase 7, green) |
| Gaps found | 0 |
| Tests generated | 0 (all coverage already present from execution) |
| Escalated | 0 |

Phase-1 test subset re-run this session: `tests/test_import_purity.py`,
`tests/test_models_frozen.py`, `tests/test_port_distinct.py`, `tests/test_doxastica.py`
→ **22 passed in 0.28s.** No gaps to fill; the draft was a metadata-completion gap only.
