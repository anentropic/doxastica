# Phase 3: Append-Only Revision Spine (Keystone) - Research

**Researched:** 2026-06-16
**Domain:** AGM belief-revision write spine over an LPG-primitive backend port (derived-current, append-only chains, atomic per-op unit-of-work)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 — Current state is DERIVED, not a stored pointer.** `current(scope, belief)` is the
  maximal `BeliefState` for a `(scope_id, belief_id)` under the UUID7 ordering contract
  (`source_event_id` byte-order, `state_id` tiebreak). **No `CURRENT_STATE` edge/pointer.**
  Every write is a pure append; the store has **zero mutable elements**. Uniqueness becomes a
  *theorem* (unique max under a unique tiebreak), and SC3's invariant test becomes a
  **consistency check** (current-selection total + single-valued, AND `query_scope`-current ≡
  `get_scope_at(latest)` ≡ `HAS_REVISION` chain tail). Current is per-`(scope, belief)`, not
  per-`belief` (multi-scope value divergence). Runs on both backends. *This SUPERSEDES ROADMAP
  SC1/SC3 and the `.planning/research/PITFALLS.md` / `ARCHITECTURE.md` pointer-form Cypher.*

- **D-02 — World scope identity: reserved constant `WORLD_SCOPE_ID = "__world__"`.** doxastica
  exports the module constant (NVM imports it). `get_or_create_scope("__world__")` returns a
  `Scope(is_world=True)`; every other id is an ordinary peer (`is_world=False`). Singleton by
  construction. Public signature `get_or_create_scope(scope_id: str) -> Scope` is unchanged.

- **D-03 — World scope creation is LAZY; the `contract()` guard is STRUCTURAL.** No
  auto-creation; `"__world__"` is created on first `get_or_create_scope` or first write.
  `contract("__world__", …)` raises `WorldScopeContractionError` by checking
  `scope_id == WORLD_SCOPE_ID` **structurally, before any backend read/write** — holds even if
  the node was never created, cannot be bypassed by op ordering.

- **D-04 — `revise` ≡ `expand` are MECHANICALLY IDENTICAL at the core.** Both, inside one
  `unit_of_work`: (1) mint `state_id` via stdlib `uuid.uuid7()`; (2) append
  `BeliefState{state_id, belief_id, scope_id, source_event_id, value, status=active}`; (3) link
  `HAS_REVISION`; (4) lay `SUPERSEDES new → prior-current` **when a prior current exists**;
  (5) return the new `BeliefState`. `current` stays derived. The names persist for NVM's stance
  layer (above the seam) and for Phase 7 exercising both AGM families. No value-semantic
  consistency engine exists in the paper to port.

- **D-05 — `contract` semantics: vacuous on absent; appends one retracted state when it acts.**
  Contract on a belief with **no active current** is a **silent no-op returning `None`** (AGM
  Vacuity). When it acts: append **exactly one** `status=retracted` `BeliefState` whose `value`
  **copies the prior current value**, plus `HAS_REVISION` and `SUPERSEDES new(retracted) →
  prior-current`, in one `unit_of_work`. **The world-scope guard (D-03) fires FIRST**, before
  the absent/no-op check and before any backend access.

- **D-06 — Auto-create scope + Belief node on write; permissive preconditions.**
  `revise`/`expand`/`contract` create the scope if absent (reserved-id rule:
  `scope_id == "__world__"` → `is_world=True`) and auto-create the `Belief` node for a novel
  `belief_id`. No novel-vs-update preconditions: `revise`/`expand` always succeed on a valid
  scope. `revise` on a novel id = first assertion (nothing to supersede); `expand` on an
  existing id = append + supersede (identical to revise).

- **D-07 — Structural-edge model laid in this phase.** `HAS_REVISION` = the append-only version
  chain → feeds `get_revision_chain` (HIST-02) + the ordering-based derived current.
  `SUPERSEDES` (already a Phase-1 `EdgeType` + ladybug REL table) is laid by the core on every
  displacement. Phase 3 must add the **`HAS_REVISION` REL table** to the ladybug bootstrap
  (`IF NOT EXISTS`). `CURRENT_STATE` is **NOT** created (D-01). Structural edges are passed to
  `add_edge` as raw strings; `HAS_REVISION` stays a structural constant, never an
  `EdgeType`-enum member.

### Claude's Discretion

- `HAS_REVISION` hub (`Belief→state`) vs chain-link (`state→state`) shape + edge direction —
  constrained only by: `get_revision_chain(belief_id)` works AND derived current/superseded are
  computable from it + the ordering contract.
- Exactly how `value` is stored below the model layer (Phase-2 pattern: ladybug adapter
  JSON-encodes the opaque `value` into the `value STRING` column; in-memory adapter holds it
  verbatim) — no new decision, but see **the value-encoding contract** below (DEF-02-01 must be
  resolved this phase).
- Per-op transaction boundaries beyond "one `unit_of_work` per public write".

### Deferred Ideas (OUT OF SCOPE)

- **Materialize a stored current pointer** (head-node or edge + new delete/replace primitive)
  ONLY if `query_scope` profiling later demands it — addable without changing the public
  surface (`05 §6` cl.3). Not now (D-01).
- **`get_scope_at` full as-of reconstruction** — Phase 6 (HIST-03). Phase 3 needs only
  "current = as-of latest"; the general as-of cut + same-ms UUID7 resolution is Phase 6.
- **`query_scope` + the four-cell deprecated/superseded query matrix** — Phase 4 (CHAIN-04 /
  HIST-01). Phase 3 lays the `SUPERSEDES` edges + `status` it reads, not the query surface.
- **`add_edge` consumer edges + `get_impact` cascade** — Phase 5 (EDGE-01/02). The core's
  structural use of `SUPERSEDES` is distinct from consumer-added edges.
