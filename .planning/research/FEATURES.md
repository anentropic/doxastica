# Feature Research

**Domain:** Graph-native AGM belief-revision memory core (standalone Kumiho implementation, arXiv 2603.17244) — a zero-LLM, domain-agnostic Python library
**Researched:** 2026-06-13
**Confidence:** HIGH (formal postulates verified against the Stanford Encyclopedia of Philosophy, Hansson's representation theorems, and the Flouris impossibility result; API surface taken verbatim from the authoritative design `05-nvm-memory-core.md §3`)

> **Reading note for the roadmap.** "Features" here are *mechanisms and formal-correctness
> obligations*, not a product feature set. The single most important section is
> **[Formal Correctness Obligations](#formal-correctness-obligations-the-differentiator)** — the
> AGM/Hansson postulate property-test suite. That suite *is* the library's specification and the
> heart of the M0 exit gate. Everything else is plumbing in service of making those properties hold.

---

## Orientation: belief BASES, not belief SETS

This is the framing decision that governs the entire postulate suite, so it comes first.

Classical AGM (Alchourrón–Gärdenfors–Makinson, 1985) operates over **belief sets**: theories
`K` that are *deductively closed* — `K = Cn(K)`, containing every logical consequence of their
members. These are infinite objects and cannot be stored directly.

Kumiho (and therefore doxastica) operates over **belief bases** in the sense of Hansson (1991,
1993, 1999): **finite sets of explicitly asserted sentences, NOT closed under consequence**. A
base `A` is just the propositions you actually wrote down. This is the right model for a graph
store — every `Belief` node is one explicit assertion; there is no machinery deriving consequences.

Two facts make this not merely pragmatic but *forced*:

1. **The closure postulate is dropped by construction.** AGM's first postulate for both revision
   and contraction is **Closure** (`K*p = Cn(K*p)`, `K÷p = Cn(K÷p)`). A belief base is by
   definition not closed, so doxastica neither satisfies nor tests Closure. Its place is taken by
   Hansson's base-specific postulates (**Relevance**, **Core-Retainment**, **Uniformity**) which
   constrain *which explicit assertions survive* an operation rather than *what the theory entails*.

2. **The Flouris impossibility result.** Flouris, Plexousakis & Antoniou showed that for a wide
   class of non-classical / description logics (including the DL-Lite family), **no AGM-compliant
   contraction operator exists at all** — the closure-based postulates are unsatisfiable in those
   logics, and the underlying problem is uncomputability in non-finitary logics. This is the
   formal validation of the design's hard "no OWL/DL inference in the graph layer" rule
   (`17-kumiho-nvm-recommendations.md §1`). doxastica stays in the finitary, explicit-base world
   precisely because that is the only world where the postulates are both *satisfiable* and
   *mechanically checkable*. Operating over a description logic would void the entire correctness
   story. (Source: Flouris et al., "Generalizing the AGM postulates"; arXiv 2409.09171.)

**Consequence for the test suite:** every postulate below is stated as a property over a *finite
explicit base of `Belief`/`BeliefState` nodes*, asserted as the result of a sequence of
`revise`/`expand`/`contract` calls. We never reason about deductive closure. "Inconsistency" and
"entailment" are not computed by the core — the core has no logic — so the postulates that mention
consistency/entailment (Consistency, the entailment clause of Relevance) are interpreted
structurally over per-`belief_id` chains, as detailed in each entry.

---

## Formal Correctness Obligations (the differentiator)

This is the library's reason to exist. Each obligation is stated **operationally** — as a property
that must hold over a generated sequence of operations — so it maps directly to a Hypothesis
property test. Classical names and symbolic forms are given for citation fidelity; the operational
restatement is what the suite asserts.

### Vocabulary mapping (formal ↔ doxastica)

| Formal notion | doxastica realization |
|---|---|
| Belief base `A` | The set of `Belief` nodes in a scope, each pointing to its `CURRENT_STATE` `BeliefState` |
| Sentence / proposition `p`, `q` | A `(belief_id, value)` pair; `value: Any` is opaque |
| Expansion `A + p` | `expand(scope, belief_id, value, event)` — add/replace one belief, no consistency check |
| Revision `A * p` | `revise(scope, belief_id, value, event)` — install `value` as the current belief for `belief_id`, superseding any prior current state |
| Contraction `A ÷ p` | `contract(scope, belief_id, event)` — mark the belief deprecated (removed from the active base) without deleting history |
| "`p ∈ A`" (membership in the active base) | `belief_id` has a non-deprecated `CURRENT_STATE` in the scope |
| Logical equivalence `p ↔ q` | **Not available** — the core has no logic. Extensionality is interpreted via value-equality on opaque values (see Extensionality entry) |

### In-scope postulates — AGM revision family (K*2–K*6)

> Closure (K*1) is **out of scope by construction** (bases are not closed). The library tests
> K*2–K*6, plus the Hansson base postulates below.

#### K*2 — Success
- **Classical:** `p ∈ K * p`. The new information is always accepted.
- **Operational property:** *After `revise(s, b, v, e)`, querying scope `s` returns a current,
  non-deprecated `BeliefState` for `belief_id b` whose value equals `v`.* Revision never silently
  refuses the input.
- **Test sketch:** for any scope state and any `(b, v)`, `revise` then assert
  `current_value(s, b) == v` and the state is active.
- **Complexity:** LOW. Dependencies: `revise`, `query_scope`.

#### K*3 — Inclusion
- **Classical:** `K * p ⊆ K + p`. Revising by `p` yields no more than expanding by `p` would.
- **Operational property:** *The active base after `revise(s, b, v, e)` is a subset of the active
  base produced by `expand(s, b, v, e)` applied to the same starting state.* In base terms: revision
  introduces no `belief_id` that expansion would not, and may only remove existing ones.
- **Test sketch:** snapshot active `belief_id` set before; after revise, assert the active set ⊆
  (active set before ∪ {b}). Because doxastica is one-belief-per-node and revision touches only `b`,
  this reduces to "revision adds no belief other than `b`."
- **Complexity:** LOW. Dependencies: `revise`, `expand`, `query_scope`.

#### K*4 — Vacuity
- **Classical:** If `¬p ∉ K`, then `K * p = K + p`. If the input does not conflict with the current
  base, revision equals expansion.
- **Operational property:** *If `belief_id b` has no current non-deprecated state in scope `s`
  (nothing to conflict with), then `revise(s, b, v, e)` produces exactly the same active base and
  current-state pointer as `expand(s, b, v, e)`.* In the one-belief-per-node model, "conflict" is
  precisely "a current state already exists for `b`"; absent that, revise and expand coincide.
- **Test sketch:** on a scope where `b` is absent, run revise on a clone and expand on a clone;
  assert identical active bases and identical `CURRENT_STATE` content.
- **Complexity:** LOW. Dependencies: `revise`, `expand`, `query_scope`.
- **Note (soft spot).** The classical antecedent `¬p ∉ K` requires a notion of negation/conflict
  the core does not have. The faithful base-level rendering is *absence of a current belief for the
  same `belief_id`* — the only conflict the core can structurally detect. Flag for requirements:
  confirm this is the intended reading of "consistent input" (it follows directly from
  one-belief-per-`Belief`-node).

#### K*5 — Consistency
- **Classical:** `K * p` is consistent whenever `p` is consistent. Revision never produces an
  inconsistent state from consistent input.
- **Operational property:** *After any `revise(s, b, v, e)` with a well-formed value, the scope's
  active base satisfies the structural-consistency invariant: at most one current, non-deprecated
  `BeliefState` per `belief_id` (`CURRENT_STATE` uniqueness).* The core's only notion of consistency
  is structural single-valuedness per belief; revision must preserve it.
- **Test sketch:** after a generated sequence of operations, assert that for every `belief_id` in
  every scope there is `≤ 1` active `CURRENT_STATE`.
- **Complexity:** MEDIUM (it is really an invariant over whole sequences, not a single op).
  Dependencies: `revise`, `query_scope`, the `CURRENT_STATE`-uniqueness structural invariant.
- **Note.** Because doxastica stores opaque values and does no logic, *propositional* inconsistency
  (`b=true` and `b=false` simultaneously) is impossible by the single-current-state rule — that is
  the whole point of modelling consistency structurally rather than logically. Document this
  explicitly so the postulate is not read as a logical-SAT obligation.

#### K*6 — Extensionality
- **Classical:** If `Cn({p}) = Cn({q})` (logically equivalent inputs), then `K * p = K * q`.
- **Operational property:** *Revising by two values that the core treats as equal produces
  identical results.* Since the core has no logic, "equivalent" collapses to *equal opaque values
  for the same `belief_id`*: `revise(s, b, v, e₁)` and `revise(s, b, v, e₂)` yield the same active
  base (the resulting current value is `v` in both cases; only the recorded `source_event_id`
  differs). Equivalently: revision is a function of `(scope, belief_id, value)` for the active-base
  outcome, deterministic in the value and indifferent to the event id except as recorded provenance.
- **Test sketch:** for any `(b, v)` and two distinct event ids `e₁ ≠ e₂`, assert the active bases
  after each revise are equal (current value `v`, same deprecation structure).
- **Complexity:** LOW. Dependencies: `revise`, `query_scope`.
- **Note.** This is the postulate most distorted by value opacity. The honest statement is
  *substitution of equal values is invariant*; full logical extensionality is impossible without a
  logic and is correctly NVM-layer's concern (NL→triple consistency, per
  `17-kumiho-nvm-recommendations.md §8`: "the consistency of the mapping is a prompt engineering
  concern, not a formal one"). Flag for requirements: state plainly that K*6 is tested as
  value-equality invariance, not logical equivalence.

### In-scope postulates — Hansson belief-base family

These replace Closure and pin down *which explicit assertions survive*. They are the postulates
that are specifically meaningful for bases and that justify the typed-dependency-edge machinery
(`get_impact`). Sources: Hansson, *A Textbook of Belief Dynamics* (1999); Stanford Encyclopedia,
"Logic of Belief Revision."

#### Contraction Success (base form)
- **Classical:** If `p ∉ Cn(∅)` (p is not a tautology) then `p ∉ Cn(A ÷ p)`. After contraction the
  belief is gone.
- **Operational property:** *After `contract(s, b, e)`, `belief_id b` has no current, non-deprecated
  `BeliefState` in scope `s`* — it is excluded from `query_scope(...)` (default `include_deprecated=False`).
- **Test sketch:** contract `b`, assert `b` not in default `query_scope`, and assert `b` *is* in
  `query_scope(include_deprecated=True)` (history preserved — the structural distinction).
- **Complexity:** LOW. Dependencies: `contract`, `query_scope`, deprecated/superseded distinction.

#### Contraction Inclusion (base form)
- **Classical:** `A ÷ p ⊆ A`. Contraction removes; it never adds.
- **Operational property:** *The active base after `contract(s, b, e)` is a subset of the active base
  before.* No new `belief_id` becomes active as a side effect of contraction.
- **Test sketch:** snapshot active set; contract; assert active-set-after ⊆ active-set-before.
- **Complexity:** LOW. Dependencies: `contract`, `query_scope`.

#### Relevance (Hansson) — the postulate that motivates dependency edges
- **Classical:** If `q ∈ A` and `q ∉ A ÷ p`, then there is `A'` with `A ÷ p ⊆ A' ⊆ A` such that
  `p ∉ Cn(A')` but `p ∈ Cn(A' ∪ {q})`. *Nothing is discarded unless its removal genuinely
  contributes to removing `p`.*
- **Operational property:** *Every belief removed by a contraction cascade is removed because it
  depended (transitively, via `DEPENDS_ON`/`DERIVED_FROM` edges, within `depth`) on the contracted
  belief.* No belief is deprecated by `contract`/`get_impact` unless there is a dependency path
  linking it to the contracted target; conversely, beliefs with no such path are untouched.
- **Test sketch:** build a scope with a dependency DAG; contract a node; assert that the set
  `get_impact` reports as affected is exactly the set reachable along `DEPENDS_ON`/`DERIVED_FROM`
  within `depth`, and that no unreachable belief is marked.
- **Complexity:** HIGH (it is the property that gives `get_impact`/the contraction cascade its
  meaning; the trickiest to generate good cases for). Dependencies: `contract`, `add_edge`,
  `get_impact`, the typed edge model.
- **Note.** doxastica's `value: Any` opacity means the core cannot compute "`p ∈ Cn(A' ∪ {q})`"
  logically. The base-faithful rendering is *graph reachability over explicit dependency edges* —
  which is exactly the operational form Kumiho uses and the paper proves adequate for explicit
  bases. The `get_impact` *mechanism* satisfies Relevance; the *policy* (what NVM does with the
  affected set) is out of scope.

#### Core-Retainment (Hansson) — the kernel-contraction counterpart of Relevance
- **Classical:** If `q ∈ A` and `q ∉ A ÷ p`, then there is `A' ⊆ A` such that `p ∉ Cn(A')` but
  `p ∈ Cn(A' ∪ {q})`. (Weaker than Relevance; the characteristic postulate of *kernel* contraction,
  whereas Relevance characterizes *partial-meet* contraction.)
