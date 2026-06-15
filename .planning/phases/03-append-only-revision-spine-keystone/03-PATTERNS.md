# Phase 3: Append-Only Revision Spine (Keystone) - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 6 (3 source modified, 1 source re-export, 2 test new) + 1 regression flip
**Analogs found:** 5 / 6 (one new pattern: Hypothesis stateful — no in-repo analog)

This phase is almost pure *composition*: it fills unwritten AGM op bodies on the existing
`MemoryCore` against the already-shipped 5 LPG primitives and adds one REL table to the ladybug
bootstrap. Every modified file has a strong same-repo analog. The single no-analog file is the
Hypothesis stateful invariant machine (hypothesis is a dev dep but unused so far).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/doxastica/core.py` (FILL op bodies + `_current`/`_append`/`_hydrate`/`_ensure_scope` helpers) | service / core engine | CRUD (append-only) + transform | itself (Phase 2 factory bodies) + `protocol.py` signatures + `backends/memory.py` primitive composition | exact (same file, established class) |
| `src/doxastica/backends/ladybug.py` (`HAS_REVISION` REL table in `_bootstrap_schema`) | adapter / config (DDL) | file-I/O (schema bootstrap) | `ladybug.py::_bootstrap_schema` existing edge-table loop (lines 144-176) | exact (same method, same loop) |
| `src/doxastica/backends/memory.py` (parity confirm — likely NO code change) | adapter / oracle | CRUD | itself — already model-blind, value-verbatim; encode/decode lives in `core.py` not here | exact (no change expected; see note) |
| `src/doxastica/__init__.py` (export `WORLD_SCOPE_ID`) | config / barrel | — | `__init__.py` existing `__all__` re-export block (lines 3-35) | exact |
| `src/doxastica/models.py` OR new `constants.py` (`WORLD_SCOPE_ID = "__world__"`) | model / constant | — | `models.py` `StrEnum`/constant style (lines 24-55) | role-match |
| `tests/test_revision_spine.py` (NEW: SCOPE/CHAIN/OPS/HIST over both backends) | test | request-response | `tests/test_backend_parity.py` (parametrized `backend` fixture, helper builders, literal-parity) | exact (same fixture, same shape) |
| `tests/test_invariants.py` (NEW: Hypothesis stateful consistency check + shadow oracle) | test | event-driven (op-sequence) | **none in-repo** — hypothesis unused so far; use `conftest.py` fixture + CLAUDE.md stateful notes + Hypothesis docs | no analog |
| `tests/test_backend_parity.py::test_value_string_round_trips_ladybug` (flip xfail → passing) | test | regression | the sibling `test_value_string_round_trips_memory` (lines 292-296) — same assertion, now both pass | exact (sibling test) |

---

## Pattern Assignments

### `src/doxastica/core.py` (service, CRUD append-only + transform)

**Analog:** the same file's Phase-2 bodies (factories + `unit_of_work` passthrough) for class
structure and driver-blind imports; `backends/memory.py` for how the 5 primitives compose;
`protocol.py` for the exact public signatures to honour.

**Class + driver-blind import convention to preserve** (`core.py` lines 29-39, 50-52):
```python
from __future__ import annotations
from typing import TYPE_CHECKING, cast
if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from doxastica.ports import BackendPort
    # NOTE (D-02): do NOT import ladybug here, even under TYPE_CHECKING.
```
Phase 3 ADDS runtime stdlib imports `import json` and `import uuid` at module top (these are NOT
drivers — `test_import_purity.py` only forbids `ladybug`). It also imports the models it hydrates
(`from doxastica.models import BeliefState, Scope, Status`) and the error
(`from doxastica.errors import WorldScopeContractionError`) and `WORLD_SCOPE_ID`. The existing
`self._backend` attribute (line 52) is the port the op bodies compose.

**`unit_of_work` passthrough already present** (`core.py` lines 97-99) — each public write opens
exactly ONE `with self._backend.unit_of_work():` (CHAIN-03); do not nest.

**get_or_create_scope pattern** (compose `match_nodes` + `upsert_node`; reserved-id rule D-02).
The primitive shapes come from `memory.py::match_nodes` (lines 85-96) and `upsert_node`
(lines 54-69) — both keyed/filtered on plain prop dicts:
```python
def get_or_create_scope(self, scope_id: str) -> Scope:
    is_world = scope_id == WORLD_SCOPE_ID                       # D-02 reserved-id rule
    existing = self._backend.match_nodes("Scope", {"scope_id": scope_id})
    if not existing:
        self._backend.upsert_node("Scope", scope_id,
                                  {"scope_id": scope_id, "is_world": is_world})
    return Scope(scope_id=scope_id, is_world=is_world)          # derive is_world, do not trust col
