# Phase 5: Edge Model & Contraction Cascade - Research

**Researched:** 2026-06-18
**Domain:** Graph traversal direction extension + thin port composition (no new deps, no new external tech)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `get_impact(X)` returns the transitive set of `BeliefState`s that **depend on X**
  (downstream dependents), called ON the retracted/contracted node. NOT "what X depends on."
- **D-02:** `reached` EXCLUDES the start node X. Shape is the locked
  `ImpactResult(reached: tuple[BeliefState, ...], frontier: frozenset[UUID], truncated: bool)`.
  `truncated = len(frontier) > 0`; `depth=None` ⇒ full closure, empty frontier, `truncated=False`.
- **D-03:** `get_impact` traverses **`{DEPENDS_ON, DERIVED_FROM}`**. `DERIVED_FROM` is REQUIRED
  (NVM invalidation edges are `DERIVED_FROM` specialisations). `SUPERSEDES` is EXCLUDED by
  construction (it is the internal revision-spine edge `_append_state` lays).
- **D-04:** The cascade walks edges INTO X. Edge-storage convention is dependent→source, so the
  impact walk runs AGAINST the arrows. The current `traverse` follows OUTGOING edges only.
- **D-05 (the one real port change):** **add a `direction='in'|'out'` parameter to the port
  `traverse` primitive**, default preserving current OUTGOING behaviour (for Phase 6
  `get_scope_at`). `get_impact` calls it with `direction='in'`.
  - Ladybug: one-token Cypher change — `MATCH (x)<-[:{rels}*1..N]-(d)` instead of `-[...]->`.
    All injection-safety / `_EDGE_ENDPOINTS` validation / `_DEPTH_CEILING` / `bound==0` frontier
    logic carries over unchanged; only the arrow flips.
  - In-memory: walk a reverse adjacency index (mirror of `_out_edges`).
  - `ports.py` docstring + `docs/backend-contract.md` (BACK-04) must document `direction`; Phase 7
    conformance must exercise BOTH directions on BOTH backends.
- **D-06:** Public `MemoryCore.add_edge` is a near-passthrough to
  `self._backend.add_edge(edge_type, from_id, to_id)` wrapped in ONE `unit_of_work()`. Idempotency
  is already guaranteed by both backends. Public signature takes the closed `EdgeType` enum.
- **D-07:** No endpoint-existence validation in the core (mechanism, not policy). The port's
  `MATCH ... MERGE` silently no-ops on a missing endpoint; the core adds NO raise. **Planner must
  confirm a test pins this silent-no-op behaviour rather than leaving it incidental.**

### Claude's Discretion

- Whether `depth` bounds *hops* vs *unique nodes* — already defined by the existing `traverse`
  (hop-bounded BFS layers); `get_impact` inherits it. No new decision unless the planner finds an
  inconsistency.
- Internal helper factoring for the reverse-adjacency index in the in-memory backend.

### Deferred Ideas (OUT OF SCOPE)

- Edge *properties* on `add_edge` — both backends `raise NotImplementedError` on non-empty
  `props` (IN-01). Storing edge props is a future port extension, NOT Phase 5.
- `get_scope_at` reuse of the new `direction` parameter — Phase 6 uses `traverse` OUTGOING; the
  default must preserve current behaviour so Phase 6 is unaffected.
- Phase 7 conformance: Relevance / Core-Retainment postulate tests, parameterising the full suite
  over both backends — exercises `get_impact` but is its own phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EDGE-01 | `add_edge(from_state, to_state, edge_type)` for generic typed edges `SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM`, no epistemic semantics in core | Both backends already implement idempotent `add_edge`; `EdgeType` enum exists; rel tables for all three already bootstrapped in ladybug DDL (ladybug.py:205-209). `MemoryCore.add_edge` body is a one-call passthrough inside `unit_of_work` (D-06). See `Architecture Patterns` Pattern 1. |
