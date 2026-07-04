# Phase 4: Retrieval & Observation Surface - Pattern Map

**Mapped:** 2026-06-18
**Files analyzed:** 6 (2 code, 1 test, 3 doc-text edits)
**Analogs found:** 6 / 6 (all analogs are in-repo; mostly intra-file siblings)

> **Crux of the phase (from RESEARCH §Summary):** every primitive `query_scope` needs already
> shipped in Phases 1–3. The only genuinely NEW logic is a **status-agnostic current-tail
> helper** (a 6-line factor of `_current`). The closest analogs are therefore *inside the file
> being edited* — `core.py`'s own `_current`, `get_revision_chain`, `_order_key`, `_hydrate`.
> Mirror them; do not invent new shapes.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/doxastica/core.py` (`query_scope` body + `_current_tail` helper; refactor `_current`) | service / engine method | request-response (read) + transform (group-by/filter/sort) | `core.py::_current` + `core.py::get_revision_chain` (same file, same role) | exact (intra-file sibling) |
| `src/doxastica/protocol.py` (flag rename `include_deprecated`→`include_retracted`) | protocol / interface | request-response (signature only) | `protocol.py::query_scope` (the method being edited) + sibling sig docstrings | exact (in-place edit) |
| `tests/test_query_scope.py` (NEW) | test | request-response (read assertions) | `tests/test_revision_spine.py` (parametrized two-backend idiom) + `tests/test_invariants.py` (shadow-oracle) | exact |
| `src/doxastica/models.py` | model | — | read-only reference; **NOT modified** (`BeliefFilter`/`Status` already closed) | n/a (no edit) |
| `.planning/REQUIREMENTS.md` (CHAIN-04 / HIST-01 text) | doc | — | text edit `include_deprecated`→`include_retracted` | n/a (doc) |
| `.planning/ROADMAP.md` (Phase-4 line) | doc | — | text edit `include_deprecated`/"deprecated"→`include_retracted`/"retracted" | n/a (doc) |

## Pattern Assignments

### `src/doxastica/core.py` — `_current_tail` helper + `query_scope` body (service, transform)

**Primary analog:** `core.py::_current` (lines 169-194) — the existing derived-current
ordering-max selection. **`query_scope` is its scope-wide, group-by, status-agnostic sibling.**

**Imports pattern** — `core.py` already imports everything `query_scope` needs; **add NO new
imports.** Current module-top block (lines 44-52):

```python
from __future__ import annotations

import base64
import json
import uuid
from typing import TYPE_CHECKING, Any, cast

from doxastica.errors import WorldScopeContractionError
from doxastica.models import WORLD_SCOPE_ID, BeliefState, Scope, Status
```

`BeliefFilter` is the one symbol `query_scope`'s signature references that is **not yet
imported** — but it is type-only at the annotation boundary. Follow the existing model-import
convention: `BeliefFilter` joins the runtime `from doxastica.models import ...` line (NOT under
`TYPE_CHECKING`) because, unlike `protocol.py`, `core.py` already imports `BeliefState`/`Status`
at runtime from the same module. (Verify: `Status` is used at runtime in `_current` line 192, so
the runtime import is the established pattern here.)

**The ONE ordering contract** — reuse `_order_key` verbatim (lines 63-73), never a second sort:

```python
def _order_key(state: dict[str, Any]) -> tuple[str, str]:
    """The ONE UUID7 ordering contract — (str(source_event_id), str(state_id)) (IN-03)."""
    return (str(state["source_event_id"]), str(state["state_id"]))
```

**Core pattern to MIRROR — `_current` (lines 169-194), the status-collapsing tail:**

```python
def _current(self, scope_id: str, belief_id: str) -> dict[str, Any] | None:
    states = self._backend.match_nodes(
        "BeliefState",
        {"scope_id": scope_id, "belief_id": belief_id},
    )
    if not states:
        return None
    tail = max(states, key=_order_key)  # IN-03: the ONE ordering contract
    if tail["status"] == Status.retracted.value:  # D-05: retracted tail ⇒ no active current
        return None
    return tail
```

**Refactor (Pattern 1, RESEARCH §"Status-agnostic current-tail helper"):** factor the
`match_nodes` + `max(..., key=_order_key)` into a status-AGNOSTIC `_current_tail`, then have
`_current` call it and apply ONLY the retracted→`None` collapse on top. This is
**behaviour-preserving for every Phase-3 caller** — the keystone invariant
`current_is_total_single_valued_and_chain_tail` (test_invariants.py:259-295) calls
`core._current` and MUST still pass unchanged. Recommended shape:

```python
def _current_tail(self, scope_id: str, belief_id: str) -> dict[str, Any] | None:
    """Status-AGNOSTIC ordering-max tail for (scope, belief) — raw, before the retracted→None
    collapse. Reuses the ONE _order_key (no second ordering)."""
    states = self._backend.match_nodes(
        "BeliefState", {"scope_id": scope_id, "belief_id": belief_id}
    )
    if not states:
        return None
    return max(states, key=_order_key)

