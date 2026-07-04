# Phase 9: Stance Value Layer, Write & Persistence - Research

**Researched:** 2026-07-04
**Domain:** Python `enum` ordering semantics + pydantic v2 frozen-model evolution + append-only serialization discipline (internal library change; zero new dependencies)
**Confidence:** HIGH

## Summary

This phase adds a single ordered enum (`Stance`) and a single required field (`stance`) to an
already-shipped, tightly-specified value layer. There is almost no design freedom left — CONTEXT
D-01/D-02 and REQUIREMENTS STANCE-01…06 lock the shape — so the research value is entirely in
*verifying the two mechanisms that could silently go wrong* and *enumerating the exact call sites
the change touches*. Both mechanisms were verified empirically against the project's own Python
3.14 + pydantic v2, not from memory.

The two verified mechanisms: (1) a **plain `Enum` + `functools.total_ordering` + `.value`-comparing
`__lt__`** gives a genuine total order while leaving `+`, `*`, and cross-type `<`/`>` raising
`TypeError` at the type level — every STANCE-06 assertion passes exactly as written; (2) pydantic v2
validates a plain-`Enum` field **by VALUE, not by name** — so `stance="certain"` (the `.name` wire
token) *raises* `ValidationError`, while `stance=3` coerces. This is the load-bearing trap of the
phase: the core's persisted wire form is the `.name` token (`"certain"`), so `_hydrate` **must**
reconstruct the member via `Stance[props["stance"]]` *before* handing it to `BeliefState(...)`, never
pass the raw stored string. The existing `_hydrate` already does the identical thing for `status`
via `Status(props["status"])` — but note `Status` is a `StrEnum` where value==name, so a naive
copy of that idiom (`Stance(props["stance"])`) would silently break. The name/value asymmetry is the
whole reason CONTEXT flags this as "the single most likely bug."

**Primary recommendation:** Land `Stance` in `models.py` exactly as the verified recipe below;
thread `stance.name` through `_append_state` (D-02 Option A) and `Stance[props["stance"]]` through
`_hydrate`; add the `stance STRING` DDL column; and fix the four enumerated `BeliefState`-construction
/ field-count sites. The byte-stable round-trip and TypeError tests are small and mirror existing
`test_revision_spine.py` / `test_backend_parity.py` shapes.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `Stance` enum + total order + arithmetic-forbidding | Value layer (`models.py`) | — | It is a frozen taxonomy type; sits beside `Status`/`EdgeType`. First *ordered* enum in the codebase. |
| Accept `stance` on write, default `certain` | Core write spine (`core.py` `revise`/`expand`) + Protocol (`protocol.py`) | — | The API surface owns the "core default, NVM overrides" default (STANCE-03); the model field stays required (D-01). |
| Serialize `.name` → stored token | Core write boundary (`_append`, `contract`) | — | Same tier that owns `_encode_value`; the token is built in the manually-constructed props dict, NOT via pydantic serialization. |
| Persist the `stance` token | Backend adapters (ladybug DDL column; memory schemaless) | — | Ladybug needs a `stance STRING` column; in-memory carries it free. Parity is the target, not new logic. |
| Reconstruct member on read | Core read boundary (`_hydrate`) | — | `Stance[token]` name-lookup; feeds every read surface (`query_scope`, `get_scope_at`, `get_revision_chain`, `get_impact`). |

## Standard Stack

No new packages. This phase uses only what the library already depends on.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stdlib `enum` (`Enum`) | py3.14 | Base for `Stance` | Plain `Enum` (NOT `IntEnum`/`StrEnum`) is the only base that leaves arithmetic unreachable (STANCE-01/06). `[VERIFIED: local run 2026-07-04]` |
| stdlib `functools.total_ordering` | py3.14 | Synthesize `>`, `>=`, `<=` from `__lt__` + `__eq__` | Standard recipe for a total order over a hand-written `__lt__`; does NOT swallow the `TypeError` (verified). `[VERIFIED: local run]` |
| `pydantic` | `>=2.11,<3` (installed 2.13.x) | Frozen `BeliefState` field validation | Already the sole required runtime dep; validates the new `stance: Stance` field at the seam. `[VERIFIED: local run]` |

