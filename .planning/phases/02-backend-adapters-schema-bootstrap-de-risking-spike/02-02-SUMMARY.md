---
phase: 02-backend-adapters-schema-bootstrap-de-risking-spike
plan: 02
subsystem: database
tags: [ladybug, kuzu, cypher, lpg, graph-db, backend-adapter, traverse, pydantic]

# Dependency graph
requires:
  - phase: 01-protocol-backend-port-data-model-decisions
    provides: BackendPort (the five LPG-primitive contract), BackendDependencyError, docs/backend-contract.md
  - phase: 02-backend-adapters-schema-bootstrap-de-risking-spike (plan 01)
    provides: InMemoryBackend oracle, MemoryCore engine + factories, errors.BackendDependencyError
provides:
  - LadybugBackend — the LadybugDB reference adapter implementing all five BackendPort primitives
  - Flexible-connection ownership (owns_conn) — injected connections never closed, self-managed ones are
  - Namespaced idempotent schema bootstrap (CREATE NODE/REL TABLE IF NOT EXISTS {ns}_*)
  - Regex-validated namespace identifier guard before the one sanctioned DDL interpolation
  - SC4 confirmation — the LPG-primitive port survives the real ladybug API unchanged
  - SC4 de-risking finding (DEF-02-01) — ladybug coerces brace/bracket-shaped STRING params
affects: [02-03 parity suite, Phase 3 AGM operations, Phase 3 value-encoding contract, Phase 7 oracle parity]

# Tech tracking
tech-stack:
  added: []  # ladybug 0.17.1 already installed (Plan 02-01 / dev env); this plan only imports it
  patterns:
    - Single guarded driver-import boundary (D-02) raising BackendDependencyError
    - Single sanctioned interpolation guard (validated namespace + validated int depth bound)
    - ACYCLIC var-length one-query traverse with raised var_length_extend_max_depth ceiling
    - QueryResult union narrowing via one isinstance helper (no missing-type-stub suppression)

key-files:
  created:
    - src/doxastica/backends/ladybug.py
    - tests/test_backend_ladybug.py
    - .planning/phases/02-backend-adapters-schema-bootstrap-de-risking-spike/deferred-items.md
  modified:
    - src/doxastica/core.py

key-decisions:
  - "Port unchanged, SC4 confirmed — the Phase-1 BackendPort survives the real ladybug 0.17.1 API; the 30-hop cap and $param-in-bound rejection are adapter-internal details, not port-signature changes"
  - "traverse compiles max_depth=None to _DEPTH_CEILING (1,000,000) with var_length_extend_max_depth raised, ACYCLIC node-distinct var-length, one-query (reached, frontier) via min(length(p)) + EXISTS{}"
  - "traverse excludes start from reached (WHERE b.state_id <> $start) to match the in-memory oracle exactly, which a cycle would otherwise re-include"
  - "DEF-02-01: ladybug coerces brace/bracket-shaped STRING params to STRUCT/LIST, breaking value opacity for JSON object/array values — deferred to the Phase 3 value-encoding contract"

patterns-established:
  - "Guarded driver import: the single D-02 isolation + basedpyright boundary"
  - "Validated-namespace + validated-int are the ONLY two sanctioned Cypher interpolations; all data is $param"
  - "Adapters return raw list[dict] below the model layer (D-04); match_nodes strips ladybug's _ID/_LABEL internals"

requirements-completed: [BACK-02, CONN-01, CONN-02, CONN-03]

# Metrics
duration: 12min
completed: 2026-06-15
---

# Phase 2 Plan 02: LadybugDB Reference Backend & SC4 Confirmation Summary

**LadybugBackend implements all five BackendPort primitives over LadybugDB — guarded driver import, owns_conn lifecycle, regex-validated namespaced idempotent bootstrap, and the SC4 ACYCLIC one-query traverse — confirming the LPG-primitive port survives the real ladybug API unchanged.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-14T23:59:32Z
- **Completed:** 2026-06-15T00:11:24Z
- **Tasks:** 2
- **Files modified:** 4 (2 created src/test, 1 modified src, 1 deferred-items log)

