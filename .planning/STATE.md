---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
stopped_at: Phase 1 context gathered
last_updated: "2026-06-14T18:24:04.291Z"
last_activity: 2026-06-13 — Roadmap revised for pluggable backends (Ports & Adapters; 39 v1 requirements mapped)
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-13)

**Core value:** A correct, append-only belief-revision core behind a clean `BeliefStore` Protocol whose correctness is *provable* — AGM/Hansson postulate compliance and structural invariants verified mechanically, zero narrative semantics leaking in.
**Current focus:** Phase 1 — Protocol, Backend Port & Data-Model Decisions

## Current Position

Phase: 1 of 8 (Protocol, Backend Port & Data-Model Decisions)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-06-13 — Roadmap revised for pluggable backends (Ports & Adapters; 39 v1 requirements mapped)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

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

Last session: 2026-06-14T18:24:04.280Z
Stopped at: Phase 1 context gathered
Resume file: .planning/phases/01-protocol-backend-port-data-model-decisions/01-CONTEXT.md
