# Phase 9: Stance Value Layer, Write & Persistence - Pattern Map

**Mapped:** 2026-07-04
**Files analyzed:** 9 (5 production edits + 3 test edits/adds + 1 unchanged parity target)
**Analogs found:** 9 / 9 — every change has an exact in-repo sibling (this is a purely additive edit to a shipped, tightly-specified value layer)

> **Nature of this phase:** No greenfield files with "no analog." Every change threads a new
> `stance` field alongside the existing `value` / `status` fields, so the closest analog is
> almost always *the adjacent line for `value` or `status` in the very same function*. The
> planner should treat "copy the `value` idiom, with the one documented divergence" as the
> governing instruction. The single divergence (name-lookup vs value-lookup on hydrate) is
> called out explicitly under Shared Pattern 2 and Pitfall Map below.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/doxastica/models.py` — add `Stance` enum | model (taxonomy enum) | transform (value-layer) | `Status` / `EdgeType` `StrEnum` in same file (structural placement only; base class differs) | role-match (house-style, not base class) |
| `src/doxastica/models.py` — `stance` field on `BeliefState` | model (frozen field) | transform | `status: Status` field on same model | exact |
| `src/doxastica/core.py` — `_hydrate` | service (read boundary) | transform (deserialize) | adjacent `status=Status(props["status"])` line | exact-with-divergence (see Pitfall 1) |
| `src/doxastica/core.py` — `_append_state` | service (write helper) | CRUD (append) | adjacent `value: encoded_value` / `status.value` props-dict lines | exact |
| `src/doxastica/core.py` — `_append` | service (write spine) | CRUD (append) | how `value` is pre-encoded (`self._encode_value(value)`) before `_append_state` | exact |
| `src/doxastica/core.py` — `revise` / `expand` | service (API surface) | CRUD (append) | existing `revise`/`expand` signatures + `_append` delegate | exact |
| `src/doxastica/core.py` — `contract` | service (API surface) | CRUD (append) | the verbatim `prior["value"]` copy line in `contract` (D-02 sibling) | exact |
| `src/doxastica/protocol.py` — `revise` / `expand` sigs | route (Protocol contract) | request-response | existing `revise`/`expand` Protocol signatures | exact |
| `src/doxastica/backends/ladybug.py` — `_bootstrap_schema` DDL | config (schema DDL) | file-I/O (persist) | adjacent `value STRING, status STRING` columns in `{ns}_BeliefState` `CREATE NODE TABLE` | exact |
| `src/doxastica/backends/memory.py` | service (schemaless store) | CRUD | **NO CHANGE** — schemaless prop store carries `stance` free (parity target) | n/a |
| `tests/test_models_frozen.py` — retarget | test (unit) | — | `test_belief_state_field_set_is_the_closed_six` + `_make_belief_state` in same file | exact |
| `tests/test_stance.py` (NEW) | test (unit) | — | RESEARCH SC2 shapes; house style from `test_models_frozen.py` enum-membership tests | role-match |
| `tests/test_stance_persistence.py` (NEW) | test (parity) | — | `_assert_value_round_trips` + `test_retracted_value_byte_identical_to_superseded` + the `backend` fixture | exact |

## Pattern Assignments

### `src/doxastica/models.py` — add `Stance` enum (model, transform)

**Analog (structural placement / house style):** the `Status` and `EdgeType` `StrEnum`
declarations, `models.py` lines 37-61. Place `Stance` directly after `EdgeType` (line 61) and
before `Scope` (line 64), grouped with the taxonomy enums (RESEARCH Open Q2 recommendation).

**House-style analog** — existing closed-taxonomy enum with docstring citing its DATA/STANCE req:
```python
# models.py:37-47 — the placement + docstring pattern to mirror
class Status(StrEnum):
    """
    Belief-state status — the closed core taxonomy (DATA-06).

    Exactly two members. ...
    """

    active = "active"
    retracted = "retracted"
```

**Base-class DIVERGENCE (do NOT copy `StrEnum`):** `Stance` is a plain `Enum` +
`functools.total_ordering` (RESEARCH verified recipe, CONTEXT "Stance enum shape"). The
analog governs *placement and docstring house-style only*, not the base class. Drop-in from
RESEARCH lines 84-105:
```python
from enum import Enum          # add alongside the existing `from enum import StrEnum` (line 24)
from functools import total_ordering


