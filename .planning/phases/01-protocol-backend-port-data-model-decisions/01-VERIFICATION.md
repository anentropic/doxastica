---
phase: 01-protocol-backend-port-data-model-decisions
verified: 2026-06-14T00:00:00Z
status: passed
score: 11/11 must-haves verified
overrides_applied: 0
human_verification: []
resolution:
  - item: "WR-01 — closed models lacked extra='forbid'"
    resolved: "Owner chose to harden now. Added extra='forbid' to all five frozen pydantic models (commit c3a5a3b); BeliefFilter/BeliefState now raise ValidationError on unknown kwargs — the 'triple-structure leak unrepresentable' claim is mechanical, not aspirational. Rejection tests added (test_belief_filter_rejects_unknown_field, test_belief_state_rejects_unknown_field)."
    expected: "Construction with an unknown kwarg should raise ValidationError if extra='forbid' were set; currently it silently discards (per 01-REVIEW.md WR-01). Human decision: accept the current behaviour as an advisory gap for this phase, or treat it as a blocker requiring a fix before closing Phase 1."
  - item: "WR-03 — ImpactResult.reached was a mutable list inside a frozen model"
    resolved: "Owner chose to fix now. Changed reached to tuple[BeliefState, ...] (commit c3a5a3b); the frozen guarantee is now complete. Test test_impact_result_reached_is_an_immutable_tuple added."
    expected: "ImpactResult.reached is typed list[BeliefState], making the frozen guarantee incomplete — result.reached.append(...) succeeds. Human decision: accept the mutable list as a Phase 1 advisory (fix before Phase 5 when get_impact produces real results), or treat as a blocker requiring tuple[BeliefState, ...] now."
---

# Phase 01: Protocol / Backend-Port / Data-Model Decisions — Verification Report

