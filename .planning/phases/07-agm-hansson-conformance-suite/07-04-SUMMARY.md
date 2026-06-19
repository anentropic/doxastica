---
phase: 07-agm-hansson-conformance-suite
plan: 04
subsystem: formal-conformance
tags: [formal-05, back-05, divergence, irony-join, dual-backend, parity]
requires:
  - src/doxastica/core.py (_current_tails rows->tails helper, MemoryCore._decode_value — 07-01)
  - tests/conftest.py (backend fixture, params=["memory","ladybug"])
  - tests/test_scope_at.py (MemoryCore(backend) injected-fixture-port precedent)
provides:
  - "tests/test_irony_join.py — FORMAL-05 two-scope divergence demo (one round-trip join + plain-Python oracle)"
  - "diverging_beliefs(core, scope_a, scope_b) test-level helper (ONE match_nodes scan -> per-scope _current_tails -> inner-join on belief_id -> decoded value-differs)"
affects: []
tech-stack:
  added: []
  patterns:
    - "Test-level divergence join (D-03a): one match_nodes('BeliefState', {}) scan, both scopes filtered in Python, each reduced via the 07-01 _current_tails helper, inner-joined on belief_id"
    - "Plain-Python expected oracle computed independently from known synthetic writes (D-03) — not by re-running the join under test"
key-files:
  created:
    - tests/test_irony_join.py
  modified: []
decisions:
  - "D-03a honored: the divergence-join helper stays TEST-LEVEL; core.py untouched, zero narrative naming in core"
  - "D-01a single-source: the join reuses the 07-01 _current_tails helper per scope rather than re-deriving the _order_key group-by-max"
  - "D-01/D-02: exactly ONE port round-trip (full-label scan), both scopes filtered in Python (the port AND-equality filter cannot express scope_id IN {a,b})"
metrics:
  duration: ~5m
  completed: 2026-06-19
  tasks: 1
  files: 1
---

# Phase 7 Plan 04: Two-Scope Divergence Demo (FORMAL-05) Summary

The FORMAL-05 showcase now demonstrates two scopes diverging on the same proposition
(`belief_id`) computed as exactly ONE port round-trip and verified against an independent
plain-Python oracle. A new `tests/test_irony_join.py` defines a TEST-LEVEL
`diverging_beliefs(core, scope_a, scope_b)` helper (a single `match_nodes("BeliefState", {})`
scan, both scopes filtered in Python, each reduced to its active current tails by reusing the
07-01 `_current_tails` helper, inner-joined on `belief_id`, emitting rows where the decoded
values differ). The test runs over the `backend` fixture so cross-backend parity (BACK-05)
falls out of the comparison to the plain-Python expected. `core.py` is untouched — the
narrative-adjacent demo stays test-level with neutral naming (D-03a).

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Two-scope divergence demo, one round-trip (FORMAL-05, D-01..D-03, BACK-05) | `3fd0fbc` | tests/test_irony_join.py |

## How the join is shaped (FORMAL-05 / D-01 / D-01a / D-02)

- **ONE port round-trip:** `core._backend.match_nodes("BeliefState", {})` — a single full-label
  scan. "Single query" = one round-trip; the synthetic data is small so the scan is cheap and
  honest. The two scopes are filtered SEPARATELY in Python (NOT two `match_nodes` calls, NOT two
  `query_scope` calls — the port's AND-equality filter cannot express `scope_id IN {a, b}`).
- **Per-scope current tails:** each scope's rows are reduced via the 07-01
  `_current_tails(rows, frozenset({Status.active}))` helper (D-01a single-source of the
  `_order_key` group-by-max + retracted-tail collapse). A retracted current tail means the
  belief is ABSENT, so it cannot diverge.
- **Inner-join on `belief_id` (D-02):** `belief_id` IS the scope-independent proposition id. A
  row is emitted only where BOTH scopes hold the proposition AND the DECODED values
  (`MemoryCore._decode_value`) differ. The SUPERSEDED ARCHITECTURE.md
  `CURRENT_STATE`/`HOLDS`/`belief_id_logical` Cypher is not used (none of those exist).

## The plain-Python oracle (D-03) and the covered edge cases

`test_irony_join_two_scopes_diverge` writes known synthetic data into a world scope and one
actor (= any non-world) scope, then computes the expected divergent set independently in plain
Python and compares order-insensitively. The synthetic data exercises every join edge case:

- `p_diverge` — shared, DIFFERING current values → the ONE expected divergent row.
- `p_agree` — shared, EQUAL current values → excluded (no divergence).
- `p_world_only` / `p_actor_only` — present in ONE scope only → excluded (inner join).
- `p_retracted` — shared and momentarily divergent, but the actor's current tail is RETRACTED
  (via `contract`) → excluded (a retracted current tail is absent, so the proposition cannot
  diverge — proves the helper's active-tail collapse is honored across the join).

## Boundary discipline (D-03a)

`src/doxastica/core.py` was NOT modified. The divergence-join helper lives entirely in the
test file with neutral naming (`diverging_beliefs(scope_a, scope_b)`); the only core surface
consumed is the generic 07-01 `_current_tails` helper and the `_decode_value` boundary. No
`ladybug` import, no constructed query string, no `BackendPort` widening (T-07-01 / T-07-IV).
The token `irony`/`actor` appears only in this file's docstrings, comments, the test name, and
test-data scope/local names — never as a core symbol; `world_truth`/`dramatic` appear nowhere.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `uv run pytest tests/test_irony_join.py -q` — 2 passed (`[memory]` + `[ladybug]`; ladybug
  driver present, both params ran and PASSED).
- ladybug param SKIPS (not fails) when the driver is absent — inherited from the `conftest.py`
  `importorskip` fixture (BACK-05 skip-not-fail).
- `grep -c 'match_nodes' tests/test_irony_join.py` → 1 (exactly one round-trip; the only
  `match_nodes` occurrence is the single code call).
- `grep -c 'query_scope' tests/test_irony_join.py` → 0; `grep -c 'import ladybug'` → 0.
- Narrative naming scan: `irony`/`actor` appear only in docstrings/comments/test-name/test-data;
  no core symbol; `world_truth`/`dramatic` absent.
- `git status` — `src/doxastica/core.py` untouched (D-03a boundary held).
- `uv run ruff check tests/test_irony_join.py` — all checks passed.
- `uv run basedpyright tests/test_irony_join.py` — 0 errors, 0 warnings, 0 notes.

## Known Stubs

None. The join computes real divergence from real synthetic writes; the expected side is an
independent plain-Python oracle (D-03), never a re-run of the helper under test.

## Self-Check: PASSED

- FOUND: tests/test_irony_join.py (`diverging_beliefs`, `test_irony_join_two_scopes_diverge`)
- FOUND commit: 3fd0fbc