@total_ordering
class Stance(Enum):
    """The canonical ordinal epistemic taxonomy (STANCE-01). ... Serialized as `.name`;
    hydrated via `Stance[token]` (name-lookup, NOT `Stance(token)`)."""

    doubted = 0
    suspected = 1
    believed = 2
    certain = 3

    def __lt__(self, other: object) -> bool:
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented
```

**Import wiring:** current top of file is `from enum import StrEnum` (line 24). Change to import
`Enum` too, and add `from functools import total_ordering`.

---

### `src/doxastica/models.py` — `stance` field on `BeliefState` (model, transform)

**Analog (exact):** the `status: Status` field, `models.py` line 99, inside the frozen
`BeliefState(BaseModel, frozen=True, extra="forbid")`.

**Current field block** (`models.py:94-99`) — add `stance: Stance` as the 7th field:
```python
    state_id: UUID
    belief_id: str
    scope_id: str
    source_event_id: UUID
    value: Any
    status: Status
    # + stance: Stance   <-- D-01: REQUIRED, NO model-level default (default lives on revise/expand)
```

**Docstring update:** line 87 says "Carries EXACTLY the closed six-field set". Retarget to
**seven** and mention `stance` (per Call-Site Inventory).

**Anti-pattern (RESEARCH):** do NOT write `stance: Stance = Stance.certain` — the model-level
default is forbidden by D-01; the default lives on the API methods only.

---

### `src/doxastica/core.py` — `_hydrate` (service, deserialize) — THE PHASE TRAP

**Analog (exact placement, ONE-LINE DIVERGENCE):** the `status=Status(props["status"])` line
inside `_hydrate`, `core.py` line 274.

**Current body** (`core.py:268-275`):
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

**Add (with the divergence):**
```python
            stance=Stance[props["stance"]],   # NAME-lookup — NOT Stance(props["stance"])
```

**CRITICAL DIVERGENCE (Pitfall 1, "single most likely bug"):** `status` uses `Status(...)`
(value-lookup) and works because `Status` is a `StrEnum` where value==name. `Stance.value` is an
integer rank, so `Stance("certain")` raises `ValueError`. Use subscript `Stance[props["stance"]]`
(name-lookup). Import `Stance` from `doxastica.models` (add to the existing import block at
`core.py:54-62`). Update the `_hydrate` docstring (lines 261-267) to note the name-lookup.

---

### `src/doxastica/core.py` — `_append_state` (service, append)

**Analog (exact):** the `value` and `status` entries in the manually-built props dict,
`core.py:303-310`. The helper receives `value` **already encoded** and never interprets it;
`stance` mirrors this exactly (D-02 Option A — receives the pre-serialized `.name` token).

**Current signature + props dict** (`core.py:278-311`):
```python
    def _append_state(
        self,
        scope_id: str,
        belief_id: str,
        encoded_value: str,
        source_event_id: UUID,
        status: Status,
        prior: dict[str, Any] | None,
    ) -> BeliefState:
        ...
        props: dict[str, Any] = {
            "state_id": str(state_id),
            "belief_id": belief_id,
            "scope_id": scope_id,
            "source_event_id": str(source_event_id),
            "value": encoded_value,   # caller-supplied stored form (encode policy is the caller's)
            "status": status.value,
            # + "stance": stance,     <-- str token, already .name; helper NEVER interprets it
        }
```

**Add:** a `stance: str` param (a pre-serialized token, exactly like `encoded_value: str`) and
`props["stance"] = stance`. Note `status.value` serializes inside the helper because `status`
arrives as a `Status` member — `stance` differs: it arrives **already a string** (serialized at
the write boundary), so it is stored raw with no `.value`/`.name` call here.

---

### `src/doxastica/core.py` — `_append` (service, append)

**Analog (exact):** how `value` is pre-encoded at the write boundary before delegation —
`self._encode_value(value)` passed positionally into `_append_state`, `core.py:341`.

**Current delegation** (`core.py:334-345`):
```python
        with self._backend.unit_of_work():
            self._ensure_scope(scope_id)
            self._backend.upsert_node("Belief", belief_id, {"belief_id": belief_id})
            prior = self._current(scope_id, belief_id)
            return self._append_state(
                scope_id,
                belief_id,
                self._encode_value(value),   # encode once on write (DEF-02-01)
                source_event_id,
                status,
                # + stance.name,             <-- D-02: serialize at the write boundary
                prior,
            )
