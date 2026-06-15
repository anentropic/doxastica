# Phase 3: Append-Only Revision Spine (Keystone) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 3-append-only-revision-spine-keystone
**Areas discussed:** Current-state modelling, World scope identity, Op semantics, Auto-create & vacuity

> The discussion was unusually grounding-heavy: the user repeatedly paused button-selection to
> trace requirement provenance back to the source design docs and the Kumiho paper before
> committing. Several decisions are deliberate, recorded mechanism-deviations justified against
> that source material rather than against the GSD requirement wording.

---

## Current-state modelling

| Option | Description | Selected |
|--------|-------------|----------|
| Derived (no stored pointer) | current = max BeliefState per (scope,belief) by ordering contract; pure append; zero port change | ✓ |
| Head-node pointer (upsert) | structural head keyed by (scope,belief) carrying current_state_id, re-pointed via upsert_node | |
| CURRENT_STATE edge + delete primitive | graph edge re-pointed by adding a delete/replace primitive to the published BackendPort | |

**User's choice:** Derived (option 1).
**Notes:** User interrogated the provenance of CHAIN-03's `CURRENT_STATE` pointer before
choosing. Traced: the pointer IS from the core design (`17 §3` / `05`, "the only mutable
element"), but its single-`(:Belief)-[:CURRENT_STATE]` topology assumed the shared-`Belief`
multi-actor model that `05 §6` explicitly RETIRES in favour of independent peer scopes with
per-`(scope,belief)` value divergence — so the original edge form doesn't transplant. Decisive:
`05 §6` cl.3 says `CURRENT_STATE` facts are "materialized as plain edges only if profiling
demands," i.e. the design itself treats current as derived with edge-materialization optional.
Recorded as a deliberate CHAIN-03 mechanism-deviation; uniqueness invariant becomes a
consistency check.

---

## World scope identity

| Option | Description | Selected |
|--------|-------------|----------|
| Reserved constant id | module constant WORLD_SCOPE_ID; get_or_create_scope(it) -> is_world=True; singleton by construction; signature unchanged | ✓ |
| Caller-configured id | world_scope_id threaded through MemoryCore construction | |
| is_world flag on get_or_create_scope | changes the locked public seam; needs separate singleton enforcement | |

**User's choice:** Reserved constant (option 1), **with the value adjusted to `"__world__"`**
(dunder-wrapped) rather than bare `"world"`, to avoid collision with a caller-chosen scope id.

### World scope creation timing

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy + structural guard | created on demand; contract() raises by id-check before any backend access | ✓ |
| Eager auto-create at construction | a write per core init; guard structural regardless | |

**User's choice:** Lazy + structural guard (option 1).

---

## Op semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Mechanically identical | revise≡expand: append + HAS_REVISION + SUPERSEDES-on-displacement; current derived; distinction = declared intent + Phase 7 suite | ✓ |
| Structurally divergent | keep some structural difference (precondition or edge) between revise and expand | |

**User's choice:** Mechanically identical (option 1).
**Notes:** User asked to stress-test the claim against the design corpus and the paper, and
correctly flagged that the "re-learning → new state even if same content" point is about
*idempotence*, not *consistency* (conceded). They then asked whether real consistency logic
could be built per the paper and not used by NVM, and what Kumiho actually stores. Read the
Kumiho paper directly (pp. 1–8): it stores **ground triples** under "a deliberately simple
propositional logic" that *avoids* the DL impossibility; conflict resolution IS the `SUPERSEDES`
edge; NL→triple mapping is explicitly pre-formal. Conclusion: there is **no value-semantic
consistency engine in the paper to port** — `revise`-as-append-and-supersede is the faithful
operator, not an under-implementation. The novel-vs-update difference lives in NVM's stance
layer (R21) above the seam. Decided revise/expand lay `SUPERSEDES` edges (paper's named conflict
operator; read by Phase 4, traversed by Phase 5).

---

## Auto-create & vacuity

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-create on write | revise/expand/contract create scope (reserved-id rule) + Belief node if absent | ✓ |
| Require explicit scope | raise if scope not pre-created via get_or_create_scope | |

**User's choice:** Auto-create on write.

| Option | Description | Selected |
|--------|-------------|----------|
| Permissive | revise/expand always succeed; novel-vs-update meaning lives above the seam | ✓ |
| Strict | expand raises on existing key; revise raises on novel key | |

**User's choice:** Permissive.

| Option | Description | Selected |
|--------|-------------|----------|
| No-op (AGM vacuity) | contract on absent/already-retracted = no-op None; when acting, one retracted state copying prior value; world-guard first | ✓ |
| Raise on absent | contract raises when nothing to retract | |

**User's choice:** No-op (AGM vacuity). Required for the Hansson Vacuity postulate (Phase 7).

---

## Claude's Discretion

- `HAS_REVISION` hub vs chain-link shape and edge direction (constrained by get_revision_chain
  + derived current/superseded computability).
- Opaque `value` storage encoding below the model layer (established Phase-2 pattern).
- Per-op transaction boundaries beyond "one unit_of_work per public write."

## Deferred Ideas

- Materialize a stored current pointer ONLY if `query_scope` profiling later demands it
  (addable without changing the public surface, per `05 §6` cl.3).
- `get_scope_at` full as-of reconstruction → Phase 6.
- `query_scope` + four-cell deprecated/superseded matrix → Phase 4.
- `add_edge` consumer edges + `get_impact` cascade → Phase 5.
- Optional `CONTRADICTS` edges (paper's explicit conflict-detection edge) — future consumer
  edge, not core.
