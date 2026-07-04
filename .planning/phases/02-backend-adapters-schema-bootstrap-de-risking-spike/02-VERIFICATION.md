---
phase: 02-backend-adapters-schema-bootstrap-de-risking-spike
verified: 2026-06-15T12:00:00Z
status: passed
score: 20/20
overrides_applied: 0
---

# Phase 2: Backend Adapters & Schema Bootstrap (De-risking Spike) Verification Report

**Phase Goal:** First real LadybugDB contact, verified before any belief logic stands on it — BOTH backends standing behind the Phase 1 LPG-primitive BackendPort (the `ladybug` reference adapter with flexible connection + idempotent namespaced schema bootstrap, AND the in-memory adapter which doubles as the Phase 7 oracle), plus the `:memory:` test-harness scaffold every later phase depends on. Confirms the port survives contact with the real ladybug API (SC4 spike).
**Verified:** 2026-06-15T12:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Verification Run

`uv run --extra ladybug pytest -p no:randomly -q` → **80 passed, 1 xfailed** in 25.96s

`uv run --extra ladybug basedpyright` → **0 errors, 0 warnings, 0 notes**

The 1 xfail is `test_value_string_round_trips_ladybug` (DEF-02-01: ladybug STRUCT/LIST coercion of brace-shaped string params), tracked with an explicit `@pytest.mark.xfail(strict=False, reason=...)` and deferred to the Phase 3 value-encoding contract. This is expected and documented — not a failure.

## CR-01 Fix Confirmation

The code review (02-REVIEW.md) flagged `upsert_node` hardcoding `state_id` as the MERGE key for all labels. Commits `f7ff677` and `0bf0f5c` land fixes:

- `_PK_BY_LABEL = {"Scope": "scope_id", "Belief": "belief_id", "BeliefState": "state_id"}` dict exists at line 86 of `ladybug.py`
- `_bootstrap_schema` reads PK columns from `_PK_BY_LABEL` (lines 159–170)
- `upsert_node` derives `pk = _PK_BY_LABEL[label]` and excludes the PK from the SET loop (lines 197–210)
- `test_backend_parity.py` exercises `_scope(backend, ...)` and `_belief(backend, ...)` helpers that call `upsert_node("Scope", ...)` and `upsert_node("Belief", ...)` on BOTH backends (tests `test_scope_upsert_parity` and `test_belief_upsert_parity`)
- `test_backend_ladybug.py` has `test_upsert_scope_and_belief_use_their_own_pk` and `test_upsert_tolerates_pk_in_props` exercising the fix directly against LadybugDB

The old masking workaround (stripping `state_id` from ladybug props in `_node()`) has been replaced: the `_node()` helper now passes `{"state_id": state_id, **props}` to BOTH backends symmetrically, with the docstring explicitly noting "true symmetric parity, no backend-specific workaround (the old state_id-stripping branch masked CR-01)". **CR-01 is FIXED and tested.**

WR-01 (PK exclusion from SET loop): fixed in the same `f7ff677` commit (`if key == pk: continue`).

WR-02 (`max_depth=0` degenerate range): fixed in `0bf0f5c` — an explicit `if bound == 0:` short-circuit returns `([], frozenset({start}))` or `([], frozenset())` matching the oracle. Tests `test_max_depth_zero_frontier_parity` and `test_max_depth_zero_no_out_edge_empty_frontier_parity` in `test_backend_parity.py`, and `test_traverse_max_depth_zero` in `test_backend_ladybug.py`.

WR-03 (assert → real raise): fixed in `0bf0f5c` — line 289 `raise ValueError(f"max_depth must be non-negative; got {bound}")` and line 362 `raise TypeError(...)`. Test `test_traverse_negative_depth_raises_valueerror` in `test_backend_ladybug.py`.

