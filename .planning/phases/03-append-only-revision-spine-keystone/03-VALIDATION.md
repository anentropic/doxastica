---
phase: 3
slug: append-only-revision-spine-keystone
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-16
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source of truth: each plan's `<verify><automated>` block + 03-RESEARCH.md §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (`>=8.0`) + pytest-cov; hypothesis `>=6.155` for the stateful machine — all over the parametrized `backend` fixture in `tests/conftest.py` (`params=["memory", "ladybug"]`, `importorskip("ladybug")`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`addopts = "-v"`); dev tooling (pytest, pytest-cov, hypothesis) already in the dependency group — no install |
| **Quick run command** | `UV_NO_SYNC=1 uv run --extra ladybug pytest tests/test_revision_spine.py -x` |
| **Full suite command** | `UV_NO_SYNC=1 uv run --extra ladybug pytest` (both backends) |
| **Estimated runtime** | ~30 seconds (spine quick run sub-30s; full suite incl. bounded Hypothesis stateful machine under ~30s) |

---

## Sampling Rate

- **After every task commit:** Run `UV_NO_SYNC=1 uv run --extra ladybug pytest tests/test_revision_spine.py -x` (the quick run; sub-30s)
- **After every plan wave:** Run `UV_NO_SYNC=1 uv run --extra ladybug pytest` (full both-backend suite + invariants)
- **Before `/gsd-verify-work`:** Full suite green on BOTH CI jobs — the base (pydantic-only) job (`UV_NO_SYNC=1 uv run pytest`, ladybug cases skip) and the ladybug job (`UV_NO_SYNC=1 uv run --extra ladybug pytest`); the DEF-02-01 xfail flipped to passing
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | SCOPE-02 (D-02) | — | N/A (constant + barrel export) | smoke | `UV_NO_SYNC=1 uv run python -c "from doxastica import WORLD_SCOPE_ID; assert WORLD_SCOPE_ID == '__world__'; print('ok')"` | ✅ (edits models.py/__init__.py) | ⬜ pending |
| 03-01-02 | 01 | 1 | CHAIN-02, HIST-02 (D-07) | T-03-01 / T-03-02 | DDL interpolates only `_NS_RE`-validated `{ns}` + fixed labels; edge endpoint ids are `$param` binds | smoke | `UV_NO_SYNC=1 uv run --extra ladybug python -c "<HAS_REVISION hub-edge probe>"` (prints `hub edge ok`) | ✅ (edits ladybug.py) | ⬜ pending |
| 03-03-01 | 03 | 1 | SCOPE-01/02/03, CHAIN-01, OPS-01/02/03, HIST-02 | T-03-07 / T-03-08 | authors the DEF-02-01 round-trip + retracted byte-identity + world-guard regression tests | scaffold (collect-only RED) | `UV_NO_SYNC=1 uv run --extra ladybug python -m pytest tests/test_revision_spine.py --collect-only -q` | ❌ W0 (this task creates it) | ⬜ pending |
| 03-02-01 | 02 | 2 | SCOPE-01/02/03, CHAIN-01 (D-01/D-02/D-06) | T-03-03 / T-03-05 | derives `is_world` in-core; values pass as `$param` binds (no Cypher in core) | unit (tdd) | `UV_NO_SYNC=1 uv run --extra ladybug pytest tests/test_revision_spine.py::test_get_or_create_scope tests/test_revision_spine.py::test_cross_scope_divergence -x` | ❌ W0 (03-03-01) | ⬜ pending |
| 03-02-02 | 02 | 2 | OPS-01/02/03, CHAIN-02/03, HIST-02 (D-03/D-04/D-05/D-07) | T-03-03 / T-03-04 / T-03-06 | json.dumps/json.loads value-encoding (DEF-02-01); world-guard before any write; append-only by construction | unit (tdd) | `UV_NO_SYNC=1 uv run --extra ladybug pytest tests/test_revision_spine.py -x` | ❌ W0 (03-03-01) | ⬜ pending |
| 03-04-01 | 04 | 3 | CHAIN-02, CHAIN-03 (D-01, SC3) | T-03-09 / T-03-10 | Hypothesis stateful: proves derived-current total+single-valued ≡ chain tail; chain immutability (monotonic state count) | invariant (stateful) | `UV_NO_SYNC=1 uv run --extra ladybug pytest tests/test_invariants.py -x` | ❌ W0 (this task creates it) | ⬜ pending |
| 03-04-02 | 04 | 3 | CHAIN-02 (DEF-02-01) | T-03-10 | flips the DEF-02-01 xfail to a passing core-routed regression (brace value round-trips byte-identically) | regression (xfail flip) | `UV_NO_SYNC=1 uv run --extra ladybug pytest tests/test_backend_parity.py -x` | ⚠️ exists as xfail — flip to passing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Wave ordering note:** Wave 1 = {03-01 (constant + ladybug schema), 03-03 (test scaffold)} run in parallel (no file overlap). Wave 2 = 03-02 (op bodies; `depends_on: [03-01, 03-03]` — needs both the `WORLD_SCOPE_ID`/`HAS_REVISION` plumbing and the RED scaffold its verify commands target). Wave 3 = 03-04 (invariants + DEF-02-01 flip; `depends_on: [03-02]`).

---

## Wave 0 Requirements

- [ ] `tests/test_revision_spine.py` — the Nyquist behavior scaffold (authored by 03-03 Task 1), covering SCOPE-01/02/03, CHAIN-01, OPS-01/02/03, HIST-02 + the DEF-02-01 brace round-trip, retracted byte-identity (Pitfall 2), and world-scope `is_world` bool (Pitfall 4), over the parametrized `backend` fixture, constructing `MemoryCore(backend)`. RED until 03-02 lands (correct).
- [ ] `tests/test_invariants.py` — the Hypothesis `RuleBasedStateMachine` consistency check + shadow-dict oracle (authored by 03-04 Task 1), run on both backends.
- [ ] `tests/conftest.py` — the parametrized `backend` fixture already exists (Phase 2); reused as-is, no change.
- [ ] Framework install: **none** — pytest + pytest-cov + hypothesis are already in the dev dependency group.

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification.* Every task above has an `<automated>` verify command; the SC3 structural invariant is the Hypothesis stateful machine (03-04-01), and the DEF-02-01 integrity fix is proven by the flipped regression (03-04-02). There are no visual, network, or interactive surfaces in this in-process library phase.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (03-02's verify commands target the 03-03 Wave-0 scaffold)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task has one)
- [x] Wave 0 covers all MISSING references (`tests/test_revision_spine.py` ← 03-03; `tests/test_invariants.py` ← 03-04)
- [x] No watch-mode flags (all commands are one-shot `pytest`/`python -c`)
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter (strategy fully populated; every task has an automated verify; plans already satisfy Nyquist sampling)
- [ ] `wave_0_complete: false` — Wave 0 (the test scaffolds in 03-03 / 03-04) has not executed yet

**Approval:** approved 2026-06-16
