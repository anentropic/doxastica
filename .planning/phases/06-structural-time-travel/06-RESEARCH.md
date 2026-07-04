# Phase 6: Structural Time-Travel - Research

**Researched:** 2026-06-19
**Domain:** AGM belief-base as-of reconstruction (`get_scope_at`) over the LPG `BackendPort`; temporal CUT (rewind) vs Phase-4 `event_id_max` POST-filter (drop); operational-fold replay-equivalence oracle
**Confidence:** HIGH (pure in-repo composition of an already-shipped Phase-3 spine + Phase-4 `query_scope` template; every claim grounded in read source, not external docs)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 — `get_scope_at` composes the `match_nodes` scope-wide scan exactly like `query_scope` (Phase 4) — NOT a graph walk.** No `SUPERSEDES`/`HAS_REVISION`/`traverse` is consulted; chain order is *implicit* in the `(source_event_id, state_id)` ordering. This supersedes the Phase-1 CONTEXT "both `get_impact` and `get_scope_at` compose from `traverse`" sketch — already superseded for `query_scope` in Phase 4, equally wrong here. Grounding: NVM treats `get_scope_at` as a CQRS projection / fold over the event log (`21-nvm-component-architecture.md` lines 98-102), not an edge traversal.
- **D-02 — The body mirrors `query_scope`'s pipeline with ONE change: a temporal CUT replaces the `event_id_max` post-filter.** scope-wide `match_nodes` scan → **filter to states with `source_event_id <= as_of_event_id`** (the cut) → group by `belief_id` → per-group ordering-MAX (the current tail *as of the cut*) → retracted-tail→absent collapse → `_order_key` sort → `_hydrate`. Pure read: no `unit_of_work`, no `_ensure_scope`, absent/empty scope → `[]`, works on any scope (incl. world — reads never trigger the world-scope guard).
- **D-03 — The cut REWINDS (re-derives the tail); it does NOT drop.** It re-derives the per-belief current tail over the `<= as_of` window, so an OLDER value resurfaces — the defining difference from `query_scope`. `query_scope`'s `event_id_max` is a post-filter that makes a too-new belief ABSENT (drop, never rewind, Phase 4 A1); `get_scope_at` reconstructs the value *current at E*. Grounding: NVM needs "what did the guard believe at T0?" (`06-nvm-knowledge-inference-design.md` line 86) and "what was true before the sale" (`05 §8` line 260) — a drop-filter would wrongly return nothing for a since-revised belief. **Conflating the cut with `event_id_max` is the central trap of this phase.**
- **D-04 — Inclusive cut on `source_event_id`, one ordering contract.** Include state `s` iff `s.source_event_id <= as_of_event_id`. A state whose `source_event_id == as_of` IS included. Comparison is `str`-vs-`str` on `source_event_id` (the SAME form `_order_key` uses — Phase 4 Pitfall 3: never `str`-vs-`UUID`). Inclusivity is what makes SC2's `get_scope_at(latest) == query_scope(current)` hold.
- **D-05 — Reuse the ONE `_order_key` contract for BOTH the cut comparison AND the per-group max** — never a second ordering (the IN-03 single-ordering discipline). The cut is on `source_event_id` alone (the caller supplies only an event id, not a `(source_event_id, state_id)` pair); the `state_id` tiebreak orders WITHIN the included set when picking the max tail. NVM nuance this gets right for free: a single turn-event that writes several beliefs shares one `source_event_id`, so the inclusive cut folds ALL of that event's writes into the base, tiebroken by `state_id`.
- **D-06 — Retracted handling at the cut.** If the as-of current tail is `retracted`, the belief is ABSENT from the reconstructed base — the same retracted-tail→`None` collapse `_current` applies (Phase 3 D-05), but computed over the cut window rather than "now". SC1 requires correct retracted-state handling. Likely factoring: a cut-aware sibling/parametrization of the status-agnostic `_current_tail` (`query_scope` takes the max over ALL states; `get_scope_at` takes it over states `<= as_of`), then the same retracted collapse on top.
- **D-07 — The operational-fold oracle is the spec (LOCKED).** Build a PURE-PYTHON operational-fold oracle that replays the `revise`/`expand`/`contract` op sequence up to each event id (`fold(ops, as_of)` → the active base), and assert `get_scope_at(scope, cut) == fold(ops, cut)` under Hypothesis on BOTH backends. This is the SPEC, not a nice-to-have: NVM *defines* `get_scope_at` as the fold-over-the-log, and its cache-watermark reconstruction + replay-debugging (`02`, `04:103`, `16:368`, `01:726`) rest on this equivalence. SC1 (`get_scope_at(latest) == query_scope(current)`), SC2 (replay equivalence), and SC3 (same-ms / out-of-order id resolution) all collapse into this one property — the Hypothesis strategy MUST generate intra-ms-colliding and out-of-order `source_event_id`s to exercise SC3, and step `as_of` across event ids to exercise SC2.

### Claude's Discretion

- The exact factoring of the cut-aware tail helper (extend `_current_tail` with an optional `as_of` bound vs. a sibling). Either is fine provided the ONE `_order_key` contract is reused.
- Hypothesis strategy shape for op-sequence + event-id generation (the oracle determines the assertion; the generator design is open).

### Deferred Ideas (OUT OF SCOPE)

- `get_scope_at ≡ replay` as a registered structural `@invariant` parametrized across both backends in the conformance suite — Phase 7 (FORMAL-03). Phase 6 lands the equivalence as a Hypothesis property; Phase 7 wires it into the backend conformance harness.
- The irony join (actor-scope vs world-scope divergence on `belief_id`) — Phase 7.
- Any caller-facing `(source_event_id, state_id)`-pair cut granularity (finer than per-event) — out of scope; the contract is `as_of_event_id` (per-event granularity), which matches NVM's event-log model.
- Any timestamp/wall-clock resolution (SC1 is explicit — the event-id ordering IS the time axis).
- The structural-invariant *suite parametrization* (`get_scope_at ≡ replay` as a registered `@invariant` across backends) — Phase 7.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **HIST-03** | `get_scope_at(scope, as_of_event_id)` reconstructs the active base as of an event, purely structurally from immutable event-id-ordered states (time-travel). | The body lands in `core.py` composing `match_nodes` (no new port primitive, no Cypher, no `traverse`). It mirrors the shipped `query_scope` pipeline (core.py:544-607) with ONE change: an inclusive `source_event_id <= as_of` CUT replaces the `event_id_max` POST-filter, and the per-belief ordering-MAX is taken over the *cut window* so an older value can resurface (D-02/D-03). The retracted-tail→absent collapse (D-06) reuses the `_current`-style rule. The signature is already locked in `protocol.py:150-165` (no change). The proof is a pure-Python operational-fold oracle (D-07) asserting `get_scope_at(scope, cut) == fold(ops, cut)` under Hypothesis on both backends. |
</phase_requirements>

