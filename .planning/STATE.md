---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
stopped_at: Completed 05-01-PLAN.md
last_updated: "2026-06-19T07:37:32.127Z"
last_activity: 2026-06-19
progress:
  total_phases: 8
  completed_phases: 6
  total_plans: 19
  completed_plans: 19
  percent: 75
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-13)

**Core value:** A correct, append-only belief-revision core behind a clean `BeliefStore` Protocol whose correctness is *provable* — AGM/Hansson postulate compliance and structural invariants verified mechanically, zero narrative semantics leaking in.
**Current focus:** Phase 06 — structural-time-travel

## Current Position

Phase: 7
Plan: Not started
Status: Phase complete — ready for verification
Last activity: 2026-06-19

Progress: [██████████] 100% (4/4 plans)

## Performance Metrics

**Velocity:**

- Total plans completed: 19
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4 | - | - |
| 02 | 4 | - | - |
| 03 | 4 | - | - |
| 04 | 2 | - | - |
| 05 | 3 | - | - |
| 06 | 2 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01 P01 | 2 | 3 tasks | 29 files |
| Phase 01 P02 | 12 | 2 tasks | 3 files |
| Phase 01 P03 | 3min | 2 tasks | 3 files |
| Phase 01 P04 | 4min | 2 tasks | 3 files |
| Phase 02 P01 | 20min | 2 tasks | 6 files |
| Phase 02 P02 | 12min | 2 tasks | 4 files |
| Phase 02 P03 | 12min | 2 tasks | 4 files |
| Phase 02 P04 | 15 | 2 tasks | 5 files |
| Phase 03 P01 | 3min | 2 tasks | 3 files |
| Phase 03 P03 | 2min | 1 tasks | 1 files |
| Phase 03 P02 | 6min | 2 tasks | 1 files |
| Phase 03 P04 | 11min | 2 tasks | 3 files |
| Phase 04 P01 | 9min | 2 tasks | 4 files |
| Phase 04 P02 | 3min | 2 tasks | 1 files |
| Phase 05 P01 | 4min | 4 tasks | 5 files |
| Phase 05 P02 | 5 | 2 tasks | 3 files |
| Phase 05 P03 | 9 | 2 tasks | 2 files |
| Phase 06 P01 | 5min | 2 tasks | 3 files |
| Phase 06 P02 | 4min | 1 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Open decisions to resolve during Phase 1 planning:

