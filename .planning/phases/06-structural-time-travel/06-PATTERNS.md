# Phase 6: Structural Time-Travel - Pattern Map

**Mapped:** 2026-06-19
**Files analyzed:** 2 (1 modified, 1 new)
**Analogs found:** 2 / 2 (both exact)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/doxastica/core.py` (ADD `get_scope_at` body) | service / read-method on `MemoryCore` | transform (read-fold over materialized states) | `MemoryCore.query_scope` (same file, core.py:544-607) + helpers `_order_key`/`_current_tail`/`_current`/`_hydrate` | exact (temporal sibling — ONE line moves) |
| `tests/test_scope_at.py` (NEW) | test (parametrized example tests + Hypothesis stateful property) | event-driven (op-sequence replay) + request-response (two-backend example tests) | `tests/test_query_scope.py` (example-test idiom + `backend` fixture) and `tests/test_invariants.py` (`RuleBasedStateMachine` + shadow-oracle + two `.TestCase` subclasses) | exact |

**Notes:**
- `src/doxastica/protocol.py` is UNCHANGED — the `get_scope_at` signature is already locked at protocol.py:150-165 (verified, see Shared Patterns §Signature).
- `src/doxastica/models.py`, `tests/conftest.py` are UNCHANGED.

---

## Pattern Assignments

### `src/doxastica/core.py` — `get_scope_at` body (service, read-fold transform)

**Analog:** `MemoryCore.query_scope` (core.py:544-607) — the direct template. `get_scope_at` is `query_scope`'s shipped body with the event-id constraint moved from a POST-filter on derived tails (step 6) to a PRE-filter on candidate states (inside the step-3 group-by loop), and the status-set machinery removed (always active-as-of).

**THE CENTRAL DIVERGENCE (read these two excerpts together — they are the whole phase):**

`query_scope` does **max-then-filter (DROP, never rewind)** — group-by max over ALL states, then post-filter the tails (core.py:586-604):
```python
# 3. group by belief_id, keep the per-group ordering-MAX over ALL statuses (reuse the key)
by_belief: dict[str, dict[str, Any]] = {}
for row in rows:
    current = by_belief.get(row["belief_id"])
    if current is None or _order_key(row) > _order_key(current):
        by_belief[row["belief_id"]] = row  # the status-agnostic current tail
tails = list(by_belief.values())
# ...
# 6. event-range POST-filter (D-06: drop, never rewind) — str-vs-str, inclusive (Pitfall 3)
if belief_filter.event_id_max is not None:
    event_max = str(belief_filter.event_id_max)
    tails = [t for t in tails if t["source_event_id"] <= event_max]   # <-- DROP a too-new tail
```

`get_scope_at` must do **cut-then-max (REWIND)** — the cut runs on candidate rows BEFORE the per-belief max, so an older value resurfaces (D-02/D-03). The `> as_of: continue` guard goes INSIDE the group-by loop:
```python
# composed from query_scope (core.py:586-607) + D-02/D-03/D-04/D-06
as_of = str(as_of_event_id)                          # D-04/Pitfall 2: str-vs-str, the _order_key form
rows = self._backend.match_nodes("BeliefState", {"scope_id": scope_id})   # D-08 pure read, absent -> []
by_belief: dict[str, dict[str, Any]] = {}
for row in rows:
    if row["source_event_id"] > as_of:               # D-04 INCLUSIVE cut: keep <= as_of, drop strictly newer
        continue                                     # <-- THE ONE STRUCTURAL DIFFERENCE (cut BEFORE max)
    current = by_belief.get(row["belief_id"])
    if current is None or _order_key(row) > _order_key(current):
        by_belief[row["belief_id"]] = row            # cut-window status-agnostic tail (D-05 state_id tiebreak)
tails = [t for t in by_belief.values() if t["status"] != Status.retracted.value]   # D-06 retracted-as-of collapse
tails.sort(key=_order_key)                           # step 5: reuse the ONE _order_key (identical to query_scope:606)
return [self._hydrate(t) for t in tails]             # step 6: identical to query_scope:607
```
*(Illustrative skeleton — implementer owns final shape. A1/D-06 give Claude's discretion between this inline cut and an `as_of`-parametrized `_current_tail`; both must reuse the ONE `_order_key`.)*

**Reused helpers (DO NOT re-implement — call the shipped ones):**

`_order_key` — the ONE ordering contract (core.py:86-96); reuse for BOTH the cut key form and the per-group max (D-05):
```python
def _order_key(state: dict[str, Any]) -> tuple[str, str]:
    return (str(state["source_event_id"]), str(state["state_id"]))