def _current(self, scope_id: str, belief_id: str) -> dict[str, Any] | None:
    tail = self._current_tail(scope_id, belief_id)
    if tail is None or tail["status"] == Status.retracted.value:
        return None
    return tail
```

**The `query_scope` body** mirrors `_current`'s `match_nodes` + `max(key=_order_key)` but scope-
wide (no `belief_id` predicate) + group-by-belief. Recommended single-scan composition
(RESEARCH Pattern 2 — ONE backend round-trip vs N; parity holds because group-by is core-side
Python over raw dicts):

```python
def query_scope(
    self,
    scope_id: str,
    belief_filter: BeliefFilter,
    include_retracted: bool = False,   # D-03 rename — matches the protocol.py signature
) -> list[BeliefState]:
    # 1. resolve status set — explicit filter.status WINS over the include_retracted sugar (D-03)
    if belief_filter.status is not None:
        allowed = belief_filter.status
    else:
        allowed = (
            frozenset({Status.active, Status.retracted})
            if include_retracted else frozenset({Status.active})
        )
    # 2. ONE round-trip; absent scope → match_nodes returns [] (D-08: pure read, no auto-create)
    rows = self._backend.match_nodes("BeliefState", {"scope_id": scope_id})
    # 3. group by belief_id, per-group ordering-MAX (status-agnostic current tail) — reuse _order_key
    by_belief: dict[str, dict[str, Any]] = {}
    for r in rows:
        cur = by_belief.get(r["belief_id"])
        if cur is None or _order_key(r) > _order_key(cur):
            by_belief[r["belief_id"]] = r
    tails = list(by_belief.values())
    # 4. status filter AFTER the max (Pitfall 2) — Status(...) rebuilds the enum (matches _hydrate)
    tails = [t for t in tails if Status(t["status"]) in allowed]
    # 5. belief_ids narrowing
    if belief_filter.belief_ids is not None:
        tails = [t for t in tails if t["belief_id"] in belief_filter.belief_ids]
    # 6. event-range POST-filter (D-06: drop, never rewind) — compare str-vs-str (Pitfall 3)
    if belief_filter.event_id_min is not None:
        tails = [t for t in tails if t["source_event_id"] >= str(belief_filter.event_id_min)]
    if belief_filter.event_id_max is not None:
        tails = [t for t in tails if t["source_event_id"] <= str(belief_filter.event_id_max)]
    # 7. deterministic order (D-07: reuse the ONE _order_key) then 8. hydrate
    tails.sort(key=_order_key)
    return [self._hydrate(t) for t in tails]
```

**Value-decode boundary** — reuse `_hydrate` (lines 214-229) verbatim; never re-implement
base64/json decode in `query_scope` (RESEARCH §Don't-Hand-Roll):

```python
def _hydrate(self, props: dict[str, Any]) -> BeliefState:
    return BeliefState(
        state_id=props["state_id"],
        belief_id=props["belief_id"],
        scope_id=props["scope_id"],
        source_event_id=props["source_event_id"],
        value=self._decode_value(props["value"]),
        status=Status(props["status"]),   # <- the same Status(...) rebuild the status-filter uses
    )
```

**Superseded-cell observation path** (for the matrix; NOT in `query_scope`) — reuse the shipped
`get_revision_chain` (lines 376-386); non-tail entries are superseded:

```python
def get_revision_chain(self, belief_id: str) -> list[BeliefState]:
    states = self._backend.match_nodes("BeliefState", {"belief_id": belief_id})
    states.sort(key=_order_key)  # IN-03: the same ONE ordering contract as `_current`
    return [self._hydrate(s) for s in states]
```

**Error handling pattern:** `query_scope` is a **pure read with NO error surface** (D-08). Unlike
the write ops (`contract` raises `WorldScopeContractionError` at core.py:352 before any backend
access), `query_scope` raises nothing, has no `unit_of_work`, no `_ensure_scope`. Absent scope →
`[]`. Do NOT copy the write-op `_ensure_scope` / guard patterns into the read path.

---

### `src/doxastica/protocol.py` — flag rename (protocol, request-response)

**Analog:** the method being edited — `protocol.py::query_scope` (lines 111-128). In-place edit,
not a new analog.

**Current signature + docstring (lines 111-127) — the EXACT text to edit:**

```python
def query_scope(
    self,
    scope_id: str,
    belief_filter: BeliefFilter,
    include_deprecated: bool = False,          # → rename to include_retracted (D-03)
) -> list[BeliefState]:
    """
    Return the belief states in ``scope_id`` matching ``belief_filter`` (DATA-02).

    ``belief_filter`` is a closed, AND-combined ``BeliefFilter`` — never a free query
    string.

    ``include_deprecated`` is ergonomic sugar over the filter's ``status`` field:   # → include_retracted
    ``False`` means ``{active}`` and ``True`` means ``{active, retracted}``. An explicit
    ``belief_filter.status`` governs — when the caller sets ``status`` it takes
    precedence over the ``include_deprecated`` shorthand.                            # → include_retracted
    """
    ...