### Supporting (test only — already present)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=8` (installed 9.x) | The SC2/SC4 targeted tests | Type-level `TypeError` asserts + byte-stable round-trip. |
| `hypothesis` | `>=6.155` | NOT in Phase 9 scope | The oracle-widening / property carry of stance is **STANCE-07, Phase 10**. Do not add here. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| plain `Enum` + `total_ordering` | `IntEnum` | REJECTED by STANCE-01: inherits `int`'s full numeric protocol → `+`/`*`/int-`<` all become reachable, contradicting STANCE-06. |
| plain `Enum` + `total_ordering` | `StrEnum` | REJECTED: lexical order is wrong (`"believed" < "certain" < "doubted"…`) and `+` concatenates. |
| explicit integer rank in `.value` | `enum.auto()` | Fine mechanically, but an explicit `0/1/2/3` rank makes the order self-documenting and is what STANCE-01 specifies. |

**Installation:** None. `uv sync --locked --dev --extra ladybug` (the existing verification env) already covers it.

## Package Legitimacy Audit

**N/A — this phase installs no external packages.** All symbols used (`enum.Enum`,
`functools.total_ordering`, `pydantic.BaseModel`) are stdlib or the already-locked `pydantic`
dependency. No registry lookup required.

## The Verified `Stance` Recipe (drop-in, matches house style)

```python
# models.py — beside Status / EdgeType (the first *ordered* enum in the codebase)
from enum import Enum
from functools import total_ordering


@total_ordering
class Stance(Enum):
    """
    The canonical ordinal epistemic taxonomy (STANCE-01).

    A *total order* doubted < suspected < believed < certain. Comparison is the ONLY
    operation: `+`/`*`/cross-type `<` each raise TypeError at the type level (STANCE-06).
    Plain `Enum` (not IntEnum/StrEnum) so no numeric protocol leaks; the integer `.value`
    is the rank, used ONLY inside `__lt__` and NEVER exposed as an operable number.
    Serialized as its `.name` token ("certain"); hydrated via `Stance[token]` (name-lookup,
    NOT `Stance(token)` — value-lookup would fail on the token).
    """

    doubted = 0
    suspected = 1
    believed = 2
    certain = 3

    def __lt__(self, other: object) -> bool:
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented
```

**Verified behavior `[VERIFIED: local run 2026-07-04, uv run python, py3.14 + pydantic 2.13]`:**

| Expression | Result |
|------------|--------|
| `doubted < suspected < believed < certain` | `True` |
| `certain > doubted`, `certain >= certain`, `doubted <= certain` | `True` (synthesized by `total_ordering`) |
| `certain == certain`, `certain != doubted` | `True` (Enum identity) |
| `sorted([certain, doubted, believed])` | `[doubted, believed, certain]` |
| `Stance.certain + Stance.doubted` | **`TypeError`** ("unsupported operand type(s) for +") |
| `Stance.certain * 2` | **`TypeError`** |
| `Stance.believed < 5` and `5 < Stance.believed` | **`TypeError`** ("'<' not supported between…") |
| `Stance.certain.name` / `.value` | `"certain"` / `3` |
| `Stance["certain"]` (name-lookup) | `Stance.certain` ✅ |
| `Stance("certain")` (value-lookup) | **`ValueError`** ❌ ← the trap |
| `Stance(3)` (value-lookup by rank) | `Stance.certain` |

## Architecture Patterns

### Data-flow (write → persist → read)

