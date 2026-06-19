# Phase 7: AGM/Hansson Backend Conformance Suite & Irony Join - Pattern Map

**Mapped:** 2026-06-19
**Files analyzed:** 5 (2 new test files, 1 extended test file, 1 lifted test file, 1 optional core helper)
**Analogs found:** 5 / 5 (every artifact has an exact in-repo analog — this phase is 95% reuse)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/test_invariants.py` (EXTEND) | test (stateful machine) | event-driven (op-sequence) | itself — `_SpineMachine` extended in place (D-06) | exact (self) |
| `tests/test_recovery_xfail.py` (NEW) | test (function + xfail) | request-response (deterministic ops) | `tests/test_backend_parity.py` + `tests/test_cascade.py` (`backend` fixture + value round-trip) | exact (idiom) |
| `tests/test_irony_join.py` (NEW) | test (function, divergence demo) | transform / batch (one scan → join) | `tests/test_scope_at.py` (function-half over `backend` fixture) + `core.py::query_scope` | exact (idiom + pipeline) |
| `tests/test_scope_at.py` (LIFT/register) | test (stateful machine) | event-driven (op-sequence) | itself — `_ScopeAtMachine.fold` already the registered conformance property (D-08) | exact (self) |
| `src/doxastica/core.py` (OPTIONAL helper) | utility (pure derived-current) | transform (rows → tails) | `core.py::query_scope` steps 3–4 + `_order_key`/`_current_tail`/`_is_active_tail` | exact (extraction) |

**Key:** this phase adds NO Protocol operation. The only candidate production change is the
optional `rows → tails` helper extraction (D-01a); a test-level helper is an acceptable alternative
(RESEARCH Open Q3 recommends extracting the helper into core but keeping the divergence-join itself
test-level).

## Pattern Assignments

---

### `tests/test_invariants.py` — EXTEND `_SpineMachine` (FORMAL-01/02/03; test, event-driven)

**Analog:** itself. The keystone `_SpineMachine` is extended in place (D-06) — do NOT rewrite it,
do NOT spawn a parallel machine (Anti-Pattern: "Rewriting `_SpineMachine`", RESEARCH). New postulate
assertions are added as `@invariant` methods (sequence-sensitive) or standalone `@given` tests
(single-op, D-06a). All new write rules MUST keep the existing oracle/pool discipline.

**The two-subclass dual-backend `.TestCase` idiom to preserve verbatim** (`test_invariants.py:132-148, 335-355`):
```python
def _make_backend(self) -> BackendPort:
    if self.backend_kind == "ladybug":
        lb = pytest.importorskip("ladybug")  # SKIP, not fail, when driver absent
        from doxastica.backends.ladybug import LadybugBackend
        db = lb.Database(max_db_size=2**30)   # 1 GiB cap — Hypothesis makes one DB PER EXAMPLE (Pitfall 4)
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
This IS the BACK-05 conformance mechanism — every new `@invariant` rides both backends transversally.

**The INDEPENDENT shadow oracle to extend, NOT replace** (`test_invariants.py:170-183`):
```python
def _shadow_current(self, scope_id: str, belief_id: str) -> tuple[bool, Any]:
    entries = self.entries.get((scope_id, belief_id))
    if not entries:
        return (False, None)
    _src, _seq, value, status = max(entries, key=lambda e: (e[0], e[1]))  # mirrors _order_key
    if status == "retracted":
        return (False, None)   # retracted ordering-max tail ⇒ no active current (D-05)
    return (True, value)
```
The oracle is `self.entries` (per `(scope, belief)` → ordered `[(src_str, seq, value, status)]`) +
`_shadow_current`. **Anti-tautology rule (Pitfall 2, the whole point):** new postulate `@invariant`s
compute "expected" ONLY from `self.entries`/`_shadow_current` — NEVER from `query_scope`/`_current`
on both sides. The `append_seq` is the monotonic stand-in for the core-minted `state_id` tiebreak.

**The independent public-history cross-check** (`test_invariants.py:87-104`, `_chain_tail`):
recomputes the tail from `get_revision_chain` rather than reusing `_current` — reuse this discipline
for the superseded-chain postulate assertions.

