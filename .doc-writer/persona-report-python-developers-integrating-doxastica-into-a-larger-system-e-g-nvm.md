# Persona Report

**Generated:** 2026-07-01
**Audience:** Python developers integrating doxastica into a larger system (e.g. NVM) (advanced)
**Scenarios tested:** 5
**Results:** 5 PASS, 0 PARTIAL, 0 FAIL

## Summary

The documentation is strong from this persona's perspective and covers all seven declared user tasks end-to-end. Diataxis type-alignment is clean: the tutorial teaches by doing, the how-to guides solve one concrete task each, and the explanation pages carry the epistemic theory this persona is new to. Crucially, every `never_assume` item (AGM revise/expand/contract semantics, the postulates, Kumiho, multi-scope/world-scope, the superseded-chain/no-recovery model, the `BeliefStore` vs `BackendPort` seam, and the UUID7 derived-current contract) is explained at first use, while strong Python/pydantic/DI/graph fluency is correctly assumed. Cross-referencing is dense and consistent, and the pure-DI construction idiom (with the explicit "there is no `MemoryCore.in_memory()` factory" statement) is stated in exactly the places the persona would look. No blocking gaps were found.

---

## Scenario S1: Construct a MemoryCore with an injected in-memory backend, type against BeliefStore, confirm no factory

**Verdict:** PASS

### Navigation Path

1. Started at: `docs/src/index.md`
   - Found: runnable Quick Start showing `core = MemoryCore(InMemoryBackend())` with revise/query round trip and the append-only supersession comment. Establishes pure-DI construction immediately.
   - Followed: link to Tutorials / the Kumiho architecture link.
2. Navigated to: `tutorials/first-belief-store.md`
   - Found: Step 1 explicitly states "there is no `MemoryCore.in_memory()` factory and no hidden default. You build the backend, you pass it in." This directly resolves the "confirm no factory" sub-goal.
3. Navigated to: `explanation/beliefstore-vs-backendport.md`
   - Found: "`MemoryCore` satisfies it, so you can type your code against `BeliefStore`... satisfying the method signatures is enough" plus the audience table confirming integrators live entirely on the public seam. Fully answers the "type against BeliefStore" sub-goal.

All three sub-goals (build via DI, know `MemoryCore` satisfies `BeliefStore`, know there is no factory) are satisfied with working code and explicit prose. PASS.

---

## Scenario S2: Swap to LadybugDB and lease a host-owned connection under a namespace without the core closing it

**Verdict:** PASS

### Navigation Path

1. Started at: `docs/src/index.md` -> How-To Guides index.
2. Navigated to: `how-to/ladybug-backend.md`
   - Found: `pip install "doxastica[ladybug]"`, the explicit note that `LadybugBackend` is not re-exported from the package root (import from `doxastica.backends.ladybug`), `open()` ownership semantics, content tabs for on-disk vs in-memory, and a `BackendDependencyError` fallback pattern.
3. Navigated to: `how-to/lease-shared-connection.md`
   - Found: full tenant-mode recipe with `LadybugBackend.from_connection(conn, namespace="beliefs")`, the explicit "not owned / never closes conn" annotation, a verification block proving the owner's connection still works after `backend.close()` is a no-op, and the namespace validation regex `^[A-Za-z_][A-Za-z0-9_]*$` with `ValueError` examples.

Every part of `done_when` (install extra, build `from_connection`, confirm `close()` is a no-op for a leased handle, know namespace rules) is covered with working, non-placeholder examples. PASS.

---

## Scenario S3: Record dependency edges and trace impact, reading ImpactResult and bounding by depth

**Verdict:** PASS

### Navigation Path

1. Started at: `docs/src/index.md` -> How-To Guides index -> "Trace a Dependency Cascade".
2. Navigated to: `how-to/trace-dependency-cascade.md`
   - Found: the dependent-to-source edge convention spelled out ("`add_edge(B, A, DERIVED_FROM)` reads as B was derived from A"), a mermaid diagram of the graph, capturing `state_id` from write return values, the closed `EdgeType` taxonomy (`DEPENDS_ON`, `DERIVED_FROM`, `SUPERSEDES`) with a note that only the first two participate, an `ImpactResult` field table (`reached` / `frontier` / `truncated`), the depth-bounded example with `truncated=True` and a non-empty `frontier`, the cycle-safety guarantee, and a runnable assertion-based verification block.

All of `done_when` (lay edges with `add_edge`, call `get_impact`, read reached/frontier/truncated including the depth-bounded case) is fully served on a single page. PASS.

---

## Scenario S4: Understand AGM semantics, the derived-current contract, and the no-recovery model

**Verdict:** PASS

### Navigation Path

1. Started at: `docs/src/index.md` -> Explanation index.
2. Navigated to: `explanation/agm-belief-revision.md`
   - Found: the epistemic problem framed for a Python-fluent but AGM-new reader, belief base vs belief set, the three operations, the two deliberate design choices (revise==expand at the core; recovery dropped), and why mechanical postulate verification matters. Opens with an explicit "if you arrived fluent in Python but new to belief-revision theory, this page is for you" — exactly this persona.
3. Navigated to: `explanation/superseded-chain-no-recovery.md`
   - Found: the append-only invariant, the `HAS_REVISION`/`SUPERSEDES` spine (with diagram), the "you cannot lose what you never delete" replacement of recovery, and the audit-history payoff.
4. Navigated to: `explanation/derived-current-uuid7-ordering.md`
   - Found: "current is a theorem, not a stored pointer", the `(source_event_id, state_id)` total-order contract, the intra-millisecond tiebreak rationale, the maximum-then-status-check algorithm, and why there is no `CURRENT_STATE` edge.

Every never-assume epistemic concept is defined at first use, calibrated precisely to a graph/Python expert new to AGM. All of `done_when` satisfied. PASS.

---

## Scenario S5: Query the current base precisely and reconstruct a scope at a past point; understand drop vs rewind

**Verdict:** PASS

### Navigation Path

1. Started at: `docs/src/index.md` -> How-To Guides index -> "Reading the store".
2. Navigated to: `how-to/query-with-belief-filter.md`
   - Found: the four closed `BeliefFilter` fields in a table (`belief_ids`, `status`, `event_id_min`, `event_id_max`), AND-combination semantics, per-field examples, the `include_retracted` precedence rule ("explicit `status` always wins"), and the "Dropping is not rewinding" admonition that primes the drop-vs-rewind distinction.
3. Navigated to: `how-to/reconstruct-scope-at.md`
   - Found: `get_scope_at(scope, as_of_event_id=cut)` with inclusive-cut semantics, an explicit side-by-side comparison table contrasting `get_scope_at` (rewinds) with `query_scope(event_id_max=...)` (drops), and a runnable divergence example returning `degraded` vs `[]`.

Both read paths, all four filter fields, `include_retracted`, `get_scope_at`, and the drop-vs-rewind distinction are covered. All of `done_when` satisfied. PASS.

---

## Revision Recommendations

No revision needed. All scenarios passed.

### Minor observations (non-blocking, not gaps)

- All inline API mentions link into the auto-generated `reference/doxastica/...` mkdocstrings tree. These resolve on the built site but do not exist as source Markdown; a persona navigating the live docs site would follow them successfully. No action required — this is the intended mkdocstrings + literate-nav setup per `mkdocs.yml`.
- The persona's declared starting point in `scenarios.yaml` is `README.md`; the effective docs homepage (`docs/src/index.md`) mirrors the README's Quick Start and links onward into Tutorials/Explanation, so navigation from either entry point converges identically.
