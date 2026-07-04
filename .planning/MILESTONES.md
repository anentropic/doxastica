# Milestones

## v0.1.0 Kumiho AGM Core (M0) (Shipped: 2026-07-04)

**Phases completed:** 8 phases, 26 plans, 38 tasks

**Key accomplishments:**

- Frozen pydantic v2 value layer and a ladybug-free `BeliefStore` Protocol / `BackendPort` seam — closed `BeliefFilter` (DATA-02), never-under-reporting `ImpactResult` (DATA-04), the written DATA-03 UUID7 ordering contract, and an AST import-purity guard.
- Two shipping backends behind the port: the zero-dependency `InMemoryBackend` (which also serves as the AGM oracle) and the `LadybugBackend` implementing all five `BackendPort` primitives — confirming the LPG-primitive port survives the real ladybug API unchanged.
- The AGM write spine on a driver-blind `MemoryCore` — derived-current selection (D-01: no stored `CURRENT_STATE`), `revise`≡`expand` append, world-scope-guarded `contract`, and an immutable revision chain — running byte-identically on both backends.
- The full retrieval and time-travel surface: `query_scope` (closed filter, retracted-vs-superseded matrix), `get_revision_chain`, a bounded cycle-safe `get_impact` cascade with a `direction`-aware `traverse` primitive, and `get_scope_at` cut-then-max (rewind) reconstruction.
- The M0 exit-gate **backend conformance suite**: AGM revision + Hansson base-contraction postulates and structural invariants proved against an independent oracle on both backends, with AGM Recovery encoded as a strict-`xfail` drift guard (194 passed, 1 xfailed).
- Shipped as an OSS reference implementation: `pydantic`-only base install with `ladybug` demoted to the `[ladybug]` extra, split isolation/full CI, PEP 639 PyPI-ready metadata, a docs site including the published backend-port contract, and an MIT license.

---