## Accomplishments
- `LadybugBackend` — the reference adapter behind the Phase-1 `BackendPort`, with the SINGLE guarded `import ladybug as lb` (D-02) raising `BackendDependencyError` on absence.
- Flexible-connection ownership (CONN-01 / R19): `open()` self-manages and closes its connection; an injected connection (`from_connection`) is never closed.
- Namespaced, idempotent schema bootstrap (CONN-02 / CONN-03): `CREATE NODE/REL TABLE IF NOT EXISTS {ns}_*`, safe to re-run; namespace regex-validated before the one sanctioned interpolation (D-04, mitigates T-02-01).
- All five LPG primitives in Cypher (BACK-02): `upsert_node` (MERGE…SET), `add_edge` (MERGE edge), `match_nodes` (AND-exact $param), `traverse` (SC4), `unit_of_work` (BEGIN/COMMIT/ROLLBACK).
- **SC4 confirmed, port unchanged** — `traverse` uses ACYCLIC var-length with the `var_length_extend_max_depth` cap raised, returning `(reached, frontier)` in ONE query; the validated-int depth bound + raised ceiling are reflected in code.

## Task Commits

1. **Task 1: Guarded import, ownership, namespace validation, idempotent bootstrap** - `61bb504` (feat)
2. **Task 2: Five LPG primitives + SC4 traverse confirmation** - `d2ca1bd` (feat)
3. **Rule 3 blocking fix: unbreak core.py type-check** - `79954e0` (fix)

## Files Created/Modified
- `src/doxastica/backends/ladybug.py` - The LadybugDB reference adapter; the single guarded driver + basedpyright boundary; ownership flag, namespace guard, idempotent DDL, the five primitives, SC4 traverse.
- `tests/test_backend_ladybug.py` - importorskip-gated tests: ownership, namespace isolation, unsafe-namespace rejection, idempotent bootstrap, five primitives, cycle-safe/unbounded/bounded traverse, unit_of_work rollback + commit (15 tests).
- `src/doxastica/core.py` - Narrowed the forward-reference pyright suppressions now that `LadybugBackend` types resolve; refreshed stale comments; stays driver-blind (Rule 3 fix).
- `.planning/phases/02-.../deferred-items.md` - Logged DEF-02-01 (value-coercion hazard) and DEF-02-02 (pre-existing memory-test type errors).

## Decisions Made
- **Port unchanged, SC4 confirmed.** Verified live against ladybug 0.17.1 / Python 3.14.2: the `(reached, frontier)` shape computes in one query; the 30-hop default cap is lifted via `CALL var_length_extend_max_depth=<bound>`; `$param` is rejected inside the var-length hop range so the bound is an interpolated validated int. None of this changes the Phase-1 port signature.
- **`traverse` excludes `start`** via `WHERE b.state_id <> $start`. Without it, ACYCLIC traversal over a cycle re-includes `start` in `reached`; the in-memory oracle never includes it. This exclusion is the parity fix (oracle parity asserted in Plan 02-03).
- **`match_nodes` uses `RETURN n`** (node object) unwrapped + `_ID`/`_LABEL` stripped, rather than `RETURN n.*` (which prefixes keys as `n.state_id`) — so returned dicts have plain prop keys matching the oracle.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] match_nodes returned `n.`-prefixed keys**
- **Found during:** Task 2
- **Issue:** `RETURN n.*` returned rows keyed `n.state_id`, `n.value`, … — not the plain prop keys the in-memory oracle returns, breaking D-04 parity.
- **Fix:** Switched to `RETURN n` and unwrapped the node-object dict, stripping ladybug's internal `_ID`/`_LABEL` keys.
- **Files modified:** src/doxastica/backends/ladybug.py
- **Verification:** `test_five_primitives` asserts `matched[0]["status"]` (plain key) round-trips.
- **Committed in:** `d2ca1bd` (Task 2 commit)

