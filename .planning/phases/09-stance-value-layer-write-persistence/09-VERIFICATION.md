---
phase: 09-stance-value-layer-write-persistence
verified: 2026-07-04T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
deferred:
  - truth: "Hypothesis property suite with oracle-widened stance tracking (STANCE-07)"
    addressed_in: "Phase 10"
    evidence: "REQUIREMENTS.md Traceability: STANCE-07 | Phase 10 | Pending"
  - truth: "Cluedo tutorial demonstrating epistemic gradient with stance (DOCS-01)"
    addressed_in: "Phase 10"
    evidence: "REQUIREMENTS.md Traceability: DOCS-01 | Phase 10 | Pending"
---

# Phase 9: Stance Value Layer / Write Persistence Verification Report

**Phase Goal:** The core stores and compares stance — a canonical ordinal `Stance` enum lands on `BeliefState`, is accepted on the write surface (optional, defaulting to `certain`), preserved verbatim by `contract`, reconstructed by `get_scope_at`, and round-trips byte-stable on both backends, with ordinal comparison the only reachable operation over the type.
**Verified:** 2026-07-04
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                                | Status     | Evidence                                                                                      |
|----|----------------------------------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------|
| 1  | `Stance` enum is plain `Enum` + `@total_ordering`; `doubted < suspected < believed < certain`; every pair ordered   | VERIFIED   | `models.py:65-98`; `test_stance.py::test_stance_total_order` passes                          |
| 2  | Arithmetic and cross-type comparison raise `TypeError`; no core path uses arithmetic on stance                      | VERIFIED   | `test_stance.py::test_stance_arithmetic_and_cross_type_raise` passes (4 TypeError proofs); no `+`/`*`/int-compare on `Stance` in production code |
| 3  | `BeliefState` carries exactly 7 fields including required `stance`; `revise`/`expand` default to `Stance.certain`   | VERIFIED   | `models.py:120-141`; `core.py:364-397`; `protocol.py:77-96`; `test_models_frozen.py::test_belief_state_field_set_is_the_closed_seven` |
| 4  | Stance round-trips byte-stable through `query_scope` on BOTH backends via `.name` serialization                    | VERIFIED   | `core.py:282,359` (`Stance[props["stance"]]` + `stance.name`); 8/8 tests pass (4×2 backends) |
| 5  | `contract` preserves prior stance verbatim; `get_scope_at` reconstructs stance unchanged                           | VERIFIED   | `core.py:443` (`prior["stance"]` verbatim); `get_scope_at` delegates to `_hydrate`; persistence tests pass on both backends |

**Score:** 5/5 truths verified

### Deferred Items

Items not yet met but explicitly addressed in later milestone phases.

| # | Item                                                    | Addressed In | Evidence                                                            |
|---|---------------------------------------------------------|-------------|---------------------------------------------------------------------|
| 1 | STANCE-07 Hypothesis oracle-widened property suite      | Phase 10    | REQUIREMENTS.md Traceability: `STANCE-07 | Phase 10 | Pending`     |
| 2 | DOCS-01 Cluedo tutorial with stance epistemic gradient  | Phase 10    | REQUIREMENTS.md Traceability: `DOCS-01 | Phase 10 | Pending`       |

### Required Artifacts

| Artifact                                       | Expected                                                   | Status   | Details                                                                        |
|------------------------------------------------|------------------------------------------------------------|----------|--------------------------------------------------------------------------------|
| `src/doxastica/models.py`                      | Stance ordered enum + stance field on BeliefState          | VERIFIED | `class Stance(Enum)` at line 66, `@total_ordering` at line 65, `stance: Stance` field at line 140 (no default) |
| `src/doxastica/core.py`                        | Write-spine threading + name-lookup hydrate                | VERIFIED | `Stance[props["stance"]]` at line 282; `stance.name` at line 359; `prior["stance"]` at line 443 |
| `src/doxastica/protocol.py`                    | revise/expand signatures gain stance param                 | VERIFIED | `stance: Stance = Stance.certain` on both `revise` (line 83) and `expand` (line 94) |
| `src/doxastica/backends/ladybug.py`            | BeliefState NODE TABLE gains stance STRING column          | VERIFIED | `stance STRING` at line 234 in `_bootstrap_schema` DDL                        |
| `tests/test_stance.py`                         | SC2 type-level order + arithmetic TypeError + name-lookup  | VERIFIED | 65 lines (>30 min); 5 tests all pass; total-order, arithmetic/cross-type, name-lookup guard all present |
| `tests/test_models_frozen.py`                  | Closed-seven field assertion; constructors pass stance=    | VERIFIED | `test_belief_state_field_set_is_the_closed_seven` at line 61; `stance=Stance.certain` in `_make_belief_state` and unknown-field test |
| `tests/test_stance_persistence.py`             | SC4/SC5 dual-backend parity proof parametrized on backend  | VERIFIED | 103 lines (>40 min); `backend: BackendPort` fixture; 4 tests × 2 backends = 8 passing |

### Key Link Verification

