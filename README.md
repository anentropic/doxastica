# doxastica

**Belief revision for systems whose knowledge goes stale.**

Most stores let you write a fact and read it back. Few can answer the question that
matters once a fact turns out to be wrong:

> *What did I conclude from this, and is any of it still true?*

doxastica keeps beliefs on append-only revision chains, records what rests on what, and
when something is retracted or superseded it tells you which conclusions stand on ground
that just moved. Knowledge is held per scope, so several holders (several agents, or an
agent and the world) can believe contradictory things at once, and where they diverge is
a query rather than a guess.

No game, narrative, or LLM concepts inside: only scopes, beliefs, revisions, and edges,
behind a `BeliefStore` protocol.

It is a standalone **reference implementation of Kumiho**
([arXiv 2603.17244](https://arxiv.org/abs/2603.17244), Young Bin Park), a graph-native
AGM belief-revision core, with one deliberate **multi-scope** extension (Kumiho is
single-agent) and one deliberate exclusion (**no recovery**; AGM *recovery* gives way to
superseded-chain semantics).

The specification is therefore a forty-year formal literature, and correctness is
*provable*: AGM/Hansson postulate compliance and structural invariants are verified
mechanically as a property-test suite, with no LLM in the loop. Revision is forward-only,
and no operation removes or rewrites a stored `BeliefState`. An AST scan in CI enforces
the seam's backend-blindness, so a storage dialect cannot leak across it.

## What you get

| Capability | API |
|---|---|
| Supersede a belief without losing what it replaced | `revise()` / `expand()`, `get_revision_chain()` |
| Find what a retraction left stale | `add_edge(..., EdgeType.DEPENDS_ON)`, then `get_impact()` |
| Per-holder knowledge, plus a world scope that can never be retracted | `get_or_create_scope()`, `WORLD_SCOPE_ID`, `WorldScopeContractionError` |
| Rank claims without inventing probabilities | `Stance.certain > believed > suspected > doubted` |
| Ask what a holder knew at a past point | `get_scope_at(scope_id, as_of_event_id)` |
| Retrieve with no free-text predicate, so injection and structure leaks are unrepresentable | `query_scope(scope_id, BeliefFilter(...))` |

`get_impact()` walks `DEPENDS_ON` and `DERIVED_FROM` but never `SUPERSEDES`. It returns an
`ImpactResult` carrying `reached`, plus `frontier` and `truncated`, so a depth-bounded
cascade cannot silently under-report.

## Installation

```bash
# Core (in-memory AGM engine, pydantic only)
pip install doxastica

# With the LadybugDB reference backend
pip install doxastica[ladybug]
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add doxastica
uv add 'doxastica[ladybug]'
```

The base install ships a fully working in-memory belief-revision core. The `[ladybug]`
extra adds the LadybugDB-backed reference backend behind the same `BeliefStore` protocol.

## Quick Start

Build the zero-dependency in-memory core, revise a belief, and read the current base
back. Revising the same belief again supersedes the prior value. `query_scope` always
returns exactly the current tail, never a duplicate (append-only supersession).

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

For the cascade in full, including laying `DEPENDS_ON` edges and reading an
`ImpactResult` after a retraction, see
[The Detective's Notebook](https://anentropic.github.io/doxastica/tutorials/cluedo-detective/),
which revises a theory under contradiction end to end.

## Before you adopt

Honest limits, so you can judge the fit before writing code:

- **You mint the belief ids.** doxastica stores an opaque value under a `belief_id` you
  choose, and does no entity resolution. Two phrasings of the same claim collide only if
  you give them the same id, so the calling layer needs a deliberate keying discipline.
  This is the real integration cost, and it is deliberate: the value stays opaque so the
  core cannot acquire your domain's semantics.
- **It is not a vector store**, and does not replace one. It holds the comparatively small
  set of load-bearing claims, not everything a system has read.
- **The payoff scales with lifetime and holders.** Long-lived state with many revisions,
  or several holders who can disagree, is where dependency tracking and scope joins earn
  their keep. A short single-holder run gets little.
- **The core API is synchronous** and single-writer by design. The reference backend's
  embedded model enforces write serialization for free.

## Documentation

Full documentation, including tutorials, how-to guides, architecture explanation, and the
API reference, is at
**[anentropic.github.io/doxastica](https://anentropic.github.io/doxastica/)**.

## License

MIT. See [LICENSE](LICENSE).
