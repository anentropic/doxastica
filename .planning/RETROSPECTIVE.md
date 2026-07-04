# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v0.1.0 — Kumiho AGM Core (M0)

**Shipped:** 2026-07-04
**Phases:** 8 | **Plans:** 26 | **Tasks:** 38

### What Was Built
- A ladybug-free `BeliefStore` Protocol over an internal `BackendPort` (Ports & Adapters), with a frozen pydantic v2 taxonomy and a written UUID7 ordering contract.
- Two shipping backends behind the port — a zero-dependency `InMemoryBackend` (doubling as the AGM oracle) and a `LadybugBackend` implementing all five LPG primitives — plus a driver-blind `MemoryCore` write spine (`revise`≡`expand`, world-scope-guarded `contract`, derived current, immutable chain).
- The full read/time-travel surface (`query_scope`, `get_revision_chain`, bounded `get_impact`, `get_scope_at`) and the M0 exit-gate backend-conformance suite (AGM + Hansson postulates + structural invariants against an independent oracle; Recovery as a strict xfail).
- OSS packaging: pydantic-only base install with `ladybug` as an extra, split CI, PEP 639 metadata, a Diataxis docs site, and a tag-triggered PyPI release pipeline.

### What Worked
- **Formal spec as the definition of done.** Grounding "done" in AGM/Hansson postulates (property tests) rather than a running app kept scope crisp and made correctness mechanically checkable.
- **Port-first, both-backends-from-the-start.** Writing every operation against the port with an in-memory oracle alongside ladybug caught divergences early (e.g. `add_edge` missing-endpoint parity) and made the conformance suite fall out naturally.
- **Decision-grade choices front-loaded** (Phase 1: port granularity, closed filter, UUID7 ordering) avoided expensive retroactive rewrites.

### What Was Inefficient
- **Docs code-block formatting only surfaced in CI.** `blacken-docs` failures round-tripped through CI twice because local verification ran `mkdocs build` but not the full `prek` suite. Fixed by making `uv sync --extra ladybug && prek run --all-files` the verification gate (recorded in CLAUDE.md).
- **Version/milestone naming drift.** The GSD milestone was labelled `v1.0` while the package shipped `0.1.0`; reconciled to `v0.1.0` at close. Pin the milestone label to the intended release version at milestone start next time.
- **Sandbox friction on `uv`/`gh`.** Package downloads and Go-based `gh` needed sandbox bypasses; addressed by widening the sandbox network allowlist.

### Patterns Established
- **In-memory backend = the oracle.** The second backend is not just a proof of the seam; it *is* the property-test oracle. Keep this for any future backend work.
- **Full `prek` suite (CI-parity env) is the verification gate**, not change-specific checks.
- **No GSD/process references in published docs** — only real paper/RFC citations.

### Key Lessons
1. When "done" is a formal property, invest first in the oracle and the conformance harness — features then verify themselves.
2. Local verification must mirror CI's gate exactly (full `prek`, correct extras synced), or failures only appear after push.
3. Reconcile milestone label ↔ release version up front; renaming at close is avoidable churn.

### Cost Observations
- Model mix: predominantly opus (planner + executor), sonnet for checker/verifier roles.
- Notable: the heaviest spend was the Phase-2 ladybug de-risking spike and the Phase-7 conformance suite; the zero-LLM core meant no inference cost in the product itself.

---

## Cross-Milestone Trends

### Process Evolution
- v0.1.0 established the baseline: port-first design, in-memory-oracle conformance testing, and a full-`prek` verification gate. Future milestones should carry these forward.