```
Note: `upsert_node` excludes the PK from its SET loop (ladybug `_PK_BY_LABEL` rule,
`ladybug.py` lines 197-209), so passing `scope_id` in props is safe and idempotent — proven by
`test_scope_upsert_parity` (`test_backend_parity.py` lines 199-206).

**derived-current — the ONE place the ordering contract lives** (D-01 / DATA-03). The ordering
key is documented on `protocol.py` lines 48-63 (`(source_event_id byte-order, state_id
tiebreak)`); the port has no ORDER-BY primitive, so sort core-side in Python:
```python
def _current(self, scope_id: str, belief_id: str) -> dict | None:
    states = self._backend.match_nodes(
        "BeliefState", {"scope_id": scope_id, "belief_id": belief_id, "status": "active"})
    if not states:
        return None
    return max(states, key=lambda s: (str(s["source_event_id"]), str(s["state_id"])))
```
Always compute `prior = self._current(...)` BEFORE the new `upsert_node`, inside the same
`unit_of_work` (Pitfall 3).

**revise ≡ expand shared `_append` body** (D-04 / OPS-01 / OPS-02). `state_id` minting uses
stdlib `uuid.uuid7()`; `value` is `json.dumps`-encoded at the port boundary (resolves DEF-02-01);
edges use `add_edge` with RAW STRING edge types (`HAS_REVISION` is NOT an `EdgeType` enum member —
D-07, enforced by the `EdgeType` closed set in `models.py` lines 43-55):
```python
def revise(self, scope_id, belief_id, value, source_event_id) -> BeliefState:
    return self._append(scope_id, belief_id, value, source_event_id, Status.active)
expand = revise   # D-04 class-body alias (or a one-line delegate)

def _append(self, scope_id, belief_id, value, source_event_id, status) -> BeliefState:
    with self._backend.unit_of_work():                          # exactly one (CHAIN-03)
        self._ensure_scope(scope_id)                            # D-06
        self._backend.upsert_node("Belief", belief_id, {"belief_id": belief_id})  # D-06
        prior = self._current(scope_id, belief_id)              # derived, BEFORE append (D-01)
        state_id = uuid.uuid7()
        props = {
            "state_id": str(state_id), "belief_id": belief_id, "scope_id": scope_id,
            "source_event_id": str(source_event_id),
            "value": json.dumps(value),                         # resolves DEF-02-01
            "status": status.value,
        }
        self._backend.upsert_node("BeliefState", state_id, props)
        self._backend.add_edge("HAS_REVISION", belief_id, str(state_id))  # hub form (D-07)
        if prior is not None:
            self._backend.add_edge("SUPERSEDES", str(state_id), prior["state_id"])
        return self._hydrate(props)                             # json.loads value back to opaque
```

**contract pattern** (D-05 / D-03 / OPS-03). World-scope structural guard is the FIRST statement,
before `unit_of_work` and any backend access (uses `WorldScopeContractionError` from
`errors.py` line 17); vacuity returns `None`; the retracted value COPIES the stored (already
JSON-encoded) prior value VERBATIM — do NOT re-`json.dumps` (Pitfall 2):
```python
def contract(self, scope_id, belief_id, source_event_id) -> None:
    if scope_id == WORLD_SCOPE_ID:                              # D-03 STRUCTURAL, before backend
        raise WorldScopeContractionError(...)
    with self._backend.unit_of_work():
        self._ensure_scope(scope_id)
        prior = self._current(scope_id, belief_id)
        if prior is None:
            return None                                         # D-05 vacuity: silent no-op
        state_id = uuid.uuid7()
        props = {
            "state_id": str(state_id), "belief_id": belief_id, "scope_id": scope_id,
            "source_event_id": str(source_event_id),
            "value": prior["value"],                            # D-05: copy STORED form verbatim
            "status": Status.retracted.value,
        }
        self._backend.upsert_node("BeliefState", state_id, props)
        self._backend.add_edge("HAS_REVISION", belief_id, str(state_id))
        self._backend.add_edge("SUPERSEDES", str(state_id), prior["state_id"])
        return None
