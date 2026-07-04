---
phase: 10
slug: stance-formal-proof-docs
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-04
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + hypothesis 6.155.2 |
| **Config file** | `pyproject.toml` (pytest/coverage), `.pre-commit-config.yaml` (prek gate), `mkdocs.yml` (docs) |
| **Quick run command** | `uv run pytest tests/test_stance.py tests/test_stance_persistence.py tests/test_invariants.py -q` |
| **Full suite command** | `uv sync --locked --dev --extra ladybug && prek run --all-files` then `uv run mkdocs build --strict` |
| **Estimated runtime** | ~60 seconds (quick ~10s; full suite + strict docs build ~60s) |

---

## Sampling Rate

- **After every task commit:** Run the quick-run command for the touched test file.
- **After every plan wave:** Run `uv run pytest -q` (full test suite, both backends).
- **Before `/gsd-verify-work`:** `uv sync --locked --dev --extra ladybug && prek run --all-files` green, then `uv run mkdocs build --strict` green.
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Task IDs are assigned during planning; rows below map by Success Criterion and will be
refined to concrete task IDs by the planner.

| SC / Task | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|-----------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| SC1 oracle widening | TBD | 1 | STANCE-07(a,b) | — | N/A | stateful property (both backends) | `uv run pytest tests/test_invariants.py -q` | ✅ widen in place | ⬜ pending |
| SC1 non-vacuity guard | TBD | 1 | STANCE-07 / D-03 | — | N/A | deterministic discrimination + `event()` stat | `uv run pytest tests/test_invariants.py -q --hypothesis-show-statistics` | ❌ W0 (new `test_widened_key_discriminates_stance`) | ⬜ pending |
| SC2 order laws | TBD | 1 | STANCE-07(d) | — | N/A | parametrized enumeration | `uv run pytest tests/test_stance.py -q` | ✅ strengthen (antisymmetry/transitivity/trichotomy new) | ⬜ pending |
| SC2 no-arithmetic closure | TBD | 1 | STANCE-06 | — | N/A | parametrized closure | `uv run pytest tests/test_stance.py -q` | ✅ strengthen to closure form | ⬜ pending |
| SC3 round-trip/preserve/reconstruct | TBD | 1 | STANCE-07(c), STANCE-04/05 | — | N/A | parametrized over `list(Stance)` × `backend` | `uv run pytest tests/test_stance_persistence.py -q` | ✅ add `@parametrize("stance", list(Stance))` | ⬜ pending |
| SC4 conformance parity | TBD | 2 | — | — | SKIP-not-fail when ladybug absent | full suite | `uv run pytest -q` (and again without `--extra ladybug`) | ✅ must not regress | ⬜ pending |
| SC5 tutorial + docs | TBD | 2 | DOCS-01 | — | N/A | docs build | `uv run mkdocs build --strict` + `prek run --all-files` | ✅ extend tutorial + export `Stance` (D-13) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_invariants.py::test_widened_key_discriminates_stance` — the D-03 non-vacuity proof (new deterministic test; must FAIL if the `Entry`/base widening is reverted).
- [ ] SC2 order-law tests in `tests/test_stance.py` — irreflexivity, antisymmetry, transitivity, trichotomy via `itertools.product(Stance, repeat=2/3)` (antisymmetry/transitivity/trichotomy are new).
- [ ] SC2 no-arithmetic closure test — strengthen the existing three-witness guard to a closure form over `operator.*` × member pairs.
- [ ] Framework install: none — pytest + hypothesis + ladybug extra all present.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Published docs contain no process-ID leakage | DOCS-01 | Editorial check beyond `--strict` | After `mkdocs build --strict`, grep the built tutorial for `D-0`, `STANCE-`, `Phase `, `SC` — must find none. |

*All other phase behaviors have automated verification.*

---

## How to Detect a Vacuous Pass (per SC)

- **SC1:** revert the `Entry`/base widening locally → `test_widened_key_discriminates_stance` MUST fail. If it still passes, the guard is not guarding. Confirm the `event("write flips the current stance…")` label appears in `--hypothesis-show-statistics`.
- **SC2:** mutate `Stance.__lt__` to a broken order (e.g. always `False`) → trichotomy/transitivity/antisymmetry MUST fail. The old fixed-chain test would slip the mutation through.
- **SC3:** introduce a `doubted`-only hydrate bug (`Stance(props["stance"])` value-lookup) → the `is`-identity assertion MUST raise for the `doubted` parametrization. A single pinned-stance test misses members it never exercises.
- **SC4:** run the suite without the ladybug extra → ladybug cases report SKIP, never fail or silently pass (auto-memory: skipped tests are a red flag — surface, never count as pass).
- **SC5:** `mkdocs build --strict` fails on any broken cross-ref; grep the built tutorial for process IDs.

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