```

**Add:** a `stance: Stance` param to `_append`; pass `stance.name` to `_append_state` (mirrors
`self._encode_value(value)` — serialize at the write boundary, exactly one place).

---

### `src/doxastica/core.py` — `revise` / `expand` (service, API surface)

**Analog (exact):** the two existing signatures, `core.py:348-372`, both one-line delegates to
`_append`.

**Current** (`core.py:348-356`):
```python
    def revise(
        self,
        scope_id: str,
        belief_id: str,
        value: Any,
        source_event_id: UUID,
    ) -> BeliefState:
        """AGM revision: append a new active ``BeliefState`` for ``belief_id`` (OPS-01)."""
        return self._append(scope_id, belief_id, value, source_event_id, Status.active)
```

**Add to BOTH `revise` and `expand`:** `stance: Stance = Stance.certain` param (STANCE-03 default
lives HERE, on the API surface — not the model), and pass `stance` through to `_append`. `expand`
(lines 358-372) gets the identical treatment (it is the D-04 mechanical twin).

---

### `src/doxastica/core.py` — `contract` (service, append) — D-02 verbatim sibling

**Analog (exact):** the verbatim `prior["value"]` copy in `contract`, `core.py:415`. Stance
copies `prior["stance"]` the same verbatim way — no decode/re-encode (STANCE-04 made
*structural*, the exact sibling of the existing verbatim-value copy).

**Current `_append_state` call inside contract** (`core.py:412-419`):
```python
            self._append_state(
                scope_id,
                belief_id,
                prior["value"],   # D-05: copy STORED form verbatim (no re-dumps, Pitfall 2)
                source_event_id,
                Status.retracted,
                # + prior["stance"],   <-- STANCE-04: stored token copied straight through
                prior,
            )
```

**Add:** `prior["stance"]` passed verbatim as the new `_append_state` stance arg. **No signature
change** to `contract` (it takes no stance param). **Anti-pattern (Pitfall 4):** do NOT write
`Stance[prior["stance"]].name` — that decode→re-encode weakens the verbatim guarantee.

---

### `src/doxastica/protocol.py` — `revise` / `expand` signatures (route, contract)

**Analog (exact):** the existing `revise` (lines 71-79) and `expand` (lines 81-89) Protocol
signatures, which mirror `core.py`.

**Current** (`protocol.py:71-79`):
```python
    def revise(
        self,
        scope_id: str,
        belief_id: str,
        value: Any,
        source_event_id: UUID,
    ) -> BeliefState:
        """AGM revision: append a new current ``BeliefState`` for ``belief_id``."""
        ...
```

**Add:** `stance: Stance = Stance.certain` to BOTH `revise` and `expand` (must stay in lockstep
with `core.py`). Import `Stance` under the existing `TYPE_CHECKING` block (`protocol.py:30-39`,
alongside `BeliefFilter`, `EdgeType`, etc.). **`contract` is unchanged** (takes no stance). Note
this module is import-purity-guarded (`test_import_purity.py`) — `Stance` is a `models` import,
which is allowed; do not add any driver import.

---

### `src/doxastica/backends/ladybug.py` — `_bootstrap_schema` DDL (config, persist)

**Analog (exact):** the `value STRING, status STRING` columns in the `{ns}_BeliefState`
`CREATE NODE TABLE`, `ladybug.py:232-235`.

**Current DDL** (`ladybug.py:231-236`):
```python
        self._exec(
            f"CREATE NODE TABLE IF NOT EXISTS {ns}_BeliefState"
            f"({_PK_BY_LABEL['BeliefState']} STRING, belief_id STRING, scope_id STRING, "
            f"source_event_id STRING, value STRING, status STRING, "
            f"PRIMARY KEY({_PK_BY_LABEL['BeliefState']}))"
        )