WR-04 (isolation CI runs full suite via importorskip): fixed in `0b478e5` — `quality.yml` line 48 now runs `uv run pytest` with no file allowlist; the isolation job relies on `pytest.importorskip` to skip ladybug-dependent tests.

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | `MemoryCore.from_connection(conn, namespace=...)` accepts injected connection never closed; `MemoryCore.open(path, namespace=...)` self-manages | VERIFIED | `LadybugBackend.__init__` stores `owns_conn`; `close()` guards on `self._owns_conn`; `test_ownership` in test_backend_ladybug.py passes: injected conn still usable after `close()`, owned conn raises on `execute()` after `close()` |
| SC2 | Ladybug backend owns namespaced closed subgraph; bootstrap is idempotent `CREATE ... IF NOT EXISTS` | VERIFIED | `_bootstrap_schema` uses `CREATE NODE/REL TABLE IF NOT EXISTS {ns}_*`; `test_bootstrap_idempotent` passes; `test_namespace_isolation` confirms no cross-reads between two namespaces on one DB |
| SC3 | In-memory backend implements same BackendPort, zero extra dep; composes with `:memory:` test harness | VERIFIED | `InMemoryBackend` at `backends/memory.py` — no ladybug import anywhere; 14 passing tests in `test_backend_memory.py`; `conftest.py` yields fresh `InMemoryBackend()` per example; `pip install doxastica` (pydantic-only) confirmed working |
| SC4 | Spike confirms port survives real ladybug API: `IF NOT EXISTS` DDL, `BEGIN`/`COMMIT`, `$param` binds, validated-int depth bound; `get_impact`/`get_scope_at` round-trips acceptable | VERIFIED | All five ladybug primitives pass 19 tests in `test_backend_ladybug.py`; `ACYCLIC` var-length + `var_length_extend_max_depth` raised ceiling; `$param` used for all data values; validated-int bound interpolated into `*1..N`; "port unchanged, SC4 confirmed" recorded in 02-02-SUMMARY.md |
| SC5 | `conftest.py` fixture provides throwaway `:memory:` per example, parametrized over both backends, no state bleed | VERIFIED | `@pytest.fixture(params=["memory","ladybug"])` with fresh `lb.Database()` per call; `importorskip` skips ladybug when absent; 26 parametrized parity tests pass with no cross-example state |