```
revise/expand(stance=Stance.certain default)   contract(no stance arg)
        |                                              |
        | stance.name  ("certain")                     | prior["stance"] (stored token, VERBATIM)
        v                                              v
   _append  ---------- stance token ----------->  _append_state(..., stance: str, ...)
                                                        |
                                    props["stance"] = <token>   (manual dict — NOT pydantic dump)
                                                        v
                                        backend.upsert_node("BeliefState", ...)
                                                        |
                          ladybug: stance STRING column | memory: schemaless prop
                                                        v
                                        match_nodes(...) -> props{"stance": "certain"}
                                                        v
                            _hydrate:  Stance[props["stance"]]   (name-lookup → member)
                                                        v
                              BeliefState(stance=<Stance member>, ...)   (frozen, validated)
```

The entire persistence path is byte-identical to how `value` and `status` already flow — the only
new subtlety is the name/value asymmetry at the `_hydrate` reconstruction.

### Pattern 1: `.name` serialize / `Stance[...]` hydrate (the locked discipline)
**What:** Store the member's `.name` token; reconstruct with name-based subscript lookup.
**When to use:** Every persist/read of `stance`.
**Example:**
```python
# WRITE — _append (in core.py), mirroring how value is pre-encoded:
return self._append_state(
    scope_id, belief_id,
    self._encode_value(value),
    source_event_id, status,
    stance.name,              # <-- D-02 Option A: serialize at the write boundary
    prior,
)

# WRITE — contract, mirroring the verbatim prior["value"] copy (Pitfall 2 sibling):
self._append_state(
    scope_id, belief_id,
    prior["value"],           # value token verbatim
    source_event_id, Status.retracted,
    prior["stance"],          # <-- stance token verbatim (STANCE-04, structural)
    prior,
)

# _append_state — store the token unchanged in the manual props dict:
props["stance"] = stance      # a str, already the .name token; helper NEVER interprets it

# READ — _hydrate (the trap):
stance=Stance[props["stance"]],   # NAME-lookup ✅  — NOT Stance(props["stance"]) ❌
```

### Anti-Patterns to Avoid
- **`Stance(props["stance"])` in `_hydrate`** — copies the `status=Status(props["status"])` idiom
  blindly. `Status` is a `StrEnum` (value==name) so it works there; `Stance.value` is an integer
  rank, so value-lookup on the `"certain"` token raises `ValueError`. Use `Stance[...]`.
- **Serializing stance via `model_dump()`/`model_dump_json()`** — pydantic emits the **integer
  rank** (`"stance":3`) for a plain-Enum field `[VERIFIED: local run]`. The core never persists via
  pydantic serialization (it builds the props dict by hand), so there is no conflict — but do NOT
  introduce a pydantic-serialization persistence path for stance; it would diverge from the `.name`
  wire form and break byte-stability.
- **A model-level default `stance: Stance = Stance.certain`** — forbidden by D-01. The default lives
  on the API methods (`revise`/`expand`), not the model.
