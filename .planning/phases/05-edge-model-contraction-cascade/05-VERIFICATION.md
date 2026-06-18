---
phase: 05-edge-model-contraction-cascade
verified: 2026-06-18T23:30:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
---

# Phase 5: Edge Model & Contraction Cascade Verification Report

**Phase Goal:** Generic typed edges and the bounded contraction-cascade mechanism that the Relevance and Core-Retainment postulates are tested against — implemented against the port (the bounded var-length traversal primitive confirmed in the Phase 2 spike).
**Verified:** 2026-06-18T23:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `MemoryCore.add_edge(from_state_id, to_state_id, edge_type)` creates generic typed edges (closed EdgeType: SUPERSEDES/DEPENDS_ON/DERIVED_FROM) with no epistemic semantics in the core (EDGE-01) | ✓ VERIFIED | `core.py:414-444` — passthrough inside one `unit_of_work`; closed `EdgeType` enum enforced at signature; `test_add_edge_each_generic_type`, `test_add_edge_lays_typed_edge` pass on both backends |
| 2 | `get_impact(belief_state_id, depth)` performs bounded-depth dependency traversal that terminates on cyclic graphs and returns exactly the reachable-within-depth set (EDGE-02); traverses {DEPENDS_ON, DERIVED_FROM} with direction="in"; excludes the start node; closes hydration gap via match_nodes re-fetch | ✓ VERIFIED | `core.py:447-510`; `_CASCADE_EDGE_TYPES = frozenset({DEPENDS_ON, DERIVED_FROM})` at line 71-73; `direction="in"` literal at line 492; `match_nodes` re-fetch loop at lines 496-501; `test_get_impact_terminates_on_cycle` (Hypothesis), `test_get_impact_exact_reachable_within_depth` (Hypothesis), `test_get_impact_excludes_start`, `test_get_impact_full_hydration_parity` all pass |
| 3 | `get_impact` returns accurate truncation/frontier signal (`ImpactResult.frontier` / `truncated = len(frontier)>0`) whenever the cascade is cut off at the depth bound | ✓ VERIFIED | `core.py:507-509`: `frontier=frozenset(uuid.UUID(str(f)) for f in frontier)`, `truncated=len(frontier) > 0`; `test_get_impact_depth_bounded_frontier_parity` and `test_get_impact_depth_zero_parity` assert `truncated=True` and correct frontier on both backends |
| 4 | Driver-blindness preserved: no ladybug import in core.py/ports.py at module level; `tests/test_import_purity.py` passes | ✓ VERIFIED | `ports.py`: no ladybug import at all; `core.py`: ladybug appears only in docstrings/comments and inside function bodies (sanctioned, not module-level); `test_import_purity.py` 7 passed |
| 5 | Cross-backend parity tests exist and pass (in-memory and ladybug produce byte-identical results for both add_edge and get_impact) | ✓ VERIFIED | `test_cascade.py`: `test_get_impact_dependents_only_parity`, `test_get_impact_full_closure_parity`, `test_get_impact_depth_bounded_frontier_parity`, `test_get_impact_depth_zero_parity`, `test_get_impact_full_hydration_parity` all use `_both_backends()` loop and assert cross-backend equality |
| 6 | Full test suite is green | ✓ VERIFIED | `uv run pytest -q` — 165 passed, 0 failures |
| 7 | Phase-5 tests are MECHANISM-only (no AGM Relevance/Core-Retainment postulate tests — Phase 7 scope boundary respected) | ✓ VERIFIED | `test_cascade.py` docstring explicitly states "The AGM Relevance/Core-Retainment POSTULATE tests are Phase 7 — NOT here"; `grep` confirms no `AGM`, `postulate`, `Relevance`, `Core.Retainment`, or `FORMAL` test names or markers in `test_cascade.py` |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/doxastica/ports.py` | `BackendPort.traverse` with keyword-only `direction: Literal["in","out"]="out"` + extended docstring | ✓ VERIFIED | Lines 96-125: signature confirmed, `Literal` imported, `"out"` default, docstring covers both directions |
| `src/doxastica/backends/memory.py` | Reverse-adjacency `_in_edges` + direction-routed traverse | ✓ VERIFIED | `_in_edges` at lines 195-215 (O(edges) predecessor scan); `traverse` selects `neighbours` at line 143 |
| `src/doxastica/backends/ladybug.py` | Arrow-flipped traverse (main query, EXISTS subquery, bound==0 probe) | ✓ VERIFIED | `lhs, rhs` derived at line 364; FLIP 1 (bound==0 probe, lines 393-403); FLIP 2+3 (main query + EXISTS frontier, lines 414-419); cap-raise/restore direction-agnostic (lines 426-434) |
| `docs/backend-contract.md` | BACK-04 §2 traverse bullet documenting the direction parameter | ✓ VERIFIED | 4 lines with "direction" including: `direction="out"` default, `"in"` walks predecessors, both backends must agree |
| `tests/test_backend_parity.py` | Reverse-direction parity cases incl. `max_depth=0` and byte-identical both-backends | ✓ VERIFIED | 11 new cases: `test_reverse_chain_full_unbounded`, `test_reverse_source_has_no_predecessors`, `test_reverse_max_depth_zero_frontier`, `test_reverse_max_depth_zero_no_frontier`, `test_reverse_max_depth_bounded`, and `test_both_backends_reverse_diamond_byte_identical`; all pass |
| `src/doxastica/core.py` | `MemoryCore.add_edge` body + `def get_impact` + `_CASCADE_EDGE_TYPES` constant | ✓ VERIFIED | `add_edge` at lines 414-444; `get_impact` at lines 447-510; `_CASCADE_EDGE_TYPES` at lines 71-73 |
| `tests/test_cascade.py` | `add_edge` mechanism tests + `get_impact` mechanism + property tests (26 total, both backends) | ✓ VERIFIED | 26 tests collected and passed: 13 add_edge (idempotency, D-07 no-op, all 3 EdgeTypes, both backends) + 13 get_impact (dependents-only, DERIVED_FROM, excludes-start, SUPERSEDES-excluded, full-closure, depth-bounded, depth-0, Hypothesis cycle-termination, Hypothesis exact-reachable-within-depth, full-hydration parity) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `core.py MemoryCore.add_edge` | `self._backend.add_edge(edge_type, str(from_id), str(to_id))` | inside `with self._backend.unit_of_work()` | ✓ WIRED | Lines 441-444 confirm single passthrough in one UoW |
| `core.py MemoryCore.get_impact` | `self._backend.traverse(str(belief_state_id), _CASCADE_EDGE_TYPES, depth, direction="in")` | driver-blind compose | ✓ WIRED | Lines 487-492 |
| `core.py get_impact hydration` | `self._backend.match_nodes("BeliefState", {"state_id": sid})` then `_hydrate` | re-fetch full props per reached state_id | ✓ WIRED | Lines 496-501 |
| `memory.py traverse` | `self._in_edges if direction == "in" else self._out_edges` | neighbour-fn selection | ✓ WIRED | Line 143 |
| `ladybug.py traverse` | `lhs, rhs = ("<-", "-") if direction == "in" else ("-", "->")` then 3 interpolation sites | closed-Literal arrow pair | ✓ WIRED | Lines 364, 395, 415, 419 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `core.py get_impact` | `reached_rows, frontier` | `self._backend.traverse(...)` — real graph walk over `_CASCADE_EDGE_TYPES` | Yes — both backends perform real BFS/Cypher traversal over stored nodes | ✓ FLOWING |
| `core.py get_impact` hydration | `props` list | `self._backend.match_nodes("BeliefState", {"state_id": sid})` per reached row | Yes — re-fetches full node props from real storage | ✓ FLOWING |
| `ImpactResult.reached` | `tuple(self._hydrate(p) for p in props)` | `_hydrate` decodes base64-encoded value field, builds `BeliefState` | Yes — `test_get_impact_full_hydration_parity` asserts all six fields populated with real values | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `get_impact` returns correct directional dependents | `pytest tests/test_cascade.py::test_get_impact_dependents_only_parity -v` | 1 passed (B depends on A: get_impact(A)=={B}, get_impact(B)=={}) | ✓ PASS |
| SUPERSEDES excluded from cascade | `pytest tests/test_cascade.py::test_get_impact_supersedes_excluded_parity -v` | 2 passed (memory + ladybug) | ✓ PASS |
| Full hydration parity across backends | `pytest tests/test_cascade.py::test_get_impact_full_hydration_parity -v` | 1 passed (all six BeliefState fields populated, memory==ladybug) | ✓ PASS |
| Import purity (no ladybug in driver-free spine) | `pytest tests/test_import_purity.py -v` | 7 passed | ✓ PASS |
| Full suite regression | `uv run pytest -q` | 165 passed | ✓ PASS |
| basedpyright strict | `uv run basedpyright src/doxastica tests` | 0 errors, 0 warnings, 0 notes | ✓ PASS |

### Probe Execution

No conventional `scripts/*/tests/probe-*.sh` probes declared for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| EDGE-01 | 05-02-PLAN.md | `add_edge(from_state, to_state, edge_type)` for generic typed edges SUPERSEDES/DEPENDS_ON/DERIVED_FROM (no epistemic semantics in core) | ✓ SATISFIED | `MemoryCore.add_edge` at `core.py:414-444`; closed `EdgeType` enum; D-07 silent no-op; idempotent; 13 add_edge tests pass on both backends |
| EDGE-02 | 05-01-PLAN.md, 05-03-PLAN.md | `get_impact(belief_state_id, depth)` performs bounded-depth, cycle-safe dependency traversal (the contraction cascade mechanism) | ✓ SATISFIED | `MemoryCore.get_impact` at `core.py:447-510`; `direction="in"` over `{DEPENDS_ON, DERIVED_FROM}`; `ImpactResult(reached, frontier, truncated)`; Hypothesis cycle-termination + exact-reachable-within-depth property tests pass |

No ORPHANED requirements: EDGE-01 and EDGE-02 are the only requirements mapped to Phase 5 in REQUIREMENTS.md traceability table (lines 211-212), and both are covered by plans 05-01/02/03.

### Anti-Patterns Found

No `TBD`, `FIXME`, or `XXX` markers found in any Phase-5 modified file. No stub patterns found. The VALIDATION.md has `status: draft` but that is a pre-execution planning document, not a modified file.

The code review (05-REVIEW.md) identified 3 warnings and 3 info items. These are recorded for completeness — none rise to BLOCKER status for phase goal achievement:

| Finding | File | Severity (Review) | Impact on Phase Goal |
|---------|------|-------------------|----------------------|
| WR-01: cap-restore writes `_DEFAULT_HOP_CAP` (30), not the tenant's prior value | `ladybug.py:426-434` | Warning | No impact on correctness for standalone use; a tenant with a custom cap could be silently reset. Advisory for future injected-connection hardening. |
| WR-02: N+1 unbatched `match_nodes` re-fetches with no atomic read scope | `core.py:495-502` | Warning | Consistency gap under concurrent writes (the single-writer model makes this unlikely in practice); performance concern deferred from v1 scope. Does not affect the mechanism tests or parity assertions. |
| WR-03: `_DEPTH_CEILING = 1_000_000` interpolated as literal `*1..1000000` | `ladybug.py:79, 415` | Warning | "Full closure" is technically `depth=1_000_000`, not truly unbounded. A real 1M-hop graph would silently under-report. Advisory only; no real belief graph approaches this in M0 scope. |
| IN-01: silent skip on empty `match_nodes` re-fetch masks invariant breach | `core.py:500-501` | Info | A defensive `if fetched:` guard silently drops a reached node whose re-fetch fails. Should raise but does not. No evidence of a real invariant breach in tests. |
| IN-02: unknown `direction` silently treated as `"out"` | `memory.py:143`, `ladybug.py:364` | Info | The `Literal` is statically enforced; a runtime typo would fall through to outgoing walk. Advisory only. |
| IN-03: `_in_edges` is O(nodes × edges) | `memory.py:195-215` | Info | Performance concern; in-memory is the oracle/Phase-7-test backend, not the production hot path. Advisory for future reverse-index pass. |

None of the above findings block the phase goal. The review found 0 critical defects.

### Human Verification Required

None. All phase behaviors are deterministic, LLM-free, and fully covered by automated tests. The VALIDATION.md itself notes: "All phase behaviors have automated verification."

### Gaps Summary

No gaps. All 7 must-have truths are VERIFIED, all artifacts are WIRED and FLOWING, both requirement IDs (EDGE-01, EDGE-02) are satisfied, the full suite is green (165/165), basedpyright is 0 errors, no debt markers, and the Phase 7 scope boundary (no AGM postulate tests here) is respected.

---

_Verified: 2026-06-18T23:30:00Z_
_Verifier: Claude (gsd-verifier)_