- **Optional `CONTRADICTS` edges** — future consumer-declared edge; not core, not this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCOPE-01 | `get_or_create_scope(scope_id)` creates/returns a named belief-holder | Compose `match_nodes("Scope", {scope_id})` → if absent `upsert_node("Scope", …)`; hydrate frozen `Scope`. Pattern 1. |
| SCOPE-02 | Privileged world scope; `contract()` on it raises `WorldScopeContractionError` | Structural guard `scope_id == WORLD_SCOPE_ID` first thing in `contract` body (D-03). Pattern 5. |
| SCOPE-03 | Multiple scopes are independent peers | `scope_id` is part of the `BeliefState` key + part of the derived-current match predicate; scopes never reference each other. Verified: per-`(scope,belief)` current divergence. |
| CHAIN-01 | `Belief` (stable identity) / `BeliefState` (immutable version) split | `Belief` node auto-created per novel `belief_id` (D-06); `BeliefState` per write. Both node tables exist (Phase 2). Pattern 2. |
| CHAIN-02 | Append-only `HAS_REVISION` chain — no delete/mutate of `BeliefState` or `HAS_REVISION` | Port has **no edge-delete / node-delete primitive**; `upsert_node` on a never-reused `state_id` PK is always an insert. Append-only by construction. |
| CHAIN-03 | Exactly one current per belief-in-scope, established atomically per write | *Mechanism-deviation (D-01):* current is the derived unique max; atomicity via `unit_of_work`; uniqueness is a theorem, verified by the consistency check. |
| OPS-01 | `revise` installs `value` as current, superseding prior current | Pattern 3 (revise≡expand body): append + `HAS_REVISION` + `SUPERSEDES → prior-current` if one exists. |
| OPS-02 | `expand` adds a belief with no conflict check | Same body as revise (D-04). Pattern 3. |
| OPS-03 | `contract` marks belief retracted; never deletes; world-scope guarded | Pattern 4: guard → derive current → if none return `None` (vacuity) → append one `retracted` state copying prior value + edges. |
| HIST-02 | `get_revision_chain(belief_id)` returns the full immutable version chain | Match all `BeliefState` for `belief_id` (across scopes — see Open Q2), sort by ordering contract. Pattern 6. |
</phase_requirements>

## Summary

Phase 3 fills the AGM operation bodies on the existing `MemoryCore` (Phase 2 left them
unwritten) by composing the **five LPG primitives already shipped and parity-tested on both
backends** — `upsert_node` / `add_edge` / `match_nodes` / `traverse` / `unit_of_work`. No new
storage primitive is needed. The single biggest modelling consequence — and the reason the port
needs no `delete`/`replace` primitive — is **D-01: current is derived, never stored.** I
verified end-to-end that `current(scope, belief)` composes from `match_nodes` + a Python `max`
over `(source_event_id, state_id)` string tuples, returning byte-identical results on the
in-memory oracle and the ladybug backend. This is the keystone: it makes "exactly one current"
a theorem (unique max under a unique tiebreak) rather than a maintained invariant a buggy write
could corrupt.

The UUID7 ordering contract reduces to **lexicographic string comparison**: I verified that
`str(uuid.uuid7())` sorts in exactly byte-order/time-order (the canonical hyphens sit at fixed
positions and do not perturb order). Both backends store ids as `STRING` (UUID7 text), so the
ordering-max is `max()` on the string in Python and `ORDER BY … DESC LIMIT 1` / `max(state_id)`
in Cypher — but **the port exposes no ORDER-BY / aggregate primitive**, so the sort happens
core-side in Python after a `match_nodes`, identically for both backends. This keeps the core
backend-agnostic and the two backends in lock-step.

There is **one inherited blocker that MUST be resolved this phase: DEF-02-01.** I reproduced it
live: ladybug 0.17.1 silently coerces a brace-shaped `value` string `{"x": 2}` to `{x: 2}`
(quotes stripped) — a silent corruption of the opaque value. The fix is the value-encoding
contract the model layer already advertises: the core `json.dumps()` the opaque `value` before
handing it to the port and `json.loads()` on read. I verified `json.dumps` round-trips all
hazard shapes (`{...}`, `[...]`, `"42"`, `"true"`, plain) byte-identically through ladybug. The
in-memory oracle must apply the identical encode/decode so the two stay equal.

**Primary recommendation:** Implement the three op bodies as thin compositions over the five
primitives, with `revise`≡`expand` sharing one private `_append_state(...)` helper; compute
derived-current via a single private `_current(scope_id, belief_id)` = `match_nodes` + Python
ordering-max (the one place the ordering contract lives); JSON-encode `value` at the core↔port
boundary on **both** backends (resolving DEF-02-01); add the `HAS_REVISION` REL table to the
ladybug bootstrap; and write the SC3 consistency check as a Hypothesis stateful machine with a
shadow-dict oracle asserting current-selection is total + single-valued and chain-tail ≡ current
on both backends.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| AGM op semantics (`revise`/`expand`/`contract`) | `MemoryCore` (core.py) | — | Belief-revision discipline is the backend-agnostic core (BACK-01); composes the port. |
| Derived-current selection (ordering-max) | `MemoryCore` (core.py) | — | The ordering contract (DATA-03) is core-owned; port has no ORDER-BY primitive. Lives in ONE private helper. |
| World-scope `contract` guard | `MemoryCore` (core.py) | — | Structural pre-backend check (D-03); a value-string comparison, no storage. |
| Model hydration + `value` JSON encode/decode | `MemoryCore` (core.py) | — | D-04 boundary: port returns raw `list[dict]`; core hydrates frozen pydantic + JSON-encodes opaque `value` (resolves DEF-02-01) — on BOTH backends for parity. |
| Atomic per-op transaction | Backend (`unit_of_work`) | `MemoryCore` (opens it) | The primitive lives in the adapter (ladybug `BEGIN/COMMIT/ROLLBACK`; in-memory snapshot/restore); the core wraps each public write in exactly one. |
| Node/edge persistence | Backend adapters | — | `upsert_node` / `add_edge` are append-only in practice (core never deletes). |
| `HAS_REVISION` REL table DDL | ladybug adapter (`_bootstrap_schema`) | — | New table this phase (D-07); in-memory needs no schema. |
| Structural invariant = consistency check | Test layer (Hypothesis stateful + oracle) | both backends via `conftest` | SC3/FORMAL-03 reframed by D-01; runs over the parametrized `backend` fixture. |

## Standard Stack

