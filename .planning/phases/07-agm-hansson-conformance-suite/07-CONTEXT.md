# Phase 7: AGM/Hansson Backend Conformance Suite & Irony Join (M0 Exit Gate) - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Assemble the **M0 exit gate** — the mechanically-verified proof that is the library's reason to
exist — as a **backend conformance suite**: every registered backend (the in-memory oracle and the
ladybug reference adapter) must pass the **same** parameterised postulate + invariant tests. This
phase adds **essentially no production code**; every postulate, invariant, the Recovery `xfail`, and
the irony join are query/test patterns over the nine operations already shipped in Phases 3–6.

Delivers (the six requirements):
- **FORMAL-01** — AGM revision postulates green via Hypothesis stateful tests over op sequences:
  Success (K*2), Inclusion (K*3), Vacuity (K*4), Consistency (K*5), Extensionality (K*6). Closure
  (K*1) dropped by construction (belief *bases*, not closed sets).
- **FORMAL-02** — Hansson belief-base contraction postulates green: Contraction Success, Inclusion,
  Relevance, Core-Retainment, Uniformity.
- **FORMAL-03** — structural-invariant suite green: `CURRENT_STATE` uniqueness, chain immutability,
  `get_scope_at ≡ replay`, world-scope no-contraction.
- **FORMAL-04** — AGM **Recovery deliberately excluded**: a loud, named, *strict* `xfail` with
  rationale, plus positive superseded-chain replacement tests in its place.
- **FORMAL-05** — the **irony join** demonstrated on synthetic data: actor-scope vs. world-scope
  divergence on `belief_id`, computed in one db round-trip.
- **BACK-05** — the postulate + invariant suite runs as a **conformance suite** parameterised over
  every registered backend (the parametrization *is* the requirement, not a discrete step).

**Depends on:** Phase 4 (`query_scope`, `get_revision_chain`), Phase 5 (edges, `get_impact`),
Phase 6 (`get_scope_at` + its replay oracle) — and the Phase-3 keystone `_SpineMachine`
(`tests/test_invariants.py`), which the suite extends rather than replaces.

**Out of scope (Phase 8):** the runtime-dep audit, MIT license, mkdocs-material site, the published
"how to write a backend" port-contract docs, the CI 3.11/3.14 matrix + release pipeline. Also out:
Closure K*1 (dropped by construction); any *new* Protocol operation (none needed); AGM Recovery as a
*passing* test (it is a named xfail, never asserted true).

</domain>

<decisions>
## Implementation Decisions

### The irony join is uniform core-level over the generic port — Option A (LOCKED)
- **D-01:** The irony join is computed **uniformly over the generic `BackendPort`**, exactly like
  `query_scope` / `get_scope_at` / `get_impact` — NOT pushed into backend-specific Cypher. Shape:
  **ONE `match_nodes("BeliefState", {})` round-trip** → derive the active current tail per
  `(scope, belief)` in core Python (reuse `_order_key` + the `_current_tail` max + retracted-tail
  collapse) → keep `{scope_a, scope_b}` → inner-join on `belief_id` → emit rows where `value`
  differs. Identical code, both backends, parameterised. **"Single query" = one port round-trip** —
  the same meaning it has for every other derived query in this codebase. **Grounding:** the port is
  generic (`upsert_node`/`add_edge`/`match_nodes`/`traverse`/`unit_of_work`); the ladybug adapter
  only pushes property-equality `MATCH` to Cypher; ALL derived-current logic already lives in core
  (`query_scope` is `match_nodes` scan → Python group-by-max). A bespoke single-Cypher join (Option
  B) was **rejected**: it would add backend-specific query surface, breaking the narrow-port non-goal
  and the uniform "compute derived queries in core" pattern.
- **D-01a (one round-trip, not two `query_scope` calls):** Target a SINGLE `match_nodes` scan, then
  filter to the two scopes in Python — `match_nodes` AND-equality can't express
  `scope_id IN {a, b}`, and two `query_scope` calls would be two round-trips, missing the
  "single query" goal. Synthetic demo data is small, so the full-label scan is cheap and honest.
  Likely refactor: extract `query_scope`'s steps 3–4 (group-by-`belief_id` → per-group ordering-max
  → status filter) as a pure `rows -> current tails` helper both `query_scope` and the irony join
  reuse — keeps the ONE `_order_key` contract single-sourced.

