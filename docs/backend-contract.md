# Backend Port Contract (BACK-04)

This document specifies the constraints a third-party **labelled-property-graph (LPG)
backend** must satisfy to be a conforming `doxastica` storage backend. It is keyed to the
internal `BackendPort` Protocol (`src/doxastica/ports.py`, BACK-01) — the seam below the
public `BeliefStore`, the one the backend-agnostic core writes against.

The port is **LPG-primitive, not Cypher-level** (BACK-01): a backend implements five graph
primitives, never a query language. A conforming backend exposes **no** `run` / `query` /
`execute` method and **no** method taking a query string — that boundary makes a dialect
passthrough (and the injection / triple-leak surface it would re-open) unrepresentable.

This spec is authored in Phase 1 and published consumer-facing in Phase 8 (PKG-04). Its
**executable form** is the parameterised conformance suite shipped in Phase 7 (BACK-05),
which the LadybugDB reference adapter and the in-memory oracle both pass identically.

## 1. Data model

A backend MUST emulate a labelled property graph:

- **Nodes** carry a `label` (a string) plus a property map keyed by a node id (`node_id`,
  a `UUID` or `str`).
- **Edges** are typed and directed (`edge_type`, `from_id` → `to_id`), with an optional
  property map.

No relational or document semantics are required beyond emulating this graph. A backend
built on a relational store, a document store, or an in-memory dictionary is conforming so
long as it presents these node/edge semantics through the five primitives below.

## 2. Primitive operation semantics

A backend MUST implement exactly these five primitives, with these semantics:

- **`upsert_node(label, node_id, props)`** — insert-or-update keyed by `node_id`.
  **Idempotent**: re-upserting the same `node_id` never produces a duplicate node.
- **`add_edge(edge_type, from_id, to_id, props=None)`** — add a typed directed edge.
  **Append-only in practice**: the core never asks a backend to delete an edge, so a
  backend may assume edges are never removed.
- **`match_nodes(label, where) -> list[dict]`** — return the nodes of `label` whose
  properties **exact-match** every entry in `where` (**AND-combined**). No query language is
  exposed; `where` is a plain property-equality predicate map, never a string.
- **`traverse(start, edge_types, max_depth) -> (reached, frontier)`** — the **single**
  graph-walk primitive. Following only edges in `edge_types` from `start`, it returns:
  - `reached`: the **de-duplicated, cycle-safe** set of reachable nodes (a visited-set
    walk — the backend MUST terminate on cyclic graphs, never loop);
  - `frontier`: the set of node ids left **unexpanded** when `max_depth` is reached.

  `max_depth=None` ⇒ **full transitive closure** with an **empty frontier**. A finite
  `max_depth` bounds the walk and reports the boundary in `frontier`, so a bounded cascade
  never silently under-reports. `get_impact` and `get_scope_at` compose from this single
  primitive (Phases 3+) — there is no separate per-query method.
- **`unit_of_work() -> AbstractContextManager[None]`** — an **atomic** (all-or-nothing)
  write-transaction context manager. The core groups a multi-write operation (e.g. a
  `revise`: append a new `BeliefState` and re-point the `CURRENT_STATE` pointer) inside one
  `unit_of_work`; either all writes commit or none do.

## 3. Uniqueness

The backend MUST enforce uniqueness on the node **primary id** (`node_id`). The core relies
on `state_id` uniqueness for correctness. LadybugDB provides this via `PRIMARY KEY` — no
separate `UNIQUE` constraint is needed or available. A backend MUST reject or coalesce a
second node sharing an existing primary id (consistent with `upsert_node` idempotency).

## 4. Append-only safety

The core is **append-only**: it never deletes nodes or edges. Contraction **marks** a state
(`status='retracted'`) rather than removing it. A backend MAY therefore assume no deletions
ever occur and optimise accordingly; it MUST NOT require a delete primitive.

## 5. Ordering left to the core

The core orders `match_nodes` / `traverse` results **itself**, by
`(source_event_id byte-order, state_id tiebreak)` (the DATA-03 UUID7 ordering contract). A
backend **need not** return results in any particular order — but it **MUST return all
matches** (no silent truncation, no pagination cap that drops matches).

## 6. Value opacity

Node `value` properties are **opaque blobs** (JSON-encoded by the core). The backend stores
and returns them **verbatim** and **never interprets** them — no eval, no query construction
from value content, no schema imposed on their shape. Opacity is the control that keeps
arbitrary value content from becoming a backend-side execution surface.

## 7. Conformance

A backend is conforming exactly when it **passes the parameterised AGM / Hansson +
structural-invariant suite** (BACK-05, Phase 7) — the **executable form** of this contract.
The in-memory oracle and the LadybugDB reference adapter run the identical parameterised
tests; passing them is the definition of a conforming backend. AGM *recovery* is a named
`xfail` (it is false for belief bases) and is never asserted against a correct backend.
