# Roadmap: doxastica

## Overview

doxastica is a standalone, zero-LLM Python library implementing the Kumiho AGM
belief-revision core (NVM's M0 milestone). Its definition of done is not a running app but a
**green backend-conformance property suite** — mechanically verified AGM/Hansson postulate
compliance and structural invariants run over every registered backend. The architecture has
TWO distinct seams: the public `BeliefStore` Protocol (the NVM↔core seam consumers code
against) and, *below* it, an internal **backend port** that a backend-agnostic `MemoryCore`
writes against (Ports & Adapters).

## Milestones

- ✅ **v0.1.0 — Kumiho AGM Core (M0)** — Phases 1–8 (shipped 2026-07-04) — full detail: [milestones/v0.1.0-ROADMAP.md](milestones/v0.1.0-ROADMAP.md)
- 🚧 **v0.2.0 — Stance (R21)** — Phases 9–10 (in progress) — adds the ordinal `stance` field, its canonical total order, and dual-backend persistence + formal proof, closing the ratified NVM R21 gap.

## Phases

<details>
<summary>✅ v0.1.0 — Kumiho AGM Core (M0) (Phases 1–8) — SHIPPED 2026-07-04</summary>

- [x] Phase 1: Protocol, Backend Port & Data-Model Decisions (4/4 plans) — 2026-06-14
- [x] Phase 2: Backend Adapters & Schema Bootstrap — De-risking Spike (4/4 plans) — 2026-06-15
- [x] Phase 3: Append-Only Revision Spine — Keystone (4/4 plans) — 2026-06-16
- [x] Phase 4: Retrieval & Observation Surface (2/2 plans) — 2026-06-18
- [x] Phase 5: Edge Model & Contraction Cascade (3/3 plans) — 2026-06-18
- [x] Phase 6: Structural Time-Travel (2/2 plans) — 2026-06-19
- [x] Phase 7: AGM/Hansson Backend Conformance Suite & Irony Join — M0 Exit Gate (4/4 plans) — 2026-06-19
- [x] Phase 8: Publishable Polish (3/3 plans) — 2026-06-19

Full phase goals, success criteria, and plan breakdowns are archived in
[milestones/v0.1.0-ROADMAP.md](milestones/v0.1.0-ROADMAP.md).

</details>

### v0.2.0 — Stance (R21) (Phases 9–10)

- [x] **Phase 9: Stance Value Layer, Write & Persistence** - Land the canonical `Stance` ordinal enum, add it to the frozen `BeliefState`, thread it through the write surface and time-travel, and round-trip it byte-stable on both backends — comparison-only, no arithmetic path. (completed 2026-07-04)
- [ ] **Phase 10: Stance Formal Proof & Docs** - Widen the dual-backend property/conformance suite so it carries stance non-vacuously (K*6 Extensionality now compares stance), and showcase stance in the Cluedo tutorial + refreshed docs.

## Phase Details

### Phase 9: Stance Value Layer, Write & Persistence

**Goal**: The core *stores and compares* stance — a canonical ordinal enum lands on `BeliefState`, is accepted on the write surface (optional, defaulting to `certain`), is preserved verbatim by `contract`, reconstructed by `get_scope_at`, and round-trips byte-stable on both backends, with ordinal comparison the only reachable operation over the type.
**Depends on**: Phase 8 (v0.1.0 shipped — frozen value layer, dual backends, write spine, `get_scope_at` all in place)
**Requirements**: STANCE-01, STANCE-02, STANCE-03, STANCE-04, STANCE-05, STANCE-06
**Success Criteria** (what must be TRUE):

  1. A `Stance` enum exists with a **total order** `doubted < suspected < believed < certain` (plain `Enum` + `functools.total_ordering` + explicit integer rank; `IntEnum`/`StrEnum` rejected) — `Stance.doubted < Stance.certain` is `True` and every pair is ordered.
  2. Arithmetic and cross-type comparison on stance raise `TypeError` at the type level — `Stance.certain + Stance.doubted`, `Stance.certain * 2`, and `Stance.believed < 5` each raise; no core code path performs arithmetic on stance.
  3. `BeliefState` carries a `stance` field (six fields → seven, closed-taxonomy docstring updated); `revise`/`expand` accept an **optional** `stance` defaulting to `certain`, and existing callers that omit it are unaffected.
  4. A stance written via `revise`/`expand` round-trips **byte-stable** through `query_scope` on **both** the in-memory and ladybug backends (same encode/hydrate discipline as `value`; serialized via member `.name`).
  5. `contract` preserves the prior stance **verbatim** on the retracted tail it appends, and `get_scope_at` reconstructs stance unchanged along with the rest of the state.**Plans**: 2 plans

**Wave 1**

- [x] 09-01-PLAN.md — Stance type, model & write-through spine (enum + required field + core/protocol/ladybug threading + SC2 unit proof)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 09-02-PLAN.md — Stance persistence & time-travel proof (dual-backend byte-stable round-trip, contract-verbatim, get_scope_at)

### Phase 10: Stance Formal Proof & Docs

**Goal**: Stance is mechanically *proven* correct, not vacuously green — the dual-backend property suite tracks stance in its oracle and widens the base-comparison key so K*6 Extensionality parity actually compares stance — and the docs showcase stance as a within-scope epistemic gradient with reader-side comparison.
**Depends on**: Phase 9
**Requirements**: STANCE-07, DOCS-01
**Success Criteria** (what must be TRUE):

  1. The shadow/fold oracle records `stance` per tracked belief-in-scope entry, and the harness state-equality key widens `{belief_id: value}` → `{belief_id: (value, stance)}` everywhere the SUT is compared to the oracle — so a pair of ops agreeing on `value` but differing on `stance` **fails** K*6 (`revise ≡ expand`) parity instead of passing vacuously.
  2. Hypothesis property tests (both backends, oracle-independent, `test_invariants.py` style) assert the order is **total and antisymmetric** and that **no arithmetic operator is reachable** on the type (the negative is asserted — `+`/`*`/int-`<` raise `TypeError`).
  3. Round-trip / preservation / reconstruction properties hold under Hypothesis on both backends: stance survives `revise → query_scope`; `contract` preserves the prior stance verbatim (STANCE-04); `get_scope_at` reconstructs it (STANCE-05).
  4. The M0 conformance suite stays green on both backends (still SKIP-not-fail when the ladybug driver is absent).
  5. The Cluedo detective tutorial demonstrates a **within-scope epistemic gradient** (`suspected` → `believed` → `certain`) plus one **reader-side ordinal comparison** driving a decision, reconciles stance (within-scope degree) against the certain/provisional **scope** split (cross-scope); `revise`/`expand` signature references are refreshed across the docs site and `mkdocs build --strict` stays green.

**Plans**: 4 plans

**Wave 1** *(three independent test tracks — disjoint files, parallel-friendly)*

- [x] 10-01-PLAN.md — SC1: widen the stateful oracle to carry stance + mandatory non-vacuity discrimination proof (tests/test_invariants.py)
- [x] 10-02-PLAN.md — SC2: exhaustive order-law enumeration (antisymmetry/transitivity/trichotomy) + no-arithmetic closure guard (tests/test_stance.py)
- [x] 10-03-PLAN.md — SC3: stance-quantified persistence — round-trip / contract-verbatim / get_scope_at over all four members × both backends (tests/test_stance_persistence.py)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 10-04-PLAN.md — D-13 export `Stance` + SC5 Cluedo tutorial (gradient + reader-side ordinal decision + stance/scope reconciliation) + SC4 dual-env SKIP-not-fail confirmation

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Protocol, Backend Port & Data-Model Decisions | v0.1.0 | 4/4 | Complete | 2026-06-14 |
| 2. Backend Adapters & Schema Bootstrap | v0.1.0 | 4/4 | Complete | 2026-06-15 |
| 3. Append-Only Revision Spine | v0.1.0 | 4/4 | Complete | 2026-06-16 |
| 4. Retrieval & Observation Surface | v0.1.0 | 2/2 | Complete | 2026-06-18 |
| 5. Edge Model & Contraction Cascade | v0.1.0 | 3/3 | Complete | 2026-06-18 |
| 6. Structural Time-Travel | v0.1.0 | 2/2 | Complete | 2026-06-19 |
| 7. AGM/Hansson Backend Conformance Suite & Irony Join | v0.1.0 | 4/4 | Complete | 2026-06-19 |
| 8. Publishable Polish | v0.1.0 | 3/3 | Complete | 2026-06-19 |
| 9. Stance Value Layer, Write & Persistence | v0.2.0 | 2/2 | Complete    | 2026-07-04 |
| 10. Stance Formal Proof & Docs | v0.2.0 | 3/4 | In Progress|  |