## Summary

Phase 6 is a **pure composition phase**, the temporal sibling of Phase 4. It adds ONE public method body — `get_scope_at` — to the already-built `MemoryCore`, plus a new Hypothesis property-test file carrying the operational-fold oracle. There is **no signature change** (`protocol.py:150-165` is already locked), **no new `BackendPort` primitive** (it composes `match_nodes` exactly like `query_scope`), **no schema change, no new write semantics, no `traverse`/edge walk (D-01), and no external dependency**. Every primitive it needs shipped in Phases 1-4: `match_nodes` (the read primitive), `_order_key` (the ONE ordering contract, core.py:86-96), `_current_tail` (the status-agnostic ordering-max, core.py:192-213), `_current`'s retracted→`None` collapse (core.py:215-232), and `_hydrate` (core.py:252-267).

The single genuinely new piece of *logic* is the **temporal CUT**, and it is exactly ONE line different from `query_scope`'s shipped body. `query_scope` derives the per-belief ordering-MAX over **all** states for the scope, then `event_id_max` POST-FILTERS the resulting tails (drop a too-new tail; **never rewind** — Phase 4 A1, core.py:602-604). `get_scope_at` instead **filters the candidate states to `source_event_id <= as_of` BEFORE the per-belief max**, so the max is re-derived over the cut window and an older value resurfaces (D-03 — the rewind). That ordering of operations (cut-then-max vs max-then-filter) is the whole phase: cut early ⇒ rewind; filter late ⇒ drop. **Conflating the two is the central trap** the entire phase exists to get right.

The proof, not the code, is where the roadmap's "most complex single query" billing is cashed (D-07, CONTEXT line 21). The deliverable correctness artefact is a pure-Python **operational-fold oracle**: replay the recorded `revise`/`expand`/`contract` op sequence, keeping only ops with `source_event_id <= as_of`, and fold them to the active base; then assert `get_scope_at(scope, cut) == fold(ops, cut)` under Hypothesis on BOTH backends, stepping `as_of` across the event ids (SC2) and generating intra-millisecond-colliding and out-of-order `source_event_id`s (SC3). SC1 (`get_scope_at(latest) == query_scope(current)`) falls out of the same equivalence at the maximal cut. The existing Phase-3 `tests/test_invariants.py` `_SpineMachine` + shadow-oracle idiom is the direct template for tracking the op sequence so the oracle can replay it.

**Primary recommendation:** Implement `get_scope_at` as a near-clone of `query_scope`'s shipped body (single scope-wide `match_nodes` scan → group-by-`belief_id`) with the ONE structural change: apply the inclusive `source_event_id <= str(as_of_event_id)` cut to the candidate rows *before* the per-belief `max(_order_key)`, then apply the retracted-tail→absent collapse (the `_current` rule) and the `_order_key` sort + `_hydrate`. Reuse the ONE `_order_key` for both the cut comparison key form (`str`-vs-`str`) and the per-group max (D-04/D-05). For the cut-aware tail derivation, the cleanest factoring (Claude's discretion, D-06) is a single scope-wide scan with an inline `if row["source_event_id"] <= as_of_str` guard in the group-by loop — symmetric with `query_scope`'s inline loop — rather than N per-belief `_current_tail` calls. Land the operational-fold oracle as a NEW test-only helper in a new `tests/test_scope_at.py`, extending the `tests/test_invariants.py` stateful idiom (fixed event-id pool for collisions; step `as_of` across the pool), parametrized over the existing two-backend `backend` fixture.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `get_scope_at` body (cut, derive cut-window tails, retracted collapse, sort, hydrate) | `MemoryCore` (core.py, driver-blind) | — | Belief-revision/temporal-reconstruction logic lives in the backend-agnostic core (BACK-01 / Phase-2 D-02); it composes port primitives, never imports a driver (enforced by `tests/test_import_purity.py`). |
| The inclusive `source_event_id <= as_of` temporal cut | `MemoryCore` (core.py) | — | The cut is core-side Python over raw dicts using the ONE `_order_key` `str` form (D-04/D-05); the port has no aggregate/ORDER-BY/range primitive, so it is taken core-side identically for both backends. |
| Cut-window ordering-MAX tail derivation | `MemoryCore` (core.py) | — | Derived-current-as-of is core logic (Phase-3 D-01: no stored pointer); the cut-aware max over states `<= as_of` is the cut-aware sibling of `_current_tail` (D-06). |
| Raw node fetch for a scope | `BackendPort.match_nodes` (both adapters) | — | The single read primitive; `get_scope_at` composes ONLY it (D-01 — no `traverse`). Adapters return raw `list[dict]`; core hydrates (Phase-2 D-04). |
| Replay-equivalence proof (`get_scope_at ≡ fold`) | operational-fold oracle (tests/, pure Python) | parametrized `backend` fixture + Hypothesis | D-07: the oracle folds the *operations*, `get_scope_at` folds the *materialized states*; the equivalence is the spec, asserted on both backends. |
| Cross-backend parity of `get_scope_at` output | parametrized `backend` conftest fixture | oracle + example tests | The in-memory oracle and ladybug must return byte-identical ordered `list[BeliefState]` (D-05 / FORMAL-06). |

## Standard Stack

**No new packages.** The phase composes the already-installed, already-verified Phase-1/2 stack. `[VERIFIED: read core.py module imports — only stdlib base64/json/uuid + pydantic models; CLAUDE.md forbids any third runtime dep]`.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | `>=2.11,<3` (installed 2.13.4) | Frozen `BeliefState` hydration at the seam (`_hydrate`) | The only required runtime dep (Phase-2 D-03); `get_scope_at` returns `list[BeliefState]` via `_hydrate`. |
| `ladybug` | `>=0.17,<0.18` (installed 0.17.1) | Reference backend; `match_nodes` Cypher | Reference-backend extra (`doxastica[ladybug]`); `match_nodes` already implemented + parity-tested. No new Cypher needed — `get_scope_at` adds zero port surface. |

