# Requirements: doxastica — v0.2.0 Stance (R21)

**Defined:** 2026-07-04
**Milestone:** v0.2.0 — Stance (ordinal epistemic enum)
**Core Value:** A correct, append-only belief-revision core behind a clean `BeliefStore`
Protocol whose correctness is *provable* — with zero narrative semantics leaking in.

> **Scoping note.** This milestone closes the ratified NVM **R21** gap (the v0.1.0 M0 core
> shipped without `stance`). It adds the *storage + canonical ordering* of stance to the core
> and keeps all stance *policy* (assignment, propagation, contradiction/torn-mind, trust,
> dice/uptake) in the NVM consumer — the same core/consumer split R21 assigns. The v0.1.0
> requirements listed "Stance / entrenchment policy" wholesale as out-of-scope; v0.2.0 splits
> that: the field, the ordering, and comparison come *in*; every policy use stays *out*.
> These requirements refine `.planning/features/FEAT-001-stance-r21.md` (its bundled
> `STANCE-03` write/round-trip/contract MUST is split here into `STANCE-03..05` for
> per-phase granularity; its `STANCE-N1/N2` MUST-NOTs are carried into Out of Scope).

## v1 Requirements

### Stance Data Model

Decision-grade edits to the frozen value layer — reversing them is a rewrite.

- [x] **STANCE-01**: A canonical `Stance` enum defines the ordinal epistemic taxonomy with
      members `doubted < suspected < believed < certain` and a **total order**, implemented as a
      **plain `Enum` + `functools.total_ordering`** with an explicit integer rank (`__lt__`
      compares `.value`, returning `NotImplemented` for non-`Stance` operands). `IntEnum` is
      **rejected**: it inherits `int`'s full numeric protocol, so `+`/`*`/int-comparison would
      be reachable — directly contradicting STANCE-06. `StrEnum` is rejected too (lexical order
      is wrong; `+` concatenates). The `.value` rank is used only inside `__lt__`, never exposed
      as an operable number. First *ordered* enum in the codebase; `Status`/`EdgeType` stay
      unordered `StrEnum`s.

- [x] **STANCE-02**: `BeliefState` (the frozen, `extra="forbid"` pydantic v2 model) gains a
      `stance: Stance` field — six fields → seven. The closed-taxonomy docstring is updated to
      keep the field roster honest.

### Write & Persistence

- [x] **STANCE-03**: The write surface (`revise` / `expand`) accepts an **optional** `stance`
      parameter **defaulting to `certain`** ("core default, NVM overrides"). The value
      round-trips **byte-stable on both backends** (in-memory + ladybug), using the same
      encode/hydrate discipline as `value`. Serialization leans on the member `.name` (a bare
      legible token like `"certain"`, matching the `Status`/`EdgeType` house style and
      base64/STRING-column safe), hydrated back to the `Stance` member — exact wire form
      confirmed at planning. Existing callers that omit `stance` are unaffected.

- [x] **STANCE-04**: `contract` preserves the prior stance **verbatim** on the retracted tail
      it appends (mirrors the existing verbatim-value copy; Pitfall-2 sibling).

- [x] **STANCE-05**: `get_scope_at` reconstructs stance unchanged — time-travel round-trips the
      field along with the rest of the state.

### Comparison Contract

- [x] **STANCE-06**: Ordinal **comparison** (`<`, `>`, `==`, ordering) is the only operation
      the `Stance` type supports. Arithmetic is a **type-level guarantee**, not a lint:
      `Stance.certain + Stance.doubted`, `Stance.certain * 2`, and `Stance.believed < 5` each
      raise `TypeError` (the plain-`Enum` base defines no `__add__`/`__mul__`, and `__lt__`
      returns `NotImplemented` for non-`Stance` operands). No core code path performs arithmetic
      on stance.

### Formal Correctness