### Observable Truths (Plan must_haves — all 4 plans merged)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Importing doxastica or doxastica.core never chain-loads the ladybug driver (D-02) | VERIFIED | `grep -n "import ladybug" core.py backends/__init__.py __init__.py` → 0 module-level hits (only comments and function-local imports); subprocess test in `test_import_purity.py` exits 0 with ladybug blocked via `sys.meta_path`; 7 import-purity tests pass |
| 2 | `MemoryCore.in_memory()` returns a working core with zero extra dependency (D-01, D-05) | VERIFIED | `test_memory_core_in_memory_works_driver_free` passes; 3 `reference-backend extra` hits in CLAUDE.md; pyproject.toml `[project.dependencies]` = `pydantic>=2.11,<3` only |
| 3 | InMemoryBackend satisfies all five BackendPort primitives (BACK-03) | VERIFIED | 14 tests in `test_backend_memory.py` cover each primitive including cycle-safety, unbounded-empty-frontier, bounded-frontier, unit_of_work rollback/persist |
| 4 | InMemoryBackend.traverse is cycle-safe visited-set BFS returning (reached, frontier) (D-05) | VERIFIED | `traverse` uses `seen: set[str]` with `start_key` pre-added; frontier logic at lines 122-125 of `memory.py`; `test_traverse_is_cycle_safe` passes |
| 5 | BackendDependencyError subclasses both DoxasticaError and ImportError (D-02) | VERIFIED | `errors.py` line 21: `class BackendDependencyError(DoxasticaError, ImportError)`; `test_backend_dependency_error_dual_catch` passes |
| 6 | LadybugBackend implements all five BackendPort primitives over LadybugDB (BACK-02) | VERIFIED | `ladybug.py` has `upsert_node`, `add_edge`, `match_nodes`, `traverse`, `unit_of_work`; 19 tests pass |
| 7 | Injected connection NEVER closed; self-managed one IS (CONN-01, R19) | VERIFIED | `close()` guarded by `self._owns_conn`; `test_ownership` confirms both branches |
| 8 | Schema bootstrap is idempotent — re-running `CREATE ... IF NOT EXISTS` is a safe no-op (CONN-03) | VERIFIED | `_bootstrap_schema` uses `IF NOT EXISTS` for all 6 DDL statements; `test_bootstrap_idempotent` passes |
| 9 | Namespaces isolate subgraphs: two namespaces coexist in one DB without cross-reads (CONN-02) | VERIFIED | `test_namespace_isolation` passes; `_NS_RE` validated before DDL |
| 10 | Namespace identifier is regex-validated before any DDL interpolation (D-04, T-02-01) | VERIFIED | `_validate_namespace` raises `ValueError` pre-DDL; `test_namespace_rejects_unsafe` with 5 bad inputs all pass |
| 11 | traverse compiles max_depth=None to raised ceiling + ACYCLIC var-length, returns (reached, frontier) in one query; port unchanged, SC4 confirmed | VERIFIED | `ladybug.py` lines 284-320: `bound = _DEPTH_CEILING` when `max_depth is None`; `CALL var_length_extend_max_depth={bound}`; `*1..{bound} ACYCLIC`; `min(length(p))` + `EXISTS{}` for frontier; tests pass |
| 12 | Parametrized `backend` fixture yields a fresh throwaway backend per example over [memory, ladybug] (FORMAL-06) | VERIFIED | `conftest.py` fixture with `params=["memory","ladybug"]`; fresh `lb.Database()` per call; parity tests collected as 26 parametrized items |
| 13 | Ladybug fixture param skipped (not errored) when driver is absent (D-03 base CI) | VERIFIED | `lb = pytest.importorskip("ladybug")` in conftest; isolation CI job asserts `ladybug` absent then runs full suite |
| 14 | Fresh in-memory lb.Database per example; no state bleed or lock errors (FORMAL-06) | VERIFIED | Fresh `lb.Database()` constructed inside fixture per call; 80 tests pass with no state bleed |
| 15 | Both backends return identical (reached, frontier) on diamond/cycle/over-bound graphs (D-05, BACK-03) | VERIFIED | 12 parametrized parity traverse tests pass; `test_both_backends_diamond_byte_identical` compares adapters to each other directly |
| 16 | Both backends return identical match_nodes on same inserts (D-05) | VERIFIED | `test_match_nodes_and_exact_parity`, `test_scope_upsert_parity`, `test_belief_upsert_parity` all pass on both backends; `test_both_backends_match_nodes_byte_identical` passes |
| 17 | doxastica imports with ladybug genuinely absent; MemoryCore.in_memory() works driver-free (D-02) | VERIFIED | Module-level AST scan covers protocol/ports/core/backends/memory; subprocess absence test exits 0 |
| 18 | pydantic is the only required runtime dep; ladybug is an opt-in extra (D-03, Option B) | VERIFIED | `pyproject.toml` line 11-12: `dependencies = ["pydantic>=2.11,<3"]`; `[project.optional-dependencies]` has `ladybug` and `all` |
| 19 | CI runs a base job WITHOUT ladybug (import-purity + in-memory); CI runs a full job WITH [ladybug] (D-03, FORMAL-06) | VERIFIED | `quality.yml` has two jobs: `isolation` (no extra, asserts `find_spec('ladybug') is None`, runs full suite) and `full` (`--extra ladybug`, prek + full suite) |
| 20 | CLAUDE.md's dep prose reversed to pydantic-required/ladybug-extra (D-03 [BLOCKING]) | VERIFIED | `grep -c "reference-backend extra" CLAUDE.md` → 3; runtime-dep constraint marked "REVERSED" in the D-03 decision; "pinned to LadybugDB" framing superseded |

