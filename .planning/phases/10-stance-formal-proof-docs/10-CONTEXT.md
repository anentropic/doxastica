# Phase 10: Stance Formal Proof & Docs - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Make stance **mechanically proven, not vacuously green**, and tell the stance story in
the docs. Three test tracks plus a docs track:

1. **Oracle widening (SC1)** — the shadow/fold oracle records `stance` per tracked
   belief-in-scope entry, and the harness state-equality key widens
   `{belief_id: value}` → `{belief_id: (value, stance)}` everywhere the SUT is compared
   to the oracle, so a pair of ops agreeing on `value` but differing on `stance` **fails**
   K*6 (`revise ≡ expand`) parity instead of passing vacuously.
2. **Order/no-arithmetic proof (SC2)** — the total order is proven **total AND
   antisymmetric**, and **no arithmetic operator is reachable** (the negative is asserted).
3. **Round-trip / preservation / reconstruction (SC3)** — stance survives
   `revise → query_scope`; `contract` preserves prior stance verbatim (STANCE-04);
   `get_scope_at` reconstructs it (STANCE-05) — quantified over stance, both backends.
4. **Docs (SC5)** — the Cluedo tutorial demonstrates a within-scope epistemic gradient
   plus a reader-side ordinal comparison driving a decision, reconciles stance
   (within-scope degree) against the certain/provisional **scope** split (cross-scope);
   `revise`/`expand` signature refs refreshed site-wide; `mkdocs build --strict` green.

This phase is **tests + docs**, with **one deliberate behavior-neutral `src/` change**:
exporting `Stance` from the package root (see D-13). No `src/` *behavior* changes — the
`Stance` type, serialization, write-spine threading, and `contract` verbatim-copy all landed
in Phase 9 and are correct as-is.

</domain>

<decisions>
## Implementation Decisions

### The core framing: existing stance tests are scaffolds, not proofs
- **D-01:** Phase 10 is **NOT** "SC1 + docs with SC2/SC3 as trivial `@given` lifts."
  The existing `tests/test_stance.py` (SC2 territory) and `tests/test_stance_persistence.py`
  (SC3 territory) are honest **example-based** tests, not property tests. They assert
  *instances* where the phase requires *laws*. None of SC2/SC3 is "done" — what exists is
  exactly the scaffold you'd point at to *fake* done. The quantification IS the substance.
  User guidance (verbatim): make **"good" property tests, not weak rubber-stamps.**

### SC1 — oracle widening (the load-bearing, genuinely-new work)
- **D-02:** Widen the oracle `Entry` in `_SpineMachine` (`tests/test_invariants.py`) and the
  `_shadow_base` state-equality key to carry stance. The oracle's stance semantics MUST
  match the SUT exactly — in particular `contract` copies prior stance **verbatim**
  (STANCE-04), so the oracle must copy-on-contract identically or the K*6 invariant
  false-positives.
- **D-03 (vacuity guard — MANDATORY, not optional):** Widening the key does nothing unless
  the Hypothesis strategy **actually generates a `revise` and an `expand` of the same
  belief with different stances**. If it never does, the widened key never fires and SC1
  passes vacuously — the exact failure this phase exists to kill. Add an explicit
  **generator-coverage guard** (`hypothesis.event()` tag, or a targeted assertion / stats
  check) proving the differing-stance discriminating case is reached. "Non-vacuous" must be
  *proven*, not asserted.

### SC2 — order laws: enumerate, don't just sample
- **D-04:** **Antisymmetry is literally unasserted today.** `test_stance_total_order` checks
  one fixed chain and a couple of reflected operators; it never checks `a < b ⟹ not (b < a)`,
  transitivity, or totality. This is the weakest current spot and is genuinely new work.
- **D-05:** The domain is **4 elements**, so **exhaustively enumerate** the order axioms
  (`itertools.product(Stance, repeat=2)` = 16 pairs for antisymmetry/totality;
  `repeat=3` = 64 triples for transitivity) rather than Hypothesis-*sampling* a tiny space.
  A complete enumeration is a proof; a sample is an anecdote. Assert the **axioms**
  (irreflexivity, antisymmetry, transitivity, totality = exactly-one-of `<`/`==`/`>`), not a
  hardcoded chain. This is **stronger** than the `@given` the roadmap literally names — and
  that is the intended reading, not a deviation. Discipline: **enumerate tiny domains
  (order laws), use Hypothesis where the space is large (op-sequences in SC1/SC3).**
