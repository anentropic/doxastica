# Phase 1 Discussion Log

**Date:** 2026-06-14
**Mode:** discuss (default, interactive)
**Phase:** 1 — Protocol, Backend Port & Data-Model Decisions

Human-reference record of the discussion. Not consumed by downstream agents (that's
`01-CONTEXT.md`).

---

## Areas selected

All four presented gray areas were selected for discussion:
1. Backend port granularity
2. BeliefState identity + UUID7 ordering
3. query_scope closed filter shape
4. get_impact shape + depth default

---

## Area 1 — Backend port granularity

**Q: Where should the internal backend port's contract sit?**
- Options: LPG-primitive (rec) / Cypher-level / think out loud
- **Chose: LPG-primitive.**

**Q: How are the two traversal-heavy reads expressed at the port boundary?**
- Options: Generic traverse primitive (rec) / domain-shaped read methods / defer to spike
- **Chose: Generic `traverse(start, edge_types, max_depth)` primitive**; get_impact &
  get_scope_at compose from it.

## Area 2 — BeliefState identity + UUID7 ordering

**Q: BeliefState PK model?**
- User asked clarifying questions instead of choosing: does the Kumiho paper use event IDs?
  does NVM need to know the belief state id?
- Answered from sources: paper/NVM model has BOTH a per-version `id` and `event_id`
  (`17 §3`); NVM needs the state id (Protocol's `add_edge`/`get_impact` consume it,
  `revise`/`expand` return it).
- **Resolved: synthesized core-minted `state_id` PK; `source_event_id` stored indexed
  non-unique.**

**Q: (raised by user) Which properties are doxastica-core vs arbitrary downstream
labelling?**
- Proposed a closed core property taxonomy. **User: "Yes, lock it."**
- status = active|retracted only; extensions in opaque value or downstream-owned
  labels/edges by state_id; never columns on core tables.

**Q: Ordering contract for get_scope_at?**
- **Chose: order by (source_event_id bytes, state_id tiebreak); core mints state_id; no
  caller monotonicity required.**

**Q: How to mint state_id given 2-dep rule + 3.11 floor (no stdlib uuid7)?**
- Options: vendor pure-Python uuid7 (rec) / uuid4 / version-split
- User: "the deps don't have to be locked to that, find a reputable uuidv7 lib" → then,
  after weighing candidates, **"we can require python 3.14 and use stdlib."**
- **Resolved: require Python 3.14, mint via stdlib `uuid.uuid7()`. Floor 3.11→3.14. Runtime
  deps stay exactly ladybug+pydantic. CI matrix 3.14 only.**

## Area 3 — query_scope closed filter shape

**Q (initial): What should the closed filter expose?**
- User requested clarification: uncertain which parts of `17` are Kumiho-core vs NVM
  extension; concern the seam is under-mapped; pointed to `21 §4`. Stated instincts: no ORM
  query-builder; all filtering in the DB; NVM adds app-specific labels; therefore allow
  filtering by arbitrary properties — "but I may be exaggerating NVM's needs."
- Read `21` in full. Surfaced the two-port split: `BeliefStore` (doxastica, belief-semantic)
  vs `KnowledgeQueries` (NVM-owned, app-specific finders + raw escape, reads core subgraph by
  state_id). Confirmed 3 of 4 instincts; the 4th (doxastica filters arbitrary props) is
  `KnowledgeQueries`' job, not doxastica's.
- **Q (re-posed): belief-semantic filter only, generic opaque-property filtering, or
  belief-semantic + raw escape?**
- **Chose: belief-semantic only (doc-faithful).** Frozen `BeliefFilter{belief_ids, status,
  event_id_min/max}`. `include_deprecated` = sugar over status.

## Area 4 — get_impact shape + depth + world scope

**Q (initial bundle, twice rejected for clarification):** user asked to be talked through it,
then asked: is max traversal depth the only option? do graph DBs have other ways to avoid
infinite cycle traversal? observed you'd always want full impact, so depth is just a
"sufficiently large" guess.
- Explained: depth conflates termination (→ solved by visited-set, not depth) with cost
  control; reachable-node-SET semantics is cycle-safe and returns the full closure; ladybug's
  unbounded cycle-safe traversal is a Phase 2 spike item.
- **Q (reframed): depth signature?** → **`depth: int | None = None` (unbounded full closure
  default).**
- **Q: return shape?** → **`ImpactResult{reached, frontier, truncated}` (frozen).**
- **Q: world-scope identity/bootstrap?** → **Defer to Phase 3 (SCOPE-01/02).**
- **Q: ready for context?** → **Ready for context.**

---

## Deferred ideas

- World-scope identity & bootstrap → Phase 3.
- EdgeType membership, Scope/Belief field finalisation, BACK-04 spec format → Phase 1
  planning (fall out of locked decisions; not separate gray areas).

## Claude's-discretion items

- `include_deprecated` reconciled as sugar over `status` (planner note, not asked).
- EdgeType generic set named (`SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM`) from the taxonomy.

## Notable ripples flagged for the planner

- `requires-python >=3.14` (was `>=3.11`); CI matrix 3.14 only; CLAUDE.md UUID7-gap section
  + `uuid-utils` dev shim become moot.
- LPG-primitive port round-trip tension and unbounded cycle-safe traversal both deferred to
  the Phase 2 ladybug spike (port adjusts there if needed).