```

**get_revision_chain pattern** (HIST-02 / D-07). Cross-scope (signature takes only `belief_id` —
Open Q2 A2); same ordering contract as `_current` but `sort`, not `max`:
```python
def get_revision_chain(self, belief_id: str) -> list[BeliefState]:
    states = self._backend.match_nodes("BeliefState", {"belief_id": belief_id})
    states.sort(key=lambda s: (str(s["source_event_id"]), str(s["state_id"])))
    return [self._hydrate(s) for s in states]
```

**`_hydrate` helper (the value-decode boundary)** — the inverse of the encode at write. Returns a
frozen `BeliefState` (model in `models.py` lines 77-93; fields `state_id: UUID`,
`source_event_id: UUID`, `value: Any`, `status: Status`). `json.loads(props["value"])` turns the
stored string back into the opaque value; cast id strings back to `UUID`:
```python
def _hydrate(self, props: dict) -> BeliefState:
    return BeliefState(
        state_id=props["state_id"], belief_id=props["belief_id"], scope_id=props["scope_id"],
        source_event_id=props["source_event_id"],
        value=json.loads(props["value"]), status=Status(props["status"]),
    )
```
(pydantic coerces the `state_id`/`source_event_id` strings to `UUID` at the seam.)

---

### `src/doxastica/backends/ladybug.py` (adapter, file-I/O / schema DDL)

**Analog:** the existing `_bootstrap_schema` edge-table loop in the SAME method.

**Existing edge-table loop to extend** (`ladybug.py` lines 172-176):
```python
for edge_type in ("SUPERSEDES", "DEPENDS_ON", "DERIVED_FROM"):
    self._exec(
        f"CREATE REL TABLE IF NOT EXISTS {ns}_{edge_type}"
        f"(FROM {ns}_BeliefState TO {ns}_BeliefState)"
    )
```

**New `HAS_REVISION` table to add** (hub shape `Belief → BeliefState`, D-07 / Open Q1 A1). It has
a DIFFERENT FROM/TO than the structural-edge loop above, so add it as its own `_exec` (not in the
loop). Place it after the `BeliefState` node table (lines 166-171) and before/after the edge loop:
```python
self._exec(
    f"CREATE REL TABLE IF NOT EXISTS {ns}_HAS_REVISION"
    f"(FROM {ns}_Belief TO {ns}_BeliefState)"          # hub: Belief -> BeliefState (D-07)
)
```
Conventions to preserve from this method: `IF NOT EXISTS` idempotency (proven by
`test_bootstrap_idempotent`, `test_backend_ladybug.py` lines 76-83); `{ns}_` namespace prefix is
the ONLY interpolated identifier (validated in `__init__` via `_NS_RE`, `ladybug.py` lines 89-92);
`CURRENT_STATE` is NOT created (D-01); update the docstring line 152 ("`HAS_REVISION` /
`CURRENT_STATE` arrive in Phase 3") to reflect that only `HAS_REVISION` lands.

**`add_edge` caveat — endpoint-label assumption** (`ladybug.py` lines 226-232): the current
`add_edge` hardcodes BOTH endpoints to `{ns}_BeliefState`:
```python
rel = f"{self._ns}_{edge_type}"
node = f"{self._ns}_BeliefState"
self._exec(
    f"MATCH (a:{node} {{state_id: $from}}), (b:{node} {{state_id: $to}}) "
    f"MERGE (a)-[:{rel}]->(b)", {"from": str(from_id), "to": str(to_id)})
