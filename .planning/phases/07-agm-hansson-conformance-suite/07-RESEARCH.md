# Phase 7: AGM/Hansson Backend Conformance Suite & Irony Join (M0 Exit Gate) - Research

**Researched:** 2026-06-19
**Domain:** Property-based formal verification (Hypothesis stateful testing) of an append-only AGM/Hansson belief-revision core over a parameterised dual-backend conformance harness
**Confidence:** HIGH (the entire phase is test/query patterns over already-shipped, already-read source; postulate phrasings cross-checked against the Stanford Encyclopedia of Philosophy)

## Summary

Phase 7 is the M0 exit gate: the mechanically-verified proof that *is* the library's reason to
exist. Critically, it adds **essentially no production code**. Every artifact — the AGM revision
postulates, the Hansson base-contraction postulates, the structural invariants, the Recovery
`xfail`, and the irony join — is a query/test pattern composed over the nine `MemoryCore`
operations already shipped and verified in Phases 3–6. The harness already exists: the Phase-3
keystone `tests/test_invariants.py` `_SpineMachine` (a `RuleBasedStateMachine` + an independent
shadow-dict oracle + a fixed colliding id/event pool + the two-subclass `Memory*`/`Ladybug*`
`.TestCase` dual-backend idiom) is the load-bearing pattern this phase **extends**, and the
`tests/conftest.py` `backend` fixture (`params=["memory","ladybug"]` + `importorskip`) is the
BACK-05 parametrization mechanism already in service across six other test files.