```

`_current_tail` — status-agnostic ordering-MAX over a `(scope, belief)` (core.py:192-213). The cut-aware variant (D-06, Claude's discretion) narrows its candidate window to `source_event_id <= as_of`:
```python
states = self._backend.match_nodes(
    "BeliefState",
    {"scope_id": scope_id, "belief_id": belief_id},
)
if not states:
    return None
return max(states, key=_order_key)  # IN-03: the ONE ordering contract
```

`_current` retracted-collapse rule (core.py:229-231) — the rule D-06 applies over the cut window instead of "now":
```python
tail = self._current_tail(scope_id, belief_id)
if tail is None or tail["status"] == Status.retracted.value:
    return None  # D-05: retracted tail ⇒ no active current
```

`_hydrate` — the value-decode boundary (core.py:252-267); the result must go through it, never a hand-rolled decode:
```python
return BeliefState(
    state_id=props["state_id"],
    belief_id=props["belief_id"],
    scope_id=props["scope_id"],
    source_event_id=props["source_event_id"],
    value=self._decode_value(props["value"]),
    status=Status(props["status"]),
)
```

**Imports already present in core.py** (no new import needed): `Status` (from models), `Any` (typing), `base64`/`json`/`uuid` (stdlib). `UUID` is the annotation for `as_of_event_id` matching protocol.py:150-154. core.py imports NO driver (module-level purity enforced by `tests/test_import_purity.py`) — `get_scope_at` adds zero imports.

---

### `tests/test_scope_at.py` — NEW (parametrized example tests + Hypothesis fold property)

This file has TWO analog idioms, used for its two halves.

#### Half A — example tests over the two-backend `backend` fixture

**Analog:** `tests/test_query_scope.py` (entire file).

**Test-helper preamble idiom** (test_query_scope.py:39-60) — copy verbatim shape:
```python
def _event_id() -> uuid.UUID:
    return uuid.uuid7()

def _core(backend: BackendPort) -> BeliefStore:
    return cast("BeliefStore", MemoryCore(backend))   # cast: MemoryCore doesn't yet fully satisfy BeliefStore

def _ids(states: list[BeliefState]) -> set[str]:
    return {s.belief_id for s in states}
```

**Example-test shape** — every test takes `backend: BackendPort`, builds `_core(backend)`, drives writes with fresh `_event_id()`s, asserts on `get_scope_at` output (test_query_scope.py:68-79):
```python
def test_query_scope_active_only(backend: BackendPort) -> None:
    core = _core(backend)
    core.revise("s", "A", "v0", _event_id())
    core.revise("s", "B", "w0", _event_id())
    core.contract("s", "B", _event_id())
    result = core.query_scope("s", BeliefFilter())
    assert _ids(result) == {"A"}, "default query_scope returns only active-current beliefs"
```

**The divergence test to write (and the analog it contrasts with):** `test_query_scope.py::test_event_range_postfilter` (lines 152-167) is the DROP semantics `get_scope_at` must NOT copy — its own comment literally points at this phase:
```python
def test_event_range_postfilter(backend: BackendPort) -> None:
    e_b_old = _event_id()
    e_b_new = _event_id()  # B's CURRENT tail — strictly newer than e_b_old
    core.revise("s", "B", "w_old", e_b_old)
    core.revise("s", "B", "w_new", e_b_new)
    result = core.query_scope("s", BeliefFilter(event_id_max=e_b_old))
    assert _ids(result) == {"A"}, "a belief whose current tail is newer than max is absent (D-06)"
    assert all(s.value != "w_old" for s in result), (
        "the range never rewinds a belief to an older superseded value (that is get_scope_at)"  # <-- THIS phase
    )