**Phase Goal:** A typed, basedpyright-strict foundation with TWO explicit seams — the public `BeliefStore` Protocol and, below it, the internal backend port the backend-agnostic core writes against — plus the decision-grade data-model choices settled before any storage code exists. Reversing any of these (including the port's granularity) would be a rewrite.
**Verified:** 2026-06-14T00:00:00Z
**Status:** passed
**Re-verification:** Yes — WR-01 and WR-03 hardened (commit c3a5a3b), both flagged items resolved; 16/16 tests green, basedpyright strict 0 errors, ruff clean.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `protocol.py` imports only `pydantic`/`typing`/`uuid` and `doxastica.models` — never `ladybug` | VERIFIED | Actual import lines are `from __future__ import annotations`, `from typing import TYPE_CHECKING, Any, Protocol`, and under `TYPE_CHECKING`: `from uuid import UUID` and `from doxastica.models import ...`. No `import ladybug` present. The AST guard in `test_import_purity.py` passes (13/13 green). |
| 2 | `BeliefStore` is a `typing.Protocol` whose `query_scope` takes a `BeliefFilter`, never a free `str` | VERIFIED | `class BeliefStore(Protocol)` at line 42 of `protocol.py`; `query_scope` signature at line 111–116 takes `filter: BeliefFilter` explicitly. Pattern confirmed. |
| 3 | `get_impact` returns `ImpactResult` with `depth: int | None = None` (unbounded default) | VERIFIED | `protocol.py` line 133: `depth: int | None = None`. Return type is `ImpactResult`. |
| 4 | UUID7 ordering contract for `source_event_id` is written into the source as a docstring/contract note | VERIFIED | `protocol.py` lines 51 and 158 both contain the exact text `(source_event_id byte-order, state_id tiebreak)`. Written on the class docstring AND the `get_scope_at` method docstring. |
| 5 | Public surface is re-exported from `doxastica/__init__.py` `__all__` | VERIFIED | `__all__` contains `['Belief', 'BeliefFilter', 'BeliefState', 'BeliefStore', 'DoxasticaError', 'EdgeType', 'ImpactResult', 'Scope', 'Status', 'WorldScopeContractionError']` — confirmed by `uv run python -c "import doxastica; print(doxastica.__all__)"`. All names importable. |
| 6 | The internal backend port is a distinct `typing.Protocol`, separate from `BeliefStore` | VERIFIED | `class BackendPort(Protocol)` in `ports.py:56`; `class BeliefStore(Protocol)` in `protocol.py:42`. They are distinct classes in distinct modules. `test_port_distinct.py` asserts `BackendPort is not BeliefStore` — passes. |
| 7 | The port exposes only LPG primitives — no `run`/`query`/`execute` method taking a query string | VERIFIED | `grep -rn "def run\|def query\|def execute" ports.py` returns empty. Five primitives present: `upsert_node`, `add_edge`, `match_nodes`, `traverse`, `unit_of_work`. `test_port_distinct.py` asserts no forbidden names — passes. |
| 8 | `traverse` is the single generic graph-walk primitive returning `(reached, frontier)` | VERIFIED | `ports.py` line 96: `def traverse(self, start, edge_types, max_depth) -> tuple[list[dict[str, Any]], frozenset[UUID]]`. Single graph-walk. No other traversal method exists. Module docstring records the named tension for Phase 2 spike. |
| 9 | `docs/backend-contract.md` enumerates the constraints a third-party LPG backend must meet | VERIFIED | File exists (90 lines); `grep -c "^## "` returns 7. Seven `##` constraint sections: 1. Data model, 2. Primitive operation semantics, 3. Uniqueness, 4. Append-only safety, 5. Ordering left to the core, 6. Value opacity, 7. Conformance. |
| 10 | Every model is frozen — mutating any field after construction raises | VERIFIED (with WR-03 advisory) | All 5 models use `BaseModel, frozen=True`: `Scope`, `Belief`, `BeliefState`, `BeliefFilter`, `ImpactResult`. Field re-assignment raises `pydantic.ValidationError` (8 tests pass). Advisory: `ImpactResult.reached: list[BeliefState]` is a mutable container inside a frozen model — field re-assignment is blocked, but `result.reached.append(...)` is not. See WR-03. |
| 11 | `BeliefFilter` closed-field "unrepresentable leak" claim is mechanically enforced by construction | UNCERTAIN — WR-01 | `BeliefFilter` is `frozen=True` with exactly four fields. However, pydantic default `extra="ignore"` means unknown constructor kwargs are silently discarded, not rejected. The docstring claim "makes a triple-structure leak unrepresentable" is aspirational under current defaults. `extra="forbid"` would make it mechanical. 01-REVIEW.md WR-01 confirms this. Human decision required. |

**Score:** 9/11 truths verified (10 with advisory acceptance, pending human decision on WR-01 and WR-03)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | Package metadata, runtime deps, dev hypothesis, `requires-python >=3.14`, basedpyright strict + ruff config | VERIFIED | `requires-python = ">=3.14"`, `dependencies = ["pydantic>=2.11,<3", "ladybug>=0.17,<0.18"]`, `hypothesis>=6.155` in dev group, `[tool.pyright]` strict with `pythonVersion = "3.14"`, ruff `target-version = "py314"`. |
| `src/doxastica/__init__.py` | Public re-export barrel with `__all__` | VERIFIED | 10-symbol `__all__` with matching `from .module import` statements. All resolve. |
| `src/doxastica/py.typed` | PEP 561 type marker | VERIFIED | File exists at path. |
| `src/doxastica/models.py` | Frozen pydantic v2 models: `Scope`, `Belief`, `BeliefState`, `BeliefFilter`, `ImpactResult`; `Status` + `EdgeType` enums | VERIFIED | 122 lines. All 5 models with `frozen=True`, 2 `StrEnum` taxonomies. `contains: "class BeliefState(BaseModel, frozen=True)"` — confirmed. |
| `src/doxastica/errors.py` | `DoxasticaError` base + `WorldScopeContractionError` | VERIFIED | Both classes present with docstrings. |
| `src/doxastica/protocol.py` | Public `BeliefStore typing.Protocol` — ladybug-free | VERIFIED | 164 lines. `class BeliefStore(Protocol)`, 9 methods, no `ladybug` import. |
| `src/doxastica/ports.py` | Internal `BackendPort(Protocol)` — LPG-primitive only | VERIFIED | 115 lines. `class BackendPort(Protocol)`, 5 primitives, no query-string method. |
| `docs/backend-contract.md` | 7-constraint port contract spec | VERIFIED | 90 lines, 7 `##` sections, all constraints enumerated. |
| `tests/test_import_purity.py` | DATA-01 guard — AST scan, no `ladybug` in `protocol.py` | VERIFIED | AST-walks full tree including `TYPE_CHECKING` blocks. Passes. |
| `tests/test_models_frozen.py` | DATA-05/DATA-06 guards: frozen-ness, enum membership, closed field sets | VERIFIED | 8 tests, all pass. Asserts frozen-ness, `Status`/{`active`,`retracted`} membership, `EdgeType`/{3 types} membership, structural-edge exclusion, 6-field `BeliefState` set, 4-field `BeliefFilter` set, `ImpactResult` constructibility. |
| `tests/test_port_distinct.py` | BACK-01 guard — port is separate, primitives-only | VERIFIED | 3 tests: distinctness from `BeliefStore`, no forbidden names, exactly 5 primitives. All pass. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pyproject.toml` | `ladybug + pydantic` | `dependencies` array | VERIFIED | `ladybug>=0.17,<0.18` and `pydantic>=2.11,<3` present; `ladybugdb` token absent (grep returns empty). |
| `src/doxastica/protocol.py` | `doxastica.models` | `from doxastica.models import ...` under `TYPE_CHECKING` | VERIFIED | TYPE_CHECKING-guarded imports: `BeliefFilter`, `BeliefState`, `EdgeType`, `ImpactResult`, `Scope`. Pattern `from doxastica.models import` confirmed. |
| `src/doxastica/protocol.py` | `BeliefFilter (not str)` | `query_scope` signature | VERIFIED | `filter: BeliefFilter` at line 114. No free `str` parameter. |
| `src/doxastica/ports.py` | `traverse` primitive | single generic graph-walk method | VERIFIED | `def traverse` at line 96 with `(reached, frontier)` tuple return. |

---

### Data-Flow Trace (Level 4)

Not applicable. This is a zero-storage-code, decision-grade phase. All artifacts are Protocol skeletons (ellipsis bodies) and value-object models. No dynamic data flows exist to trace. Skip per verification context instructions.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite (13 tests) passes | `UV_NO_SYNC=1 uv run pytest -q` | `13 passed in 0.16s` | PASS |
| basedpyright strict — 0 errors | `UV_NO_SYNC=1 uv run basedpyright` | `0 errors, 0 warnings, 0 notes` | PASS |
| ruff lint — all checks passed | `UV_NO_SYNC=1 uv run ruff check .` | `All checks passed!` | PASS |
| `doxastica` importable; `__all__` populated | `uv run python -c "import doxastica; print(doxastica.__all__)"` | 10-symbol list printed | PASS |

---

### Probe Execution

No probes defined or applicable for this decision-grade phase. Step 7c: SKIPPED.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DATA-01 | 01-03 | `BeliefStore` Protocol imports only `pydantic`/`typing`/`uuid`, never `ladybug` | SATISFIED | `protocol.py` imports verified; `test_import_purity.py` AST guard passes. |
| DATA-02 | 01-02, 01-03 | `query_scope` takes a closed typed `BeliefFilter`, never a free `str` | SATISFIED | `BeliefFilter` with 4 closed fields exists; `query_scope(filter: BeliefFilter)` in Protocol confirmed. Advisory: `extra="ignore"` makes the construction boundary aspirational (WR-01). |
| DATA-03 | 01-03 | UUID7 ordering contract for `source_event_id` written into source | SATISFIED | Contract text `(source_event_id byte-order, state_id tiebreak)` present in `protocol.py` at lines 51 and 158. |
| DATA-04 | 01-02, 01-03 | `get_impact` return shape carries `frontier` + `truncated` signal; `depth` default ratified | SATISFIED | `ImpactResult` has `reached`, `frontier`, `truncated`; `get_impact(depth: int | None = None)` confirmed. |
| DATA-05 | 01-02, 01-03 | Beliefs modelled as finite belief bases — no DL/OWL inference | SATISFIED | `BeliefState` closed 6-field set with no inference/deductive machinery; asserted by `test_models_frozen.py`. |
| DATA-06 | 01-02 | Frozen pydantic v2 models for `Scope`, `BeliefState`; `EdgeType` enum; opaque `value: Any`; opaque UUID7 `source_event_id` | SATISFIED | All models `frozen=True`, `StrEnum` taxonomies, `value: Any`, `source_event_id: UUID` present. |
| PKG-01 | 01-01 | Scaffolded from `cookiecutter-python-uv-library`; import name `doxastica` | SATISFIED | Package scaffold present; `pyproject.toml` metadata correct; basedpyright strict + ruff clean; 13 tests pass. |
| BACK-01 | 01-04 | Backend-agnostic core above a defined backend port; port granularity decided (LPG-primitive) | SATISFIED | `BackendPort(Protocol)` in `ports.py` distinct from `BeliefStore`; LPG-primitive granularity decision recorded in module docstring; round-trip tension named and deferred to Phase 2 spike. |
| BACK-04 | 01-04 | Backend port contract documented for third-party backend authors | SATISFIED | `docs/backend-contract.md` exists, 90 lines, 7 `##` constraint sections covering all required aspects. |

**All 9 Phase-1 requirement IDs satisfied.** No orphaned requirements found (REQUIREMENTS.md traceability table assigns DATA-01..06, PKG-01, BACK-01, BACK-04 exclusively to Phase 1).

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/doxastica/models.py` | all models | No `extra="forbid"` on any frozen model | WARNING (WR-01) | The "triple-structure leak unrepresentable by construction" docstring claim is aspirational, not mechanical. Unknown constructor kwargs are silently discarded under pydantic default `extra="ignore"`. See 01-REVIEW.md WR-01 for full analysis. |
| `src/doxastica/models.py` | 120 | `reached: list[BeliefState]` in frozen `ImpactResult` | WARNING (WR-03) | A mutable `list` inside a `frozen=True` model — field reassignment is blocked but `result.reached.append(...)` is not. Inconsistent with `frontier: frozenset[UUID]` on the same model. See 01-REVIEW.md WR-03. |

No `TBD`, `FIXME`, or `XXX` markers found in any Phase 1 source file (confirmed by search). No unreferenced debt markers exist. Warnings are not blockers under the verification context: the phase is decision-grade and zero-storage; WR-01 and WR-03 are quality gaps that matter when real data flows (Phase 3+).

---

### Human Verification Required

#### 1. WR-01: Accept or fix `extra="ignore"` on closed models

**Test:** In a Python session with the venv active, run:
```python
from uuid import uuid7
from doxastica.models import BeliefState, Status
from pydantic import ValidationError
try:
    s = BeliefState(state_id=uuid7(), belief_id="b", scope_id="s",
                    source_event_id=uuid7(), value=1, status=Status.active,
                    provenance="leaked")
    print("SILENT DISCARD — extra='ignore' active:", s.model_fields_set)
except ValidationError:
    print("REJECTED — extra='forbid' active")
```
**Expected:** Current code prints SILENT DISCARD. With `extra="forbid"` it would raise `ValidationError`.
**Why human:** Whether to fix this now (add `extra="forbid"` to all frozen models) or accept it as a Phase 1 advisory is a design policy call. The 01-REVIEW.md WR-01 fix is straightforward (`ConfigDict(frozen=True, extra="forbid")`) but changes the model surface and requires updating at least one test assertion. The project owner must decide if the aspirational docstring wording is acceptable for Phase 1 or must be hardened before Phase 1 closes.

#### 2. WR-03: Accept or fix `ImpactResult.reached` as mutable list

**Test:** In a Python session:
```python
from doxastica.models import ImpactResult
result = ImpactResult(reached=[], frontier=frozenset(), truncated=False)
result.reached.append("mutated")  # This should fail if immutability is real
print("reached after append:", result.reached)  # Prints ['mutated'] — mutable!
```
**Expected:** Currently `result.reached.append(...)` succeeds (mutable list). With `tuple[BeliefState, ...]` it would raise `AttributeError`.
**Why human:** Whether the mutable list inside a frozen model is acceptable for a zero-storage Phase 1 is a design policy call. The field is only meaningful when `get_impact` returns real cascade results (Phase 3+). The 01-REVIEW.md WR-03 fix (`tuple[BeliefState, ...]`) would require updating the test asserting `result.reached == []` to `result.reached == ()`.

---

### Gaps Summary

No hard blockers found. The two human verification items are quality advisories surfaced by the code review (01-REVIEW.md WR-01, WR-03), not failures of the phase's must-haves. Both issues were identified and documented during the Phase 1 code review, so they are known and named, not hidden gaps.

The phase successfully delivers:
- Two explicit, distinct `typing.Protocol` seams (`BeliefStore` + `BackendPort`) in code
- The LPG-primitive port granularity decision recorded and mechanically guarded
- All data-model decisions (DATA-01..06) embodied as frozen types with mechanical tests
- The UUID7 ordering contract written into the source (DATA-03)
- The backend-port contract documented in `docs/backend-contract.md` (BACK-04)
- `basedpyright` strict: 0 errors; `ruff`: all checks passed; 13/13 tests green

The two outstanding questions (WR-01 `extra="ignore"`, WR-03 mutable `list`) require a human policy decision before the phase can be marked fully closed.

---

_Verified: 2026-06-14T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