Phase 3 introduces **no new packages.** Everything needed is already pinned and verified
(Phase 1/2). The "stack" for this phase is the stdlib + the existing port.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `uuid` (stdlib) | Python 3.14 | `uuid.uuid7()` mints `state_id` (RFC 9562 §5.7, monotonic) | Native on the locked 3.14 floor; zero runtime dep. `[VERIFIED: ran `uuid.uuid7()` on 3.14.3 — exists, monotonic, str sorts in byte-order]` |
| `json` (stdlib) | Python 3.14 | Encode/decode opaque `value` at the core↔port boundary (resolves DEF-02-01) | The model layer already promises "JSON-encoded value". `[VERIFIED: json.dumps round-trips all hazard shapes through ladybug 0.17.1]` |
| `pydantic` | `>=2.11,<3` (2.13.4 installed) | Hydrate frozen `Scope`/`Belief`/`BeliefState` above the port | Sole required runtime dep (D-03). `[VERIFIED: pyproject.toml + Phase 2 usage]` |
| `ladybug` | `>=0.17,<0.18` (0.17.1) | Reference backend extra; `HAS_REVISION` REL table added this phase | Already wired behind `BackendPort`. `[VERIFIED: imported via uv --extra ladybug; ran live]` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `hypothesis` | `>=6.155` (dev group) | The SC3 consistency check as a stateful machine + shadow oracle | The Phase-3 structural-invariant test (the only postulate-grade test this phase needs; full AGM/Hansson suite is Phase 7). `[VERIFIED: dev-group in pyproject.toml]` |
| `pytest` / `pytest-cov` | `>=8.0` / `>=6.0` | Test runner over the parametrized `backend` fixture | All Phase-3 tests. `[VERIFIED: pyproject.toml]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Derived current (Python ordering-max over `match_nodes`) | Stored `CURRENT_STATE` pointer + a new port `delete_edge`/`replace` primitive | The pointer form needs a mutation primitive the port deliberately lacks, reintroduces a mutable element a buggy write can corrupt, and cannot host a per-`(scope,belief)` value on the single global `Belief` node. **Rejected by D-01.** Deferred as a pure profiling optimization. |
| Cypher `ORDER BY … LIMIT 1` / `max(state_id)` for current | Core-side Python `max()` after `match_nodes` | The port has no ORDER-BY/aggregate primitive (LPG-primitive granularity, BACK-01). A Cypher aggregate would couple the core to a dialect and break in-memory parity. **Use Python max** — verified byte-identical on both backends. |
| `json.dumps(value)` value encoding | Store `value` raw / `repr()` / `pickle` | Raw triggers DEF-02-01 silent corruption on brace-shaped strings; `repr` is not portable; `pickle` is an arbitrary-code execution surface and not a `STRING`. **`json` is what the model docstring already promises.** |

**Installation:** None — no new dependencies.

**Version verification:**
```
Python 3.14.3                 # uuid.uuid7() native, str(uuid7) sorts byte-order — VERIFIED live
ladybug 0.17.1 (extra)        # imported via `uv run --extra ladybug`; ran derived-current + DEF-02-01 probes
pydantic >=2.11,<3 (2.13.4)   # pyproject.toml
hypothesis >=6.155 (dev)      # pyproject.toml dependency-groups
```

## Package Legitimacy Audit

> No new packages are installed in this phase. All dependencies were vetted in Phase 1/2 and
> are pinned in `pyproject.toml`. Listed here for completeness; verdicts carry forward.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| pydantic | PyPI | 8+ yrs | very high | github.com/pydantic/pydantic | OK | Approved (Phase 1) |
| ladybug | PyPI | est. months (Kùzu fork) | low (niche) | github.com/LadybugDB/ladybug | OK | Approved (Phase 2, extra) |
| hypothesis | PyPI | 10+ yrs | very high | github.com/HypothesisWorks/hypothesis | OK | Approved (dev, Phase 1) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none
**Reminder:** the slopsquat token `ladybugdb` (the brand) does **not** exist on PyPI — the
installable is `ladybug`. Any new import/dep string must read `ladybug`. (Carried from CLAUDE.md.)

## Architecture Patterns

### System Architecture Diagram

```
public write call (NVM / consumer)
   revise / expand / contract(scope_id, belief_id, value?, source_event_id)
        │
        ▼
┌─────────────────────────── MemoryCore (core.py) — backend-agnostic ──────────────────────────┐
│                                                                                               │
│  contract ONLY: world-scope guard  ── scope_id == WORLD_SCOPE_ID? ──► raise WorldScope-       │
│                 (D-03, BEFORE backend)                                ContractionError        │
│        │ (not world)                                                                          │
│        ▼                                                                                       │
│  with backend.unit_of_work():            ◄── exactly ONE atomic scope per public write (CHAIN-03)
│        │                                                                                       │
│        ├─ ensure scope:   _current scope absent? ─► upsert_node("Scope", {scope_id, is_world})│  (D-06)
│        ├─ ensure belief:  upsert_node("Belief", {belief_id})  (idempotent, novel id)          │  (D-06)
│        │                                                                                       │
│        ├─ prior = _current(scope_id, belief_id)   ◄── DERIVED, not stored (D-01):             │
│        │        match_nodes("BeliefState", {scope_id, belief_id, status:active})              │
│        │        → Python max over (source_event_id, state_id) strings  ── ordering contract   │
│        │                                                                                       │
│        ├─ revise/expand (D-04):  append active state; if prior: SUPERSEDES new→prior          │
│        ├─ contract (D-05):       if prior is None ─► return None (vacuity)                     │
│        │                         else append retracted state copying prior.value;             │
│        │                              SUPERSEDES new(retracted)→prior                          │
│        │                                                                                       │
│        │   append-state helper:                                                                │
│        │     state_id = uuid.uuid7()                                                           │
│        │     props = {state_id, belief_id, scope_id, source_event_id, value:json.dumps(value),│  ◄ resolves DEF-02-01
│        │              status}                                                                   │
│        │     upsert_node("BeliefState", state_id, props)                                       │
│        │     add_edge("HAS_REVISION", <hub>, state_id)         ── append-only chain (D-07)     │
│        │     (if prior) add_edge("SUPERSEDES", state_id, prior.state_id)                       │
│        └─ hydrate & return frozen BeliefState (json.loads value back to opaque)                │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
        │                                   │
        ▼ (the 5 primitives only)           ▼
  InMemoryBackend (oracle)            LadybugBackend (reference, extra)
  dict store, value verbatim          Cypher MERGE/MATCH; value STRING col;
  snapshot/restore unit_of_work       BEGIN/COMMIT/ROLLBACK; HAS_REVISION REL table (new)