**The keystone `@invariant` shape new postulates mirror** (`test_invariants.py:258-315`):
```python
@invariant()
def current_is_total_single_valued_and_chain_tail(self) -> None:
    for scope_id in _SCOPE_POOL:
        for belief_id in _BELIEF_POOL:
            has_current, expected = self._shadow_current(scope_id, belief_id)  # ORACLE, independent
            current = self.core._current(scope_id, belief_id)                  # SUT
            if not has_current:
                assert current is None
                continue
            assert current is not None
            assert MemoryCore._decode_value(current["value"]) == expected
            tail = _chain_tail(self.core, scope_id, belief_id)                 # independent recompute
            assert tail is not None and tail["state_id"] == current["state_id"]
```
This is FORMAL-03 `CURRENT_STATE`-uniqueness (the single-valued derived-current THEOREM — D-08)
AND chain-tail equality, ALREADY present. `chain_is_immutable` (`:297-315`) is FORMAL-03 chain
immutability, ALREADY present.

**The write-rule + oracle-mirror + collision-pool pattern to copy for any new contraction postulate**
(`test_invariants.py:198-255`): every write rule draws `source_event_id=_event_ids` (the fixed
`_EVENT_POOL` of 3 pre-minted UUID7s — Pitfall 6, the tiebreak coverage) and calls `self._record(...)`
after the real op. The `contract` rule is `@precondition`-gated on `_asserted_keys()` and
`world_contract_raises` is the FORMAL-03 world-scope no-contraction invariant ALREADY present at
`:246-255` — D-08 only requires routing it into the named conformance set (it is already a `@rule`).

**Postulate assignment guidance** (D-06a, RESEARCH Pattern 3/4, Open Q2):
- Sequence-sensitive (K*2 Success, K*3 Inclusion, K*5 Consistency, Hansson Contraction Success /
  Inclusion / Relevance / Core-Retainment) → `@invariant`s on the extended `_SpineMachine`,
  comparing `query_scope(scope, BeliefFilter())` (the observed base = AGM `K`) against
  `_shadow_current` over the pools.
- Single-op (K*4 Vacuity, K*6 Extensionality, Hansson Uniformity) → standalone `@given` tests over
  the `backend` fixture (clearer than riding the machine).
- Relevance + Core-Retainment collapse to the SAME structural claim under the engine-free model
  (D-07): "contraction is surgical — symmetric-difference-of-bases-is-exactly-`{p}`". Do NOT
  fabricate a derivation relation the core lacks (Anti-Pattern).

---

### `tests/test_recovery_xfail.py` — NEW (FORMAL-04; test, function + strict xfail)

**Analog:** `tests/test_backend_parity.py` (value-round-trip THROUGH `MemoryCore` + the `backend`
fixture) and `tests/test_cascade.py` (NEW-file-composing-existing-idioms header style). The
superseded-chain POSITIVES (D-05) run over the `conftest.py` `backend` fixture; the Recovery xfail
is a single deterministic function test (NOT a Hypothesis sweep — D-04).

**Imports pattern** (from `test_backend_parity.py:30-43`, `test_cascade.py:29-46`):
```python
from __future__ import annotations
import uuid
from typing import TYPE_CHECKING
import pytest
from doxastica import BeliefFilter, MemoryCore
if TYPE_CHECKING:
    from doxastica.ports import BackendPort
```

**The strict-xfail mark** (D-04; pyproject has `addopts = "-v"` and NO `xfail_strict` — VERIFIED
`pyproject.toml:68-69` — so `strict=True` MUST be on the mark itself, Pitfall 3):
```python
@pytest.mark.xfail(
    strict=True,
    reason="AGM Recovery excluded — belief base (not closed set); Hansson; "
           "replaced by superseded-chain semantics",
)
def test_recovery_does_not_hold_for_belief_bases() -> None:
    core = MemoryCore.in_memory()                      # zero-dep construction (core.py:128-133)
    e = lambda: uuid.uuid7()
    core.revise("s", "p", "v", e())
    core.contract("s", "p", e())
    core.revise("s", "p", "vprime", e())               # re-assert p at a NEW value
    base = {s.belief_id: s.value for s in core.query_scope("s", BeliefFilter())}
    # Recovery (closed-set) would DEMAND base == the pre-contraction base ({"p": "v"}); the
    # superseded chain correctly DENIES it (base == {"p": "vprime"}). The assertion below states
    # the Recovery conclusion → it FAILS against the correct engine → xfail GREEN. If the engine
    # ever satisfies Recovery, this PASSES → strict xfail XPASSes → suite RED (the drift guard).
    assert base == {"p": "v"}
```
> **PLANNER MUST RESOLVE (Open Q1 / Pitfall 1):** the naive `{p, q}` base does NOT bite (independent
> `q` survives → erroneous XPASS → red against correct code). The honest base re-asserts `p` at a
> NEW value (above): the superseded chain does not resurrect superseded content, so the closed-set
> Recovery conclusion genuinely fails. Ratify the exact base + document it in the docstring (D-04).