- **Operational property:** *A belief is retained through contraction unless it actually participated
  in supporting the contracted belief.* Operationally for doxastica this is the contrapositive
  guard on the cascade: a belief with **no** dependency edge into the contracted target is
  **guaranteed retained**. (Where Relevance asserts "removals are justified," Core-Retainment is the
  retention guarantee — they coincide structurally here because the dependency graph is explicit.)
- **Test sketch:** contract `b`; assert every belief with zero `DEPENDS_ON`/`DERIVED_FROM` path to
  `b` remains active and unchanged.
- **Complexity:** MEDIUM. Dependencies: same as Relevance.
- **Note.** Test BOTH Relevance and Core-Retainment even though they coincide in the explicit-base
  case — they are distinct citations (partial-meet vs. kernel) and asserting both documents that the
  cascade is *minimal in both directions* (removes only the justified, retains all the unjustified).

#### Uniformity (Hansson) — companion to Relevance/Core-Retainment
- **Classical:** If for all `A' ⊆ A`, (`p ∈ Cn(A')` iff `q ∈ Cn(A')`), then `A ÷ p = A ÷ q`.
  Equivalent targets are contracted identically.
- **Operational property:** *Contracting the same `belief_id` always produces the same active-base
  effect regardless of the supplied `source_event_id`* (the event id is recorded provenance, not an
  input to the removal decision). Mirrors Extensionality on the contraction side.
