---
phase: 5
slug: edge-model-contraction-cascade
status: validated
nyquist_compliant: true
wave_0_complete: true
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

All rows in `tests/test_cascade.py`, parametrized over the `backend` fixture
(`params=["memory","ladybug"]`); ladybug variants SKIP when the extra is absent.

| Behavior | Plan | Requirement | Test Type | Automated Command (`tests/test_cascade.py::`) | Status |
|----------|------|-------------|-----------|-----------------------------------------------|--------|
| `add_edge` lays a typed edge, observable both directions | 05-02 | EDGE-01 | unit (both backends) | `test_add_edge_lays_typed_edge` | ✅ green |
| `add_edge` is idempotent (no dup, no raise on repeat) | 05-02 | EDGE-01 | unit | `test_add_edge_is_idempotent` | ✅ green |
| `add_edge` accepts each of the 3 generic `EdgeType`s | 05-02 | EDGE-01 | unit (parametrized) | `test_add_edge_each_generic_type` | ✅ green |
| `add_edge` to a missing endpoint is a silent no-op (D-07) | 05-02 | EDGE-01 | unit | `test_add_edge_missing_endpoint_is_silent_no_op` | ✅ green |
| `add_edge` idempotency agrees across both backends | 05-02 | EDGE-01 | parity | `test_add_edge_idempotency_both_backends_agree` | ✅ green |
| `get_impact` returns dependents-only (`direction="in"`); excludes start | 05-03 | EDGE-02 | unit/parity | `test_get_impact_dependents_only_parity` | ✅ green |
| `get_impact` walks the transitive dependent chain | 05-03 | EDGE-02 | unit (both backends) | `test_get_impact_transitive_*` | ✅ green |
| `get_impact` truncation/frontier signal (`ImpactResult.truncated`) | 05-03 | EDGE-02 | unit | `test_get_impact_*frontier*` / depth-bounded cases | ✅ green |
| `get_impact` re-fetch divergence RAISES, not skips (IN-01) | 05-03 | EDGE-02 | unit | `test_get_impact_reached_store_divergence_raises` | ✅ green |
| `traverse(direction=...)` port extension parity (in/out) | 05-01 | EDGE-02 | parity | `tests/test_backend_parity.py` + cascade direction cross-checks | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · 16 test functions in `test_cascade.py`, all green on memory; ladybug variants skip when the extra is absent.*

---

## Wave 0 Requirements

- [x] `traverse(direction=...)` port extension parity — `tests/test_backend_parity.py` + cascade cross-checks
- [x] `tests/test_cascade.py` — `MemoryCore.add_edge` (EDGE-01) and `get_impact` (EDGE-02), 16 tests
- [x] Reused existing conftest `backend` fixture / parametrization — no infra re-scaffold

*Existing pytest + Hypothesis infrastructure covers the framework; only new test modules are needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|

*All phase behaviors have automated verification — the cascade mechanism is deterministic and LLM-free.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-19

---

## Validation Audit 2026-06-19

| Metric | Count |
|--------|-------|
| Requirements audited | 2 (EDGE-01, EDGE-02) |
| Automated (COVERED) | 2 |
| Gaps found | 0 |
| Tests generated | 0 (`test_cascade.py` already covers add_edge + get_impact incl. D-07 no-op, IN-01 divergence-raises, direction parity) |
| Escalated | 0 |

`/gsd-validate-phase 5` (State A audit): the draft Per-Task Map was a TBD stub; replaced
with the as-built map from `tests/test_cascade.py` (16 functions). Re-run this session:
`tests/test_query_scope.py` + `tests/test_cascade.py` → **23 passed, 26 skipped
(ladybug-extra, expected)**. No gaps; metadata-completion only.