- **Passing the `.name` string into `BeliefState(...)` directly** — pydantic validates by value and
  raises `ValidationError` (type `"enum"`) `[VERIFIED: local run]`. Always construct with a real
  `Stance` member (which `_hydrate`'s `Stance[...]` guarantees).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Total order over the enum | Custom `__gt__`/`__ge__`/`__le__` | `functools.total_ordering` + one `__lt__` | Verified it synthesizes the rest AND preserves the `NotImplemented`→`TypeError` path. Hand-writing four dunders invites an inconsistency. |
| Reject arithmetic | A `__add__`/`__mul__` that raises | Just use plain `Enum` | The plain-`Enum` base *already* defines no `__add__`/`__mul__`, so `+`/`*` raise for free. Adding raising dunders is dead code. |
| Reject cross-type `<` | Explicit isinstance-raise in `__lt__` | `return NotImplemented` for the non-`Stance` branch | Verified `NotImplemented` from `__lt__` makes Python raise `TypeError` on `<` with an int. Raising directly would break the `total_ordering` reflection contract. |
| stance wire form | A new serializer | The manual props dict `.name` idiom already used for `status` | Same tier, same discipline; keeps both backends byte-identical. |

**Key insight:** The requirement's negative guarantees (STANCE-06) are satisfied by *choosing the
minimal base class*, not by *adding guard code*. The correct implementation is almost entirely
subtractive.

## Common Pitfalls

### Pitfall 1: value-lookup on the stored token (THE phase bug)
**What goes wrong:** `_hydrate` uses `Stance(props["stance"])`, raising `ValueError` on every read.
**Why it happens:** Muscle-memory copy of the adjacent `status=Status(props["status"])` line, which
is a `StrEnum` where value==name.
**How to avoid:** Use `Stance[props["stance"]]` (subscript = name-lookup). CONTEXT flags this
explicitly; the plan's `_hydrate` task must call it out.
**Warning signs:** `ValueError: 'certain' is not a valid Stance` on the first `query_scope`.

### Pitfall 2: forgetting the ladybug `stance STRING` DDL column
**What goes wrong:** `upsert_node` sends `n.stance = $p` against a table with no `stance` column →
ladybug error.
**Why it happens:** `upsert_node` flows props dynamically; the DDL is the only place the column set
is fixed. The `BeliefState` NODE TABLE (`ladybug.py` `_bootstrap_schema`) hardcodes
`... value STRING, status STRING ...`.
**How to avoid:** Add `stance STRING` to the `{ns}_BeliefState` `CREATE NODE TABLE` DDL, next to
`value STRING, status STRING`.
**Warning signs:** ladybug binder error naming an unknown property `stance`.

### Pitfall 3: the `CREATE ... IF NOT EXISTS` non-migration (scope boundary, not a bug here)
**What goes wrong:** A *pre-existing on-disk* ladybug DB won't gain the new column, because the DDL
is `IF NOT EXISTS`.
**Why it's acceptable:** **Verified** the test suite never reuses an on-disk ladybug DB across schema
versions — every ladybug backend is built from a fresh in-memory `lb.Database()` / `:memory:` (see
`conftest.py`, `test_backend_ladybug.py` all use `LadybugBackend.open(":memory:")`, and the
Hypothesis suites build a fresh `lb.Database(max_db_size=…)` per example). Clean v0.2.0 installs and
`:memory:` tests always get the 7-column table. `[VERIFIED: grep of tests/, 2026-07-04]`
**How to avoid:** No ALTER/migration is in scope. If a real on-disk-upgrade need surfaces later,
flag it — but nothing in the current suite hits it.

### Pitfall 4: contract re-encoding the stance token
**What goes wrong:** `contract` does `Stance[prior["stance"]].name` (decode→re-encode) instead of
passing `prior["stance"]` verbatim — weakening STANCE-04's *structural* verbatim guarantee to an
incidental identity round-trip.
**Why it happens:** Symmetry pressure to "normalize" before storing.
**How to avoid:** D-02: `contract` passes `prior["stance"]` straight through, exactly like the
existing `prior["value"]` verbatim copy. The helper never interprets stance.

## Call-Site Inventory (exhaustive — every place the change touches)

Verified by grep of `BeliefState(`, `.revise(`, `.expand(`, and field-count assertions across
`src/` and `tests/` on 2026-07-04.

### Production code (must change)
| File / symbol | Change |
|---------------|--------|
| `src/doxastica/models.py` — add `Stance` | New enum (recipe above); update `from enum import StrEnum` → also import `Enum` + `functools.total_ordering`. |
| `models.py` — `BeliefState` | Add `stance: Stance` field (6→7); update the "closed six-field set" docstring (line ~87) to seven. |
| `src/doxastica/core.py` — `_hydrate` (line ~268) | Add `stance=Stance[props["stance"]]`; import `Stance`; update docstring. |
| `core.py` — `_append_state` (line ~278) | Add `stance: str` param; set `props["stance"] = stance`. |
| `core.py` — `_append` (line ~317) | Add `stance: Stance` param; pass `stance.name` to `_append_state`. |
| `core.py` — `revise` / `expand` (lines ~348/358) | Add `stance: Stance = Stance.certain` param (STANCE-03 default); pass through to `_append`. |
| `core.py` — `contract` (line ~374) | Pass `prior["stance"]` verbatim as the new `_append_state` stance arg (STANCE-04). No signature change (contract takes no stance). |
| `core.py` — `get_impact` comment (line ~482) | Doc-only: "all six BeliefState fields" → seven. |
| `src/doxastica/protocol.py` — `revise` / `expand` | Add `stance: Stance = Stance.certain` to both signatures; import `Stance` under `TYPE_CHECKING`. `contract` unchanged. |
| `src/doxastica/backends/ladybug.py` — `_bootstrap_schema` | Add `stance STRING` to the `{ns}_BeliefState` `CREATE NODE TABLE` DDL. |
| `src/doxastica/backends/memory.py` | **No change** — schemaless prop store carries `stance` free (parity target). |

### Tests that BREAK under D-01 (required field) and must be updated
| File / test | Why it breaks | Fix |
|-------------|---------------|-----|
| `tests/test_models_frozen.py::_make_belief_state` (line 25) | Direct `BeliefState(...)` with 6 fields → `ValidationError: missing` | Add `stance=Stance.certain`. |
| `tests/test_models_frozen.py::test_belief_state_rejects_unknown_field` (line 111) | Same direct construction | Add `stance=Stance.certain` (keep the `provenance=` extra that must still raise). |
| `tests/test_models_frozen.py::test_belief_state_field_set_is_the_closed_six` (line 59) | Asserts the field set is exactly six | Rename/retarget to the closed **seven** including `"stance"`. |

**No other direct `BeliefState(...)` construction exists** — all other tests obtain states via
`core.revise(...)` (which supplies the default), so they are **unaffected** by STANCE-03's optional
param (verified: `revise`/`expand` callers across `test_revision_spine.py`, `test_invariants.py`,
`test_cascade.py`, `test_irony_join.py`, `test_query_scope.py`, `test_scope_at.py`,
`test_backend_parity.py`, `test_recovery_xfail.py` all omit stance and stay green).

## Code Examples (test shapes — mirror existing house style)

### SC4 — byte-stable round-trip on BOTH backends (mirror `test_backend_parity.py::_assert_value_round_trips`)
```python
# Parametrized by the `backend` fixture (conftest.py) → runs on memory AND ladybug.
def test_stance_round_trips_byte_stable(backend: BackendPort) -> None:
    """STANCE-03: a non-default stance survives revise → query_scope unchanged on both backends."""
    core = MemoryCore(backend)
    core.revise("alice", "b1", "v", _event_id(), stance=Stance.suspected)
    [state] = core.query_scope("alice", BeliefFilter())
    assert state.stance is Stance.suspected      # member identity, name-hydrated
    assert state.stance.name == "suspected"       # the stored wire token

def test_stance_defaults_to_certain(backend: BackendPort) -> None:
    """STANCE-03: omitting stance defaults to certain (existing callers unaffected)."""
    core = MemoryCore(backend)
    core.revise("alice", "b1", "v", _event_id())
    [state] = core.query_scope("alice", BeliefFilter())
    assert state.stance is Stance.certain
```

### SC5 — contract preserves stance verbatim; get_scope_at reconstructs (mirror `test_retracted_value_byte_identical_to_superseded`)
```python
def test_contract_preserves_stance_verbatim(backend: BackendPort) -> None:
    """STANCE-04: the retracted tail carries the prior stance unchanged."""
    core = MemoryCore(backend)
    active = core.revise("alice", "p", "v", _event_id(), stance=Stance.believed)
    core.contract("alice", "p", _event_id())
    retracted = core.get_revision_chain("p")[-1]
    assert retracted.status is Status.retracted
    assert retracted.stance is active.stance      # verbatim, no decode/re-encode

def test_get_scope_at_reconstructs_stance(backend: BackendPort) -> None:
    """STANCE-05: time-travel round-trips stance along with the rest of the state."""
    core = MemoryCore(backend)
    s = core.revise("alice", "p", "v", _event_id(), stance=Stance.suspected)
    [state] = core.get_scope_at("alice", s.source_event_id)
    assert state.stance is Stance.suspected       # no dedicated code — _hydrate does it
```

### SC2 — type-level TypeError guarantees (unit; no backend needed)
```python
import pytest
from doxastica.models import Stance

def test_stance_total_order() -> None:
    assert Stance.doubted < Stance.suspected < Stance.believed < Stance.certain
    assert sorted([Stance.certain, Stance.doubted]) == [Stance.doubted, Stance.certain]

@pytest.mark.parametrize("op", [
    lambda: Stance.certain + Stance.doubted,   # type: ignore[operator]
    lambda: Stance.certain * 2,                # type: ignore[operator]
    lambda: Stance.believed < 5,               # type: ignore[operator]
    lambda: Stance.believed > 5,               # type: ignore[operator]
])
def test_stance_arithmetic_and_cross_type_raise(op) -> None:
    with pytest.raises(TypeError):
        op()

def test_stance_hydration_is_name_based() -> None:
    # guards Pitfall 1 directly
    assert Stance["certain"] is Stance.certain
    with pytest.raises(ValueError):
        Stance("certain")   # value-lookup on the token must fail — proves the .name discipline
```
*(Note the `# type: ignore[operator]` markers: basedpyright-strict will statically flag these as
invalid operations — which is itself part of the guarantee. Confirm the exact ignore code during
implementation; strict mode may report `reportOperatorIssue`. A `pyright: ignore[...]` narrow-scoped
to those lines keeps the suite clean.)*

### `test_models_frozen.py` field-set update
```python
def test_belief_state_field_set_is_the_closed_seven() -> None:
    assert set(BeliefState.model_fields) == {
        "state_id", "belief_id", "scope_id",
        "source_event_id", "value", "status", "stance",
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `BeliefState` = closed **6** fields | closed **7** fields (adds `stance`) | Phase 9 (this) | Decision-grade value-layer edit; the `test_belief_state_field_set` guard and docstring move to seven. |
| `revise`/`expand(scope, belief, value, event)` | `+ stance: Stance = certain` | Phase 9 | Backward-compatible optional param; DOCS-01 (Phase 10) refreshes doc-site signature refs. |
| unordered `StrEnum`s only (`Status`,`EdgeType`) | first **ordered** enum (`Stance`) | Phase 9 | New enum idiom (`total_ordering`) lands beside the existing StrEnums; they stay unordered. |

**Deprecated/outdated:** none — this is purely additive.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | basedpyright-strict flags the arithmetic-negative test lines and needs `# pyright: ignore[reportOperatorIssue]` (exact code TBD at implementation) | Code Examples SC2 | LOW — the runtime `pytest.raises(TypeError)` still passes; only the strict-lint gate needs the correct ignore code. Confirm on first `prek` run. |

*All other claims are `[VERIFIED: local run]` against py3.14 + pydantic 2.13, or `[VERIFIED: grep]`
against the actual tree. This table is intentionally short — the phase is well-specified.*

## Open Questions

1. **Exact basedpyright ignore code for the arithmetic-negative asserts.**
   - What we know: strict mode will reject `Stance.certain + Stance.doubted` and `Stance.believed < 5`
     statically (that rejection is *part of* the STANCE-06 guarantee).
   - What's unclear: whether the code is `reportOperatorIssue` (likely) or `reportGeneralTypeIssues`.
   - Recommendation: write the tests, run `uv sync --locked --dev --extra ladybug && prek run
     --all-files`, and adopt whatever narrow `# pyright: ignore[...]` code basedpyright names.

2. **Placement of `Stance` within `models.py` (Claude's discretion per CONTEXT).**
   - Recommendation: directly after `EdgeType` and before `Scope`, grouped with the other taxonomy
     enums; add `Enum`/`total_ordering` imports at the top alongside the existing `StrEnum` import.

## Environment Availability

No external tooling beyond the already-present dev stack. Verified installed / green on the target:

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | `uuid.uuid7`, `enum`, `functools` | ✓ | 3.14 (locked floor) | — |
| pydantic | `BeliefState` field validation | ✓ | 2.13.x | — |
| pytest | SC2/SC4/SC5 tests | ✓ | 9.x | — |
| ladybug (extra) | SC4 ladybug-backend round-trip | ✓ (sync with `--extra ladybug`) | 0.17.1 | tests SKIP (not fail) when absent — existing conftest `importorskip` |

**Missing dependencies:** none.

## Validation Architecture

> `nyquist_validation: true` — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x (+ pytest-cov 6.x) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_models_frozen.py tests/test_revision_spine.py -x -q` |
| Full suite command | `uv sync --locked --dev --extra ladybug && prek run --all-files` (CI parity) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STANCE-01 | `Stance` total order `doubted<…<certain` | unit | `pytest tests/test_stance.py::test_stance_total_order -x` | ❌ Wave 0 |
| STANCE-02 | `BeliefState` closed **seven**-field set | unit | `pytest tests/test_models_frozen.py::test_belief_state_field_set_is_the_closed_seven -x` | ⚠️ retarget existing 6→7 |
| STANCE-03 | optional `stance` default `certain`; byte-stable round-trip both backends | parity | `pytest tests/test_stance_persistence.py -x` (uses `backend` fixture) | ❌ Wave 0 |
| STANCE-04 | `contract` preserves prior stance verbatim | parity | `pytest tests/test_stance_persistence.py::test_contract_preserves_stance_verbatim -x` | ❌ Wave 0 |
| STANCE-05 | `get_scope_at` reconstructs stance | parity | `pytest tests/test_stance_persistence.py::test_get_scope_at_reconstructs_stance -x` | ❌ Wave 0 |
| STANCE-06 | `+`/`*`/cross-type `<` raise `TypeError` | unit | `pytest tests/test_stance.py::test_stance_arithmetic_and_cross_type_raise -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_stance.py tests/test_models_frozen.py -x -q`
- **Per wave merge:** full parity suite incl. ladybug — `uv run pytest -q` (with `--extra ladybug` synced)
- **Phase gate:** `uv sync --locked --dev --extra ladybug && prek run --all-files` green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_stance.py` — SC2 type-level order + arithmetic-TypeError + name-lookup guard (STANCE-01/06)
- [ ] `tests/test_stance_persistence.py` — SC4/SC5 round-trip, default, contract-verbatim, get_scope_at (STANCE-03/04/05), parametrized on the existing `backend` fixture
- [ ] Retarget `tests/test_models_frozen.py::test_belief_state_field_set_is_the_closed_six` → seven, and add `stance=` to the two direct constructors
- [ ] No framework install needed — pytest/hypothesis/ladybug already in the dev+extra groups

*(Discretion per CONTEXT: the two new files may instead be folded into `test_revision_spine.py` /
`test_backend_parity.py` alongside the sibling `value` round-trip tests — either satisfies SC4/SC5.
The full Hypothesis oracle-widening is **STANCE-07, Phase 10**, explicitly out of scope here.)*

## Security Domain

> `security_enforcement` absent → treated as enabled. This is an internal value-layer change with no
> new input surface, so the applicable footprint is narrow.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `stance` is a **closed** `Stance` enum at the pydantic seam — an out-of-taxonomy value raises `ValidationError` by construction (same closed-taxonomy guarantee as `Status`/`EdgeType`). No free string enters. |
| V6 Cryptography | no | none |
| V2/V3/V4 (authn/session/access) | no | library core, no auth surface |

### Known Threat Patterns for this change
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher identifier injection via a new column | Tampering | `stance` is a fixed DDL identifier + a `$param`-bound value; the existing `_validate_identifier` guard already covers the `n.stance = $p` path. No new interpolation surface. |
| Corrupted stance token on read (value vs name confusion) | Tampering / integrity | Name-lookup `Stance[token]` fails loud on an unknown token rather than silently coercing — a stored-data-integrity signal, not a vulnerability, but worth the explicit failure mode. |

No new attack surface: stance is a closed enum, stored as a validated identifier column, bound as a
parameter — it inherits every injection-hardening property already proven for `value`/`status`.

## Sources

### Primary (HIGH confidence)
- **Local execution** (`uv run python`, py3.14 + pydantic 2.13.x, 2026-07-04) — the `Stance` order /
  TypeError / `.name`/`Stance[...]` behavior AND pydantic by-value validation + integer-rank
  serialization. All `[VERIFIED: local run]` claims.
- **Repo source read** (`models.py`, `core.py`, `protocol.py`, `backends/ladybug.py`,
  `backends/memory.py`, `conftest.py`, `test_models_frozen.py`, `test_revision_spine.py`,
  `test_backend_parity.py`) — call-site inventory, DDL, hydrate/encode discipline.
- **grep audit** of `tests/` + `src/` — the exhaustive `BeliefState(` / `.revise(` / `.expand(` /
  on-disk-DB inventory. All `[VERIFIED: grep]`.
- `.planning/phases/09-…/09-CONTEXT.md` (D-01, D-02, serialization discipline) and
  `.planning/REQUIREMENTS.md` (STANCE-01…06) — the locked authority.

### Secondary (MEDIUM confidence)
- `CLAUDE.md` project constraints (append-only, `.name`-token house style, strict basedpyright,
  full-prek gate) — the verification and style contract.

### Tertiary (LOW confidence)
- none — every claim in this document is grounded in a local run, a source read, or a grep.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; all stdlib/pydantic verified by execution.
- Architecture / discipline: HIGH — grounded in the actual `core.py` write spine + verified pydantic behavior.
- Pitfalls: HIGH — the two load-bearing traps (name/value lookup; DDL column) were reproduced/verified.

**Research date:** 2026-07-04
**Valid until:** 2026-08-03 (30 days — stable stdlib + locked deps; no fast-moving surface)

## RESEARCH COMPLETE

**Phase:** 9 - Stance Value Layer, Write & Persistence
**Confidence:** HIGH

### Key Findings
- The verified `Stance` recipe (plain `Enum` + `functools.total_ordering` + `.value`-comparing
  `__lt__` returning `NotImplemented`) delivers a total order AND makes `+`/`*`/cross-type `<`/`>`
  raise `TypeError` — every STANCE-06 assertion passes exactly as written (executed, not assumed).
- **The phase's load-bearing trap, confirmed empirically:** pydantic v2 validates a plain-Enum field
  **by value, not name** (`stance="certain"` → `ValidationError`; `stance=3` → coerces). So the
  `.name` wire token MUST be reconstructed via `Stance[props["stance"]]` in `_hydrate` before
  reaching the model — `Stance(props["stance"])` (copying the `status` idiom) silently breaks.
- pydantic `model_dump_json` emits the **integer rank** for the plain-Enum field — irrelevant because
  the core persists via a hand-built props dict (`.name`), not pydantic serialization; but a plan
  must not introduce a pydantic-serialization persistence path for stance.
- Exhaustive call-site inventory: 3 production files + the ladybug DDL change; exactly **3 tests
  break** under D-01 (all in `test_models_frozen.py`); every `revise`/`expand` caller elsewhere is
  unaffected (default supplies stance).
- The `IF NOT EXISTS` non-migration is a non-issue for the suite — **verified** every ladybug test
  uses a fresh `:memory:`/`lb.Database()`, never an on-disk DB reused across schema versions.

### File Created
`.planning/phases/09-stance-value-layer-write-persistence/09-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | No new deps; enum + pydantic behavior executed on the target runtime. |
| Architecture | HIGH | Grounded in the real `core.py` write spine and verified serialization asymmetry. |
| Pitfalls | HIGH | Both traps (name/value lookup; DDL column) reproduced/verified. |

### Open Questions
- Exact basedpyright strict ignore code for the arithmetic-negative test lines (`reportOperatorIssue`
  likely) — resolve on first `prek` run; does not affect runtime behavior.

### Ready for Planning
Research complete. The planner can create PLAN.md files directly against the verified recipe, the
call-site inventory, and the SC2/SC4/SC5 test shapes.
