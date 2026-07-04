---
phase: 03-append-only-revision-spine-keystone
plan: 02
subsystem: core
tags: [agm, belief-revision, uuid7, json, base64, ladybug, pydantic, append-only]

# Dependency graph
requires:
  - phase: 03-01
    provides: WORLD_SCOPE_ID export, HAS_REVISION ladybug hub REL table, add_edge per-edge-type endpoint resolution
  - phase: 03-03
    provides: tests/test_revision_spine.py Wave-0 behavior scaffold (RED until these op bodies land)
  - phase: 02
    provides: BackendPort 5 LPG primitives (upsert_node/add_edge/match_nodes/traverse/unit_of_work) on both backends, MemoryCore factories, driver-blind import discipline
provides:
  - MemoryCore.get_or_create_scope (reserved-id rule, derived is_world, idempotent)
  - MemoryCore._ensure_scope / _current (DERIVED current, no CURRENT_STATE pointer) / _hydrate
  - MemoryCore._append shared revise/expand body (D-04)
  - MemoryCore.revise / expand / contract / get_revision_chain
  - DEF-02-01 value-encoding contract (base64-over-JSON, byte-identical on both backends)
affects: [04-query-scope-matrix, 05-add-edge-get-impact, 06-get-scope-at, 07-agm-conformance-suite]

# Tech tracking
tech-stack:
  added: [stdlib base64 (value encoding), stdlib json + uuid (already in-tree)]
  patterns:
    - "Encode-once-on-write / decode-on-hydrate value boundary lives in core.py, applied identically to both backends (oracle stays value-verbatim, parity preserved)"
    - "DERIVED current as ordering-max over immutable append-only states — zero mutable store elements (D-01)"
    - "Structural pre-backend guard (world-scope contract) fires before any unit_of_work"
    - "Structural edges (HAS_REVISION/SUPERSEDES) passed to add_edge as RAW STRINGS, never EdgeType members (D-07)"

key-files:
  created: []
  modified:
    - src/doxastica/core.py

key-decisions:
  - "DEF-02-01 closed via base64-over-JSON (not bare json.dumps): ladybug's STRING column coerces any brace/bracket-shaped literal, dropping inner quotes — base64 yields a non-brace token both backends store verbatim"
  - "expand implemented as an explicit one-line delegate to _append (not a bare `expand = revise` class-body alias) to keep the basedpyright-strict bound-method type"
  - "current is DERIVED (ordering-max over active states); no CURRENT_STATE pointer stored (D-01)"

patterns-established:
  - "Value codec at the core↔port boundary: _encode_value/_decode_value static helpers, single encode on write, verbatim copy on contract (no double-encode)"
  - "Per-write atomicity: each public write opens EXACTLY one unit_of_work; prior current computed BEFORE the new append"

requirements-completed: [SCOPE-01, SCOPE-02, SCOPE-03, CHAIN-01, CHAIN-02, CHAIN-03, OPS-01, OPS-02, OPS-03, HIST-02]

# Metrics
duration: 6min
completed: 2026-06-15
---

# Phase 3 Plan 02: Append-Only Revision Spine Op Bodies Summary

**The AGM write spine on MemoryCore — derived-current selection, revise≡expand append, world-scope-guarded contract, and an ordered immutable revision chain — composing only the five BackendPort primitives and running byte-identically on the in-memory oracle and the ladybug reference backend.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-06-15T23:44:24Z
- **Completed:** 2026-06-15T23:49:44Z
- **Tasks:** 2
- **Files modified:** 1 (src/doxastica/core.py)

## Accomplishments
- `get_or_create_scope` + `_ensure_scope`: reserved-id rule, `is_world` derived in the core (never trusts the stored column — Pitfall 4), idempotent.
- `_current`: the single place the UUID7 ordering contract `(source_event_id, state_id)` lives — DERIVED ordering-max active state per exact `(scope, belief)`, no stored `CURRENT_STATE` pointer (D-01), enforcing cross-scope divergence (SCOPE-03).
- `_append` shared body (D-04): one `unit_of_work`, auto-create scope + `Belief` (D-06), `prior` computed BEFORE the append (Pitfall 3), `uuid.uuid7()` `state_id`, `HAS_REVISION` hub edge + conditional `SUPERSEDES new→prior`, all as raw-string edge types (D-07).
- `revise` / `expand` (mechanically identical, D-04) / `contract` (structural `WORLD_SCOPE_ID` guard first per D-03, vacuity→None per D-05, retracted state copying the stored value verbatim per Pitfall 2) / `get_revision_chain` (cross-scope, ordered, HIST-02).
- Closed DEF-02-01 (T-03-03 brace-coercion): the opaque value round-trips byte-identically on BOTH backends, including `{"x": 2}` and `{"nested": [1,2,3]}`.

## Task Commits

1. **Task 1: scope + derived-current + hydrate helpers** - `d90badd` (feat)
2. **Task 2: revise/expand/contract + get_revision_chain ops (incl. base64 value-codec fix)** - `f40a8ec` (feat)

_TDD note: the RED scaffold (`tests/test_revision_spine.py`) was delivered by plan 03-03; this plan implemented the bodies to GREEN. Per-task verification confirmed RED→GREEN at each step._

