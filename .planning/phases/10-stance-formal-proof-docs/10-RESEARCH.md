# Phase 10: Stance Formal Proof & Docs - Research

**Researched:** 2026-07-04
**Domain:** Hypothesis stateful/property testing (oracle widening + exhaustive enumeration), pydantic-frozen enum laws, mkdocs-material tutorial authoring
**Confidence:** HIGH (all mechanics read directly from the code under test; tool versions verified against the installed env)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Phase 10 is NOT "SC1 + docs with SC2/SC3 as trivial `@given` lifts." The existing `tests/test_stance.py` (SC2) and `tests/test_stance_persistence.py` (SC3) are honest *example-based* tests, not property tests. They assert *instances* where the phase requires *laws*. None of SC2/SC3 is "done." The quantification IS the substance. Standard: **"good" property tests, not weak rubber-stamps.**
- **D-02:** Widen the oracle `Entry` in `_SpineMachine` (`tests/test_invariants.py`) and the `_shadow_base` state-equality key to carry stance. The oracle's stance semantics MUST match the SUT exactly — `contract` copies prior stance **verbatim** (STANCE-04), so the oracle must copy-on-contract identically or the K*6 invariant false-positives.
- **D-03 (vacuity guard — MANDATORY):** Widening the key does nothing unless the Hypothesis strategy **actually generates a `revise` and an `expand` of the same belief with different stances**. Add an explicit **generator-coverage guard** (`hypothesis.event()` tag, or a targeted assertion / stats check) proving the differing-stance discriminating case is reached. "Non-vacuous" must be *proven*, not asserted.
- **D-04:** Antisymmetry is literally unasserted today. `test_stance_total_order` checks one fixed chain + a couple of reflected operators; never `a < b ⟹ not (b < a)`, transitivity, or totality. Genuinely new work.
- **D-05:** Domain is **4 elements** → **exhaustively enumerate** the order axioms (`itertools.product(Stance, repeat=2)` = 16 pairs; `repeat=3` = 64 triples) rather than Hypothesis-*sampling*. A complete enumeration is a proof; a sample is an anecdote. Assert the **axioms** (irreflexivity, antisymmetry, transitivity, totality = exactly-one-of `<`/`==`/`>`). This is **stronger** than the roadmap's literal `@given` — the intended reading. Discipline: **enumerate tiny domains, use Hypothesis where the space is large (op-sequences in SC1/SC3).**
- **D-06:** For no-arithmetic: strengthen toward a **closure claim** (parametrize/enumerate operators × member pairs) so "no arithmetic operator is reachable" is asserted broadly, not by three witnesses.
- **D-07:** `tests/test_stance_persistence.py` is a solid backbone (backend-parametrized, `is`-identity, driven through `MemoryCore`) — keep that shape. But each test pins one stance; a `doubted`-only hydrate bug would sail through.
- **D-08:** Quantify the stance — `@given(stance=st.sampled_from(Stance))` (and/or a stance-varying op-sequence) — so round-trip / contract-verbatim / `get_scope_at` hold for **all four members**, not one witness each.
- **D-09:** The genuine explanatory hazard is **conflating stance with scope**. Stance is a *within-scope* epistemic gradient; the certain/provisional **scope** split is a *cross-scope* distinction. The tutorial must hold these apart and reconcile them explicitly.
- **D-10:** Cluedo tutorial demonstrates a gradient `suspected → believed → certain` plus **one reader-side ordinal comparison driving a decision** (e.g. "act only if stance ≥ believed"). Ordinal comparison is a **reader-side** concern — the core stores/returns stance and never interprets it.
- **D-11:** Refresh `revise`/`expand` signature references site-wide (they now carry `stance: Stance = Stance.certain`). Docs must contain **no GSD/decision-ID/phase-number leakage** — real paper/RFC citations only. Gate on `mkdocs build --strict`.
- **D-12:** The verification gate is the **full prek suite under CI-parity env**: `uv sync --locked --dev --extra ladybug && prek run --all-files`. M0 conformance stays green on both backends and **SKIP-not-fail** when the ladybug driver is absent (SC4).

### Claude's Discretion
- Exact `Entry`-tuple shape and `_shadow_base` widening mechanics (D-02) — implementer's call as long as oracle stance semantics match the SUT and the vacuity guard (D-03) is present.
- Whether SC3 uses `st.sampled_from(Stance)`, a stance-varying op-sequence, or both — as long as all four members are exercised on both backends.
- Concrete Cluedo narrative beats, provided the gradient + one decision-driving ordinal comparison + the stance/scope reconciliation are all present.

