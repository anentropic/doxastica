---
gsd_state_version: 1.0
milestone: v0.2.0
milestone_name: — Stance
status: executing
stopped_at: Completed 08-02-PLAN.md
last_updated: "2026-07-04T22:06:47.231Z"
last_activity: 2026-07-04 -- Phase 10 planning complete
progress:
  total_phases: 2
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-13)

**Core value:** A correct, append-only belief-revision core behind a clean `BeliefStore` Protocol whose correctness is *provable* — AGM/Hansson postulate compliance and structural invariants verified mechanically, zero narrative semantics leaking in.
**Current focus:** Phase 09 — stance-value-layer-write-persistence

## Current Position

Phase: 10
Plan: Not started
Status: Ready to execute
Last activity: 2026-07-04 -- Phase 10 planning complete

## Performance Metrics

**Velocity:**

- Total plans completed: 28
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
| 07 | 4 | - | - |
| 08 | 3 | - | - |
| 9 | 2 | - | - |

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
| Phase 07 P01 | 6m | 3 tasks | 2 files |
| Phase 07 P02 | 4 | 1 tasks | 1 files |
| Phase 07 P03 | 9min | 2 tasks | 1 files |
| Phase 07 P04 | 5 | 1 tasks | 1 files |
| Phase 08 P01 | 2min | 2 tasks | 3 files |
| Phase 08 P02 | 3min | 2 tasks | 2 files |
| Phase 08 P03 | 15m | 3 tasks | 5 files |
| Phase 09 P01 | 8min | 2 tasks | 6 files |
| Phase 09 P02 | 8min | 2 tasks | 1 files |

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
- [Phase ?]: [Phase 07]: 07-02: get_scope_at ≡ replay registered into FORMAL-03 via reciprocal registry marker in test_scope_at.py (D-08) — registration not re-implementation; fold oracle left SUT-independent (Pitfall 6 anti-tautology)
- [Phase 07]: 07-03: AGM Recovery encoded as @pytest.mark.xfail(strict=True) on the mark itself (no global xfail_strict) — reports xfailed against correct code; drift toward closed belief sets XPASSes -> suite red (FORMAL-04, D-04)
- [Phase 07]: 07-03: ratified Recovery counterexample base = single belief p re-asserted at a NEW value (revise->contract->revise); the naive {p,q} base XPASSes erroneously (independent q survives) — Open Q1 resolved
- [Phase 07]: 07-03: superseded-chain positives (D-05) assert active->retracted->active + current==v' + retained-retracted + base-not-restored on both backends; kept distinct from temporal recoverability (no get_scope_at)
- [Phase ?]: [Phase 08]: 08-01: PyPI metadata added additively to pyproject [project] (PEP 639 license = MIT -> License-Expression, classifiers, keywords, [project.urls]); dependencies/optional-dependencies/requires-python untouched (D-03 split + 3.14 floor LOCKED)
- [Phase ?]: [Phase 08]: 08-01: REQUIREMENTS PKG-02 + ROADMAP Phase-8 SC1 prose reconciled to the decided bar (pydantic sole required, ladybug the [ladybug] extra, CI 3.14-only) with D-03 / CONTEXT #2 citations; stale exactly-ladybug+pydantic / 3.11-floor strings removed
- [Phase 08]: 08-02: README leads with PKG-03 Kumiho framing (reference implementation of Kumiho, multi-scope extension, no recovery) + D-03 install split; docs/src/index.md Quick Start is a runnable zero-dep MemoryCore.in_memory->revise->query_scope example using uuid7 (verified by running it)
- [Phase ?]: Used git mv (relocation, not duplication) to publish the backend contract inside docs_dir
- [Phase ?]: Pinned CI git-cliff to .cliff.toml explicitly (default search path is cliff.toml, not the dot-file)
- [Phase 09]: 09-01: Stance is a plain Enum + total_ordering with an isinstance-guarded __lt__ (not IntEnum/StrEnum); +/*/cross-type < raise TypeError by base-class choice. Serialize .name / hydrate Stance[token] name-lookup (never value-lookup on the wire token).
- [Phase 09]: 09-01: stance is a REQUIRED 7th BeliefState field (no model default, D-01); the certain default lives on revise/expand. protocol.py imports Stance at RUNTIME because the =Stance.certain default is evaluated at class-definition time (TYPE_CHECKING-only would NameError).
- [Phase ?]: STANCE persistence proofs driven through MemoryCore(backend) with member-identity assertions; a value-vs-name hydrate regression raises on read (T-09-02)

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 2]: Biggest project risk is the LadybugDB de-risking spike — verify `IF NOT EXISTS` DDL, multi-statement transactions, `$param` binds, and `$depth` patterns against the actually-installed `ladybug` (PyPI, NOT `ladybugdb`) before any belief logic stands on them. Phase 2 now also ships BOTH backends (ladybug reference + in-memory) behind the port; the in-memory backend doubles as the Phase 7 conformance-suite oracle.
- [Phase 7]: AGM Recovery must remain a named `xfail` (false for belief bases); never assert it against correct code. The property suite is now a backend conformance suite — in-memory oracle and ladybug must pass the identical parameterised tests. **(07-03: RESOLVED — Recovery is now a strict xfail in tests/test_recovery_xfail.py reporting xfailed against correct code with a drift guard; superseded-chain positives pass on both backends.)**

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260619-put | Add `.github/copilot-instructions.md` telling Copilot code review to ignore `.planning/` | 2026-06-19 | 4c999a7 | [260619-put-add-github-copilot-instructions-md-telli](./quick/260619-put-add-github-copilot-instructions-md-telli/) |
| 260621-m02 | Refactor MemoryCore to pure DI — move factory classmethods to `factories.py` so `core.py` has zero backend refs | 2026-06-21 | 0133558 | [260621-m02-refactor-memorycore-to-pure-di-move-fact](./quick/260621-m02-refactor-memorycore-to-pure-di-move-fact/) |
| 260621-mjb | Remove the `factories` layer entirely — pure-DI construction; `LadybugBackend.from_connection` classmethod added | 2026-06-21 | ee969c8 | [260621-mjb-remove-doxastica-factories-layer-pure-di](./quick/260621-mjb-remove-doxastica-factories-layer-pure-di/) |
| 260622-h2l | Fix stale "`MemoryCore`'s factories" docstring in `backends/__init__.py` (layer removed in be64fe8); update to pure-DI construction story | 2026-06-22 | 680b280 | [260622-h2l-fix-stale-factories-docstring](./quick/260622-h2l-fix-stale-factories-docstring/) |
| 260622-hiy | PR #1 review fixes: broken `MemoryCore.in_memory()` Quick Start → `MemoryCore(InMemoryBackend())`; drop stored `CURRENT_STATE` from backend-contract; test `-> None` consistency; assert port surface is exactly five primitives | 2026-06-22 | 3fac85b | [260622-hiy-pr1-review-fixes](./quick/260622-hiy-pr1-review-fixes/) |
| 260702-tab | Switch mkdocs docs to top tabs navigation — add `navigation.tabs` to theme features (kept `navigation.sections` for per-tab section grouping) | 2026-07-02 | be5a828 | — (gsd-fast) |
| 260702-bpc | Nest Backend Port Contract under Explanation — move `backend-contract.md` into `docs/src/explanation/`, drop its top-level tab | 2026-07-02 | 3eee04e | — (gsd-fast) |
| 260704-1x1 | Replace agent-team tutorial with Cluedo detective belief-revision tutorial (centers Story B: contradiction → supersede → stale cascade) | 2026-07-04 | c22f7f7 | [260704-1x1-replace-agent-team-tutorial-with-cluedo-](./quick/260704-1x1-replace-agent-team-tutorial-with-cluedo-/) |

## Deferred Items

Items acknowledged at v0.1.0 milestone close (5 open artifacts; none are functional gaps):

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| quick_task | 260619-put — add `.github/copilot-instructions.md` | done (audit status "unknown"; work complete) | 2026-07-04 |
| quick_task | 260704-1x1 — replace agent-team tutorial with Cluedo | done (audit status "unknown"; work complete) | 2026-07-04 |
| seed | SEED-001 — doxastica-demo TUI "belief inspector" | dormant (future work) | 2026-07-04 |
| context_question | Phase 01 — 2 CONTEXT open questions | resolved in the Phase-2 ladybug spike | 2026-07-04 |
| context_question | Phase 02 — 3 CONTEXT open questions | resolved in the Phase-2 ladybug spike | 2026-07-04 |

## Session Continuity

Last session: 2026-07-04T20:20:38.651Z
Stopped at: Completed 08-02-PLAN.md
Resume file: .planning/phases/07-agm-hansson-conformance-suite/07-04-PLAN.md

## Operator Next Steps

- Plan Phase 9 with /gsd-plan-phase 9
