# Phase 4: Retrieval & Observation Surface - Research

**Researched:** 2026-06-18
**Domain:** AGM belief-base read surface (`query_scope`) over the LPG `BackendPort`; retracted-vs-superseded query matrix
**Confidence:** HIGH (the phase is pure in-repo composition of an already-shipped Phase-3 spine; every claim is grounded in read source, not external docs)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 — `query_scope` returns exactly ONE current state per `(scope, belief)`.** It returns the single derived-current tail (the Phase-3 ordering-max selection), never the full history. `query_scope` *is* the AGM belief base B ("what does this scope hold now"). SC3 ("no duplicate beliefs") is a **postcondition that falls out of the model**, not dedup logic to write.
- **D-02 — `include_retracted` surfaces retracted-current beliefs, never superseded history.**
  - `include_retracted=False` (default): return beliefs whose current tail is `status=active` (equivalent to the existing `_current`, which nulls a retracted tail).
  - `include_retracted=True`: ALSO return beliefs whose current tail is `status=retracted`.
  - Still exactly one state per belief in both modes. Superseded (non-current) states are **never** returned by `query_scope`.
  - `_current()` returns `None` on a retracted tail (Phase-3 D-05), so `query_scope` **cannot reuse it directly** for the retracted case — it needs a **current-tail-regardless-of-status** helper (the raw ordering-max tail) then filters by the resolved status set.