**The superseded-chain replacement POSITIVES** (D-05, PASSING; analog = `test_backend_parity.py`
value-round-trip through `MemoryCore` + `core.py::get_revision_chain:547-557`):
```python
def test_superseded_chain_replaces_recovery(backend: BackendPort) -> None:
    core = MemoryCore(backend)                         # injected fixture port (test_scope_at.py:58-69 precedent)
    e = lambda: uuid.uuid7()
    core.revise("s", "p", "v", e())
    core.contract("s", "p", e())
    core.revise("s", "p", "vprime", e())
    chain = core.get_revision_chain("p")               # cross-scope, _order_key-sorted (core.py:547-557)
    assert [s.status.value for s in chain] == ["active", "retracted", "active"]  # the documented read (D-05)
    assert chain[-1].value == "vprime"                 # current resolves to v', not v
    base = {s.belief_id: s.value for s in core.query_scope("s", BeliefFilter())}
    assert base.get("p") == "vprime"                   # old value NOT silently restored
```
**Boundary (D-05 / Pitfall 5):** keep DISTINCT from temporal recoverability (`get_scope_at`) — do
NOT call `get_scope_at` in a Recovery test; state the distinction in docstrings.

---

### `tests/test_irony_join.py` — NEW (FORMAL-05; test, transform/batch)

**Analog:** `tests/test_scope_at.py` function-half (function tests over the `backend` fixture, D-01)
+ `core.py::query_scope` steps 3–4 (the derived-current pipeline the join reuses).

**The ONE round-trip + derived-tail + inner-join shape** (D-01/D-01a/D-02; reuses `_order_key` +
`_is_active_tail`, `core.py:86-112`, and the group-by-max from `query_scope:602-610`):
```python
def diverging_beliefs(core: MemoryCore, scope_a: str, scope_b: str) -> list[tuple[str, Any, Any]]:
    rows = core._backend.match_nodes("BeliefState", {})   # ONE scan — "single query" = one round-trip (D-01a)
    tails_a = _current_tails_for_scope(rows, scope_a)      # {belief_id: tail} — group-by-max + active-tail collapse
    tails_b = _current_tails_for_scope(rows, scope_b)
    out: list[tuple[str, Any, Any]] = []
    for belief_id in tails_a.keys() & tails_b.keys():      # inner join on belief_id (D-02)
        va = MemoryCore._decode_value(tails_a[belief_id]["value"])
        vb = MemoryCore._decode_value(tails_b[belief_id]["value"])
        if va != vb:
            out.append((belief_id, va, vb))
    return out
```
The `_current_tails_for_scope` body is `query_scope` steps 3–4 filtered to one scope
(`core.py:602-610`) — the D-01a `rows → tails` extraction. **Anti-pattern to avoid:** two
`query_scope` calls or a second `match_nodes` (that is two round-trips — Pitfall, D-01a). One
`match_nodes("BeliefState", {})` scan, filter both scopes in Python (AND-equality `match_nodes`
cannot express `scope_id IN {a,b}`).

**The plain-Python expected oracle** (D-03): compute the divergent rows directly from the known
synthetic writes and compare — no second-backend implementation, no port widening. Run over the
`backend` fixture so cross-backend parity falls out (the `test_backend_parity.py` Open-Q1 logic:
fixture runs once per backend, comparison to a literal already proves parity).

