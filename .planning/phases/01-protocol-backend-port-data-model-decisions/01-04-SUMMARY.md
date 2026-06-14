---
phase: 01-protocol-backend-port-data-model-decisions
plan: 04
subsystem: backend-port
tags: [protocol, backend-port, lpg-primitive, seam, contract]
requires:
  - "src/doxastica/models.py (EdgeType — port references it)"
  - "src/doxastica/protocol.py (BeliefStore — port must be distinct from it)"
provides:
  - "src/doxastica/ports.py :: BackendPort(Protocol) — internal LPG-primitive backend seam (BACK-01)"
  - "docs/backend-contract.md — the 7-constraint port-contract spec (BACK-04)"
  - "tests/test_port_distinct.py — BACK-01 distinctness + primitives-only guard"
affects:
  - "Phase 2 (ladybug + in-memory adapters implement BackendPort)"
  - "Phase 3+ (get_impact / get_scope_at compose from traverse)"
  - "Phase 7 (BACK-05 conformance suite = executable form of the contract)"
  - "Phase 8 (PKG-04 publishes docs/backend-contract.md consumer-facing)"
tech-stack:
  added: []
  patterns:
    - "typing.Protocol structural-interface (ellipsis bodies, no inheritance required)"
    - "TYPE_CHECKING-guarded annotation imports + from __future__ import annotations (ruff-clean, backend-blind)"
key-files:
  created:
    - "src/doxastica/ports.py"
    - "docs/backend-contract.md"
    - "tests/test_port_distinct.py"
  modified: []
decisions:
  - "BACK-01: backend port granularity is LPG-PRIMITIVE (five graph primitives), not Cypher-level — recorded in ports.py module docstring; reversal would be a rewrite"
  - "traverse is the SINGLE generic graph-walk primitive returning (reached, frontier); get_impact/get_scope_at compose from it (Phases 3+), no per-query method"
  - "get_impact/get_scope_at round-trip tension under LPG-primitive is NAMED and flagged for the Phase 2 spike (SC4) — not resolved here"
  - "BACK-04 contract authored as prose Markdown keyed to the port methods (Open Q3 resolved); its executable form is the Phase 7 conformance suite (BACK-05)"
metrics:
  duration_min: 4
  completed: "2026-06-14"
  tasks: 2
  files: 3
---

# Phase 1 Plan 04: Backend Port & Contract Summary

Authored the internal LPG-primitive `BackendPort` Protocol (BACK-01) as a seam distinct from
the public `BeliefStore`, plus the 7-constraint backend-port contract spec (BACK-04) and a
mechanical distinctness/primitives-only guard.

## What Was Built

- **`src/doxastica/ports.py`** — `BackendPort(Protocol)`, the second, internal seam below
  the public `BeliefStore`. Exactly five graph primitives, ellipsis bodies, no behavior:
  - `upsert_node(label, node_id, props) -> None` (idempotent on node id)
  - `add_edge(edge_type, from_id, to_id, props=None) -> None` (append-only in practice)
  - `match_nodes(label, where) -> list[dict]` (exact-match AND-combined predicate)
  - `traverse(start, edge_types, max_depth) -> (reached, frontier)` (the single graph-walk)
  - `unit_of_work() -> AbstractContextManager[None]` (atomic write tx)

  The module docstring records the BACK-01 LPG-primitive decision and the named
  `get_impact`/`get_scope_at` round-trip tension flagged for the Phase 2 spike (SC4). No
  `run`/`query`/`execute` method, no query-string method, no `import ladybug` — backend-blind
  like the public seam.

- **`docs/backend-contract.md`** — the BACK-04 drafted spec, 7 constraints keyed to the port
  methods: (1) LPG data model, (2) primitive op semantics (idempotent upsert, append-only
  edges, exact-AND match, cycle-safe `traverse` with `max_depth=None` ⇒ full closure, atomic
  `unit_of_work`), (3) PK uniqueness, (4) append-only safety, (5) ordering left to the core,
  (6) value opacity, (7) conformance via the Phase 7 suite. Notes Phase-8 publication (PKG-04).

- **`tests/test_port_distinct.py`** — three tests: `BackendPort` is a distinct Protocol from
  `BeliefStore`; the port exposes none of `run`/`query`/`execute`; the port surface is exactly
  the five decided primitives.

## Verification Results

- `uv run basedpyright src/doxastica/ports.py` — 0 errors, 0 warnings, 0 notes (strict)
- `uv run ruff check .` — all checks passed
- `uv run pytest -q` — 13 passed (including the 3 new BACK-01 guard tests)
- `docs/backend-contract.md` — 7 `##` constraint headings present
- No `run`/`query`/`execute` method on the port; no `import ladybug`

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

- **BACK-01 (recorded): LPG-primitive granularity.** The port exposes only graph primitives;
  the LPG-vs-Cypher decision is now real in the types, not deferred. Reversal is a rewrite.
- **`traverse` is the single graph-walk primitive.** `get_impact`/`get_scope_at` compose from
  it (Phases 3+); no separate per-query method exists.
- **Round-trip tension named, not resolved.** Composing the cascade ops from the generic
  `traverse` may cost more round-trips than one hand-written Cypher query — accepted cost of
  backend-agnosticism; confirmed (or adjusted) in the Phase 2 ladybug spike (SC4).
- **Contract format: prose Markdown** keyed to the port methods (Open Q3 resolved); the Phase 7
  conformance suite (BACK-05) is its executable form.

## Follow-ups / Carried Forward

- **[Phase 2 spike, SC4]** Confirm the `get_impact`/`get_scope_at` traversal round-trip budget
  is acceptable against the real `ladybug` API, and that an unbounded cycle-safe reachable-set
  is expressible (Open Q2 carry-forward). The port adjusts then if the spike demands it.
- **[Phase 7, BACK-05]** Implement the parameterised conformance suite — the executable form of
  `docs/backend-contract.md`; in-memory oracle and ladybug adapter pass the identical tests.
- **[Phase 8, PKG-04]** Publish `docs/backend-contract.md` consumer-facing.

## Self-Check: PASSED