```
The hub-form `HAS_REVISION` is `Belief → BeliefState` (from-endpoint is a `Belief`, keyed
`belief_id`, not a `BeliefState` keyed `state_id`). **This is a planner-grade flag:** either
(a) `add_edge` must generalize its endpoint labels/PKs per edge type, or (b) the planner picks the
chain-link `BeliefState → BeliefState` shape (Open Q1 alternative) so `add_edge` stays unchanged.
The CONTEXT/RESEARCH default is hub form — if kept, `add_edge` needs an endpoint-label map
(parallel to `_PK_BY_LABEL`). Resolve in the plan. The in-memory `add_edge` (`memory.py`
lines 71-83) is label-agnostic (keys on raw `str(from_id)`), so only ladybug is affected.

---

### `src/doxastica/backends/memory.py` (adapter / oracle, CRUD)

**Analog:** itself — no code change expected. The oracle stores props verbatim (`upsert_node`
lines 54-69) and is model-blind (returns raw `list[dict]`). The `json.dumps`/`json.loads`
encode/decode lives in `core.py` and runs identically for BOTH backends, so the oracle needs no
encoding logic. `add_edge` (lines 71-83) is already label-agnostic and accepts the raw
`HAS_REVISION` string with no schema. **Action: confirm parity via tests; do not edit unless a
test reveals a gap.** Listed for completeness because CONTEXT names "memory.py parity".

---

### `src/doxastica/__init__.py` + `WORLD_SCOPE_ID` constant (config / barrel)

**Analog:** the existing `__all__` re-export block (`__init__.py` lines 3-35) and the `StrEnum`/
constant declaration style in `models.py` (lines 24-55).

**Define** `WORLD_SCOPE_ID = "__world__"` (D-02) in `models.py` (alongside the taxonomy) OR a new
`src/doxastica/constants.py`. **Re-export** from `__init__.py` by adding it to the import block and
`__all__` (NVM imports it):
```python
# in __init__.py, mirror the existing pattern (lines 10-18, 21-35):
from doxastica.models import (..., Scope, Status)   # add WORLD_SCOPE_ID to the source it lives in
__all__ = [..., "WORLD_SCOPE_ID", ...]              # keep alphabetical, matches existing ordering
```
`core.py` imports `WORLD_SCOPE_ID` from wherever it is defined (function-blind, plain runtime
import — it is a `str`, not a driver).

---

### `tests/test_revision_spine.py` (test, request-response — NEW)

**Analog:** `tests/test_backend_parity.py` — same parametrized `backend` fixture, same
helper-builder + literal-assertion shape.

**Fixture-consumption + module-header convention** (`test_backend_parity.py` lines 29-42; fixture
in `conftest.py` lines 34-55). Every test takes `backend: BackendPort` so it runs once per backend
(`["memory", "ladybug"]`); ladybug is skipped (not failed) when the driver is absent:
```python
from __future__ import annotations
from typing import TYPE_CHECKING
import pytest
if TYPE_CHECKING:
    from doxastica.ports import BackendPort

def test_get_or_create_scope(backend: BackendPort) -> None:
    core = MemoryCore(backend)         # construct over the injected port (core.py line 50)
    ...