```

**Add:** `stance STRING` next to `value STRING, status STRING` (Pitfall 2 — `upsert_node` flows
props dynamically, so the DDL is the ONE place the column set is fixed; omitting the column gives a
ladybug binder error on `n.stance = $p`). `stance` is bound as a `$param` value with a fixed
identifier — no new injection surface (inherits the `_validate_identifier` guard already covering
`n.stance`). **Scope note (Pitfall 3, NOT a bug here):** the DDL is `IF NOT EXISTS`, so a
pre-existing on-disk DB won't gain the column — acceptable for clean v0.2.0 / fresh `:memory:`
tests; no ALTER/migration in scope. Flag if a real on-disk upgrade need surfaces.

---

### `src/doxastica/backends/memory.py` — NO CHANGE (parity target)

Schemaless prop store carries `stance` free. The work here is *confirming* byte-stable parity
with ladybug via the new persistence tests — no code edit.

---

### `tests/test_models_frozen.py` — retarget (test, unit) — 3 sites BREAK under D-01

**Analog (exact):** the file's own existing shapes. Three sites break because `stance` becomes a
required field:

1. `_make_belief_state()` (lines 24-32): add `stance=Stance.certain` to the direct constructor.
2. `test_belief_state_rejects_unknown_field` (lines 109-119): add `stance=Stance.certain` (keep
   the `provenance=` extra that must still raise `ValidationError`).
3. `test_belief_state_field_set_is_the_closed_six` (lines 59-67): retarget 6 → 7. Current:
```python
def test_belief_state_field_set_is_the_closed_six() -> None:
    assert set(BeliefState.model_fields) == {
        "state_id", "belief_id", "scope_id",
        "source_event_id", "value", "status",
    }
```
Rename to `..._closed_seven` and add `"stance"` to the set (RESEARCH shape, lines 353-358). Add
`Stance` to the `from doxastica.models import (...)` block (lines 15-21).

---

### `tests/test_stance.py` (NEW) — SC2 unit tests (test, unit)

**Analog:** RESEARCH SC2 shapes (lines 321-349); house-style precedent is the enum-membership
tests in `test_models_frozen.py` (e.g. `test_status_membership_is_exactly_active_and_retracted`,
lines 41-42). No backend fixture needed — pure type-level tests.

Covers STANCE-01 (total order + `sorted`), STANCE-06 (`+`/`*`/cross-type `<` raise `TypeError`
via `pytest.raises`), and the name-lookup guard (`Stance["certain"] is Stance.certain`;
`Stance("certain")` raises `ValueError`). **basedpyright note (Assumptions A1 / Open Q1):** the
arithmetic-negative lines need a narrow `# pyright: ignore[reportOperatorIssue]` (exact code TBD —
adopt whatever `prek run --all-files` names on first run).

---

### `tests/test_stance_persistence.py` (NEW) — SC4/SC5 parity tests (test, parity)

**Analog (exact):** `_assert_value_round_trips` (`test_backend_parity.py:460-480`) and
`test_retracted_value_byte_identical_to_superseded` (`test_revision_spine.py:211-221`), both
driven through `MemoryCore(backend)` over the parametrized `backend` fixture.

**Round-trip analog** (`test_backend_parity.py:471-479`) — the exact shape to mirror for
`test_stance_round_trips_byte_stable`:
```python
    core = MemoryCore(backend)
    state = core.revise("alice", "b1", _SHAPED_VALUE, uuid.uuid7())
    assert state.value == _SHAPED_VALUE
    chain = core.get_revision_chain("b1")
    assert chain[0].value == _SHAPED_VALUE
```

**Verbatim-preservation analog** (`test_revision_spine.py:211-221`) — the exact shape for
`test_contract_preserves_stance_verbatim`:
```python
def test_retracted_value_byte_identical_to_superseded(backend: BackendPort) -> None:
    core = MemoryCore(backend)
    active = core.revise("alice", "payload", {"nested": [1, 2, 3]}, _event_id())
    core.contract("alice", "payload", _event_id())
    retracted = core.get_revision_chain("payload")[-1]
    assert retracted.status.value == "retracted"
    assert retracted.value == active.value   # <-- swap to: retracted.stance is active.stance
```

**Fixture + helper to reuse:** the `backend` fixture (`conftest.py:34-55`, runs
`params=["memory", "ladybug"]`) and the local `_event_id()` helper
(`test_revision_spine.py:41-43`, returns `uuid.uuid7()`). New tests: round-trip a non-default
stance (`Stance.suspected`), default-to-`certain`, contract-verbatim, and get_scope_at
reconstruction — all four assert `state.stance is Stance.<member>` (member identity, name-hydrated).
RESEARCH SC4/SC5 shapes at lines 283-319 are the drop-in.

## Shared Patterns

