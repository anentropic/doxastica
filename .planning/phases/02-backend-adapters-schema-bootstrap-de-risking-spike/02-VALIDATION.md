---
phase: 2
slug: backend-adapters-schema-bootstrap-de-risking-spike
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-15
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + hypothesis 6.x (via uv) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~10–30 seconds (in-memory `:memory:` backends; no disk/network) |

**Two-environment note (D-03):** validation runs in BOTH dependency environments:
- **base** (`uv sync` without the `ladybug` extra) → in-memory backend subset + the import-purity
  test must pass with `ladybug` genuinely absent. This is what proves D-02 isolation.
- **`[ladybug]`** (`uv sync --extra ladybug` + dev group) → full suite parametrized over BOTH
  backends.

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest` (both env jobs where the wave touches packaging/isolation)
- **Before `/gsd-verify-work`:** Full suite green in both the base and `[ladybug]` environments
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Reconciled with the actual plan files: tests live as FLAT modules
> (`tests/test_backend_memory.py`, `tests/test_backend_ladybug.py`,
> `tests/test_backend_parity.py`) and a FILLED `tests/conftest.py` — NOT `tests/backends/`
> or a `tests/conftest_smoke` module.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | BACK-03 | T-02-IM-01/02 | in-memory backend satisfies BackendPort (5 primitives, cycle-safe traverse) | unit | `uv run pytest tests/test_backend_memory.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | BACK-03 | — | `MemoryCore.in_memory()` works driver-free; top-level exports importable | unit | `uv run pytest tests/test_backend_memory.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | BACK-02, CONN-01, CONN-02, CONN-03 | T-02-01 | ladybug adapter: ownership (injected conn never closed), namespace isolation, idempotent DDL | unit | `uv run pytest tests/test_backend_ladybug.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | BACK-02 | T-02-02/03/04/05 | five Cypher primitives + SC4 traverse confirmation (ACYCLIC, raised hop cap) + unit_of_work rollback | unit | `uv run pytest tests/test_backend_ladybug.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 3 | BACK-03, FORMAL-06 | T-02-PAR-01 | parametrized throwaway `:memory:` `backend` fixture + oracle parity (diamond/cycle/over-bound + match_nodes) | parametrized | `uv run pytest -p no:randomly tests/test_backend_parity.py -q` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 3 | (D-02) | T-02-PAR-02 | extended import-purity: AST scan over core + backends/memory; subprocess proves driver-free spine | unit | `uv run pytest tests/test_import_purity.py -x -q` | ⚠️ EXTEND | ⬜ pending |
| 02-04-01 | 04 | 4 | BACK-03 | T-02-PKG-01/02 | Option B pyproject (pydantic-only required, ladybug extra); uv.lock consistent | packaging | `uv lock --check && uv sync --dev --extra ladybug && uv run pytest -q` | (config) | ⬜ pending |
| 02-04-02 | 04 | 4 | FORMAL-06 | — | two-env CI (base-isolation job ladybug-absent + full [ladybug] job over both backends); [BLOCKING] CLAUDE.md reversal | ci+docs | `uv run python -c "import yaml; [yaml.safe_load(open(p)) for p in ('.github/workflows/quality.yml','.github/workflows/pr.yml')]" && grep -c "reference-backend extra" CLAUDE.md` | (config) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

> Test scaffolds that must exist (failing/empty) before implementation. Reconciled to the
> actual FLAT plan paths.

- [ ] `tests/test_backend_memory.py` — standalone in-memory primitives + `MemoryCore.in_memory()` (Plan 01)
- [ ] `tests/test_backend_ladybug.py` — `importorskip("ladybug")`-gated: ownership, namespace isolation, idempotent bootstrap, five primitives, SC4 traverse, unit_of_work rollback (Plan 02)
- [ ] `tests/conftest.py` — FILLED with a parametrized `backend` fixture over `["memory", "ladybug"]` (plain params list, D-01a), throwaway `lb.Database()` per example, ladybug param `importorskip`-skipped when absent (Plan 03)
- [ ] `tests/test_backend_parity.py` — oracle-parity suite (diamond / cycle / over-bound chain + match_nodes), the BACK-03/D-05 / FORMAL-06 guarantee (Plan 03)
- [ ] Extend `tests/test_import_purity.py` — add `core` + `backends/memory` to the AST scan AND a subprocess-absence test proving the driver-free spine imports + `MemoryCore.in_memory()` runs with ladybug blocked (Plan 03)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SC4 spike confirmations are documented (30-hop cap, `$param`-in-bound rejection, ACYCLIC unbounded traversal) | BACK-02 | The spike is a *confirmation that the port is unchanged* — its evidence lives in RESEARCH.md and the plan-02 SUMMARY, not a runtime assertion | Verify RESEARCH.md SC4 findings are reflected in `LadybugBackend.traverse` (validated-int bound, raised `var_length_extend_max_depth`) and that the decision string "port unchanged, SC4 confirmed" is recorded in `02-02-SUMMARY.md` |
| Two-env CI runs a job WITHOUT the ladybug extra | FORMAL-06 | CI YAML executes in GitHub Actions, not pytest | Confirm `quality.yml` has a base-isolation job (no `--extra ladybug`) running `tests/test_import_purity.py tests/test_backend_memory.py` with ladybug absent, and a full job with `--extra ladybug` running the whole suite over both backends (the `grep -c "extra ladybug"` asymmetry check covers Job 1 vs Job 2 wiring) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (reconciled to flat plan paths)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready
