---
phase: 09-stance-value-layer-write-persistence
plan: 01
subsystem: database
tags: [enum, total_ordering, pydantic, ladybug, stance, agm, value-layer]

# Dependency graph
requires:
  - phase: 03-belief-revision-spine
    provides: the _append/_append_state/_hydrate write spine, _encode_value/_decode_value codec, contract verbatim-value copy
  - phase: 01-protocol-backend-port-data-model-decisions
    provides: frozen BeliefState value layer, Status/EdgeType closed StrEnums, BeliefStore Protocol
provides:
  - Stance ordinal enum (plain Enum + total_ordering, doubted<suspected<believed<certain) — first ordered enum in the codebase
  - required stance field on the frozen BeliefState (six -> seven fields, no model-level default per D-01)
  - optional stance param defaulting to Stance.certain on revise/expand (core + Protocol)
  - stance threaded end-to-end write -> persist -> read on both backends (.name serialize / Stance[token] name-hydrate)
  - stance STRING column on the ladybug BeliefState NODE TABLE
affects: [09-02-stance-persistence-parity, phase-10-stance-oracle-widening, phase-10-cluedo-tutorial]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ordered enum idiom: plain Enum + functools.total_ordering + explicit integer rank + isinstance-guarded __lt__ returning NotImplemented"
    - ".name serialize / Stance[token] name-hydrate discipline (never value-lookup on the wire token)"
    - "Pre-serialized token threading: _append_state receives stance as an already-serialized str, mirroring encoded_value"

key-files:
  created:
    - tests/test_stance.py
  modified:
    - src/doxastica/models.py
    - src/doxastica/core.py
    - src/doxastica/protocol.py
    - src/doxastica/backends/ladybug.py
    - tests/test_models_frozen.py

key-decisions:
  - "Stance.__lt__ uses isinstance(other, Stance) (not self.__class__ is other.__class__) so basedpyright-strict narrows other.value — equivalent for a member-ful (unsubclassable) Enum and satisfies CONTEXT's compares-.value/returns-NotImplemented contract"
  - "protocol.py imports Stance at RUNTIME (models-only, import-purity safe) because the stance=Stance.certain default is a runtime expression evaluated at class-definition time even under `from __future__ import annotations`"
  - "SC2 arithmetic/cross-type test written as inline pytest.raises blocks (not lambda+parametrize) to avoid strict reportUnknownLambdaType / TC003 / SIM300 churn; narrow # pyright: ignore[reportOperatorIssue(, reportUnknownVariableType)] per line"

patterns-established:
  - "Ordinal taxonomy enum: total_ordering over a single isinstance-guarded __lt__; comparison is the only reachable operation (+/*/cross-type < raise TypeError by base-class choice, not guard code)"
  - "Name-token wire discipline for a value-ranked enum: serialize .name, hydrate Stance[token]; the write helper never interprets the token (D-02 Option A)"

requirements-completed: [STANCE-01, STANCE-02, STANCE-03, STANCE-04, STANCE-06]

# Metrics
duration: 8min
completed: 2026-07-04
---

# Phase 9 Plan 01: Stance Value Layer, Write & Persistence Summary

**Ordinal `Stance` enum (plain `Enum` + `total_ordering`) added as a required seventh `BeliefState` field and threaded write -> persist -> read on both backends with `certain` as the API default, via `.name`-serialize / `Stance[token]`-name-hydrate.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-07-04T20:04:27Z
- **Completed:** 2026-07-04T20:12:00Z
- **Tasks:** 2
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments
- Landed `Stance` — the first *ordered* enum in the codebase: plain `Enum` + `functools.total_ordering` + explicit integer rank `doubted=0 < suspected=1 < believed=2 < certain=3`, with an `isinstance`-guarded `__lt__` returning `NotImplemented` so `+`/`*`/cross-type `<`/`>` all raise `TypeError` (STANCE-06 satisfied by base-class choice, not guard code).
- Added `stance: Stance` as a REQUIRED seventh field on the frozen `BeliefState` (no model-level default, D-01).
- Threaded stance through the entire write spine: `_append_state` takes a pre-serialized token, `_append` serializes via `stance.name`, `revise`/`expand` gained `stance: Stance = Stance.certain` (STANCE-03), and `contract` copies `prior["stance"]` verbatim (STANCE-04, structural).
- `_hydrate` reconstructs via `Stance[props["stance"]]` name-lookup — dodging the phase's load-bearing trap (value-lookup on the `.name` token would `ValueError`).
- Added the `stance STRING` column to the ladybug `BeliefState` NODE TABLE; in-memory backend carries it free (schemaless).
- New `tests/test_stance.py` proves the total order, arithmetic/cross-type `TypeError`, and the name-lookup discipline. Full suite green on both backends (198 passed, 1 xfailed); full `prek run --all-files` green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Stance enum + required BeliefState field + SC2 unit proof** - `4560a89` (feat)
2. **Task 2: thread stance through core write spine, Protocol, ladybug DDL** - `3e971a1` (feat)
3. **Verification-gate fixes (basedpyright-strict on `__lt__` + SC2 test)** - `46519da` (fix)

_Note: the fix commit resolves strict-typing findings surfaced by the phase `prek` gate; both belong to Task 1 files._

