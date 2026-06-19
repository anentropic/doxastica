---
phase: 4
slug: retrieval-observation-surface
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-18
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (+ optional hypothesis 6.155.2 for the parity property) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`); shared fixtures in `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/test_query_scope.py -x -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~5 seconds (both backends; sub-second for the new file on memory) |

**Backend parametrization:** the existing `backend` fixture (`params=["memory", "ladybug"]`, `importorskip`) — every `query_scope` test runs on BOTH backends (D-05). No conftest change needed.

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_query_scope.py -x -q`
- **After every plan wave:** Run `uv run pytest -q` (must keep the Phase-3 `test_invariants.py` keystone green — proves the `_current_tail` refactor is behaviour-preserving)
- **Before `/gsd-verify-work`:** Full suite green on BOTH backends + basedpyright strict clean + ruff clean + the `include_deprecated` grep gate empty
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| query_scope default returns only `current+active`, one per belief | — | — | HIST-01 | — | N/A | unit (both backends) | `uv run pytest tests/test_query_scope.py::test_query_scope_active_only -x` | ✅ | ✅ green |
| `include_retracted=True` ALSO returns `current+retracted`; still one per belief | — | — | HIST-01 | — | N/A | unit (both backends) | `... ::test_query_scope_include_retracted -x` | ✅ | ✅ green |
| Explicit `filter.status` overrides the flag (precedence, D-03) | — | — | HIST-01 | — | N/A | unit | `... ::test_status_filter_precedence -x` | ✅ | ✅ green |
| `belief_ids` narrows the result set | — | — | HIST-01 | — | N/A | unit | `... ::test_belief_ids_filter -x` | ✅ | ✅ green |
| `event_id_min/max` POST-filter current tails; newer-than-max belief ABSENT not rewound (D-06) | — | — | HIST-01 | — | N/A | unit | `... ::test_event_range_postfilter -x` | ✅ | ✅ green |
| Event-range boundary inclusive at exact min/max (A1) | — | — | HIST-01 | — | N/A | unit | `... ::test_event_range_boundary_inclusive -x` | ✅ | ✅ green |
| Empty/absent scope returns `[]`, creates no `Scope` node (D-08) | — | — | HIST-01 | — | N/A | unit | `... ::test_empty_scope_returns_empty -x` | ✅ | ✅ green |
| Result is `_order_key`-sorted; in-memory ≡ ladybug sequence (D-07) | — | — | HIST-01 | — | N/A | unit (both backends) | `... ::test_query_scope_deterministic_order -x` | ✅ | ✅ green |
| No duplicate beliefs — exactly one state per `(scope,belief)` (D-01 postcondition / SC3) | — | — | HIST-01 | — | N/A | unit + (optional) property | `... ::test_no_duplicate_beliefs -x` | ✅ | ✅ green |
| Four-cell matrix: all of current+active, current+retracted, superseded+active, superseded+retracted distinguishable via `query_scope` + `get_revision_chain` (+ `SUPERSEDES`) | — | — | CHAIN-04 / SC2 | — | N/A | unit (both backends) | `... ::test_retracted_superseded_matrix -x` | ✅ | ✅ green |
| `query_scope` NEVER returns a superseded (non-tail) state (D-05) | — | — | CHAIN-04 | — | N/A | unit | `... ::test_query_scope_excludes_superseded -x` | ✅ | ✅ green |
| `_current` write-side contract unchanged after `_current_tail` refactor (Phase-3 keystone green) | — | — | HIST-01 (regression) | — | N/A | regression | `uv run pytest tests/test_invariants.py tests/test_revision_spine.py -q` | ✅ exists | ✅ green |
| No `include_deprecated` token remains in code or planning docs (D-03) | — | — | HIST-01 / CHAIN-04 (doc) | — | N/A | grep gate | `! grep -rn include_deprecated src tests .planning/REQUIREMENTS.md .planning/ROADMAP.md` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task/Plan/Wave columns are filled in by the planner once PLAN.md files exist; rows above are the requirement→test contract the plans must satisfy.*

---

## Wave 0 Requirements

- [x] `tests/test_query_scope.py` — covers HIST-01 (all rows above) + the CHAIN-04 four-cell matrix; parametrized over the existing `backend` fixture (11 named tests)
- [x] (optional) `_SpineMachine` query-scope invariant — the derived-active equivalence is covered by `test_invariants.py` (Phase-3 keystone) + `test_no_duplicate_beliefs`; discretionary extension not needed
- [x] No `conftest.py` change — the `params=["memory","ladybug"]` fixture is reused verbatim
- [x] No framework install — pytest + hypothesis already in the dev group

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-19

---

## Validation Audit 2026-06-19

| Metric | Count |
|--------|-------|
| Requirements audited | 2 (HIST-01, CHAIN-04) |
| Automated (COVERED) | 2 |
| Gaps found | 0 |
| Tests generated | 0 (full HIST-01 + CHAIN-04 contract already present in `test_query_scope.py`) |
| Escalated | 0 |

`/gsd-validate-phase 4` (State A audit): the draft Per-Task Map was a pre-execution
contract; every named row exists as a passing test in `tests/test_query_scope.py` (11
functions, one per row). Re-run this session: `tests/test_query_scope.py` +
`tests/test_cascade.py` → **23 passed, 26 skipped (ladybug-extra, expected)**. The D-03
`include_deprecated` grep gate passes (zero tokens). No gaps; metadata-completion only.
