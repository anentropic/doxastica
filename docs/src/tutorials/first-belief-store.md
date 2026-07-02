---
title: "Your First Belief Store: Revise, Supersede, Time-Travel"
description: Build a doxastica core from scratch and exercise every operation, including revise, expand, contract, walking the revision chain, and reconstructing an earlier state.
difficulty: beginner
---

# Your First Belief Store: Revise, Supersede, Time-Travel

In this tutorial you will build a working belief store and put it through its paces.
By the end you will have:

- Constructed a [`MemoryCore`](../reference/doxastica/core.md#doxastica.core.MemoryCore) with an injected backend (pure dependency injection).
- Recorded beliefs with [`revise`](../reference/doxastica/core.md#doxastica.core.MemoryCore.revise) and read them back with [`query_scope`](../reference/doxastica/core.md#doxastica.core.MemoryCore.query_scope).
- Seen why [`expand`](../reference/doxastica/core.md#doxastica.core.MemoryCore.expand) is mechanically identical to `revise` at the core.
- Retracted a belief with [`contract`](../reference/doxastica/core.md#doxastica.core.MemoryCore.contract).
- Walked the full immutable history with [`get_revision_chain`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_revision_chain).
- Reconstructed a past state with [`get_scope_at`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_scope_at).

**Time:** about 15 minutes.

**Prerequisites:** Python 3.14 (doxastica needs the stdlib `uuid.uuid7()` minted there) and a way to install a package. Nothing else: this tutorial uses only the zero-dependency in-memory backend, so there is no database to set up.

!!! info "New to belief revision?"
    doxastica is an implementation of *AGM belief revision*, a formal model for changing what a knowledge base holds as new information arrives. You do not need to know the theory to finish this tutorial; we define each term as we meet it. When you want the full picture, read [What Is AGM Belief Revision?](../explanation/agm-belief-revision.md).

## Setup

Install doxastica:

```bash
pip install doxastica
```

The base install pulls in only `pydantic` and ships a fully working in-memory core. No graph database is required.

## Step 1: Build the core

doxastica's engine, [`MemoryCore`](../reference/doxastica/core.md#doxastica.core.MemoryCore), has exactly one constructor: it takes a *backend* you build yourself and inject. This is pure dependency injection: there is no `MemoryCore.in_memory()` factory and no hidden default. You build the backend, you pass it in.

For this tutorial we use the zero-dependency [`InMemoryBackend`](../reference/doxastica/backends/memory.md#doxastica.backends.memory.InMemoryBackend).

```python
from uuid import uuid7

from doxastica import BeliefFilter, InMemoryBackend, MemoryCore

core = MemoryCore(InMemoryBackend())  # (1)!
```

1. Build the backend, then inject it. Swapping to the durable LadybugDB backend later means changing only this one line. See [How to Use the LadybugDB Backend](../how-to/ladybug-backend.md).

That is the whole engine. `core` is now ready to record beliefs.

## Step 2: Revise a belief, then read it back

A *belief* is a single piece of knowledge with a stable identity (its `belief_id`) living inside a *scope* (a named belief-holder identified by its `scope_id`). *Revising* a belief records a new value for it.

We will track what an agent named `mission-control` believes about a satellite's status. Every write needs a `source_event_id`: a caller-supplied UUID7 that the core treats as an opaque, time-ordered handle (it is *your* identifier for the event that caused the change; the core never invents it). Mint one with the stdlib `uuid7()`.

```python
scope_id = "mission-control"
belief_id = "satellite-status"

core.revise(scope_id, belief_id, "nominal", source_event_id=uuid7())
```

Now read the current belief base back with [`query_scope`](../reference/doxastica/core.md#doxastica.core.MemoryCore.query_scope). It takes the scope and a [`BeliefFilter`](../reference/doxastica/models.md#doxastica.models.BeliefFilter); an empty filter means "no constraints: give me everything current."

```python
base = core.query_scope(scope_id, BeliefFilter())
print({b.belief_id: b.value for b in base})
```

You should see:

```text
{'satellite-status': 'nominal'}
```

Each entry returned is a [`BeliefState`](../reference/doxastica/models.md#doxastica.models.BeliefState), an immutable record carrying the belief's `value`, its `status`, and the ordering handles. You read its `.value` and `.belief_id` above.

Now revise the same belief to a new value:

```python
core.revise(scope_id, belief_id, "degraded", source_event_id=uuid7())

base = core.query_scope(scope_id, BeliefFilter())
print({b.belief_id: b.value for b in base})
```

You should see:

```text
{'satellite-status': 'degraded'}
```

Notice what *did not* happen: there is no duplicate. `query_scope` returned exactly one entry, the new value. The first state was not edited or deleted; it was *superseded*. The old `"nominal"` state still exists in history (you will see it in Step 5); the current belief base just shows the live tail.

!!! tip "Current state is computed, never stored"
    doxastica never keeps a "current pointer" that could drift out of sync. The current value is *derived* on every read by ordering the states and taking the latest. That this always yields exactly one entry per belief is a mathematical consequence, not an enforced rule. If that intrigues you, see [Derived Current State and the UUID7 Ordering Contract](../explanation/derived-current-uuid7-ordering.md).

## Step 3: Expand vs revise

doxastica exposes a second write operation, [`expand`](../reference/doxastica/core.md#doxastica.core.MemoryCore.expand). In AGM theory, *revision* and *expansion* differ in how they handle consistency. At doxastica's core they are **mechanically identical**: both append a new active state. doxastica stores ground facts and does not run a value-level consistency engine, so the two operations do the same thing here.

Record a second, unrelated belief using `expand`:

```python
core.expand(scope_id, "ground-link", "online", source_event_id=uuid7())

base = core.query_scope(scope_id, BeliefFilter())
print({b.belief_id: b.value for b in base})
```

You should see both beliefs:

```text
{'satellite-status': 'degraded', 'ground-link': 'online'}
```

Use whichever name matches your intent; they behave the same. The difference is explained in [What Is AGM Belief Revision?](../explanation/agm-belief-revision.md).

## Step 4: Contract a belief

*Contracting* a belief retracts it: after a contraction, the belief is no longer in the current base. doxastica does this the append-only way: it appends a `retracted` state rather than deleting anything.

Retract the ground link:

```python
core.contract(scope_id, "ground-link", source_event_id=uuid7())

base = core.query_scope(scope_id, BeliefFilter())
print({b.belief_id: b.value for b in base})
```

The ground link is gone from the current base:

```text
{'satellite-status': 'degraded'}
```

[`contract`](../reference/doxastica/core.md#doxastica.core.MemoryCore.contract) returns `None`; it is a command, not a query. The retracted state is still on the chain; it simply no longer counts as active.

## Step 5: Walk the revision chain

So far you have only seen the *current* base. The full history is always there. [`get_revision_chain`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_revision_chain) returns every state ever recorded for a belief, in order, across all scopes.

Look at the complete history of the satellite status:

```python
chain = core.get_revision_chain("satellite-status")
for state in chain:
    print(state.value, "-", state.status.value)
```

You should see both values, oldest first:

```text
nominal - active
degraded - active
```

Both states are present. The `"nominal"` state was superseded in Step 2, but nothing was destroyed. That is the append-only spine, the foundation of doxastica's audit story. (See [The Superseded Chain](../explanation/superseded-chain-no-recovery.md) for why nothing is ever deleted.)

Now look at the ground link's chain to see the contraction you applied in Step 4:

```python
chain = core.get_revision_chain("ground-link")
for state in chain:
    print(state.value, "-", state.status.value)
```

You should see:

```text
online - active
online - retracted
```

The contraction appended a `retracted` copy of the value rather than removing the original `active` state.

## Step 6: Reconstruct an earlier state

Because every state carries its ordering handle, you can rebuild what a scope looked like at any past point, with no snapshots required. [`get_scope_at`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_scope_at) reconstructs the active base as of a given event id.

We need an `as_of` cut point. Let us record a fresh write and capture its `source_event_id`, then change the belief again afterward:

```python
cut = uuid7()
core.revise(scope_id, "satellite-status", "recovering", source_event_id=cut)

# Later, the status changes again.
core.revise(scope_id, "satellite-status", "nominal", source_event_id=uuid7())

# The current base reflects the latest value:
now = core.query_scope(scope_id, BeliefFilter())
print({b.belief_id: b.value for b in now})
```

You should see the latest value:

```text
{'satellite-status': 'nominal'}
```

Now reconstruct the base *as of* the `cut` event. The cut is inclusive: the state written at `cut` is included.

```python
past = core.get_scope_at(scope_id, as_of_event_id=cut)
print({b.belief_id: b.value for b in past})
```

You should see the value that was current at the cut, not the latest one:

```text
{'satellite-status': 'recovering'}
```

The later `"nominal"` revision is correctly excluded, and the belief *rewinds* to the value it held at the cut. This is structural time-travel: doxastica computes it from chain ordering alone.

## What you have learned

You built a belief store and exercised the whole core surface:

- Constructed a [`MemoryCore`](../reference/doxastica/core.md#doxastica.core.MemoryCore) by injecting an [`InMemoryBackend`](../reference/doxastica/backends/memory.md#doxastica.backends.memory.InMemoryBackend): pure DI.
- Recorded knowledge with [`revise`](../reference/doxastica/core.md#doxastica.core.MemoryCore.revise) and [`expand`](../reference/doxastica/core.md#doxastica.core.MemoryCore.expand), and saw supersession keep the current base free of duplicates.
- Retracted a belief with [`contract`](../reference/doxastica/core.md#doxastica.core.MemoryCore.contract).
- Read the current base with [`query_scope`](../reference/doxastica/core.md#doxastica.core.MemoryCore.query_scope).
- Inspected full immutable history with [`get_revision_chain`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_revision_chain).
- Reconstructed a past state with [`get_scope_at`](../reference/doxastica/core.md#doxastica.core.MemoryCore.get_scope_at).

## Next steps

- [How to Query the Current Belief Base with BeliefFilter](../how-to/query-with-belief-filter.md): narrow `query_scope` results precisely.
- [How to Trace a Dependency Cascade with get_impact](../how-to/trace-dependency-cascade.md): see what a belief change affects downstream.
- [How to Use the LadybugDB Backend](../how-to/ladybug-backend.md): swap the in-memory backend for durable graph storage.
- [What Is AGM Belief Revision?](../explanation/agm-belief-revision.md): the theory behind the operations you just used.
