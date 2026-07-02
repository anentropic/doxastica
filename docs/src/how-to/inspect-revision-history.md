---
title: How to Inspect Revision History with get_revision_chain
description: Retrieve the full ordered, immutable revision history of a belief across all scopes with get_revision_chain, and pair it with query_scope.
---

# How to Inspect Revision History with get_revision_chain

This guide shows you how to retrieve the complete, ordered history of a belief (every state it ever held, including superseded and retracted ones) using [`get_revision_chain`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_revision_chain).

Where [`query_scope`](../reference/doxastica/core.md#doxastica.core.MemoryCore.query_scope) shows you the *current* base, `get_revision_chain` shows you the *whole spine*. doxastica is append-only, so the history is always intact.

## Requirements

- A constructed [`MemoryCore`](../reference/doxastica/core.md#doxastica.core.MemoryCore) with a belief that has been written more than once. See [Your First Belief Store](../tutorials/first-belief-store.md).

## Call get_revision_chain

`get_revision_chain` takes a single `belief_id` and returns a `list` of [`BeliefState`](../reference/doxastica/models.md#doxastica.models.BeliefState), ordered oldest to newest:

```python
from uuid import uuid7

from doxastica import InMemoryBackend, MemoryCore

core = MemoryCore(InMemoryBackend())
scope = "mission-control"

core.revise(scope, "satellite-status", "nominal", source_event_id=uuid7())
core.revise(scope, "satellite-status", "degraded", source_event_id=uuid7())
core.revise(scope, "satellite-status", "recovering", source_event_id=uuid7())

chain = core.get_revision_chain("satellite-status")
for state in chain:
    print(state.value, "-", state.status.value)
```

You should see every revision in order:

```text
nominal - active
degraded - active
recovering - active
```

## Read the ordered chain

The chain is ordered by the same contract doxastica uses everywhere: primarily by each state's `source_event_id`, with the core-minted `state_id` breaking ties. Because that order is total and deterministic, the last element of the chain is always the most recent state.

```python
latest = chain[-1]
print(latest.value)  # recovering

oldest = chain[0]
print(oldest.value)  # nominal
```

Retracted states appear in the chain too; a contraction is just another appended state:

```python
core.contract(scope, "satellite-status", source_event_id=uuid7())

for state in core.get_revision_chain("satellite-status"):
    print(state.value, "-", state.status.value)
# nominal - active
# degraded - active
# recovering - active
# recovering - retracted
```

Nothing is ever removed or rewritten. Why this matters for auditing is covered in [The Superseded Chain: Append-Only, No Recovery](../explanation/superseded-chain-no-recovery.md).

## Cross-scope behaviour

`get_revision_chain` keys on `belief_id` **alone**, so it is cross-scope. If the same belief id is used in more than one scope, the chain contains states from all of them.

```python
core.revise("agent-a", "shared-belief", "x", source_event_id=uuid7())
core.revise("agent-b", "shared-belief", "y", source_event_id=uuid7())

chain = core.get_revision_chain("shared-belief")
for state in chain:
    print(state.scope_id, state.value)
# agent-a x
# agent-b y
```

Inspect `state.scope_id` to tell the scopes apart. If you want history for one belief in one scope, filter the chain yourself:

```python
agent_a_only = [s for s in chain if s.scope_id == "agent-a"]
```

## Pair with query_scope

`get_revision_chain` and `query_scope` answer different questions. Use them together:

- `get_revision_chain(belief_id)` answers *"What is the full history of this belief?"* Returns every state, across scopes, ordered.
- `query_scope(scope_id, BeliefFilter())` answers *"What does this scope believe right now?"* Returns one current state per belief, in this scope only.

```python
# Full history of one belief:
history = core.get_revision_chain("satellite-status")

# Current value of that belief in a scope:
current = next(
    b for b in core.query_scope(scope, BeliefFilter(), include_retracted=True)
    if b.belief_id == "satellite-status"
)
print(current.value, current.status.value)
```

The current state from `query_scope` is always the tail of the chain for that scope. For precise current-base queries, see [How to Query the Current Belief Base with BeliefFilter](query-with-belief-filter.md).

## Verification

```python
from doxastica import BeliefFilter

core = MemoryCore(InMemoryBackend())
for value in ("nominal", "degraded", "recovering"):
    core.revise("mission-control", "satellite-status", value, source_event_id=uuid7())

chain = core.get_revision_chain("satellite-status")
assert len(chain) == 3
assert chain[0].value == "nominal"
assert chain[-1].value == "recovering"
```

A chain length of 3 in oldest-to-newest order confirms the full immutable history is intact.

## Related guides

- [How to Query the Current Belief Base with BeliefFilter](query-with-belief-filter.md)
- [How to Reconstruct a Scope's State at a Point in Time](reconstruct-scope-at.md)
- [The Superseded Chain: Append-Only, No Recovery](../explanation/superseded-chain-no-recovery.md)