**2. [Rule 3 - Blocking] core.py type-check broke once LadybugBackend types landed**
- **Found during:** Post-Task-2 full-project basedpyright
- **Issue:** With the real `LadybugBackend.__init__(conn: lb.Connection, ...)` resolvable, `core.from_connection` (which passes `conn: object` to stay driver-blind) raised `reportArgumentType`. The pre-existing forward-reference suppressions (`reportAttributeAccessIssue` etc.) were calibrated for when the module did not yet exist.
- **Fix:** Narrowed the suppression to the now-accurate `reportArgumentType` on the construction; refreshed the stale "unresolved until plan 02-02" comments. core.py stays driver-blind (no module-level ladybug import; importing it does not chain-load the driver, verified).
- **Files modified:** src/doxastica/core.py
- **Verification:** `basedpyright src/doxastica/core.py` → 0 errors; `tests/test_import_purity.py` passes; runtime check confirms `ladybug` not in `sys.modules` after importing core.
- **Committed in:** `79954e0`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking).
**Impact on plan:** Both necessary for correctness/build health. No scope creep — only `core.py` was touched beyond the plan's `files_modified`, and only to unbreak the type-check its own Plan-01 forward-references anticipated.

## Issues Encountered

### SC4 de-risking finding — value-opacity hazard (DEF-02-01)

The spike surfaced a real ladybug behavior NOT anticipated by RESEARCH (whose Code Examples claimed `'{"x":1}'` round-trips): **ladybug 0.17.1 parses a STRING parameter whose entire content is a valid Cypher struct/list literal and binds it as a STRUCT / LIST, not a STRING.** Stored into a STRING column it loses its JSON quotes (`'{"x": 2}'` → `'{x: 2}'`; `'[1, 2, 3]'` → `'[1,2,3]'`). Scalar JSON (string/number/bool) and any non-parseable content round-trip fine. Root cause confirmed via the binder error `+(STRING, STRUCT(x INT8))`; no driver-side typed-Value API exists in 0.17.1, `prepare()` is deprecated, and `cast(... AS STRING)` runs too late.

This violates BACK-04 §6 value opacity for exactly the JSON object/array values the core will store. It does NOT affect Phase 2 scope (no value-fidelity is asserted here — only ids/edges/traverse). **Deferred to the Phase 3 value-encoding contract** (the core owns value encoding per BACK-04 §6, explicitly out of Phase 2 scope). Full detail, evidence table, and candidate fixes in `deferred-items.md` (DEF-02-01). Recommendation: Plan 02-03's parity suite should add a value-round-trip case so the chosen Phase-3 fix is locked by a regression test.

### Pre-existing type errors (DEF-02-02)
`tests/test_backend_memory.py` (from Plan 02-01) has 3 `reportArgumentType` errors on `sorted(<generator of object>)`. Unchanged by this plan → out of scope (SCOPE BOUNDARY). Logged for a 02-01 follow-up / 02-03.

## Known Stubs
None. All five primitives are fully wired to LadybugDB and exercised by 15 passing tests.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: value-opacity | src/doxastica/backends/ladybug.py | ladybug coerces brace/bracket-shaped STRING params (DEF-02-01) — value opacity (T-02-02) is currently violated by driver inference, not interpolation. Mitigation deferred to the Phase 3 value-encoding contract. |

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The ladybug reference backend is stood up and confirmed against the real API. SC4 is CONFIRMED: the LPG-primitive port survives unchanged.
- **Plan 02-03 (parity suite) should:** (a) assert `(reached, frontier)` + `match_nodes` parity between LadybugBackend and InMemoryBackend on diamond/cycle/over-bound graphs; (b) add a value-round-trip case to pin DEF-02-01.
- **Phase 3 must resolve DEF-02-01** before writing real belief `value`s (the value-encoding contract). `HAS_REVISION` / `CURRENT_STATE` edge tables also arrive in Phase 3.

## Self-Check: PASSED

- FOUND: src/doxastica/backends/ladybug.py
- FOUND: tests/test_backend_ladybug.py
- FOUND: .planning/phases/02-.../02-02-SUMMARY.md
- FOUND: .planning/phases/02-.../deferred-items.md
- FOUND commits: 61bb504, d2ca1bd, 79954e0
- Verification: 46 tests pass; basedpyright 0 errors on ladybug.py/core.py/test_backend_ladybug.py; ruff clean.

---
*Phase: 02-backend-adapters-schema-bootstrap-de-risking-spike*
*Completed: 2026-06-15*
