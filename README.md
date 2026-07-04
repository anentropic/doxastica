# doxastica

A standalone **reference implementation of Kumiho** ([arXiv 2603.17244](https://arxiv.org/abs/2603.17244), Young Bin Park) —
a graph-native AGM belief-revision core — with one deliberate **multi-scope** extension
(Kumiho is single-agent) and one deliberate exclusion (**no recovery**; AGM *recovery* is
dropped in favour of superseded-chain semantics). Zero narrative concepts; correctness is
*provable*, with AGM/Hansson postulates verified mechanically as a backend conformance suite.

## What it is

doxastica is a standalone, append-only belief-revision library. It has **no game, narrative,
or LLM concepts inside it** — only scopes, beliefs, and revisions behind a clean
`BeliefStore` protocol. Revision is forward-only: no operation removes or rewrites a stored
`BeliefState`; superseded states stay on the chain. The library ships a working in-memory AGM
core that depends on `pydantic` alone, with the LadybugDB graph backend available as an
optional extra.

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

The base install ships a fully working in-memory belief-revision core. The `[ladybug]` extra
adds the LadybugDB-backed reference backend behind the same `BeliefStore` protocol.

## Quick Start

See the [Quick Start in the documentation](https://anentropic.github.io/doxastica/) for a
runnable first program using `MemoryCore(InMemoryBackend())`.

## License

MIT. See [LICENSE](LICENSE).