### Pattern 1 — Threading a new field alongside `value`/`status` through the write spine
**Source:** `core.py` `_append_state` (props dict, lines 303-310) → `_append`
(`self._encode_value(value)` pre-encode, line 341) → `contract` (`prior["value"]` verbatim,
line 415).
**Apply to:** every `stance` edit in `core.py`.
The whole persistence path is byte-identical to how `value` already flows. Serialize at the write
boundary (`_append`: `stance.name`; mirrors `_encode_value(value)`); copy verbatim in `contract`
(`prior["stance"]`; mirrors `prior["value"]`); store the raw token in the props dict
(`_append_state`; mirrors `value: encoded_value`).

### Pattern 2 — `.name` serialize / `Stance[...]` hydrate (the locked discipline, ONE divergence)
**Source:** the existing `status=Status(props["status"])` hydrate line (`core.py:274`) and the
`.name`-token house style (CLAUDE.md).
**Apply to:** the `_hydrate` `stance` reconstruction, and every persist/read of stance.
Serialize via `.name` (`"certain"`), NOT `.value` (the integer rank). Hydrate via
`Stance[props["stance"]]` (subscript = name-lookup), **NOT** `Stance(props["stance"])`
(value-lookup — a blind copy of the adjacent `Status(...)` idiom, which works only because
`Status` is a `StrEnum`). This is the single most likely bug in the phase (CONTEXT + RESEARCH
Pitfall 1). Never serialize stance via pydantic `model_dump()` — it emits the integer rank
(`"stance":3`), diverging from the `.name` wire form.

### Pattern 3 — Parametrized dual-backend parity via the `backend` fixture
**Source:** `conftest.py:34-55` (`@pytest.fixture(params=["memory", "ladybug"])`) +
`_assert_value_round_trips` (`test_backend_parity.py:460-480`).
**Apply to:** all `test_stance_persistence.py` tests.
Any test taking `backend: BackendPort` runs once per backend; `importorskip` skips (never fails)
the ladybug param when the driver is absent. Drive assertions through `MemoryCore(backend)`, NOT
the bare port — the serialize/hydrate discipline lives in `core.py`, so byte-stability must be
proven at the core boundary on both backends.

### Pattern 4 — Closed-taxonomy enum house style
**Source:** `models.py:37-61` (`Status`, `EdgeType`) + their membership tests
(`test_models_frozen.py:41-56`).
**Apply to:** the new `Stance` enum + its `test_stance.py` order/membership tests.
Enum lives in `models.py` grouped with the other taxonomy enums; carries a docstring citing its
requirement ID; closedness/behavior proven by a dedicated unit test. Only divergence: `Stance` is
ordered (`total_ordering` + plain `Enum`), the first ordered enum in the codebase — `Status` /
`EdgeType` stay unordered `StrEnum`s.

## Pitfall Map (the divergences from the `value`/`status` analogs)

| # | Where | The trap (copying the analog blindly) | The fix |
|---|-------|---------------------------------------|---------|
| 1 | `_hydrate` (`core.py:274`) | `Stance(props["stance"])` — copies the `Status(...)` value-lookup idiom → `ValueError` on every read | `Stance[props["stance"]]` (name-lookup) |
| 2 | ladybug DDL (`ladybug.py:234`) | forgetting `stance STRING` → ladybug binder error on `n.stance = $p` | add `stance STRING` next to `value STRING, status STRING` |
| 3 | ladybug DDL `IF NOT EXISTS` | expecting an on-disk DB to gain the column | out of scope — clean v0.2.0 / `:memory:` only; flag if real upgrade need surfaces |
| 4 | `contract` (`core.py:415`) | `Stance[prior["stance"]].name` (decode→re-encode) | pass `prior["stance"]` verbatim (STANCE-04 structural) |
| 5 | `models.py` field | `stance: Stance = Stance.certain` model default | REQUIRED field, no default (D-01); default lives on `revise`/`expand` |

## No Analog Found

None. This phase is purely additive over a shipped value layer; every change has an exact or
near-exact in-repo sibling (the adjacent `value` / `status` line). The planner should NOT fall
back to RESEARCH-only patterns — the codebase analogs above are authoritative.

## Metadata

**Analog search scope:** `src/doxastica/{models,core,protocol}.py`, `src/doxastica/backends/{ladybug,memory}.py`, `tests/{conftest,test_models_frozen,test_revision_spine,test_backend_parity}.py`
**Files scanned:** 9 (all read fully or by targeted section; no re-reads)
**Pattern extraction date:** 2026-07-04
