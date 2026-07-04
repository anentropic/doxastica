---
title: How to Retract a Belief with contract
description: Retract a belief in a doxastica scope using contract, understand the vacuity no-op and the world-scope guard, and observe the retracted tail.
---

# How to Retract a Belief with contract

This guide shows you how to retract a belief so it leaves the current belief base, why contracting an absent belief does nothing, why contracting the world scope is forbidden, and how to see the retracted state in history.

*Contraction* is the AGM operation for giving up a belief. doxastica implements it the append-only way: it appends a `retracted` state rather than deleting anything. If the concept is new to you, read [What Is AGM Belief Revision?](../explanation/agm-belief-revision.md) first.

## Requirements

- A constructed [`MemoryCore`](../reference/doxastica/core.md#doxastica.core.MemoryCore). This guide uses the in-memory backend; see [Your First Belief Store](../tutorials/first-belief-store.md) for construction.

## Call contract

[`contract`](../reference/doxastica/core.md#doxastica.core.MemoryCore.contract) takes the scope, the belief id, and a caller-supplied `source_event_id`. It returns `None`.

```python
from uuid import uuid7

from doxastica import BeliefFilter, InMemoryBackend, MemoryCore

core = MemoryCore(InMemoryBackend())
core.revise("mission-control", "ground-link", "online", source_event_id=uuid7())

# Retract the belief.
core.contract("mission-control", "ground-link", source_event_id=uuid7())

base = core.query_scope("mission-control", BeliefFilter())
print({b.belief_id: b.value for b in base})  # {}
```

After the contraction the belief is absent from the current base. Nothing was deleted: a `retracted` state was appended on top of the chain, and that retracted tail clears the belief from the live view.

## Contracting an absent belief is a vacuity no-op

If the belief has no active current state (because it was never recorded, or was already retracted), `contract` does nothing at all. It writes no state and creates no scope. This is the AGM *vacuity* property: contracting something you do not believe leaves the store unchanged.

```python
# The belief was never recorded — this is a silent no-op.
core.contract("mission-control", "never-existed", source_event_id=uuid7())
# No error, no write, no scope created.
```

You do not need to guard your calls with an existence check; a redundant contraction is safe and silent.

## The world-scope guard

doxastica reserves one privileged scope, the *world scope*, identified by [`WORLD_SCOPE_ID`](../reference/doxastica/models.md#doxastica.models). Contracting any belief in the world scope is **forbidden** and raises [`WorldScopeContractionError`](../reference/doxastica/errors.md#doxastica.errors.WorldScopeContractionError).

```python
from doxastica import WORLD_SCOPE_ID, WorldScopeContractionError

try:
    core.contract(WORLD_SCOPE_ID, "satellite-status", source_event_id=uuid7())
except WorldScopeContractionError:
    print("World-scope contraction is not allowed.")
```

!!! warning "The guard fires before any write"
    The world-scope check is the first thing `contract` does, before it touches the backend. A forbidden contraction can never leak a partial write, even if the world scope was never created. Why the world scope is special is explained in [Scopes and the World Scope](../explanation/scopes-and-world-scope.md).

## Observe the retracted tail with include_retracted

By default [`query_scope`](../reference/doxastica/core.md#doxastica.core.MemoryCore.query_scope) returns only active beliefs, so a retracted belief is invisible. Pass `include_retracted=True` to surface beliefs whose current tail is `retracted`:

```python
base = core.query_scope("mission-control", BeliefFilter(), include_retracted=True)
for b in base:
    print(b.belief_id, b.value, b.status.value)
# ground-link online retracted
```

The retracted state still carries the value it had at contraction; `contract` copies the prior stored value verbatim. To see the *full* history (the active state and the retracted state side by side) use [`get_revision_chain`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_revision_chain):

```python
for state in core.get_revision_chain("ground-link"):
    print(state.value, state.status.value)
# online active
# online retracted
```

For finer control over status filtering, see [How to Query the Current Belief Base with BeliefFilter](query-with-belief-filter.md).

## Verification

Confirm the three behaviours in one pass:

```python
core = MemoryCore(InMemoryBackend())
core.revise("mission-control", "ground-link", "online", source_event_id=uuid7())
core.contract("mission-control", "ground-link", source_event_id=uuid7())

# Gone from the active base:
print(core.query_scope("mission-control", BeliefFilter()))  # []

# But visible with include_retracted:
retracted = core.query_scope("mission-control", BeliefFilter(), include_retracted=True)
print([b.status.value for b in retracted])  # ['retracted']

# And still in full history:
print([s.status.value for s in core.get_revision_chain("ground-link")])
# ['active', 'retracted']
```

## Troubleshooting

**Problem:** `WorldScopeContractionError` raised when you call `contract`.

**Cause:** The `scope_id` you passed equals `WORLD_SCOPE_ID` (`"__world__"`). Contraction is forbidden there by design.

**Solution:** Contract in a regular scope, or supersede the world-scope belief with a new [`revise`](../reference/doxastica/core.md#doxastica.core.MemoryCore.revise) instead of retracting it. See [Scopes and the World Scope](../explanation/scopes-and-world-scope.md) for the reasoning.

**Problem:** `contract` "did nothing": no error, no change.

**Cause:** This is the intended vacuity no-op: the belief had no active current state to retract.

**Solution:** Confirm the belief is actually active first with `query_scope` if you expected it to exist.

## Related guides

- [How to Query the Current Belief Base with BeliefFilter](query-with-belief-filter.md)
- [How to Inspect Revision History with get_revision_chain](inspect-revision-history.md)
- [The Superseded Chain: Append-Only, No Recovery](../explanation/superseded-chain-no-recovery.md)
