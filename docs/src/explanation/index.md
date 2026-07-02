---
title: Explanation
description: Understanding-oriented background on doxastica, covering AGM belief revision, the Kumiho architecture, scopes, the superseded chain, the two seams, and derived current state.
---

# Explanation

These pages explain the ideas behind doxastica: the theory it implements, the architecture it follows, and the design decisions that make it correct and reusable. Read them when you want to understand *why* the library works the way it does. The [tutorial](../tutorials/first-belief-store.md) and [how-to guides](../how-to/index.md) show you *how*.

## Theory and architecture

- **[What Is AGM Belief Revision? Revise, Expand, Contract](agm-belief-revision.md)**: The epistemic problem doxastica solves, belief base versus belief set, the three operations, and what doxastica keeps and drops from the theory.
- **[The Kumiho Architecture](kumiho-architecture.md)**: The graph-native, append-only design doxastica implements, and its two deliberate departures from the paper.

## The core model

- **[Scopes and the World Scope](scopes-and-world-scope.md)**: What a scope is, why multi-scope extends single-agent Kumiho, and why contracting the world scope is forbidden.
- **[The Superseded Chain: Append-Only, No Recovery](superseded-chain-no-recovery.md)**: Why nothing is ever deleted, how the revision spine is structured, and how it replaces AGM recovery with an audit trail.
- **[Derived Current State and the UUID7 Ordering Contract](derived-current-uuid7-ordering.md)**: Why current state is computed rather than stored, and how the ordering contract handles intra-millisecond collisions.

## Design boundaries

- **[The Two Seams: BeliefStore vs BackendPort](beliefstore-vs-backendport.md)**: The public protocol consumers code against, the internal one storage backends implement, and why there are two.