```

### Recommended Project Structure
No new modules. Phase 3 edits exactly:
```
src/doxastica/
├── core.py           # FILL op bodies + private _current / _append_state helpers + WORLD_SCOPE_ID use
├── __init__.py       # export WORLD_SCOPE_ID (NVM imports it, D-02)
└── backends/
    └── ladybug.py    # add HAS_REVISION REL table to _bootstrap_schema (D-07)
tests/
├── conftest.py       # (reuse the parametrized `backend` fixture as-is)
├── test_revision_spine.py   # NEW: op-body behaviour over both backends (SCOPE/CHAIN/OPS/HIST)
└── test_invariants.py       # NEW: Hypothesis stateful consistency check + shadow oracle (SC3)
```
`WORLD_SCOPE_ID` may live in `models.py` or a small `constants.py`; re-export from `__init__`.

### Pattern 1: `get_or_create_scope` (SCOPE-01 / SCOPE-02 / D-02)
**What:** Read-or-create a `Scope`, applying the reserved-id rule.
**When to use:** The scope entry point; the same ensure-scope step is reused inside each write (D-06).
```python
# core-side; composes match_nodes + upsert_node (no transaction needed for a pure get_or_create,
# but the write ops call the same ensure step INSIDE their unit_of_work)
def get_or_create_scope(self, scope_id: str) -> Scope:
    is_world = scope_id == WORLD_SCOPE_ID          # D-02 reserved-id rule
    existing = self._backend.match_nodes("Scope", {"scope_id": scope_id})
    if not existing:
        self._backend.upsert_node("Scope", scope_id,
                                  {"scope_id": scope_id, "is_world": is_world})
    return Scope(scope_id=scope_id, is_world=is_world)
```
Note: `upsert_node` excludes the PK from its SET loop (ladybug `_PK_BY_LABEL` rule), so re-upsert
is safe and idempotent — verified in Phase 2 parity tests.

### Pattern 2: derived-current — the ONE place the ordering contract lives (D-01 / DATA-03)
**What:** Compute `current(scope, belief)` from immutable data via `match_nodes` + Python max.
**When to use:** Every op (to find prior-current) and the consistency check.
**Why core-side max, not Cypher:** the port has no ORDER-BY/aggregate primitive (BACK-01);
keeping the sort in Python guarantees byte-identical results on both backends.
```python
# VERIFIED byte-identical on InMemoryBackend AND LadybugBackend (live probe, 2026-06-16)
def _current(self, scope_id: str, belief_id: str) -> dict | None:
    states = self._backend.match_nodes(
        "BeliefState",
        {"scope_id": scope_id, "belief_id": belief_id, "status": "active"},
    )
    if not states:
        return None
    # ordering contract (DATA-03): source_event_id byte-order, state_id tiebreak.
    # str(uuid7) lexical order == byte order == time order — VERIFIED on 3.14.3.
    return max(states, key=lambda s: (str(s["source_event_id"]), str(s["state_id"])))
```
> A "prior-current" for the SUPERSEDES edge means the prior current *before this write* —
> compute `_current` BEFORE the new `upsert_node`, inside the same `unit_of_work`.

### Pattern 3: `revise` ≡ `expand` shared body (OPS-01 / OPS-02 / D-04)
**What:** Append an active state; supersede the prior current if one exists.
```python
def revise(self, scope_id, belief_id, value, source_event_id) -> BeliefState:
    return self._append(scope_id, belief_id, value, source_event_id, Status.active)
expand = revise   # D-04: mechanically identical — OR define expand as a one-line delegate.

def _append(self, scope_id, belief_id, value, source_event_id, status) -> BeliefState:
    with self._backend.unit_of_work():                 # exactly one atomic scope (CHAIN-03)
        self._ensure_scope(scope_id)                   # D-06 (reserved-id rule inside)
        self._backend.upsert_node("Belief", belief_id, {"belief_id": belief_id})  # D-06
        prior = self._current(scope_id, belief_id)     # derived, BEFORE the append (D-01)
        state_id = uuid.uuid7()                         # stdlib, 3.14
        props = {
            "state_id": str(state_id), "belief_id": belief_id, "scope_id": scope_id,
            "source_event_id": str(source_event_id),
            "value": json.dumps(value),                 # resolves DEF-02-01
            "status": status.value,
        }
        self._backend.upsert_node("BeliefState", state_id, props)
        self._backend.add_edge("HAS_REVISION", belief_id, str(state_id))  # hub form (D-07)
        if prior is not None:
            self._backend.add_edge("SUPERSEDES", str(state_id), prior["state_id"])
        return self._hydrate(props)                     # json.loads value back to opaque
```
*Note `expand = revise` is a class-body alias — both names stay on the public surface for
Phase 7 (which exercises revision K\*2–6 AND expansion) and for NVM's stance layer.*

### Pattern 4: `contract` (OPS-03 / D-05 / D-03)
**What:** Guard world scope first; vacuous no-op on absent; else append one retracted state.
```python
def contract(self, scope_id, belief_id, source_event_id) -> None:
    if scope_id == WORLD_SCOPE_ID:                      # D-03: STRUCTURAL, BEFORE any backend
        raise WorldScopeContractionError(...)
    with self._backend.unit_of_work():
        self._ensure_scope(scope_id)
        prior = self._current(scope_id, belief_id)     # derived
        if prior is None:                              # D-05 vacuity: silent no-op
            return None
        state_id = uuid.uuid7()
        props = {
            "state_id": str(state_id), "belief_id": belief_id, "scope_id": scope_id,
            "source_event_id": str(source_event_id),
            "value": prior["value"],                   # D-05: copy the prior value VERBATIM
            "status": Status.retracted.value,
        }
        self._backend.upsert_node("BeliefState", state_id, props)
        self._backend.add_edge("HAS_REVISION", belief_id, str(state_id))
        self._backend.add_edge("SUPERSEDES", str(state_id), prior["state_id"])
        return None