## Files Created/Modified
- `src/doxastica/core.py` - Added the Phase-3 AGM op bodies and helpers on `MemoryCore`; added stdlib `base64`/`json`/`uuid` imports, runtime `WORLD_SCOPE_ID`/`BeliefState`/`Scope`/`Status` + `WorldScopeContractionError` imports; updated the module docstring. Stays driver-blind (no module-level `ladybug` import).

## Decisions Made
- **DEF-02-01 value codec changed from bare `json.dumps` to base64-over-JSON.** The plan/PATTERNS prescribed `value: json.dumps(value)` / `json.loads`, asserting that single-encode closes DEF-02-01. Empirically the ladybug `STRING` column silently coerces any value whose string *starts* with `{` or `[` (it parses the literal as a STRUCT/LIST and re-stringifies, dropping inner quotes/spaces) — so `json.dumps({"x":2})` = `'{"x": 2}'` came back as `'{x: 2}'` and crashed `json.loads`. base64 produces an alnum/`+/=` token that never starts with a brace, so both the ladybug column and the in-memory oracle store it verbatim and decode identically. The encode/decode boundary still lives in `core.py` (not the adapters), single-encode on write, verbatim copy on contract — fully honoring the contract's intent (byte-identical round-trip on both backends, no double-encode).
- **`expand` is an explicit one-line delegate, not a `expand = revise` class-body alias.** The PATTERNS sketch offered the alias as the preferred form with the delegate as fallback; the delegate keeps the basedpyright-strict bound-method type and an explicit signature matching `protocol.py`, so both names stay first-class on the public surface.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] DEF-02-01 brace-coercion round-trip failure on the ladybug backend**
- **Found during:** Task 2 (revise/contract bodies)
- **Issue:** The plan's prescribed `value: json.dumps(value)` / `value=json.loads(props["value"])` encoding does NOT survive the ladybug `STRING` column. Ladybug coerces any stored string that starts with `{` or `[`, parsing it as a STRUCT/LIST and re-stringifying without the inner double-quotes (`'{"x": 2}'` → `'{x: 2}'`). The plan's own acceptance tests `test_brace_value_round_trips[ladybug]` and `test_retracted_value_byte_identical_to_superseded[ladybug]` failed with `JSONDecodeError` — exactly the inherited T-03-03 corruption the DEF-02-01 contract exists to close.
- **Fix:** Introduced `MemoryCore._encode_value` (base64-over-JSON) and `_decode_value` (base64-decode then `json.loads`) static helpers; `_append` encodes once on write, `_hydrate` decodes on read, `contract` still copies the already-encoded stored token verbatim (no double-encode). Applied identically on both backends so the stored form is byte-identical everywhere and the in-memory oracle stays value-verbatim (parity preserved). Encode/decode boundary remains in `core.py`, not the adapters.
- **Files modified:** src/doxastica/core.py
- **Verification:** `tests/test_revision_spine.py` 22/22 pass on both backends; full suite 102 passed / 1 xfailed (the pre-existing bare-port DEF-02-01 xfail, owned by the parity test, out of scope here); brace one-liner passes on the base pydantic-only install.
- **Committed in:** f40a8ec (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — DEF-02-01 round-trip correctness).
**Impact on plan:** The fix is required for the plan's own acceptance gate and the DEF-02-01/T-03-03 mitigation to actually hold. It preserves the contract's stated invariants (single encode on write, verbatim copy on contract, identical on both backends, boundary in core.py) and adds no runtime dependency (stdlib `base64`). No scope creep.

## Issues Encountered
- Acceptance-criterion grep `grep -c 'import ladybug' src/doxastica/core.py` returns 3, not 0: those are a docstring NOTE comment plus the two pre-existing **function-local** `from doxastica.backends import ladybug` imports in the `open`/`from_connection` factories (sanctioned by D-02, untouched by this plan). The authoritative driver-blindness gate is `tests/test_import_purity.py` (a module-level AST scan that permits function-local imports), which passes — core.py adds no module-level driver import.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The keystone spine is GREEN on both backends: Phase 4 (`query_scope` + deprecated/superseded matrix), Phase 5 (`add_edge`/`get_impact`), and Phase 6 (`get_scope_at`) can now compose on it.
- `SUPERSEDES` edges are laid on every displacement (read by Phase 4, traversed by Phase 5); `HAS_REVISION` chains + the derived-current ordering contract are in place.
- Forward note for downstream backends: the value codec (base64-over-JSON) lives in `core.py` and applies uniformly, so any future backend behind `BackendPort` inherits the brace-coercion-proof round-trip for free.

## Threat Flags

None — no new security surface beyond the plan's `<threat_model>`. T-03-03 (value round-trip integrity) is mitigated as planned (now via base64-over-JSON); the core writes no Cypher and never eval's the value.

## Self-Check: PASSED

- FOUND: src/doxastica/core.py
- FOUND: .planning/phases/03-append-only-revision-spine-keystone/03-02-SUMMARY.md
- FOUND commit: d90badd
- FOUND commit: f40a8ec

---
*Phase: 03-append-only-revision-spine-keystone*
*Completed: 2026-06-15*
