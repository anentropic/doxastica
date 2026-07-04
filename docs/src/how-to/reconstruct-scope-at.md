---
title: How to Reconstruct a Scope's State at a Point in Time
description: Use get_scope_at to rebuild the active belief base of a scope as of a past event id, with inclusive-cut semantics, and contrast it with query_scope's event range.
---

# How to Reconstruct a Scope's State at a Point in Time

This guide shows you how to rebuild what a scope believed at a past moment using [`get_scope_at`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_scope_at): structural time-travel computed from chain ordering, with no stored snapshots.

The key distinction to keep in mind: `get_scope_at` **rewinds** beliefs to the value they held at the cut, whereas [`query_scope`](../reference/doxastica/core.md#doxastica.core.MemoryCore.query_scope)'s event range **drops** beliefs outside the range. This guide makes that difference concrete.

## Requirements

- A constructed [`MemoryCore`](../reference/doxastica/core.md#doxastica.core.MemoryCore) with a belief that has been revised over time. See [Your First Belief Store](../tutorials/first-belief-store.md).

## Call get_scope_at with an as_of event id

`get_scope_at` takes a scope id and an `as_of_event_id` (a UUID7 cut point) and returns the active belief base as it stood at that cut. The cut point is typically a `source_event_id` you captured at an earlier write.

```python
from uuid import uuid7

from doxastica import InMemoryBackend, MemoryCore

core = MemoryCore(InMemoryBackend())
scope = "mission-control"

core.revise(scope, "satellite-status", "nominal", source_event_id=uuid7())

cut = uuid7()
core.revise(scope, "satellite-status", "degraded", source_event_id=cut)

# The status changes again, after the cut.
core.revise(scope, "satellite-status", "recovering", source_event_id=uuid7())

# Reconstruct the base as of the cut.
past = core.get_scope_at(scope, as_of_event_id=cut)
print({b.belief_id: b.value for b in past})
```

You should see the value that was current *at the cut*, not the latest one:

```text
{'satellite-status': 'degraded'}
```

The belief **rewound** to `"degraded"` (the value it held at `cut`), and the later `"recovering"` revision is excluded.

## Inclusive-cut semantics

The cut is **inclusive**: a state whose `source_event_id` equals `as_of_event_id` *is* included. This is what makes reconstructing at the latest event id give you exactly the current base.

```python
from doxastica import BeliefFilter

latest_event = uuid7()
core.revise(scope, "satellite-status", "nominal", source_event_id=latest_event)

reconstructed = core.get_scope_at(scope, as_of_event_id=latest_event)
current = core.query_scope(scope, BeliefFilter())

print({b.belief_id: b.value for b in reconstructed})  # {'satellite-status': 'nominal'}
print({b.belief_id: b.value for b in current})  # {'satellite-status': 'nominal'}
```

A belief that was retracted at or before the cut is absent from the reconstruction, exactly as it would be in the current base: the cut applies the same active-tail rule, just over the window up to `as_of`.

!!! info "Why no include_retracted here"
    `get_scope_at` has no `include_retracted` flag. It always reconstructs the *active* base as of the cut; that is the meaning of "what did this scope believe then." To browse retracted states, use [`get_revision_chain`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_revision_chain) (see [How to Inspect Revision History](inspect-revision-history.md)).

## Contrast with query_scope's event range

It is easy to confuse `get_scope_at(scope, as_of)` with `query_scope(scope, BeliefFilter(event_id_max=as_of))`. They are different operations:

| | `get_scope_at(scope, as_of)` | `query_scope(scope, BeliefFilter(event_id_max=as_of))` |
|---|---|---|
| Cut applied | **before** picking each belief's latest state | **after** picking each belief's current tail |
| Effect on a since-revised belief | **rewinds** to the value held at the cut | **drops** the belief entirely |
| Use when | You want the past *state* of the scope | You want current beliefs whose latest write is `<= as_of` |

The example below shows the divergence directly. The belief's latest write is *after* the cut:

```python
core = MemoryCore(InMemoryBackend())
scope = "mission-control"

cut = uuid7()
core.revise(scope, "satellite-status", "degraded", source_event_id=cut)
core.revise(scope, "satellite-status", "recovering", source_event_id=uuid7())

# get_scope_at REWINDS to the value at the cut:
print(core.get_scope_at(scope, as_of_event_id=cut))
# [BeliefState(... value='degraded' ...)]

# query_scope event_id_max DROPS the belief (its current tail is newer than the cut):
from doxastica import BeliefFilter

print(core.query_scope(scope, BeliefFilter(event_id_max=cut)))
# []
```

`get_scope_at` returns the rewound `"degraded"` state; `query_scope` returns nothing, because the belief's *current* tail is `"recovering"`, which is newer than the bound. For the `query_scope` side, see [How to Query the Current Belief Base with BeliefFilter](query-with-belief-filter.md).

## Verification

```python
core = MemoryCore(InMemoryBackend())
scope = "mission-control"

core.revise(scope, "satellite-status", "nominal", source_event_id=uuid7())
cut = uuid7()
core.revise(scope, "satellite-status", "degraded", source_event_id=cut)
core.revise(scope, "satellite-status", "recovering", source_event_id=uuid7())

past = core.get_scope_at(scope, as_of_event_id=cut)
assert {b.value for b in past} == {"degraded"}  # rewound, inclusive of the cut
```

Getting `"degraded"` (the value at the cut, not the latest `"recovering"`) confirms inclusive rewind semantics.

## Related guides

- [How to Query the Current Belief Base with BeliefFilter](query-with-belief-filter.md)
- [How to Inspect Revision History with get_revision_chain](inspect-revision-history.md)
- [Derived Current State and the UUID7 Ordering Contract](../explanation/derived-current-uuid7-ordering.md)