```
> **Subtlety (value copy):** `prior["value"]` from `match_nodes` is the **already-encoded** JSON
> string (the stored form). Store it verbatim — do NOT `json.dumps` it again, or you double-encode.
> Symmetric: `_append` (Pattern 3) takes the *opaque* value and encodes once; `contract` copies the
> *stored* form and re-stores it. Get this boundary right or the retracted state's value diverges
> from the superseded one.

### Pattern 5: world-scope guard ordering (SCOPE-02 / D-03)
The guard is a plain string comparison placed as the **first statement** of `contract`, before
`unit_of_work` and before any `match_nodes`/`upsert_node`. It therefore holds even when the
world node was never created (lazy creation, D-03) and cannot be reordered around. This is the
"raises before any write" success criterion (SC1).

### Pattern 6: `get_revision_chain` (HIST-02 / D-07)
**What:** Return every revision of `belief_id` in ordering-contract order.
```python
def get_revision_chain(self, belief_id: str) -> list[BeliefState]:
    states = self._backend.match_nodes("BeliefState", {"belief_id": belief_id})
    states.sort(key=lambda s: (str(s["source_event_id"]), str(s["state_id"])))  # ordering contract
    return [self._hydrate(s) for s in states]
```
*See Open Q2 — whether the chain is scoped or cross-scope (the protocol signature takes only
`belief_id`).*

### Anti-Patterns to Avoid
- **Storing a `CURRENT_STATE` pointer/edge** — D-01 forbids it; the port has no mutation
  primitive to maintain it. Current is derived.
- **Sorting/aggregating in Cypher for derived-current** — couples the core to a dialect and
  breaks in-memory parity. Use Python `max`/`sort` after `match_nodes`.
- **Storing `value` raw on ladybug** — triggers DEF-02-01 silent coercion. Always `json.dumps`.
- **Double-encoding the retracted value** — `contract` copies the already-encoded stored form;
  don't `json.dumps` it again (Pattern 4 subtlety).
- **Multiple `unit_of_work` per public write** — exactly one atomic scope per op (CHAIN-03).
- **Computing prior-current AFTER the new append** — you'd supersede the wrong (or new) state.
- **Adding `HAS_REVISION` to the `EdgeType` enum** — it stays a structural string constant (D-07).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID7 generation | A custom RFC-9562 byte layout / `uuid-utils` dep | stdlib `uuid.uuid7()` (3.14) | Native, monotonic, zero dep — VERIFIED. The whole 3.14-floor decision exists for this. |
| Total-order comparison of ids | A custom byte-array comparator | Python `max`/`sorted` on `str(uuid)` | `str(uuid7)` lexical order == byte order — VERIFIED. No byte juggling needed. |
| Atomicity of a multi-step write | A hand-rolled try/except rollback in the core | `backend.unit_of_work()` | Already implemented + parity-tested on both backends (ladybug `BEGIN/COMMIT/ROLLBACK`, in-memory snapshot/restore). |
| Idempotent node insert | "exists? then update else insert" round-trips | `upsert_node` (`MERGE … SET`) | One round-trip, race-free, verified idempotent (Phase 2). |
| Opaque value serialization | `repr`/`pickle`/raw | `json.dumps`/`json.loads` at the core boundary | Portable, the model docstring's promise, resolves DEF-02-01 — VERIFIED round-trip. |
| Cycle-safe traversal (future) | Python BFS in the core | `backend.traverse` | Already the port primitive (Phase 5 uses it). Phase 3 doesn't traverse for current. |

**Key insight:** Phase 3 is almost pure *composition*. The five primitives + stdlib `uuid`/`json`
+ frozen pydantic models are everything; the novel logic is the ordering-max selection and the
op-body sequencing, both small and both core-owned.

## Runtime State Inventory

> Phase 3 is greenfield feature implementation (filling unwritten op bodies + adding one REL
> table), NOT a rename/refactor/migration. No pre-existing runtime state stores the data this
> phase introduces. The one schema addition is covered below.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no prior belief data exists; this phase WRITES the first `BeliefState`/`Belief`/`Scope` rows. | None (greenfield). |
| Live service config | None — embedded in-process DB only (`:memory:` per test; caller-injected conn in prod). | None. |
| OS-registered state | None. | None. |
| Secrets/env vars | None (`UV_NO_SYNC=1` is a dev convenience, unrelated). | None. |
| Build artifacts | None new; `HAS_REVISION` REL table is created idempotently at bootstrap (`IF NOT EXISTS`), so existing test DBs (all `:memory:`, recreated per example) pick it up automatically. | None — no migration; fresh DBs every run. |

**Schema addition (the one structural change):** ladybug `_bootstrap_schema` gains
`CREATE REL TABLE IF NOT EXISTS {ns}_HAS_REVISION(FROM {ns}_Belief TO {ns}_BeliefState)` (hub
shape, D-07). Idempotent; no data migration (every DB is fresh `:memory:`). The in-memory backend
needs no schema. *If the chain-link `state→state` shape is chosen instead, the FROM/TO is
`BeliefState→BeliefState` — see Open Q1.*

## Common Pitfalls

### Pitfall 1: DEF-02-01 — ladybug silently corrupts brace-shaped value strings (INHERITED BLOCKER)
**What goes wrong:** Storing `value="{\"x\": 2}"` raw on ladybug reads back `{x: 2}` — quotes
stripped, value corrupted. Brackets `[1,2,3]` happen to survive; braces do not.
**Why it happens:** ladybug 0.17.1 coerces JSON-object/list-shaped `$param` STRING binds toward
STRUCT/LIST. Confirmed live (2026-06-16).
**How to avoid:** The core `json.dumps(value)` before the port write and `json.loads` on read,
on **both** backends (so the in-memory oracle stays byte-equal). VERIFIED: `json.dumps` round-trips
`{...}`, `[...]`, `"42"`, `"true"`, plain through ladybug byte-identically. This is the
**value-encoding contract** the Phase-2 deferral (DEF-02-01) named.
**Warning signs:** The existing `test_value_string_round_trips_ladybug` is an `xfail(strict=False)`
— once the encoding contract lands, **flip it to a passing test** (or strict xpass) so the
regression is proven closed, mirroring the Phase-2 security-verification discipline.

### Pitfall 2: Double-encoding the contracted value
**What goes wrong:** The retracted state's `value` no longer equals the superseded state's value
(extra quotes/escapes), breaking `get_scope_at` history fidelity (Phase 6) and the SC3 chain-tail
equivalence.
**Why it happens:** `contract` copies `prior["value"]` from `match_nodes`, which is *already the
encoded JSON string*; `json.dumps`-ing it again double-encodes.
**How to avoid:** In `contract`, store `prior["value"]` verbatim. Only `_append` (which receives
the *opaque* value) encodes. Add a test asserting the retracted state's stored `value` is
byte-identical to the superseded state's stored `value`.

### Pitfall 3: Computing prior-current after the append
**What goes wrong:** The new state becomes its own "prior current" (or the max flips), so the
SUPERSEDES edge points wrong or is missing.
**Why it happens:** Calling `_current` after `upsert_node` includes the just-written state.
**How to avoid:** Always compute `prior = self._current(...)` BEFORE the new `upsert_node`,
inside the same `unit_of_work`.

### Pitfall 4: `is_world` type round-trip across backends
**What goes wrong:** A scope created as world reads back non-world, or `match_nodes({"is_world": True})`
misses on one backend.
**Why it happens:** ladybug stores `is_world` as a native `BOOLEAN` column (schema: `is_world BOOLEAN`);
the in-memory oracle stores the Python `bool` verbatim. Both handle `True`/`False` — Phase-2
`test_scope_upsert_parity` already proves `match_nodes("Scope", {"is_world": True})` agrees. But
confirm the hydrated `Scope.is_world` is a real `bool`, not a `0/1` int, after the round-trip.
**How to avoid:** Derive `is_world` from `scope_id == WORLD_SCOPE_ID` in the core (Pattern 1) rather
than trusting the stored column for the return value — the stored column is for `match_nodes`
filtering only. Add a parity test that a world scope round-trips `is_world=True` on both backends.

### Pitfall 5: Treating `revise`/`expand` as different at the core
**What goes wrong:** Drift between the two op bodies; Phase 7's oracle has to model two behaviours
that are actually one.
**Why it happens:** The names *suggest* a consistency check that the paper does not perform (D-04).
**How to avoid:** Single shared `_append` helper; `expand = revise` (or a one-line delegate). The
difference is purely nominal (for the NVM stance layer + Phase-7 family coverage).

### Pitfall 6: Same-`source_event_id` collisions and the tiebreak
**What goes wrong:** Two states share a caller `source_event_id` (callers may collide
intra-ms — monotonicity is NOT demanded of the caller, DATA-03); current selection is ambiguous
without the tiebreak.
**Why it happens:** Only `source_event_id` is used for ordering.
**How to avoid:** The ordering key is the PAIR `(source_event_id, state_id)`. `state_id` is
core-minted `uuid.uuid7()` — write-monotonic — so it deterministically breaks ties in true
insertion order. Pattern 2's `max` key already encodes this. The consistency check should
generate colliding `source_event_id`s to exercise it.

## Code Examples

### Deriving current per `(scope, belief)` — VERIFIED byte-identical on both backends
```python
# Live probe 2026-06-16 (uv run --extra ladybug). Output identical for InMemoryBackend and
# LadybugBackend:
#   current(s1,b1) = ...0003   current(s2,b1) = ...0009   current(s1,missing) = None
def _current(self, scope_id, belief_id):
    states = self._backend.match_nodes(
        "BeliefState", {"scope_id": scope_id, "belief_id": belief_id, "status": "active"})
    return max(states, key=lambda s: (str(s["source_event_id"]), str(s["state_id"]))) if states else None
