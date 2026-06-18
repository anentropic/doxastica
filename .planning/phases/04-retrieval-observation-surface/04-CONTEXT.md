# Phase 4: Retrieval & Observation Surface - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the **read/observation surface the entire AGM postulate suite (Phase 7)
observes the belief base *through*** — `query_scope(scope, belief_filter, include_retracted)`
implemented against the Phase-1 `BackendPort`, plus the **retracted-vs-superseded query
matrix** (CHAIN-04). It runs identically on both backends (in-memory + ladybug) from the
start, composing the derived-current spine laid in Phase 3.

**Requirements in scope:** CHAIN-04, HIST-01.

**In scope:**
- `query_scope` body on `MemoryCore`: derive the current tail per `(scope, belief)`, apply the
  closed `BeliefFilter`, return a deterministically-ordered `list[BeliefState]`.
- A "current-tail-regardless-of-status" helper (a sibling to `_current`, which nulls a
  retracted tail) so `include_retracted=True` can surface contracted beliefs.
- The retracted-vs-superseded four-cell matrix as a structural/query distinction, tested on
  both backends.
- The `include_deprecated` → `include_retracted` public-flag rename (recorded reversal — D-03).

**Out of scope (later phases):**
- `get_scope_at` as-of reconstruction / event-window time-travel (Phase 6, HIST-03). Phase 4's
  event-range filter is a pure post-filter, NOT an as-of cut.
- `add_edge` consumer edges + `get_impact` cascade (Phase 5, EDGE-01/02).
- The assembled AGM/Hansson backend conformance suite + irony join (Phase 7).
- `get_revision_chain` (already shipped — HIST-02, Phase 3); Phase 4 only *reads through* it
  to observe the superseded cells.

</domain>

<decisions>
## Implementation Decisions

### Return granularity (HIST-01)
- **D-01 — `query_scope` returns exactly ONE current state per `(scope, belief)`.** For each
  belief in the scope it returns the single derived-current tail (composing the Phase-3
  ordering-max selection), never the full history. `query_scope` *is* the AGM belief base B —
  "what does this scope hold now." SC3 ("no duplicate beliefs") is therefore a **postcondition
  that falls out of the model**, not dedup logic to write.
- **D-02 — `include_retracted` surfaces retracted-current beliefs, never superseded history.**
  - Default (`include_retracted=False`): return beliefs whose current tail is `status=active`
    (equivalent to the existing `_current`, which nulls a retracted tail).
  - `include_retracted=True`: ALSO return beliefs whose current tail is `status=retracted`.
  - Still exactly one state per belief in both modes. Superseded (non-current) states are
    **never** returned by `query_scope`.
  - Implementation note: `_current()` returns `None` on a retracted tail (D-05, Phase 3), so
    `query_scope` cannot reuse it directly for the retracted case — it needs a
    **current-tail-regardless-of-status** helper (the raw ordering-max tail) and then filters
    by the resolved status set.

### Naming rationalisation (Phase-1-surface reversal)
- **D-03 — Rename the public flag `include_deprecated` → `include_retracted`** (Option A).
  Recorded as a **deliberate Phase-1-surface reversal**, in the same family as the Phase-1
  3.14-floor raise, the Phase-2 D-03 dep reversal, and the Phase-3 D-01 derived-current
  mechanism-deviation. NVM has not shipped against the flag (M0 still in progress), so the
  blast radius is the flag name + the CHAIN-04 / HIST-01 requirement wording only.
  - **Why:** there were three words for two concepts. The genuine smell was **deprecated vs
    retracted** — the *same* concept under two names straddling the seam: the stored
    `Status` value is `retracted` (AGM "re**tract**ion", matching `contract`), while the flag
    and the SC2 matrix said "deprecated". Standardise on **`retracted`** everywhere.
  - **`Status` stays `{active, retracted}`** (DATA-06 frozen taxonomy unchanged — Option B,
    renaming the status value to `deprecated`, was rejected as a larger blast radius that also
    abandons the AGM term).
  - The public matrix is now the clean two-axis pair **retracted vs superseded**.
  - **Status-filter precedence is unchanged** (already locked in `protocol.py`): an explicit
    `belief_filter.status` governs; `include_retracted` is sugar — `False` ≡ `{active}`,
    `True` ≡ `{active, retracted}`.
  - Touch points: `src/doxastica/protocol.py` (signature + docstring), and the CHAIN-04 /
    HIST-01 text in `.planning/REQUIREMENTS.md` + the Phase-4 line in `.planning/ROADMAP.md`.