**Boundary (D-03a / Anti-Pattern "Narrative naming in core"):** if any of this lands in `core.py`,
name it NEUTRALLY (`diverging_beliefs(scope_a, scope_b)`) — never `irony`/`actor`/`world_truth`/
`dramatic_irony`. `WORLD_SCOPE_ID` already exists (`__init__.py:11`); an "actor" scope is any
non-world scope. RESEARCH Open Q3 recommends keeping the divergence-join itself as a TEST-LEVEL
helper in this file (cleanest D-03a posture).

---

### `tests/test_scope_at.py` — LIFT/register `_ScopeAtMachine.fold` (FORMAL-03 `get_scope_at ≡ replay`; D-08)

**Analog:** itself. The Phase-6 operational-fold property is ALREADY a registered dual-backend
conformance property — D-08 is satisfied by re-referencing it OR re-expressing it as a registered
`@invariant` (Claude's discretion). Do NOT build a new replay function (Anti-Pattern / Don't Hand-Roll).

**The independent operational-fold oracle** (`test_scope_at.py:367-390`):
```python
def fold(self, scope_id: str, as_of: str) -> dict[str, Any]:
    base: dict[str, Any] = {}
    for (entry_scope, belief_id), ops in self.entries.items():
        if entry_scope != scope_id:
            continue
        eligible = [e for e in ops if e[0] <= as_of]          # SAME inclusive str-vs-str cut (D-04)
        if not eligible:
            continue
        winner = max(eligible, key=lambda e: (e[0], e[1]))    # mirror _order_key (src, seq)
        if winner[3] == "contract":                           # retracted-as-of ⇒ absent (D-06)
            continue
        base[belief_id] = winner[2]
    return base
```
**The registered conformance `@invariant`** (`test_scope_at.py:457-474`):
```python
@invariant()
def scope_at_equals_fold_for_every_cut(self) -> None:
    for scope_id in _SCOPE_POOL:
        for cut in (*_EVENT_POOL, _MAX_CUT):
            got = {s.belief_id: s.value for s in self.core.get_scope_at(scope_id, cut)}
            expected = self.fold(scope_id, str(cut))
            assert got == expected
```
Already runs on both backends via `MemoryScopeAtFoldMachine` / `LadybugScopeAtFoldMachine`
(`test_scope_at.py:494-515`) — identical idiom to `_SpineMachine`. D-08 needs only to NAME this in
the conformance set (a docstring/registry reference), not re-implement.

---

### `src/doxastica/core.py` — OPTIONAL `rows → tails` helper extraction (D-01a; utility, transform)

**Analog:** `query_scope` steps 3–4 (`core.py:602-610`) + the ONE ordering contract (`_order_key`
`:86-96`, `_is_active_tail` `:99-112`, `_current_tail` `:208-229`). Extract the group-by-`belief_id`
→ per-group ordering-MAX → status filter as a pure helper both `query_scope` and the irony join
reuse — single-sourcing the `_order_key` contract so the two cannot drift.

**The exact steps to extract** (`core.py:602-610`):
```python
by_belief: dict[str, dict[str, Any]] = {}
for row in rows:                                        # rows = match_nodes scan, filtered to scope
    current = by_belief.get(row["belief_id"])
    if current is None or _order_key(row) > _order_key(current):
        by_belief[row["belief_id"]] = row              # per-belief ordering-max (status-agnostic)
tails = list(by_belief.values())
tails = [t for t in tails if Status(t["status"]) in allowed]   # status filter AFTER the max (Pitfall 2)
```
**Constraints:** behavior-preserving (the existing keystone + `query_scope` tests must stay green);
status filter runs AFTER the per-belief max (Pitfall: pre-filtering to `active` leaks a stale active
value below a retracted tail). Driver-blind — composes only the already-imported stdlib + the
`_order_key`/`Status` helpers (no `ladybug` import; `test_import_purity.py` guards this). This change
is OPTIONAL — a test-level helper in `test_irony_join.py` is an acceptable substitute (RESEARCH Open Q3).

---

## Shared Patterns