- **Test sketch:** two contractions of `b` with distinct event ids on cloned states produce identical
  active bases.
- **Complexity:** LOW. Dependencies: `contract`, `query_scope`.

### Structural invariants (the other half of the test suite)

These are not AGM postulates but are co-equal exit-gate obligations — they guarantee the data
structure the postulates assume.

| Invariant | Operational property | Complexity | Deps |
|---|---|---|---|
| `CURRENT_STATE` uniqueness | For every `belief_id` in every scope, at most one `BeliefState` is the current, non-deprecated head | MEDIUM | revise/expand/contract |
| Chain immutability (append-only) | No operation deletes or mutates an existing `BeliefState` node or `HAS_REVISION` edge; revision only appends and re-points `CURRENT_STATE` | MEDIUM | all write ops |
| `get_scope_at ≡ replay` | `get_scope_at(s, e)` returns exactly the active base that results from replaying all operations with `source_event_id ≤ e` in event-id order | HIGH | `get_scope_at`, `get_revision_chain`, UUID7 ordering |
| World-scope no-contraction | `contract()` on the privileged world scope raises an error (never deprecates) | LOW | `contract`, world scope |

### EXCLUDED postulate — Recovery (justified)

- **Classical:** `K ⊆ (K ÷ p) + p`. Contracting `p` and then re-expanding by `p` restores the
  *entire* original belief set.