**Score:** 20/20 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/doxastica/errors.py` | BackendDependencyError(DoxasticaError, ImportError) | VERIFIED | Line 21; dual catch confirmed |
| `src/doxastica/core.py` | MemoryCore engine + in_memory/open/from_connection factories | VERIFIED | 100 lines; all three factories with function-local ladybug imports |
| `src/doxastica/backends/__init__.py` | Re-exports only InMemoryBackend | VERIFIED | Confirmed; no ladybug import |
| `src/doxastica/backends/memory.py` | InMemoryBackend — five primitives, zero extra dep | VERIFIED | 172 lines; all five primitives fully implemented |
| `src/doxastica/backends/ladybug.py` | LadybugBackend — guarded import + five Cypher primitives | VERIFIED | 367 lines; `_PK_BY_LABEL`, CR-01/WR-01/WR-02/WR-03 all fixed |
| `tests/test_backend_memory.py` | Standalone exercise of five in-memory primitives | VERIFIED | 14 tests, all pass |
| `tests/test_backend_ladybug.py` | importorskip-gated; ownership, isolation, bootstrap, SC4 | VERIFIED | 19 tests (added CR-01/WR-01/WR-02/WR-03 coverage beyond original plan) |
| `tests/conftest.py` | Parametrized backend fixture; fresh throwaway :memory: per example | VERIFIED | Plain `params=["memory","ladybug"]`; no registry (0 grep hits); fresh DB per call |
| `tests/test_backend_parity.py` | Oracle-parity suite: identical (reached, frontier) + match_nodes | VERIFIED | 26 tests including Scope/Belief CR-01 coverage; xfail for DEF-02-01 |
| `tests/test_import_purity.py` | Module-level AST scan + subprocess absence test (D-02) | VERIFIED | Covers protocol/ports/core/backends/memory; negative + positive controls; subprocess test |
| `pyproject.toml` | Option B: pydantic required, ladybug optional-dep | VERIFIED | Confirmed structure |
| `uv.lock` | Re-resolved after ladybug demotion | VERIFIED | ladybug present in lock under optional-dependencies section |
| `.github/workflows/quality.yml` | Two-env CI: isolation + full | VERIFIED | Two jobs; isolation asserts ladybug absent; full syncs `--extra ladybug` |
| `.github/workflows/pr.yml` | Coverage syncs --extra ladybug | VERIFIED | Line 33: `uv sync --locked --dev --extra ladybug` |
| `CLAUDE.md` | Decision-grade dep reversal prose | VERIFIED | 3 `reference-backend extra` mentions; "REVERSED" annotation |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `core.py` | `backends/memory.py` | function-local import in `in_memory()` | VERIFIED | Line 57: `from doxastica.backends.memory import InMemoryBackend` inside method body |
| `core.py` | `backends/ladybug.py` | function-local import in `open()`/`from_connection()` | VERIFIED | Lines 72/89: `from doxastica.backends import ladybug` inside method bodies |
| `backends/ladybug.py` | `ladybug (lb.Connection)` | guarded `import ladybug as lb` | VERIFIED | Lines 58-64: try/except `ImportError` raising `BackendDependencyError` |
| `backends/ladybug.py` | `errors.py` | raises `BackendDependencyError` on absence | VERIFIED | `from doxastica import errors`; error raised in except block |
| `conftest.py` | `backends/{memory,ladybug}.py` | function-local imports; importorskip skips ladybug | VERIFIED | Lines 45/53: function-local imports; `importorskip` at line 45 |
| `test_backend_parity.py` | `conftest.py` | consumes parametrized `backend` fixture | VERIFIED | `def test_*(backend: BackendPort)` throughout; 12 fixture-consuming tests |
| `test_import_purity.py` | `core.py` | module-level AST scan asserts no top-level ladybug import | VERIFIED | `@pytest.mark.parametrize("module", ["protocol","ports","core","backends/memory"])` |
| `pyproject.toml` | `uv.lock` | `uv lock` re-resolves after ladybug demotion | VERIFIED | `ladybug` in lock under optional-dep section only |
| `quality.yml` | `pyproject.toml extras` | base job omits extra; full job syncs `--extra ladybug` | VERIFIED | Lines 34/77 confirm two-env asymmetry |

### Data-Flow Trace (Level 4)

Not applicable — this phase delivers backend adapter primitives and a test harness, not components that render dynamic data from a data source. The backends ARE the data source layer.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite (both backends) | `uv run --extra ladybug pytest -p no:randomly -q` | 80 passed, 1 xfailed in 25.96s | PASS |
| basedpyright strict | `uv run --extra ladybug basedpyright` | 0 errors, 0 warnings, 0 notes | PASS |
| Driver-blind import | `uv run python -c "import doxastica, doxastica.core, doxastica.backends.memory"` | clean | PASS (verified by test_driver_free_spine_imports_with_ladybug_blocked subprocess) |
| Option B install surface | `pyproject.toml [project.dependencies]` = pydantic only | confirmed | PASS |
| No guarded import in driver-blind modules | `grep "import ladybug" core.py backends/__init__.py __init__.py` | 0 module-level hits | PASS |
| Exactly one guarded ladybug import | `grep -n "import ladybug as lb" backends/ladybug.py` | line 59 only | PASS |
| No reportMissingTypeStubs suppression | `grep "reportMissingTypeStubs" backends/ladybug.py` | 0 | PASS |
| Conftest uses plain params list, no registry | `grep "registry" tests/conftest.py` | 0 | PASS |

### Probe Execution

No conventional `scripts/*/tests/probe-*.sh` files declared or present for this phase. The PLAN verification sections use `uv run pytest` + `uv run basedpyright` as the integration checks, run and confirmed above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| BACK-02 | 02-02-PLAN | `ladybug` reference backend adapter implements port over LadybugDB | SATISFIED | LadybugBackend has all five primitives; 19 tests pass |
| BACK-03 | 02-01-PLAN, 02-03-PLAN, 02-04-PLAN | In-memory backend implements same port, zero extra dep, Phase 7 oracle | SATISFIED | InMemoryBackend; 14+26 tests; pydantic-only base install |
| CONN-01 | 02-02-PLAN | Flexible connection: injected never closed; self-managed owned | SATISFIED | `owns_conn` flag; `test_ownership` passes |
| CONN-02 | 02-02-PLAN | Label-family tenancy; closed subgraph; sole writer of ns tables | SATISFIED | Namespaced DDL; `test_namespace_isolation` passes |
| CONN-03 | 02-02-PLAN | Idempotent bootstrap `CREATE ... IF NOT EXISTS` | SATISFIED | `_bootstrap_schema` uses IF NOT EXISTS; `test_bootstrap_idempotent` passes |
| FORMAL-06 | 02-03-PLAN, 02-04-PLAN | Throwaway `:memory:` per example; parametrized fixture; no state bleed | SATISFIED | `conftest.py` fixture; fresh `lb.Database()` per call; 26 parity tests pass |

All 6 required Phase 2 requirements accounted for. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backends/ladybug.py` | 308 | `return [], frontier_zero` | Info | This is the intentional `max_depth=0` short-circuit in `traverse` — returns empty reached + conditional frontier. Not a stub; the adjacent test `test_traverse_max_depth_zero` confirms the behavior is intentional and correct. |

No debt markers (TBD, FIXME, XXX) found in any phase-2-modified files. No unreferenced stubs. The `return [], frontier_zero` at line 308 is a deliberate early-exit with a correct non-empty return value when `start` has out-edges.

### Human Verification Required

None. All deliverables for this phase (adapter primitives, connection lifecycle, schema bootstrap, namespace isolation, parity suite, import isolation, packaging) are mechanically verifiable. The tests run and pass. No visual, real-time, or external-service behavior requiring human confirmation.

### Gaps Summary

No gaps. All 20 must-haves are VERIFIED against the actual codebase:

- The REVIEW.md's CR-01 (hardcoded `state_id` MERGE key), WR-01 (PK re-SET on upsert), WR-02 (`max_depth=0` degenerate range), WR-03 (`assert` → `raise`), and WR-04 (isolation CI file allowlist) are all fixed in commits `f7ff677`, `0bf0f5c`, and `0b478e5`, confirmed in the actual code.
- The 1 xfail (DEF-02-01 ladybug value-coercion) is correctly tracked as a visible deferred item, not masked.
- The code review warnings IN-01 through IN-04 are informational (IN-01 unvalidated edge_type interpolation, IN-02 duck-type check, IN-03 add_edge props stub, IN-04 test helper duplication) and are not blockers for this phase's stated goal. They are noted for Phase 3 awareness.

---

_Verified: 2026-06-15T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