```

### Value-encoding round-trip — VERIFIED resolves DEF-02-01
```python
import json
# Raw store on ladybug:  '{"x": 2}'  -> reads back '{x: 2}'   (CORRUPT)
# json.dumps store:      json.dumps('{"x": 2}') -> '"{\\"x\\": 2}"' -> json.loads -> '{"x": 2}' (OK)
stored = json.dumps(value)        # on write, in _append
opaque = json.loads(stored)       # on read, in _hydrate
```

### ladybug `HAS_REVISION` REL table (hub shape) — add to `_bootstrap_schema`
```python
# Source: src/doxastica/backends/ladybug.py _bootstrap_schema (pattern matches existing edge loop)
ns = self._ns
self._exec(
    f"CREATE REL TABLE IF NOT EXISTS {ns}_HAS_REVISION"
    f"(FROM {ns}_Belief TO {ns}_BeliefState)"          # hub: Belief -> BeliefState (D-07 sketch)
)
# (chain-link alternative: FROM {ns}_BeliefState TO {ns}_BeliefState — see Open Q1)
```

### `revise`/`expand`/`contract` ordering on STRING ids — VERIFIED in ladybug
```python
# Live: ORDER BY n.state_id DESC LIMIT 1 and max(state_id) both pick the byte-order max over
# STRING-stored UUID7s; group max(state_id) by (scope_id, belief_id) yields one current per
# (scope, belief). The CORE does this in Python (no port aggregate primitive); the Cypher form
# is shown only to confirm the ordering semantics agree.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ROADMAP SC1/SC3: stored `CURRENT_STATE` pointer re-pointed atomically per write | D-01: current is DERIVED (ordering-max over immutable states); uniqueness is a theorem; SC3 invariant → consistency check | Phase-3 CONTEXT (2026-06-15) | No mutation primitive needed; zero mutable elements; the `.planning/research/*` pointer Cypher is the rejected alternative. |
| `value` stored raw (Phase 2 left it untyped/unencoded) | `json.dumps`/`json.loads` value-encoding contract at the core boundary | Phase 3 (this phase resolves DEF-02-01) | Closes the inherited ladybug brace-coercion corruption; flips the xfail to passing. |
| `revise` performs a consistency check, `expand` does not (classical AGM intuition) | `revise` ≡ `expand` mechanically (D-04); difference lives in NVM's stance layer | Phase-3 CONTEXT, grounded in the Kumiho paper | One shared `_append`; trivial Phase-7 oracle. |

**Deprecated/outdated:**
- `.planning/research/PITFALLS.md` and `ARCHITECTURE.md` revise/contract Cypher (delete-then-create
  `CURRENT_STATE` edge): **superseded by D-01.** Read as the rejected pointer-form alternative.
- ROADMAP Phase-3 SC1/SC3 wording ("`CURRENT_STATE` pointer", "re-points exactly one"):
  superseded by D-01's derived-current consistency check.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `HAS_REVISION` hub shape (`Belief→BeliefState`) is the right default over chain-link (`state→state`). | D-07 / Patterns 3,6 / Open Q1 | LOW — both satisfy `get_revision_chain` (the chain is reconstructed by ordering-sort regardless of edge shape, since derived-current uses `match_nodes` not the edge). Hub is simpler and matches the design sketch. Planner ratifies. `[ASSUMED]` |
