---
phase: 6
slug: structural-time-travel
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-19
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` 9.1.0 + `hypothesis` 6.155.2 (the fold property is REQUIRED, D-07) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`); shared fixtures in `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/test_scope_at.py -x -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~30–60 seconds (bounded Hypothesis: `max_examples=50, stateful_step_count=20`) |

Every example test runs on BOTH backends via the existing `backend` fixture
(`params=["memory", "ladybug"]`, `importorskip`); the fold machine exposes two
`.TestCase` subclasses (`MemoryScopeAtFoldTest` + `LadybugScopeAtFoldTest`),
mirroring `tests/test_invariants.py`.

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_scope_at.py -x -q`
- **After every plan wave:** Run `uv run pytest -q` (includes the unchanged
  `tests/test_invariants.py` keystone + `tests/test_query_scope.py`, proving the
  `_current_tail`/`_is_active_tail` touch is behaviour-preserving, and
  `tests/test_import_purity.py` proving `core.py` stays driver-blind)
- **Before `/gsd-verify-work`:** Full suite green on BOTH backends + fold property
  green on both + basedpyright strict clean + ruff check clean
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Req / Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|----------------|----------|-----------|-------------------|-------------|--------|
| HIST-03 / D-03 | The cut REWINDS: revise→revise, `get_scope_at(scope, first_event)` returns the OLDER value (not absent, not newer) | unit (both backends) | `uv run pytest tests/test_scope_at.py::test_cut_rewinds_to_older_value -x` | ✅ | ✅ green |
| HIST-03 / D-04 | Inclusive cut: a state with `source_event_id == as_of` IS included | unit | `... ::test_cut_is_inclusive_at_boundary -x` | ✅ | ✅ green |
| HIST-03 / SC1 / D-04 | `get_scope_at(latest) == query_scope(current)` | unit (both backends) | `... ::test_scope_at_latest_equals_query_scope_now -x` | ✅ | ✅ green |
| HIST-03 / D-06 | Retracted-as-of: a belief contracted AT/BEFORE the cut is ABSENT; one contracted AFTER the cut is PRESENT at its as-of value | unit | `... ::test_retracted_as_of_collapse -x` | ✅ | ✅ green |
| HIST-03 / D-05 | A single multi-belief event folds ALL its writes inclusively; intra-event order uses the `state_id` tiebreak | unit | `... ::test_single_event_multi_belief_inclusive -x` | ✅ | ✅ green |
| HIST-03 / D-02 / D-08 | Absent/empty scope → `[]`, creates no `Scope` node; `get_scope_at(world, e)` is valid (no world-scope guard) | unit | `... ::test_empty_scope_and_world_read -x` | ✅ | ✅ green |
| HIST-03 / D-01 | Result is `_order_key`-sorted; in-memory ≡ ladybug sequence (no `traverse` consulted) | unit (both backends) | `... ::test_scope_at_deterministic_order -x` | ✅ | ✅ green |
| HIST-03 / SC2 / SC3 / D-07 | **`get_scope_at(scope, cut) == fold(ops, cut)`** for every cut, under Hypothesis, on BOTH backends — colliding + out-of-order `source_event_id`s, `as_of` stepped across event ids | property (stateful, both backends) | `uv run pytest tests/test_scope_at.py -k Fold -q` | ✅ | ✅ green |
| HIST-03 (regression) | Phase-3/4 surface unchanged — `_current`/`query_scope`/keystone still green after the `_is_active_tail` extraction | regression | `uv run pytest tests/test_invariants.py tests/test_query_scope.py tests/test_revision_spine.py -q` | ✅ | ✅ green |
| HIST-03 (purity) | `core.py` still imports no `ladybug` after adding `get_scope_at` (no driver, no Cypher) | regression | `uv run pytest tests/test_import_purity.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_scope_at.py` — NEW FILE. Covers HIST-03: cut-rewind example,
  inclusive-boundary, SC1 equivalence, retracted-as-of collapse, single-event
  multi-belief, absent/empty/world read, deterministic order (7 named tests × 2
  backends = 14 parametrized cases) — PLUS the operational-fold
  `_ScopeAtMachine` (two `.TestCase` subclasses, memory + ladybug) carrying the
  `fold(ops, as_of)` oracle and the `scope_at_equals_fold_for_every_cut`
  invariant (D-07).
- [x] No `conftest.py` change — the `params=["memory","ladybug"]` fixture is reused
  verbatim; the stateful machine reuses the `tests/test_invariants.py` `_make_backend`
  idiom (bounded `Database(max_db_size=2**30)`).
- [x] No framework install — `pytest` + `hypothesis` already in the dev group.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Audit 2026-06-19

| Metric | Count |
|--------|-------|
| Requirements audited | 1 (HIST-03) |
| Map rows | 10 |
| COVERED | 10 |
| PARTIAL | 0 |
| MISSING | 0 |

State A audit: all per-task map entries verified present and green. 7 named
example tests + the `_ScopeAtMachine` fold property (2 `.TestCase` subclasses)
confirmed in `tests/test_scope_at.py`; `-k Fold` passes 2/2 (both backends);
full suite 184 passed. No gaps — phase is Nyquist-compliant. No tests generated
(none were missing).

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified 2026-06-19
