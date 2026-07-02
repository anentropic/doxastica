---
title: How to Query the Current Belief Base with BeliefFilter
description: Narrow query_scope results with the four closed BeliefFilter fields (belief_ids, status, event_id_min, and event_id_max) and understand the include_retracted precedence rule.
---

# How to Query the Current Belief Base with BeliefFilter

This guide shows you how to narrow the results of [`query_scope`](../reference/doxastica/core.md#doxastica.core.MemoryCore.query_scope) using [`BeliefFilter`](../reference/doxastica/models.md#doxastica.models.BeliefFilter): selecting specific beliefs, filtering by status, restricting by event-id range, and resolving the `include_retracted` precedence.

`query_scope` returns the *current belief base* of a scope: exactly one current state per belief, never a superseded one. `BeliefFilter` lets you constrain which of those current states come back.

## Requirements

- A constructed [`MemoryCore`](../reference/doxastica/core.md#doxastica.core.MemoryCore) with some beliefs recorded. See [Your First Belief Store](../tutorials/first-belief-store.md).

## The four closed fields

`BeliefFilter` is a frozen pydantic model with **exactly four** optional fields. There is no free-text query string; the filter is closed by design, which makes a query injection or an unexpected predicate unrepresentable.

| Field | Type | Meaning when set |
|-------|------|------------------|
| `belief_ids` | `frozenset[str]` | Keep only these belief ids |
| `status` | `frozenset[Status]` | Keep only beliefs whose current tail has one of these statuses |
| `event_id_min` | `UUID` | Keep beliefs whose current tail's `source_event_id` is `>=` this |
| `event_id_max` | `UUID` | Keep beliefs whose current tail's `source_event_id` is `<=` this |

Every field defaults to `None`, meaning *unconstrained*. The fields combine with AND. An empty `BeliefFilter()` constrains nothing and returns the entire current base.

Set up some data to filter against:

```python
from uuid import uuid7

from doxastica import BeliefFilter, InMemoryBackend, MemoryCore, Status

core = MemoryCore(InMemoryBackend())
scope = "mission-control"

core.revise(scope, "satellite-status", "nominal", source_event_id=uuid7())
core.revise(scope, "ground-link", "online", source_event_id=uuid7())
core.revise(scope, "battery", "full", source_event_id=uuid7())

base = core.query_scope(scope, BeliefFilter())
print({b.belief_id: b.value for b in base})
# {'satellite-status': 'nominal', 'ground-link': 'online', 'battery': 'full'}
```

## Narrow by belief_ids

Pass a `frozenset` of belief ids to retrieve only those beliefs:

```python
base = core.query_scope(
    scope,
    BeliefFilter(belief_ids=frozenset({"satellite-status", "battery"})),
)
print({b.belief_id: b.value for b in base})
# {'satellite-status': 'nominal', 'battery': 'full'}
```

## Filter by status

`status` takes a `frozenset` of [`Status`](../reference/doxastica/models.md#doxastica.models.Status) members. The taxonomy is closed to exactly `Status.active` and `Status.retracted`.

Retract a belief, then ask for only retracted ones:

```python
core.contract(scope, "ground-link", source_event_id=uuid7())

retracted = core.query_scope(
    scope,
    BeliefFilter(status=frozenset({Status.retracted})),
)
print({b.belief_id: b.value for b in retracted})
# {'ground-link': 'online'}
```

The status filter is applied to each belief's *current tail* (the latest state), not to its history. A belief whose latest state is active will not appear in a `{retracted}` query even if it was retracted earlier and revised again.

## Restrict by event-id range

`event_id_min` and `event_id_max` filter on the current tail's `source_event_id`. The comparison is **inclusive** on both ends. This *drops* beliefs whose current value falls outside the range; it does not rewind them to an older value.

```python
checkpoint = uuid7()
core.revise(scope, "battery", "charging", source_event_id=checkpoint)

# Only beliefs whose current tail is at or after `checkpoint`.
recent = core.query_scope(scope, BeliefFilter(event_id_min=checkpoint))
print({b.belief_id: b.value for b in recent})
# {'battery': 'charging'}
```

!!! info "Dropping is not rewinding"
    `event_id_max` makes a belief whose current value is newer than the bound simply *absent*; it is never rewound to the value it held earlier. If you want the value a belief *held* at a past point (rewinding), use [`get_scope_at`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_scope_at) instead. See [How to Reconstruct a Scope's State at a Point in Time](reconstruct-scope-at.md).

## include_retracted precedence

`query_scope` takes an `include_retracted` keyword that is ergonomic sugar over the `status` field:

- `include_retracted=False` (the default) is equivalent to `status=frozenset({Status.active})`.
- `include_retracted=True` is equivalent to `status=frozenset({Status.active, Status.retracted})`.

**An explicit `belief_filter.status` always wins.** When you set `status` on the filter, `include_retracted` is ignored entirely.

```python
# include_retracted=True is IGNORED because status is set explicitly.
result = core.query_scope(
    scope,
    BeliefFilter(status=frozenset({Status.active})),
    include_retracted=True,
)
print({b.belief_id for b in result})  # only active beliefs — status wins
```

!!! tip "Pick one mechanism"
    Use `include_retracted` for the common active/active+retracted toggle. Reach for `BeliefFilter(status=...)` when you need exactly one status. Setting both is not an error, but the explicit `status` governs, so avoid mixing them to keep intent clear.

## Verification

```python
# Empty filter returns the whole current base.
assert len(core.query_scope(scope, BeliefFilter())) >= 1

# belief_ids narrows to the requested ids only.
only_battery = core.query_scope(scope, BeliefFilter(belief_ids=frozenset({"battery"})))
assert {b.belief_id for b in only_battery} == {"battery"}

# Explicit status overrides include_retracted.
active_only = core.query_scope(
    scope,
    BeliefFilter(status=frozenset({Status.active})),
    include_retracted=True,
)
assert all(b.status is Status.active for b in active_only)
```

## Related guides

- [How to Reconstruct a Scope's State at a Point in Time](reconstruct-scope-at.md)
- [How to Retract a Belief with contract](contract-a-belief.md)
- [Derived Current State and the UUID7 Ordering Contract](../explanation/derived-current-uuid7-ordering.md)
