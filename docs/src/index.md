# doxastica

Graph-native AGM belief-revision core (Kumiho M0)

## Installation

```bash
pip install doxastica
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add doxastica
```

## Quick Start

Build the zero-dependency in-memory core, revise a belief, and read the current base back.
Revising the same belief again supersedes the prior value — `query_scope` always returns
exactly the current tail, never a duplicate (append-only supersession).

```python
from uuid import uuid7

from doxastica import BeliefFilter, InMemoryBackend, MemoryCore

# Zero-dependency in-memory core (no ladybug install needed) — pure DI: build the
# backend and inject it.
core = MemoryCore(InMemoryBackend())

scope_id = "agent-1"
belief_id = "sky-colour"

# Revise: append an active BeliefState for the belief.
core.revise(scope_id, belief_id, "blue", source_event_id=uuid7())

# Read the current base back.
base = core.query_scope(scope_id, BeliefFilter())
print({b.belief_id: b.value for b in base})  # {'sky-colour': 'blue'}

# Revise the same belief to a new value — the prior state is superseded, not removed.
core.revise(scope_id, belief_id, "grey", source_event_id=uuid7())

# query_scope returns exactly the new current tail (one entry, no duplicate).
base = core.query_scope(scope_id, BeliefFilter())
print({b.belief_id: b.value for b in base})  # {'sky-colour': 'grey'}
```