- **D-03 — Rename the public flag `include_deprecated` → `include_retracted`** (Option A; a deliberate Phase-1-surface reversal). `Status` stays `{active, retracted}` (DATA-06 frozen — unchanged). The public matrix vocabulary standardises on **retracted vs superseded**. Status-filter precedence unchanged: an explicit `belief_filter.status` governs; `include_retracted` is sugar — `False` ≡ `{active}`, `True` ≡ `{active, retracted}`. **Touch points:** `src/doxastica/protocol.py` (signature + docstring), CHAIN-04 / HIST-01 text in `.planning/REQUIREMENTS.md`, and the Phase-4 line in `.planning/ROADMAP.md`.
- **D-04 — Two orthogonal axes, observed by two read methods:** *Status axis* (`active`/`retracted`, per-state stored field, what `contract()` stamps) and *Currency axis* (`current`/`superseded`, per-state structural — `superseded` = displaced by a newer revision, has an incoming `SUPERSEDES` edge / is not the ordering-max tail). Four cells: `current+active` (live), `current+retracted` (contracted), `superseded+active` (overwritten value), `superseded+retracted` (a retraction state itself later superseded).
- **D-05 — `query_scope` observes the *current* row; `get_revision_chain` + `SUPERSEDES` observe the *superseded* cells.** `query_scope` only ever returns current tails. The two superseded cells are reached via `get_revision_chain` (full chain, HIST-02) + the `SUPERSEDES` edges — **never** via `query_scope`. The matrix test combines both read methods.
- **D-06 — `event_id_min`/`event_id_max` POST-FILTER the current tails; no as-of reconstruction.** Derive the current tail per belief first (unchanged), THEN drop tails whose `source_event_id` falls outside `[min, max]`. The range filters *which current beliefs you see*; it never changes *which state is current*. A belief whose current tail is newer than `event_id_max` is simply **absent** — NOT rewound. As-of/window reconstruction is `get_scope_at` (HIST-03, Phase 6).
- `belief_ids` narrows the belief set (pre-filter); `status` filters the current tail's status with the D-03 precedence.
- **D-07 — Deterministic order, sorted by the existing `_order_key` `(source_event_id, state_id)`.** Result is semantically a set; deterministic order makes parity + Hypothesis shrinking clean. **Reuse the single `_order_key` in `core.py` — do NOT introduce a second ordering.** Document: callers must not ascribe meaning to order.
- **D-08 — Non-existent or empty scope returns `[]`.** `query_scope` is a **pure read** — never auto-creates (unlike write ops' get-or-create). No existence probe, no new error type.

### Claude's Discretion

- Exact shape/name of the current-tail-regardless-of-status helper, and whether it factors out shared code with `_current` (**constraint:** ONE ordering contract via `_order_key`; `_current`'s retracted-tail→`None` behaviour must remain intact for the write ops).
- Whether `query_scope` derives per-belief current via N `_current`-style lookups or a single scope-wide scan + group-by-belief + per-group max (backend-efficiency call; in-memory and ladybug may differ as long as parity holds).
- How the four-cell matrix test is constructed (the operation sequence producing each cell) — a test-design call, constrained by "runs on both backends via the parametrized conftest."

### Deferred Ideas (OUT OF SCOPE)

- **`get_scope_at` as-of reconstruction** (HIST-03, Phase 6) — the event-window/time-travel cut D-06 deliberately keeps OUT of the Phase-4 event-range filter.
- **`add_edge` consumer edges + `get_impact` cascade** (EDGE-01/02, Phase 5) — Phase 4 reads the Phase-3 structural `SUPERSEDES` edges but adds no consumer edges.
- **Materialize a stored current pointer** ONLY if `query_scope` profiling later demands it (Phase-3 D-01 deferred). Addable without changing the public surface; not now.
- **An `is_current`/currency flag on returned states** — not needed; `query_scope` returns only current tails by construction (D-01). Revisit only for a future mixed-currency surface.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **CHAIN-04** | Deprecated-vs-superseded is a **structural/query distinction** (`include_retracted` flag + `SUPERSEDES` edge); meaning left to consumers. (Wording carries the D-03 rename `include_deprecated` → `include_retracted`.) | Two-axis matrix (D-04/D-05) is realised by the *combination* of `query_scope` (current row) + `get_revision_chain` + `SUPERSEDES` edges (superseded cells). The `SUPERSEDES` edge already exists in both adapters' schema (`_EDGE_ENDPOINTS`, in-memory `_edges`) and is laid on every displacement by `_append_state`. No new mechanism needed — only the `query_scope` body + the four-cell test that reads through both surfaces. |
| **HIST-01** | `query_scope(scope, filter, include_retracted=False)` returns active (or, with the flag, retracted) belief states — the observation surface. | The `query_scope` body lands in `core.py` composing `match_nodes` (no new port primitive). The status-agnostic current-tail helper (a sibling to `_current`) plus the closed `BeliefFilter` (4 fields) and `_order_key` sort deliver the full signature behaviour. |

**Note on requirement-text edits (D-03):** REQUIREMENTS.md lines 60–61 (CHAIN-04) and 84–85 (HIST-01) still say `include_deprecated`; ROADMAP.md lines 139–140 say `include_deprecated` / "deprecated". These three text sites must be updated to `include_retracted` / "retracted" as part of this phase. They are documentation edits, not code — but they are *in scope* per D-03's touch-point list.
</phase_requirements>

## Summary

Phase 4 is a **pure composition phase**: it adds ONE public method body (`query_scope`) to the already-built `MemoryCore`, plus a rename of one keyword argument on the `BeliefStore` Protocol, plus a four-cell matrix test. There is **no new `BackendPort` primitive, no new schema, no new write semantics, and no external dependency**. Everything `query_scope` needs already exists: `match_nodes` (the read primitive), `_order_key` (the one ordering contract), `_hydrate` (the value-decode boundary), `_current` (the active-only derived tail), `get_revision_chain` (HIST-02), and the `SUPERSEDES` edges laid by `_append_state` on every displacement.

The single genuinely new piece of *logic* is a **status-agnostic current-tail helper** — the raw ordering-max tail per `(scope, belief)`, WITHOUT `_current`'s retracted-tail→`None` collapse (Phase-3 D-05). `query_scope` needs the raw tail so that `include_retracted=True` can surface a belief whose current tail is `retracted`; `_current` deliberately nulls that tail because the *write* side (`revise`/`expand`/`contract` computing `prior`) must see "no active current." The two cannot be the same function — but they MUST share `_order_key` so the read surface never desynchronises from the write spine. This is the crux of the phase and the main pitfall (Pitfall 1 below).

The retracted/superseded matrix (CHAIN-04) is **not a new data structure** — it is an *observation* assembled from two existing read methods. `query_scope` returns only the current row (the two `current+*` cells, gated by `include_retracted`); the two `superseded+*` cells are read through `get_revision_chain` + the `SUPERSEDES` edges. The matrix *test* is the deliverable that proves all four cells are distinguishable, run over the parametrized two-backend conftest.

**Primary recommendation:** Add a private `_current_tail(scope_id, belief_id) -> dict | None` (status-agnostic ordering-max; reuse `_order_key`, no retracted collapse) and refactor `_current` to call it then apply the retracted→`None` rule. Implement `query_scope` as **single scope-wide `match_nodes` scan + group-by-`belief_id` + per-group `max(_order_key)`** (one backend round-trip on ladybug, vs N round-trips for N `_current`-style calls), then apply status filter → event-range post-filter → `_order_key` sort → `_hydrate`. Land the `include_deprecated`→`include_retracted` rename in `protocol.py` + the two doc sites in the same phase.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `query_scope` body (derive current tails, filter, sort, hydrate) | `MemoryCore` (core.py, driver-blind) | — | Belief-revision logic lives in the backend-agnostic core (BACK-01 / Phase-2 D-02); it composes port primitives, never imports a driver. |
| Status-agnostic current-tail derivation | `MemoryCore` (core.py) | — | Derived-current is core logic (Phase-3 D-01: no stored pointer); the port has no aggregate/ORDER-BY primitive, so the max is taken core-side. |
| Raw node fetch for a scope | `BackendPort.match_nodes` (both adapters) | — | The single read primitive; `query_scope` composes it. Adapters return raw `list[dict]`; core hydrates (Phase-2 D-04). |
| Public flag rename `include_retracted` | `BeliefStore` Protocol (protocol.py) | REQUIREMENTS.md + ROADMAP.md text | The seam the rename lands on (D-03). The two doc sites carry the requirement-text half of the same decision. |
| Superseded-cell observation (matrix) | `get_revision_chain` (HIST-02, shipped) + `SUPERSEDES` edges | matrix test (tests/) | D-05: `query_scope` never returns superseded rows; the chain + edges do. |
| Cross-backend parity of `query_scope` output | parametrized `backend` conftest fixture | matrix + parity tests | The in-memory oracle and ladybug must return byte-identical ordered `list[BeliefState]` (D-05 / D-07). |

## Standard Stack

No new packages. The phase composes the already-installed, already-verified stack.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | `>=2.11,<3` (installed 2.13.4) | Frozen `BeliefState` / `BeliefFilter` hydration at the seam | The only required runtime dep (Phase-2 D-03); already wired via `_hydrate`. `query_scope` returns `list[BeliefState]`. |
| `ladybug` | `>=0.17,<0.18` (installed 0.17.1) | Reference backend; `match_nodes` Cypher | Reference-backend extra (`doxastica[ladybug]`); `match_nodes` already implemented. No new Cypher needed beyond what exists. |

### Supporting (dev — already present)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=8` (installed 9.0.3) | Parametrized two-backend test runner | Every Phase-4 test takes `backend: BackendPort` via the conftest fixture. |
| `hypothesis` | `6.155.2` | (Optional) stateful parity property for `query_scope` ≡ derived current | A `query_scope`-vs-oracle invariant could extend the Phase-3 `_SpineMachine`; the four-cell matrix itself is a plain example-based test. |

**Installation:** None. `query_scope` adds zero dependencies. (CLAUDE.md: any third runtime dep is forbidden; this phase introduces none — `[VERIFIED: read core.py imports — only stdlib base64/json/uuid + pydantic models]`.)

## Package Legitimacy Audit

> Not applicable — **this phase installs no external packages.** It composes the already-installed, already-audited Phase-1/2 stack (`pydantic`, `ladybug`, `pytest`, `hypothesis`). No new `pip install`, no new import. The Phase-2 audit (CLAUDE.md: `ladybug` 0.17.1 verified on PyPI, `ladybugdb` slopsquat token confirmed ABSENT) stands.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram — `query_scope` data flow

```
caller (NVM / postulate test)
   │  query_scope(scope_id, BeliefFilter, include_retracted=False)
   ▼
┌─────────────────────────────  MemoryCore.query_scope  (core.py, driver-blind) ──────────────────┐
│                                                                                                  │
│  1. resolve status set            include_retracted + belief_filter.status  ──►  {active} |      │
│     (D-02/D-03 precedence)         (explicit filter.status WINS over the flag sugar)   {active,   │
│                                                                                         retracted}│
│  2. fetch raw nodes ──────────────────────────────►  backend.match_nodes("BeliefState",          │
│     (ONE round-trip, recommended)                       {"scope_id": scope_id})  ──► list[dict]   │
│                                       │                                                           │
│                                       ▼                                                           │
│  3. group raw nodes by belief_id  ──►  per (scope,belief): max over _order_key  =  CURRENT TAIL   │
│     (status-AGNOSTIC ordering-max; the _current_tail helper logic, NOT _current)                  │
│                                       │                                                           │
│                                       ▼                                                           │
│  4. status filter  ──────────────►  keep tail iff  tail.status ∈ resolved-status-set             │
│                                       │            (active-only by default; +retracted with flag) │
│                                       ▼                                                           │
│  5. belief_ids pre/post-filter  ──►  if filter.belief_ids: keep iff belief_id ∈ set              │
│                                       │                                                           │
│                                       ▼                                                           │
│  6. event-range POST-filter  ────►  drop tail iff source_event_id < min OR > max  (D-06:          │
│     (NOT an as-of cut)                absent, never rewound)                                       │
│                                       │                                                           │
│                                       ▼                                                           │
│  7. sort by _order_key  ─────────►  deterministic (source_event_id, state_id) order (D-07)        │
│                                       │                                                           │
│                                       ▼                                                           │
│  8. hydrate  ────────────────────►  [_hydrate(tail) for tail in kept]  ──►  list[BeliefState]     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
   │  list[BeliefState]  (exactly one current tail per belief; [] for empty/absent scope, D-08)
   ▼
caller
```

The matrix observation (CHAIN-04) is a *separate* read path that composes the above with history:

```
four-cell matrix observation
   ├─ current+active     ──► query_scope(scope, filter, include_retracted=False)   contains belief
   ├─ current+retracted  ──► query_scope(scope, filter, include_retracted=True)    contains belief
   │                          AND query_scope(..., include_retracted=False)         does NOT
   ├─ superseded+active   ─┐
   └─ superseded+retracted ┴► get_revision_chain(belief_id)  →  every non-tail state is superseded;
                              read its .status to split active/retracted; the SUPERSEDES edge
                              (laid by _append_state) is the structural witness of "superseded".
```

### Recommended Project Structure (no new modules)

```
src/doxastica/
├── core.py        # ADD: query_scope body + _current_tail helper; refactor _current to call it
├── protocol.py    # EDIT: rename include_deprecated → include_retracted (signature + docstring)
└── models.py      # UNCHANGED (BeliefFilter already closed-4-field; Status unchanged by D-03)
tests/
├── conftest.py            # UNCHANGED (the params=["memory","ladybug"] fixture is reused)
└── test_query_scope.py    # NEW: query_scope behaviors + the four-cell matrix, parametrized
.planning/
├── REQUIREMENTS.md  # EDIT: CHAIN-04 + HIST-01 text → include_retracted / retracted (D-03)
└── ROADMAP.md       # EDIT: Phase-4 success-criteria text → include_retracted / retracted (D-03)
```

### Pattern 1: Status-agnostic current-tail helper (the phase crux)
**What:** Factor `_current`'s ordering-max selection so `query_scope` gets the raw tail (any status), while `_current` keeps its retracted→`None` write-side contract.
**When to use:** Always for `query_scope`'s `include_retracted=True` path; `_current` stays the write-side "active current or nothing" probe.
**Recommended refactor (preserves `_current` behaviour exactly):**
```python
# Source: composed from existing core.py:169-194 (_current) + _order_key
def _current_tail(self, scope_id: str, belief_id: str) -> dict[str, Any] | None:
    """Status-AGNOSTIC ordering-max tail for (scope, belief) — or None if no state.

    The raw derived tail BEFORE the retracted→None collapse. `_current` applies that
    collapse on top (write-side: a retracted tail means no ACTIVE current). `query_scope`
    needs the raw tail so include_retracted=True can surface a retracted-current belief.
    Reuses the ONE ordering contract (_order_key) — must not introduce a second ordering.
    """
    states = self._backend.match_nodes(
        "BeliefState", {"scope_id": scope_id, "belief_id": belief_id}
    )
    if not states:
        return None
    return max(states, key=_order_key)  # IN-03: the ONE ordering contract

def _current(self, scope_id: str, belief_id: str) -> dict[str, Any] | None:
    """ACTIVE derived current — None on a retracted tail (D-05, write-side contract)."""
    tail = self._current_tail(scope_id, belief_id)
    if tail is None or tail["status"] == Status.retracted.value:
        return None
    return tail
```
This is behaviour-preserving for every Phase-3 caller of `_current` (verified against the `_SpineMachine` keystone invariant semantics: `_current` is still the ordering-max-then-retracted-collapse). The keystone invariant `current_is_total_single_valued_and_chain_tail` continues to call `core._current` and must still pass unchanged.

### Pattern 2: Single-scan group-by-belief current derivation (recommended over N lookups)
**What:** `query_scope` fetches ALL `BeliefState` rows for the scope in one `match_nodes`, groups by `belief_id`, takes the per-group ordering-max.
**When to use:** The recommended approach (Claude's-discretion item resolved here). One ladybug round-trip vs N (one per distinct belief). Parity holds because the grouping + max are core-side Python over raw dicts, identical for both backends.
**Example:**
```python
# Source: composed from match_nodes (ports.py:88) + _order_key (core.py:63) + D-07 sort
def query_scope(
    self,
    scope_id: str,
    belief_filter: BeliefFilter,
    include_retracted: bool = False,
) -> list[BeliefState]:
    # 1. resolve status set — explicit filter.status WINS over the include_retracted sugar (D-03)
    if belief_filter.status is not None:
        allowed = belief_filter.status
    else:
        allowed = (
            frozenset({Status.active, Status.retracted})
            if include_retracted else frozenset({Status.active})
        )
    # 2. ONE round-trip: every state in the scope (D-08: absent scope → empty list, pure read)
    rows = self._backend.match_nodes("BeliefState", {"scope_id": scope_id})
    # 3. group by belief_id, take per-group ordering-MAX (status-agnostic current tail)
    by_belief: dict[str, dict[str, Any]] = {}
    for r in rows:
        bid = r["belief_id"]
        cur = by_belief.get(bid)
        if cur is None or _order_key(r) > _order_key(cur):
            by_belief[bid] = r
    tails = list(by_belief.values())
    # 4. status filter (the resolved set) — Status(...) rebuilds the enum from the stored str
    tails = [t for t in tails if Status(t["status"]) in allowed]
    # 5. belief_ids narrowing
    if belief_filter.belief_ids is not None:
        tails = [t for t in tails if t["belief_id"] in belief_filter.belief_ids]
    # 6. event-range POST-filter (D-06: drop, never rewind). See Pitfall 3 on the comparison key.
    if belief_filter.event_id_min is not None:
        tails = [t for t in tails if t["source_event_id"] >= str(belief_filter.event_id_min)]
    if belief_filter.event_id_max is not None:
        tails = [t for t in tails if t["source_event_id"] <= str(belief_filter.event_id_max)]
    # 7. deterministic order (D-07: reuse the ONE _order_key) then 8. hydrate
    tails.sort(key=_order_key)
    return [self._hydrate(t) for t in tails]
```
*(Illustrative — the planner/implementer owns final shape; this proves the composition is sound against the real port + models.)*

### Anti-Patterns to Avoid
- **Reusing `_current` for the `include_retracted=True` path** — it returns `None` on a retracted tail, so retracted-current beliefs would silently vanish even with the flag on (the exact bug D-02's implementation note warns about).
- **Introducing a second ordering** (e.g. sorting by `state_id` only, or a fresh lambda) — desynchronises the read surface from the spine; D-07 mandates reuse of `_order_key`. The Phase-3 `_order_key` docstring (core.py:63-72) is explicit that drift between selection sites is the failure mode.
- **Letting `event_id_min/max` rewind the current** — D-06: the range is a post-filter on the *already-derived* tail. A belief whose tail is newer than `event_id_max` is ABSENT, not shown at an older value. (Showing the older value is `get_scope_at`, Phase 6 — building it here is the deferred-scope leak.)
- **Auto-creating the scope on read** — D-08: `query_scope` is a pure read; no `_ensure_scope`, no get-or-create. Absent scope → `[]`.
- **Filtering `match_nodes` to `status=active` at the port** — the status filter must run core-side AFTER the per-belief max, because the *ordering-max* tail's status is what decides visibility (a retracted tail must clear an older active state from the result — exactly the Phase-3 D-05 lesson where pre-filtering to active left contracted beliefs reporting a current). Take the max over ALL statuses, THEN filter.
- **Free-string or interpolated query** — DATA-02: `query_scope` consumes only the 4 closed `BeliefFilter` fields; no triple-structure leak.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ordering of states | A new sort key / comparison | `_order_key` (core.py:63) | The ONE ordering contract; a second one desyncs read from spine (D-07). |
| Current-state derivation | A stored `CURRENT_STATE` pointer / `is_current` flag | Derived ordering-max over append-only states | Phase-3 D-01: current is derived, never stored. A pointer is the rejected alternative; PITFALLS.md/ARCHITECTURE.md model it and are SUPERSEDED. |
| Value decode on read | Re-implementing base64/JSON decode in `query_scope` | `self._hydrate(props)` (core.py:214) | The single value-decode boundary; bypassing it reintroduces the DEF-02-01 brace-coercion corruption. |
| Superseded-cell read | A new "list superseded" query/primitive | `get_revision_chain` (HIST-02) + `SUPERSEDES` edges | D-05: the chain already returns full history ordered; non-tail entries are superseded. No new mechanism. |
| Cross-backend grouping | Backend-specific Cypher GROUP BY vs in-memory loop | Core-side Python group-by over raw `list[dict]` | Keeps `query_scope` driver-blind (BACK-01) and guarantees parity — identical code path for both backends. |
| Dedup of duplicate beliefs | A `set()`/dedup pass on results | Nothing — D-01 postcondition | "One current per (scope,belief)" falls out of the per-belief max; SC3 is a property, not logic. |

**Key insight:** Phase 4 is composition, not construction. Every primitive it needs shipped in Phases 1–3. The only *new* code is (a) the status-agnostic tail helper (a 6-line factor of `_current`), (b) the `query_scope` body (filter + group + sort + hydrate), and (c) the rename. Any larger surface is scope creep into Phases 5/6.

## Runtime State Inventory

> Phase 4 is greenfield *additive* logic (one new method + one keyword rename), not a rename/migration of stored data. The D-03 rename touches a **public API keyword and documentation text**, NOT any stored value, key, or schema. A focused inventory of the rename's blast radius:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None.** `Status` values stay `{active, retracted}` (D-03 keeps DATA-06 frozen); no stored string changes. `include_deprecated` was a *parameter name*, never persisted. Verified: `grep` finds `include_deprecated` only in `protocol.py` (signature/docstring) — never in `models.py`, the adapters, or any DDL. | code edit only (protocol.py keyword) |
| Live service config | **None** — this is an embedded library; no live service, no UI-held config, no scheduler. | none |
| OS-registered state | **None** — no OS registrations. | none |
| Secrets/env vars | **None** — no env var or secret references the flag. | none |
| Build artifacts | **None** — `query_scope` is an additive method on an existing class; no `egg-info`/entry-point change. The existing `MemoryCore` is already exported via the barrel (`__init__.py`); no new export needed (`query_scope` is a method, `BeliefStore`/`BeliefFilter` already exported). | none |

**Canonical question — after every file is updated, what runtime state still carries the old name?** Nothing. `include_deprecated` is a not-yet-shipped public *parameter* (NVM has not built against it — CONTEXT D-03), present in exactly 3 code/doc sites (`protocol.py` signature+docstring; `REQUIREMENTS.md` CHAIN-04/HIST-01; `ROADMAP.md` Phase-4 line). No stored data, no migration. **The rename is a pure source edit; no data migration task is needed** — explicitly verified, not assumed.

## Common Pitfalls

### Pitfall 1: Reusing `_current` for the retracted path (the central trap)
**What goes wrong:** `query_scope(..., include_retracted=True)` silently omits beliefs whose current tail is `retracted`.
**Why it happens:** `_current` returns `None` on a retracted ordering-max tail (core.py:192, Phase-3 D-05) — by design, for the write side. If `query_scope` loops `_current` per belief, the retracted-current beliefs are invisible even with the flag set.
**How to avoid:** Derive the **status-agnostic** ordering-max tail (Pattern 1's `_current_tail`), then apply the resolved status filter. Never route the retracted path through `_current`.
**Warning signs:** A four-cell matrix test where the `current+retracted` cell is empty under `include_retracted=True`; a parity test where retracted-current beliefs differ between flag states by *nothing* (the flag has no effect).

### Pitfall 2: Status pre-filter at the wrong stage (the Phase-3 D-05 lesson, recurring)
**What goes wrong:** A belief that was revised (active) then contracted (retracted tail) wrongly shows its OLD active value in `query_scope` results.
**Why it happens:** If you filter `match_nodes` (or the grouped rows) to `status=active` BEFORE taking the per-belief max, the now-superseded active state below the retracted tail becomes the "max of the active subset" and leaks back into the result.
**How to avoid:** Take the ordering-max over **ALL** statuses first (the true current tail), THEN test that tail's status against the allowed set. This is exactly the fix recorded in STATE.md for Phase-3 `_current` ("`_current` now selects ordering-max over ALL statuses … prior active-filter left contracted beliefs reporting a current").
**Warning signs:** `include_retracted=False` returns a contracted belief's stale active value instead of omitting the belief.

### Pitfall 3: `event_id_min/max` comparison — UUID vs string ordering key
**What goes wrong:** The event-range post-filter (D-06) compares inconsistently with `_order_key`, dropping or keeping the wrong tails at boundaries.
**Why it happens:** `_order_key` compares `str(source_event_id)` (lexicographic). `BeliefFilter.event_id_min/max` are typed `UUID`. Comparing a stored `str` `source_event_id` against a `UUID` object is a type error / wrong order; comparing `UUID < UUID` uses Python's `UUID.__lt__` (integer order), while the stored prop is the canonical hyphenated lowercase hex string. For RFC-9562 UUID7 the canonical lowercase-hex **string** order and the integer order **agree** (hex digits sort identically to their numeric value, and the field layout is big-endian time-first) — but ONLY if you compare like-with-like. **Mixing** `str >= UUID` raises `TypeError`.
**How to avoid:** Normalise both sides to the SAME representation the ordering contract uses — compare `t["source_event_id"]` (already a `str`) against `str(belief_filter.event_id_min)` / `str(...event_id_max)`. (`str(UUID)` yields the canonical lowercase hyphenated form, byte-for-byte what the core stored via `_append_state`'s `str(source_event_id)`.) This keeps the range filter consistent with `_order_key` and works identically on both backends. **Confidence note:** that lowercase-hex string order == UUID7 byte/time order is `[VERIFIED: RFC 9562 §5.7 canonical text form is the big-endian hex of the same bytes — Phase-1 DATA-03 already pins "(source_event_id byte-order, state_id tiebreak)" and protocol.py:48-63 documents it]`. The inclusive `[min, max]` boundary (`>=` / `<=`) is the natural reading of "range"; confirm inclusivity in a test (it is a Claude's-discretion edge worth pinning in VALIDATION).
**Warning signs:** `TypeError: '>=' not supported between str and UUID`; off-by-one at the exact min/max boundary; backend divergence if one adapter stored the id differently (it does not — both store `str(...)`).

### Pitfall 4: Forgetting the doc-site half of D-03
**What goes wrong:** Code renames `include_deprecated`→`include_retracted` but REQUIREMENTS.md (CHAIN-04, HIST-01) and ROADMAP.md still say `include_deprecated`/"deprecated"; the requirement text and the code drift.
**Why it happens:** The rename feels like a code-only change; the three doc sites are easy to miss.
**How to avoid:** Treat D-03 as a 3-site edit (verified by `grep`: `protocol.py:115,123,126`; `REQUIREMENTS.md:61,84`; `ROADMAP.md:139,140`). Include a doc-edit task in the plan.
**Warning signs:** A `grep include_deprecated` after the phase still returns hits.

### Pitfall 5: Empty / absent scope handling (D-08)
**What goes wrong:** `query_scope` on a never-created scope raises or auto-creates a `Scope` node.
**Why it happens:** Copying the write-op `_ensure_scope` pattern into the read path.
**How to avoid:** `match_nodes("BeliefState", {"scope_id": scope_id})` on an absent scope simply returns `[]` (verified: in-memory `match_nodes` returns `[]` for a missing label/bucket; ladybug `MATCH` returns no rows). Return `[]`. No probe, no create, no new error type.
**Warning signs:** A `Scope` node appears after a query; the postulate suite (which queries empty scopes routinely) fails on an unexpected write.

### Pitfall 6: Cross-backend `status` round-trip type
**What goes wrong:** The status filter compares an enum member against a stored string and never matches.
**Why it happens:** Both adapters store `status` as the raw string (`status.value`, e.g. `"active"`); `BeliefFilter.status` is `frozenset[Status]` (enum members). `Status(t["status"]) in allowed` rebuilds the enum from the stored string before the membership test — matching `_hydrate`'s `Status(props["status"])` boundary (core.py:228). Comparing the raw `"active"` string against `frozenset[Status]` works only because `StrEnum` members `==` their string value, but normalise via `Status(...)` for clarity and to match the hydrate boundary.
**How to avoid:** Rebuild `Status(t["status"])` before the membership check (or compare `t["status"]` against `{s.value for s in allowed}`). Both backends store the identical string form (verified: `_append_state` writes `status.value`).
**Warning signs:** `include_retracted=False` returns everything or nothing regardless of the flag.

## Code Examples

### Resolving the status set (D-02 / D-03 precedence)
```python
# Source: protocol.py:117-127 docstring (the locked precedence) + models.py BeliefFilter
def _resolve_status_set(
    belief_filter: BeliefFilter, include_retracted: bool
) -> frozenset[Status]:
    # explicit filter.status GOVERNS; include_retracted is sugar (False≡{active}, True≡both)
    if belief_filter.status is not None:
        return belief_filter.status
    return (
        frozenset({Status.active, Status.retracted})
        if include_retracted
        else frozenset({Status.active})
    )
```

### Reading the superseded cells for the matrix (D-05, via shipped surface)
```python
# Source: get_revision_chain (core.py:376) — already ordered by _order_key
chain = core.get_revision_chain(belief_id)           # full history, (src_event, state_id)-ordered
current_tail = chain[-1] if chain else None          # the ordering-max tail = current
superseded = chain[:-1]                               # every non-tail state is superseded
superseded_active    = [s for s in superseded if s.status is Status.active]
superseded_retracted = [s for s in superseded if s.status is Status.retracted]
# The SUPERSEDES edge laid by _append_state (core.py:268) is the STRUCTURAL witness:
# new --SUPERSEDES--> prior on every displacement. The matrix test can also assert the edge
# exists via the port if it wants the structural (not just ordinal) form of "superseded".
```

### The four-cell matrix construction (operation sequence — test-design discretion)
```python
# Source: composed from test_revision_spine.py idiom (parametrized backend fixture) + D-04/D-05
def test_retracted_superseded_matrix(backend: BackendPort) -> None:
    core = MemoryCore(backend)
    e = lambda: uuid.uuid7()
    # belief A: revise -> revise -> contract  yields, in its chain:
    #   state0 (active)   ── superseded+active     (overwritten value)
    #   state1 (active)   ── superseded+active     (overwritten, then contracted below)
    #   state2 (retracted)── current+retracted     (the contract tail)
    core.revise("s", "A", "v0", e()); core.revise("s", "A", "v1", e()); core.contract("s", "A", e())
    # belief B: revise -> revise  yields:
    #   state0 (active) ── superseded+active
    #   state1 (active) ── current+active
    core.revise("s", "B", "w0", e()); core.revise("s", "B", "w1", e())
    # belief C: revise -> contract -> revise  yields a superseded+retracted cell:
    #   state0 (active)    ── superseded+active
    #   state1 (retracted) ── superseded+retracted  (a retraction state later superseded)
    #   state2 (active)    ── current+active
    core.revise("s", "C", "x0", e()); core.contract("s", "C", e()); core.revise("s", "C", "x1", e())

    f = BeliefFilter()
    active_now    = {bs.belief_id for bs in core.query_scope("s", f, include_retracted=False)}
    with_retracted= {bs.belief_id for bs in core.query_scope("s", f, include_retracted=True)}
    assert active_now    == {"B", "C"}            # current+active cells
    assert with_retracted == {"A", "B", "C"}      # + the current+retracted cell (A)
    # superseded cells are NOT in query_scope (D-05) — read them via the chain:
    a_chain = core.get_revision_chain("A")
    assert any(s.status is Status.active    for s in a_chain[:-1])   # superseded+active exists
    c_chain = core.get_revision_chain("C")
    assert any(s.status is Status.retracted for s in c_chain[:-1])   # superseded+retracted exists
    # all four cells distinguishable across the two read methods (CHAIN-04 / D-04 / D-05).
```
*(The exact sequence is Claude's discretion per CONTEXT; this one produces all four cells and runs on both backends unchanged via the conftest fixture.)*

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Stored `CURRENT_STATE` edge/pointer (PITFALLS.md / ARCHITECTURE.md research-layer Cypher) | Derived ordering-max current (no pointer) | Phase-3 D-01 | `query_scope` derives current core-side; the research-layer query Cypher is the REJECTED alternative — read it only as the rejected form. |
| Public flag `include_deprecated` | `include_retracted` | Phase-4 D-03 | Standardises on the AGM term `retracted`; `Status` taxonomy unchanged. |
| "deprecated vs superseded" matrix vocabulary | "retracted vs superseded" | Phase-4 D-03 | The two clean axes (D-04); requirement + roadmap text updated. |

**Deprecated/outdated:**
- The word **"deprecated"** anywhere in the Phase-4 surface — replaced by **"retracted"** (D-03). `Status.deprecated` was rejected (Option B) — the status value stays `retracted`.
- `.planning/research/PITFALLS.md` and `ARCHITECTURE.md` stored-`CURRENT_STATE` query forms — SUPERSEDED by D-01; do not copy their Cypher.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Inclusive `[min, max]` (`>=`/`<=`) is the intended event-range boundary semantics | Pitfall 3 / Pattern 2 | Low — off-by-one at exact boundary only; pin with a boundary test in VALIDATION. The "range" wording in D-06 implies inclusive; flagged because exclusivity is a defensible alternative the user did not pin. |
| A2 | A single scope-wide `match_nodes` scan + core-side group-by is acceptable performance for both backends (vs N per-belief queries) | Pattern 2 | Low — both approaches are correct and parity-equivalent; the scan is the Claude's-discretion efficiency recommendation, reversible without API change. On ladybug it is ONE round-trip vs N. No profiling data exists yet (M0 is correctness-first). |

**All other claims are VERIFIED against read source or CITED from the locked CONTEXT/Phase-3 decisions.** A1/A2 are the only genuinely open choices, both low-risk and both inside Claude's discretion per CONTEXT.

## Open Questions

1. **Event-range boundary inclusivity (A1)**
   - What we know: D-06 says the range "filters which current beliefs you see"; `[min, max]` notation implies inclusive.
   - What's unclear: whether `event_id_max` equal to a tail's `source_event_id` includes or excludes it.
   - Recommendation: Implement inclusive (`>=` / `<=`), pin with an explicit boundary test in VALIDATION.md. Trivially reversible.

2. **Whether to assert the `SUPERSEDES` edge structurally in the matrix test, or only the ordinal `chain[:-1]` form**
   - What we know: D-05 names both the chain AND the `SUPERSEDES` edges as the superseded-cell witnesses; the edge is laid by `_append_state` and queryable via the port.
   - What's unclear: whether the matrix test should assert the structural edge (stronger, proves the displacement edge exists) or rely on the ordinal "non-tail" definition (simpler).
   - Recommendation: Assert the ordinal form as the primary check (it is what `query_scope`/`get_revision_chain` expose); optionally add one structural `SUPERSEDES`-edge presence assertion since CHAIN-04 literally names the edge. Test-design discretion per CONTEXT.

## Environment Availability

> No new external dependencies. The phase composes the already-installed stack. The one optional dependency (`ladybug`) is already gated by `pytest.importorskip` in the conftest fixture (skips, never fails, when absent).

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `pydantic` | `BeliefState`/`BeliefFilter` hydration | ✓ (required dep) | 2.13.4 | — (required) |
| `ladybug` | ladybug-backend parity tests | ✓ if `[ladybug]` extra installed | 0.17.1 | `importorskip` → memory-only test run (conftest already handles) |
| `pytest` | test runner | ✓ (dev) | 9.0.3 | — |
| `hypothesis` | optional `query_scope` parity property | ✓ (dev) | 6.155.2 | example-based matrix test alone suffices |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `ladybug` — absent → the parametrized fixture skips the ladybug param (Job-1 base-install path); the in-memory param still proves `query_scope` behaviour.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` 9.0.3 (+ optional `hypothesis` 6.155.2 for a parity property) |
| Config file | `pyproject.toml` (template `[tool.pytest.ini_options]`); shared fixtures in `tests/conftest.py` |
| Quick run command | `uv run pytest tests/test_query_scope.py -x -q` |
| Full suite command | `uv run pytest -q` |
| Backend parametrization | `backend` fixture (`params=["memory", "ladybug"]`, `importorskip`) — every `query_scope` test runs on BOTH backends (D-05) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HIST-01 | `query_scope` default returns only `current+active` beliefs, one per belief | unit (param both backends) | `uv run pytest tests/test_query_scope.py::test_query_scope_active_only -x` | ❌ Wave 0 |
| HIST-01 | `include_retracted=True` ALSO returns `current+retracted`; still one per belief | unit | `... ::test_query_scope_include_retracted -x` | ❌ Wave 0 |
| HIST-01 | Explicit `filter.status` overrides the flag (precedence, D-03) | unit | `... ::test_status_filter_precedence -x` | ❌ Wave 0 |
| HIST-01 | `belief_ids` narrows the result set | unit | `... ::test_belief_ids_filter -x` | ❌ Wave 0 |
| HIST-01 | `event_id_min/max` POST-filter current tails; newer-than-max belief is ABSENT not rewound (D-06) | unit | `... ::test_event_range_postfilter -x` | ❌ Wave 0 |
| HIST-01 | Event-range boundary is inclusive at exact min/max (A1) | unit | `... ::test_event_range_boundary_inclusive -x` | ❌ Wave 0 |
| HIST-01 | Empty/absent scope returns `[]`, creates no `Scope` node (D-08) | unit | `... ::test_empty_scope_returns_empty -x` | ❌ Wave 0 |
| HIST-01 | Result is deterministically `_order_key`-sorted; in-memory ≡ ladybug sequence (D-07) | unit (param) | `... ::test_query_scope_deterministic_order -x` | ❌ Wave 0 |
| HIST-01 / SC3 | No duplicate beliefs — exactly one state per `(scope,belief)` (D-01 postcondition) | unit + (optional) property | `... ::test_no_duplicate_beliefs -x` | ❌ Wave 0 |
| CHAIN-04 / SC2 | Four-cell matrix: all of current+active, current+retracted, superseded+active, superseded+retracted distinguishable via `query_scope` + `get_revision_chain` (+ `SUPERSEDES`) | unit (param both backends) | `... ::test_retracted_superseded_matrix -x` | ❌ Wave 0 |
| CHAIN-04 | `query_scope` NEVER returns a superseded (non-tail) state (D-05) | unit | `... ::test_query_scope_excludes_superseded -x` | ❌ Wave 0 |
| HIST-01 (regression) | `_current` write-side contract unchanged after the `_current_tail` refactor (Phase-3 keystone still green) | regression | `uv run pytest tests/test_invariants.py tests/test_revision_spine.py -q` | ✅ (exists) |
| D-03 (doc) | No `include_deprecated` token remains in code or planning docs | grep gate | `! grep -rn include_deprecated src tests .planning/REQUIREMENTS.md .planning/ROADMAP.md` | ❌ Wave 0 (check) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_query_scope.py -x -q` (the new file; ~sub-second on memory, both backends).
- **Per wave merge:** `uv run pytest -q` (full suite — must include the unchanged Phase-3 `test_invariants.py` keystone, proving the `_current` refactor is behaviour-preserving).
- **Phase gate:** Full suite green on BOTH backends + basedpyright strict clean + ruff clean + the `include_deprecated` grep gate empty, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_query_scope.py` — covers HIST-01 (all rows above) + CHAIN-04 matrix; parametrized over the existing `backend` fixture. NEW FILE.
- [ ] (optional) extend `tests/test_invariants.py` `_SpineMachine` with a `@invariant` asserting `query_scope` active set ≡ the oracle's derived-active set — turns SC3/D-01 into a stateful property. Discretionary; the example matrix test is the required deliverable.
- [ ] No `conftest.py` change needed — the `params=["memory","ladybug"]` fixture is reused verbatim.
- [ ] No framework install — `pytest` + `hypothesis` already in the dev group.

*(Existing infrastructure covers the regression surface; the only genuinely new test file is `test_query_scope.py`.)*

## Security Domain

> `security_enforcement` is not set to `false` in config, so this section is included. Phase 4 is an **embedded library read method** with no network, no auth, no session, no user input beyond a typed closed filter. The one relevant control is input-validation-by-construction, already satisfied by the closed `BeliefFilter`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface (embedded library tenant of NVM). |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | The core is a closed-subgraph tenant; access policy is NVM-layer (R19/R21). |
| V5 Input Validation | yes | Closed typed `BeliefFilter` (4 fields, no free `str`) — DATA-02 makes a query-injection / triple-structure leak **unrepresentable** at the seam. `query_scope` consumes ONLY these fields. |
| V6 Cryptography | no | No crypto in the read path. (UUID7 ids are identifiers, not secrets.) |

### Known Threat Patterns for the doxastica read surface

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via a free query string | Tampering / Info-disclosure | Already designed out: `BackendPort` exposes NO query-string method (BACK-01 LPG-primitive); `query_scope` composes `match_nodes` with `$param`-bound values + validated identifiers (ladybug.py `_validate_identifier`). Phase 4 adds no new interpolation. |
| Triple-structure / schema leak across the seam | Info-disclosure | `query_scope` returns frozen `BeliefState` models via `_hydrate`; no raw dict / `_ID`/`_LABEL` internal key escapes (the ladybug adapter already strips `_`-prefixed keys, core.py path returns models only). |
| Reading another tenant's namespace | Info-disclosure | The ladybug adapter is the sole writer/reader of its `{ns}_*` subgraph (CONN-02); `query_scope` runs entirely within the injected backend's namespace. No change in Phase 4. |

**No new security-sensitive surface is introduced.** The phase is a read composed of already-injection-proofed primitives.

## Sources

### Primary (HIGH confidence)
- `src/doxastica/core.py` (read in full) — `_order_key`, `_current`, `_append_state` (`SUPERSEDES` edge), `_hydrate`, `_decode_value`, `get_revision_chain`. The exact reuse surface.
- `src/doxastica/protocol.py` (read in full) — locked `query_scope` signature + `include_deprecated` docstring (the D-03 rename site); UUID7 ordering-contract docstring.
- `src/doxastica/models.py` (read in full) — `BeliefFilter` (closed 4 fields), `Status` (`{active, retracted}`), `BeliefState`.
- `src/doxastica/ports.py` (read in full) — `match_nodes` / `traverse` primitives; LPG-primitive granularity.
- `src/doxastica/backends/memory.py` + `backends/ladybug.py` (read in full) — `match_nodes` behaviour on both backends; `SUPERSEDES` schema; status stored as `status.value` string.
- `tests/conftest.py`, `tests/test_revision_spine.py`, `tests/test_invariants.py` (read in full) — the parametrized two-backend idiom, the shadow-oracle pattern, the keystone invariant `query_scope` must not break.
- `.planning/phases/04-retrieval-observation-surface/04-CONTEXT.md` — the locked D-01..D-08 decisions (authoritative).
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` — CHAIN-04 / HIST-01 text, the D-03 doc-edit targets, the Phase-3 `_current` "ordering-max over ALL statuses" fix.

### Secondary (MEDIUM confidence)
- RFC 9562 §5.7 (UUID7) canonical text form ↔ byte order — grounds Pitfall 3's "lowercase-hex string order == time order" claim (already pinned by Phase-1 DATA-03 in `protocol.py`).

### Tertiary (LOW confidence)
- None. No WebSearch / external docs were needed — the phase is wholly in-repo composition.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; reuse surface read directly from source.
- Architecture: HIGH — `query_scope` composition path verified against the actual port + models + both adapters.
- Pitfalls: HIGH — each pitfall is grounded in a specific read line (e.g. `_current`'s retracted→`None` at core.py:192) or a recorded Phase-3 STATE.md decision.
- Validation: HIGH — every requirement maps to a concrete pytest command over the existing fixture.
- Assumptions: only A1 (boundary inclusivity) and A2 (single-scan efficiency), both low-risk and within Claude's discretion.

**Research date:** 2026-06-18
**Valid until:** 2026-07-18 (stable — in-repo composition; no fast-moving external dependency. The only invalidator is a change to the Phase-3 `_current`/`_order_key` contract, which this phase deliberately preserves.)