### Dual-backend conformance parametrization (BACK-05)
**Source:** `tests/conftest.py:34-55` (the `backend` fixture) + the two-subclass `.TestCase` idiom
(`tests/test_invariants.py:335-355`, `tests/test_scope_at.py:494-515`).
**Apply to:** EVERY new artifact. Function tests consume `backend: BackendPort`; stateful machines
use two `backend_kind` subclasses. BACK-05 is satisfied transversally — NOT as a discrete step.
```python
@pytest.fixture(params=["memory", "ladybug"])
def backend(request: pytest.FixtureRequest) -> Iterator[BackendPort]:
    if request.param == "ladybug":
        lb = pytest.importorskip("ladybug")            # SKIP, not fail, when driver absent
        from doxastica.backends.ladybug import LadybugBackend
        conn = lb.Connection(lb.Database())            # fresh in-memory DB per example (FORMAL-06)
        be = LadybugBackend(conn, namespace="dx", owns_conn=True)
        yield be
        be.close()
    else:
        from doxastica.backends.memory import InMemoryBackend
        yield InMemoryBackend()
```

### The INDEPENDENT shadow oracle (anti-tautology)
**Source:** `tests/test_invariants.py:121-183` (`self.entries` + `_shadow_current`),
`tests/test_scope_at.py:367-390` (`fold`).
**Apply to:** every postulate/invariant assertion. The oracle has its OWN
`(source_event_id_str, append_seq)` winner selection and NEVER calls `query_scope`/`_current`/
`_current_tail`/`get_scope_at`. The proof is the comparison between the oracle (the AGM belief base)
and the core's observed base — if the oracle calls the SUT, it is a restatement, not a cross-check.

### The fixed colliding `source_event_id` pool (Pitfall 6 tiebreak coverage)
**Source:** `tests/test_invariants.py:62-66, 82-84` (`_EVENT_POOL` of 3 pre-minted UUID7s,
`st.sampled_from(_EVENT_POOL)`).
**Apply to:** every new stateful write rule. Draw `source_event_id` from the small fixed pool
(never a fresh `uuid.uuid7()` per op) so the `(source_event_id, state_id)` tiebreak in `_order_key`
is actually exercised. A fresh UUID7 per op makes the primary key alone sufficient and the tiebreak
branch dead.

### The ONE ordering contract + retracted-tail collapse
**Source:** `src/doxastica/core.py:86-112` (`_order_key`, `_is_active_tail`), `:208-248`
(`_current_tail`, `_current`).
**Apply to:** the irony join, the `rows → tails` helper, and any oracle winner selection. Reuse
`_order_key` = `(str(source_event_id), str(state_id))` and `_is_active_tail` — never a second sort.

### The value codec at the core boundary (DEF-02-01)
**Source:** `src/doxastica/core.py:251-266` (`_encode_value`/`_decode_value`, base64-over-JSON).
**Apply to:** any test comparing stored `value` tokens. Compare DECODED values
(`MemoryCore._decode_value(...)`) — the stored form is base64. Values round-trip byte-identically on
both backends (the irony join decodes both scopes' tails before comparison).

### Ladybug per-example handle hygiene (Pitfall 4)
**Source:** `tests/test_invariants.py:140-148` (`lb.Database(max_db_size=2**30)`), `:317-328`
(`teardown` with `getattr(self._be, "close", None)`).
**Apply to:** any NEW stateful machine. The 1 GiB cap + `teardown` close are MANDATORY — Hypothesis
builds one DB per example and the default ~8 TiB mmap reservation exhausts the address space. The
in-memory backend has no `close`; the `getattr` guard makes teardown a no-op there.

## No Analog Found

None. Every Phase-7 artifact has an exact in-repo analog (the keystone `_SpineMachine`, the
`_ScopeAtMachine` fold, the `backend` fixture, the `query_scope` pipeline, the value codec). This
phase is additive and pattern-following — the temptation to "build a proper test framework" is the
trap; extend the keystone and compose the existing helpers.

## Metadata

**Analog search scope:** `tests/` (test_invariants, test_scope_at, conftest, test_cascade,
test_backend_parity), `src/doxastica/` (core, __init__), `pyproject.toml`.
**Files scanned:** 8 (read in full or in the load-bearing ranges).
**Config facts verified:** `pyproject.toml:68-69` has `addopts = "-v"` and NO `xfail_strict`
(confirming D-04's per-mark `strict=True` requirement); public surface re-exports
`MemoryCore`, `BeliefFilter`, `WORLD_SCOPE_ID`, `WorldScopeContractionError` (`__init__.py:22-37`).
**Pattern extraction date:** 2026-06-19