### Supporting (dev — already present)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=8` (installed 9.0.3) | Parametrized two-backend test runner | Every `get_scope_at` test takes `backend: BackendPort` via the conftest fixture. |
| `hypothesis` | `6.155.2` | The operational-fold replay-equivalence property (D-07, the SPEC) | The `RuleBasedStateMachine` + shadow-oracle idiom (tests/test_invariants.py) is the direct template; here the oracle additionally steps `as_of` and folds the op sequence. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `match_nodes` scope-scan + core-side cut (D-01) | `traverse` over `SUPERSEDES`/`HAS_REVISION` | REJECTED by D-01 — chain order is implicit in `(source_event_id, state_id)`; an edge walk is the SUPERSEDED Phase-1 sketch and would reintroduce the hydration gap + a second ordering. |
| Cut-then-max in one inline loop | N per-belief cut-aware `_current_tail(as_of=...)` calls | Either is correct (Claude's discretion, D-06). The single scan is ONE ladybug round-trip vs N and mirrors `query_scope`'s shipped shape; the per-belief helper is more reuse-symmetric with `_current_tail`. Both reuse the ONE `_order_key`. |
| Pure-Python operational-fold oracle (D-07) | Compare `get_scope_at` to a second `get_scope_at` impl | REJECTED — the oracle must be an INDEPENDENT spec (folds *operations*, not *states*) so the equivalence is a real cross-check, not a tautology (the `tests/test_invariants.py` `_chain_tail` lesson: recompute via a different surface). |

**Installation:** None. `get_scope_at` adds zero dependencies and zero port primitives.

## Package Legitimacy Audit

> Not applicable — **this phase installs no external packages.** It composes the already-installed, already-audited Phase-1/2 stack (`pydantic`, `ladybug`, `pytest`, `hypothesis`). No new `pip install`, no new import. The Phase-2 audit (CLAUDE.md: `ladybug` 0.17.1 verified on PyPI, `ladybugdb` slopsquat token confirmed ABSENT) stands.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram — `get_scope_at` data flow

```
caller (NVM / postulate test)
   │  get_scope_at(scope_id, as_of_event_id)
   │    e.g. get_scope_at(guard_scope, t0) = "what did the guard believe at T0"
   │         get_scope_at(world, e42)      = "what was true before the sale"
   ▼
┌────────────────────────  MemoryCore.get_scope_at  (core.py, driver-blind, NO traverse) ────────┐
│                                                                                                 │
│  1. fetch raw nodes ───────────────────►  backend.match_nodes("BeliefState",                    │
│     (ONE round-trip; D-01: NO traverse,      {"scope_id": scope_id})  ──►  list[dict]            │
│      NO edges walked; D-08 pure read)                                                            │
│                                       │   absent/empty scope → [] (no _ensure_scope, no UoW)     │
│                                       ▼                                                          │
│  2. TEMPORAL CUT (D-02/D-03/D-04) ─►  keep row iff  row["source_event_id"] <= str(as_of)         │
│     ★ THE ONE DIFFERENCE FROM           (INCLUSIVE; str-vs-str, the _order_key form, Pitfall 1)  │
│       query_scope: cut runs BEFORE    │   ── applied to CANDIDATE STATES, before the max ──      │
│       the per-belief max (cut→max),   ▼                                                          │
│       so an older value can RESURFACE                                                            │
│  3. group cut rows by belief_id  ──►  per (scope,belief): max over _order_key  =  AS-OF TAIL     │
│     (status-AGNOSTIC ordering-max         over the cut window; the cut-aware _current_tail (D-06)│
│      over the <= as_of window)            — state_id tiebreak orders WITHIN one event, D-05)     │
│                                       │                                                          │
│                                       ▼                                                          │
│  4. retracted collapse (D-06) ────►  drop belief iff as-of tail.status == retracted              │
│     (the _current rule, over the cut     (a contracted-as-of belief is ABSENT from the base)    │
│      window not "now")                │                                                          │
│                                       ▼                                                          │
│  5. sort by _order_key  ───────────►  deterministic (source_event_id, state_id) order (reuse)    │
│                                       │                                                          │
│                                       ▼                                                          │
│  6. hydrate  ──────────────────────►  [_hydrate(tail) for tail in kept]  ──►  list[BeliefState]  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
   │  list[BeliefState]  (the active base AS OF as_of_event_id; [] for empty/absent scope)
   ▼
caller
```

The replay-equivalence proof (D-07) is a *separate* path that folds the **operations**, not the states:

```
operational-fold oracle (test-only, pure Python — the SPEC)
   │  ops = recorded [(op, scope, belief, value, source_event_id, append_seq), …]
   ▼
   fold(ops, as_of):
     ├─ keep ops with source_event_id <= as_of                     (the SAME inclusive cut)
     ├─ per (scope, belief): winner = max over (source_event_id, append_seq)   (mirror _order_key)
     ├─ winner is revise/expand ⇒ value present (active)
     │  winner is contract       ⇒ belief ABSENT (retracted-as-of)              (mirror D-06)
     └─ ⇒ {(scope,belief): value}  =  the active base as of as_of
   │
   ▼
ASSERT  { (s.scope_id, s.belief_id): s.value  for s in get_scope_at(scope, cut) }
        ==  fold(ops, cut) restricted to `scope`     for every cut in the event pool
        on BOTH backends   (SC2: step cut; SC3: colliding/out-of-order ids; SC1: cut=max == query_scope)
```

### Recommended Project Structure (no new modules in `src/`)

```
src/doxastica/
├── core.py        # ADD: get_scope_at body (+ optional cut-aware tail helper / as_of param on _current_tail)
├── protocol.py    # UNCHANGED (get_scope_at signature already locked, protocol.py:150-165)
└── models.py      # UNCHANGED (BeliefState/BeliefFilter unchanged; get_scope_at takes scope_id + UUID)
tests/
├── conftest.py        # UNCHANGED (the params=["memory","ladybug"] fixture is reused verbatim)
├── test_invariants.py # UNCHANGED (the Phase-3 keystone; the stateful idiom this phase mirrors)
└── test_scope_at.py   # NEW: get_scope_at example behaviors + the operational-fold replay property
```

### Pattern 1: The temporal cut as a near-clone of `query_scope` (the phase crux)
**What:** `get_scope_at` reuses `query_scope`'s single-scan group-by shape, moving the event-id constraint from a POST-filter on tails (drop) to a PRE-filter on candidate states (rewind).
**When to use:** Always — it is the whole method. The cut-before-max ordering is what distinguishes time-travel from `query_scope`'s window filter.
**Example (illustrative — implementer owns final shape; proven against the real port + models):**
```python
# Source: composed from query_scope (core.py:544-607) + _order_key (core.py:86) + D-02/D-03/D-04/D-06
def get_scope_at(
    self,
    scope_id: str,
    as_of_event_id: UUID,
) -> list[BeliefState]:
    # str-vs-str, the SAME form _order_key uses — never str-vs-UUID (Pitfall 1, Phase-4 Pitfall 3)
    as_of = str(as_of_event_id)
    # 1. ONE scope-wide round-trip; absent scope → [] (D-08: pure read, no _ensure_scope, no UoW)
    rows = self._backend.match_nodes("BeliefState", {"scope_id": scope_id})
    # 2+3. CUT THEN MAX (D-02/D-03): consider only states <= as_of, group by belief, take the
    #      per-group ordering-MAX over that cut window — so an OLDER value can resurface (rewind).
    by_belief: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["source_event_id"] > as_of:  # D-04 inclusive cut: keep <= as_of (drop strictly newer)
            continue
        current = by_belief.get(row["belief_id"])
        if current is None or _order_key(row) > _order_key(current):
            by_belief[row["belief_id"]] = row  # cut-window status-agnostic tail (D-05 tiebreak)
    # 4. retracted-tail → absent collapse over the cut window (D-06; the _current rule, as-of)
    tails = [
        t for t in by_belief.values() if t["status"] != Status.retracted.value
    ]
    # 5. deterministic order (reuse the ONE _order_key) then 6. hydrate
    tails.sort(key=_order_key)
    return [self._hydrate(t) for t in tails]
```
Note how steps 5-6 and the round-trip are byte-identical to `query_scope`; only the `> as_of: continue` guard placement (inside the group-by, before the max) carries the temporal semantics. There is no status *set* resolution here — `get_scope_at` has no `include_retracted` flag; the base is always active-as-of (D-06 drops a retracted-as-of tail unconditionally).

### Pattern 2: The operational-fold oracle (D-07 — the SPEC, mirrors `tests/test_invariants.py`)
**What:** A pure-Python shadow model that records every op `(op_kind, scope, belief, value, source_event_id, append_seq)` and folds them up to a cut.
**When to use:** The required correctness deliverable. The Hypothesis machine drives `revise`/`expand`/`contract`, records each op into the oracle, then asserts `get_scope_at(scope, cut) == fold(ops, cut)` at cuts stepped across the event-id pool.
**Example (composed from `tests/test_invariants.py` `_shadow_current` (lines 170-183) + the D-07 cut):**
```python
# Source: tests/test_invariants.py _shadow_current/_record idiom, extended with the as_of cut
def fold(self, scope_id: str, as_of: str) -> dict[str, Any]:
    """Pure-Python operational fold: the active base of `scope_id` as of `as_of`.

    Mirrors get_scope_at structurally over the OPERATIONS: keep ops <= as_of, per (scope,belief)
    take the winner by (source_event_id, append_seq) [== the _order_key (source_event_id, state_id)
    contract — append_seq stands in for the monotonic core-minted state_id tiebreak], and drop a
    belief whose winning op is a contract (retracted-as-of, D-06).
    """
    base: dict[str, Any] = {}
    for belief_id, entries in self.entries_for_scope(scope_id).items():
        eligible = [e for e in entries if e.source_event_id <= as_of]  # the SAME inclusive cut
        if not eligible:
            continue
        winner = max(eligible, key=lambda e: (e.source_event_id, e.append_seq))  # mirror _order_key
        if winner.op_kind == "contract":   # retracted-as-of ⇒ absent (D-06)
            continue
        base[belief_id] = winner.value
    return base
```
The assertion projects `get_scope_at`'s `list[BeliefState]` to `{belief_id: value}` for the scope and compares to `fold`. Because the fixture runs each example on both backends, agreement with the oracle is already cross-backend parity (the Phase-2/4 lesson). **The oracle must be independent** — it folds operations, the method folds materialized states — so the equivalence is a real proof, not a restatement (the `_chain_tail` independence lesson, `tests/test_invariants.py:87-104`).

### Anti-Patterns to Avoid
- **Cut as a POST-filter on the already-derived current tail (the CENTRAL TRAP, D-03).** Copying `query_scope`'s `event_id_max` shape (derive the per-belief max over ALL states, THEN drop tails `> as_of`) makes a since-revised belief ABSENT instead of rewinding it to the value current at `as_of`. The cut MUST run on the candidate states BEFORE the per-belief max. Cut-then-max = rewind; max-then-cut = drop. This is the one bug the whole phase exists to avoid.
- **Walking `SUPERSEDES`/`HAS_REVISION`/`traverse` (D-01).** The chain order is implicit in `(source_event_id, state_id)`; an edge walk is the SUPERSEDED Phase-1 sketch and reintroduces the hydration gap (`get_impact`'s Option-A re-fetch, core.py:471-519) for no benefit.
- **Introducing a second ordering (D-05).** The cut comparison and the per-group max MUST both use the ONE `_order_key` form. The cut compares `str(source_event_id)` ≤ `str(as_of)`; the max uses the full `(source_event_id, state_id)` key. A separate sort key or a `state_id`-only order desynchronises from the spine.
- **`str`-vs-`UUID` comparison (Pitfall 1 / Phase-4 Pitfall 3).** `match_nodes` rows store `source_event_id` as a `str`; `as_of_event_id` is a `UUID`. Compare `row["source_event_id"] <= str(as_of_event_id)` — `str(UUID)` is the canonical lowercase hyphenated form the core stored via `_append_state`. Mixing `str <= UUID` raises `TypeError`.
- **Exclusive cut (D-04).** The cut is INCLUSIVE (`<=`): a state whose `source_event_id == as_of` IS included. Exclusivity would break SC1 (`get_scope_at(latest) == query_scope(current)`).
- **Auto-creating the scope / wrapping in `unit_of_work` (D-02 pure read).** `get_scope_at` is a pure read: no `_ensure_scope`, no `unit_of_work`, no world-scope guard (reads never trigger it — `get_scope_at(world, e)` is valid and answers "what was true before the sale"). Absent scope → `[]`.
- **An `include_retracted`-style flag.** `get_scope_at` has no status flag; the as-of base is always active-as-of, dropping a retracted-as-of tail (D-06). Do not add a retracted-surfacing mode (not in scope).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ordering of states / the cut key | A new sort key, a `state_id`-only order, or a UUID-int comparator | `_order_key` (core.py:86) + its `str(source_event_id)` form | The ONE ordering contract (D-05); a second one desyncs the read surface from the spine and risks the `str`-vs-`UUID` `TypeError`. |
| As-of current derivation | A stored `CURRENT_STATE`-as-of pointer / per-event snapshot table | Derived cut-window ordering-MAX over append-only states | Phase-3 D-01: current is derived, never stored; the temporal variant is just a narrower candidate window. A snapshot table is the rejected materialization. |
| Value decode on read | Re-implementing base64/JSON decode in `get_scope_at` | `self._hydrate(props)` (core.py:252) | The single value-decode boundary; bypassing it reintroduces the DEF-02-01 brace-coercion corruption. |
| Chain reconstruction | A `traverse`/edge walk to find the as-of tail | The implicit `(source_event_id, state_id)` order over `match_nodes` rows | D-01: chain order is implicit; no edge is needed and walking one is the SUPERSEDED sketch. |
| Cross-backend grouping/cut | Backend-specific Cypher `WHERE … <= $as_of` + GROUP BY | Core-side Python cut + group-by over raw `list[dict]` | Keeps `get_scope_at` driver-blind (BACK-01, enforced by `test_import_purity.py`) and guarantees parity — identical code path for both backends. |
| The replay spec | A second `get_scope_at`-shaped implementation to diff against | An independent pure-Python operational-fold oracle (folds OPS, not states) | D-07: only an independent fold makes the equivalence a real proof, not a tautology. |

**Key insight:** Phase 6 is composition, not construction — and even narrower than Phase 4. The only *new* production code is the `get_scope_at` body, which is `query_scope`'s shipped body with the event-id constraint moved one stage earlier (POST-filter→PRE-filter) and the status-set machinery removed. Everything else (scan, group-by, `_order_key`, retracted collapse, sort, hydrate) is copied verbatim from a method that already passes on both backends. The intellectual weight lives in the *oracle* and the Hypothesis strategy, not the method. Any larger production surface (a snapshot table, an edge walk, a new port primitive) is scope creep.

## Runtime State Inventory

> Phase 6 is greenfield *additive* logic (one new read method + one new test file), NOT a rename/refactor/migration of stored data. No string is renamed; no stored value, key, or schema changes; no caller has yet built against `get_scope_at` (HIST-03 is the one Pending requirement). A focused inventory confirming nothing carries old state:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None.** `get_scope_at` is a pure read over the existing immutable `BeliefState` nodes; it writes nothing and changes no stored string. Verified: the body composes only `match_nodes` + `_hydrate`. | none |
| Live service config | **None** — embedded library; no live service, UI-held config, or scheduler. | none |
| OS-registered state | **None** — no OS registrations. | none |
| Secrets/env vars | **None** — no env var or secret references `get_scope_at`. | none |
| Build artifacts | **None** — `get_scope_at` is an additive method on the existing exported `MemoryCore`; `BeliefStore`/`MemoryCore` are already barrel-exported (`__init__.py`). No new export, no `egg-info`/entry-point change. | none |

**Canonical question — after every file is updated, what runtime state still carries an old name or stale value?** Nothing. `get_scope_at` is the LAST unimplemented method of an already-shipped Protocol; the signature is already present and locked in `protocol.py`. This is pure additive logic — **no data migration task is needed**, explicitly verified, not assumed.

## Common Pitfalls

### Pitfall 1: The cut as a POST-filter — drop instead of rewind (the CENTRAL TRAP)
**What goes wrong:** `get_scope_at(scope, e)` returns NOTHING for a belief that was asserted before `e` and revised after `e`, instead of returning the value it held at `e`.
**Why it happens:** Copying `query_scope`'s `event_id_max` shape — deriving the per-belief ordering-MAX over ALL states first (core.py:587-592), THEN dropping tails whose `source_event_id > as_of`. The max picks the newest (post-`e`) state; dropping it leaves the belief absent. `query_scope` *wants* that drop (Phase-4 A1, D-06); `get_scope_at` must NOT.
**How to avoid:** Run the inclusive cut on the CANDIDATE STATES inside the group-by loop, BEFORE the per-belief max (Pattern 1). The max is then taken over the `<= as_of` window, so the older value resurfaces (D-03 rewind). Order of operations is everything: cut-then-max = rewind; max-then-cut = drop.
**Warning signs:** A test where `get_scope_at(scope, mid_event)` for a revise→revise belief returns `[]` or the newer value instead of the older one; the oracle `fold` and `get_scope_at` diverge precisely on since-revised beliefs.

### Pitfall 2: `str`-vs-`UUID` comparison on the cut (Phase-4 Pitfall 3, recurring)
**What goes wrong:** `TypeError: '<=' not supported between instances of 'str' and 'UUID'`, or a silently wrong boundary if one side is coerced.
**Why it happens:** `match_nodes` rows store `source_event_id` as a `str` (written via `_append_state`'s `str(source_event_id)`, core.py:299); the `as_of_event_id` parameter is a `UUID`. Comparing them directly mixes types.
**How to avoid:** Normalise the cut bound ONCE to the `_order_key` form: `as_of = str(as_of_event_id)`, then compare `row["source_event_id"] <= as_of` (`str`-vs-`str`). `str(UUID)` yields the canonical lowercase hyphenated form, byte-for-byte what the core stored. `[VERIFIED: RFC 9562 §5.7 — the canonical text form is the big-endian hex of the same bytes, so lowercase-hex string order == UUID7 byte/time order; Phase-1 DATA-03 pins "(source_event_id byte-order, state_id tiebreak)" and protocol.py:48-63 documents it]`.
**Warning signs:** `TypeError` at the cut; off-by-one at the exact `as_of` boundary; cross-backend divergence (there is none if both compare `str`-vs-`str`, since both adapters store `str(...)`).

### Pitfall 3: Tiebreak dropped when one event writes several beliefs (D-05 nuance)
**What goes wrong:** When a single turn-event (one `source_event_id`) wrote several beliefs, or the cut lands exactly on a shared `source_event_id`, the inclusive cut wrongly includes/excludes only some of that event's writes, or the per-group max ignores the `state_id` tiebreak.
**Why it happens:** Cutting on `source_event_id` alone is correct (the caller supplies only an event id), but the *max within the included set* must still use the full `(source_event_id, state_id)` key so colliding `source_event_id`s resolve deterministically (D-05).
**How to avoid:** Cut on `str(source_event_id) <= as_of` (event granularity — folds ALL of that event's writes in inclusively, D-04/D-05), but take the per-belief max with the full `_order_key` `(source_event_id, state_id)`. The cut is per-event; the tiebreak orders WITHIN the included set.
**Warning signs:** A multi-belief single-event write where `get_scope_at(scope, that_event)` includes only some of the writes; non-determinism on intra-ms-colliding ids (the SC3 generator must catch this).

### Pitfall 4: Retracted-as-of collapse computed at "now" instead of at the cut (D-06)
**What goes wrong:** A belief that was contracted AFTER `as_of` is wrongly dropped from `get_scope_at(scope, as_of)`, or a belief contracted BEFORE `as_of` wrongly appears.
**Why it happens:** Reusing `_current` (which collapses the retracted tail at "now") instead of applying the retracted rule to the CUT-WINDOW tail. The retracted collapse must run on the as-of tail, not the live tail.
**How to avoid:** Take the cut-window ordering-MAX first (over states `<= as_of`), THEN test THAT tail's status. If the as-of tail is `retracted`, the belief is absent as of `as_of`; if a later (post-`as_of`) state retracted it, that state is outside the cut and irrelevant. This is the `_current` retracted→`None` rule (core.py:230-231) applied over the cut window, not "now" (D-06).
**Warning signs:** `get_scope_at(scope, e_before_contract)` omits a belief that was still active at `e_before_contract`; the oracle and method diverge on beliefs whose contract event straddles the cut.

### Pitfall 5: Empty / absent scope or world-scope handling (D-02 pure read)
**What goes wrong:** `get_scope_at` on a never-created scope raises or auto-creates a `Scope` node; or `get_scope_at(world, e)` raises a `WorldScopeContractionError`.
**Why it happens:** Copying a write-op pattern (`_ensure_scope`, `unit_of_work`, or the world-scope guard) into the read path.
**How to avoid:** `match_nodes("BeliefState", {"scope_id": scope_id})` on an absent scope returns `[]` (verified Phase-4 behaviour on both backends). Return `[]`. No probe, no create, no `unit_of_work`, no world-scope guard — reads are valid on every scope including world (D-02; `get_scope_at(world, e42)` is the canonical "what was true before the sale" call).
**Warning signs:** A `Scope` node appears after a `get_scope_at`; `get_scope_at(WORLD_SCOPE_ID, …)` raises.

### Pitfall 6: A tautological oracle (D-07)
**What goes wrong:** The "oracle" is really a second copy of `get_scope_at`'s state-folding logic, so the equivalence test passes even when both share the same bug.
**Why it happens:** Building the oracle by folding the materialized `BeliefState` nodes (the same data `get_scope_at` reads) instead of the recorded OPERATIONS.
**How to avoid:** The oracle folds the OP SEQUENCE (`revise`/`expand`/`contract` calls recorded in the stateful machine), independent of how the states are stored or selected — mirroring `tests/test_invariants.py`'s `_chain_tail` recomputing via the PUBLIC `get_revision_chain` rather than reusing `_current` (lines 87-104). It must use its own `(source_event_id, append_seq)` winner selection, not call into the core.
**Warning signs:** The oracle imports or calls `MemoryCore._current_tail`/`get_scope_at`; the property test never fails even under a deliberately-injected cut bug.

## Code Examples

### Recording the op sequence so the oracle can replay it (extends `tests/test_invariants.py`)
```python
# Source: tests/test_invariants.py _record (lines 160-168), extended to carry op_kind for the fold
def _record(self, op_kind: str, scope_id: str, belief_id: str, value: Any,
            source_event_id: uuid.UUID) -> None:
    """Append one op to the shadow op-log, bumping the monotonic append seq (state_id stand-in)."""
    self._seq += 1
    self.ops.append(Op(op_kind, scope_id, belief_id, value, str(source_event_id), self._seq))
# revise/expand record op_kind="revise"; contract records op_kind="contract" (value irrelevant).
```

### Stepping `as_of` across the event pool (SC2) with colliding ids (SC3)
```python
# Source: tests/test_invariants.py _EVENT_POOL idiom (line 66) — a small FIXED UUID7 pool forces
# collisions; the cut steps across every pooled id PLUS a below-all and above-all sentinel.
_EVENT_POOL: tuple[uuid.UUID, ...] = tuple(uuid.uuid7() for _ in range(3))  # collisions guaranteed

@invariant()
def scope_at_equals_fold_for_every_cut(self) -> None:
    for scope_id in _SCOPE_POOL:
        for cut in (*_EVENT_POOL, max(self._all_event_strs(), default="")):  # SC2: step the cut
            cut_str = str(cut)
            got = {
                s.belief_id: s.value
                for s in self.core.get_scope_at(scope_id, _as_uuid(cut))
            }
            assert got == self.fold(scope_id, cut_str), (
                f"get_scope_at({scope_id}, {cut_str}) must equal the operational fold"
            )
    # SC1 corollary at the maximal cut: get_scope_at(latest) == query_scope(current).
```
*(Illustrative — the Hypothesis strategy shape is Claude's discretion per CONTEXT; the oracle determines the assertion.)*

### SC1 equivalence at the maximal cut (`get_scope_at(latest) == query_scope(current)`)
```python
# Source: D-04 inclusivity makes the maximal cut fold the full history == the live current.
# A direct example test (not only the property): pick a cut >= every written source_event_id.
latest = max(all_written_event_ids)  # any id >= the maximum included
at_latest = {(s.belief_id, s.value) for s in core.get_scope_at("s", latest)}
now       = {(s.belief_id, s.value) for s in core.query_scope("s", BeliefFilter())}
assert at_latest == now, "get_scope_at at/after the latest event equals query_scope now (SC1, D-04)"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| "`get_impact` and `get_scope_at` compose from `traverse`" (Phase-1 CONTEXT sketch) | `get_scope_at` composes the `match_nodes` scope-scan; chain order is implicit in `(source_event_id, state_id)` | Phase-6 D-01 (already superseded for `query_scope` in Phase 4) | No edge walk, no hydration gap; the method is a `query_scope` temporal variant. |
| Event-id constraint as a POST-filter on derived tails (drop) | Event-id constraint as a PRE-filter on candidate states (rewind) | Phase-6 D-02/D-03 | The cut re-derives the per-belief tail over the `<= as_of` window so older values resurface; this IS time-travel. |
| Materialized per-event snapshot / stored as-of pointer | Derived cut-window ordering-MAX over immutable append-only states | Phase-3 D-01 (carried to Phase 6) | No snapshot table; the as-of base is computed structurally, "free" (NVM `06:86`). |

**Deprecated/outdated:**
- The Phase-1 "composes from `traverse`" framing for `get_scope_at` — SUPERSEDED by D-01 (no edge walk).
- Any `event_id_max`-shaped POST-filter for `get_scope_at` — that is `query_scope`'s DROP semantics (Phase-4 D-06), the exact thing D-03 diverges from. Do not copy core.py:602-604 into `get_scope_at`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The single scope-wide `match_nodes` scan + inline core-side cut (vs N per-belief cut-aware `_current_tail` calls) is the preferred factoring | Pattern 1 / Standard Stack Alternatives | Low — both are correct and parity-equivalent (Claude's discretion per D-06); the single scan mirrors `query_scope`'s shipped shape and is ONE ladybug round-trip vs N. Reversible without API change. |
| A2 | The operational-fold oracle / Hypothesis strategy is best built by extending the `tests/test_invariants.py` `_SpineMachine` idiom (fixed event-id pool + shadow op-log) | Pattern 2 / Code Examples | Low — Hypothesis strategy shape is explicitly Claude's discretion (CONTEXT); the assertion (`get_scope_at == fold`) is locked by D-07, only the generator design is open. |

**All other claims are VERIFIED against read source or CITED from the locked CONTEXT / Phase-3/4 decisions.** A1/A2 are the only genuinely open choices, both low-risk and both explicitly inside Claude's discretion per CONTEXT.

## Open Questions (RESOLVED)

1. **Cut-aware tail factoring: extend `_current_tail` with an `as_of` param vs. an inline cut in a fresh scan (A1)** — **RESOLVED: inline cut in the single scope-wide scan (recommended), per Claude's discretion (D-06).**
   - What we know: D-06 names both options as fine provided the ONE `_order_key` is reused.
   - What's unclear: whether to thread an `as_of: str | None = None` bound through `_current_tail` (which `query_scope` would call with `None`) or keep `get_scope_at`'s cut inline.
   - Recommendation: Keep the cut inline in `get_scope_at`'s group-by loop (Pattern 1) to mirror `query_scope`'s shipped shape and avoid touching `_current_tail`'s Phase-3/4 callers; OR, equivalently, add `as_of` to `_current_tail` if the implementer prefers maximal reuse. Both reuse `_order_key`; either passes the oracle. Pinned in the plan as a Claude's-discretion implementation choice.

2. **Whether to assert SC1 (`get_scope_at(latest) == query_scope(current)`) as a standalone example test in addition to the fold property** — **RESOLVED: yes, both.**
   - What we know: SC1/SC2/SC3 all collapse into the D-07 fold property, but SC1 is the cleanest single regression and the most legible "sanity" assertion.
   - Recommendation: Land an explicit `test_scope_at_latest_equals_query_scope_now` example (Pattern 3 code example) AND the fold property. The example is a fast, readable guard; the property is the spec.

## Environment Availability

> No new external dependencies. The phase composes the already-installed stack. The one optional dependency (`ladybug`) is already gated by `pytest.importorskip` in the conftest fixture (skips, never fails, when absent).

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `pydantic` | `BeliefState` hydration (`_hydrate`) | ✓ (required dep) | 2.13.4 | — (required) |
| `ladybug` | ladybug-backend parity + oracle property | ✓ if `[ladybug]` extra installed | 0.17.1 | `importorskip` → memory-only test run (conftest already handles) |
| `pytest` | test runner | ✓ (dev) | 9.0.3 | — |
| `hypothesis` | the operational-fold replay-equivalence property (D-07) | ✓ (dev) | 6.155.2 | example-based cut tests still prove the mechanism; the fold property is the SPEC and should run |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `ladybug` — absent → the parametrized fixture / stateful machine skips the ladybug param (Job-1 base-install path); the in-memory param still proves `get_scope_at` behaviour and the fold equivalence on one backend.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` 9.0.3 + `hypothesis` 6.155.2 (the fold property is REQUIRED, D-07) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`); shared fixtures in `tests/conftest.py` |
| Quick run command | `uv run pytest tests/test_scope_at.py -x -q` |
| Full suite command | `uv run pytest -q` |
| Backend parametrization | `backend` fixture (`params=["memory", "ladybug"]`, `importorskip`) — every example test runs on BOTH backends; the fold machine exposes two `.TestCase` subclasses (memory + ladybug), mirroring `tests/test_invariants.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HIST-03 / D-03 | The cut REWINDS: revise→revise, `get_scope_at(scope, first_event)` returns the OLDER value (not absent, not newer) | unit (param both backends) | `uv run pytest tests/test_scope_at.py::test_cut_rewinds_to_older_value -x` | ❌ Wave 0 |
| HIST-03 / D-04 | Inclusive cut: a state with `source_event_id == as_of` IS included | unit | `... ::test_cut_is_inclusive_at_boundary -x` | ❌ Wave 0 |
| HIST-03 / SC1 / D-04 | `get_scope_at(latest) == query_scope(current)` | unit (param) | `... ::test_scope_at_latest_equals_query_scope_now -x` | ❌ Wave 0 |
| HIST-03 / D-06 | Retracted-as-of: a belief contracted AT/BEFORE the cut is ABSENT; one contracted AFTER the cut is PRESENT at its as-of value | unit | `... ::test_retracted_as_of_collapse -x` | ❌ Wave 0 |
| HIST-03 / D-05 | A single multi-belief event folds ALL its writes inclusively; intra-event order uses the `state_id` tiebreak | unit | `... ::test_single_event_multi_belief_inclusive -x` | ❌ Wave 0 |
| HIST-03 / D-02 / D-08 | Absent/empty scope → `[]`, creates no `Scope` node; `get_scope_at(world, e)` is valid (no world-scope guard) | unit | `... ::test_empty_scope_and_world_read -x` | ❌ Wave 0 |
| HIST-03 / D-01 | Result is `_order_key`-sorted; in-memory ≡ ladybug sequence (no `traverse` consulted) | unit (param) | `... ::test_scope_at_deterministic_order -x` | ❌ Wave 0 |
| HIST-03 / SC2 / SC3 / D-07 | **`get_scope_at(scope, cut) == fold(ops, cut)`** for every cut, under Hypothesis, on BOTH backends — with colliding + out-of-order `source_event_id`s and `as_of` stepped across event ids | property (stateful, both backends) | `uv run pytest tests/test_scope_at.py -k Fold -q` | ❌ Wave 0 |
| HIST-03 (regression) | Phase-3/4 surface unchanged — `_current`/`query_scope`/keystone still green after any `_current_tail` touch | regression | `uv run pytest tests/test_invariants.py tests/test_query_scope.py tests/test_revision_spine.py -q` | ✅ (exists) |
| HIST-03 (purity) | `core.py` still imports no `ladybug` after adding `get_scope_at` (no driver, no Cypher) | regression | `uv run pytest tests/test_import_purity.py -q` | ✅ (exists) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_scope_at.py -x -q` (the new file; example tests are sub-second on memory + ladybug; the fold property runs bounded — `max_examples=50, stateful_step_count=20` per the `tests/test_invariants.py` precedent).
- **Per wave merge:** `uv run pytest -q` (full suite — MUST include the unchanged `tests/test_invariants.py` keystone + `tests/test_query_scope.py`, proving any `_current_tail` touch is behaviour-preserving, and `tests/test_import_purity.py` proving `core.py` stays driver-blind).
- **Phase gate:** Full suite green on BOTH backends + the fold property green on both + basedpyright strict clean + ruff clean, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_scope_at.py` — NEW FILE. Covers HIST-03: the cut-rewind example, inclusive-boundary, SC1 equivalence, retracted-as-of collapse, single-event multi-belief, absent/empty/world read, deterministic order — all parametrized over the existing `backend` fixture — PLUS the operational-fold `RuleBasedStateMachine` (two `.TestCase` subclasses, memory + ladybug) carrying the `fold(ops, as_of)` oracle and the `get_scope_at == fold` invariant (D-07).
- [ ] No `conftest.py` change needed — the `params=["memory","ladybug"]` fixture is reused verbatim; the stateful machine reuses the `tests/test_invariants.py` `_make_backend` idiom (bounded `Database(max_db_size=2**30)` to cap per-example mmap reservation on ladybug).
- [ ] No framework install — `pytest` + `hypothesis` already in the dev group.
- [ ] No `src/` test-support gaps — `get_scope_at` composes only shipped core helpers + `match_nodes`.

*(Existing infrastructure covers the regression + purity surface; the only genuinely new test file is `tests/test_scope_at.py`. The oracle is test-only Python, not production code.)*

## Security Domain

> `security_enforcement` is absent from `.planning/config.json` (treated as enabled). Phase 6 is an **embedded-library read method** with no network, no auth, no session, and no free user input — the sole argument beyond `scope_id` is a typed `UUID`. The relevant control is input-validation-by-construction, already satisfied by the closed signature (no free `str`, no query string).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface (embedded library tenant of NVM). |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | The core is a closed-subgraph tenant; access policy is NVM-layer (R19/R21). `get_scope_at` reads only within the injected backend's namespace (CONN-02). |
| V5 Input Validation | yes | `get_scope_at(scope_id: str, as_of_event_id: UUID)` — no free query string, no interpolation; `match_nodes` binds `$param` values + validated identifiers (ladybug `_validate_identifier`). The `str(as_of_event_id)` cut is a canonical UUID text form, not attacker-controlled free text. |
| V6 Cryptography | no | No crypto in the read path. (UUID7 ids are identifiers, not secrets.) |

### Known Threat Patterns for the doxastica read surface
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via a free query string | Tampering / Info-disclosure | Designed out: `BackendPort` exposes NO query-string method (BACK-01 LPG-primitive); `get_scope_at` composes `match_nodes` with `$param`-bound values. Phase 6 adds NO new interpolation and NO new port method. |
| Triple-structure / schema leak across the seam | Info-disclosure | `get_scope_at` returns frozen `BeliefState` models via `_hydrate`; no raw dict / internal `_`-prefixed key escapes (the ladybug adapter strips them; core returns models only). |
| Reading another tenant's namespace | Info-disclosure | The ladybug adapter is the sole reader/writer of its `{ns}_*` subgraph (CONN-02); `get_scope_at` runs entirely within the injected backend's namespace. No change in Phase 6. |
| Temporal info-disclosure (reading a past state a caller shouldn't see) | Info-disclosure | Out of the core's remit: access/temporal-visibility policy is NVM-layer (R19/R21). The core faithfully reconstructs the structural as-of base; *who may call `get_scope_at` with which `as_of`* is the consumer's policy, not the core's. |

**No new security-sensitive surface is introduced.** The phase is a read composed of already-injection-proofed primitives, with a typed-`UUID` cut argument that cannot carry free text.

## Sources

### Primary (HIGH confidence)
- `src/doxastica/core.py` (read in full) — `query_scope` (the template pipeline, lines 544-607), `_order_key` (the ONE ordering contract, 86-96), `_current_tail` (status-agnostic ordering-max, 192-213), `_current` (retracted→`None` collapse, 215-232), `_hydrate` (252-267), `_append_state` (stores `str(source_event_id)`, 270-307), `get_impact` (the `traverse`+hydration-gap path `get_scope_at` deliberately does NOT use). The exact reuse + divergence surface.
- `src/doxastica/protocol.py` (read in full) — the LOCKED `get_scope_at` signature + as-of-cut docstring (150-165, no change) and the UUID7 ordering-contract docstring (48-63).
- `src/doxastica/models.py` (read in full) — `BeliefState`, `BeliefFilter`, `Status` `{active, retracted}`, `WORLD_SCOPE_ID`. `get_scope_at` takes `scope_id` + `UUID`, returns `list[BeliefState]`.
- `tests/test_query_scope.py` (read in full) — the Phase-4 example idiom (`event_id_max` POST-filter / drop-never-rewind, `test_event_range_postfilter` line 152) the cut diverges from; the parametrized two-backend convention.
- `tests/test_invariants.py` (read in full) — the `RuleBasedStateMachine` + shadow-oracle idiom (the direct template for the fold oracle): `_EVENT_POOL` collision pool (66), `_record`/`_shadow_current` (160-183), `_chain_tail` independent recompute (87-104), the two-backend `.TestCase` subclassing + bounded `Database(max_db_size)` (132-148, 335-355).
- `tests/test_backend_parity.py`, `tests/test_cascade.py`, `tests/conftest.py` (read in full) — the byte-identical-across-backends comparison idiom, `_both_backends`, the `params=["memory","ladybug"]` + `importorskip` fixture.
- `.planning/phases/06-structural-time-travel/06-CONTEXT.md` — the locked D-01..D-07 decisions (authoritative).
- `.planning/phases/04-retrieval-observation-surface/04-RESEARCH.md` + `04-CONTEXT.md` — the `query_scope` decisions, the `event_id_max` POST-filter (drop, never rewind) the central trap diverges from, and Phase-4 Pitfall 3 (`str`-vs-`UUID`).
- `.planning/REQUIREMENTS.md` (HIST-03 + FORMAL-03), `.planning/STATE.md` — the Phase-3 `_current` "ordering-max over ALL statuses, retracted→None" fix and the Phase-5 `traverse` `direction` default-`"out"` cross-phase contract noted to keep `get_scope_at` green.

### Secondary (MEDIUM confidence)
- RFC 9562 §5.7 (UUID7) canonical text form ↔ byte order — grounds Pitfall 2's "lowercase-hex string order == time order" claim (already pinned by Phase-1 DATA-03 in `protocol.py:48-63`).
- NVM design refs cited in CONTEXT `<canonical_refs>` (`21 §Event Sourcing+CQRS` lines 98-105; `06` lines 82-87; `05 §3`/§8) — the consumer contract (no traverse, rewind-not-drop, replay=spec) that drove D-01/D-03/D-07. Used only to confirm the locked decisions, not re-derive them; cited as grounding, not re-read into new claims.

### Tertiary (LOW confidence)
- None. No WebSearch / external docs were needed — the phase is wholly in-repo composition of an already-shipped spine + `query_scope` template.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, no new port primitive; reuse surface read directly from source.
- Architecture: HIGH — the `get_scope_at` composition path (cut-then-max) verified against the actual `query_scope` body, port, and models; the ONE divergence (cut placement) is precisely located against core.py:587-604.
- Pitfalls: HIGH — each pitfall is grounded in a specific read line (the `event_id_max` POST-filter at core.py:602-604; `_current`'s retracted collapse at core.py:230-231; `_append_state`'s `str(source_event_id)` at core.py:299) or a locked CONTEXT decision (D-03 central trap, D-04 inclusivity, D-05 tiebreak, D-06 collapse).
- Validation: HIGH — every requirement maps to a concrete pytest command over the existing fixture; the fold property has a direct template in `tests/test_invariants.py`.
- Assumptions: only A1 (single-scan cut factoring) and A2 (oracle/strategy shape), both low-risk and explicitly within Claude's discretion per CONTEXT.

**Research date:** 2026-06-19
**Valid until:** 2026-07-19 (stable — in-repo composition; no fast-moving external dependency. The only invalidator is a change to the Phase-3 `_current`/`_order_key` contract or the Phase-4 `query_scope` body, both of which this phase deliberately mirrors and preserves.)