## Files Created/Modified
- `src/doxastica/models.py` - Added `Stance` ordered enum (after `EdgeType`, before `Scope`); added required `stance: Stance` field on `BeliefState`; docstring six -> seven; imports `Enum` + `total_ordering`.
- `src/doxastica/core.py` - Imported `Stance`; `_hydrate` name-lookup reconstruction; `_append_state` pre-serialized token param + props; `_append` passes `stance.name`; `revise`/`expand` gained the default param; `contract` verbatim copy; get_impact doc six -> seven.
- `src/doxastica/protocol.py` - Runtime `Stance` import; `revise`/`expand` Protocol signatures gained `stance: Stance = Stance.certain`.
- `src/doxastica/backends/ladybug.py` - `stance STRING` column on the `{ns}_BeliefState` NODE TABLE DDL.
- `tests/test_stance.py` - NEW. SC2 total-order, arithmetic/cross-type `TypeError`, name-lookup guard, wire-token proofs.
- `tests/test_models_frozen.py` - Retargeted closed-six -> closed-seven; `stance=Stance.certain` on both direct `BeliefState(...)` constructors; `Stance` import.

## Decisions Made
- **`isinstance`-guarded `__lt__` over `self.__class__ is other.__class__`:** the verified recipe's class-identity check does not narrow `other` for basedpyright-strict (`other.value` errored). `isinstance(other, Stance)` is exactly equivalent for a member-ful `Enum` (which cannot be subclassed) and satisfies CONTEXT's "compares `.value`, returns `NotImplemented` for non-`Stance`" contract while keeping the strict gate green.
- **Runtime `Stance` import in protocol.py:** the plan specified importing `Stance` under `TYPE_CHECKING`, but `stance: Stance = Stance.certain` uses `Stance.certain` as a *default value* — a runtime expression evaluated when the `def` executes at class-definition time, even under `from __future__ import annotations` (which only defers the annotation). A `TYPE_CHECKING`-only import would raise `NameError` on import. A models-only runtime import is permitted by the import-purity guard (it forbids only `ladybug`).
- **SC2 test shape:** rewrote the plan's `lambda`+`parametrize` arithmetic test as inline `pytest.raises` blocks — the lambda form tripped `reportUnknownLambdaType` / `TC003` (via `Callable`) and ruff's `SIM300` rewrote a reflected comparison into a duplicate. Narrow per-line `# pyright: ignore[...]` codes adopted from the actual `prek` run (`reportOperatorIssue`, plus `reportUnknownVariableType` on the `+`/`*` lines whose result type is unknown).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] protocol.py `Stance` import moved from `TYPE_CHECKING` to runtime**
- **Found during:** Task 2 (Protocol signatures)
- **Issue:** The plan/PATTERNS instructed importing `Stance` under `TYPE_CHECKING`, but `stance: Stance = Stance.certain` evaluates `Stance.certain` at class-definition time — a `TYPE_CHECKING`-only import raises `NameError` on module import.
- **Fix:** Added a module-level runtime `from doxastica.models import Stance` (models-only; import-purity guard forbids only `ladybug`), removed `Stance` from the `TYPE_CHECKING` block.
- **Files modified:** src/doxastica/protocol.py
- **Verification:** `tests/test_import_purity.py` green; full suite imports and runs.
- **Committed in:** `3e971a1` (Task 2 commit)

**2. [Rule 1 - Bug] `Stance.__lt__` guard changed for basedpyright-strict**
- **Found during:** Phase `prek` gate (after Task 2)
- **Issue:** `self.__class__ is other.__class__` does not narrow `other: object`, so `other.value` produced `reportAttributeAccessIssue` / `reportUnknownMemberType` under strict typing — the CI-parity gate would fail.
- **Fix:** Switched to `isinstance(other, Stance)` (behaviorally identical for a member-ful, unsubclassable `Enum`); documented the equivalence inline.
- **Files modified:** src/doxastica/models.py
- **Verification:** `prek run --all-files` (basedpyright) green; `test_stance.py` total-order + TypeError proofs still pass.
- **Committed in:** `46519da` (fix commit)

**3. [Rule 3 - Blocking] SC2 arithmetic test restructured to satisfy strict + ruff**
- **Found during:** Phase `prek` gate (after Task 2)
- **Issue:** The `lambda`+`parametrize` shape tripped `reportUnknownLambdaType`, the `Callable` import tripped `TC003`, and ruff `SIM300` rewrote `5 < Stance.believed` into a duplicate line.
- **Fix:** Rewrote as inline `pytest.raises` blocks with narrow per-line `# pyright: ignore[...]` codes adopted from the actual run.
- **Files modified:** tests/test_stance.py
- **Verification:** `prek run --all-files` green; the four arithmetic/cross-type cases still assert `TypeError`.
- **Committed in:** `46519da` (fix commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All three are strict-typing / lint-gate reconciliations of the verified recipe against CI-parity `prek`; no behavioral or scope change. Open Q1 (exact basedpyright ignore code) resolved to `reportOperatorIssue` (+ `reportUnknownVariableType` on unknown-result lines), exactly as the research anticipated.

## Issues Encountered
- `uv sync --locked --dev --extra ladybug` emits a macOS-sandbox Tokio panic (known environment workaround, not a project fault); the ladybug extra was already synced, so ladybug backend tests ran and passed — dual-backend coverage confirmed.

## Known Stubs
None. No placeholder values, empty returns, or unwired data paths introduced. STANCE-05 (`get_scope_at` reconstruction) needs no code — `_hydrate` covers it; its dedicated proof lands in plan 09-02.

## Next Phase Readiness
- Write -> persist -> read threads stance end to end on both backends with `certain` as the default — the foundation ROADMAP SC4/SC5 stand on.
- Plan 09-02 adds `tests/test_stance_persistence.py` (dual-backend byte-stable round-trip, default-to-certain, contract-verbatim, get_scope_at reconstruction) — no further production code expected.

---
*Phase: 09-stance-value-layer-write-persistence*
*Completed: 2026-07-04*

## Self-Check: PASSED

All 6 touched source/test files and the SUMMARY exist on disk; all three task commits (`4560a89`, `3e971a1`, `46519da`) are present in the git log.