- **D-06:** For no-arithmetic: the current guard samples `+`/`*`/cross-type `<`/`>` on fixed
  operands. Strengthen toward a closure claim (parametrize/enumerate operators × member
  pairs) so "no arithmetic operator is reachable" is asserted broadly, not by three witnesses.

### SC3 — persistence: quantify over stance
- **D-07:** `tests/test_stance_persistence.py` is a **solid backbone** (backend-parametrized,
  `is`-identity so a value-vs-name hydrate regression raises loud, driven through
  `MemoryCore` not the bare port) — keep that shape. But each test **pins one stance**
  (`suspected` here, `believed` there); a `doubted`-only hydrate bug would sail through.
- **D-08:** Quantify the stance — `@given(stance=st.sampled_from(Stance))` (and/or a sequence
  of revises with varying stances) — so round-trip / contract-verbatim / `get_scope_at`
  reconstruction hold for **all four members** and under op-sequences, not one witness each.
  The quantification-over-stance IS the property; it's a small diff but it's the difference
  between a proof and an anecdote.

### SC5 — docs: hold stance and scope apart
- **D-09:** The genuine explanatory hazard is **conflating stance with scope**. Stance is a
  *within-scope* epistemic gradient (`doubted < suspected < believed < certain`); the
  certain/provisional **scope** split is a *cross-scope* distinction. A reader could read
  "certain stance" as "certain scope." The tutorial must hold these apart cleanly and
  reconcile them explicitly (SC5 requires this reconciliation).
- **D-10:** Cluedo tutorial (`docs/src/tutorials/cluedo-detective.md`, currently zero stance
  mentions) demonstrates a gradient `suspected → believed → certain` plus **one reader-side
  ordinal comparison driving a decision** (e.g. "act only if stance ≥ believed"). Ordinal
  comparison is a **reader-side** concern — the core stores/returns stance and never
  interprets it.
- **D-11:** Refresh `revise`/`expand` signature references site-wide (they now carry
  `stance: Stance = Stance.certain`). Docs must contain **no GSD/decision-ID/phase-number
  leakage** — real paper/RFC citations only. Gate on `mkdocs build --strict`.

### Scope-fence amendment — export `Stance` (user decision, post-research)
- **D-13:** Phase 10 makes **one deliberate, behavior-neutral `src/` change**: export `Stance`
  from `src/doxastica/__init__.py` (add to the `doxastica.models` import block and to
  `__all__`, alongside `Status`). Rationale: `Stance` is already a **public parameter type**
  on `revise`/`expand`, yet — unlike its sibling `Status` — it is not importable from the
  package root, so consumers (and the SC5 tutorial) would need `from doxastica.models import
  Stance`, an internal-path leak that violates the docs "no internal details" rule
  ([[no-gsd-process-refs-in-docs]] sibling concern). This narrowly widens the otherwise
  "tests + docs only" fence; it is an **API-completeness fix**, not new behavior. All docs
  then use `from doxastica import Stance`. (Chosen over keeping the fence + leaking the
  internal path — user decision during planning.)

### Verification gate
- **D-12:** The verification gate is the **full prek suite under CI-parity env**, not
  change-specific checks: `uv sync --locked --dev --extra ladybug && prek run --all-files`.
  M0 conformance stays green on both backends and **SKIP-not-fail** when the ladybug driver
  is absent (SC4) — never assert skips as passes.

### Claude's Discretion
- Exact `Entry`-tuple shape and `_shadow_base` widening mechanics (D-02) — implementer's call
  as long as oracle stance semantics match the SUT and the vacuity guard (D-03) is present.
- Whether SC3 uses `st.sampled_from(Stance)` on the existing single-op tests, a stance-varying
  op-sequence, or both — as long as all four members are exercised on both backends.
- Concrete Cluedo narrative beats, provided the gradient + one decision-driving ordinal
  comparison + the stance/scope reconciliation are all present.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — STANCE-07 (oracle-independent Hypothesis property suite,
  both backends) and DOCS-01 (Cluedo tutorial demonstrates stance).