```
**Important:** these tests exercise `MemoryCore` (the op bodies), so construct
`MemoryCore(backend)` directly from the fixture's port — NOT `MemoryCore.in_memory()` (which would
ignore the parametrized ladybug backend). This is the one deviation from `test_backend_parity.py`,
which tests the bare port; here we test the core composed over the parametrized port.

**Helper-builder + sorted-normalize convention to mirror** (`test_backend_parity.py` lines 45-76):
small `_node`/`_scope` style helpers and `sorted(...)` normalizers keep assertions order-agnostic.

**Tests to write** (RESEARCH Test Map, lines 610-622): `test_get_or_create_scope` (idempotent),
`test_world_contract_raises` (raises before any write — use `pytest.raises(WorldScopeContractionError)`),
`test_cross_scope_divergence` (SCOPE-03), `test_belief_state_split` (CHAIN-01),
`test_revise_supersedes` (OPS-01), `test_expand_equals_revise` (OPS-02),
`test_contract_vacuity_and_acts` (OPS-03), `test_revision_chain_order` (HIST-02), plus a
retracted-value-byte-identical-to-superseded test (Pitfall 2) and a world-scope-round-trips-
`is_world=True`-as-real-`bool` test (Pitfall 4).

---

### `tests/test_invariants.py` (test, event-driven op-sequence — NEW, NO IN-REPO ANALOG)

**Analog:** none — Hypothesis is in the dev group (`pyproject.toml`) but no stateful machine
exists in the repo yet. Use the parametrized `backend` fixture from `conftest.py` for the
both-backends sweep and the CLAUDE.md "Testing stack — Hypothesis stateful" section + the
Hypothesis stateful docs (https://hypothesis.readthedocs.io/en/latest/stateful.html) as the
pattern source.

**Structure prescribed by CLAUDE.md + D-01** (the SC3 consistency check, RESEARCH lines 596-633):
- `RuleBasedStateMachine` with `Bundle`s tracking created scopes + beliefs (so later rules draw
  real ids, not random misses).
- `@initialize` spins up the throwaway backend once per example.
- `@rule` methods for `revise`/`expand`/`contract` that mirror each op into a shadow-dict oracle
  `self.model: dict[(scope, belief), current_value]`.
- `@invariant` for: (a) chain-immutability (no `BeliefState`/`HAS_REVISION` ever deleted —
  CHAIN-02), (b) current-selection is TOTAL + SINGLE-VALUED per `(scope, belief)` and chain-tail ≡
  `_current` (CHAIN-03 / D-01 consistency check, the keystone reframing).
- `@precondition` to gate `contract` on existing beliefs and route world-scope-contract into its
  own assertion.
- Generate colliding `source_event_id`s to exercise the `state_id` tiebreak (Pitfall 6).
- Run over BOTH backends (parametrize the machine's backend construction, mirroring the
  `conftest.py` `params=["memory", "ladybug"]` + `importorskip` skip-when-absent pattern).

This is the only file with no copy-from source in the repo; lean on the CLAUDE.md notes (which
specify `Bundle`/`@initialize`/`@invariant`/`@precondition` + shadow/oracle model verbatim) and
the `conftest.py` backend-selection idiom.

---

### `tests/test_backend_parity.py::test_value_string_round_trips_ladybug` (regression flip)

**Analog:** its passing sibling `test_value_string_round_trips_memory` (lines 292-296) — identical
assertion. Once the `json.dumps`/`json.loads` value-encoding contract lands in `core.py`, the
DEF-02-01 corruption is closed AT THE CORE BOUNDARY. **Subtlety:** the xfail test (lines 299-317)
asserts round-trip at the BARE PORT level (`backend.upsert_node` raw, no core encoding), where
ladybug still coerces — so flipping it requires routing the value through the core encode/decode,
OR re-pointing the test to assert via `MemoryCore.revise` + `get_revision_chain` (where encoding
applies). The planner must decide which: the encoding contract lives in `core.py`, not the port,
so the cleanest flip asserts through the core, not the bare port. Mirror the Phase-2
security-verification discipline (flip xfail → strict passing once closed). RESEARCH line 622 and
Wave-0 gap line 632 flag this.

---

## Shared Patterns

### Value encoding (the DEF-02-01 fix — the integrity deliverable)
**Source:** new in `core.py`; the contract the model docstring already promises (`models.py`
lines 5-9). **Apply to:** every write (`_append` encodes the opaque value once; `contract` copies
the already-encoded stored form verbatim) and every read (`_hydrate` decodes). Identical on BOTH
backends so the oracle stays byte-equal.
```python
stored = json.dumps(value)     # on write, in _append (opaque -> stored string)
opaque = json.loads(stored)    # on read, in _hydrate (stored string -> opaque)
# contract: store prior["value"] VERBATIM (already encoded) — do NOT re-dumps (Pitfall 2)
```

### Atomic per-op transaction
**Source:** `ladybug.py::unit_of_work` (lines 322-338, BEGIN/COMMIT/ROLLBACK);
`memory.py::unit_of_work` (lines 135-153, snapshot/restore). **Apply to:** every public write —
exactly one `with self._backend.unit_of_work():` per op (CHAIN-03); never nested, never multiple.

### Idempotent upsert keyed on the label PK
**Source:** `ladybug.py::upsert_node` (lines 178-210, `_PK_BY_LABEL` + PK excluded from SET loop);
`memory.py::upsert_node` (lines 54-69). **Apply to:** scope/belief/state creation in every op.
Pass the PK in props safely; re-upsert is a no-op. `BeliefState` keys on `state_id`, `Belief` on
`belief_id`, `Scope` on `scope_id` (`_PK_BY_LABEL`, `ladybug.py` line 86).

### Derived-current ordering contract (the ONE place ordering lives)
**Source:** new `_current`/`get_revision_chain` in `core.py`; semantics documented on
`protocol.py` lines 48-63. **Apply to:** every op (prior-current lookup) and the consistency
check. Key: `(str(source_event_id), str(state_id))`; `max` for current, `sort` for the chain.
Core-side Python only — the port has no ORDER-BY primitive.

### Driver-blind core
**Source:** `core.py` lines 18-22, 33-38 (TYPE_CHECKING-only port import; no ladybug). **Apply
to:** all `core.py` Phase-3 additions. `import json`/`import uuid` are stdlib (allowed at module
top); models/errors/`WORLD_SCOPE_ID` are first-party (allowed). NEVER `import ladybug`. Enforced
by `tests/test_import_purity.py`.

### Parametrized both-backends test fixture
**Source:** `conftest.py` lines 34-55 (`params=["memory", "ladybug"]` + `importorskip`).
**Apply to:** both new test files. Construct `MemoryCore(backend)` over the injected port so the
op bodies run on both adapters; ladybug skips (not fails) when the driver is absent.

### Structural edges as raw strings, NOT EdgeType members
**Source:** `models.py::EdgeType` closed set (lines 43-55, docstring explicitly excludes
`HAS_REVISION`/`CURRENT_STATE`). **Apply to:** every `add_edge("HAS_REVISION", ...)` and the
core's structural `add_edge("SUPERSEDES", ...)` — pass raw strings (D-07). `HAS_REVISION` never
becomes an enum member.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/test_invariants.py` | test | event-driven (op-sequence) | No Hypothesis stateful machine exists in the repo yet (hypothesis is a dev dep, unused). Use CLAUDE.md "Hypothesis stateful" notes + `conftest.py` fixture idiom + the Hypothesis stateful docs as the pattern source. |