| From                              | To                                    | Via                                          | Status   | Details                                               |
|-----------------------------------|---------------------------------------|----------------------------------------------|----------|-------------------------------------------------------|
| `core.py _hydrate`                | `models.py Stance`                    | `Stance[props["stance"]]` name-lookup        | WIRED    | Line 282; `# NAME-lookup — NOT Stance(props[...])` comment confirms the critical divergence from Status |
| `core.py _append`                 | `_append_state` stance token          | `stance.name` at write boundary              | WIRED    | Line 359; mirrors `_encode_value(value)` serialize-once discipline |
| `core.py contract`                | `_append_state`                       | `prior["stance"]` verbatim copy              | WIRED    | Line 443; comment `STANCE-04: copy the stored stance token VERBATIM` |
| `backends/ladybug.py DDL`         | core.py props dict stance key         | `stance STRING` column                       | WIRED    | Line 234; DDL bootstrap includes `stance STRING` in `{ns}_BeliefState` CREATE TABLE |
| `tests/test_stance_persistence.py`| `MemoryCore(backend)` via conftest    | parametrized dual-backend (memory + ladybug) | WIRED    | `backend: BackendPort` fixture from conftest.py `params=["memory","ladybug"]`; `importorskip` for absent driver |
| `tests/test_stance_persistence.py`| `query_scope / get_scope_at`          | `state.stance is Stance.<member>` assertions | WIRED    | Member-identity assertions at lines 54, 57, 70, 85, 86, 100 |

### Data-Flow Trace (Level 4)

The core is a library with no rendered components; data flow is through the write→persist→read pipeline verified by tests.

| Artifact                   | Data Variable | Source                    | Produces Real Data | Status    |
|----------------------------|---------------|---------------------------|--------------------|-----------|
| `core.py _hydrate`         | `stance`      | `props["stance"]` from backend `match_nodes` | Yes — `stance.name` written via `_append_state`; `Stance[token]` reconstructs | FLOWING   |
| `core.py contract`         | `stance`      | `prior["stance"]` verbatim token | Yes — verbatim copy of stored token, no decode/re-encode | FLOWING   |
| `backends/ladybug.py`      | `stance STRING` column | DDL + `$param`-bound `upsert_node` SET | Yes — `stance` flows through props dict as `stance.name` token | FLOWING   |

### Behavioral Spot-Checks

| Behavior                                                           | Command                                                          | Result         | Status |
|--------------------------------------------------------------------|------------------------------------------------------------------|----------------|--------|
| Stance total order + arithmetic TypeError + name-lookup discipline | `uv run pytest tests/test_stance.py tests/test_models_frozen.py -x -q` | 16 passed in 0.43s | PASS |
| Stance byte-stable round-trip + contract/get_scope_at on both backends | `uv run pytest tests/test_stance_persistence.py -x -q`     | 8 passed in 0.39s (4 tests × 2 backends) | PASS |

### Probe Execution

No conventional probe scripts (`scripts/*/tests/probe-*.sh`) exist for this phase. Behavioral spot-checks above serve as the executable proof. SKIPPED (no probe scripts).

### Requirements Coverage

| Requirement | Source Plan | Description                                              | Status    | Evidence                                                                 |
|-------------|-------------|----------------------------------------------------------|-----------|--------------------------------------------------------------------------|
| STANCE-01   | 09-01       | Canonical `Stance` enum with total order, plain Enum     | SATISFIED | `models.py:65-98`; `test_stance.py::test_stance_total_order` passes      |
| STANCE-02   | 09-01       | `BeliefState` gains required `stance: Stance` (7th field) | SATISFIED | `models.py:140`; `test_models_frozen.py::test_belief_state_field_set_is_the_closed_seven` |
| STANCE-03   | 09-01/09-02 | Write surface accepts optional stance defaulting to `certain`; byte-stable both backends | SATISFIED | `core.py:370,387`; `protocol.py:83,94`; `test_stance_persistence.py` 8/8 pass |
| STANCE-04   | 09-01/09-02 | `contract` preserves prior stance verbatim              | SATISFIED | `core.py:443`; `test_stance_persistence.py::test_contract_preserves_stance_verbatim` |
| STANCE-05   | 09-02       | `get_scope_at` reconstructs stance unchanged            | SATISFIED | `_hydrate` called at `core.py:704`; `test_stance_persistence.py::test_get_scope_at_reconstructs_stance` |
| STANCE-06   | 09-01       | Arithmetic/cross-type TypeError; no core arithmetic     | SATISFIED | `test_stance.py::test_stance_arithmetic_and_cross_type_raise`; no `+`/`*`/int-`<` in production code |
| STANCE-07   | —           | Hypothesis oracle-widened property suite (Phase 10)     | DEFERRED  | Traceability: Phase 10, Pending                                          |
| DOCS-01     | —           | Cluedo tutorial demonstrating stance (Phase 10)         | DEFERRED  | Traceability: Phase 10, Pending                                          |

### Anti-Patterns Found

No blocking anti-patterns detected. Scanned all 7 phase-modified files for TBD/FIXME/XXX (zero matches), TODO/PLACEHOLDER (none in production code), empty returns, hardcoded empty data, and stub patterns.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | — |

### Human Verification Required

None. All phase 9 deliverables are mechanically verifiable and the behavioral spot-checks pass. No visual, real-time, or external-service behaviors introduced.

### Gaps Summary

No gaps. All five ROADMAP success criteria are satisfied by substantive, wired production code and passing tests on both backends. STANCE-07 and DOCS-01 are Phase 10 work explicitly tracked in REQUIREMENTS.md — not gaps for this phase.

---

_Verified: 2026-07-04_
_Verifier: Claude (gsd-verifier)_