| A2 | `get_revision_chain(belief_id)` is **cross-scope** (all scopes' states for that belief), matching the protocol signature taking only `belief_id`. | Pattern 6 / Open Q2 | MEDIUM — if it should be scope-scoped, the signature can't express it (no scope arg). Likely cross-scope by design (the chain is the belief's global version history); but confirm against `05 §6` intent. `[ASSUMED]` |
| A3 | `_DEPTH_CEILING`/traverse is NOT needed for Phase-3 derived-current (current uses `match_nodes`, not `traverse`). | Pattern 2 | LOW — verified: derived-current is a `match_nodes` + Python max, no graph walk. `traverse` first matters in Phase 5. `[VERIFIED: live probe]` |
| A4 | The SC3 consistency check belongs in this phase as a Hypothesis stateful machine (a scoped subset), with the FULL AGM/Hansson suite assembled in Phase 7. | Validation Architecture | LOW — SC3/FORMAL-03 are the Phase-3 success criterion; CONTEXT D-01 explicitly reframes the invariant test as a consistency check for this phase. `[CITED: 03-CONTEXT.md D-01]` |

## Open Questions

1. **`HAS_REVISION` shape: hub (`Belief→state`) vs chain-link (`state→state`)?**
   - What we know: Claude's Discretion (D-07). Hub matches the design sketch; both satisfy
     `get_revision_chain`. Derived-current does NOT depend on the edge shape (it uses
     `match_nodes` + ordering, not edge-walk).
   - What's unclear: whether any later phase (Phase 6 `get_scope_at`) wants to *walk*
     `HAS_REVISION` rather than re-`match_nodes`. If so, chain-link gives a literal chain to
     traverse; hub gives a fan-out from the Belief.
   - Recommendation: **Hub form** (`FROM Belief TO BeliefState`) — simplest, matches the sketch,
     and Phase 6 reconstructs by ordering-sort anyway (no edge-walk needed). Revisit only if
     Phase-6 profiling wants a walkable chain.

2. **Is `get_revision_chain(belief_id)` scoped or cross-scope?**
   - What we know: the protocol signature takes only `belief_id` (no `scope_id`), so it cannot be
     scoped at the public surface. HIST-02 says "the full immutable version chain".
   - What's unclear: in multi-scope, the same `belief_id` has states in several scopes; "the
     chain" is naturally the union across scopes ordered by the contract.
   - Recommendation: return **all states for `belief_id` across scopes**, ordered by
     `(source_event_id, state_id)` (Pattern 6). This matches the signature and HIST-02's "full".
     Flag for the planner to confirm against `05 §6` and to add a multi-scope chain test.

3. **Does `_ensure_scope` inside a write need to re-derive `is_world`, and should an existing
   non-world scope ever flip?**
   - What we know: D-06 says apply the reserved-id rule on auto-create. A pre-existing
     `"__world__"` scope is already `is_world=True`; a non-`"__world__"` id can never be world.
   - Recommendation: `is_world` is a pure function of `scope_id == WORLD_SCOPE_ID`; never flip an
     existing scope. The ensure step only needs to create-if-absent. No ambiguity in practice.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 + `uuid.uuid7()` | `state_id` minting | ✓ | 3.14.3 | — (floor is 3.14; no shim) |
| `json` (stdlib) | value-encoding contract | ✓ | stdlib | — |
| `pydantic` | model hydration | ✓ | 2.13.4 | — |
| `ladybug` (extra) | reference backend + `HAS_REVISION` DDL | ✓ (via `uv run --extra ladybug`) | 0.17.1 | in-memory backend (base install runs the non-ladybug subset) |
| `hypothesis` (dev) | SC3 consistency check | ✓ | dev group | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `ladybug` is an optional extra — the base-install CI job
(pydantic-only) runs the in-memory subset; the ladybug job runs the full both-backend suite. This
matches the Phase-2 two-environment CI (D-03). Phase-3 tests must keep the `importorskip` pattern
so the ladybug-specific assertions skip (not fail) in the base job.

## Validation Architecture

> `workflow.nyquist_validation` is not set to `false` in `.planning/config.json` workflow keys
> (treated as enabled). This section maps Phase-3 requirements to tests.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x (`>=8.0`) + pytest-cov; hypothesis `>=6.155` for the stateful machine |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`addopts = "-v"`) |
| Quick run command | `UV_NO_SYNC=1 uv run --extra ladybug pytest tests/test_revision_spine.py -x` |
| Full suite command | `UV_NO_SYNC=1 uv run --extra ladybug pytest` (both backends via the parametrized `backend` fixture) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCOPE-01 | get_or_create returns/creates a scope; idempotent | unit (both backends) | `pytest tests/test_revision_spine.py::test_get_or_create_scope -x` | ❌ Wave 0 |
| SCOPE-02 | `contract("__world__", …)` raises before any write | unit | `pytest tests/test_revision_spine.py::test_world_contract_raises -x` | ❌ Wave 0 |
| SCOPE-03 | same belief_id diverges per scope (current is per (scope,belief)) | unit | `pytest tests/test_revision_spine.py::test_cross_scope_divergence -x` | ❌ Wave 0 |
| CHAIN-01 | Belief/BeliefState split; one Belief node per belief_id | unit | `pytest tests/test_revision_spine.py::test_belief_state_split -x` | ❌ Wave 0 |
| CHAIN-02 | no op deletes/mutates a BeliefState or HAS_REVISION edge | invariant | `pytest tests/test_invariants.py::TestSpine -x` (`@invariant` chain-immutability) | ❌ Wave 0 |
| CHAIN-03 | exactly one current per (scope,belief), atomic per write | invariant (consistency check, D-01) | `pytest tests/test_invariants.py::TestSpine -x` | ❌ Wave 0 |
| OPS-01 | revise installs current, supersedes prior | unit | `pytest tests/test_revision_spine.py::test_revise_supersedes -x` | ❌ Wave 0 |
| OPS-02 | expand == revise (no conflict check) | unit | `pytest tests/test_revision_spine.py::test_expand_equals_revise -x` | ❌ Wave 0 |
| OPS-03 | contract: vacuous on absent; one retracted state copying prior value | unit | `pytest tests/test_revision_spine.py::test_contract_vacuity_and_acts -x` | ❌ Wave 0 |
| HIST-02 | get_revision_chain returns full ordered chain | unit | `pytest tests/test_revision_spine.py::test_revision_chain_order -x` | ❌ Wave 0 |
| DEF-02-01 | value JSON-round-trips byte-identically on BOTH backends | regression (flip xfail) | `pytest tests/test_backend_parity.py::test_value_string_round_trips_ladybug` | ⚠️ exists as xfail — flip to passing |

### Sampling Rate
- **Per task commit:** `UV_NO_SYNC=1 uv run --extra ladybug pytest tests/test_revision_spine.py -x` (sub-30s).
- **Per wave merge:** `UV_NO_SYNC=1 uv run --extra ladybug pytest` (full both-backend suite + invariants).
- **Phase gate:** full suite green on BOTH the base (pydantic-only) and ladybug CI jobs before `/gsd-verify-work`; the DEF-02-01 xfail flipped to passing.

### Wave 0 Gaps
- [ ] `tests/test_revision_spine.py` — covers SCOPE-01/02/03, CHAIN-01, OPS-01/02/03, HIST-02 over the parametrized `backend` fixture.
- [ ] `tests/test_invariants.py` — Hypothesis `RuleBasedStateMachine` with `Bundle`s for scopes/beliefs, `@initialize` per example, `@invariant` for chain-immutability + current-is-total-single-valued, `@precondition` to route world-scope-contract to its own assertion, and a shadow-dict oracle (`{(scope,belief): current_value}`) — the SC3 consistency check (D-01), run on both backends.
- [ ] Flip `tests/test_backend_parity.py::test_value_string_round_trips_ladybug` from `xfail` to a passing assertion once the value-encoding contract lands (DEF-02-01 closed).
- [ ] Framework install: none — pytest + hypothesis already in the dev group.

## Security Domain

> `security_enforcement` is not disabled in config (treated as enabled). Phase 3 is an in-process
> library with no network/auth/session surface; most ASVS categories are N/A. Input-handling and
> injection-safety are the live concerns.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | In-process library; no auth. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | Tenancy (R19) handled by the namespace boundary, already in place (Phase 2). |
| V5 Input Validation | yes | Frozen pydantic models validate `Scope`/`BeliefState` at the seam (`extra="forbid"`); `value` is opaque and **never** interpreted/eval'd/used to build a query — it is `json.dumps`-encoded and stored as data only. |
| V6 Cryptography | no | No crypto; UUID7 is an id, not a secret. |

### Known Threat Patterns for the doxastica core
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via belief data | Tampering | All belief DATA flows through `$param` binds (Phase-2 invariant, BACK-04 §). Phase-3 op bodies pass values to `upsert_node`/`add_edge` which already bind — the core writes NO Cypher. |
| Identifier injection via `scope_id`/`belief_id` | Tampering | These are stored as `$param` bind VALUES (node props), never interpolated into Cypher (only the validated `namespace` + fixed labels are interpolated — Phase-2 `_NS_RE` guard). A scope named `"; DROP …"` is inert data. |
| Opaque `value` as an execution surface | Tampering / Elevation | Stored verbatim as a JSON STRING, never eval'd or used to build a query (BACK-04 §6). The DEF-02-01 fix (`json.dumps`) reinforces this — value is pure data. |
| Value corruption (DEF-02-01) | Tampering (integrity) | The JSON value-encoding contract — the integrity fix this phase delivers; verified round-trip. |

## Sources

### Primary (HIGH confidence)
- Live codebase (this repo, read in full): `src/doxastica/{protocol,ports,models,core,errors}.py`,
  `src/doxastica/backends/{memory,ladybug}.py`, `tests/{conftest,test_backend_parity}.py`,
  `pyproject.toml`, `__init__.py` — exact signatures + the 5 primitives + the parametrized fixture.
- Live ladybug 0.17.1 probes (via `uv run --extra ladybug`, 2026-06-16): derived-current
  byte-identical on both backends; `str(uuid7)` lexical == byte order on Python 3.14.3;
  DEF-02-01 brace-coercion reproduced AND `json.dumps` mitigation verified round-trip.
- `.planning/phases/03-…/03-CONTEXT.md` — locked decisions D-01..D-07 (authoritative).
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` — scope, SCs, history.
- `../narrative-vm/_design/v2/05-nvm-memory-core.md` §6 — world scope canonical truth,
  world-contraction forbidden, `CURRENT_STATE` "materialized only if profiling demands" (grounds D-01/02/03).

### Secondary (MEDIUM confidence)
- `.planning/phases/02-…/02-RESEARCH.md` — DEF-02-01 deferral, value-encoding note, SC4 traverse
  details, `_PK_BY_LABEL` source-of-truth.
- CLAUDE.md — pydantic-only required dep, ladybug-extra, append-only discipline, parameterized
  Cypher only, `ladybug`-not-`ladybugdb`.

### Tertiary (LOW confidence)
- `.planning/research/PITFALLS.md` / `ARCHITECTURE.md` — read only as the REJECTED pointer-form
  alternative (superseded by D-01); not used as a positive source.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; all versions verified live against the installed env.
- Architecture: HIGH — derived-current composition and value-encoding both verified end-to-end
  on both backends with live probes; op-body patterns are direct compositions of the read source.
- Pitfalls: HIGH — DEF-02-01 reproduced and mitigated live; the rest derive from the locked
  decisions + the actual port signatures.

**Project Constraints (from CLAUDE.md):**
- Runtime deps: `pydantic` only required; `ladybug` is the `[ladybug]` extra (D-03). No third
  runtime dep — Phase 3 adds none (stdlib `uuid`/`json` only).
- Zero NVM/game/narrative/LLM concepts in core code. `WORLD_SCOPE_ID = "__world__"` is a neutral
  reserved id, not a narrative concept.
- Append-only: no op removes/rewrites `BeliefState` or `HAS_REVISION`; the port has no delete
  primitive — enforced by construction. World-scope `contract()` is an error.
- Parameterized Cypher only: the core writes NO Cypher; it composes the port, which already binds
  all data via `$param` (only the validated namespace + fixed labels are interpolated).
- Sync core (no async). basedpyright strict + ruff clean must hold.
- Import name `ladybug` (never `ladybugdb`).

**Research date:** 2026-06-16
**Valid until:** 2026-07-16 (stable — internal codebase + a pinned ladybug 0.17.1; re-verify only
if the `ladybug` pin or the port signatures change).
