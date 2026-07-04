# Phase 4: Retrieval & Observation Surface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** 4-retrieval-observation-surface
**Areas discussed:** Return granularity, Retracted/superseded matrix, Filter field semantics, Ordering & edge cases

---

## Return granularity

| Option | Description | Selected |
|--------|-------------|----------|
| One current state per belief | For each belief, return its single derived-current tail (compose `_current`); SC3 dedup is a free postcondition; `query_scope` = the AGM belief base B | ✓ |
| All states matching filter | Return every matching `BeliefState` incl. superseded; needs explicit dedup; stops being a clean belief-base surface | |
| You decide | Defer to research/planning | |

**User's choice:** One current state per belief
**Notes:** Establishes `query_scope` as the "what does this scope hold now" surface the postulate tests read through.

### Follow-up: what does `include_*` add?

| Option | Description | Selected |
|--------|-------------|----------|
| Beliefs whose current tail is retracted | Default = active tails; flag=True also returns retracted-current tails; still one per belief; needs a status-agnostic tail helper | ✓ (implied) |
| Also surface superseded history | Breaks one-per-belief + reintroduces duplicates | |
| You decide | Defer | |

**User's choice:** "Other" — *"can we rationalise the naming? the distinction between deprecated vs retracted is confusing"* → led to the naming decision below; the recommended retracted-tail semantics were retained.

### Naming rationalisation (raised by user)

| Option | Description | Selected |
|--------|-------------|----------|
| A — standardize on `retracted` | Rename flag `include_deprecated` → `include_retracted`; `Status` stays `{active, retracted}`; matrix = retracted vs superseded; recorded Phase-1-surface reversal (small blast radius) | ✓ |
| B — standardize on `deprecated` | Rename `Status` value `retracted` → `deprecated`; touches frozen DATA-06 enum + Phase-3 code; abandons AGM "retraction" term | |
| Keep `include_deprecated` as-is | Document the belief-vs-state level distinction; subtlety persists | |

**User's choice:** Option A
**Notes:** The genuine smell was deprecated-vs-retracted (same concept, two names across the seam) — NOT deprecated-vs-superseded (genuinely distinct axes). Standardising on `retracted` keeps the term that pairs with `contract`.

---

## Retracted/superseded matrix

| Option | Description | Selected |
|--------|-------------|----------|
| query_scope = current row; chain = superseded | `query_scope` returns only current tails; the two superseded cells observed via `get_revision_chain` + `SUPERSEDES`; needs a status-agnostic tail helper | ✓ |
| query_scope exposes all four cells | Contradicts one-current-per-belief + SC3 dedup | |
| You decide | Defer the split to planning | |

**User's choice:** query_scope = current row; chain = superseded
**Notes:** SC2's four cells are distinguishable by combining the two read methods. Two orthogonal axes: status (active/retracted) × currency (current/superseded).

---

## Filter field semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Post-filter the current tails | Derive current tail first, then drop tails whose `source_event_id` is outside [min,max]; filters which beliefs you see, never which state is current; no time-travel | ✓ |
| As-of window reconstruction | Treat `event_id_max` as an "as of E" cut — this IS `get_scope_at` (Phase 6); rejected here | |
| You decide | Defer, constrained by "no as-of in Phase 4" | |

**User's choice:** Post-filter the current tails
**Notes:** Keeps as-of/time-travel cleanly in Phase 6 (HIST-03).

---

## Ordering & edge cases

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic sort by ordering key | Sort by the existing `_order_key` `(source_event_id, state_id)`; clean cross-backend parity + Hypothesis shrinking; order semantically meaningless | ✓ |
| Unordered / backend-defined | Forces sort/setify before parity comparison; non-reproducible counterexamples | |
| You decide | Defer, constrained by "parity must be deterministic" | |

**User's choice:** Deterministic sort by ordering key

| Option | Description | Selected |
|--------|-------------|----------|
| Return empty list | Non-existent/empty scope → `[]`; pure read, never auto-creates; empty belief base is valid AGM | ✓ |
| Raise on non-existent scope | Adds existence probe + error type; complicates the oracle; no real safety | |
| You decide | Defer, constrained by "pure read, never auto-creates" | |

**User's choice:** Return empty list

---

## Claude's Discretion

- Exact shape/name of the current-tail-regardless-of-status helper, and whether it shares code
  with `_current` (constraint: ONE `_order_key` ordering; `_current`'s retracted→`None`
  behaviour must remain intact).
- Whether per-belief current is derived via N lookups or a single scope-wide scan + group-by +
  per-group max — a backend-efficiency call (in-memory and ladybug may differ as long as parity
  holds).
- How the four-cell matrix test is constructed (the operation sequence producing each cell) —
  test-design call, constrained by "runs on both backends via the parametrized conftest."

## Deferred Ideas

- `get_scope_at` as-of reconstruction (HIST-03, Phase 6).
- `add_edge` consumer edges + `get_impact` cascade (EDGE-01/02, Phase 5).
- Materialize a stored current pointer only if profiling demands (Phase-3 D-01 deferred item).
- An `is_current` / currency flag on returned states — unneeded under one-current-per-belief.