```

Three token sites in this file: the parameter name (line 115), and two docstring mentions
(lines 123, 126). The **status-set precedence wording is already correct** (lines 123-126
document `False`≡`{active}`, `True`≡`{active, retracted}`, explicit `status` governs) — keep it;
only the flag *name* changes. `Status` stays `{active, retracted}` (models.py:45-46, UNCHANGED).
Keep `from __future__ import annotations` so `BeliefFilter`/`BeliefState` stay under
`TYPE_CHECKING` (protocol.py:30-39) — this module must NEVER import at runtime (import-purity gate).

---

### `tests/test_query_scope.py` — NEW test file (test, request-response)

**Primary analog:** `tests/test_revision_spine.py` (the parametrized two-backend behaviour
scaffold). **Secondary analog:** `tests/test_invariants.py` (shadow-oracle stateful pattern, for
the optional `query_scope`-parity property only).

**Imports + event-helper pattern** (test_revision_spine.py:28-43) — copy verbatim, add
`BeliefFilter` to the public import:

```python
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from doxastica import MemoryCore  # + BeliefFilter, Status as needed (verify barrel exports them)

if TYPE_CHECKING:
    from doxastica.ports import BackendPort


def _event_id() -> uuid.UUID:
    """Mint a fresh caller-side source_event_id (UUID7, time-ordered, RFC 9562 §5.7)."""
    return uuid.uuid7()
```

> **Action for planner:** confirm `BeliefFilter` and `Status` are exported from the `doxastica`
> barrel (`src/doxastica/__init__.py`). RESEARCH §Runtime-State-Inventory asserts
> `BeliefStore`/`BeliefFilter` are already exported; verify before importing from the barrel vs
> `doxastica.models`.

**Parametrized-backend test pattern** (test_revision_spine.py:51-58, the load-bearing idiom) —
every test takes `backend: BackendPort` and constructs `MemoryCore(backend)` from the INJECTED
fixture port (NOT `MemoryCore.in_memory()`), so the ladybug param is exercised:

```python
def test_query_scope_active_only(backend: BackendPort) -> None:
    """HIST-01: query_scope default returns only current+active beliefs, one per belief."""
    core = MemoryCore(backend)
    core.revise("s", "A", "v0", _event_id())
    # ... assert against core.query_scope("s", BeliefFilter()) ...
```

The `backend` fixture is REUSED VERBATIM from `tests/conftest.py` (lines 34-55) — **no conftest
change** (`params=["memory", "ladybug"]` + `importorskip`). Do not re-declare the fixture.

**Four-cell matrix construction** (RESEARCH §Code-Examples, test-design discretion) — combines
`query_scope` (current cells) + `get_revision_chain` (superseded cells), e.g.:

```python
def test_retracted_superseded_matrix(backend: BackendPort) -> None:
    core = MemoryCore(backend)
    # A: revise→revise→contract  → current+retracted (tail) + superseded+active (below)
    core.revise("s", "A", "v0", _event_id()); core.revise("s", "A", "v1", _event_id())
    core.contract("s", "A", _event_id())
    # B: revise→revise           → current+active + superseded+active
    core.revise("s", "B", "w0", _event_id()); core.revise("s", "B", "w1", _event_id())
    # C: revise→contract→revise  → current+active + superseded+retracted (the retraction, then revived)
    core.revise("s", "C", "x0", _event_id()); core.contract("s", "C", _event_id())
    core.revise("s", "C", "x1", _event_id())

    f = BeliefFilter()
    active_now     = {bs.belief_id for bs in core.query_scope("s", f, include_retracted=False)}
    with_retracted = {bs.belief_id for bs in core.query_scope("s", f, include_retracted=True)}
    assert active_now     == {"B", "C"}
    assert with_retracted == {"A", "B", "C"}
    # superseded cells are NOT in query_scope (D-05) — read via the chain:
    assert any(s.status is Status.active    for s in core.get_revision_chain("A")[:-1])
    assert any(s.status is Status.retracted for s in core.get_revision_chain("C")[:-1])
