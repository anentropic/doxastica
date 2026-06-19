# Phase 6: Structural Time-Travel - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement `get_scope_at(scope_id, as_of_event_id)` (HIST-03) — the public `BeliefStore` /
`MemoryCore` method that reconstructs the active belief base of a scope **as of an event**,
purely structurally from immutable `source_event_id`-ordered `BeliefState` nodes, under the
Phase-1 UUID7 ordering contract. Plus the correctness proof NVM's event-sourcing story rests on.

**Depends on:** Phase 3 (write spine + `_order_key`/`_current` pattern) and Phase 4 (`query_scope`
— the direct template). **NOT Phase 5** — no edges are walked.

**Key framing (NVM-grounded):** `get_scope_at` is the smallest *implementation* of the phase and
the largest *proof*. NVM defines it as a CQRS fold-over-the-event-log (`21 §Event Sourcing+CQRS`);
doxastica's immutable `source_event_id`-stamped states ARE that materialized log, so the query is a
temporal variant of `query_scope` (~one helper + ~15 lines). The roadmap's "most complex single
query" billing is cashed out in the **verification** (replay-equivalence oracle), not the code.

**Out of scope:** any timestamp/wall-clock resolution (SC1 is explicit — the event-id ordering IS
the time axis); the structural-invariant *suite parametrization* (`get_scope_at ≡ replay` as a
registered `@invariant` across backends) — that assembly is Phase 7; the irony join (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### `get_scope_at` is a temporal `query_scope` — `match_nodes`, NOT `traverse`
- **D-01:** `get_scope_at` composes the `match_nodes` scope-wide scan exactly like `query_scope`
  (Phase 4) — NOT a graph walk. No `SUPERSEDES`/`HAS_REVISION`/`traverse` is consulted; the chain
  order is *implicit* in the `(source_event_id, state_id)` ordering. **This supersedes the Phase-1
  CONTEXT sketch** that said "both `get_impact` and `get_scope_at` compose from `traverse`" — that
  was already superseded for `query_scope` in Phase 4, and it is equally wrong for `get_scope_at`.
  **Grounding:** NVM treats `get_scope_at` as a CQRS projection / fold over the event log
  (`21-nvm-component-architecture.md` lines 98-102), not an edge traversal.
- **D-02:** The body mirrors `query_scope`'s pipeline with ONE change — a temporal CUT replaces the
  `event_id_max` post-filter: scope-wide `match_nodes` scan → **filter to states with
  `source_event_id <= as_of_event_id`** (the cut) → group by `belief_id` → per-group ordering-MAX
  (the current tail *as of the cut*) → retracted-tail→absent collapse → `_order_key` sort →
  `_hydrate`. Pure read: no `unit_of_work`, no `_ensure_scope`, absent/empty scope → `[]`, works on
  any scope (incl. world — reads never trigger the world-scope guard).

### The cut REWINDS (re-derives the tail), it does NOT drop
- **D-03:** The cut RE-DERIVES the per-belief current tail over the `<= as_of` window, so an OLDER
  value resurfaces — this is the defining difference from `query_scope`. `query_scope`'s
  `event_id_max` is a post-filter that makes a too-new belief ABSENT (drop, never rewind, Phase 4
  A1); `get_scope_at` reconstructs the value *current at E*. **Grounding:** NVM needs "what did the
  guard believe at T0?" (`06-nvm-knowledge-inference-design.md` line 86) and "what was true before
  the sale" (`05 §8` line 260) — a drop-filter would wrongly return nothing for a since-revised
  belief. Conflating the cut with `event_id_max` is the central trap of this phase.

### Inclusive cut on `source_event_id`, one ordering contract
- **D-04:** The cut is INCLUSIVE: include state `s` iff `s.source_event_id <= as_of_event_id`. A
  state whose `source_event_id == as_of` IS included. Comparison is `str`-vs-`str` on
  `source_event_id` (the SAME form `_order_key` uses — Phase 4 Pitfall 3: never `str`-vs-`UUID`).
  Inclusivity is what makes SC2's `get_scope_at(latest) == query_scope(current)` hold.
- **D-05:** Reuse the ONE `_order_key` contract for BOTH the cut comparison AND the per-group max —
  never a second ordering (the IN-03 single-ordering discipline). The cut is on `source_event_id`
  alone (the caller supplies only an event id, not a `(source_event_id, state_id)` pair); the
  `state_id` tiebreak orders WITHIN the included set when picking the max tail. NVM nuance this gets
  right for free: a single turn-event that writes several beliefs shares one `source_event_id`, so
  the inclusive cut folds ALL of that event's writes into the base, tiebroken by `state_id`.

### Retracted handling at the cut
- **D-06:** If the as-of current tail is `retracted`, the belief is ABSENT from the reconstructed
  base — the same retracted-tail→`None` collapse `_current` applies (Phase 3 D-05), but computed
  over the cut window rather than "now". SC1 requires correct retracted-state handling. Likely
  factoring: a cut-aware sibling/parametrization of the status-agnostic `_current_tail`
  (`query_scope` takes the max over ALL states; `get_scope_at` takes it over states `<= as_of`),
  then the same retracted collapse on top.

### Verification — the operational-fold oracle is the spec (LOCKED)
- **D-07:** Build a PURE-PYTHON operational-fold oracle that replays the `revise`/`expand`/
  `contract` op sequence up to each event id (`fold(ops, as_of)` → the active base), and assert
  `get_scope_at(scope, cut) == fold(ops, cut)` under Hypothesis on BOTH backends. This is the SPEC,
  not a nice-to-have: NVM *defines* `get_scope_at` as the fold-over-the-log, and its cache-watermark
  reconstruction + replay-debugging (`02`, `04:103`, `16:368`, `01:726`) rest on this equivalence.
  SC1 (`get_scope_at(latest) == query_scope(current)`), SC2 (replay equivalence), and SC3 (same-ms /
  out-of-order id resolution) all collapse into this one property — the Hypothesis strategy MUST
  generate intra-ms-colliding and out-of-order `source_event_id`s to exercise SC3, and step `as_of`
  across event ids to exercise SC2.

### Claude's Discretion
- The exact factoring of the cut-aware tail helper (extend `_current_tail` with an optional
  `as_of` bound vs. a sibling). Either is fine provided the ONE `_order_key` contract is reused.
- Hypothesis strategy shape for op-sequence + event-id generation (the oracle determines the
  assertion; the generator design is open).

</decisions>

<specifics>
## Specific Ideas

- The replay oracle and `get_scope_at` are the two sides of a CQRS read model: the oracle folds the
  *operations*, `get_scope_at` folds the *materialized states*. The phase succeeds when they are
  proven identical under adversarial id ordering — that equivalence is literally NVM's "replay
  history into a projection" guarantee (`21:102`), the thing that lets NVM rebuild caches and add
  M5 components by replay.
- Concrete NVM call shapes to keep the mechanism honest against: `get_scope_at(guard_scope, t0)` =
  "what did the guard believe at T0"; `get_scope_at(world, e42)` = "what was true before the sale".
  Same query, any scope, read-only.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Time-travel semantics (the consumer contract that drove these decisions)
- `../narrative-vm/_design/v2/21-nvm-component-architecture.md` §"Event Sourcing + CQRS" (lines
  98-105) — `get_scope_at` is a CQRS projection/fold over the event log; replay-into-projection is
  the temporal-story owner. The grounding for D-01 (no traverse) and D-07 (replay = spec).
- `../narrative-vm/_design/v2/06-nvm-knowledge-inference-design.md` (lines 82-87) — "Temporal
  belief queries ('what did the guard believe at T0?') are `get_scope_at` — structural, free." The
  grounding for D-03 (rewind, not drop).
- `../narrative-vm/_design/v2/05-nvm-memory-core.md` §3 (the `get_scope_at` signature, lines
  120-129 — "time-travel query… answerable purely structurally because states are immutable and
  event-id-ordered") and §8 (line 260 — "`get_scope_at(world, e₄₂)` answers 'what was true before
  the sale'"); §10.x soft spots.
- `../narrative-vm/_design/v2/09-nvm-diegetic-time.md` (line 185) & `00-...overview.md` (line 213)
  — "appends history without ever rewriting / without time travel": the STORE never mutates;
  `get_scope_at` is a READ reconstruction. Reinforces SC1 (no timestamp dependency).
- `../narrative-vm/_design/v2/16-nvm-decision-register.md` (line 368, R2) — the `as_of_event`
  watermark / prune-and-regenerate cache pattern that consumes `get_scope_at`; why SC3 determinism
  is load-bearing, not academic.

### In-repo design lineage (decisions already locked upstream)
- `.planning/phases/01-protocol-backend-port-data-model-decisions/01-CONTEXT.md` §2 (DATA-03
  ordering contract: `(source_event_id byte-order, state_id tiebreak)`, no caller monotonicity
  demanded) — the ordering `get_scope_at` honours; and the now-SUPERSEDED "composes from traverse"
  note (see D-01).
- `.planning/phases/04-retrieval-observation-surface/04-CONTEXT.md` — `query_scope` decisions; the
  `event_id_max` POST-filter (drop, never rewind) that D-03 deliberately diverges from.
- `src/doxastica/core.py` — `query_scope` (the template, the pipeline to mirror), `_order_key`
  (the ONE ordering contract, reuse), `_current_tail` / `_current` (the status-agnostic max +
  retracted→`None` collapse to make cut-aware), `_hydrate`.
- `src/doxastica/protocol.py` — `BeliefStore.get_scope_at` signature + the UUID7-ordering-contract
  docstring (already defines the as-of cut semantics; do not change the signature).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MemoryCore.query_scope` (core.py): the direct structural template — scan → group-by-belief
  per-group `_order_key` max → status filter → sort → hydrate. `get_scope_at` swaps the
  `event_id_max` post-filter for the `<= as_of` cut (D-02/D-03).
- `_order_key`, `_current_tail`, `_current`, `_hydrate` (core.py): reuse all four; `get_scope_at`
  needs a cut-aware variant of the `_current_tail` max (D-06).
- `BackendPort.match_nodes` (both backends, parity-tested): the only port primitive needed.

### Established Patterns
- Driver-blind core (D-02 lineage): `get_scope_at` composes ONLY `match_nodes`; no Cypher, no
  `ladybug` import in core.py (enforced by tests/test_import_purity.py).
- Pure-read surface (Phase 4 D-08): non-existent/empty scope → `[]`, no `_ensure_scope`, no
  `unit_of_work`, no error.
- Cross-backend parity + Hypothesis property tests are the existing test idioms to mirror
  (tests/test_query_scope.py, tests/test_backend_parity.py, tests/test_cascade.py).

### Integration Points
- `protocol.py` `BeliefStore.get_scope_at` is already the public contract — implement on
  `MemoryCore`; no signature change.
- The operational-fold oracle (D-07) is a NEW test-only helper (pure Python over the op sequence),
  not production code.

</code_context>

<deferred>
## Deferred Ideas

- `get_scope_at ≡ replay` as a registered structural `@invariant` parametrized across both backends
  in the conformance suite — Phase 7 (FORMAL-03). Phase 6 lands the equivalence as a Hypothesis
  property; Phase 7 wires it into the backend conformance harness.
- The irony join (actor-scope vs world-scope divergence on `belief_id`) — Phase 7.
- Any caller-facing `(source_event_id, state_id)`-pair cut granularity (finer than per-event) —
  out of scope; the contract is `as_of_event_id` (per-event granularity), which matches NVM's
  event-log model.

</deferred>

---

*Phase: 06-structural-time-travel*
*Context gathered: 2026-06-19*
