---
title: How-To Guides
description: Goal-oriented recipes for specific doxastica tasks: choosing a backend, leasing connections, retracting beliefs, querying, and tracing dependency cascades.
---

# How-To Guides

These guides assume you already know how to build a [`MemoryCore`](../reference/doxastica/core.md#doxastica.core.MemoryCore) (if not, start with [the tutorial](../tutorials/first-belief-store.md)). Each one solves a single, concrete task and links to the relevant explanation when you want the reasoning behind it.

## Backends

- **[How to Use the LadybugDB Backend](ladybug-backend.md)**: Install the ladybug extra and run a core on durable, graph-native storage, on disk or in memory.
- **[How to Lease a Shared LadybugDB Connection (Tenant Mode)](lease-shared-connection.md)**: Inject a connection your application owns under a namespace, so the core runs as a tenant and never closes a handle it does not own.

## Operations

- **[How to Retract a Belief with contract](contract-a-belief.md)**: Retract a belief, understand the vacuity no-op and the world-scope guard, and observe the retracted state in history.

## Reading the store

- **[How to Query the Current Belief Base with BeliefFilter](query-with-belief-filter.md)**: Narrow `query_scope` results with the four closed filter fields and resolve the `include_retracted` precedence rule.
- **[How to Inspect Revision History with get_revision_chain](inspect-revision-history.md)**: Retrieve the full, ordered, cross-scope history of a belief.
- **[How to Reconstruct a Scope's State at a Point in Time](reconstruct-scope-at.md)**: Rewind a scope to the beliefs it held as of a past event id with `get_scope_at`.
- **[How to Trace a Dependency Cascade with get_impact](trace-dependency-cascade.md)**: Record dependency edges and trace every belief affected by a change.