The work is therefore overwhelmingly *additive and pattern-following*: lift the Phase-6
operational-fold property (`tests/test_scope_at.py`) into the registered invariant set; add the
AGM/Hansson postulate assertions as either `@invariant`s on the spine machine or standalone
`@given` tests (D-06a, Claude's discretion); encode Recovery as a single deterministic
`@pytest.mark.xfail(strict=True)` counterexample; and demonstrate the irony join as ONE
`match_nodes("BeliefState", {})` round-trip filtered/joined in core Python (D-01). The two
genuinely-new design questions a planner must resolve — both small, both flagged as Claude's
discretion in CONTEXT — are (a) where the irony-join code lives (test helper vs. neutrally-named
core method, D-03a) and (b) whether each postulate rides the stateful machine or a `@given` test.

**Primary recommendation:** Extend the existing `_SpineMachine` in place (do NOT rewrite it),
add postulate `@invariant`s + standalone `@given` tests against the **independent shadow oracle**
(never against the code under test), lift the Phase-6 `fold` property into the conformance set,
encode Recovery as a deterministic per-mark `strict=True` xfail (there is NO global
`xfail_strict` in `pyproject.toml`, so `strict=True` MUST be on the mark itself), and compose the
irony join as one `match_nodes` scan → reuse the extractable `rows → tails` helper → inner-join on
`belief_id`. Keep every claim grounded in the read source — this phase's honesty is its whole
value.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The irony join is computed **uniformly over the generic `BackendPort`**, exactly like
  `query_scope` / `get_scope_at` / `get_impact` — NOT pushed into backend-specific Cypher. Shape:
  ONE `match_nodes("BeliefState", {})` round-trip → derive the active current tail per
  `(scope, belief)` in core Python (reuse `_order_key` + the `_current_tail` max + retracted-tail
  collapse) → keep `{scope_a, scope_b}` → inner-join on `belief_id` → emit rows where `value`
  differs. Identical code, both backends, parameterised. "Single query" = one port round-trip.
  Option B (a bespoke single-Cypher join) was **rejected** (narrow-port non-goal violation).
- **D-01a (one round-trip, not two `query_scope` calls):** Target a SINGLE `match_nodes` scan,
  then filter to the two scopes in Python. Likely refactor: extract `query_scope`'s steps 3–4
  (group-by-`belief_id` → per-group ordering-max → status filter) as a pure `rows → current tails`
  helper both `query_scope` and the irony join reuse — keeps the ONE `_order_key` contract
  single-sourced.
- **D-02:** Join on **`belief_id` directly**. The `research/ARCHITECTURE.md` irony-join Cypher
  (joins via `CURRENT_STATE`/`HOLDS` edges on `belief_id_logical`) is **SUPERSEDED** — none of
  those exist: current is DERIVED (no `CURRENT_STATE` pointer, no `HOLDS`), and there is no
  `belief_id_logical` (`belief_id` *is* the scope-independent proposition id; `scope_id` is a
  separate `BeliefState` field).
- **D-03:** The synthetic data is small and known, so the **expected divergent rows are computed
  directly in the test (plain Python)** and compared against the irony-join result. No
  second-backend implementation, no port widening. The in-memory backend is not required to
  satisfy "single query" but runs the SAME uniform core logic, so cross-backend parity holds.
- **D-03a (boundary — no narrative naming in core):** "Actor", "world", "irony", "dramatic irony"
  are NVM's framing; the core sees only *two scopes diverging on `belief_id`*. If the join lives
  in core it MUST be named neutrally (e.g. diverging-beliefs-between-two-scopes), never
  `irony`/`actor`. `WORLD_SCOPE_ID` already exists; an "actor" scope is just any non-world scope.
- **D-04:** Encode Recovery (`K ⊆ (K ÷ p) + p`) as a **deterministic, hand-built belief-base
  counterexample** asserting Recovery's conclusion, marked
  `@pytest.mark.xfail(strict=True, reason="AGM Recovery excluded — belief base (not closed set);
  Hansson; replaced by superseded-chain semantics")`. NOT a Hypothesis sweep, NOT a silent
  omission, NOT a bare `assert`. `strict=True` is the drift guard: if the engine ever satisfies
  Recovery, the test XPASSes → suite goes red.
- **D-05:** In Recovery's place, assert superseded-chain **replacement** (these PASS): after
  `contract(p)` then `revise(p, v')`, the chain reads `active(v) → retracted → active(v')`; the old
  value is NOT silently restored; the derived current resolves to `v'`; `get_revision_chain` still
  contains the contracted state. Keep distinct from temporal recoverability (`get_scope_at` /
  `get_revision_chain` is a separate, held property — do not conflate).
- **D-06:** FORMAL-01/02/03 build on the Phase-3 keystone `_SpineMachine` — same
  `RuleBasedStateMachine` + shadow-dict oracle + fixed id/event pools + the two-subclass
  `Memory*`/`Ladybug*` `.TestCase` dual-backend idiom. The shadow oracle IS the AGM belief base;
  postulates are asserted by comparing `query_scope` output against the oracle's derived-current
  set. BACK-05 is satisfied transversally by this parametrization, not as a separate step.
- **D-06a:** Single-operation postulates (Extensionality K*6, Vacuity K*4) MAY be plain `@given`
  property tests; the sequence-sensitive postulates (Success, Inclusion, Consistency) and the
  structural invariants ride the stateful machine. *(Claude's discretion.)*
- **D-07:** Relevance and Core-Retainment must be phrased against doxastica's **append-only
  superseded-chain contraction** (contract APPENDS a retracted state; `revise ≡ expand`; NO
  value-semantic consistency engine — only structural `SUPERSEDES` + `DEPENDS_ON`), NOT classical
  partial-meet remainder sets. Picks up the deferral flagged in `tests/test_cascade.py`.
- **D-08:** Add the full named structural-invariant set: `CURRENT_STATE` uniqueness phrased as the
  derived-current single-valued *theorem* (no pointer edge — it is the unique ordering-max under a
  unique `state_id` tiebreak); `get_scope_at ≡ replay` lifted from the Phase-6 Hypothesis property;
  world-scope no-contraction (already present as `world_contract_raises`, route into the registered
  set).

### Claude's Discretion

- Whether each AGM postulate is an `@invariant` on the spine machine vs. a standalone `@given`
  test (D-06a) — the oracle/comparison is the spec; the harness placement is open.
- The exact home of the irony-join code (a test-level helper vs. a neutrally-named core method),
  provided it is one round-trip (D-01a) and leaks no narrative naming into core (D-03a).
- Whether `get_scope_at ≡ replay` is re-expressed as a registered `@invariant` or the Phase-6
  property is re-run inside the conformance harness (D-08) — either satisfies FORMAL-03.
- The precise Recovery counterexample base (D-04), provided it is deterministic and documented.

### Deferred Ideas (OUT OF SCOPE)

- A bespoke single-Cypher irony join pushed into the ladybug backend (Option B) — rejected (D-01).
- Widening `BackendPort` with any belief-revision-aware query (`irony_join`, `current_states`, …).
- The runtime-dep audit, MIT license, mkdocs port-contract docs, CI 3.11/3.14 matrix + release
  pipeline — Phase 8 (PKG-02/03/04).
- AGM Closure (K*1) — dropped by construction (belief bases); not a test, not an xfail.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FORMAL-01 | AGM revision postulates (Success K*2, Inclusion K*3, Vacuity K*4, Consistency K*5, Extensionality K*6) green as Hypothesis stateful tests over op sequences | Postulate phrasings against the shadow oracle (see Architecture Patterns §AGM); `_SpineMachine` already drives revise/expand/contract with the oracle in lockstep — add `@invariant`/`@given` assertions comparing `query_scope` (the belief base B) to `_shadow_current` |
| FORMAL-02 | Hansson base-contraction postulates (Contraction Success, Inclusion, Relevance, Core-Retainment, Uniformity) green | Phrased against superseded-chain semantics (D-07); contract() body already appends a retracted state copying the prior value — the oracle's `(src, seq, value, status)` entry list models exactly this |
| FORMAL-03 | Structural-invariant suite green: `CURRENT_STATE` uniqueness, chain immutability, `get_scope_at ≡ replay`, world-scope no-contraction | `current_is_total_single_valued_and_chain_tail` (uniqueness theorem) + `chain_is_immutable` already present; lift `_ScopeAtMachine.scope_at_equals_fold_for_every_cut` (Phase 6) + route `world_contract_raises` into the registered set |
| FORMAL-04 | AGM Recovery excluded — loud strict xfail + positive superseded-chain replacement tests | Deterministic counterexample + `@pytest.mark.xfail(strict=True)` (no global `xfail_strict` exists — must be per-mark); D-05 positives over `get_revision_chain` |
| FORMAL-05 | Irony join on synthetic data — two scopes diverging on `belief_id`, one round-trip | ONE `match_nodes("BeliefState", {})` + the extractable `rows → tails` helper + plain-Python expected oracle (D-01/D-02/D-03) |
| BACK-05 | The suite runs as a backend conformance suite parameterised over every registered backend | Satisfied transversally by the `conftest.py` fixture + the two-subclass `.TestCase` idiom — NOT a discrete task; the parametrization IS the requirement |

## Architectural Responsibility Map

This is a pure-Python library; "tiers" map to the layered seam architecture, not network tiers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| AGM/Hansson postulate assertions | Test harness (`tests/`) | — | Postulates are properties OF the core, asserted against an independent oracle; no production code |
| Structural invariants | Test harness (`tests/`) | — | `@invariant`s over the `BackendPort`-visible state; the shadow oracle is the spec |
| Recovery xfail + superseded-chain positives | Test harness (`tests/`) | — | A documented negative result + its replacement; pure test artifacts |
| Irony join (divergence computation) | Core (`MemoryCore`) OR test helper | `BackendPort` (one `match_nodes`) | Derived query over the generic port (D-01) — same tier as `query_scope`; D-03a forbids narrative naming if it lands in core |
| `rows → tails` helper extraction (D-01a) | Core (`core.py`) | — | Single-sources the `_order_key` group-by-max so `query_scope` and the join cannot drift |
| Backend conformance parametrization | Test fixtures (`conftest.py` + `.TestCase` subclasses) | Both backends | The fixture + subclass idiom already exists and is the BACK-05 mechanism |

## Standard Stack

Everything is already installed and verified in the running repo. No new packages.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hypothesis | `>=6.155` (installed line 6.155.2 per CLAUDE.md) | The property/stateful test engine — `RuleBasedStateMachine`, `@rule`/`@invariant`/`@precondition`/`@initialize`, `Bundle`, `strategies` | Already the keystone engine for `test_invariants.py` + `test_scope_at.py`; shrinking minimal failing op sequences is what makes the AGM claim credible [VERIFIED: pyproject.toml dependency-groups + tests/test_invariants.py imports] |
| pytest | `>=8.0.0` (9.x resolves) | Test runner + `@pytest.mark.xfail(strict=True)` for the Recovery exclusion | Already the runner; `xfail(strict=True)` is the D-04 drift guard [VERIFIED: pyproject.toml] |
| pydantic | `>=2.11,<3` | Frozen `BeliefState`/`Scope`/`BeliefFilter` value objects the assertions compare | The sole required runtime dep; models already shipped [VERIFIED: src/doxastica/models.py] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ladybug (`doxastica[ladybug]` extra) | `>=0.17,<0.18` | The reference backend the conformance suite runs the IDENTICAL tests against | Always present in the dual-backend `.TestCase`/fixture; `importorskip` SKIPS (not fails) when absent [VERIFIED: pyproject.toml optional-dependencies + tests/conftest.py] |
| basedpyright | `>=1.38` strict | Strict typing over the new test code (the `.TestCase` dynamic-attr ignores are an established narrow pattern) | The new test files inherit the same `# pyright: ignore[reportUnknownMemberType,...]` pattern at the `.TestCase` boundary [VERIFIED: tests/test_invariants.py:351-355] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extending `_SpineMachine` | A fresh standalone postulate machine | Rejected by D-06 — duplicates the oracle/pool/teardown plumbing and risks the two oracles drifting; extend in place |
| Property-based Recovery xfail (Hypothesis sweep) | Deterministic single counterexample xfail | Rejected by D-04 — a strict XPASS would fire on mere absence-of-counterexample in N examples, which is not a proof; use a hand-built deterministic base |
| Irony join as one Cypher query in the ladybug backend | Uniform core-Python join over `match_nodes` | Rejected by D-01 — adds backend-specific query surface, breaks the narrow-port non-goal |

**Installation:** No new install. The full dev environment is already provisioned:
```bash
uv sync                       # installs the dev group (hypothesis, pytest, basedpyright, ruff)
uv sync --extra ladybug       # adds the ladybug reference backend so the Ladybug* TestCases run
```

**Version verification:** All versions are pinned and resolved in the running repo (CLAUDE.md
records hypothesis 6.155.2, pytest 9.0.3, pydantic 2.13.4, ladybug 0.17.1 verified on PyPI). No
ecosystem registry lookup is needed — this phase installs nothing new.

## Package Legitimacy Audit

> Not applicable in the install sense — Phase 7 adds **zero** new packages. All dependencies
> (hypothesis, pytest, pydantic, ladybug, basedpyright, ruff) are already declared, resolved, and
> in active use across Phases 1–6. The `ladybug` legitimacy (vs. the `ladybugdb` slopsquat token,
> which is confirmed absent from PyPI) was settled in Phase 1/2 and is recorded in CLAUDE.md and
> STATE.md.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| hypothesis | PyPI | mature | high | github.com/HypothesisWorks/hypothesis | OK | Already installed (dev group) |
| pytest | PyPI | mature | very high | github.com/pytest-dev/pytest | OK | Already installed (dev group) |
| pydantic | PyPI | mature | very high | github.com/pydantic/pydantic | OK | Already installed (required dep) |
| ladybug | PyPI | 0.17.1 (2026-06-02) | n/a | github.com/LadybugDB/ladybug | OK | Already installed (optional extra) — `ladybugdb` slopsquat confirmed absent |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                       Phase 7 conformance suite (the M0 exit gate)
                       ─────────────────────────────────────────────

   pytest collects
   .TestCase classes
        │
        ▼
  ┌──────────────────────────────────────────────────────────┐
  │  Two-subclass dual-backend idiom (D-06, BACK-05)          │
  │  Memory<Machine>.TestCase  +  Ladybug<Machine>.TestCase   │
  │  (Ladybug SKIPS via importorskip when driver absent)      │
  └──────────────────────────────────────────────────────────┘
        │ each example                          │ each example
        ▼                                        ▼
  ┌──────────────────┐                    ┌──────────────────────┐
  │ InMemoryBackend  │  ← the AGM oracle  │ LadybugBackend        │
  │ (zero-dep)       │    substrate       │ (bounded :memory: DB) │
  └──────────────────┘                    └──────────────────────┘
        │                                        │
        └──────────────┬─────────────────────────┘
                       ▼
              ┌──────────────────┐      drives        ┌─────────────────────────┐
              │   MemoryCore     │ ◄───────────────── │ RuleBasedStateMachine    │
              │ (9 shipped ops)  │  revise/expand/    │  @rule write ops         │
              └──────────────────┘  contract           │  @initialize fresh core  │
                       │                                │  teardown closes ladybug │
                       │ query_scope / _current /       └─────────────────────────┘
                       │ get_revision_chain /                     │ mirrors each op
                       │ get_scope_at / match_nodes               ▼
                       │                                ┌─────────────────────────┐
                       ▼                                │ INDEPENDENT shadow oracle│
              ┌──────────────────────────┐  compared   │ self.entries: per        │
              │ @invariant + @given       │ ◄────────── │ (scope,belief) → [(src,  │
              │ postulate/invariant checks │             │ seq, value, status/kind)]│
              │  AGM K*2..K*6              │             │ (recomputes the winner   │
              │  Hansson 5 postulates     │             │  by its OWN _order_key —  │
              │  4 structural invariants  │             │  never calls the SUT)    │
              └──────────────────────────┘             └─────────────────────────┘

   Separate artifacts (same fixture, NOT on the spine machine):
   ┌──────────────────────────────┐   ┌────────────────────────────────────────┐
   │ Recovery xfail (D-04)        │   │ Irony join (D-01/D-05)                   │
   │ deterministic counterexample │   │ ONE match_nodes("BeliefState",{}) scan → │
   │ @xfail(strict=True)          │   │ rows→tails helper → keep {scope_a,b} →   │
   │ + superseded-chain positives │   │ inner-join on belief_id → value differs  │
   │   over get_revision_chain    │   │ vs. plain-Python expected oracle         │
   └──────────────────────────────┘   └────────────────────────────────────────┘
```

The data flow to trace: a Hypothesis example spins up a fresh backend + `MemoryCore` (`@initialize`),
drives a sequence of `revise`/`expand`/`contract` `@rule`s while mirroring each into the
independent shadow oracle, and after every step asserts that the core's *observed* belief base
(`query_scope` / `_current` / `get_scope_at`) agrees with the oracle's *independently computed*
derived current — which is exactly the AGM/Hansson postulate or structural invariant being proved.

### Recommended Project Structure

```
tests/
├── conftest.py                # EXISTING — the backend fixture (BACK-05 mechanism, do not change)
├── test_invariants.py         # EXTEND — add AGM/Hansson @invariant/@given checks to _SpineMachine
│                              #   (FORMAL-01/02/03; D-06/D-08)
├── test_scope_at.py           # EXISTING Phase-6 fold property — LIFT into the conformance set
│                              #   (D-08: get_scope_at ≡ replay) or re-reference it
├── test_recovery_xfail.py     # NEW — the strict-xfail Recovery counterexample +
│                              #   superseded-chain positives (FORMAL-04; D-04/D-05)
└── test_irony_join.py         # NEW — the two-scope divergence demo (FORMAL-05; D-01..D-03)

src/doxastica/
└── core.py                    # OPTIONAL small changes only:
                               #   - extract `rows → current tails` helper (D-01a)
                               #   - OPTIONAL neutrally-named divergence method (D-03a)
                               #   (a test-level helper is an acceptable alternative to both)
```

### Pattern 1: The dual-backend `.TestCase` idiom (D-06, BACK-05) — the parametrization

**What:** Two subclasses of a `_*Machine(RuleBasedStateMachine)` bind `backend_kind` to
`"memory"` / `"ladybug"`; `_make_backend` builds the matching throwaway backend per example
(`importorskip` SKIPS ladybug when absent); each subclass's auto-generated `.TestCase` is the
pytest entry point, with `settings` attached.
**When to use:** Every stateful machine in this phase. This IS the BACK-05 conformance mechanism —
no separate parametrization step.
**Example:**
```python
# Source: tests/test_invariants.py:132-148, 335-355 (verbatim established pattern)
def _make_backend(self) -> BackendPort:
    if self.backend_kind == "ladybug":
        lb = pytest.importorskip("ladybug")  # SKIP, not fail, when driver absent
        from doxastica.backends.ladybug import LadybugBackend
        db = lb.Database(max_db_size=2**30)   # 1 GiB cap — Hypothesis makes one DB PER EXAMPLE
        return LadybugBackend(lb.Connection(db), namespace="dx", owns_conn=True)
    from doxastica.backends.memory import InMemoryBackend
    return InMemoryBackend()

_SETTINGS = settings(max_examples=50, stateful_step_count=20, deadline=None)

class MemorySpineMachine(_SpineMachine):
    backend_kind = "memory"
class LadybugSpineMachine(_SpineMachine):
    backend_kind = "ladybug"

MemorySpineMachine.TestCase.settings = _SETTINGS   # pyright: ignore[reportUnknownMemberType]
LadybugSpineMachine.TestCase.settings = _SETTINGS  # pyright: ignore[reportUnknownMemberType]
MemorySpineTest = MemorySpineMachine.TestCase      # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
LadybugSpineTest = LadybugSpineMachine.TestCase    # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
```
For non-stateful (function) tests, consume the `conftest.py` `backend` fixture instead — it runs
each test once per backend, so a comparison to an expected literal already proves cross-backend
parity (`tests/test_scope_at.py`, `tests/test_cascade.py` precedent).

### Pattern 2: The INDEPENDENT shadow oracle (the anti-tautology rule — the whole point)

**What:** The oracle (`self.entries` + `_shadow_current` / `fold`) recomputes the derived current
from its OWN `(source_event_id_str, append_seq)` winner selection — `append_seq` is the monotonic
stand-in for the core-minted `state_id` tiebreak. It MUST NOT call `query_scope`, `_current`,
`_current_tail`, `get_scope_at`, or any production reconstruction helper, or the proof becomes a
restatement, not a cross-check.
**When to use:** Every postulate/invariant assertion. The oracle IS the AGM belief base B; the
postulate is the comparison between B (oracle) and the core's observed base.
**Example:**
```python
# Source: tests/test_invariants.py:170-183 (the oracle's independent winner selection)
def _shadow_current(self, scope_id: str, belief_id: str) -> tuple[bool, Any]:
    entries = self.entries.get((scope_id, belief_id))
    if not entries:
        return (False, None)
    _src, _seq, value, status = max(entries, key=lambda e: (e[0], e[1]))  # mirrors _order_key
    if status == "retracted":
        return (False, None)   # retracted ordering-max tail ⇒ no active current (D-05)
    return (True, value)
```
The cross-check discipline is also enforced via the public history surface: `_chain_tail`
(`test_invariants.py:87-104`) recomputes the tail from `get_revision_chain` rather than reusing
`_current`, making the agreement real rather than tautological. **Reuse this discipline for every
new postulate.**

### Pattern 3: AGM revision postulates against the belief-base oracle (FORMAL-01)

The shadow oracle's derived-current set per scope IS the belief base B. Phrase each postulate as a
comparison between `query_scope(scope, BeliefFilter())` (the observed base, the AGM `K`) and the
oracle. `revise(scope, p, v)` is `K * (p=v)`; `expand` is `K + (p=v)`; `revise ≡ expand` at the
core (no value-semantic consistency engine — the Kumiho memory model), so K*3/K*4 collapse to
expansion identities, which is the correct phrasing for belief bases.

| Postulate | Classical form (SEP) | doxastica phrasing (against the base oracle) | Harness |
|-----------|----------------------|----------------------------------------------|---------|
| **K*1 Closure** | `K*p = Cn(K*p)` | **DROPPED by construction** — belief bases are NOT deductively closed (DATA-05). Not a test, not an xfail. | — |
| **K*2 Success** | `p ∈ K*p` | After `revise(scope, p, v)`, `p` is present in `query_scope(scope)` with `value == v` (the current tail decodes to `v`). | `@invariant` / `@given` |
| **K*3 Inclusion** | `K*p ⊆ K+p` | Since `revise ≡ expand` (D-04, no consistency engine), `revise` adds exactly the new tail and removes nothing pre-existing except the superseded prior tail of the SAME `belief_id` — the post-base ⊆ the expand-base. Phrase: the set of `(belief_id)` keys after `revise` equals the prior keys ∪ `{p}`. | `@invariant` |
| **K*4 Vacuity** | If `¬p ∉ K` then `K*p = K+p` | With no negation/consistency machinery, revising a `belief_id` NOT currently asserted equals expanding it: `query_scope` after `revise` on a fresh `belief_id` = prior base ∪ `{(p, v)}`. | `@given` (single-op, D-06a) |
| **K*5 Consistency** | `K*p` consistent if `p` consistent | "Consistency" for a base = the structural invariant that `query_scope` is single-valued (exactly one current tail per `(scope, belief)`) — already proved by `current_is_total_single_valued_and_chain_tail`. Phrase explicitly as: no `belief_id` appears twice in `query_scope`. | `@invariant` (reuse keystone) |
| **K*6 Extensionality** | If `⊢ p ↔ q` then `K*p = K*q` | The core treats `belief_id` as an opaque identity and `value` opaquely; "logically equivalent inputs" = identical `(belief_id, value)` writes via either `revise` or `expand` produce identical bases. Phrase: `revise(s,p,v)` and `expand(s,p,v)` yield byte-identical `query_scope` projections. | `@given` (single-op, D-06a) |

> **CITED:** AGM postulate forms K*1–K*6 confirmed against the Stanford Encyclopedia of Philosophy,
> *Logic of Belief Revision* [CITED: plato.stanford.edu/entries/logic-belief-revision/]. The
> doxastica phrasings are the locked re-statements for belief bases + `revise ≡ expand` (DATA-05,
> D-04, the Kumiho memory model).

### Pattern 4: Hansson base-contraction postulates against superseded-chain semantics (FORMAL-02, D-07)

doxastica's `contract(scope, p, e)` APPENDS a `retracted` state copying the prior stored value
verbatim (`core.py:382-427`) — it never removes a node. So the Hansson postulates are phrased over
the *observed base* (`query_scope`, which drops a belief whose ordering-max tail is retracted) and
the *immutable chain* (`get_revision_chain`, which retains everything). `A` = the base before
contraction; `A÷p` = the base after.

| Postulate | Classical form (SEP) | doxastica phrasing (superseded-chain) | Harness |
|-----------|----------------------|----------------------------------------|---------|
| **Contraction Success** | If `p ∉ Cn(∅)` then `p ∉ Cn(A÷p)` | After `contract(scope, p, e)` (with `e` newer than `p`'s current tail), `p` is ABSENT from `query_scope(scope)` (its tail is now retracted). | `@invariant` (gate on an asserted key, like the existing `contract` rule) |
| **Inclusion** | `A÷p ⊆ A` | Every `belief_id` present after the contract was present before — contraction adds no NEW asserted belief (it only retracts `p`). Phrase: `keys(query_scope after) ⊆ keys(query_scope before)`. | `@invariant` |
| **Relevance** | removed `q` must contribute to deriving `p` | No value-semantic derivation engine (D-07): the ONLY belief removed by `contract(p)` is `p` ITSELF (its retracted tail). Phrase: the symmetric difference of the bases is exactly `{p}` — nothing irrelevant is lost. This is the superseded-chain re-statement of Relevance. | `@invariant` |
| **Core-Retainment** | if `q` removed then `q` helped derive `p` | Same engine-free re-statement: any `belief_id` whose current tail changed across the contract is exactly `p` (no collateral retraction). Phrase: `∀ belief_id ≠ p`, the current tail is byte-identical before and after `contract(p)`. | `@invariant` |
| **Uniformity** | identical derivational role ⇒ identical contraction | With opaque values and no derivation, two `contract` calls on the SAME `(scope, belief_id)` at ordering-equivalent events produce identical bases (determinism). Phrase: contracting the same key twice is idempotent at the base level (the second is a vacuous no-op per D-05). | `@given` / `@invariant` |

**Note for the planner:** Because there is no consistency/derivation engine (Kumiho memory model,
CLAUDE.md), Relevance and Core-Retainment collapse to the same structural claim — *contraction is
surgical: it retracts exactly the named belief and nothing else*. The honest phrasing is to assert
the symmetric-difference-is-`{p}` property; do NOT fabricate a derivation relation the core does
not have. This is the explicit point of D-07 and the `test_cascade.py` deferral note (line 13-14).

### Pattern 5: The Recovery strict-xfail (FORMAL-04, D-04) — a documented negative result

**What:** A deterministic, hand-built belief-base counterexample that ASSERTS Recovery's
conclusion (`K ⊆ (K÷p)+p`), marked `@pytest.mark.xfail(strict=True, reason=...)`. The assertion
FAILS against the correct (Recovery-violating) engine → the xfail is GREEN. If the engine ever
drifts toward closed belief sets and satisfies Recovery, the assertion PASSES → strict xfail
XPASSes → suite goes RED.
**When to use:** Exactly once, as a standalone test (NOT a Hypothesis sweep — D-04).
**Critical config finding:** `pyproject.toml` `[tool.pytest.ini_options]` has `addopts = "-v"` and
**NO `xfail_strict = true`**. Therefore `strict=True` MUST be on the mark itself — a bare
`@pytest.mark.xfail` would silently pass on XPASS, defeating the drift guard.
**Example shape (the deterministic base):**
```python
# The classic Recovery counterexample for belief BASES (Hansson): A = {p, q}, contract p,
# then expand p back — q is NOT recovered because a base is not closed.
import pytest, uuid
from doxastica import MemoryCore

@pytest.mark.xfail(
    strict=True,
    reason="AGM Recovery excluded — belief base (not closed set); Hansson; "
           "replaced by superseded-chain semantics",
)
def test_recovery_does_not_hold_for_belief_bases() -> None:
    core = MemoryCore.in_memory()
    e = lambda: uuid.uuid7()
    core.revise("s", "p", "vp", e())
    core.revise("s", "q", "vq", e())          # base A = {p:vp, q:vq}
    core.contract("s", "p", e())              # A ÷ p   (p retracted; q untouched)
    core.revise("s", "p", "vp", e())          # (A ÷ p) + p   (p re-asserted)
    base = {s.belief_id: s.value for s in core.query_scope("s", BeliefFilter())}
    # Recovery would require A ⊆ (A÷p)+p — i.e. q still present at its ORIGINAL value AND nothing
    # lost. The assertion below is what Recovery DEMANDS; it holds here (q was never touched), so
    # pick a base where contraction's cascade WOULD drop a dependent to make the xfail bite, OR
    # assert the stronger closed-set Recovery claim the base deliberately fails. See Open Q1.
    assert base == {"p": "vp", "q": "vq"}      # the Recovery conclusion to be DENIED
```
> **OPEN QUESTION (planner must resolve, see Open Questions §1):** The naive `{p, q}` base does NOT
> actually violate Recovery because `q` is independent and survives — making the assertion PASS and
> the strict-xfail XPASS (red) erroneously. The counterexample must be constructed so the
> Recovery-demanded conclusion genuinely FAILS against the superseded-chain engine. The honest
> belief-base Recovery failure is: after `contract(p)` then `revise(p, v')` with a NEW value, the
> chain reads `active(vp) → retracted → active(v')` and the OLD value `vp` is gone from the
> base — Recovery (which for closed sets would restore the pre-contraction `K`) is denied because
> the superseded chain does not resurrect superseded content. Assert the closed-set Recovery
> conclusion (`base after == base before contraction`) which the engine correctly DENIES.

### Pattern 6: Superseded-chain replacement positives (FORMAL-04, D-05) — Recovery's replacement

**What:** PASSING tests that assert the behaviour that REPLACES Recovery: after `contract(p)` then
`revise(p, v')`, (a) `get_revision_chain(p)` reads `active(v) → retracted → active(v')` in order,
(b) the old value is NOT restored, (c) the derived current resolves to `v'`, (d) the contracted
state is still in the chain (append-only — nothing deleted).
**Example:**
```python
# Source pattern: tests/test_backend_parity.py value-round-trip + core.py contract/get_revision_chain
def test_superseded_chain_replaces_recovery(backend: BackendPort) -> None:
    core = MemoryCore(backend)
    e = lambda: uuid.uuid7()
    core.revise("s", "p", "v", e())
    core.contract("s", "p", e())
    core.revise("s", "p", "vprime", e())
    chain = core.get_revision_chain("p")             # cross-scope, ordering-sorted
    statuses = [s.status.value for s in chain]
    assert statuses == ["active", "retracted", "active"]   # the chain reads as documented (D-05)
    assert chain[-1].value == "vprime"                      # current resolves to v', not v
    assert any(s.status.value == "retracted" for s in chain)  # contracted state retained (append-only)
    base = {s.belief_id: s.value for s in core.query_scope("s", BeliefFilter())}
    assert base.get("p") == "vprime"                        # old value NOT silently restored
```
Runs over the `backend` fixture (both backends). Keep DISTINCT from temporal recoverability
(`get_scope_at`) — that is a separate, held property (D-05), not Recovery.

### Pattern 7: The irony join — two scopes diverging on `belief_id`, one round-trip (FORMAL-05, D-01)

**What:** ONE `match_nodes("BeliefState", {})` scan → derive the active current tail per
`(scope, belief)` (reuse `_order_key` max + `_is_active_tail` collapse — ideally via the extracted
`rows → tails` helper, D-01a) → keep only the two named scopes → inner-join on `belief_id` → emit
rows where the decoded `value` differs.
**When to use:** Once, as the FORMAL-05 demonstration on synthetic data.
**Boundary (D-03a):** if it lands in core, name it neutrally (e.g.
`diverging_beliefs(scope_a, scope_b)`), never `irony`/`actor`/`world_truth`. A test-level helper is
an acceptable alternative.
**Example shape:**
```python
# ONE port round-trip = the "single query" meaning (D-01); identical on both backends.
def diverging_beliefs(core: MemoryCore, scope_a: str, scope_b: str) -> list[tuple[str, Any, Any]]:
    rows = core._backend.match_nodes("BeliefState", {})         # ONE scan (D-01a)
    # reuse the extracted rows->tails helper to get the active current tail per (scope, belief)
    tails_a = _current_tails_for_scope(rows, scope_a)            # {belief_id: tail}
    tails_b = _current_tails_for_scope(rows, scope_b)
    out: list[tuple[str, Any, Any]] = []
    for belief_id in tails_a.keys() & tails_b.keys():            # inner join on belief_id (D-02)
        va = MemoryCore._decode_value(tails_a[belief_id]["value"])
        vb = MemoryCore._decode_value(tails_b[belief_id]["value"])
        if va != vb:                                            # divergence
            out.append((belief_id, va, vb))
    return out
```
The test computes the EXPECTED divergent rows in plain Python from the known synthetic writes and
compares (D-03). The `_current_tails_for_scope` helper is the D-01a extraction of
`query_scope`'s steps 3–4 (`core.py:602-610`).

### Anti-Patterns to Avoid

- **Oracle calling the SUT.** Never let the shadow oracle / `fold` call `query_scope`, `_current`,
  `get_scope_at`, etc. — that turns the proof into a tautology. The oracle must have its own
  winner selection (`test_invariants.py:170-183`, `test_scope_at.py:367-390`).
- **Bare `@pytest.mark.xfail` for Recovery.** No global `xfail_strict` exists; a bare xfail
  silently passes on XPASS, killing the drift guard. Always `strict=True` on the mark (D-04).
- **A Hypothesis sweep for Recovery.** A strict XPASS would fire on absence-of-counterexample in N
  examples, which is not a proof (D-04). Deterministic counterexample only.
- **Two `query_scope` calls or a second `match_nodes` for the irony join.** That is two round-trips,
  missing the "single query" goal (D-01a). One `match_nodes("BeliefState", {})` scan, filter in
  Python.
- **Narrative naming in core.** `irony`, `actor`, `world_truth`, `dramatic_irony` are the leak the
  seam exists to prevent (D-03a, CLAUDE.md boundary). Name any core method neutrally.
- **Rewriting `_SpineMachine`.** Extend it in place (D-06). A parallel machine duplicates the
  oracle/pool/teardown and risks divergence.
- **Fabricating a derivation relation for Relevance/Core-Retainment.** The core has no
  value-semantic consistency engine (D-07); phrase those postulates as the surgical
  symmetric-difference-is-`{p}` property, not a remainder-set computation.
- **Pre-filtering to `active` before the per-belief max.** The retracted-tail collapse depends on
  taking the max over ALL statuses first (`core.py:208-248`, Pitfall 2 in `query_scope`); the
  oracle mirrors this. New assertions must respect it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stateful op-sequence generation + shrinking | A hand-written loop of random ops | Hypothesis `RuleBasedStateMachine` (already in use) | Shrinking minimal failing op sequences is what makes the AGM claim credible; hand-rolled sequences don't shrink |
| The derived-current ordering | A second sort/max in the test | Reuse `_order_key` + `_current_tail` / `_is_active_tail` (`core.py:86-112, 208-248`) | The ONE ordering contract is single-sourced precisely so the read surface and the spine cannot desync (IN-03) |
| The belief-base oracle | A new shadow model | Extend `_SpineMachine.entries` / `_shadow_current` (`test_invariants.py:121-183`) | D-06: one oracle, kept independent of the SUT, already models out-of-order/colliding event ids correctly (Pitfall 6) |
| Backend parametrization | `@pytest.mark.parametrize` over backend names by hand | The `conftest.py` `backend` fixture + the two-subclass `.TestCase` idiom | BACK-05 IS this mechanism; it already handles `importorskip` skip-not-fail + per-example throwaway DBs |
| `get_scope_at ≡ replay` oracle | A new replay function | Lift `_ScopeAtMachine.fold` (`test_scope_at.py:367-390`) | The Phase-6 operational-fold oracle is already the independent replay; D-08 lifts it into the conformance set |
| Ladybug per-example DB cleanup | Manual handle tracking | The established `_make_backend` bounded-`max_db_size` + `teardown` `getattr(...,'close')` pattern | An unclosed owning handle per example exhausts the native layer; the cap prevents the ~8 TiB mmap reservation blowout (`test_invariants.py:140-148, 317-328`) |

**Key insight:** This phase is 95% reuse. The harness, the oracle discipline, the parametrization,
the ordering contract, the value codec, and even the operational-fold replay all already exist and
are read in this research. The temptation to "build a proper test framework" is the trap —
*extend* the keystone and *compose* the existing helpers.

## Common Pitfalls

### Pitfall 1: The Recovery xfail erroneously XPASSes (goes red against correct code)
**What goes wrong:** A naive `{p, q}` Recovery counterexample doesn't actually violate Recovery
(independent `q` survives the `contract(p)` + re-expand), so the Recovery-demanded assertion PASSES,
the strict-xfail XPASSes, and the suite goes RED against a correct engine — the exact opposite of
the intent.
**Why it happens:** Recovery (`K ⊆ (K÷p)+p`) is only interesting where contraction loses something
that re-expansion should restore. For belief bases with no derivation engine, the loss is the
SUPERSEDED VALUE of the same belief, not a collateral belief.
**How to avoid:** Build the counterexample so the Recovery-demanded conclusion genuinely fails:
assert the closed-set Recovery claim (`base after contract+re-expand == base before contraction`)
with a re-expand to a NEW value — the superseded chain correctly DENIES it (the old value is gone),
so the assertion fails → xfail green. See Open Question §1 for the exact base.
**Warning signs:** The new Recovery test passes (not xfails) on first run; an `XPASS` in the report.

### Pitfall 2: The shadow oracle silently mirrors the implementation (tautology)
**What goes wrong:** A new postulate `@invariant` computes "expected" by calling `query_scope` or
`_current` — so it compares the code to itself and would pass even if both were wrong.
**Why it happens:** It is the path of least resistance; the SUT is right there on `self.core`.
**How to avoid:** Compute expected ONLY from `self.entries` via the oracle's own
`(source_event_id_str, append_seq)` winner selection. The `_chain_tail` cross-check
(`test_invariants.py:87-104`) is the reference for recomputing via the PUBLIC history surface
independently.
**Warning signs:** The assertion references `self.core.query_scope`/`_current` on BOTH sides; the
test cannot fail when a deliberate bug is injected into `_current`.

### Pitfall 3: `strict=True` omitted on the Recovery xfail (drift guard disabled)
**What goes wrong:** Without `xfail_strict` globally (it is absent — verified) and without
`strict=True` on the mark, an XPASS is reported as a PASS, so the engine could silently drift to
satisfying Recovery and nobody would notice.
**Why it happens:** Assuming pytest defaults to strict, or copying a non-strict xfail from
elsewhere.
**How to avoid:** Put `strict=True` directly on `@pytest.mark.xfail` (D-04). Optionally also
consider `xfail_strict = true` in `[tool.pytest.ini_options]`, but the per-mark flag is the locked
requirement.
**Warning signs:** No `strict=` in the mark; the report shows `XPASS` without failing.

### Pitfall 4: Ladybug native-handle / mmap exhaustion in stateful machines
**What goes wrong:** Hypothesis runs dozens of examples per test, each building a fresh ladybug
in-memory DB; the default ~8 TiB virtual-address reservation per DB exhausts the process address
space ("Buffer manager exception: Mmap … failed"), or unclosed owning handles leak the native
resource.
**Why it happens:** The `conftest.py` fixture creates ONE DB per test and never hits this; the
stateful machine creates many.
**How to avoid:** Reuse the established pattern verbatim: `lb.Database(max_db_size=2**30)` in
`_make_backend` and the `teardown` `getattr(self._be, 'close', None)` guard
(`test_invariants.py:140-148, 317-328`). Any NEW stateful machine in this phase MUST copy both.
**Warning signs:** Mmap/Buffer-manager exceptions; native memory growth across examples; ladybug
tests pass solo but fail in the full suite.

### Pitfall 5: Conflating Recovery (the excluded postulate) with temporal recoverability (a held property)
**What goes wrong:** Treating `get_scope_at`/`get_revision_chain` "you can reconstruct the past" as
if it satisfies AGM Recovery — they are unrelated. Recovery is a postulate about contraction +
re-expansion restoring `K`; temporal recoverability is structural history access.
**Why it happens:** Both use the word "recover".
**How to avoid:** Keep the Recovery xfail (postulate) and the superseded-chain positives (D-05)
clearly separate from the Phase-6 `get_scope_at` property. State it in the test docstrings (D-05).
**Warning signs:** A "Recovery" test that calls `get_scope_at`; documentation claiming Recovery is
satisfied via time-travel.

### Pitfall 6: Colliding `source_event_id` pool dropped when extending the oracle
**What goes wrong:** New rules mint a fresh `uuid7()` per op instead of drawing from the small
fixed pool, so the `(source_event_id, state_id)` tiebreak is never exercised — the proof silently
weakens to "every event id is unique," missing out-of-order/intra-ms-collision bugs.
**Why it happens:** A fresh `uuid7()` is the obvious thing to write.
**How to avoid:** Draw `source_event_id` from `_EVENT_POOL` (`st.sampled_from(_EVENT_POOL)`) in
every new write rule, as the existing rules do (`test_invariants.py:62-66, 82-84`). The colliding
pool is the whole point of the tiebreak coverage.
**Warning signs:** New rules use `uuid.uuid7()` directly; the tiebreak branch in `_order_key` is
never covered; a contraction recorded against an earlier event "winning" is never tested.

## Runtime State Inventory

> Not a rename/refactor/migration phase. The only candidate production change is an OPTIONAL
> `rows → tails` helper extraction (D-01a) and/or an OPTIONAL neutrally-named divergence method
> (D-03a) — both small, both behaviour-preserving, both optional (a test-level helper suffices).
> No stored data, live service config, OS-registered state, secrets, or build artifacts are
> renamed or migrated. **None found in any category — verified by reading every source file in
> `src/doxastica/` and the full test suite.**

## Code Examples

All examples are drawn from the read repo source (authoritative for THIS codebase).

### The contract() body the Hansson postulates are phrased against (append-only retracted copy)
```python
# Source: src/doxastica/core.py:382-427 (verbatim semantics)
def contract(self, scope_id, belief_id, source_event_id) -> None:
    if scope_id == WORLD_SCOPE_ID:                      # D-03 structural guard, FIRST
        raise WorldScopeContractionError(...)
    with self._backend.unit_of_work():
        prior = self._current(scope_id, belief_id)      # probe BEFORE any write
        if prior is None:
            return None                                 # D-05 vacuity: true silent no-op
        self._ensure_scope(scope_id)
        self._append_state(                             # append a RETRACTED state...
            scope_id, belief_id,
            prior["value"],                             # ...copying the prior STORED value verbatim
            source_event_id, Status.retracted, prior,   # lays SUPERSEDES new(retracted) -> prior
        )
```

### The derived-current selection the oracle must mirror (ordering-max + retracted collapse)
```python
# Source: src/doxastica/core.py:86-112, 208-248
def _order_key(state):                                  # the ONE ordering contract (IN-03)
    return (str(state["source_event_id"]), str(state["state_id"]))

def _is_active_tail(tail):                              # the ONE retracted-tail-is-absent rule
    return tail["status"] != Status.retracted.value

def _current_tail(self, scope_id, belief_id):          # status-AGNOSTIC ordering-max
    states = self._backend.match_nodes("BeliefState", {"scope_id": scope_id, "belief_id": belief_id})
    return max(states, key=_order_key) if states else None

def _current(self, scope_id, belief_id):               # active current (None if tail retracted)
    tail = self._current_tail(scope_id, belief_id)
    return tail if tail and _is_active_tail(tail) else None
```

### query_scope steps 3–4 — the D-01a `rows → tails` extraction candidate
```python
# Source: src/doxastica/core.py:602-610 (the steps to extract as a shared helper)
by_belief: dict[str, dict[str, Any]] = {}
for row in rows:                                        # rows = match_nodes scan, filtered to scope
    current = by_belief.get(row["belief_id"])
    if current is None or _order_key(row) > _order_key(current):
        by_belief[row["belief_id"]] = row              # per-belief ordering-max (status-agnostic)
tails = list(by_belief.values())
tails = [t for t in tails if Status(t["status"]) in allowed]   # status filter AFTER the max
```

### The `@invariant` shape (checked after every step) the new postulates follow
```python
# Source: tests/test_invariants.py:258-315 (the keystone invariant; new postulates mirror it)
@invariant()
def current_is_total_single_valued_and_chain_tail(self) -> None:
    for scope_id in _SCOPE_POOL:
        for belief_id in _BELIEF_POOL:
            has_current, expected = self._shadow_current(scope_id, belief_id)  # oracle, independent
            current = self.core._current(scope_id, belief_id)                  # SUT
            if not has_current:
                assert current is None
                continue
            assert current is not None
            assert MemoryCore._decode_value(current["value"]) == expected
            tail = _chain_tail(self.core, scope_id, belief_id)                 # independent recompute
            assert tail is not None and tail["state_id"] == current["state_id"]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `research/ARCHITECTURE.md` irony join via `CURRENT_STATE`/`HOLDS` edges on `belief_id_logical` (Cypher) | ONE `match_nodes("BeliefState", {})` scan + core-Python join on `belief_id` (D-01/D-02) | Phase-3 D-01 made current DERIVED (no pointer edge); Phase 7 D-01/D-02 | The ARCHITECTURE.md Cypher sketch (lines 323-337) is SUPERSEDED — none of those edges/fields exist; do NOT implement it |
| `CURRENT_STATE` uniqueness as an edge-count invariant (`COUNT(...)==1`) | Single-valued derived-current THEOREM (unique ordering-max under unique `state_id` tiebreak) | Phase-3 D-01 | There is no pointer edge to corrupt; PITFALLS.md Pitfall 2's `COUNT` query is superseded by the keystone `@invariant` |
| Hansson Relevance/Core-Retainment as partial-meet remainder sets | Superseded-chain "surgical contraction" (symmetric-difference-is-`{p}`) | Phase 7 D-07 | No value-semantic derivation engine exists; the remainder-set form is not applicable |

**Deprecated/outdated:**
- The `research/ARCHITECTURE.md` §"Irony join" Cypher (lines 323-337): read AS SUPERSEDED (D-02).
- `belief_id_logical`: does not exist — `belief_id` IS the proposition id (D-02).
- `CURRENT_STATE` / `HOLDS` edges: do not exist — current is derived (Phase-3 D-01).
- PITFALLS.md Pitfall 2's `COUNT((b:Belief)-[:CURRENT_STATE]->()) == 1` invariant: superseded by
  the single-valued-derived-current theorem (no pointer to count).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The doxastica-specific phrasings of K*3 Inclusion / K*4 Vacuity (collapsing to expansion identities because `revise ≡ expand` and there is no consistency engine) are the intended FORMAL-01 assertions | Architecture Pattern 3 | LOW — grounded in D-04 (`revise ≡ expand`), DATA-05 (bases), and the Kumiho memory model; but the EXACT assertion shape is the planner's to ratify. If wrong, a postulate test asserts the wrong identity |
| A2 | Relevance and Core-Retainment collapse to the same "symmetric-difference-is-`{p}`" structural claim under the engine-free model | Architecture Pattern 4 | LOW-MEDIUM — directly follows from D-07 + "no value-semantic consistency engine" (CLAUDE.md memory), but two distinct test names should still exist for the proof's completeness; confirm the phrasing in discuss-phase |
| A3 | The honest Recovery counterexample asserts the closed-set Recovery conclusion (`base after contract+re-expand == base before`) which the superseded chain denies | Pattern 5 + Open Q1 | MEDIUM — the naive `{p,q}` base does NOT bite (Pitfall 1); the exact base must be chosen so the assertion genuinely fails. Planner MUST resolve Open Q1 |
| A4 | A test-level helper for the irony join is acceptable (vs. a core method), per D-03a discretion | Pattern 7 | LOW — explicitly Claude's discretion in CONTEXT; either satisfies FORMAL-05 |

**If this table is empty:** it is not — A3 in particular needs ratification during planning.

## Open Questions

1. **The exact Recovery counterexample base (D-04, Pitfall 1).**
   - What we know: it must be deterministic, hand-built, assert Recovery's conclusion, and
     `@pytest.mark.xfail(strict=True)`. The naive `{p, q}` base does NOT violate Recovery (q
     survives independently), so it would erroneously XPASS.
   - What's unclear: the precise base + ops that make the Recovery-demanded conclusion genuinely
     FAIL against the superseded-chain engine.
   - Recommendation: assert the closed-set Recovery claim — after `revise(p,v)`, `contract(p)`,
     `revise(p,v')` (a NEW value), the base does NOT equal the pre-contraction base (the old `v` is
     gone). For closed sets Recovery would restore the pre-contraction content; the superseded chain
     correctly denies it, so the assertion fails → xfail green. Document the base in the test
     docstring (D-04). Ratify the exact shape in discuss-phase.

2. **Per-postulate harness placement (D-06a, Claude's discretion).**
   - What we know: single-op postulates (K*4 Vacuity, K*6 Extensionality, Uniformity) MAY be
     `@given`; sequence-sensitive ones (K*2 Success, K*3 Inclusion, K*5 Consistency, Contraction
     Success/Inclusion/Relevance/Core-Retainment) ride the stateful machine.
   - What's unclear: nothing blocking — it is explicitly the planner's choice.
   - Recommendation: ride sequence-sensitive postulates + all structural invariants on the extended
     `_SpineMachine` (one machine, one oracle, both backends); put the two single-op AGM postulates
     as standalone `@given` tests over the `backend` fixture for clarity. Keeps the oracle in one
     place while keeping single-op proofs readable.

3. **Irony-join home: core method vs. test helper (D-01a/D-03a, Claude's discretion).**
   - What we know: must be one round-trip and leak no narrative naming into core.
   - Recommendation: extract the `rows → tails` helper into `core.py` (it single-sources the
     `_order_key` group-by-max and is genuinely reused by `query_scope`), but keep the
     divergence-join itself as a TEST-LEVEL helper in `test_irony_join.py` — that keeps the
     narrative-adjacent demo entirely out of core (cleanest D-03a posture) while still
     single-sourcing the ordering contract. Confirm in planning.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | the whole library | ✓ (assumed per project posture) | 3.14 floor | — (no UUID7 shim; native `uuid.uuid7()`) |
| hypothesis | all stateful/property tests | ✓ | >=6.155 (6.155.2) | — (it is the engine; no fallback) |
| pytest | the test runner + xfail | ✓ | >=8.0 (9.x) | — |
| pydantic | the frozen models | ✓ | >=2.11 (2.13.4) | — (sole required runtime dep) |
| ladybug | the `Ladybug*` `.TestCase` conformance runs | conditional | >=0.17,<0.18 (0.17.1) | `importorskip` SKIPS those cases (not fails); the `Memory*` oracle still runs — established discipline |

**Missing dependencies with no fallback:** none (the memory backend is zero-dependency and always
runs; the full proof requires ladybug, but the suite is honest-by-skip when it is absent).
**Missing dependencies with fallback:** `ladybug` — when absent, the ladybug `.TestCase`/fixture
param SKIPS via `pytest.importorskip` (BACK-05 conformance is then proven only on the in-memory
oracle; CI installs the extra so the full dual-backend proof runs).

## Validation Architecture

> nyquist_validation is enabled (no `workflow.nyquist_validation: false` found; `.planning/config.json`
> absent ⇒ treat as enabled). For this phase the suite IS the validation — each requirement maps to
> a concrete test artifact below.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + hypothesis 6.155.2 (stateful + `@given`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`addopts = "-v"`; **no `xfail_strict`** — D-04 needs per-mark `strict=True`) |
| Quick run command | `uv run pytest tests/test_invariants.py tests/test_recovery_xfail.py tests/test_irony_join.py -q` |
| Full suite command | `uv run pytest` (runs all backends; install `--extra ladybug` for the dual-backend proof) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FORMAL-01 | AGM K*2/K*3/K*4/K*5/K*6 over op sequences vs. shadow oracle | stateful + `@given` | `uv run pytest tests/test_invariants.py -k "Spine or postulate" -q` | ⚠️ EXTEND `test_invariants.py` (machine exists; postulate assertions are Wave 0) |
| FORMAL-02 | Hansson Contraction Success/Inclusion/Relevance/Core-Retainment/Uniformity (superseded-chain phrasing) | stateful `@invariant` | `uv run pytest tests/test_invariants.py -k "Spine" -q` | ⚠️ EXTEND `test_invariants.py` (Wave 0: add the contraction postulate invariants) |
| FORMAL-03 | `CURRENT_STATE` uniqueness (theorem) + chain immutability + `get_scope_at ≡ replay` + world-scope no-contraction | stateful `@invariant` | `uv run pytest tests/test_invariants.py tests/test_scope_at.py -k "Spine or Fold" -q` | ✅ uniqueness + immutability present (`test_invariants.py`); fold present (`test_scope_at.py`); ⚠️ Wave 0: register fold + `world_contract_raises` into the named conformance set per D-08 |
| FORMAL-04 | Recovery excluded (strict xfail) + superseded-chain replacement positives | `@pytest.mark.xfail(strict=True)` + function tests over `backend` | `uv run pytest tests/test_recovery_xfail.py -q -rxX` | ❌ NEW file `tests/test_recovery_xfail.py` (Wave 0) |
| FORMAL-05 | Two scopes diverging on `belief_id`, one round-trip, vs. plain-Python expected | function test over `backend` (or both-backends) | `uv run pytest tests/test_irony_join.py -q` | ❌ NEW file `tests/test_irony_join.py` (Wave 0) |
| BACK-05 | Suite parameterised over every registered backend (memory + ladybug) | the `.TestCase` two-subclass idiom + `backend` fixture | `uv run pytest -k "Memory or Ladybug" -q` and `uv run --extra ladybug pytest -q` | ✅ mechanism exists (`conftest.py` + `.TestCase` pattern); transversal — every new artifact inherits it |

### Sampling Rate
- **Per task commit:** `uv run pytest <the file touched> -q` (e.g. `tests/test_invariants.py -q`)
- **Per wave merge:** `uv run pytest -q` (memory-only fast path) then `uv run --extra ladybug pytest -q`
- **Phase gate:** Full dual-backend suite green (`uv run --extra ladybug pytest -q -rxX`, confirming
  the Recovery xfail shows `x` not `X`) + basedpyright strict + ruff clean before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_recovery_xfail.py` — covers FORMAL-04 (Recovery strict xfail + D-05 positives)
- [ ] `tests/test_irony_join.py` — covers FORMAL-05 (two-scope divergence demo)
- [ ] EXTEND `tests/test_invariants.py` — add AGM K*2–K*6 + Hansson 5-postulate assertions to
      `_SpineMachine` (FORMAL-01/02); register the named structural set per D-08 (FORMAL-03)
- [ ] Lift / register `tests/test_scope_at.py::_ScopeAtMachine.fold` property into the conformance
      set OR re-express as a registered `@invariant` (FORMAL-03 `get_scope_at ≡ replay`, D-08)
- [ ] OPTIONAL `src/doxastica/core.py` — extract the `rows → current tails` helper (D-01a) so
      `query_scope` and the irony join single-source the `_order_key` group-by-max
- [ ] Framework install: none — hypothesis/pytest already in the dev group; ensure CI installs
      `--extra ladybug` for the dual-backend proof (the install wiring itself is Phase 8 PKG-02)

## Security Domain

> `security_enforcement` is not set to `false` anywhere in the project config (absent ⇒ enabled).
> This phase adds NO new attack surface: it is test/query code over already-shipped operations,
> introduces no I/O, no new external input, no new dependency, and no network/auth/session surface.
> The relevant security property is the one the architecture already enforces by construction.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Library has no auth surface |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No multi-user access control (tenancy is the NVM layer's concern) |
| V5 Input Validation | yes (already controlled) | DATA-02 closed `BeliefFilter` (no free query string); the irony join composes ONLY `match_nodes` with property-equality `where` maps — NO query-string passthrough exists at the port (LPG-primitive, BACK-01). No new validation surface added by this phase |
| V6 Cryptography | no | No crypto (UUID7 is identity/ordering, not a security token) |

### Known Threat Patterns for the doxastica core

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher/query injection via a free query string | Tampering | Designed out at BOTH seams: the public `BeliefFilter` is closed (DATA-02) and the `BackendPort` exposes NO `run`/`query`/`execute` and no string-taking method (BACK-01). The irony join MUST honor this — one `match_nodes` scan + Python join, NEVER a constructed query (D-01). Verified by `tests/test_import_purity.py` (no `ladybug` import in core) |
| Value content becoming a backend execution surface | Tampering / Elevation | Value opacity (backend-contract.md §6): values are base64-over-JSON opaque blobs, never interpreted. The conformance suite's value strategies already exercise brace/bracket-shaped values (DEF-02-01 round-trip) |
| Driver/dialect leak across the core seam | Information disclosure | The driver-blind core (D-02) is statically guarded by `tests/test_import_purity.py`; any irony-join code in core MUST stay driver-blind (compose only `match_nodes`) |

## Sources

### Primary (HIGH confidence)
- `tests/test_invariants.py` (read in full) — the `_SpineMachine` keystone: oracle shape, fixed
  pools, `.TestCase` idiom, `_make_backend` bounded-ladybug builder, `teardown`, the keystone
  invariants. [VERIFIED: repo source]
- `tests/test_scope_at.py` (read in full) — the `_ScopeAtMachine` operational-fold oracle
  (`fold`), the anti-tautology discipline, the `<= as_of` cut, the two `.TestCase` subclasses.
  [VERIFIED: repo source]
- `tests/conftest.py` (read in full) — the `backend` fixture (`params=["memory","ladybug"]` +
  `importorskip`), the BACK-05 parametrization mechanism. [VERIFIED: repo source]
- `src/doxastica/core.py` (read in full) — `_order_key`, `_is_active_tail`, `_current_tail`,
  `_current`, `query_scope` (steps 3-4), `get_scope_at`, `get_revision_chain`, `contract`,
  `_encode_value`/`_decode_value`, `_append_state`. [VERIFIED: repo source]
- `src/doxastica/ports.py` (read in full) — the LPG-primitive `BackendPort`
  (`upsert_node`/`add_edge`/`match_nodes`/`traverse`/`unit_of_work`). [VERIFIED: repo source]
- `src/doxastica/models.py`, `src/doxastica/protocol.py`, `src/doxastica/__init__.py` (read) —
  the frozen models, the public `BeliefStore` Protocol, the public surface. [VERIFIED: repo source]
- `tests/test_cascade.py`, `tests/test_backend_parity.py`, `tests/test_import_purity.py` (read) —
  the Phase-7 deferral note, the xfail-flip discipline, the driver-blind static guard.
  [VERIFIED: repo source]
- `docs/backend-contract.md` (read in full) — BACK-04 prose; §7 names the Phase-7 suite as its
  executable form. [VERIFIED: repo source]
- `pyproject.toml` — `requires-python>=3.14`, `[tool.pytest.ini_options] addopts="-v"` (NO
  `xfail_strict`), `optional-dependencies.ladybug`, dependency-group `hypothesis>=6.155`.
  [VERIFIED: repo source]
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `07-CONTEXT.md` (read in full) — the six
  requirements, locked decisions D-01..D-08, project history. [VERIFIED: repo source]

### Secondary (MEDIUM confidence)
- Stanford Encyclopedia of Philosophy, *Logic of Belief Revision* — AGM postulates K*1–K*6 and
  Hansson base-contraction postulates (Success, Inclusion, Relevance, Core-Retainment, Uniformity)
  + Recovery. [CITED: plato.stanford.edu/entries/logic-belief-revision/]
- Hypothesis stateful API reference — `RuleBasedStateMachine`, `@rule`/`@invariant`/
  `@precondition`/`@initialize`, `Bundle`, `consumes`, `multiple`, `.TestCase` settings.
  [CITED: hypothesis.readthedocs.io/en/latest/reference/api.html]

### Tertiary (LOW confidence)
- None — every load-bearing claim is grounded in read repo source or an authoritative reference.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — nothing new is installed; all versions verified in the running repo.
- Architecture (harness extension, oracle discipline, parametrization): HIGH — the patterns are
  read verbatim from the existing, passing test suite.
- Postulate phrasings: MEDIUM-HIGH — classical forms cited against SEP; the doxastica-specific
  re-statements (belief-base + `revise ≡ expand` + superseded-chain) follow directly from the
  locked decisions but their exact assertion shapes (A1–A3) are the planner's to ratify.
- Recovery counterexample: MEDIUM — the strict-xfail mechanism is locked, but the exact base must
  be chosen to avoid the erroneous-XPASS trap (Open Q1).
- Pitfalls: HIGH — each is grounded in a specific source line or the absence of `xfail_strict`.

**Research date:** 2026-06-19
**Valid until:** 2026-07-19 (stable — internal repo patterns + a settled formal literature; the
only external moving part is hypothesis, which is already pinned `>=6.155`)
