---
phase: 03-append-only-revision-spine-keystone
verified: 2026-06-16T00:30:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
overrides:
  - must_have: "Each write re-points exactly one CURRENT_STATE pointer per belief atomically in a single transaction (a port unit-of-work), and a structural-invariant test confirms CURRENT_STATE uniqueness holds after every operation on both backends"
    reason: "ROADMAP SC3 phrasing is superseded by CONTEXT.md D-01 (a recorded, decision-grade reversal equivalent to the Phase 1 floor-raise and Phase 2 D-03 reversal): current-state is DERIVED (ordering-max BeliefState per (scope, belief) under the UUID7 contract), never stored. There is no CURRENT_STATE edge/pointer/table by design. The functional guarantee (exactly one current per belief-in-scope, established atomically per write) is fully preserved; only the mechanism changes from a stored mutable pointer to a derived selection over immutable data. The SC3 structural-invariant test is correctly implemented as a Hypothesis consistency check (derived-current total + single-valued + chain-tail equivalence) on both backends in tests/test_invariants.py."
    accepted_by: "precondition_note_in_verification_request"
    accepted_at: "2026-06-16T00:30:00Z"
---

# Phase 3: Append-Only Revision Spine (Keystone) Verification Report

**Phase Goal:** The keystone the entire postulate suite assumes — scopes (including the privileged world scope), the Belief/BeliefState split with immutable chains, the single (derived) current per belief-in-scope established atomically per write, and the three core write operations (revise/expand/contract) — implemented against the backend port so it runs on both backends from the start.
**Verified:** 2026-06-16T00:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `get_or_create_scope` creates/returns named belief-holders; multiple scopes exist as independent peers; world scope exists and `contract()` raises `WorldScopeContractionError` before any write | VERIFIED | `core.py:124-139` — `get_or_create_scope` implemented; `core.py:301-303` — structural guard fires before `unit_of_work`; 22 spine tests pass including `test_get_or_create_scope`, `test_world_contract_raises`, `test_cross_scope_divergence` on both backends |
| 2 | `revise` installs a value as the current belief superseding prior; `expand` is mechanically identical; `contract` marks a belief retracted (never deletes); vacuous contract on absent belief is a no-op returning None | VERIFIED | `core.py:258-335` — all three ops implemented; `_append` lays SUPERSEDES edge when prior exists; `contract` copies stored value verbatim (no re-encode); `test_revise_supersedes`, `test_expand_equals_revise`, `test_contract_vacuity_and_acts` pass on both backends |
| 3 | Exactly one derived current per belief-in-scope established atomically per write; a structural-invariant Hypothesis test confirms derived-current is total + single-valued + chain-tail-equivalent after every operation on both backends (D-01 reframing — CURRENT_STATE is derived, not stored) | VERIFIED (override) | `core.py:156-181` — `_current` computes ordering-max over all statuses, returns None on retracted tail (D-01); `tests/test_invariants.py` — `RuleBasedStateMachine` with two `@invariant`s: current-total-single-valued + chain-tail equivalence (CHAIN-03/SC3), and chain immutability (CHAIN-02); 105 tests pass including 2 stateful machine runs (memory + ladybug). Note: the ROADMAP SC3 phrase "CURRENT_STATE pointer" is superseded by CONTEXT.md D-01 — the invariant is implemented as a consistency check, not an edge count. See `overrides` in frontmatter. |
| 4 | No operation deletes or mutates an existing BeliefState node or HAS_REVISION edge; `get_revision_chain(belief_id)` returns the full immutable version chain in (source_event_id, state_id) order | VERIFIED | `core.py:325-335` — `get_revision_chain` cross-scope, ordered by UUID7 contract; `BackendPort` has no delete primitive (ports.py), making deletion structurally impossible; `chain_is_immutable @invariant` in `test_invariants.py` verifies monotonic-non-decreasing BeliefState count; `test_revision_chain_order` (includes tiebreak) and `test_belief_state_split` pass on both backends |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/doxastica/models.py` | `WORLD_SCOPE_ID = '__world__'` module constant | VERIFIED | Line 34; dunder-wrapped per D-02; includes docstring citing reserved-id rule |
| `src/doxastica/__init__.py` | `WORLD_SCOPE_ID` re-export in `__all__` | VERIFIED | Line 11 (import), line 35 (`__all__`); importable as `from doxastica import WORLD_SCOPE_ID` |
| `src/doxastica/backends/ladybug.py` | `HAS_REVISION` REL table + `_EDGE_ENDPOINTS` map + no `CURRENT_STATE` table | VERIFIED | Lines 94-99 (`_EDGE_ENDPOINTS`); lines 191-197 (hub-form DDL `FROM Belief TO BeliefState`); no `CREATE REL TABLE` statement containing `CURRENT_STATE` (verified by grep) |
| `src/doxastica/core.py` | `get_or_create_scope`, `_current`, `_append`, `_ensure_scope`, `_hydrate`, `revise`, `expand`, `contract`, `get_revision_chain` bodies | VERIFIED | All methods present; driver-blind (no `import ladybug` at module level); `_encode_value`/`_decode_value` (base64-over-JSON) close DEF-02-01; `test_import_purity.py` (7 tests) confirms driver-blindness |
| `tests/test_revision_spine.py` | 11 named behavior tests, parametrized over both backends, constructing `MemoryCore(backend)` | VERIFIED | 22 collected tests (11 x 2 backends); constructs `MemoryCore(backend)` (grep count: 12); never `MemoryCore.in_memory()`; ruff-clean |
| `tests/test_invariants.py` | `RuleBasedStateMachine` with `@invariant`s proving derived-current consistency + chain immutability on both backends | VERIFIED | `_SpineMachine` with 2 `@invariant`s, `@precondition`, `Bundle`, `importorskip`; `MemorySpineMachine.TestCase` + `LadybugSpineMachine.TestCase` both collected; passes on both backends |
| `tests/test_backend_parity.py` | DEF-02-01 regression flipped from `xfail` to passing | VERIFIED | `test_value_string_round_trips_ladybug` is a plain passing test routed through `MemoryCore.revise` + `get_revision_chain`; no `@pytest.mark.xfail` decorator; docstring documents "was xfail" |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `core.py revise/expand` | `_backend` (BackendPort primitives) | `_append` calls `upsert_node` + `add_edge` + `_current` inside `unit_of_work` | WIRED | `core.py:238-255`: single `unit_of_work` context manager; 4 `add_edge` calls total (2 in `_append`, 2 in `contract`) |
| `core.py contract` | `WORLD_SCOPE_ID` guard | Structural `if scope_id == WORLD_SCOPE_ID` BEFORE `unit_of_work` | WIRED | `core.py:301`: guard is first statement, preceding the `with self._backend.unit_of_work()` at line 305 |
| `core.py _append` | `_encode_value` / `_hydrate _decode_value` | `_encode_value(value)` on write, `_decode_value(props["value"])` on hydrate | WIRED | `core.py:248` (encode); `core.py:214` (decode); base64-over-JSON closes DEF-02-01 brace-coercion on both backends |
| `ladybug.py add_edge` | `_EDGE_ENDPOINTS` / `_PK_BY_LABEL` | Per-edge-type endpoint label + PK lookup | WIRED | `ladybug.py:252`: `_EDGE_ENDPOINTS[str(edge_type)]` resolves FROM/TO labels; `HAS_REVISION` maps to `(Belief, BeliefState)` enabling hub-form edges |
| `tests/test_revision_spine.py` | `conftest.py backend fixture` | `def test_*(backend: BackendPort)` | WIRED | All 11 test functions accept `backend: BackendPort`; `conftest.py` parametrizes `["memory", "ladybug"]` with `importorskip` |
| `tests/test_invariants.py @invariant` | `MemoryCore._current` vs shadow model | `current-total-single-valued + chain-tail equivalence` | WIRED | `test_invariants.py:259-295`: invariant crosses `_current` against shadow oracle and `_chain_tail` (recomputed from public `get_revision_chain`) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `core.py revise` | `props` / `BeliefState` | `uuid.uuid7()` + `_encode_value(value)` + `BackendPort.upsert_node` | Yes — uuid7 minted fresh, value base64-encoded, node persisted | FLOWING |
| `core.py get_revision_chain` | `states` | `_backend.match_nodes("BeliefState", {"belief_id": belief_id})` | Yes — queries all persisted BeliefState nodes for the belief | FLOWING |
| `core.py _current` | `tail` | `_backend.match_nodes("BeliefState", {"scope_id": ..., "belief_id": ...})` then `max(...)` | Yes — queries and sorts in-memory; returns real ordering-max | FLOWING |
| `test_invariants.py chain_is_immutable` | `total` | `self._be.match_nodes("BeliefState", {})` | Yes — counts all persisted BeliefState nodes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `WORLD_SCOPE_ID` importable and equals `"__world__"` | `from doxastica import WORLD_SCOPE_ID; assert WORLD_SCOPE_ID == '__world__'` | Exits 0, prints `WORLD_SCOPE_ID ok: '__world__'` | PASS |
| Brace value `{"x": 2}` round-trips through `revise` + `get_revision_chain` | `c.revise('a','b',{'x':2},uuid.uuid7()); chain[-1].value == {'x':2}` | `data-flow ok: value round-trips through core` | PASS |
| World-scope contract raises before any write | `contract(WORLD_SCOPE_ID, ...)` raises + chain stays empty | `world-scope guard ok: raised before write` | PASS |
| Contract vacuity: no-op on absent belief | `contract('alice', 'absent', ...)` returns None, empty chain | `vacuity ok: no-op on absent belief` | PASS |
| Cross-scope divergence | `test_cross_scope_divergence[memory]` + `[ladybug]` | 2 passed | PASS |
| Full test suite (105 tests) | `UV_NO_SYNC=1 uv run --extra ladybug pytest -q` | 105 passed in 24.68s | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SCOPE-01 | 03-03 / 03-02 | `get_or_create_scope(scope_id)` creates/returns a named belief-holder | SATISFIED | `core.py:124-139`; `test_get_or_create_scope` passes on both backends |
| SCOPE-02 | 03-02 / 03-03 | Privileged world scope; `contract()` raises `WorldScopeContractionError` | SATISFIED | `core.py:301-303`; `test_world_contract_raises` passes; guard fires before any backend access |
| SCOPE-03 | 03-02 / 03-03 | Multiple scopes are independent peers; cross-scope divergence | SATISFIED | `_current` scoped to exact `(scope_id, belief_id)`; `test_cross_scope_divergence` passes |
| CHAIN-01 | 03-02 / 03-03 | `Belief`/`BeliefState` split — one belief per `Belief` node | SATISFIED | `_append` calls `upsert_node("Belief", ...)` then `upsert_node("BeliefState", ...)`; `test_belief_state_split` passes |
| CHAIN-02 | 03-04 | Append-only — no delete/mutate of `BeliefState` or `HAS_REVISION` | SATISFIED | `BackendPort` has no delete primitive; `chain_is_immutable @invariant` (monotonic state count) passes on both backends |
| CHAIN-03 | 03-04 | Exactly one derived current per belief-in-scope, atomically per write (D-01 reframing) | SATISFIED | `current_is_total_single_valued_and_chain_tail @invariant` passes 50 examples × 20 steps on both backends; single `unit_of_work` per public write |
| OPS-01 | 03-02 / 03-03 | `revise(scope, belief_id, value, source_event_id)` installs current, supersedes prior | SATISFIED | `core.py:258-266`; `test_revise_supersedes` passes; SUPERSEDES edge laid when prior exists |
| OPS-02 | 03-02 / 03-03 | `expand` adds a belief with no conflict check (AGM expansion reference) | SATISFIED | `core.py:268-282` — explicit delegate to `_append(..., Status.active)`, mechanically identical to `revise` (D-04); `test_expand_equals_revise` passes |
| OPS-03 | 03-02 / 03-03 | `contract` marks deprecated; never deletes; world-scope guarded | SATISFIED | `core.py:284-322`; vacuity (None on absent), retracted-copy (verbatim stored value), world-scope guard first; `test_contract_vacuity_and_acts` passes |
| HIST-02 | 03-02 / 03-03 | `get_revision_chain(belief_id)` returns full immutable chain | SATISFIED | `core.py:325-335`; cross-scope, ordered by `(source_event_id, state_id)`; `test_revision_chain_order` (includes tiebreak) passes |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/doxastica/backends/ladybug.py` | 338 | `return [], frontier_zero` | Info | Legitimate `max_depth=0` edge case in `traverse` — the `[]` is the empty `reached` set when no nodes are within depth; the frontier is computed correctly. Not a stub; the full traversal path is below for non-zero depths. |

No `TBD`, `FIXME`, `XXX`, `TODO`, `HACK`, or `PLACEHOLDER` markers found in any phase-3-modified file. No `@pytest.mark.xfail` decorators (the DEF-02-01 xfail was flipped to passing in plan 03-04). No stub patterns in implementation files.

### Human Verification Required

None. All phase-3 behaviors are mechanically verifiable and the full test suite is green.

### Gaps Summary

No gaps. All 10 requirements (SCOPE-01, SCOPE-02, SCOPE-03, CHAIN-01, CHAIN-02, CHAIN-03, OPS-01, OPS-02, OPS-03, HIST-02) are traceable to substantive, wired, data-flowing implementation. The test suite passes 105/105 on both backends in 24.68s.

One override applied: ROADMAP SC3's phrase "re-points exactly one CURRENT_STATE pointer" is superseded by CONTEXT.md D-01 (a recorded decision-grade reversal). The functional guarantee is satisfied via a Hypothesis consistency check instead of an edge-count invariant. The override is documented in the frontmatter and is pre-authorized by the `<critical_precedence_note>` in the verification request.

---

_Verified: 2026-06-16T00:30:00Z_
_Verifier: Claude (gsd-verifier)_