### Deferred Ideas (OUT OF SCOPE)
- **Stance filtering** in `query_scope` / `BeliefFilter` — no stance field on the filter today; stored/returned but not a query predicate.
- Any stance *behavior* change in `src/` — Phase 10 is tests + docs. (See Open Question 1 for the one surgical, behavior-neutral `__init__.py` export the docs need — flag for user confirmation.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STANCE-07 | Oracle-independent Hypothesis property suite, both backends, that *carries* stance rather than staying vacuously green: (a) oracle tracks stance per entry, (b) base comparison key widens to `(value, stance)`, (c) round-trip/preservation/reconstruction, (d) total+antisymmetric order & no-arithmetic negative. | SC1 oracle-widening mechanics (exact lines below), SC1 vacuity guard design, SC2 exhaustive order-law enumeration, SC3 stance-quantified persistence. All four sub-parts mapped to concrete tests in Validation Architecture. |
| DOCS-01 | Cluedo tutorial demonstrates a within-scope epistemic gradient + one reader-side ordinal comparison; reconciles stance (within-scope) vs the certain/provisional scope split (cross-scope); `revise`/`expand` signature refs refreshed site-wide; `mkdocs build --strict` green. | Docs plan with exact insertion point, the reconciliation framing, the site-wide signature-refresh grep list, the `Stance` export snag (Open Q1), and the mkdocs --strict / blacken-docs gates. |
</phase_requirements>

## Summary

Phase 10 converts four scaffolds into mechanical proofs and threads stance through the Cluedo tutorial. The work is **tests + docs only** — the `Stance` type, its total order, name-token serialization, write-spine threading, and `contract` verbatim-copy all landed in Phase 9 and are correct as-is (verified by reading `src/doxastica/models.py` §66–98 and `src/doxastica/core.py` §364–445).

The load-bearing new work is **SC1**: the stateful oracle in `tests/test_invariants.py` currently records `(source_event_id, seq, value, status)` per entry and compares belief bases on `{belief_id: value}`. Widening the recorded `Entry`, `_shadow_current`, `_shadow_base`, `_observed_base` (and the standalone `_base_of` / K*6 test) to carry stance is a small, contained diff — but it is **vacuous unless the strategy actually generates a `revise` and an `expand` of the same belief with *different* stances** (D-03). The MANDATORY non-vacuity proof is a deterministic *discrimination test* asserting the widened key distinguishes two states that agree on value but differ on stance, backed by `hypothesis.event()` labels for stats visibility. SC2 (exhaustive `itertools.product(Stance, ...)` order laws + a closure-form no-arithmetic guard) and SC3 (exhaustive `@pytest.mark.parametrize("stance", list(Stance))` over the existing backend-parametrized persistence tests) are straightforward given the discipline "enumerate tiny domains."

**Primary recommendation:** Widen the oracle in place (5-tuple `Entry` carrying the `Stance` member; contract copies it verbatim), prove non-vacuity with a deterministic discrimination test + `event()` label, enumerate SC2 order laws exhaustively via `operator`-module functions (which sidestep basedpyright-strict operator diagnostics), enumerate SC3 over `list(Stance)` on the existing `backend` fixture, and slot a "How sure are you?" gradient step into the Cluedo tutorial with an explicit stance-vs-scope reconciliation callout. **Flag the `Stance`-not-exported snag (Open Q1) for the planner** before writing the tutorial's import line.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Oracle stance tracking + base-key widening (SC1) | Test harness (`tests/test_invariants.py`) | — | The shadow oracle is a pure-Python model; no `src/` change. It must *mirror* the SUT's write-spine semantics (verbatim copy-on-contract) without calling it. |
| Order-law + no-arithmetic proof (SC2) | Test (`tests/test_stance.py`) | Type layer (`models.py`, read-only) | Laws are asserted *about* the frozen `Stance` enum; the enum itself is unchanged. |
| Stance persistence quantification (SC3) | Test (`tests/test_stance_persistence.py`) | Core boundary (`MemoryCore`, read-only) | Serialize/hydrate discipline lives in `core.py`; tests drive it through `MemoryCore(backend)`, never the bare port. |
| Tutorial gradient + reconciliation (SC5) | Docs (`docs/src/tutorials/cluedo-detective.md`) | Reference docs (mkdocstrings, auto-generated) | Stance ordinal comparison is a **reader-side** concern; the core stores/returns and never interprets. |
| Package export surface (`Stance`) | `src/doxastica/__init__.py` | — | **Open Q1** — behavior-neutral one-line export the tutorial import needs; requires user confirmation vs the "no src change" boundary. |

## Standard Stack

No new dependencies. Everything needed is already in the dev toolchain and verified present.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hypothesis | 6.155.2 (installed, verified) | Stateful `RuleBasedStateMachine` (SC1) + `@given` property tests (SC3) | Already the AGM property engine for the whole suite; `event()` / `target()` confirmed importable in this env. `[VERIFIED: uv run python -c import]` |
| pytest | 9.0.3 (per CLAUDE.md, verified line) | Parametrized enumeration (`@pytest.mark.parametrize`) for SC2/SC3 exhaustive tiny-domain proofs | Enumeration over `itertools.product(Stance, …)` / `list(Stance)` is a plain parametrize — no Hypothesis needed for the tiny domains (D-05). `[CITED: CLAUDE.md tool pins]` |
| mkdocs-material + mkdocstrings | 9.7.x line (per CLAUDE.md) | Tutorial authoring + auto-generated `Stance` reference page | `revise`/`expand` reference signatures auto-render from source docstrings, so they update for free; `Stance` gets a reference entry via `gen_ref_pages.py` walking `models.py`. `[CITED: mkdocs.yml, docs/scripts/gen_ref_pages.py]` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `operator` (stdlib) | 3.14 | SC2 no-arithmetic closure guard | `operator.add(a, b)` etc. enumerate operators without triggering basedpyright-strict `reportOperatorIssue` per line (the operands enter as function args, not literal `a + b` source). |
| `itertools` (stdlib) | 3.14 | SC2 exhaustive pair/triple enumeration | `itertools.product(Stance, repeat=2)` (16), `repeat=3` (64). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@pytest.mark.parametrize("stance", list(Stance))` on the fixture-based SC3 tests | `@given(st.sampled_from(Stance))` | The `backend` fixture is **function-scoped**; combining it with `@given` triggers Hypothesis's `function_scoped_fixture` health check AND bleeds state across examples (documented in `test_invariants.py` §560–583, which builds a fresh backend *per example* to dodge exactly this). Exhaustive `parametrize` over 4 members needs no Hypothesis, keeps the existing `backend` fixture verbatim, and is *stronger* (exhaustive, not sampled). **Recommended for the single-op SC3 tests.** Reserve Hypothesis for stance-*varying op sequences* (already covered by the SC1 stateful machine once stance is threaded). |
| `operator`-module functions for SC2 no-arithmetic | Literal `Stance.certain + Stance.doubted` per line | Literal form needs a `# pyright: ignore[reportOperatorIssue]` on every line (see current `test_stance.py` §42–49). The closure form (`operator.add` over `itertools.product`) needs at most one narrow ignore and asserts the *closure*, not three witnesses (D-06). |

**Installation:** none — `uv sync --locked --dev --extra ladybug` (the existing CI-parity command) suffices.

## Package Legitimacy Audit

Not applicable — Phase 10 installs **no external packages**. All libraries (hypothesis, pytest, mkdocs-material, operator, itertools) are already pinned in the project (see CLAUDE.md Technology Stack) and verified present in the env.

## Architecture Patterns

### System Data Flow (SC1 oracle widening)

```
Hypothesis strategy
  ├─ revise rule  ─(scope, belief, value, source_event_id, STANCE←sampled_from(Stance))→ core.revise(...)  ──┐
  ├─ expand rule  ─(same shape, own STANCE draw)───────────────────────────────────────→ core.expand(...)  ──┤
  └─ contract rule ─(scope, belief, source_event_id)────────────────────────────────────→ core.contract(...) ─┤
                                                                                                               │ SUT write-spine
        mirror each op into the shadow oracle (NEVER reads the SUT)                                            ▼
  _record(scope, belief, value, source_event_id, status, STANCE)  →  Entry = (src, seq, value, status, stance)
        contract mirrors: _record(..., "retracted", prior_stance)   # VERBATIM copy, matches STANCE-04
                                                                                                               │
        oracle winner select: max((src, seq)) over Entries per (scope, belief)                                 ▼
  _shadow_current → (has_current, value, STANCE)      _shadow_base → {belief_id: (value, STANCE)}
                                                                                                               │
        @invariant / contract rule compares:                                                                  ▼
  _observed_base(scope) = {s.belief_id: (s.value, s.stance)}  ═══compare═══  _shadow_base(scope)
        (widened key: agreement on value BUT divergence on stance now FAILS K*2/K*3 parity)
```

The diagram's only new edges vs. the current file are the `STANCE` payload threaded through `_record`/`Entry`/`_shadow_current`/`_shadow_base` and the `s.stance` projection in `_observed_base`. Everything else (winner selection by `(src, seq)`, the anti-tautology independent-oracle rule) is unchanged.

### Pattern 1: Widen the oracle `Entry` to a 5-tuple carrying the `Stance` member

**What:** Record the `Stance` member (not the `.name` token) in the oracle so comparisons are direct member equality against `BeliefState.stance` (also a member).
**When to use:** SC1, `tests/test_invariants.py`.
**Exact lines to change (quoted from the current file):**

- §135 `Entry = tuple[str, int, Any, str]` → `Entry = tuple[str, int, Any, str, Stance]`
- §165–173 `_record(self, scope_id, belief_id, value, source_event_id, status)` → add `stance: Stance`; append it into the tuple: `(str(source_event_id), self._seq, value, status, stance)`
- §175–188 `_shadow_current` returns `(False, None)` / `(True, value)` → return `(False, None, None)` / `(True, value, stance)`; unpack `_src, _seq, value, status, stance = max(...)`
- §229–245 `_shadow_base` builds `base[b] = value` → `base[b] = (value, stance)`; unpack the widened `_shadow_current` return (`has_current, value, stance = self._shadow_current(s, b)`)
- §247–255 `_observed_base` returns `{s.belief_id: s.value ...}` → `{s.belief_id: (s.value, s.stance) ...}`
- §209–223 `revise` / `expand` rules: add rule kwarg `stance=st.sampled_from(Stance)` and pass it to both `core.revise(...)`/`core.expand(...)` and `_record(...)`
- §262–299 `contract` rule: `_has, prior_value = self._shadow_current(...)` → `_has, prior_value, prior_stance = ...`; and `self._record(scope_id, belief_id, prior_value, source_event_id, "retracted", prior_stance)` — **this is the STANCE-04 verbatim-copy mirror; if the oracle copies a default here instead of `prior_stance`, K*2/K*3 false-positive.**
- §284/§325 the second `_shadow_current` unpack inside `_assert_hansson_success_inclusion` — add the third return slot.
- §387–424 keystone `current_is_total_single_valued_and_chain_tail`: `has_current, expected = self._shadow_current(...)` → `has_current, expected, expected_stance = ...`; after the existing value assertion add `assert Stance[current["stance"]] is expected_stance` (`_current` returns the raw tail dict whose `"stance"` is the stored `.name` token — verified `core.py` §322 stores `"stance": stance` = the pre-serialized name token, and §443 reads `prior["stance"]`).
- §92–109 `_chain_tail` helper returns `{"state_id", "value"}` → add `"stance": tail.stance` (a `Stance` member; `get_revision_chain` returns hydrated `BeliefState`s). Then assert it in the keystone alongside `state_id`.

**Why the member (not the token):** `BeliefState.stance` is a `Stance` member (models.py §140), `query_scope` returns hydrated states, so `s.stance` is a member. Storing the member in the oracle makes `_observed_base == _shadow_base` a direct tuple-equality with no token/member mismatch. The one place the SUT exposes the *stored token* rather than a member is the `_current` dict (`current["stance"]`), handled with `Stance[...]` name-lookup in the keystone.

**Postulate helpers are unaffected by the widening except by construction:** `_assert_hansson_relevance` / `_assert_hansson_success_inclusion` operate on `set(base)` (keys) — unchanged. `_assert_hansson_core_retainment` (§367–373) iterates `base_before.items()` comparing `base_after[other] == value` where `value` is now `(value, stance)` — this correctly asserts *no collateral stance change* on other beliefs for free.

### Pattern 2: SC1 non-vacuity — deterministic discrimination test (MANDATORY, D-03)

**What:** Prove the widened key actually discriminates, and that the strategy reaches the differing-stance case.
**When to use:** SC1, mandatory.
**Two complementary mechanisms — recommend BOTH:**

1. **`hypothesis.event()` label (observability).** In the `revise`/`expand` rules, after mirroring, emit an event when the new op changes the *current winning stance* for its `(scope, belief)`:
   ```python
   # Source: hypothesis stateful docs (event() shows in --hypothesis-show-statistics)
   from hypothesis import event
   ...
   has_cur, _v, cur_stance = self._shadow_current(scope_id, belief_id)  # BEFORE mirroring the new op
   if has_cur and cur_stance is not stance:
       event("write flips the current stance of an existing belief")
   ```
   Surfaces in CI via `pytest --hypothesis-show-statistics`; documents that the discriminating path is exercised.

2. **Deterministic discrimination meta-test (the load-bearing proof).** A plain test — no Hypothesis — that would FAIL if someone reverted the widening to value-only:
   ```python
   # Two ops that AGREE on value but DIFFER on stance must yield DIFFERENT widened base entries.
   # If the key were still {belief_id: value}, these would compare equal and the guard is vacuous.
   @pytest.mark.parametrize("backend_kind", ["memory", "ladybug"])
   def test_widened_key_discriminates_stance(backend_kind):
       be = _build_backend(backend_kind)
       try:
           core = MemoryCore(be)
           core.revise("alice", "b1", "v", uuid.uuid7(), stance=Stance.believed)
           core.expand("bob", "b1", "v", uuid.uuid7(), stance=Stance.certain)
           a = {s.belief_id: (s.value, s.stance) for s in core.query_scope("alice", BeliefFilter())}
           b = {s.belief_id: (s.value, s.stance) for s in core.query_scope("bob", BeliefFilter())}
           assert a != b, "widened (value, stance) key must distinguish same-value/different-stance"
           assert a == {"b1": ("v", Stance.believed)}
           assert b == {"b1": ("v", Stance.certain)}
       finally:
           close = getattr(be, "close", None)
           if callable(close): close()
   ```
   This is a *proof the guard guards* — it pins the widening itself, on both backends. Reuses the existing `_build_backend` helper (§573–583).

**Alternative to the event() approach** (if the reviewer wants a hard programmatic assertion rather than stats): a module-level `set` populated inside the rule when the discriminating condition holds, asserted non-empty in a dedicated test that runs the machine via `run_state_machine_as_test`. Heavier and collection-order-fragile — the deterministic discrimination test above is the cleaner defensible proof; keep `event()` for the stateful run's visibility.

### Pattern 3: SC2 exhaustive order laws via `itertools.product`

**What:** Replace the single fixed-chain assertion with the four order axioms over the complete domain.
**When to use:** SC2, `tests/test_stance.py`.
**Example:**
```python
import itertools, operator
import pytest
from doxastica.models import Stance

_PAIRS = list(itertools.product(Stance, repeat=2))     # 16
_TRIPLES = list(itertools.product(Stance, repeat=3))   # 64

@pytest.mark.parametrize("a", list(Stance))
def test_irreflexivity(a):
    assert not (a < a) and not (a > a) and (a == a)

@pytest.mark.parametrize("a,b", _PAIRS)
def test_totality_trichotomy(a, b):
    # exactly one of <, ==, > holds (totality + antisymmetry together)
    assert (a < b) + (a == b) + (a > b) == 1

@pytest.mark.parametrize("a,b", _PAIRS)
def test_antisymmetry(a, b):
    if a < b:
        assert not (b < a) and a != b

@pytest.mark.parametrize("a,b,c", _TRIPLES)
def test_transitivity(a, b, c):
    if a < b and b < c:
        assert a < c
```
`(a < b) + (a == b) + (a > b) == 1` is the trichotomy law — it simultaneously proves totality (at least one holds) and antisymmetry+irreflexivity (at most one holds). Keep an explicit `test_antisymmetry` too for a named proof artifact (D-04 calls it out by name).

### Pattern 4: SC2 no-arithmetic closure guard

**What:** Assert *no* arithmetic/bitwise operator is reachable across the whole domain, and cross-type comparison raises for representative non-`Stance` operands.
**Example:**
```python
import operator
_ARITH = [operator.add, operator.sub, operator.mul, operator.truediv,
          operator.floordiv, operator.mod, operator.pow,
          operator.and_, operator.or_, operator.xor, operator.lshift, operator.rshift]

@pytest.mark.parametrize("op", _ARITH)
@pytest.mark.parametrize("a,b", _PAIRS)
def test_no_arithmetic_operator_is_reachable(op, a, b):
    with pytest.raises(TypeError):
        op(a, b)  # closure: every arithmetic op × every member pair raises

@pytest.mark.parametrize("other", [5, "certain", None, 1.5, Stance])  # representative non-Stance operands
@pytest.mark.parametrize("member", list(Stance))
def test_cross_type_comparison_raises(member, other):
    for cmp in (operator.lt, operator.gt, operator.le, operator.ge):
        with pytest.raises(TypeError):
            cmp(member, other)
```
Using `operator.*` functions avoids the per-line `# pyright: ignore[reportOperatorIssue]` wall in the current `test_stance.py` §42–49 (the operands enter as `Any`-typed function args). Note `==`/`!=` do NOT raise on cross-type (they return `False`/`True` — Python object identity fallback) — assert only `<`/`>`/`<=`/`>=` raise, matching STANCE-06's precise claim.

### Pattern 5: SC3 exhaustive stance parametrization on the existing backend fixture

**What:** Quantify the three persistence tests over all four members without disturbing the `backend` fixture.
**When to use:** SC3, `tests/test_stance_persistence.py`.
**Example:**
```python
@pytest.mark.parametrize("stance", list(Stance))
def test_stance_round_trips_byte_stable(backend, stance):
    core = MemoryCore(backend)
    core.revise("alice", "b1", "v", _event_id(), stance=stance)
    [state] = core.query_scope("alice", BeliefFilter())
    assert state.stance is stance          # `is`-identity: name-vs-value hydrate bug raises loud
    assert state.stance.name == stance.name
```
Apply the same `@pytest.mark.parametrize("stance", list(Stance))` to `test_contract_preserves_stance_verbatim` and `test_get_scope_at_reconstructs_stance`. This is **exhaustive over the 4-member domain** (D-05 discipline: enumerate tiny domains) and composes cleanly with the `backend` fixture's `params=["memory","ladybug"]` → 8 cases each. Keeps the `is`-identity assertions (D-07). Optionally add ONE stance-*varying op-sequence* test if the reviewer wants sequences — but the SC1 stateful machine already exercises stance-varying sequences on both backends once threaded, so the exhaustive single-op parametrization is sufficient for SC3's stated properties.

### Anti-Patterns to Avoid
- **`@given(st.sampled_from(Stance))` on a test that also takes the `backend` fixture.** Triggers the `function_scoped_fixture` health check and bleeds state across examples. The suite already documents this (`test_invariants.py` §560–583). Use `@pytest.mark.parametrize` for the fixture-based tests, OR the `_build_backend`-per-example pattern if Hypothesis is genuinely needed.
- **Oracle copying a default stance on contract.** STANCE-04 is verbatim; the oracle mirror MUST copy `prior_stance`, else K*2/K*3 false-positive (D-02).
- **Storing the `.name` token in the oracle.** Store the `Stance` *member* so comparisons are direct; only `_current`'s raw dict exposes the token (`Stance[current["stance"]]` there).
- **Sampling the 4-element order domain with Hypothesis.** D-05: a complete enumeration is a proof; a sample is an anecdote.
- **GSD/decision-ID/phase-number leakage in published docs** (D-11 + auto-memory "No GSD process refs in docs"): no `D-02`, `STANCE-07`, `SC5`, `Phase 10` in the tutorial. Real paper/RFC citations only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Prove a differing-stance op-sequence is generated | A bespoke coverage counter framework | `hypothesis.event()` + one deterministic discrimination test | `event()` is the built-in stats channel; the deterministic test is the hard proof. |
| Enumerate order-law pairs/triples | Hand-written 16/64-case lists | `itertools.product(Stance, repeat=n)` | Exhaustive, self-maintaining if the enum grows. |
| Assert no operator is reachable | 12 literal `with pytest.raises` blocks + pyright ignores | `operator.*` × `itertools.product` parametrize | Closure claim (D-06), no per-line ignores. |
| Fresh isolated backend per property example | New fixture | Existing `_build_backend` / `backend` fixture | Already handles ladybug `importorskip` SKIP-not-fail + per-example isolation. |

**Key insight:** Every tool this phase needs already exists in the suite; the work is *composition and quantification*, not new machinery.

## Common Pitfalls

### Pitfall 1: The oracle-widening looks done but is vacuous
**What goes wrong:** `Entry`/`_shadow_base` carry stance, all tests pass — but the strategy never generated a same-belief revise+expand with differing stances, so the widened key never discriminated. SC1 passes green while proving nothing (the exact failure this phase exists to kill).
**Why it happens:** With independent `st.sampled_from(Stance)` draws on a 3-belief pool over 20 steps, collisions *are* frequent — but "frequent in practice" is not "proven reached."
**How to avoid:** The deterministic discrimination test (Pattern 2, mechanism 2) + `event()` label (mechanism 1). MANDATORY per D-03.
**Warning signs:** No `event` line in `--hypothesis-show-statistics`; a discrimination test that still passes when the widening is reverted.

### Pitfall 2: `function_scoped_fixture` health check on SC3
**What goes wrong:** Adding `@given(st.sampled_from(Stance))` to a `backend`-fixture test raises a Hypothesis health-check error and bleeds backend state across examples.
**Why it happens:** Hypothesis does not reset a function-scoped fixture between generated inputs.
**How to avoid:** Use `@pytest.mark.parametrize("stance", list(Stance))` (exhaustive, no Hypothesis) on the fixture-based tests, per Pattern 5.
**Warning signs:** `FailedHealthCheck: function_scoped_fixture`.

### Pitfall 3: token-vs-member mismatch in the keystone invariant
**What goes wrong:** Comparing `current["stance"]` (a `.name` token string, e.g. `"certain"`) directly to a `Stance` member → always unequal → false failure.
**Why it happens:** `_current` returns the raw stored tail dict; `core.py` §322 stores `"stance": stance` as the pre-serialized `.name` token (not a member).
**How to avoid:** `Stance[current["stance"]] is expected_stance` (name-lookup, NOT `Stance(current["stance"])` which is value-lookup and raises — guarded by `test_stance.py::test_stance_hydration_is_name_based`).
**Warning signs:** Keystone invariant fails on the very first stateful step with a token != member message.

### Pitfall 4: `Stance` is not importable as `from doxastica import Stance` in the tutorial
**What goes wrong:** The tutorial's reader-side comparison example (`if state.stance >= Stance.believed`) needs `Stance`, but `doxastica/__init__.py` does not export it (verified — `__all__` §22–37 omits `Stance`). `from doxastica import Stance` raises `ImportError`; a runnable-tested tutorial code block would fail `mkdocs`/doctest and the blacken-docs/CI gate.
**Why it happens:** Phase 9 added `Stance` to `models.py` and the `revise`/`expand` signatures but never to the package `__all__`.
**How to avoid:** See Open Question 1 — either export `Stance` (one-line, behavior-neutral) or import it as `from doxastica.models import Stance` in the tutorial. **Resolve before writing the tutorial import line.**
**Warning signs:** `ImportError: cannot import name 'Stance' from 'doxastica'`.

### Pitfall 5: `==` cross-type is expected to NOT raise
**What goes wrong:** Over-asserting that `Stance.certain == 3` raises `TypeError`. It does not — `Enum.__eq__` falls back to identity and returns `False`. Only ordering (`<`/`>`/`<=`/`>=`) raises (via `__lt__` returning `NotImplemented`).
**How to avoid:** The no-arithmetic closure guard asserts `TypeError` only for arithmetic ops and for the four *ordering* comparisons — never for `==`/`!=`. Matches STANCE-06's exact wording.

### Pitfall 6: blacken-docs reformats tutorial code
**What goes wrong:** New Python code blocks in the tutorial fail the `blacken-docs` prek hook (args `-l 100`) if not pre-formatted.
**How to avoid:** Write code blocks black-clean at line length 100; run `prek run --all-files` (D-12) which includes `blacken-docs`, `ruff`, `ruff-format`, `trailing-whitespace`, `end-of-file-fixer`. `mkdocs build --strict` is a *separate* gate (CI `.github/workflows/docs.yml` §45), not in prek — run it explicitly too.

## Code Examples

### `_shadow_current` / `_shadow_base` widened (SC1)
```python
# Source: tests/test_invariants.py §175-245 (current), widened for stance
def _shadow_current(self, scope_id: str, belief_id: str) -> tuple[bool, Any, Stance | None]:
    entries = self.entries.get((scope_id, belief_id))
    if not entries:
        return (False, None, None)
    _src, _seq, value, status, stance = max(entries, key=lambda e: (e[0], e[1]))
    if status == "retracted":
        return (False, None, None)
    return (True, value, stance)

def _shadow_base(self, scope_id: str) -> dict[str, tuple[Any, Stance]]:
    base: dict[str, tuple[Any, Stance]] = {}
    for s, b in self.entries:
        if s != scope_id:
            continue
        has_current, value, stance = self._shadow_current(s, b)
        if has_current:
            base[b] = (value, stance)
    return base
```

### Reader-side ordinal decision in the tutorial (SC5)
```python
# Source: doxastica reader-side comparison (the core stores/returns; the reader decides)
from doxastica.models import Stance  # or `from doxastica import Stance` if exported (Open Q1)

[culprit] = core.query_scope("theory", BeliefFilter(belief_ids={"culprit"}))
# Only accuse when the theory has hardened past a mere suspicion.
if culprit.stance >= Stance.believed:
    print(f"Accuse {culprit.value}.")
else:
    print("Keep gathering evidence.")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Example-based stance tests (fixed chain, single pinned stance) | Law-based property/enumeration tests (D-01) | Phase 10 | The quantification is the deliverable, not a lift. |
| `{belief_id: value}` oracle base key | `{belief_id: (value, stance)}` | Phase 10 SC1 | K*2/K*3/K*6 parity now compares stance. |

**Deprecated/outdated:** none — this phase adds proofs over a correct-as-shipped Phase 9 core.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exporting `Stance` in `__init__.py` counts as behavior-neutral (packaging surface), not a "src behavior change" barred by the phase boundary. | Open Q1 / Pitfall 4 | If the user insists on zero `__init__.py` edits, the tutorial must `from doxastica.models import Stance` (an internal-path leak in a public tutorial). Low risk, but must be decided before writing the tutorial. |
| A2 | `mkdocs build --strict` remains a CI gate (docs.yml §45) and is the intended SC5 gate; it is NOT part of the prek suite, so it must be run explicitly in phase verification alongside `prek run --all-files`. | Docs plan / Pitfall 6 | If missed, a broken cross-ref/nav lands green locally and fails only in CI. `[VERIFIED: .github/workflows/docs.yml grep]` |
| A3 | The existing hand-written `core.revise(...)` call examples across the 10 docs files need no edit (stance is optional; omitting it is valid and unchanged behavior); only *prose that enumerates the signature* and the new tutorial section need touching. | Docs plan (D-11) | If a doc block prose-lists the parameter roster, it must gain `stance`. Grep confirms no prose signature-roster listing exists today (only live `core.revise(..., source_event_id=...)` calls, which stay valid). Low risk. |

## Open Questions (RESOLVED)

1. **Is `Stance` meant to be a top-level export?** (Blocks the tutorial import line.)
   - What we know: `Stance` is public API (accepted by `revise`/`expand`, returned on `BeliefState.stance`) but is absent from `doxastica/__init__.py` `__all__` (verified). Every other public type is `from doxastica import ...`.
   - What's unclear: whether adding `Stance` to `__all__` (a one-line, runtime-behavior-neutral packaging change) is within Phase 10's "tests + docs only, no src change" boundary, or must be deferred.
   - Recommendation: **Export it.** A public tutorial teaching a reader-side `Stance` comparison that must import from `doxastica.models` is an internal-structure leak. Adding one name to `__all__` changes no behavior and no signatures. If the user holds the boundary strictly, fall back to `from doxastica.models import Stance` in the tutorial and note it. Flag to the user in discuss/plan.
   - **RESOLVED:** Export it. Locked as CONTEXT D-13; implemented in plan 10-04 Task 1 (`Stance` added to `doxastica/__init__.py` `__all__`). The tutorial imports `from doxastica import Stance`.

2. **Does the reviewer want a hard programmatic non-vacuity assertion inside the stateful run, or is `event()` + the deterministic discrimination test sufficient?**
   - What we know: D-03 accepts "`hypothesis.event()` tag, or a targeted assertion / stats check."
   - Recommendation: `event()` (stats visibility) + the deterministic discrimination test (hard proof) satisfies D-03 cleanly; the module-level-counter approach is available but collection-order-fragile.
   - **RESOLVED:** `event()` + the deterministic discrimination test (no hard programmatic assertion inside the stateful run). Implemented in plan 10-01 Task 2 — the deterministic `test_widened_key_discriminates_stance` (routed through the widened `_base_of`, breaks on revert) is the hard proof; the `hypothesis.event()` label gives stateful-oracle stats visibility.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| hypothesis | SC1/SC3 property tests | ✓ | 6.155.2 | — |
| ladybug (extra) | SC4 dual-backend parity | ✓ (extra) | per lock | SKIP-not-fail via `importorskip` (already wired) |
| mkdocs-material + mkdocstrings | SC5 docs build | ✓ (docs group) | 9.7.x | — |
| `operator`, `itertools`, `uuid` | SC2/SC3 | ✓ stdlib 3.14 | 3.14 | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** ladybug (optional extra) — SKIP-not-fail is the correct and already-implemented behavior (SC4).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + hypothesis 6.155.2 |
| Config file | `pyproject.toml` (pytest/coverage), `.pre-commit-config.yaml` (prek gate), `mkdocs.yml` (docs) |
| Quick run command | `uv run pytest tests/test_stance.py tests/test_stance_persistence.py tests/test_invariants.py -q` |
| Full suite command | `uv sync --locked --dev --extra ladybug && prek run --all-files` (D-12) + `uv run mkdocs build --strict` |

### Success Criterion → Test Map
| SC / Req | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| SC1 / STANCE-07(a,b) | Oracle records stance; base key `(value, stance)`; K*2/K*3/K*6 compare stance | stateful property (both backends) | `uv run pytest tests/test_invariants.py -q` | ✅ (widen in place) |
| SC1 non-vacuity / D-03 | Differing-stance revise+expand discriminated; guard is non-vacuous | deterministic discrimination + `event()` stat | `uv run pytest tests/test_invariants.py -q --hypothesis-show-statistics` | ❌ Wave 0 (add `test_widened_key_discriminates_stance`) |
| SC2 / STANCE-07(d) | Order total+antisymmetric (irreflexivity, antisymmetry, transitivity, trichotomy) exhaustively | parametrized enumeration | `uv run pytest tests/test_stance.py -q` | ✅ (strengthen; antisymmetry/transitivity/trichotomy new) |
| SC2 / STANCE-06 | No arithmetic/bitwise op reachable; cross-type ordering raises (closure) | parametrized closure | `uv run pytest tests/test_stance.py -q` | ✅ (strengthen to closure form) |
| SC3 / STANCE-07(c), STANCE-04/05 | round-trip, contract-verbatim, get_scope_at over all 4 members, both backends | parametrized over `list(Stance)` × `backend` | `uv run pytest tests/test_stance_persistence.py -q` | ✅ (add `@parametrize("stance", list(Stance))`) |
| SC4 | M0 conformance green both backends; SKIP-not-fail when ladybug absent | full suite | `uv run pytest -q` (and again without `--extra ladybug` to confirm SKIP) | ✅ (must not regress) |
| SC5 / DOCS-01 | Cluedo gradient + reader-side ordinal decision + stance/scope reconciliation; signature refs; strict build | docs build | `uv run mkdocs build --strict` + `prek run --all-files` (blacken-docs, ruff on code blocks) | ✅ (extend tutorial) |

### How to detect a VACUOUS pass (per SC)
- **SC1:** revert the `Entry`/base widening locally → `test_widened_key_discriminates_stance` MUST fail. If it still passes, the guard is not guarding. Confirm `event("write flips the current stance…")` appears in `--hypothesis-show-statistics`.
- **SC2:** mutate `Stance.__lt__` to a broken order (e.g. always `False`) → trichotomy/transitivity/antisymmetry MUST fail. If only the old fixed-chain test existed, the mutation would slip through.
- **SC3:** introduce a `doubted`-only hydrate bug (`Stance(props["stance"])` value-lookup) → the `is`-identity assertion MUST raise for the `doubted` parametrization. A single pinned-stance test would miss members it doesn't exercise.
- **SC4:** run the suite in an env without the ladybug extra → ladybug cases report SKIP, not fail or silent pass (auto-memory: "Skipped tests are a red flag" — surface them, never count as pass).
- **SC5:** `mkdocs build --strict` fails on any broken cross-ref; grep the built tutorial for `D-0`, `STANCE-`, `Phase `, `SC` to confirm no process-ID leakage.

### Sampling Rate
- **Per task commit:** the quick-run command for the touched test file.
- **Per wave merge:** `uv run pytest -q` (full test suite, both backends).
- **Phase gate:** `uv sync --locked --dev --extra ladybug && prek run --all-files` green, then `uv run mkdocs build --strict` green, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_invariants.py::test_widened_key_discriminates_stance` — the D-03 non-vacuity proof (new deterministic test).
- [ ] SC2 order-law tests (irreflexivity, antisymmetry, transitivity, trichotomy) — new parametrized enumerations in `tests/test_stance.py`.
- [ ] SC2 no-arithmetic closure test — strengthen the existing three-witness guard.
- [ ] Framework install: none — all present.

## Security Domain

This is a **tests + docs** phase with **no new `src/` code path and no new external input surface** — the injection-hardened boundaries (closed `BeliefFilter`, base64/JSON `value` encoding, name-token `Stance` serialization) all shipped and are unchanged.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Indirectly (unchanged) | The closed pydantic `BeliefFilter` + `extra="forbid"` frozen models are the existing control; this phase adds no new input surface. |
| V6 Cryptography | No | none |
| V2/V3/V4 (auth/session/access) | No | library core, no auth surface |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher/value injection via stance token | Tampering | Already mitigated: stance serialized as a closed-enum `.name` (never free string), hydrated via `Stance[token]` name-lookup; no new surface in Phase 10. |

No new threats introduced.

## Sources

### Primary (HIGH confidence)
- `tests/test_invariants.py` (full read) — exact `Entry`/`_shadow_current`/`_shadow_base`/`_observed_base`/keystone lines to widen; `_build_backend` per-example pattern; K*2/K*3/K*6 structure.
- `tests/test_stance.py`, `tests/test_stance_persistence.py`, `tests/conftest.py` (full read) — SC2/SC3 scaffolds; `backend` fixture SKIP-not-fail.
- `src/doxastica/models.py` §65–99, `src/doxastica/core.py` §224–260, §303–345, §364–445 — `Stance` type; `_current`/`_hydrate` stance token semantics; write-spine verbatim copy-on-contract.
- `src/doxastica/__init__.py` (full read) — `Stance` NOT exported (Open Q1).
- `docs/src/tutorials/cluedo-detective.md` (full read) — insertion point + zero current stance mentions; scope-split framing to reconcile against.
- `.github/workflows/docs.yml` §45, `.pre-commit-config.yaml` (blacken-docs §33–38, basedpyright §26) — the SC5/D-12 gates.
- `uv run python -c "import hypothesis; event; target"` → hypothesis 6.155.2, `event`/`target`/stateful importable — VERIFIED.
- `.planning/config.json` — `nyquist_validation: true`, `commit_docs: true`.

### Secondary (MEDIUM confidence)
- CLAUDE.md Technology Stack — tool version pins (pytest 9.0.3, mkdocs-material 9.7.x) not independently re-verified this session but consistent with the installed hypothesis.

### Tertiary (LOW confidence)
- none.

## Metadata

**Confidence breakdown:**
- SC1 oracle-widening mechanics: HIGH — every line to change read and quoted.
- SC1 non-vacuity design: HIGH — `event()`/deterministic-discrimination both verified available.
- SC2 enumeration + no-arithmetic closure: HIGH — domain is 4 elements; `operator`/`itertools` stdlib.
- SC3 quantification: HIGH — exhaustive parametrize composes with the existing fixture.
- SC5 docs: HIGH on mechanics/gates; the `Stance` export decision (Open Q1) is the one MEDIUM item needing user confirmation.

**Research date:** 2026-07-04
**Valid until:** 2026-08-04 (stable — internal test/docs work over a frozen core; no fast-moving external deps)
</content>
</invoke>