### The retracted/superseded matrix (CHAIN-04, SC2)
- **D-04 — Two orthogonal axes, observed by two different read methods:**
  - **Status axis** (`active` / `retracted`) — per-state stored field; what `contract()`
    stamps. The query-facing "retracted" = a withdrawn belief.
  - **Currency axis** (`current` / `superseded`) — per-state structural; `superseded` = a state
    displaced by a newer revision (has an incoming `SUPERSEDES` edge / is not the ordering-max
    tail). Still true *history*, just not the tail.
  - The four cells: `current+active` (live), `current+retracted` (contracted/withdrawn),
    `superseded+active` (overwritten value), `superseded+retracted` (a retraction state itself
    later superseded).
- **D-05 — `query_scope` observes the *current* row; `get_revision_chain` + `SUPERSEDES`
  observe the *superseded* cells.** `query_scope` only ever returns current tails
  (`current+active` by default, `+current+retracted` with `include_retracted=True`). The two
  superseded cells are reached via `get_revision_chain` (full chain, HIST-02) plus the
  `SUPERSEDES` edges laid in Phase 3 — never via `query_scope`. The matrix test combines both
  read methods to assert all four cells are distinguishable. (Grounding: `17-kumiho §2`,
  paper §8.6 "superseded ≠ deprecated".)

### Filter field semantics (DATA-02 closed filter)
- **D-06 — `event_id_min` / `event_id_max` POST-FILTER the current tails; no as-of
  reconstruction.** Derive the current tail per belief first (unchanged), THEN drop tails whose
  `source_event_id` falls outside `[min, max]`. The range filters *which current beliefs you
  see*; it never changes *which state is current*. A belief whose current tail is newer than
  `event_id_max` is simply **absent** — NOT rewound to an older value. As-of/window
  reconstruction is `get_scope_at` (HIST-03), explicitly Phase 6.
- `belief_ids` narrows the belief set (obvious pre-filter); `status` filters the current tail's
  status with the precedence in D-03.

### Ordering & edge cases
- **D-07 — Deterministic order, sorted by the existing `_order_key` `(source_event_id,
  state_id)`.** Semantically the result is a *set* (a belief base), but a deterministic order
  makes cross-backend parity assertions and Hypothesis shrinking clean (in-memory and ladybug
  return identical sequences). Document: callers must not ascribe meaning to order. Reuse the
  single `_order_key` contract already centralized in `core.py` — do not introduce a second
  ordering.
