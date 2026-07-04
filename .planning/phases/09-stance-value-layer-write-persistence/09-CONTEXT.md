# Phase 9: Stance Value Layer, Write & Persistence - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning
**Source:** /gsd-discuss-phase 9 --assumptions (assumptions pass + two locked follow-up decisions)

<domain>
## Phase Boundary

The core *stores and compares* stance. A canonical ordinal `Stance` enum lands, is added to
the frozen `BeliefState`, is accepted (optional, defaulting to `certain`) on the write surface
(`revise`/`expand`), is preserved verbatim by `contract`, reconstructed by `get_scope_at`, and
round-trips **byte-stable on both backends** (in-memory + ladybug) — with ordinal comparison the
only reachable operation over the type.

Requirements in scope: **STANCE-01 … STANCE-06**.

Out of scope (Phase 10): STANCE-07 (the Hypothesis oracle widening / K*6 Extensionality carrying
stance), DOCS-01 (Cluedo tutorial), and all stance *policy* (assignment, propagation, contradiction
resolution) — permanently NVM-layer work.

</domain>

<decisions>
## Implementation Decisions

Most of Phase 9 is already locked by REQUIREMENTS.md STANCE-01…06 (read them — they are the
authority). The two decisions below were resolved in the assumptions discussion and are NOT
otherwise written down; they resolve the two genuine ambiguities the requirements leave open.

### D-01: `stance` is a REQUIRED field on `BeliefState` (no model-level default)
- `BeliefState` gains `stance: Stance` as a **required** field (6 → 7 fields). It does **not**
  carry a model-level default of `certain`.
- Rationale: the *API methods* provide the default (`revise`/`expand` default `stance` to
  `Stance.certain` per STANCE-03), and `_hydrate` always supplies it on read, so every
  construction path already sets it. Keeping the model field required keeps the closed taxonomy
  honest — nothing constructs a `BeliefState` with an implicit stance.
- Consequence: any test helper / call site that hand-builds a `BeliefState` must now pass
  `stance=...` explicitly. This is intended (a forcing function), not incidental breakage.

### D-02: `_append_state` takes stance as an ALREADY-SERIALIZED string token (Option A)
- The shared `_append_state` helper receives `stance` as a **pre-serialized string token**
  (the member `.name`, e.g. `"certain"`), exactly mirroring how it already receives `value` as a
  pre-encoded token. The helper never interprets stance.
- Call sites:
  - `_append` (revise/expand): passes `stance.name` (serialize at the write boundary).
  - `contract`: passes `prior["stance"]` **verbatim** — the stored token copied straight through,
    no decode/re-encode. This makes STANCE-04's verbatim-preservation *structural*, the exact
    sibling of the existing verbatim-`value` copy (Pitfall 2), rather than an incidental identity
    round-trip.
- Rejected alternative (Option B): pass the `Stance` enum into `_append_state` and serialize
  inside it. Rejected because `contract` holds only `prior` (a raw props dict with a stored string
  token) — Option B would force `Stance[prior["stance"]]` then immediately `.name` it back, a
  pointless decode/encode cycle that weakens the verbatim guarantee.

### Serialization / hydration discipline (locked by STANCE-01/03, restated to prevent the trap)
- **Serialize via `.name`** (`"certain"` — legible token, base64/STRING-column safe), **NOT**
  `.value` (which is the integer rank, used only inside `__lt__`).
- **Hydrate via `Stance[props["stance"]]`** (name-based lookup) in `_hydrate`, **NOT**
  `Stance(props["stance"])` (value-based lookup would `KeyError` on the token). This is the single
  most likely bug in the phase.

### `Stance` enum shape (locked by STANCE-01/06, restated)
- Plain `Enum` + `functools.total_ordering` + explicit integer rank; `__lt__` compares `.value`
  and returns `NotImplemented` for non-`Stance` operands. `IntEnum` and `StrEnum` are **rejected**
  (both would make `+`/`*`/cross-type `<` reachable, contradicting STANCE-06). First *ordered*
  enum in the codebase — `Status`/`EdgeType` stay unordered `StrEnum`s. Lives in `models.py`.

### Claude's Discretion
- Exact placement of the `Stance` enum within `models.py` and import wiring.
- Test structure for the byte-stable round-trip (SC4) and the type-level `TypeError` assertions
  (SC-STANCE-06) — a targeted test in Phase 9; the full oracle/property widening is Phase 10.
- Whether `_hydrate` reconstructs stance inline or via a small helper (behavior is fixed; shape
  is discretion).

</decisions>

<specifics>
## Specific Ideas

- `get_scope_at` and `query_scope` both route through `_hydrate` — once `_hydrate` reconstructs
  stance, SC5 (`get_scope_at` reconstruction) needs **no dedicated code**, only a test.
- The ladybug `BeliefState` NODE TABLE DDL must gain a `stance STRING` column next to
  `value STRING, status STRING`. The DDL is `CREATE ... IF NOT EXISTS`, so a *pre-existing* on-disk
  table will NOT gain the column — acceptable for a clean v0.2.0 (fresh `:memory:` test DBs and new
  installs); there is no ALTER/migration path in scope. Flag if planning surfaces a real upgrade need.
- The in-memory backend stores props as-is, so it carries `stance` without schema changes; the
  work there is confirming byte-stable parity with ladybug.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — STANCE-01 … STANCE-07 (the authority; STANCE-07 is Phase 10),
  DOCS-01 (Phase 10), and the "Out of Scope" stance-policy fence.
- `.planning/ROADMAP.md` §"Phase 9: Stance Value Layer, Write & Persistence" — goal + 5 success
  criteria.

### Code the phase touches (verified present, v0.1.0 shipped)
- `src/doxastica/models.py` — `BeliefState` (frozen, `extra="forbid"`, current 6 fields);
  `Status`/`EdgeType` `StrEnum` house style; add `Stance` here.
- `src/doxastica/core.py` — write spine: `_append` / `_append_state` (the shared node+edge body,
  value passed pre-encoded), `_hydrate`, `revise`, `expand`, `contract` (verbatim-value copy at
  the `prior["value"]` line), `get_scope_at` (reconstructs via `_hydrate`), `_encode_value`.
- `src/doxastica/protocol.py` — `revise` / `expand` Protocol signatures (must gain the optional
  `stance` param alongside `core.py`).
- `src/doxastica/backends/ladybug.py` — `BeliefState` NODE TABLE DDL (`value STRING, status STRING`
  → add `stance STRING`); props flow through `upsert_node` dynamically.
- `src/doxastica/backends/memory.py` — schemaless prop store; parity target for byte-stability.

### Project constraints
- `CLAUDE.md` — append-only discipline, `.name`-token house style, pydantic-v2 frozen models,
  strict basedpyright, full-`prek` verification gate.

</canonical_refs>

<deferred>
## Deferred Ideas

- STANCE-07: Hypothesis oracle widening — shadow oracle tracks `stance` per entry, state-equality
  key widens `{belief_id: value}` → `{belief_id: (value, stance)}`, K*6 Extensionality `revise ≡
  expand` parity compares stance. **Phase 10.**
- DOCS-01: Cluedo tutorial demonstrating the within-scope epistemic gradient + a reader-side
  ordinal comparison; refreshed `revise`/`expand` signature references; `mkdocs build --strict`.
  **Phase 10.**
- Stance *policy* (assignment, weakest-link propagation, contradiction resolution, trust/dice) —
  NVM-layer, permanently out of this library.

</deferred>

---

*Phase: 09-stance-value-layer-write-persistence*
*Context gathered: 2026-07-04 via /gsd-discuss-phase 9 --assumptions*