- **Why it is in classical AGM:** for deductively-closed belief *sets*, Recovery holds and is one
  of the six basic contraction postulates.
- **Why doxastica deliberately EXCLUDES it — three converging reasons:**
  1. **It is false for belief bases anyway.** This is a *theorem*, not a design compromise.
     Stanford Encyclopedia: "Recovery does not hold for partial meet contraction of belief bases."
     Hansson's standard counterexample: base `A = {p, q}` (two *independent* explicit assertions);
     contract `p` to get `{q}`... but consider `A = {p, p∧q}` style cases where a merely-derived
     belief loses its support. When you remove a foundational assertion, dependent explicit
     assertions are gone, and re-asserting the foundation does **not** automatically resurrect them.
     A base is not closed, so there is no closure to "recover." Recovery is precisely the postulate
     that *requires* closure; dropping closure (which bases do by construction) drops Recovery with it.
  2. **It is incompatible with immutable, observable history.** Recovery presupposes that
     "contract then re-expand" returns you to a state indistinguishable from the original — i.e.
     that the intermediate revision can be erased. doxastica's append-only discipline makes every
     state permanently observable: re-expanding `b` after contracting it creates a *new*
     `BeliefState` with a *new* `source_event_id`, leaving the contraction visible in the chain. An
     agent that re-learns something does not return to its prior epistemic state — it has a new
     state with new provenance (`17-kumiho-nvm-recommendations.md §5`). Recovery would require
     pretending history did not happen, which is exactly the no-retcon principle the world scope
     enforces.
  3. **Superseded-chain semantics is the strictly better replacement.** What Recovery tries to buy
     (don't lose information on contraction) doxastica provides *more honestly*: contraction
     **deprecates** rather than deletes, the full `HAS_REVISION` chain is retained, and
     `query_scope(include_deprecated=True)` / `get_revision_chain` / `get_scope_at` can recover any
     past state *as history* — without the fiction that the contraction never occurred. This is the
     **superseded ≠ deprecated** distinction made structural: *superseded* = a newer state exists in
     the chain (still retrievable); *deprecated* = removed from the active base by contraction (still
     retrievable with the flag). Both preserve information; neither pretends to undo.
- **Test-suite consequence:** there is **no Recovery property test.** Instead the suite asserts the
  *replacement guarantees* — chain immutability, `include_deprecated` retrievability, and
  `get_scope_at ≡ replay` — which together provide the "no information lost" value Recovery aimed at,
  under an immutable-history model where Recovery is both false and undesirable.

---

## API Surface — categorized against the M0 exit gate

The Protocol is reproduced verbatim from `05-nvm-memory-core.md §3` and treated as authoritative.
Each operation is categorized **Table Stakes** (required to pass the M0 exit gate), **Differentiator**
(the publishable / NVM-distinguishing capabilities), or supporting.

### Table Stakes — required for the M0 exit gate

The exit gate (per `15-nvm-milestones.md`) is: AGM postulate suite green + structural invariants
green + irony join demonstrated. Every operation the postulate/invariant tests exercise is table
stakes.

| Operation | Why exit-gate-required | Exit-gate criterion served | Complexity |
|---|---|---|---|
| `get_or_create_scope(scope_id)` | All belief operations target a scope; the privileged world scope is created here | All (precondition) | LOW |
| `revise(scope, belief_id, value, event)` | The K*2–K*6 revision postulates are *about* this operation | AGM suite (Success, Inclusion, Vacuity, Consistency, Extensionality) | MEDIUM |
| `expand(scope, belief_id, value, event)` | Reference operation for Inclusion (K*3) and Vacuity (K*4) — revision compared against it | AGM suite | LOW |
| `contract(scope, belief_id, event)` | The Hansson contraction postulates + deprecated distinction; world-scope error path | AGM suite (Success/Inclusion/Relevance/Core-Retainment/Uniformity), world-scope invariant | MEDIUM |
| `add_edge(from, to, edge_type)` (SUPERSEDES / DEPENDS_ON / DERIVED_FROM) | Dependency edges are the substrate Relevance/Core-Retainment and `get_impact` operate over | AGM suite (Relevance, Core-Retainment) | LOW |
| `query_scope(scope, query, include_deprecated)` | The observation surface every postulate test reads through; `include_deprecated` *is* the deprecated/superseded distinction | AGM + structural suites | MEDIUM (see soft spot) |
| `get_revision_chain(belief_id)` | Observes chain immutability and append-only history | Structural invariants | LOW |
| `get_scope_at(scope, as_of_event_id)` | The `get_scope_at ≡ replay` invariant; also enables the irony join over historical states | Structural invariants **and** irony-join demo | HIGH |
| `get_impact(belief_state_id, depth)` | The contraction-cascade mechanism that Relevance/Core-Retainment characterize | AGM suite (Relevance, Core-Retainment) | HIGH |

> **All nine Protocol operations are table stakes.** There is no Protocol operation that the M0
> exit gate does not exercise. The categorization that matters for the *roadmap* is therefore
> *dependency ordering* (below) and *which give the library its differentiated value* (next).

### Differentiators (what makes this publishable / what NVM needs that Kumiho lacks)

These are capabilities, not separate operations — they are the reason the library is worth
extracting and citing.

| Capability | Value proposition | Realized by | Complexity |
|---|---|---|---|
| **Mechanically-verified AGM/Hansson compliance** | The whole point: a reference implementation whose correctness is a *formal* property, proven by a Hypothesis property suite over operation sequences. Citable. | The entire postulate suite above | HIGH |
| **The irony join** | Actor-scope vs. world-scope divergence ("everything scope X believes that the world scope contradicts") computed as a *single query* over `belief_id`, not remembered. Named explicitly in the exit gate. | `query_scope` × two scopes joined on `belief_id`; multi-scope extension | MEDIUM |
| **Structural time-travel (`get_scope_at`)** | "What did this scope hold as of event E," answered purely from immutable, event-id-ordered states — no snapshots, no undo log. | `get_scope_at` + UUID7 ordering + append-only chains | HIGH |
| **Multi-scope extension to Kumiho** | Kumiho is single-agent; doxastica's `Scope` abstraction makes per-holder belief states independent peers (including the privileged world scope). Enables the irony join. | `get_or_create_scope` + world-scope contraction guard | MEDIUM |
| **Superseded-chain semantics replacing Recovery** | A *better* answer to "don't lose information on contraction" than classical AGM offers — honest, observable history instead of the recovery fiction. | deprecated/superseded distinction + chain immutability | MEDIUM |

### Anti-Features (deliberately NOT built — with reasons)

Documented to prevent re-adding. Reasons drawn from `PROJECT.md` Out-of-Scope and the design docs.

| Anti-feature | Surface appeal | Why excluded / problematic | What instead |
|---|---|---|---|
| **AGM Recovery postulate** | "It's one of the six AGM postulates — surely we want all six" | False for belief bases (theorem); incompatible with immutable history; would require erasing observable revisions | Superseded-chain semantics + `include_deprecated` retrieval + `get_scope_at` |
| **Any narrative / game / LLM concept** (actors, turns, scenes, plausibility, diegetic time, GM assembly) | "The consumer is a game engine" | Each appearance is the leak the Protocol seam exists to prevent; meaning lives in the NVM layer above | Generic `Scope` + opaque `value: Any` + opaque event ids; NVM layers meaning |
| **Storage abstraction over the database** | "Don't lock in to one DB" | Non-goal by decision; the DI seam is NVM↔core, not core↔DB. Speculative generality bloats clean libraries | Pin to LadybugDB/Cypher; flexible *connection* model (injected vs. self-managed), not a storage interface |
| **Epistemic edge labels** (`WITNESSED_BY`, `TOLD_BY`, `INFERRED_FROM`) | "Provenance is useful" | These are NVM *specialisations* of generic edges; epistemic meaning is narrative semantics | Generic `SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM`; NVM specialises `DERIVED_FROM` |
| **Stance / entrenchment policy** (confidence arithmetic, entrenchment ordering, contradiction resolution) | "AGM needs entrenchment to pick what to contract" | Type-dependent entrenchment and stance comparison are NVM-layer *policy* (R21); arithmetic over stance exists nowhere | Core stores opaque values and traverses dependency edges; NVM decides what to contract |
| **Deductive closure / OWL / DL inference in the graph** | "Richer reasoning" | Flouris impossibility: no AGM-compliant operator exists for DLs; voids the entire correctness story | Stay finitary: explicit belief bases only; inference is NVM-layer prompt engineering |
| **The Chronicle / prospective indexing** | "Kumiho's biggest benchmark win" | RAG/document concern decided in-thread as an NVM-side add-on, outside the core | NVM owns it above the seam; shared async infra is implementation reuse, not a core boundary |
| **LLM semantic merge of revisions** | "Preserve unchanged sub-beliefs automatically" | Non-deterministic; breaks formal guarantees. Paper explicitly rejects it | One-belief-per-`Belief`-node (granularity strategy ii) — partial updates are trivial and deterministic |
| **Owning the database / entity nodes / topology / planner cache** | "Core could manage everything" | Forces game concepts into the API, destroying the boundary; the core is a *tenant* (R19) | Label-family tenancy; injected connection; the core subgraph is closed (no outbound graph refs) |
| **K*7 / K*8 supplementary (iterated-revision) postulates** | "Complete the AGM picture" | The paper flags these as open questions; iterated-revision entrenchment is NVM policy | Out of scope; not in the exit gate. Document as deliberate. |

---

## Feature Dependencies

```
get_or_create_scope (incl. world scope)
    └──required by──> revise, expand, contract, query_scope, get_scope_at

expand ──reference-operation-for──> revise   (Inclusion K*3, Vacuity K*4 compare against expand)

revise / expand / contract
    └──maintain──> CURRENT_STATE uniqueness invariant
    └──append-only──> chain immutability invariant
                          └──enables──> get_revision_chain
                          └──enables──> get_scope_at (≡ replay)
                                            └──enables──> irony join over historical states

add_edge (DEPENDS_ON / DERIVED_FROM)
    └──substrate-for──> get_impact (contraction cascade)
                            └──characterized-by──> Relevance + Core-Retainment postulates
add_edge (SUPERSEDES)
    └──realizes──> superseded-chain semantics (Recovery replacement)

contract + deprecated/superseded distinction
    └──exposed-via──> query_scope(include_deprecated)
    └──guarded-in──> world scope (contract() is an error)

query_scope × world scope × actor scope (join on belief_id)
    └──produces──> THE IRONY JOIN  (exit-gate demo)
```

### Dependency notes (for phase ordering)

- **Scopes before everything.** `get_or_create_scope` and the world-scope distinction are the
  precondition for all belief ops and for the irony join. Build first.
- **Append-only chains before history queries.** `get_revision_chain`, `get_scope_at`, and the
  superseded semantics all *depend on* the `Belief`/`BeliefState` split with immutable
  `HAS_REVISION` + single mutable `CURRENT_STATE`. The chain model is the keystone — build it before
  any retrieval/history surface.
- **Edges before cascade.** `add_edge` (dependency edges) must exist before `get_impact` can mean
  anything, and `get_impact` must exist before Relevance/Core-Retainment can be tested. This is the
  one place where a postulate (Relevance) has a hard prerequisite on two operations.
- **`get_scope_at ≡ replay` depends on UUID7 ordering.** The time-travel invariant assumes event ids
  impose a total order; confirm UUID7 monotonicity assumptions early (research flag below).
- **Irony join depends on multi-scope + `query_scope`.** It is the last exit-gate item to come
  together because it composes two scopes and a join — but it adds *no new operation*, only a query
  pattern. Cheap once the pieces exist.

---

## MVP Definition (= the M0 exit gate)

For this library, "MVP" and "M0 exit gate" are the same thing. There is no v1.x of mechanisms —
the Protocol is fixed; what evolves is fidelity and polish.

### Launch With (M0 exit gate — all required)

- [ ] All nine Protocol operations implemented against LadybugDB — *every one is exit-gate-load-bearing*
- [ ] `Belief`/`BeliefState` split: immutable append-only `HAS_REVISION` chains, single mutable `CURRENT_STATE`, one belief per `Belief` node
- [ ] Scopes including the privileged world scope (`contract()` raises there)
- [ ] Generic typed edges `SUPERSEDES` / `DEPENDS_ON` / `DERIVED_FROM` via `add_edge`
- [ ] AGM revision property suite green: **Success, Inclusion, Vacuity, Consistency, Extensionality** (K*2–K*6) — Hypothesis over operation sequences
- [ ] Hansson base property suite green: **Contraction Success, Inclusion, Relevance, Core-Retainment, Uniformity**
- [ ] Structural-invariant suite green: `CURRENT_STATE` uniqueness, chain immutability, `get_scope_at ≡ replay`, world-scope no-contraction
- [ ] **NO** Recovery test (its absence is deliberate and documented) — replacement guarantees tested instead
- [ ] The **irony join** demonstrated on synthetic data: actor-scope vs. world-scope divergence as one query
- [ ] Flexible connection model (injected + self-managed), label-family tenancy, `ladybugdb` + `pydantic` only, zero NVM imports
- [ ] Publishable polish: MIT, docs site, CI/release, PyPI-ready; README leads with "reference implementation of Kumiho (arXiv 2603.17244), multi-scope extension, no recovery"

### Add After Validation (not M0 — listed only to bound scope)

- [ ] Nothing mechanism-wise. Post-M0 work is NVM-layer (consumes the Protocol) or fidelity
      refinements (e.g. tightening `query_scope` semantics — see soft spots) and is explicitly out
      of this library's M0.

### Future / Out of scope permanently

- [ ] K*7/K*8 iterated-revision postulates — NVM-policy territory, flagged open in the paper
- [ ] Anything in the Anti-Features table

---

## Feature Prioritization Matrix

"User value" = value to the M0 exit gate / library correctness. "Cost" = implementation+test effort.

| Mechanism | Value | Cost | Priority | Rationale |
|---|---|---|---|---|
| `Belief`/`BeliefState` split + chains | HIGH | MEDIUM | P1 | Keystone; everything depends on it |
| `revise` / `expand` / `contract` | HIGH | MEDIUM | P1 | The operations the postulates are about |
| Scopes + world scope guard | HIGH | LOW | P1 | Precondition + enables irony join |
| `add_edge` (typed edges) | HIGH | LOW | P1 | Substrate for Relevance/Core-Retainment |
| AGM revision postulate suite (K*2–6) | HIGH | HIGH | P1 | The differentiator; exit gate |
| Hansson base suite (Relevance etc.) | HIGH | HIGH | P1 | The base-specific correctness story |
| Structural invariants suite | HIGH | MEDIUM | P1 | Co-equal exit-gate obligation |
| `query_scope` + `include_deprecated` | HIGH | MEDIUM | P1 | Observation surface for all tests; deprecated distinction (semantics soft spot) |
| `get_revision_chain` | MEDIUM | LOW | P1 | Observes chain immutability |
| `get_impact` (cascade) | HIGH | HIGH | P1 | Realizes Relevance/Core-Retainment; depth/truncation undesigned |
| `get_scope_at` (time-travel) | HIGH | HIGH | P1 | Differentiator + `≡ replay` invariant |
| Irony-join demo | HIGH | LOW | P1 | Named exit-gate item; no new op, just a query |
| Flexible connection / tenancy | HIGH | MEDIUM | P1 | Required for both standalone + NVM use |
| Publishable polish (docs/CI/PyPI) | MEDIUM | MEDIUM | P1 | Scope is "publishable from day one" per Key Decisions |

> Everything is P1 because M0 *is* the MVP and the exit gate enumerates all of it. The roadmap's job
> is **ordering by dependency**, not triage — see the dependency notes.

---

## Reference Analysis: doxastica vs. Kumiho (the paper)

| Mechanism | Kumiho (paper) | doxastica | Note |
|---|---|---|---|
| Belief base (not set) | Yes — Hansson bases over ground triples | Yes — opaque values, one belief per node | Paper proves K*2–6 + Relevance/Core-Retainment hold over explicit bases |
| Item/Revision split | `Item` + append-only `Revision` chain, mutable tag | `Belief` + `BeliefState` + `CURRENT_STATE` | Isomorphic |
| Recovery | Rejected, remaining postulates proven to hold | Excluded; superseded-chain replacement | Same stance; doxastica makes it a structural invariant |
| Typed dependency edges | Yes — operationalize Relevance/Core-Retainment | Yes — `DEPENDS_ON`/`DERIVED_FROM` + `get_impact` | Direct mapping |
| Deprecated vs superseded | §8.6 distinction | `include_deprecated` flag + `SUPERSEDES` edge | Direct mapping |
| Single agent | Yes | **Multi-scope extension** | doxastica's deliberate addition; enables irony join |
| Time-travel | Implied by chains | First-class `get_scope_at` | doxastica surfaces it as a Protocol op |
| Prospective indexing / Chronicle | Yes (the benchmark win) | **Excluded** (NVM add-on) | Out of core boundary |

---

## Sources

- [Logic of Belief Revision — Stanford Encyclopedia of Philosophy](https://plato.stanford.edu/entries/logic-belief-revision/) — authoritative formulations of AGM K*1–K*6 revision and contraction postulates (incl. Recovery), Levi/Harper identities, Hansson base postulates (Relevance, Core-Retainment, Uniformity), and the statement that Recovery fails for partial-meet contraction of belief bases. (HIGH)
- [Kernel Contraction and Base Dependence (IJCAI 2015)](https://www.ijcai.org/Proceedings/15/Papers/442.pdf) — kernel contraction characterized by Success, Inclusion, Core-Retainment, Uniformity (Hansson 1994). (HIGH)
- [Pseudo-Contractions in Belief Revision — Santos (USP thesis)](https://www.teses.usp.br/teses/disponiveis/45/45134/tde-08062016-105125/publico/santos16.pdf) — operational glosses of Success, Inclusion, Vacuity, Relevance, Core-Retainment for bases. (MEDIUM)
- [Flouris et al., Generalizing the AGM postulates / Effective AGM Belief Contraction (arXiv 2409.09171)](https://arxiv.org/html/2409.09171) and [Updating DLs Using the AGM Theory (CEUR Vol-147)](https://ceur-ws.org/Vol-147/26-Flouris.pdf) — the impossibility result: no AGM-compliant contraction operator for a wide class of (description) logics; uncomputability in non-finitary logics. Grounds the "no DL inference" rule. (HIGH)
- `narrative-vm/_design/v2/05-nvm-memory-core.md §3, §6, §8` — the authoritative Protocol surface, world scope, and testing obligations. (HIGH — design authority)
- `narrative-vm/_design/v2/17-kumiho-nvm-recommendations.md §1, §3, §5, §8` — belief-base framing, Item/Revision split, Recovery rejection, NL→triple as a pre-formal concern. (HIGH — design authority)
- `narrative-vm/_design/v2/15-nvm-milestones.md` (M0) — the exit-gate definition of done. (HIGH — design authority)
- Hansson, *A Textbook of Belief Dynamics* (1999) — primary source for the base postulates (cited via the secondary sources above; not directly fetched). (Referenced)

---
*Feature research for: graph-native AGM belief-revision memory core (doxastica / Kumiho)*
*Researched: 2026-06-13*