- [x] **STANCE-07**: Hypothesis property suite (both backends, **oracle-independent** — the
      shadow oracle never calls the SUT), in the style of `tests/test_invariants.py`, that
      actually *carries* stance rather than staying vacuously green:

    - **(a) Oracle tracks stance per entry.** The shadow/fold oracle model records `stance`
      alongside `value` for every tracked belief-in-scope entry, so the oracle can diverge from
      the SUT on stance.

    - **(b) Base comparison includes stance.** The harness's state-equality key widens from
      `{belief_id: value}` to `{belief_id: (value, stance)}` everywhere the SUT is compared to
      the oracle. This is the load-bearing change: **Extensionality (K*6) `revise ≡ expand`
      parity now compares stance too**, so two ops that agree on value but differ on stance
      correctly *fail* parity instead of passing vacuously.

    - **(c) Round-trip / preservation / reconstruction properties.** `stance` survives
      `revise → query_scope` unchanged; `contract` preserves the prior stance **verbatim** on
      the retracted tail (STANCE-04); `get_scope_at` reconstructs stance (STANCE-05).

    - **(d) Type-level ordering guarantees.** The enum order is **total and antisymmetric**, and
      **no arithmetic operator is reachable** on the type (assert the negative — `+`/`*`/int-`<`
      raise `TypeError`, STANCE-06).

      The M0 conformance suite stays green on both backends (still SKIP-not-fail when the ladybug
      driver is absent).

### Documentation

- [x] **DOCS-01**: The Cluedo detective tutorial demonstrates stance — a **within-scope
      epistemic gradient** (a first guess at `suspected`, upgraded to `believed`, a forced
      conclusion at `certain`) plus one **reader-side ordinal comparison** driving a decision
      (e.g. a shown card outranks a mere suspicion), keeping stance *policy* the reader's, per
      R21. The tutorial reconciles stance (within-scope degree) against the certain/provisional
      **scope** split (cross-scope) as composing extensions. `revise` / `expand` signature
      references are refreshed across the docs site; `mkdocs build --strict` stays green.

## v2 Requirements

None (mechanism-wise). Stance *policy* (assignment, weakest-link propagation, contradiction
resolution, trust/dice machinery) is NVM-layer work that consumes this field and ordering — out
of this library's scope, permanently (see Out of Scope).

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Stance **assignment** logic (observed→certain, told-cap, trust modulation, inferred≤weakest premise) | NVM policy (R21); the core stores and compares only (STANCE-N1) |
| Weakest-link **propagation** + step-down | NVM policy (R21) |
| **Contradiction / torn-mind** policy (higher displaces; ties → both capped at `suspected`, `CONTRADICTS`-linked) | NVM policy (R21); a `certain`/`believed`/… name in a *policy* role is the leak this boundary prevents |
| Dice→uptake gate, persuasion inertia, verb routing, host-system DC adapters | NVM policy (R21) |
| **Numeric `confidence` field**, ever | Stance replaces it; numeric confidence invites fake-precision arithmetic over an uncalibrated quantity (STANCE-N2) |
| **Edge stance** — a stance property payload on `add_edge` | Core edges are generic (`SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM`); epistemic edges are NVM specialisations that don't exist in core. R21's "edges carry stance" is reconciled as NVM edge metadata, not silently dropped. Adding an `add_edge` payload is a bigger port change deferred to NVM |
| **`BeliefFilter` stance predicate** (filter `query_scope` by stance) | Not required by R21 (comparison is a primitive, not a query predicate); would widen the injection-hardened closed filter for no current need |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STANCE-01 | Phase 9 | Complete |
| STANCE-02 | Phase 9 | Complete |
| STANCE-03 | Phase 9 | Complete |
| STANCE-04 | Phase 9 | Complete |
| STANCE-05 | Phase 9 | Complete |
| STANCE-06 | Phase 9 | Complete |
| STANCE-07 | Phase 10 | Complete |
| DOCS-01 | Phase 10 | Complete |