| EDGE-02 | `get_impact(belief_state_id, depth)` bounded-depth, cycle-safe dependency traversal (cascade mechanism; policy is consumer's) | `traverse` already cycle-safe + bounded + `(reached, frontier)`. Phase 5 adds the `direction='in'` param, then composes `get_impact` = `traverse(start, {DEPENDS_ON, DERIVED_FROM}, depth, 'in')` → `_hydrate` → `ImpactResult`. See Pattern 2. |
</phase_requirements>

## Summary

Phase 5 is **mostly wiring over already-built substrate**, with exactly **one genuine new
capability**: a `direction='in'|'out'` parameter on the port `traverse` primitive (D-05). Both
backends already ship idempotent `add_edge`, a cycle-safe bounded `traverse` returning
`(reached, frontier)`, atomic `unit_of_work`, and `_hydrate`. The `EdgeType` enum,
`ImpactResult` model, and all three rel tables (`SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM`) already
exist. No new runtime dependency, no schema change, no Cypher beyond an arrow flip.

The work decomposes into four near-orthogonal seams: (1) extend `BackendPort.traverse` and BOTH
backend implementations with `direction` (the only non-trivial change — a reverse-adjacency walk
in memory, an arrow-flip in ladybug); (2) implement `MemoryCore.add_edge` as a one-call
passthrough inside `unit_of_work`; (3) implement `MemoryCore.get_impact` as a `traverse(...,
direction='in')` → `_hydrate` → `ImpactResult` composition; (4) update the `ports.py` docstring
and `docs/backend-contract.md` (BACK-04) for the new parameter and add mechanism property tests
(cycle termination, exact reachable-within-depth set, frontier/truncated at the bound, cross-
backend parity).

The verified-on-contact risk is the ladybug reverse traversal. The live ladybug/Kùzu Cypher docs
confirm `(a)<-[:REL* ACYCLIC 1..N]-(b)` is valid and the EXISTS-subquery direction flips the same
way (`EXISTS { MATCH (b)<-[:rels]-() }`). The `bound==0` fast-path and `_DEPTH_CEILING`/cap-raise
logic are direction-agnostic and carry over verbatim — only the two arrows in the main query and
the one arrow in the `bound==0` out-edge probe flip.

**Primary recommendation:** Extend `traverse` with a keyword-only `direction: str = "out"` on the
port + both backends FIRST (it is the only real change and everything composes on it); then write
`add_edge` (passthrough) and `get_impact` (compose) on `MemoryCore`; then doc + property/parity
tests. Keep the direction logic 100% in the backends — `core.py` stays driver-blind and only ever
passes `direction="in"` from `get_impact`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `add_edge` typed-edge creation | Core (`MemoryCore`) | Backend (`add_edge` primitive) | Core owns the public closed-`EdgeType` seam + `unit_of_work` wrap; the backend owns idempotent edge storage. Already split this way. |
| `get_impact` cascade composition | Core (`MemoryCore`) | Backend (`traverse` primitive) | Core composes `traverse` → `_hydrate` → `ImpactResult` and is driver-blind; the backend owns the cycle-safe bounded walk. D-02 driver-blind discipline. |
| Direction-aware graph walk | Backend (both adapters) | — | D-05: the `direction` change lives in the BACKENDS, not the core. `core.py` passes a literal `"in"`/`"out"` and never knows how each backend flips. |
| Reverse-adjacency indexing | Backend (`InMemoryBackend`) | — | The mirror of `_out_edges`; an internal helper-factoring discretion area. |
| Reverse Cypher var-length walk | Backend (`LadybugBackend`) | — | One arrow flip inside the existing injection-safe interpolation story. |

## Standard Stack

No new packages. This phase ships against the already-installed substrate. The "stack" is the
existing in-repo modules, verified present and current.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.13.x (pin `>=2.11,<3`) | `ImpactResult` / `BeliefState` frozen models hydrated by `get_impact` | Sole required runtime dep; already validated at the seam [VERIFIED: pyproject.toml]. |
| ladybug | 0.17.1 (pin `>=0.17,<0.18`) | Reference-backend reverse var-length Cypher traversal | Installed and pinned; reverse `<-[:r* ACYCLIC 1..N]-` confirmed valid [VERIFIED: docs.ladybugdb.com]. |
| stdlib `uuid` | 3.14 native | `frontier: frozenset[UUID]` ids; no new minting in this phase | Native UUID7; no extra dep [VERIFIED: pyproject.toml requires-python>=3.14]. |

### Supporting (dev/test)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hypothesis | 6.155.x (pin `>=6.155`) | Mechanism property tests (cycle termination, exact reachable set, frontier accuracy) | The cascade mechanism tests; reuse the existing `tests/test_invariants.py` stateful idiom OR plain `@given` for single-operation properties [VERIFIED: pyproject.toml]. |
| pytest | 9.x (pin `>=8`) | Parametrized `backend` fixture (memory + ladybug) | Every parity test reuses the existing `conftest.py` `backend` fixture [VERIFIED: tests/conftest.py]. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `direction` param on `traverse` (D-05) | Reverse the edge-storage convention, OR parameterise `get_impact` directly with raw Cypher | Both rejected in CONTEXT. Reversing storage breaks `_append_state`'s `SUPERSEDES new→prior` and the Phase-6 `get_scope_at` outgoing walk; parameterising `get_impact` with Cypher breaks D-02 driver-blindness. LOCKED — do not re-litigate. |

**Installation:** None. No `npm`/`pip`/`cargo install` step in this phase.

## Package Legitimacy Audit

> Not applicable — Phase 5 installs **no** external packages. All dependencies (pydantic,
> ladybug, hypothesis, pytest) are already pinned in `pyproject.toml` and installed; their
> legitimacy was audited in Phases 1–2 (ladybug 0.17.1 on PyPI verified; `ladybugdb` slopsquat
> token confirmed absent). No new package surface this phase.

## Architecture Patterns

### System Architecture Diagram

```
EDGE-01 write path:
  consumer ──add_edge(from_state_id, to_state_id, EdgeType)──▶ MemoryCore.add_edge
      │  (closed EdgeType enum; no endpoint validation — D-07)
      ▼
  with self._backend.unit_of_work():            ◀── ONE atomic scope (D-06)
      self._backend.add_edge(edge_type, from_id, to_id)
      │  (idempotent MERGE — double-add ⇒ 1 edge; silent no-op on missing endpoint — D-07)
      ▼
  ┌─ InMemoryBackend.add_edge ─┐   ┌─ LadybugBackend.add_edge ─┐
  │ adjacency list append      │   │ MATCH endpoints, MERGE edge│
  └────────────────────────────┘   └────────────────────────────┘

EDGE-02 read path (the cascade — walks AGAINST the arrows, D-04):
  consumer ──get_impact(X_state_id, depth=None)──▶ MemoryCore.get_impact
      │  (driver-blind; passes direction="in")
      ▼
  reached_rows, frontier = self._backend.traverse(
        X, frozenset({DEPENDS_ON, DERIVED_FROM}), depth, direction="in")   ◀── D-03 edge set, D-05 direction
      │
      ▼
  reached = tuple(self._hydrate(r) for r in reached_rows)   ◀── excludes X (D-02)
  ImpactResult(reached=reached,
               frontier=frozenset(frontier),                ◀── boundary ids
               truncated=len(frontier) > 0)                 ◀── D-02 derivation
      │
      ▼
  ┌─ InMemoryBackend.traverse(direction="in") ─┐   ┌─ LadybugBackend.traverse(direction="in") ─┐
  │ reverse-adjacency BFS (mirror _out_edges)  │   │ MATCH (x)<-[:{rels}* ACYCLIC 1..N]-(d)     │
  │ _in_edges(node, edge_types)                │   │ EXISTS { MATCH (b)<-[:rels]-() }           │
  └────────────────────────────────────────────┘   └────────────────────────────────────────────┘
```

File-to-implementation mapping (NOT in the diagram — see this table):

| Capability | File | Symbol(s) touched |
|------------|------|-------------------|
| Port signature + docstring | `src/doxastica/ports.py` | `BackendPort.traverse` — add `direction: str = "out"` kwarg |
| Reverse in-memory walk | `src/doxastica/backends/memory.py` | `traverse` (route on direction), new `_in_edges` / reverse index |
| Reverse ladybug walk | `src/doxastica/backends/ladybug.py` | `traverse` (arrow flip in main query + `bound==0` probe + EXISTS subquery) |
| Public `add_edge` body | `src/doxastica/core.py` | `MemoryCore.add_edge` (currently absent) |
| Public `get_impact` body | `src/doxastica/core.py` | `MemoryCore.get_impact` (currently absent); reuse `_hydrate` |
| Contract doc | `docs/backend-contract.md` | §2 `traverse` bullet — document `direction` |
| Tests | `tests/test_backend_parity.py`, new mechanism test file | reverse-direction parity + property tests |

### Recommended Project Structure
No new files required for source. One new test file is the natural home for the mechanism
property tests (the existing parity file already covers backend-primitive parity):
```
src/doxastica/
├── ports.py          # traverse signature + docstring gain `direction`
├── core.py           # MemoryCore gains add_edge + get_impact bodies
└── backends/
    ├── memory.py     # traverse routes on direction; reverse adjacency
    └── ladybug.py    # traverse arrow-flips on direction
tests/
├── test_backend_parity.py   # ADD reverse-direction parity cases (in-edge graphs)
└── test_cascade.py          # NEW: get_impact mechanism property tests (Hypothesis)
docs/
└── backend-contract.md      # §2 traverse bullet documents direction
```

### Pattern 1: `add_edge` near-passthrough inside one `unit_of_work` (D-06)
**What:** The public `MemoryCore.add_edge(from_state_id, to_state_id, edge_type)` wraps a single
backend `add_edge` call in one atomic scope. No endpoint validation (D-07).
**When to use:** EDGE-01.
**Example:**
```python
# Source: composed from existing MemoryCore.unit_of_work + backend.add_edge (core.py:132-134,
# ports.py:78-86). Signature matches protocol.py:101-108 EXACTLY (do not change it).
def add_edge(
    self,
    from_state_id: UUID,
    to_state_id: UUID,
    edge_type: EdgeType,
) -> None:
    """Add a consumer-facing typed edge between two belief states (EDGE-01, D-06)."""
    with self._backend.unit_of_work():  # exactly one atomic scope (D-06)
        # passthrough — the port's MERGE is idempotent and silently no-ops on a missing
        # endpoint (D-07: mechanism, not policy — the core adds NO endpoint-existence raise).
        self._backend.add_edge(edge_type, str(from_state_id), str(to_state_id))
```
**Note on id stringification:** every existing `core.py` backend call stringifies UUIDs
(`str(state_id)`, see `_append_state` lines 280-283). `add_edge` must do the same so ids match
the stored STRING PKs on the ladybug side. The port signature accepts `UUID | str`, but the
ladybug `MATCH ... {pk: $from}` binds against STRING-typed PK columns — pass `str(...)`.

### Pattern 2: `get_impact` compose-and-hydrate (D-01/D-02/D-03/D-05)
**What:** `get_impact` is a pure composition of `traverse(direction="in")` → `_hydrate` →
`ImpactResult`. No Cypher, no driver import.
**When to use:** EDGE-02.
**Example:**
```python
# Source: composed from backend.traverse (ports.py:96-111) + _hydrate (core.py:229-244) +
# ImpactResult (models.py:117-128). Signature matches protocol.py:131-135 EXACTLY.
_CASCADE_EDGE_TYPES: frozenset[EdgeType] = frozenset(
    {EdgeType.DEPENDS_ON, EdgeType.DERIVED_FROM}  # D-03 — SUPERSEDES EXCLUDED by construction
)

def get_impact(
    self,
    belief_state_id: UUID,
    depth: int | None = None,
) -> ImpactResult:
    """Return the dependency cascade reachable from ``belief_state_id`` (EDGE-02, D-01..D-05)."""
    reached_rows, frontier = self._backend.traverse(
        str(belief_state_id),      # stringify to match stored STRING PKs
        _CASCADE_EDGE_TYPES,       # D-03
        depth,                     # depth=None ⇒ full closure (D-02)
        direction="in",            # D-04/D-05: walk AGAINST the arrows (X's dependents)
    )
    reached = tuple(self._hydrate(self._fetch_props(rid)) for rid in ...)  # see note below
    return ImpactResult(
        reached=reached,                        # excludes start X (D-02)
        frontier=frozenset(frontier),
        truncated=len(frontier) > 0,            # D-02 derivation
    )
```
**CRITICAL HYDRATION GAP — flag for the planner.** The ladybug `traverse` returns
`reached` rows shaped `[{"state_id": ...}]` ONLY — it does **not** return full node props
(ladybug.py:414: `reached = [{"state_id": r["state_id"]} for r in rows]`). The in-memory
`traverse` returns full props (memory.py:140: `dict(self._node_index.get(to_key, {}))`). So the
two backends' `reached` row shapes **differ**, and `_hydrate` needs ALL six `BeliefState` fields.
`get_impact` therefore cannot hydrate directly from `reached` on the ladybug side. Options (planner
must choose ONE):
  - **(A) Re-fetch props in the core (RECOMMENDED, driver-blind, parity-clean):** from the
    `reached` rows take the `state_id`s, then `match_nodes("BeliefState", {"state_id": sid})` per
    id (or a single scan filtered to the id set) and `_hydrate` those. Works identically on both
    backends because `match_nodes` props are already parity-tested. Adds round-trips but stays
    inside the accepted LPG-primitive round-trip budget (ports.py "Named tension").
  - **(B) Make ladybug `traverse` return full props:** change the `RETURN` to project all
    columns. This widens the `traverse` contract beyond the documented `(reached, frontier)`
    "set of nodes" shape and risks breaking the existing parity literals — heavier, NOT
    recommended for this phase.
  Recommendation: **(A)** — it keeps `traverse` unchanged in shape, keeps the core driver-blind,
  and reuses the already-parity-tested `match_nodes`. Confirm `reached` ordering does not matter
  (BACK-04 §5: the core orders results itself; `ImpactResult.reached` is a tuple but the cascade
  set is unordered-by-contract — confirm no test asserts a specific order, or sort by `_order_key`
  for determinism).

### Pattern 3: `direction` on the port `traverse` — backend implementations (D-05)
**What:** A keyword-only `direction: str = "out"` parameter. Default preserves OUTGOING (Phase 6
`get_scope_at` unaffected). `"in"` walks reverse adjacency.

**Port signature (ports.py):**
```python
def traverse(
    self,
    start: UUID | str,
    edge_types: frozenset[EdgeType | str],
    max_depth: int | None,
    direction: str = "out",   # NEW (D-05): "out" (default) follows edges FROM start;
    ...                        # "in" follows edges INTO start (the dependency cascade)
) -> tuple[list[dict[str, Any]], frozenset[UUID | str]]: ...
```
Consider `Literal["in", "out"]` for the type (basedpyright-strict friendly, self-documenting,
and lets the backends `raise ValueError` on anything else for free at the type boundary). The
import of `Literal` is already available via `typing`.

**In-memory (memory.py):** add a reverse-adjacency lookup mirroring `_out_edges`. Two viable
factorings (discretion area, D-05):
```python
# Mirror of _out_edges (memory.py:166-176) — scan adjacency for edges INTO node_key.
def _in_edges(self, node_key: str, edge_types: frozenset[EdgeType | str]) -> list[str]:
    """Predecessor node keys with an edge INTO node_key over any of edge_types."""
    out: list[str] = []
    for edge_type in edge_types:
        adjacency = self._edges.get(str(edge_type), {})
        for src, dsts in adjacency.items():
            if node_key in dsts:
                out.append(src)
    return out
```
Then `traverse` selects the neighbour function by direction:
`neighbours = self._in_edges if direction == "in" else self._out_edges`. The BFS layer/frontier
logic (memory.py:129-144) is otherwise UNCHANGED. Note: `_in_edges` as written is O(edges) per
node; for the small belief graphs in scope this is fine, but the discretion area explicitly allows
maintaining a reverse-adjacency *index* (built in `add_edge`) if the planner prefers symmetry with
`_out_edges`' O(1) lookup. Keep the snapshot/restore in `unit_of_work` covering any reverse index
too (extend `_reindex` if an index is added).

**Ladybug (ladybug.py):** the arrow flips in exactly THREE places; everything else
(`_DEPTH_CEILING`, cap-raise/restore `var_length_extend_max_depth`, `bound==0` fast-path
structure, injection validation, `EXISTS` frontier logic) is direction-agnostic:
```python
# 1. main var-length query (ladybug.py:393-399) — flip both arrows for direction="in":
#    OUT: MATCH p=(a {pk:$start})-[:{rels}* ACYCLIC 1..{bound}]->(b)
#    IN:  MATCH p=(a {pk:$start})<-[:{rels}* ACYCLIC 1..{bound}]-(b)
# 2. EXISTS frontier subquery (ladybug.py:398) — flip its arrow too:
#    OUT: EXISTS { MATCH (b)-[:{rels}]->() }
#    IN:  EXISTS { MATCH (b)<-[:{rels}]-() }
# 3. bound==0 out-edge probe (ladybug.py:375-380) — flip its arrow:
#    OUT: MATCH (a {pk:$start})-[:{rels}]->() RETURN a LIMIT 1
#    IN:  MATCH (a {pk:$start})<-[:{rels}]-() RETURN a LIMIT 1
```
Build the arrow pair from `direction` once (e.g.
`lhs, rhs = ("<-", "-") if direction == "in" else ("-", "->")`) and interpolate — `direction`
is a closed `Literal`, validated, never a `$param`-able position, so it stays inside the
sanctioned-interpolation story (like the namespace). [VERIFIED: docs.ladybugdb.com — reverse
`<-[:REL* ACYCLIC 1..N]-` and incoming EXISTS-subquery arrow both valid Kùzu/ladybug Cypher.]

### Anti-Patterns to Avoid
- **Putting direction logic in `core.py`:** violates D-02 driver-blindness. The core passes a
  literal `"in"`/`"out"`; both backends own the flip. (D-05 explicit.)
- **Validating endpoint existence in `add_edge`:** D-07 forbids it — mechanism, not policy. The
  silent no-op is the *intended* behaviour; pin it with a test, do not "fix" it.
- **Including `SUPERSEDES` in the cascade edge set:** D-03 — `SUPERSEDES` is the internal
  revision-spine edge; following it reports a belief's own version history as "impact."
- **Hydrating `ImpactResult.reached` directly from ladybug `traverse` rows:** they carry only
  `state_id` (Pattern 2 critical gap). Re-fetch via `match_nodes`.
- **Changing the `traverse` return shape to carry full props:** breaks existing parity literals;
  out of scope (Option B rejected).
- **Reusing the OUTGOING default accidentally in `get_impact`:** must pass `direction="in"`
  explicitly, or the cascade walks the wrong way and silently under-reaches (the genuine failure
  mode this surface guards against — D-03 note).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cycle-safe bounded traversal | A new visited-set BFS or recursive walker | The existing `traverse` primitive (both backends) | Already cycle-safe, bounded, `(reached, frontier)`, parity-tested. Phase 5 only adds `direction`. |
| Edge idempotency (double-add ⇒ 1 edge) | A pre-check / dedup pass in the core | Backend `add_edge` MERGE / adjacency-dedup | Both backends already guarantee it (D-06); the core adds nothing. |
| Atomic write grouping | Manual try/commit/rollback | `self._backend.unit_of_work()` | Already the established core pattern (`_append`, `contract`). |
| Raw→model conversion | A new mapper for `ImpactResult` | `_hydrate` (core.py:229) | Reuse the same decode boundary `query_scope`/`get_revision_chain` use — keeps value-codec parity. |
| Truncation signal | A separate "was it cut off" flag computed by walking again | `truncated = len(frontier) > 0` (D-02) | The frontier already carries it; derive, don't recompute. |

**Key insight:** This phase builds almost nothing new — it *composes* and *flips direction*. The
only genuinely new code is the reverse walk in each backend and two short `MemoryCore` method
bodies. Every "hard" property (cycle-safety, idempotency, atomicity, value round-trip) is already
solved and tested upstream.

## Runtime State Inventory

> Greenfield-of-mechanism within an existing codebase — but the D-05 change touches a SHARED
> primitive (`traverse`) consumed by a future phase. Inventory the cross-phase state the change
> could disturb:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no migration. The three rel tables (`SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM`) and `HAS_REVISION` already exist in the ladybug DDL (ladybug.py:205-216); the in-memory backend stores edges in adjacency dicts. `add_edge` writes new edges only; no rewrite of existing nodes/edges (append-only). | None — verified by reading `_bootstrap_schema`. |
| Live service config | None — embedded DB; no external service. | None. |
| OS-registered state | None. | None. |
| Secrets/env vars | None. | None. |
| Build artifacts / shared-primitive contracts | **`traverse` is consumed by Phase 6 `get_scope_at` (not yet written) and the Phase 7 conformance suite (not yet written).** The new `direction` parameter MUST default to `"out"` so the not-yet-written Phase 6 caller (which expects outgoing) compiles unchanged. The existing parity tests call `traverse(start, edge_types, max_depth)` positionally with NO direction arg (test_backend_parity.py:120 etc.) — the default must keep them green. | Make `direction` keyword-only with `"out"` default; verify the existing positional `traverse(...)` call sites still pass (they will, given a default). Re-run the full parity suite after the signature change. |

**Canonical question — after the signature change, what still calls `traverse` the old way?**
The 9 existing parity cases + the backend-level `traverse` tests + (future) Phase 6. All are
satisfied by a defaulted keyword-only `direction="out"`. Confirmed: no existing call site passes a
4th positional arg, so a keyword-only default is non-breaking.

## Common Pitfalls

### Pitfall 1: ladybug `reached` rows carry only `state_id`, in-memory carries full props
**What goes wrong:** `get_impact` hydrates `ImpactResult.reached` directly from `traverse` rows
and passes on ladybug (full-prop rows) in dev but the backends disagree, or `_hydrate` raises
`KeyError` on ladybug because the row lacks `belief_id`/`scope_id`/`value`/`status`.
**Why it happens:** ladybug.py:414 projects only `state_id`; memory.py:140 returns full props.
**How to avoid:** Pattern 2 Option A — re-fetch full props via `match_nodes("BeliefState",
{"state_id": sid})` in the core before `_hydrate`. Add a cross-backend parity test on
`get_impact` output (full `BeliefState` tuples), not just on `traverse`.
**Warning signs:** a `get_impact` test passing on memory and `KeyError`/empty-field on ladybug.

### Pitfall 2: Walking the cascade OUTWARD (wrong direction) silently under-reaches
**What goes wrong:** `get_impact` returns `[]` or only X's *dependencies* instead of its
*dependents*; tests on a single-direction graph may not catch it.
**Why it happens:** forgetting `direction="in"`, or the reverse-adjacency `_in_edges` having a
direction bug (returning successors not predecessors).
**How to avoid:** test on an ASYMMETRIC graph (A→B where B depends on A): `get_impact(A)` must
return `{B}` and `get_impact(B)` must return `{}`. A symmetric graph (cycles only) would pass even
with a direction bug. The entrenchment corollary (CONTEXT specifics: `get_impact(X, depth=1)` ==
in-degree) is a good asymmetric probe.
**Warning signs:** `get_impact(leaf)` non-empty, or `get_impact(root)` empty, on a DAG.

### Pitfall 3: `bound==0` and `direction` interaction
**What goes wrong:** the `bound==0` fast-path (ladybug.py:372-385) probes for an out-edge to
decide if `start` is on the frontier; under `direction="in"` it must probe for an IN-edge instead,
or `max_depth=0` returns the wrong frontier.
**Why it happens:** the `bound==0` branch is a separate code path from the main query; flipping
the main query's arrow but not the `bound==0` probe's arrow leaves a direction-inconsistency.
**How to avoid:** flip ALL THREE arrows (Pattern 3) — main query, EXISTS subquery, AND the
`bound==0` probe. Add a `direction="in", max_depth=0` parity case.
**Warning signs:** `max_depth=0` frontier differs between directions on the same graph.

### Pitfall 4: `var_length_extend_max_depth` global-config restore under reverse walk
**What goes wrong:** the reverse query path forgets the `finally`-restore of the 30-hop cap,
leaking a changed ceiling onto an injected tenant connection (R19/WR-05).
**Why it happens:** copy-pasting the main query without preserving the `try/finally` (ladybug.py:
405-413).
**How to avoid:** the cap-raise/restore is direction-AGNOSTIC — keep it wrapping BOTH the outgoing
and incoming main-query execution identically. Do not duplicate the query into a branch that skips
the `finally`.
**Warning signs:** a deep reverse walk leaves a tenant connection with a non-default hop cap.

### Pitfall 5: `EdgeType` enum vs raw string at the `traverse` validation gate
**What goes wrong:** `get_impact` passes `frozenset({EdgeType.DEPENDS_ON, EdgeType.DERIVED_FROM})`;
the ladybug `traverse` validates each `str(et) in _EDGE_ENDPOINTS` (ladybug.py:364-366). Since
`str(EdgeType.DEPENDS_ON) == "DEPENDS_ON"` and both are in `_EDGE_ENDPOINTS`, this passes — but a
typo or a non-member would `raise ValueError`.
**Why it happens:** the enum→string coercion is implicit; the validation gate is string-keyed.
**How to avoid:** rely on the existing `str(et)` coercion (already correct); the closed
`_CASCADE_EDGE_TYPES` constant guarantees only valid members. No new validation needed.
**Warning signs:** `ValueError: unknown edge type for traverse` from `get_impact`.

## Code Examples

### Cross-backend parity test for `get_impact` (the mechanism contract)
```python
# Source: pattern from tests/test_backend_parity.py (_both_backends, _reached_ids) extended to
# the MemoryCore.get_impact surface. Asymmetric graph catches direction bugs (Pitfall 2).
def test_get_impact_dependents_only_parity() -> None:
    """B depends on A (A<-B): get_impact(A) == {B}; get_impact(B) == {} — on both backends."""
    results: dict[str, tuple[list[str], list[str]]] = {}
    for name, be in _both_backends():
        core = MemoryCore(be)
        a = core.revise("s", "ba", 1, uuid.uuid7())
        b = core.revise("s", "bb", 2, uuid.uuid7())
        core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)  # B --DEPENDS_ON--> A
        impact_a = core.get_impact(a.state_id)
        impact_b = core.get_impact(b.state_id)
        results[name] = (
            sorted(str(s.state_id) for s in impact_a.reached),
            sorted(str(s.state_id) for s in impact_b.reached),
        )
        assert results[name] == ([str(b.state_id)], [])  # A's dependent is B; B has none
    assert results["memory"] == results["ladybug"]
```

### `add_edge` silent-no-op-on-missing-endpoint test (D-07 pin)
```python
# Source: D-07 requires a test pinning this behaviour rather than leaving it incidental.
def test_add_edge_missing_endpoint_is_silent_no_op(backend: BackendPort) -> None:
    """add_edge to a non-existent endpoint creates no edge and raises nothing (D-07)."""
    core = MemoryCore(backend)
    real = core.revise("s", "b", 1, uuid.uuid7())
    ghost = uuid.uuid7()  # never created
    core.add_edge(real.state_id, ghost, EdgeType.DEPENDS_ON)  # must NOT raise
    # the cascade from `real` is empty — no edge was actually laid to a missing node
    assert core.get_impact(ghost).reached == ()
```

### Cycle-termination property test (Hypothesis)
```python
# Source: reuse the existing _build_cycle idiom (test_backend_parity.py:94-100) at the
# get_impact level — proves the mechanism terminates and de-dupes through the core.
@given(depth=st.one_of(st.none(), st.integers(min_value=0, max_value=10)))
def test_get_impact_terminates_on_cycle(depth: int | None) -> None:
    core = MemoryCore.in_memory()
    a = core.revise("s", "a", 1, uuid.uuid7())
    b = core.revise("s", "b", 2, uuid.uuid7())
    # A<-B and B<-A (mutual dependency = cycle through DEPENDS_ON)
    core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)
    core.add_edge(a.state_id, b.state_id, EdgeType.DEPENDS_ON)
    result = core.get_impact(a.state_id, depth)  # must terminate
    assert a.state_id not in {s.state_id for s in result.reached}  # excludes start (D-02)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `traverse(start, edge_types, max_depth)` — outgoing only | `traverse(..., direction="out"\|"in")` — direction-aware | Phase 5 (this) | `get_impact` becomes expressible; Phase 6 `get_scope_at` unaffected by the default. |
| `depth=5` sketch default for `get_impact` | `depth=None` ⇒ full closure (DATA-04, D-02) | Phase 1, ratified | The magic `5` is retired; bounded walks report frontier/truncated. |

**Deprecated/outdated:** none for this phase. No library version changes; the ladybug pin
(`>=0.17,<0.18`) and pydantic pin (`>=2.11,<3`) are unchanged and current.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Re-fetching props via `match_nodes` per reached `state_id` (Pattern 2 Option A) stays within the accepted LPG-primitive round-trip budget for realistic belief-graph sizes | Pattern 2, Don't Hand-Roll | If impact sets are huge, N+1 `match_nodes` is slow; mitigated by a single scope-wide scan filtered to the id set. Mechanism-correct regardless; only a perf concern. |
| A2 | `ImpactResult.reached` order is not contractually significant (cascade is a set); sorting by `_order_key` or leaving traverse order is both acceptable | Pattern 2, Pitfall 1 | If a downstream test asserts a specific `reached` order, need a deterministic sort. Low risk — BACK-04 §5 says the core orders results itself; recommend sorting by `_order_key` for determinism. |
| A3 | `Literal["in", "out"]` typing is basedpyright-strict clean and the existing `typing` import covers it | Pattern 3 | Trivial to verify on contact; if `Literal` needs importing it is a one-line add. |

**Note:** No `[ASSUMED]` package or compliance claims — all tech facts here are VERIFIED against
the codebase or live ladybug docs. The three assumptions above are design-judgement calls the
planner/discuss can confirm cheaply, not unverified external facts.

## Open Questions (RESOLVED)

1. **Hydration source for `ImpactResult.reached` (Pattern 2 gap).** RESOLVED: Option A (re-fetch
   via `match_nodes`) — adopted by Plan 05-03 Task 2.
   - What we know: ladybug `traverse` returns `state_id`-only rows; in-memory returns full props;
     `_hydrate` needs all six fields.
   - Resolution: Option A — driver-blind, parity-clean, reuses tested `match_nodes`. (Option B,
     widening `traverse`'s return, rejected.)

2. **Reverse-adjacency: scan vs index in the in-memory backend (discretion area).** RESOLVED: scan
   — adopted by Plan 05-01 Task 3.
   - What we know: D-05 leaves this to Claude's discretion; `_in_edges` as a scan is O(edges).
   - Resolution: start with the scan (simplest, correct, fine for in-scope graph sizes); add an
     index only if a perf test demands it. Either is acceptable per D-05.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pydantic | `ImpactResult`/`BeliefState` hydration | ✓ | 2.13.x (pin `>=2.11,<3`) | — |
| ladybug | reference-backend reverse traversal | ✓ | 0.17.1 (pin `>=0.17,<0.18`) | in-memory backend (the parametrized fixture skips ladybug if absent) |
| hypothesis | mechanism property tests | ✓ | 6.155.x | — |
| pytest | parametrized `backend` fixture | ✓ | 9.x | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** ladybug — if absent, `conftest.py` `importorskip` skips
the ladybug param and the in-memory backend still exercises the full mechanism (existing pattern).

## Validation Architecture

> nyquist_validation: not disabled in config — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + hypothesis 6.155.x |
| Config file | `pyproject.toml` (`[tool.pytest...]`); shared fixtures in `tests/conftest.py` |
| Quick run command | `uv run pytest tests/test_cascade.py -x -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EDGE-01 | `add_edge` lays a typed edge, idempotent, closed `EdgeType` | unit + parity | `uv run pytest tests/test_cascade.py -k add_edge -x` | ❌ Wave 0 (new `test_cascade.py`) |
| EDGE-01 | `add_edge` silent no-op on missing endpoint (D-07 pin) | unit + parity | `uv run pytest tests/test_cascade.py -k missing_endpoint -x` | ❌ Wave 0 |
| EDGE-02 | `get_impact` returns dependents only (asymmetric, Pitfall 2) | parity | `uv run pytest tests/test_cascade.py -k dependents_only -x` | ❌ Wave 0 |
| EDGE-02 | `get_impact` terminates + de-dupes on cycles | property (Hypothesis) | `uv run pytest tests/test_cascade.py -k terminates_on_cycle -x` | ❌ Wave 0 |
| EDGE-02 | `get_impact` exact reachable-within-depth set | property | `uv run pytest tests/test_cascade.py -k reachable_within_depth -x` | ❌ Wave 0 |
| EDGE-02 | `get_impact` frontier/truncated at the bound (incl. depth=0) | parity | `uv run pytest tests/test_cascade.py -k frontier -x` | ❌ Wave 0 |
| D-05 | reverse `traverse(direction="in")` parity (both backends) | parity | `uv run pytest tests/test_backend_parity.py -k direction -x` | ❌ Wave 0 (extend existing file) |
| D-05 | default `traverse` (no direction arg) unchanged — outgoing parity green | regression | `uv run pytest tests/test_backend_parity.py -q` | ✅ exists (must stay green) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_cascade.py tests/test_backend_parity.py -x -q`
- **Per wave merge:** `uv run pytest -q` (full suite — proves Phase 6 `traverse` callers + all
  prior phases unbroken by the signature change)
- **Phase gate:** full suite green + basedpyright strict clean + ruff clean before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cascade.py` — `MemoryCore.add_edge` + `get_impact` mechanism tests (covers
      EDGE-01, EDGE-02, D-07 pin) — NEW file
- [ ] `tests/test_backend_parity.py` — ADD reverse-direction (`direction="in"`) parity cases
      including `max_depth=0` (Pitfall 3) — extend existing file
- [ ] No new framework install — hypothesis/pytest already present
- [ ] basedpyright check on the `Literal["in","out"]` direction type (A3)

## Security Domain

> `security_enforcement` not disabled in config — section included. This phase touches the one
> injection-relevant surface in the codebase (interpolated Cypher in `traverse`), so it is
> genuinely in scope.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | embedded library, no auth surface |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | The `direction` value MUST be a closed `Literal["in","out"]`, validated before it reaches interpolated Cypher (same discipline as the namespace + `edge_types` + depth). `edge_types` already validated against `_EDGE_ENDPOINTS`; depth already a runtime-guarded int. |
| V6 Cryptography | no | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via the new `direction`-driven interpolated arrow | Tampering | `direction` is a closed `Literal`, never caller-free-text and never a `$param` position; derive the arrow pair from it (`"<-"/"-"` vs `"-"/"->"`) — it is a fixed internal token like the namespace, inside the one sanctioned-interpolation story (ladybug.py D-04). No untrusted value reaches the Cypher text; `$start` stays `$param`-bound. |
| Reverse query leaking a changed `var_length_extend_max_depth` onto an injected tenant connection | Tampering (state leak, R19) | Keep the direction-agnostic `try/finally` cap-restore wrapping BOTH directions (Pitfall 4). |
| `add_edge` writing to an unintended endpoint | — (not a security issue) | D-07 silent no-op is intended mechanism, not a vulnerability — the edge simply isn't laid; pinned by test. |

## Sources

### Primary (HIGH confidence)
- Codebase (read this session): `src/doxastica/{ports,protocol,models,core}.py`,
  `src/doxastica/backends/{memory,ladybug}.py`, `tests/{conftest,test_backend_parity}.py`,
  `docs/backend-contract.md`, `pyproject.toml` — the substrate `add_edge`/`traverse`/`_hydrate`/
  `unit_of_work`/`EdgeType`/`ImpactResult` all verified present.
- docs.ladybugdb.com — Cypher MATCH: reverse var-length `(a)<-[:REL* ACYCLIC 1..N]-(b)` and the
  default-30-hop cap confirmed valid.
- docs.kuzudb.com / docs.ladybugdb.com — Cypher subquery: incoming-edge EXISTS subquery direction
  (`EXISTS { MATCH (b)<-[:rels]-() }`) confirmed.
- `pyproject.toml` + `uv pip show ladybug` — ladybug 0.17.1 installed; pins `>=0.17,<0.18`,
  pydantic `>=2.11,<3`, hypothesis `>=6.155`, requires-python `>=3.14`.

### Secondary (MEDIUM confidence)
- CONTEXT.md D-01..D-07 (the locked decisions this research implements, not re-litigates).

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all verified installed/pinned.
- Architecture: HIGH — composed directly from read source; the one new capability (direction) has
  its Cypher syntax verified against live docs.
- Pitfalls: HIGH — Pitfalls 1, 3, 4 are derived from specific lines in `ladybug.py`/`memory.py`;
  Pitfall 2 is the CONTEXT-flagged under-reach failure mode.

**Research date:** 2026-06-18
**Valid until:** 2026-07-18 (stable — embedded library, pinned deps, no fast-moving surface)
