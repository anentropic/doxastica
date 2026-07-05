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
- ✅ **v0.2.0 — Stance (R21)** — Phases 9–10 (shipped 2026-07-05) — full detail: [milestones/v0.2.0-ROADMAP.md](milestones/v0.2.0-ROADMAP.md)

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

<details>
<summary>✅ v0.2.0 — Stance (R21) (Phases 9–10) — SHIPPED 2026-07-05</summary>

- [x] Phase 9: Stance Value Layer, Write & Persistence (2/2 plans) — 2026-07-04
- [x] Phase 10: Stance Formal Proof & Docs (4/4 plans) — 2026-07-05

Adds the ordinal `stance` field, its canonical total order, and dual-backend persistence
plus a proven-non-vacuous formal suite — closing the ratified NVM R21 gap. Full phase goals,
success criteria, and plan breakdowns are archived in
[milestones/v0.2.0-ROADMAP.md](milestones/v0.2.0-ROADMAP.md).

</details>

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
| 9. Stance Value Layer, Write & Persistence | v0.2.0 | 2/2 | Complete | 2026-07-04 |
| 10. Stance Formal Proof & Docs | v0.2.0 | 4/4 | Complete | 2026-07-05 |