### The irony join's key is `belief_id`; the ARCHITECTURE.md Cypher sketch is SUPERSEDED
- **D-02:** Join on **`belief_id` directly**. The `research/ARCHITECTURE.md` irony-join Cypher (joins
  via `CURRENT_STATE`/`HOLDS` edges on `belief_id_logical`) is **SUPERSEDED** — none of those exist:
  Phase-3 D-01 made current DERIVED (no `CURRENT_STATE` pointer edge, no `HOLDS`), and the model has
  **no `belief_id_logical`** — `belief_id` *is* the scope-independent proposition id (`scope_id` is a
  separate `BeliefState` field). Same `belief_id` across two scopes = same proposition, different
  holders.

### The irony join's expected result is a plain-Python oracle; "single query" is a graph-DB notion
- **D-03:** The synthetic data is small and known, so the **expected divergent rows are computed
  directly in the test** (plain Python) and compared against the irony-join result. No second-backend
  implementation, no port widening. The in-memory backend is **not required to satisfy "single
  query"** — "one db round-trip" is meaningless for a Python dict — but it runs the SAME uniform core
  logic (D-01), so cross-backend result parity still holds and the demonstration stays honest.
- **D-03a (boundary — no narrative naming in core):** "Actor", "world", "irony", "dramatic irony"
  are NVM's framing; the core sees only *two scopes diverging on `belief_id`*. If the join lives in
  core it MUST be named neutrally (e.g. diverging-beliefs-between-two-scopes), never `irony`/`actor`
  — each such word is the leak the seam exists to prevent (CLAUDE.md boundary). `WORLD_SCOPE_ID`
  already exists; an "actor" scope is just any non-world scope.

### AGM Recovery is a loud, named, strict xfail — the single deliberate exclusion
- **D-04:** Encode Recovery (`K ⊆ (K ÷ p) + p`) as a **deterministic, hand-built belief-base
  counterexample** asserting Recovery's conclusion, marked
  `@pytest.mark.xfail(strict=True, reason="AGM Recovery excluded — belief base (not closed set);
  Hansson; replaced by superseded-chain semantics")`. **NOT** a Hypothesis sweep (a property-based
  xfail is fragile — a *strict* XPASS would fire on mere absence-of-counterexample in N examples,
  which is not a proof). **NOT** a silent omission (invisible in a suite that *is* the formal proof).
  **NOT** a bare `assert` (would red-fail CI against correct code). **`strict=True` is the drift
  guard:** if the engine ever *satisfies* Recovery (e.g. drifts toward closed belief sets), the test
  **XPASSes → suite goes red**, loudly announcing the semantics moved away from belief-base.
  **Grounding:** CLAUDE.md "one deliberate exclusion (AGM *recovery*, replaced by superseded-chain
  semantics)"; STATE.md blocker "never assert it against correct code"; Hansson base contraction
  drops Recovery and replaces it with Relevance + Core-Retainment (the FORMAL-02 pair).

### Positive superseded-chain tests fill Recovery's slot
- **D-05:** In Recovery's place, assert superseded-chain **replacement** (these PASS): after
  `contract(p)` then `revise(p, v')`, the chain reads `active(v) → retracted → active(v')`; the old
  value is NOT silently restored; the derived current resolves to `v'`; and `get_revision_chain`
  still contains the contracted state (append-only — nothing deleted). **Keep distinct from temporal
  recoverability:** AGM Recovery (the *postulate*) is excluded; *history* recoverability
  (`get_scope_at` / `get_revision_chain` reconstructs any past state — Phase 6, satisfied) is a
  separate, held property. Do not conflate the two.

### The postulate + invariant suite extends the existing `_SpineMachine`
- **D-06:** FORMAL-01/02/03 build on the Phase-3 keystone `tests/test_invariants.py` `_SpineMachine`
  — same `RuleBasedStateMachine` + shadow-dict oracle + fixed id/event pools (forcing `state_id`
  tiebreaks) + the two-subclass `Memory*`/`Ladybug*` `.TestCase` dual-backend idiom (ladybug SKIPS,
  not fails, when the driver is absent). **The shadow oracle IS the AGM belief base**; postulates are
  asserted by comparing `query_scope` output against the oracle's derived-current set. BACK-05 is
  satisfied transversally by this parametrization, not as a separate step.
