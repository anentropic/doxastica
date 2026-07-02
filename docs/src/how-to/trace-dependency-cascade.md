---
title: How to Trace a Dependency Cascade with get_impact
description: Lay DEPENDS_ON and DERIVED_FROM edges with add_edge, then use get_impact to find every belief affected by a change, reading the ImpactResult and bounding the walk with depth.
---

# How to Trace a Dependency Cascade with get_impact

This guide shows you how to record dependencies between belief states and then trace, from a changed belief, every belief that depends on it (the *impact cascade*) using [`get_impact`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_impact).

When you revise or retract a belief, you often need to know what else is affected. If belief B was derived from belief A, changing A means B may need re-examining. `get_impact` answers "what depends on this?" over a bounded, cycle-safe walk.

## Requirements

- A constructed [`MemoryCore`](../reference/doxastica/core.md#doxastica.core.MemoryCore). See [Your First Belief Store](../tutorials/first-belief-store.md).
- A grasp of the closed [`EdgeType`](../reference/doxastica/models.md#doxastica.models.EdgeType) taxonomy: `DEPENDS_ON`, `DERIVED_FROM`, and `SUPERSEDES`. Only the first two participate in impact cascades.

## Lay dependency edges with add_edge

[`add_edge`](../reference/doxastica/core.md#doxastica.core.MemoryCore.add_edge) connects two belief *states* by their `state_id`. Every write operation returns the [`BeliefState`](../reference/doxastica/models.md#doxastica.models.BeliefState) it created, so capture those return values to get the ids you need.

The core's edge-storage convention is **dependent → source**: the edge points *from* the belief that depends *to* the belief it depends on. Read `add_edge(B, A, DERIVED_FROM)` as "B was derived from A."

```python
from uuid import uuid7

from doxastica import EdgeType, InMemoryBackend, MemoryCore

core = MemoryCore(InMemoryBackend())
scope = "mission-control"

# Record three beliefs and capture their states.
power = core.revise(scope, "power-budget", "120W", source_event_id=uuid7())
thermal = core.revise(scope, "thermal-model", "stable", source_event_id=uuid7())
schedule = core.revise(scope, "ops-schedule", "v1", source_event_id=uuid7())

# thermal-model was derived from power-budget; ops-schedule depends on thermal-model.
core.add_edge(thermal.state_id, power.state_id, EdgeType.DERIVED_FROM)  # (1)!
core.add_edge(schedule.state_id, thermal.state_id, EdgeType.DEPENDS_ON)
```

1. Dependent first, source second. This edge means "`thermal` derives from `power`."

The resulting dependency graph looks like this, with arrows pointing from dependent to source:

```mermaid
flowchart LR
    schedule["ops-schedule"] -->|DEPENDS_ON| thermal["thermal-model"]
    thermal -->|DERIVED_FROM| power["power-budget"]
```

## Call get_impact

`get_impact` takes the `state_id` of the belief that changed and returns everything that *depends on* it: its downstream dependents. It walks **against** the stored arrows, following `DEPENDS_ON` and `DERIVED_FROM` edges (never `SUPERSEDES`).

Ask what is affected by a change to `power-budget`:

```python
result = core.get_impact(power.state_id)
print(sorted(b.belief_id for b in result.reached))
# ['ops-schedule', 'thermal-model']
```

Both `thermal-model` (directly derived from power) and `ops-schedule` (transitively, via thermal) come back. The start node itself (`power-budget`) is **excluded** from `reached`.

## Read the ImpactResult

`get_impact` returns an [`ImpactResult`](../reference/doxastica/models.md#doxastica.models.ImpactResult) with three fields:

| Field | Type | Meaning |
|-------|------|---------|
| `reached` | `tuple[BeliefState, ...]` | The affected belief states (excluding the start) |
| `frontier` | `frozenset[UUID]` | State ids left unexpanded when a depth bound stopped the walk |
| `truncated` | `bool` | `True` exactly when the walk was cut short by the depth bound |

```python
result = core.get_impact(power.state_id)
print(len(result.reached))  # 2
print(result.frontier)  # frozenset() — nothing left unexpanded
print(result.truncated)  # False — the walk ran to completion
```

A full-closure walk (the default) always finishes with an empty `frontier` and `truncated=False`. The `frontier`/`truncated` fields exist so that a *bounded* walk can never silently under-report; it always tells you it stopped early and what it left behind.

## Bound the walk with depth

Pass `depth` to limit how many hops the walk follows. This is useful for large graphs where you only care about immediate or near dependents.

```python
# Only direct dependents of power-budget (one hop).
shallow = core.get_impact(power.state_id, depth=1)
print(sorted(b.belief_id for b in shallow.reached))  # ['thermal-model']
print(shallow.truncated)  # True — more lies beyond
print(len(shallow.frontier))  # 1 — the unexpanded boundary
```

At `depth=1` only `thermal-model` is reached; `ops-schedule` sits beyond the bound. `truncated=True` and a non-empty `frontier` tell you the cascade continues past what was returned. Increase `depth` (or pass `depth=None`, the default, for full closure) to see more.

!!! tip "The walk is cycle-safe"
    Dependency graphs can contain cycles. `get_impact` de-duplicates as it walks and terminates even on cyclic graphs, so you will never get an infinite traversal. A full-closure walk over a finite graph always terminates with an empty frontier.

## Verification

```python
core = MemoryCore(InMemoryBackend())
scope = "mission-control"

a = core.revise(scope, "a", 1, source_event_id=uuid7())
b = core.revise(scope, "b", 2, source_event_id=uuid7())
c = core.revise(scope, "c", 3, source_event_id=uuid7())
core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)
core.add_edge(c.state_id, b.state_id, EdgeType.DEPENDS_ON)

full = core.get_impact(a.state_id)
assert sorted(s.belief_id for s in full.reached) == ["b", "c"]
assert full.truncated is False
assert full.frontier == frozenset()

bounded = core.get_impact(a.state_id, depth=1)
assert sorted(s.belief_id for s in bounded.reached) == ["b"]
assert bounded.truncated is True
```

The full walk reaching both dependents with no truncation, and the bounded walk reporting `truncated=True`, confirms the cascade and its bound-reporting are working.

## Related guides

- [How to Inspect Revision History with get_revision_chain](inspect-revision-history.md)
- [The Superseded Chain: Append-Only, No Recovery](../explanation/superseded-chain-no-recovery.md)
