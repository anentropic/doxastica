# Milestones

## v0.2.0 Stance (Shipped: 2026-07-05)

**Phases completed:** 2 phases, 6 plans, 13 tasks
**Timeline:** 2026-07-04 → 2026-07-05 · Git range: `97c677d` → `361b12d`
**Delivered:** the ordinal `Stance` field, its canonical total order, and dual-backend persistence + a proven-non-vacuous formal suite — closing the ratified NVM R21 gap.
**Known deferred items at close:** 1 (see STATE.md Deferred Items)

**Key accomplishments:**

- Ordinal `Stance` enum (plain `Enum` + `total_ordering`) added as a required seventh `BeliefState` field and threaded write -> persist -> read on both backends with `certain` as the API default, via `.name`-serialize / `Stance[token]`-name-hydrate.
- Four dual-backend parity tests proving a written stance round-trips byte-stable through query_scope, defaults to certain when omitted, is copied verbatim by contract onto the retracted tail, and is reconstructed by get_scope_at — all via member-identity assertions on both the in-memory and ladybug backends.
- The dual-backend AGM property suite now carries `stance` per belief-in-scope, with a deterministic non-vacuity proof and a `hypothesis.event()` flip label that make the stance widening mechanically proven rather than vacuously green.
- Turned the SC2 stance scaffold into a mechanical proof: the total order is enumerated exhaustively over all 4 members (irreflexivity, trichotomy/totality, antisymmetry, transitivity + reflected-operator consistency), and no arithmetic/bitwise operator is reachable via a closure over every op x every member pair — with a proven-non-vacuous broken-`__lt__` mutation check.
- Widened the three stance-persistence proofs (round-trip, contract-verbatim, get_scope_at) from one pinned witness each to exhaustive `@pytest.mark.parametrize("stance", list(Stance))` — every member proven byte-stable on both the memory and ladybug backends (24 cases, D-08/SC3).
- Exported `Stance` from the package root (the one deliberate behavior-neutral `src/` change), extended the Cluedo tutorial with a within-scope `suspected → believed → certain` gradient plus a single reader-side ordinal decision gate and a stance-vs-scope reconciliation callout, and confirmed the widened M0 conformance suite stays green on both backends with correct SKIP-not-fail behavior when the ladybug driver is absent.

---

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