```

**Optional stateful-parity analog** (test_invariants.py shadow-oracle) — if extending the
`_SpineMachine` with a `@invariant` that `query_scope`'s active set ≡ the oracle's derived-active
set, mirror the `_shadow_current` (test_invariants.py:170-183) + `@invariant` (lines 258-295)
patterns. This is DISCRETIONARY; the example-based matrix test is the required deliverable.

---

## Shared Patterns

### The ONE ordering contract (`_order_key`)
**Source:** `core.py::_order_key` (lines 63-73)
**Apply to:** `_current_tail`, the `query_scope` group-by max, AND the `query_scope` result sort.
Never introduce a second ordering — D-07 mandates reuse; a fresh lambda desyncs the read surface
from the spine. The `_order_key` docstring is explicit that drift between selection sites is the
failure mode.
```python
return (str(state["source_event_id"]), str(state["state_id"]))
```

### Value-decode boundary (`_hydrate` / `_decode_value`)
**Source:** `core.py::_hydrate` (lines 214-229) + `_decode_value` (lines 209-212)
**Apply to:** the final `[self._hydrate(t) for t in tails]` step. Bypassing it reintroduces the
DEF-02-01 brace-coercion corruption. `Status(props["status"])` inside `_hydrate` is the same
enum-rebuild the `query_scope` status-filter must use (Pitfall 6).

### Status round-trip at the seam (`Status(stored_str) in allowed`)
**Source:** `core.py::_current` line 192 (`tail["status"] == Status.retracted.value`) and
`_hydrate` line 228 (`Status(props["status"])`). Both backends store `status` as the raw string
`status.value` (`_append_state` line 263). Rebuild `Status(t["status"])` before the membership
test against `frozenset[Status]` — matches the hydrate boundary.

### Parametrized two-backend fixture (parity for free)
**Source:** `tests/conftest.py` (lines 34-55) — `params=["memory", "ladybug"]` + `importorskip`
**Apply to:** every test in `test_query_scope.py`. Construct `MemoryCore(backend)` from the
injected port (test_revision_spine.py:53 convention), NOT `MemoryCore.in_memory()`. No conftest edit.

### Pure-read contract (no error surface, no auto-create)
**Source (anti-pattern reference):** the WRITE ops `_ensure_scope` (core.py:154-166) and the
`WorldScopeContractionError` guard (core.py:352). `query_scope` must do NEITHER — `match_nodes`
on an absent scope returns `[]` on both backends (memory.py:102 `self._nodes.get(label, {})`;
ladybug.py:319-328 `MATCH` yields no rows). Return `[]`; raise nothing (D-08).

## No Analog Found

None. Every Phase-4 file has a strong in-repo analog (most are intra-file siblings of the method
being edited). This phase is **pure composition** — no new mechanism, no new dependency, no new
port primitive.

## Watch-Outs (from RESEARCH §Common Pitfalls — load-bearing for the planner)

| # | Pitfall | Pattern that avoids it |
|---|---------|------------------------|
| 1 | Reusing `_current` for `include_retracted=True` silently drops retracted-current beliefs (it returns `None` on a retracted tail, core.py:192) | Use the status-agnostic `_current_tail`, filter status AFTER the max |
| 2 | Pre-filtering rows to `status=active` BEFORE the per-belief max leaks a stale active value below a retracted tail | Take ordering-max over ALL statuses first, THEN test the tail's status (the Phase-3 D-05 lesson) |
| 3 | `event_id_min/max` are typed `UUID`; stored `source_event_id` is a `str` — mixing raises `TypeError` / wrong order | Compare `t["source_event_id"]` (str) against `str(belief_filter.event_id_min/max)` — same form `_order_key` uses; inclusive `[min,max]` (`>=`/`<=`), pin a boundary test |
| 4 | The doc-edit half of D-03 (REQUIREMENTS.md CHAIN-04/HIST-01, ROADMAP.md Phase-4 line) is easy to miss | Treat D-03 as a 3-site edit; gate with `! grep -rn include_deprecated src tests .planning/REQUIREMENTS.md .planning/ROADMAP.md` |
| 5 | Copying write-op `_ensure_scope` into the read path auto-creates a `Scope` node on query | Pure read — no `_ensure_scope`, no get-or-create; absent scope → `[]` (D-08) |
| 6 | Comparing an enum member against a stored string in the status filter never matches cleanly | Rebuild `Status(t["status"])` before the membership check (matches `_hydrate`) |

## Metadata

**Analog search scope:** `src/doxastica/` (core.py, protocol.py, models.py, ports.py,
backends/memory.py, backends/ladybug.py), `tests/` (conftest.py, test_revision_spine.py,
test_invariants.py).
**Files scanned (read):** 9.
**All line numbers verified against current source** (not inherited from RESEARCH unread).
**Pattern extraction date:** 2026-06-18