- [Phase 1]: **Backend port granularity** — Cypher-level vs. LPG-primitive (lean LPG-primitive). Decide AND record in Phase 1; the named `get_impact`/`get_scope_at` round-trip tension is confirmed in the Phase 2 ladybug spike. Two distinct seams must be explicit in code: public `BeliefStore` Protocol (NVM↔core, unchanged) vs. internal backend port (below it).
- [Phase 1]: `query_scope` filter semantics — replace free `str` with a closed typed filter on core-owned fields (the #1 retroactive-rewrite risk; design against `05-nvm-memory-core.md §10.1`)
- [Phase 1]: `get_impact` return shape must carry a truncation/frontier signal; ratify the `depth` default
- [Phase 1]: UUID7 ordering contract for `get_scope_at` (byte-order total order or core-owned sequence tie-breaker)
- [Phase 1]: Draft the backend port contract spec (BACK-04) here; publish the consumer-facing "how to write a backend" docs in Phase 8 via PKG-04
- [Phase 2]: Confirm `$depth` bind param in variable-length Cypher and `belief_id` synthesized vs. composite PK against the installed `ladybug` package (the spike IS the research); confirm the chosen port granularity survives the real ladybug API and the traversal round-trip budget is acceptable
- [Phase ?]: Python floor raised 3.11 -> 3.14 at the cookiecutter prompt (CONTEXT #2); requires-python, CI matrices, ruff target, .python-version all render at 3.14
- [Phase ?]: Runtime deps pinned to exactly ladybug + pydantic; ladybugdb slopsquat token absent; pins resolved on PyPI (ladybug 0.17.1, pydantic 2.13.4)
- [Phase ?]: EdgeType excludes structural HAS_REVISION/CURRENT_STATE (Open Q1 resolved); Status closed to {active,retracted}; BeliefState closed six-field set; used enum.StrEnum as the UP042-clean (str,Enum) equivalent
- [Phase ?]: 01-03: Public Protocol annotation imports guarded under TYPE_CHECKING (with future annotations) instead of noqa — keeps the seam ruff-clean while the DATA-01 AST scan still inspects them
- [Phase ?]: 01-03: DATA-03 UUID7 ordering contract written into protocol.py source as docstrings so the doc-assertion finds the (source_event_id byte-order, state_id tiebreak) text
- [Phase ?]: 01-04: BACK-01 backend port granularity DECIDED as LPG-primitive (five graph primitives, no run/query/execute); recorded in ports.py
- [Phase ?]: 01-04: traverse is the single graph-walk primitive; get_impact/get_scope_at compose from it (Phases 3+); round-trip tension flagged for Phase 2 spike SC4
- [Phase ?]: 01-04: BACK-04 contract drafted as prose Markdown (docs/backend-contract.md, 7 constraints); executable form is the Phase 7 conformance suite BACK-05
- [Phase ?]: Phase 2: MemoryCore factories forward-reference the wave-2 ladybug adapter via function-local import + scoped pyright ignores + cast, keeping core.py driver-blind and strict-clean before backends/ladybug.py exists
- [Phase ?]: Port unchanged, SC4 confirmed — LPG-primitive BackendPort survives ladybug 0.17.1 unchanged; 30-hop cap and $param-in-bound rejection are adapter-internal details
- [Phase ?]: LadybugBackend.traverse: ACYCLIC var-length, raised var_length_extend_max_depth ceiling, one-query (reached, frontier); excludes start (WHERE b.state_id <> $start) to match the in-memory oracle
- [Phase ?]: DEF-02-01: ladybug coerces brace/bracket-shaped STRING params to STRUCT/LIST (value-opacity hazard) — deferred to the Phase 3 value-encoding contract
- [Phase ?]: Phase 2 D-03 (Option B packaging): pydantic is the sole required runtime dep; ladybug demoted to the doxastica[ladybug] opt-in extra; future backends are extras.
- [Phase ?]: [BLOCKING] CLAUDE.md constraint reversal recorded as decision-grade (sibling to the 3.14-floor decision): exactly-ladybug+pydantic and pinned-to-LadybugDB / no-storage-abstraction superseded by the Phase-1 BackendPort; ladybug is the reference backend, not the only substrate.
- [Phase 03]: 03-01: WORLD_SCOPE_ID is the dunder-wrapped '__world__' constant in models.py (not constants.py), barrel-re-exported; get_or_create_scope signature unchanged (D-02)
- [Phase 03]: 03-01: HAS_REVISION is hub form FROM Belief TO BeliefState, passed to add_edge as a raw string; ladybug add_edge generalized via _EDGE_ENDPOINTS for per-edge-type endpoint labels+PKs; no CURRENT_STATE table (D-01/D-07)
- [Phase ?]: 03-03: test_revision_spine.py constructs MemoryCore(backend) over the parametrized fixture port so spine behaviors run on both backends; verified collect-only (RED until 03-02)
- [Phase ?]: 03-02: DEF-02-01 closed via base64-over-JSON value codec in core.py (bare json.dumps corrupted by ladybug STRING brace-coercion); identical on both backends
- [Phase ?]: 03-02: current is DERIVED ordering-max over active states, no CURRENT_STATE pointer (D-01); expand is an explicit one-line delegate to _append (D-04)
- [Phase 03]: 03-04: SC3/D-01 keystone is a Hypothesis RuleBasedStateMachine + shadow oracle (tests/test_invariants.py) proving derived-current total+single-valued+≡chain-tail and chain immutability on BOTH backends
- [Phase 03]: 03-04: [Rule 1 fix] _current now selects ordering-max over ALL statuses and returns None on a retracted tail — a contraction correctly clears the derived current (prior active-filter left contracted beliefs reporting a current). Phase 4/7 query-current must align with this.
- [Phase 03]: 03-04: DEF-02-01 CLOSED — regression flipped from xfail to a passing assertion routed through MemoryCore.revise + get_revision_chain (the core encode boundary) on both backends
- [Phase 03]: 03-04: stateful-test both-backends idiom = two machine subclasses each exposing .TestCase + bounded ladybug Database(max_db_size) to cap per-example mmap reservation
- [Phase ?]: query_scope reuses the ONE _order_key for both the per-belief group-by max and the result sort (D-07) — no second ordering
- [Phase ?]: Factor-then-specialise: _current_tail is the status-agnostic ordering-max tail; _current delegates then applies the retracted->None collapse (behaviour-preserving)
- [Phase 05]: 05-01: BackendPort.traverse gains keyword-only direction: Literal['in','out']='out' (D-05) — the ONE genuine Phase-5 port change; default 'out' is a cross-phase contract keeping 27 positional callers + Phase-6 get_scope_at green
- [Phase 05]: 05-01: in-memory reverse walk = _in_edges O(edges) predecessor SCAN (no reverse index, per D-05 discretion) so _reindex/unit_of_work need no extension
- [Phase 05]: 05-01: ladybug direction flips ALL THREE arrows from one (lhs,rhs)=('<-','-') if 'in' else ('-','->') pair (main query, EXISTS frontier subquery, bound==0 probe); cap-raise/restore stays direction-agnostic; direction is a closed-Literal internal token, no new $param/interpolation surface
- [Phase 05]: 05-01: hydration gap persists for Plan 05-03 — ladybug traverse still returns state_id-only rows, so get_impact must re-fetch props via match_nodes (Option A)
- [Phase ?]: 05-02: MemoryCore.add_edge is a one-call passthrough to backend.add_edge inside exactly one unit_of_work (D-06); idempotency left to the backend, no endpoint-existence raise (D-07)
- [Phase ?]: 05-02: [Rule 1] InMemoryBackend.add_edge now silently no-ops on a missing endpoint (MATCH-MERGE parity with ladybug) so the oracle honors the documented D-07 behavior
- [Phase ?]: 06-01: get_scope_at uses cut-then-max (inclusive <= as_of PRE-filter BEFORE the per-belief ordering-max) so the cut REWINDS rather than drops
- [Phase ?]: 06-01: inline cut in get_scope_at's group-by loop (not an as_of param on _current_tail) — keeps the Phase-3/4 keystone behaviour-preserving

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 2]: Biggest project risk is the LadybugDB de-risking spike — verify `IF NOT EXISTS` DDL, multi-statement transactions, `$param` binds, and `$depth` patterns against the actually-installed `ladybug` (PyPI, NOT `ladybugdb`) before any belief logic stands on them. Phase 2 now also ships BOTH backends (ladybug reference + in-memory) behind the port; the in-memory backend doubles as the Phase 7 conformance-suite oracle.
- [Phase 7]: AGM Recovery must remain a named `xfail` (false for belief bases); never assert it against correct code. The property suite is now a backend conformance suite — in-memory oracle and ladybug must pass the identical parameterised tests.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-06-19T07:28:25.022Z
Stopped at: Completed 05-01-PLAN.md
Resume file: .planning/phases/05-edge-model-contraction-cascade/05-02-PLAN.md