```
The Phase-6 mirror (`test_cut_rewinds_to_older_value`) writes the SAME revise→revise setup but asserts `get_scope_at("s", e_b_old)` returns B at **`"w_old"`** (rewind), not absent. This pair is the regression guard for the central trap.

**Backend fixture (UNCHANGED — reused verbatim):** `tests/conftest.py:34-55` — `@pytest.fixture(params=["memory", "ladybug"])`, `importorskip` skips the ladybug param when the driver is absent, fresh `:memory:` DB per call. No conftest change.

#### Half B — the operational-fold oracle (D-07, the SPEC)

**Analog:** `tests/test_invariants.py` (entire `_SpineMachine` idiom).

**Fixed event-id pool forcing collisions** (test_invariants.py:62-84) — exercises SC3 (intra-ms / out-of-order ids):
```python
_EVENT_POOL: tuple[uuid.UUID, ...] = tuple(uuid.uuid7() for _ in range(3))  # collisions guaranteed
_SCOPE_POOL: tuple[str, ...] = ("alice", "bob", "carol")
_BELIEF_POOL: tuple[str, ...] = ("b1", "b2", "b3")
_event_ids = st.sampled_from(_EVENT_POOL)
_scope_ids = st.sampled_from(_SCOPE_POOL)
_belief_ids = st.sampled_from(_BELIEF_POOL)
```

**`_make_backend` per-example builder with bounded ladybug DB** (test_invariants.py:132-148) — copy verbatim; the `max_db_size=2**30` cap is load-bearing (the stateful machine creates dozens of DBs):
```python
def _make_backend(self) -> BackendPort:
    if self.backend_kind == "ladybug":
        lb = pytest.importorskip("ladybug")
        from doxastica.backends.ladybug import LadybugBackend
        db = lb.Database(max_db_size=2**30)  # 1 GiB cap — Hypothesis makes one DB PER example
        return LadybugBackend(lb.Connection(db), namespace="dx", owns_conn=True)
    from doxastica.backends.memory import InMemoryBackend
    return InMemoryBackend()
```

**`@initialize` + `_record` op-log** (test_invariants.py:150-168) — the Phase-6 `_record` must additionally carry `op_kind` so `fold` can drop a contract winner (D-06). The `append_seq` is the `state_id`-tiebreak stand-in:
```python
@initialize()
def _setup(self) -> None:
    self._be = self._make_backend()
    self.core = MemoryCore(self._be)
    self.entries: dict[tuple[str, str], list[_SpineMachine.Entry]] = {}
    self._seq = 0  # monotonic append counter — the oracle's state_id-tiebreak stand-in

def _record(self, scope_id, belief_id, value, source_event_id, status) -> None:
    self._seq += 1
    self.entries.setdefault((scope_id, belief_id), []).append(
        (str(source_event_id), self._seq, value, status)
    )
```

**The shadow-fold to extend** — `_shadow_current` (test_invariants.py:170-183) computes the winner at "now"; the Phase-6 `fold(scope_id, as_of)` adds the `<= as_of` cut on `entries` BEFORE the max (the SAME cut-then-max as the method), dropping a `contract`/`retracted` winner:
```python
def _shadow_current(self, scope_id: str, belief_id: str) -> tuple[bool, Any]:
    entries = self.entries.get((scope_id, belief_id))
    if not entries:
        return (False, None)
    _src, _seq, value, status = max(entries, key=lambda e: (e[0], e[1]))   # (source_event_id, seq) == _order_key
    if status == "retracted":
        return (False, None)
    return (True, value)
```

**Independent-recompute lesson (CRITICAL — Pitfall 6 anti-tautology):** `_chain_tail` (test_invariants.py:87-104) recomputes the current via the PUBLIC `get_revision_chain` rather than reusing `_current`, "so the agreement is a real cross-check, not a tautology." The Phase-6 `fold` must likewise fold the recorded OP SEQUENCE with its own `(source_event_id, append_seq)` winner selection — it must NOT call `MemoryCore._current_tail` / `get_scope_at`.

**Write rules mirror each op into the oracle** (test_invariants.py:204-244) — `revise`/`expand` record an active op; `contract` records a retracted op gated by `@precondition` on currently-active keys:
```python
@rule(scope_id=scopes, belief_id=beliefs, value=_values, source_event_id=_event_ids)
def revise(self, scope_id, belief_id, value, source_event_id) -> None:
    self.core.revise(scope_id, belief_id, value, source_event_id)
    self._record(scope_id, belief_id, value, source_event_id, "active")
```

**The `@invariant` to add** — `scope_at_equals_fold_for_every_cut`: for each scope × each cut (every pooled id + a maximal sentinel), assert `{s.belief_id: s.value for s in core.get_scope_at(scope, cut)} == fold(scope, cut)`. SC1 falls out at the maximal cut.

**`teardown` releasing the per-example backend** (test_invariants.py:317-328) — copy verbatim (closes the owning ladybug DB handle):
```python
def teardown(self) -> None:
    close = getattr(getattr(self, "_be", None), "close", None)
    if callable(close):
        close()