---

## Planner-Grade Flags (resolve in PLAN.md)

1. **`add_edge` endpoint labels vs. `HAS_REVISION` hub shape (Open Q1).** The ladybug `add_edge`
   hardcodes both endpoints to `BeliefState` keyed `state_id` (`ladybug.py` lines 226-232). The
   hub-form `HAS_REVISION` (`Belief → BeliefState`) has a `Belief` from-endpoint keyed
   `belief_id`. Either generalize `add_edge` endpoint labels/PKs, or choose the chain-link
   `BeliefState → BeliefState` shape so `add_edge` stays unchanged. CONTEXT default = hub.

2. **Where `WORLD_SCOPE_ID` lives** — `models.py` vs new `constants.py` (Claude's Discretion).
   Either way, re-export from `__init__.py`.

3. **How to flip the DEF-02-01 xfail** — the encoding contract lives in `core.py`, not the bare
   port; the cleanest flip asserts the round-trip THROUGH `MemoryCore.revise` + `get_revision_chain`
   rather than the raw `backend.upsert_node` the current xfail uses.

4. **`expand = revise` alias vs one-line delegate** (D-04) — class-body alias keeps both names on
   the public surface (`protocol.py` lines 81-89 require both); confirm basedpyright-strict accepts
   the alias form, else use an explicit one-line delegate.

---

## Metadata

**Analog search scope:** `src/doxastica/` (all 7 modules) + `src/doxastica/backends/` + `tests/`
(all 8 files) + `.planning/phases/03-*/{CONTEXT,RESEARCH}.md`.
**Files scanned:** 15 source/test + 2 planning docs.
**Pattern extraction date:** 2026-06-16