- **D-08 — Non-existent or empty scope returns `[]`.** `query_scope` is a **pure read** — it
  never auto-creates (unlike the write ops' get-or-create, Phase-3 D-06). An empty belief base
  is a valid AGM state, and the postulate tests routinely query scopes that may hold nothing.
  No existence probe, no new error type.

### Claude's Discretion
- Exact shape/name of the current-tail-regardless-of-status helper, and whether it factors out
  shared code with `_current` (constraint: ONE ordering contract via `_order_key`; `_current`'s
  retracted-tail→`None` behaviour must remain intact for the write ops).
- Whether `query_scope` derives per-belief current via N `_current`-style lookups or a single
  scope-wide scan + group-by-belief + per-group max — a backend-efficiency call for
  research/planning (the in-memory adapter and the ladybug Cypher may differ in approach as
  long as parity holds).
- How the four-cell matrix test is constructed (the operation sequence producing each cell) —
  a test-design call, constrained by "runs on both backends via the parametrized conftest."

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The formal spec (sibling `narrative-vm` repo; read-only design inputs)
- `../narrative-vm/_design/v1/kumiho Graph-Native Cognitive Memory for AI Agents.pdf` —
  the paper (arXiv 2603.17244). **§8.6 "superseded ≠ deprecated"** grounds the two-axis matrix
  (D-04/D-05); abstract = "simple propositional logic over ground triples" (no value-semantic
  inference in the read surface either).
- `../narrative-vm/_design/v2/17-kumiho-nvm-recommendations.md` — **§2 superseded ≠ deprecated**
  (the query-matrix distinction CHAIN-04 implements). NOTE: §6's multi-actor sketch is
  SUPERSEDED by `05 §6` on the scope model — read with that precedence.
- `../narrative-vm/_design/v2/05-nvm-memory-core.md` — PRIMARY spec. §6 scopes (independent
  peers; world scope); §8 structural invariants (the consistency check `query_scope`-current ≡
  chain tail that Phase 3 reframed and Phase 4's surface must keep satisfying).
- `../narrative-vm/_design/v2/01-nvm-glossary.md` — §AGM/Hansson: contraction = retraction (the
  term that anchors the `retracted` status and the D-03 rename), recovery excluded.
- `../narrative-vm/_design/v2/15-nvm-milestones.md` — M0 exit gate; the irony join (Phase 7)
  that reads divergence through `query_scope`.

### This repo — the seams Phase 4 composes
- `src/doxastica/protocol.py` — the locked `BeliefStore.query_scope` signature + docstring;
  **the `include_deprecated` → `include_retracted` rename (D-03) lands here.**
- `src/doxastica/models.py` — frozen `BeliefFilter` (4 closed fields: `belief_ids`,
  `status: frozenset[Status]`, `event_id_min`, `event_id_max`), `Status = {active, retracted}`
  (UNCHANGED by D-03), `BeliefState`.
- `src/doxastica/core.py` — `MemoryCore`: `_order_key` (the ONE ordering contract, reuse for
  D-07), `_current` (ordering-max tail; nulls a retracted tail — the reason D-02 needs a
  status-agnostic helper), `get_revision_chain` (HIST-02; the superseded-cell observation path,
  D-05). **`query_scope` body lands here.**
- `src/doxastica/ports.py` — `BackendPort`: `match_nodes` / `traverse` are the primitives
  `query_scope` composes (no new port primitive needed).
- `src/doxastica/backends/memory.py` / `backends/ladybug.py` — the two adapters; `query_scope`
  stays driver-blind in `core.py` and reads through these via the port.
- `.planning/phases/03-append-only-revision-spine-keystone/03-CONTEXT.md` — D-01 (derived
  current), D-04 (revise≡expand), D-05 (contract appends a retracted tail), D-07 (structural
  edges incl. `SUPERSEDES` laid on every displacement — the edges Phase 4's matrix reads).
- `.planning/phases/01-…/01-CONTEXT.md`, `.planning/phases/02-…/02-CONTEXT.md` — locked upstream
  decisions (LPG-primitive port, closed taxonomy/filter, parametrized two-backend conftest,
  adapters return raw `list[dict]` and `MemoryCore` hydrates frozen models).
- `.planning/research/PITFALLS.md`, `.planning/research/ARCHITECTURE.md` — GSD research layer.
  **Caveat:** both model a stored `CURRENT_STATE` edge — SUPERSEDED by D-01 (derived current);
  read their query Cypher as the *rejected* pointer-form alternative.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_order_key(state)`** in `core.py` — the single `(source_event_id, state_id)` ordering
  contract. D-07 reuses it verbatim for the result sort; introducing a second ordering would
  desynchronise the surface from the spine.
- **`_current(scope_id, belief_id)`** — the derived ordering-max tail, already correct for the
  default (active) case. D-02 needs a status-agnostic sibling for the `include_retracted=True`
  case (since `_current` nulls a retracted tail by design).
- **`get_revision_chain(belief_id)`** (HIST-02, shipped) — the superseded-cell observation path
  (D-05); Phase 4 reads through it in the matrix test, does not modify it.
- **`SUPERSEDES` edges** — laid by the core on every displacement in Phase 3 (D-07); the
  structural signal for the superseded axis (D-04).
- **Parametrized two-backend `conftest`** — runs every test over in-memory + ladybug; the home
  of the four-cell matrix test and the deterministic-order parity assertions.

### Established Patterns
- **Adapters return raw `list[dict]`; `MemoryCore` hydrates frozen pydantic `BeliefState`**
  (Phase 2 D-04). `query_scope` follows this: compose `match_nodes`/`traverse` below, hydrate +
  sort + filter above the port.
- **Driver-blind core** (Phase 2 D-02) — `query_scope` logic lives in `core.py` against the
  port; no driver import.
- **Closed typed filter, never interpolated `str`** (DATA-02) — `query_scope` consumes only the
  4 `BeliefFilter` fields; no triple-structure or free-query leak.

### Integration Points
- Phase 4 composes the Phase-3 spine (no new write semantics, no new port primitive).
- The deterministic order (D-07) and empty-list contract (D-08) are what the Phase-7
  conformance suite and irony join rely on when observing the belief base.

</code_context>

<specifics>
## Specific Ideas

- The public flag is specifically `include_retracted` (not `include_deprecated`), and the
  matrix vocabulary is specifically **retracted vs superseded** — the user's call (D-03).
- `query_scope` is the AGM belief base B observed "as of now" — the postulate tests read the
  base *through* it; this is the framing that fixes return granularity (D-01) and empty-scope
  behaviour (D-08).

</specifics>

<deferred>
## Deferred Ideas

- **`get_scope_at` as-of reconstruction** (HIST-03, Phase 6) — the event-window/time-travel cut
  that D-06 deliberately keeps OUT of the Phase-4 event-range filter.
- **`add_edge` consumer edges + `get_impact` cascade** (EDGE-01/02, Phase 5) — Phase 4 reads the
  Phase-3 structural `SUPERSEDES` edges but adds no consumer edges.
- **Materialize a stored current pointer** ONLY if `query_scope` profiling later demands it
  (Phase-3 D-01 deferred item) — addable without changing the public surface; not now.
- **An `is_current` / currency flag on returned states** — not needed, since `query_scope`
  returns only current tails by construction (D-01); revisit only if a future surface must
  return mixed-currency results.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.

</deferred>

---

*Phase: 4-retrieval-observation-surface*
*Context gathered: 2026-06-18*