```

**Bounded settings + two `.TestCase` subclasses** (test_invariants.py:331-355) — the two-backend entry-point idiom, copy verbatim with renamed classes:
```python
_SETTINGS = settings(max_examples=50, stateful_step_count=20, deadline=None)

class MemoryScopeAtMachine(_ScopeAtMachine):
    backend_kind = "memory"
class LadybugScopeAtMachine(_ScopeAtMachine):
    backend_kind = "ladybug"

MemoryScopeAtMachine.TestCase.settings = _SETTINGS   # pyright: ignore[reportUnknownMemberType]
LadybugScopeAtMachine.TestCase.settings = _SETTINGS  # pyright: ignore[reportUnknownMemberType]
MemoryScopeAtTest = MemoryScopeAtMachine.TestCase    # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
LadybugScopeAtTest = LadybugScopeAtMachine.TestCase  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
```

**Hypothesis imports** (test_invariants.py:46-55): `from hypothesis import settings`, `from hypothesis import strategies as st`, `from hypothesis.stateful import Bundle, RuleBasedStateMachine, initialize, invariant, precondition, rule`.

---

## Shared Patterns

### The ONE ordering contract (`_order_key`)
**Source:** `src/doxastica/core.py:86-96`
**Apply to:** the `get_scope_at` cut comparison (`str`-form), the per-group max, and the final sort — AND the oracle's winner selection (mirror it as `(source_event_id, append_seq)`).
```python
return (str(state["source_event_id"]), str(state["state_id"]))
```
Never introduce a second ordering (D-05 / IN-03). The cut compares `str(source_event_id)`; the max uses the full key.

### str-vs-str cut (never str-vs-UUID)
**Source:** `query_scope` post-filter form, core.py:600/603 (`event_max = str(belief_filter.event_id_max)`); `_append_state` stores `str(source_event_id)` (core.py:299).
**Apply to:** the `get_scope_at` cut. Normalize ONCE: `as_of = str(as_of_event_id)`, then `row["source_event_id"] <= as_of`. Mixing `str <= UUID` raises `TypeError` (Pitfall 2).

### Pure-read surface (no auto-create, no UoW, no world-guard)
**Source:** `query_scope` docstring + body, core.py:571-585 ("A pure read (D-08): a non-existent or empty scope returns `[]` and creates NO `Scope` node").
**Apply to:** `get_scope_at` — absent/empty scope → `[]`; `get_scope_at(world, e)` is valid (reads never trigger the world-scope guard). No `_ensure_scope`, no `unit_of_work`.

### Value-decode boundary (`_hydrate` / `_decode_value`)
**Source:** `src/doxastica/core.py:248-267`
**Apply to:** every state `get_scope_at` returns — route through `self._hydrate(props)`; never re-implement base64/JSON decode (avoids the DEF-02-01 brace-coercion corruption).

### Two-backend parity via the `backend` fixture / two `.TestCase` subclasses
**Source:** `tests/conftest.py:34-55` (example tests) and `tests/test_invariants.py:335-355` (stateful machine).
**Apply to:** all example tests (take `backend: BackendPort`) and the fold machine (memory + ladybug subclasses). Agreement with the oracle on both backends IS cross-backend parity (no separate parity test needed for the fold).

### `get_scope_at` signature (LOCKED — do not change)
**Source:** `src/doxastica/protocol.py:150-165` (verified present)
```python
def get_scope_at(
    self,
    scope_id: str,
    as_of_event_id: UUID,
) -> list[BeliefState]:
```

---

## No Analog Found

None. Both files have exact in-repo analogs (`get_scope_at` is the temporal sibling of `query_scope`; `test_scope_at.py` combines the two shipped test idioms). The phase is pure composition — RESEARCH.md confirms no new package, no new port primitive, no new module.

---

## Metadata

**Analog search scope:** `src/doxastica/core.py`, `src/doxastica/protocol.py`, `tests/test_query_scope.py`, `tests/test_invariants.py`, `tests/conftest.py`
**Files scanned:** 5 (all cited by RESEARCH.md as primary HIGH-confidence sources; line numbers verified against current source)
**Pattern extraction date:** 2026-06-19