- **D-06a:** Per the CLAUDE.md testing notes, single-operation postulates (Extensionality K*6,
  Vacuity K*4) MAY be plain `@given` property tests where a full sequence is overkill; the
  sequence-sensitive postulates (Success, Inclusion, Consistency) and the structural invariants ride
  the stateful machine. *(Claude's discretion — see below.)*

### Hansson postulates phrased against superseded-chain semantics, NOT classical partial-meet
- **D-07:** Relevance and Core-Retainment must be phrased against doxastica's **append-only
  superseded-chain contraction** (contract APPENDS a retracted state; `revise ≡ expand`; there is NO
  value-semantic consistency engine — only structural `SUPERSEDES` + `DEPENDS_ON`), **not** classical
  partial-meet remainder sets. This picks up the deferral explicitly flagged in
  `tests/test_cascade.py` ("the AGM Relevance/Core-Retainment POSTULATE tests are Phase 7 — NOT
  here"). **Grounding:** CLAUDE.md (Hansson base contraction, no recovery); the
  *Kumiho value & consistency model* memory (paper stores ground triples; no value-semantic
  consistency engine; revise ≡ expand at core).

### FORMAL-03 extends the two invariants already present
- **D-08:** `test_invariants.py` already asserts derived-current consistency + chain immutability.
  Add the full named set: **`CURRENT_STATE` uniqueness** phrased as the derived-current
  single-valued *theorem* (there is no pointer edge to corrupt — Phase-3 D-01 — it is the unique
  ordering-max under a unique `state_id` tiebreak); **`get_scope_at ≡ replay`** lifted from the
  Phase-6 Hypothesis property into the conformance harness; **world-scope no-contraction** (already
  present as `world_contract_raises`, route into the registered set).

### Claude's Discretion
- Whether each AGM postulate is an `@invariant` on the spine machine vs. a standalone `@given` test
  (D-06a) — the oracle/comparison is the spec; the harness placement is open.
- The exact home of the irony-join code (a test-level helper vs. a neutrally-named core method),
  provided it is one round-trip (D-01a) and leaks no narrative naming into core (D-03a).
- Whether `get_scope_at ≡ replay` is re-expressed as a registered `@invariant` or the Phase-6
  property is re-run inside the conformance harness (D-08) — either satisfies FORMAL-03.
- The precise Recovery counterexample base (D-04), provided it is deterministic and documented.

</decisions>

<specifics>
## Specific Ideas

- The suite is the *proof*, so its honesty matters more than its size: the shadow oracle must assert
  the postulates WITHOUT baking the implementation into the oracle (the Phase-3 oracle already
  models the ordering/tiebreak independently — keep that discipline when extending it to postulates).
- The Recovery xfail is a *positive* artifact, not a gap: a green strict-xfail + the superseded-chain
  positives together say "we know Recovery is an AGM postulate, we deliberately don't satisfy it,
  here is the behaviour that replaces it" — a documented, mechanically-guarded negative result.
- The irony join is the showcase of *why* multi-scope (the deliberate Kumiho extension) earns its
  keep: dramatic irony is **computed** from two scopes diverging on a proposition, not remembered.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### In-repo proof lineage (the harness this phase extends)
- `tests/test_invariants.py` — the Phase-3 `_SpineMachine` keystone: `RuleBasedStateMachine` +
  shadow-dict oracle + fixed id/event pools + two-subclass dual-backend `.TestCase` idiom +
  `teardown` closing the ladybug handle. FORMAL-01/02/03 extend THIS (D-06).
- `tests/test_cascade.py` — explicitly DEFERS the Relevance/Core-Retainment postulate tests to this
  phase (D-07); the cascade behaviour they build on.
- `tests/test_scope_at.py` — the Phase-6 `get_scope_at ≡ replay` operational-fold oracle to lift
  into the conformance harness (D-08, FORMAL-03).
- `tests/conftest.py` — the `params=["memory","ladybug"]` throwaway-backend fixture + `importorskip`
  skip-not-fail discipline = the BACK-05 parametrization mechanism.
- `src/doxastica/core.py` — `query_scope` (the derived-current pipeline the irony join reuses;
  steps 3–4 are the extractable `rows -> tails` helper, D-01a), `_order_key` / `_current_tail` /
  `_current` (the ONE ordering contract + retracted collapse), `get_revision_chain` (superseded-chain
  positives, D-05), `get_scope_at` (FORMAL-03 invariant).
- `src/doxastica/ports.py` — the generic `BackendPort` surface; the grounding for Option A (D-01):
  no belief-revision-aware query method exists or should be added.

### Project-level contract (what the exit gate must prove)
- `.planning/REQUIREMENTS.md` — FORMAL-01..05, BACK-05 (the six requirements); FORMAL-06 already
  satisfied (throwaway `:memory:` per example).
- `.planning/PROJECT.md` — the irony-join demonstration + "no recovery, superseded chains" framing.
- `.planning/research/ARCHITECTURE.md` §"Irony join" (lines 323–337) — **READ AS SUPERSEDED**: its
  `CURRENT_STATE`/`HOLDS`/`belief_id_logical` Cypher is replaced by D-01/D-02 (derived-current,
  join on `belief_id`).
- `.planning/research/PITFALLS.md` (lines 43, 66) — the `CURRENT_STATE`-uniqueness and
  world-scope-contraction traps the invariants exist to catch.
- CLAUDE.md — Kumiho fidelity, the deliberate Recovery exclusion, the Hansson base-contraction
  posture, the no-narrative-in-core boundary (D-03a).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_SpineMachine` (`tests/test_invariants.py`): the stateful harness + shadow oracle + dual-backend
  `.TestCase` plumbing — extend, don't rewrite (D-06).
- `query_scope` derived-current pipeline + `_order_key` / `_current_tail` (`core.py`): reuse for the
  irony join's per-`(scope,belief)` tail derivation (D-01); candidate `rows -> tails` extraction
  (D-01a).
- The Phase-6 replay oracle (`tests/test_scope_at.py`): the `get_scope_at ≡ replay` proof to wire
  into the conformance suite (D-08).
- `conftest.py` `backend` fixture: the BACK-05 parametrization (D-06).

### Established Patterns
- Driver-blind core + import purity (`tests/test_import_purity.py`): the irony join composes ONLY
  `match_nodes` — no Cypher, no `ladybug` import in core (D-01).
- xfail flip discipline (`tests/test_backend_parity.py` DEF-02-01: xfail → passing once a control
  closes) — the inverse of the Recovery xfail, which must stay xfail forever (strict guard, D-04).
- Fixed colliding `source_event_id` pools forcing the `state_id` tiebreak (Pitfall 6) — keep when
  extending the oracle to postulates.

### Integration Points
- All nine operations are shipped; this phase adds NO Protocol operation. The only candidate
  production change is the optional neutrally-named irony-join core method (D-03a) or the
  `rows -> tails` helper extraction (D-01a) — both small, both optional (a test-level helper is
  acceptable).
- The Recovery counterexample + superseded-chain positives + irony-join demo are new test files
  (e.g. `tests/test_recovery_xfail.py`, `tests/test_irony_join.py`); the postulate/invariant
  extensions land in/alongside `tests/test_invariants.py`.

</code_context>

<deferred>
## Deferred Ideas

- A bespoke single-Cypher irony join pushed into the ladybug backend (Option B) — rejected here
  (D-01) as narrow-port-non-goal violation; could be reconsidered only as a backend-internal
  optimization that does NOT widen the port, and only if a real performance need appears (none for
  M0 synthetic demos).
- Widening `BackendPort` with any belief-revision-aware query (`irony_join`, `current_states`, …) —
  out of scope; the port stays generic (D-01).
- The runtime-dep audit, MIT license, mkdocs port-contract docs, CI 3.11/3.14 matrix + release
  pipeline — Phase 8 (PKG-02/03/04).
- AGM Closure (K*1) — dropped by construction (belief bases); not a test, not an xfail.

</deferred>

---

*Phase: 07-agm-hansson-conformance-suite*
*Context gathered: 2026-06-19*