- `.planning/ROADMAP.md` §"Phase 10: Stance Formal Proof & Docs" — the five success criteria.

### Prior stance phase (the machinery this phase proves)
- `.planning/phases/09-stance-value-layer-write-persistence/09-CONTEXT.md` — the Phase-9
  stance decisions (D-01/D-02 defaults, name-token serialization, contract verbatim-copy).

### Code under test
- `src/doxastica/models.py` §66–98 — `Stance` (plain `Enum` + `@total_ordering`;
  `doubted=0 < suspected=1 < believed=2 < certain=3`; `.name` is the wire token; hydrate via
  `Stance[token]` name-lookup, NOT `Stance(token)`).
- `src/doxastica/core.py` — stance flow: `revise`/`expand` (`stance: Stance = Stance.certain`),
  `contract` (verbatim copy, no stance param), `_append`/`_append_state`/`_hydrate`.
- `tests/test_invariants.py` §112+ — `_SpineMachine` + `MemorySpineMachine`/`LadybugSpineMachine`;
  the `Entry` tuple and `_shadow_base` key to widen (SC1).
- `tests/test_stance.py` — SC2 scaffold to strengthen (antisymmetry currently unasserted).
- `tests/test_stance_persistence.py` — SC3 backbone to quantify over stance.
- `tests/conftest.py` §34–56 — `backend` fixture `params=["memory","ladybug"]` +
  `importorskip` SKIP-not-fail; `tests/test_backend_parity.py` — parity shapes.
- `docs/src/tutorials/cluedo-detective.md` — the tutorial to extend (SC5).

### External (real citations only — no GSD terms in published docs)
- RFC 9562 §5.7 (UUID7) — `source_event_id` minting; already cited in the suite.
- Kumiho / AGM references as already used elsewhere in docs (stance is the doxastica
  within-scope extension, not from the paper — frame accordingly).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_SpineMachine` shadow/oracle model + `MemorySpineMachine`/`LadybugSpineMachine` subclasses
  — extend in place for SC1; both-backends parameterization already there.
- `backend` fixture (`conftest.py`, `params=["memory","ladybug"]`, `importorskip`) — reuse
  verbatim for SC3 property tests; SKIP-not-fail is already correct.
- `test_stance_persistence.py` conventions — backend-parametrized, `is`-identity, drive
  through `MemoryCore(backend)` — keep this shape and quantify over stance.

### Established Patterns
- **Enumerate tiny domains, Hypothesis for large ones** (D-05): 4-member order laws →
  `itertools.product`; op-sequences → Hypothesis stateful/`@given`.
- **`is`-identity assertions** make name-vs-value hydrate regressions raise loud rather than
  silently pass — keep for all stance round-trip checks.
- **Prove the negative** — no-arithmetic (SC2) and the vacuity guard (SC1, D-03) are both
  "assert the thing that should be impossible/absent is actually exercised-or-rejected."

### Integration Points
- Oracle stance semantics ↔ `core.py` write-spine (contract verbatim-copy is the fiddly
  match point).
- Docs `revise`/`expand` signature refs ↔ `core.py` current signatures (must not drift;
  `mkdocs build --strict`).

</code_context>

<specifics>
## Specific Ideas

- User's explicit standard for this phase: **"good" property tests, not weak rubber-stamps.**
  The whole phase is judged against non-vacuity — the widened oracle must be *proven* to
  discriminate stance (D-03), not merely capable of it.
- Prefer **exhaustive enumeration over Hypothesis sampling** for the 4-element order axioms
  (D-05) — a complete proof, deliberately stronger than the roadmap's literal `@given` ask.

</specifics>

<deferred>
## Deferred Ideas

- **Stance filtering** in `query_scope` / `BeliefFilter` (no stance field on the filter
  today) — out of scope for Phase 10; stance is stored/returned but not a query predicate.
  Revisit only if a consumer needs it.
- Any stance *behavior* change in `src/` — out of scope; Phase 10 is tests + docs.

None else — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-stance-formal-proof-docs*
*Context gathered: 2026-07-04*
