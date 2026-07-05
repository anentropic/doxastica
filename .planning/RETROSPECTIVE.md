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

## Milestone: v0.2.0 — Stance (R21)

**Shipped:** 2026-07-05
**Phases:** 2 | **Plans:** 6 | **Tasks:** 13

### What Was Built
- A canonical ordinal `Stance` enum (plain `Enum` + `functools.total_ordering` + explicit integer rank — `IntEnum`/`StrEnum` rejected) as a required seventh `BeliefState` field, threaded write → persist → read on both backends with `certain` as the API default (`.name`-serialize / `Stance[token]`-hydrate).
- Byte-stable dual-backend persistence proven exhaustively over all four members × both backends (24 cases): round-trip, `contract`-verbatim, and `get_scope_at` reconstruction.
- A **non-vacuous** formal proof: the shadow oracle's state-equality key widened to `{belief_id: (value, stance)}` so K*6 Extensionality (`revise ≡ expand`) fails on a stance mismatch instead of passing vacuously — plus an exhaustive order-law enumeration and a no-arithmetic closure guard proving `+`/`*`/int-`<` raise `TypeError`.
- `Stance` exported from the package root; the Cluedo tutorial teaches the within-scope epistemic gradient + a reader-side ordinal decision + a stance-vs-scope reconciliation; `mkdocs build --strict` green. Closes the ratified NVM R21 gap.

### What Worked
- **Non-vacuity treated as a first-class requirement, not an afterthought.** The milestone's definition of done was "proven non-vacuous," so each success criterion shipped with a mutation/revert probe (broken `_base_of`, broken `__lt__`, `doubted`-only hydrate) and a `hypothesis.event()` label confirming the discriminating path actually fires. This is the pattern that stops a green-but-vacuous suite.
- **Reusing the v0.1.0 oracle harness.** Widening the existing stateful oracle's base key to carry stance was a small, load-bearing change — the port-first / in-memory-oracle foundation paid off directly.
- **Type-choice validated against its operational contract before locking.** `IntEnum` was rejected on contact because it inherits `int`'s arithmetic; the comparison-only contract forced a plain `Enum` + `total_ordering`. Catching this at decision time (not in review) avoided a rework.

### What Was Inefficient
- **A VALIDATION.md artifact was left in `draft` for Phase 9** even though the phase passed VERIFICATION 5/5 with substantive dual-backend tests — a stale artifact, not a coverage gap, but it surfaced as a Nyquist "partial" at audit. Close validation artifacts as part of phase completion.
- **Minor doc-anchor / conformance-registry drift** (WR-01/WR-02) carried as advisory tech debt; a mechanical conformance-registry check was added mid-milestone (`bb486be`) to prevent the unchecked-string-registry drift recurring.

### Patterns Established
- **Prove non-vacuity with a mutation probe per success criterion.** For any "the suite now checks X" claim, ship a deliberately-broken variant that must fail, plus a coverage label that must fire. A widening that can't fail is vacuous.
- **Widen the oracle key, not just the SUT.** When adding a tracked field to a property suite, the oracle's comparison key must widen too, or parity passes vacuously.
- **Validate an enum/type against its operational contract before locking** (comparison-only ⇒ not `IntEnum`).

### Key Lessons
1. "Green suite" ≠ "meaningful suite." When adding a field to a property-tested invariant, prove the new dimension can *fail* — a mutation probe per criterion is the cheapest credible evidence.
2. A tracked field must be added to the oracle's equality key, not only to the system under test, or the postulate that should discriminate it passes vacuously.
3. Close per-phase validation artifacts (VALIDATION.md draft → approved) at phase completion, so milestone audit doesn't flag stale-but-passing phases.

### Cost Observations
- Model mix: predominantly opus (planner + executor), sonnet for checker/verifier roles — unchanged from v0.1.0.
- Notable: a small, tightly-scoped milestone (6 plans) riding on the v0.1.0 harness; most spend was in the Phase-10 formal-proof widening (oracle key + exhaustive parametrization), not new production code (~75 net `src` LOC).

---

## Cross-Milestone Trends

### Process Evolution
- v0.1.0 established the baseline: port-first design, in-memory-oracle conformance testing, and a full-`prek` verification gate. Future milestones should carry these forward.
- v0.2.0 added a **non-vacuity discipline**: extending a property suite ships with a per-criterion mutation probe + coverage label proving the new dimension can fail. Carry this into any future field/invariant addition.

### Recurring Lessons
- **Local verification must mirror CI's gate** (full `prek`, correct extras synced) — v0.1.0 lesson, still standing.
- **Green ≠ meaningful** — v0.2.0 sharpened this: prove the suite discriminates the thing it claims to test.
- **Close artifacts at the boundary they belong to** — v0.1.0 (milestone label ↔ version), v0.2.0 (VALIDATION.md draft state) — leftover-artifact drift is a repeating small tax; close on completion.
