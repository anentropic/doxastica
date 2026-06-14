---
phase: 01-protocol-backend-port-data-model-decisions
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/doxastica/__init__.py
  - src/doxastica/models.py
  - src/doxastica/errors.py
  - src/doxastica/protocol.py
  - src/doxastica/ports.py
  - tests/test_import_purity.py
  - tests/test_models_frozen.py
  - tests/test_port_distinct.py
  - tests/conftest.py
  - docs/backend-contract.md
  - pyproject.toml
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-06-14T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

This is a decision-grade, zero-storage-code phase: typed Protocol/port/model skeletons plus a
backend-contract doc. Judged against that intent, the import-boundary discipline is sound
(`protocol.py` and `ports.py` import only `typing`/`uuid`/`contextlib`/`doxastica.models`, never
`ladybug`, mechanically guarded by `test_import_purity.py`); the two seams are distinct objects
with the port exposing no query-string method (guarded by `test_port_distinct.py`); the closed
enums are pinned by membership tests; and `query_scope` takes a closed `BeliefFilter` rather than a
free `str`. The deliberately-absent runtime/storage behavior is NOT flagged.

However, the central claim repeated across docstrings and tests — that these models are *closed*
and make a "triple-structure leak unrepresentable" — is **not actually enforced**. pydantic's
default `extra="ignore"` silently accepts and discards unknown constructor kwargs, so the "closed
field set" is closed only on read-back, not on construction. That is the strongest finding (WR-01).
Two further warnings concern a hard floor-raise to Python 3.14 that contradicts the stated
`>=3.11` posture (WR-02) and a mutable list inside a "frozen" result model (WR-03).

## Warnings

### WR-01: Models claim a "closed" field set but pydantic default `extra="ignore"` silently accepts unknown fields

**File:** `src/doxastica/models.py:58-123`
**Issue:** Every model is declared `BaseModel, frozen=True` with no `model_config`/`ConfigDict`
setting `extra="forbid"`. pydantic v2's default is `extra="ignore"`, which means unknown
constructor kwargs are *silently accepted and dropped*, not rejected. Verified against the pinned
pydantic:

```
BeliefState(state_id=..., belief_id="b", scope_id="s", source_event_id=..., value=1,
            status=Status.active, provenance="leaked", timestamp="leaked")
# -> constructs successfully; provenance/timestamp silently discarded
```

This directly undercuts the load-bearing design claims in the docstrings and tests:
- `models.py:96-103` (DATA-02): "There is no free `str` and no arbitrary-property predicate: the
  model makes a triple-structure leak or query injection unrepresentable." A caller *can* pass
  arbitrary extra kwargs to `BeliefFilter`; they are unrepresentable on read-back but representable
  (and silently swallowed) on construction.
- `models.py:77-86` / DATA-05/06: the "closed six-field set" / "closed taxonomy" framing.
- The `test_models_frozen.py` suite asserts `set(Model.model_fields) == {...}` — this verifies the
  *declared* schema, NOT that extra input is rejected, so the test passes while the boundary leaks.

For a decision-grade taxonomy whose explicit purpose is to make leaks *unrepresentable* by
construction, accept-and-ignore is the wrong default: a downstream NVM author who fat-fingers a
field (or smuggles a narrative field) gets silent data loss instead of a `ValidationError`.

**Fix:** Add `extra="forbid"` to each frozen model so construction with unknown fields raises:

```python
from pydantic import BaseModel, ConfigDict

class BeliefState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    ...
```

(or `class BeliefState(BaseModel, frozen=True, extra="forbid")`). Then add a test asserting
`BeliefFilter(bogus=1)` / `BeliefState(..., extra_field=1)` raises `ValidationError`, so the
"unrepresentable leak" claim is mechanically true rather than aspirational.

### WR-02: `requires-python = ">=3.14"` contradicts the stated `>=3.11` floor and silently raises the support floor

**File:** `pyproject.toml:9`
**Issue:** CLAUDE.md states the floor is **3.11** (`requires-python>=3.11`), with 3.14 as the
*dev/CI primary* and a documented plan: "The only floor-sensitive code is UUID7 *generation in
tests* — handled by the dev-group `uuid-utils` shim." The roadmap even prescribes a CI matrix of
"3.11 and 3.14 at minimum." This file pins `>=3.14`, which:
1. Raises the support floor from 3.11 to 3.14 — a posture reversal not obviously decided in this
   phase's artifacts.
2. Lets `tests/test_models_frozen.py:10` use `from uuid import uuid7` (stdlib, 3.14-only) with **no
   `uuid-utils` dev-group shim present** in `pyproject.toml:19-28`. So the test suite is now
   un-runnable on 3.11–3.13, contradicting the documented multi-version test matrix.

This is either an intentional, undocumented floor-raise (then CLAUDE.md and the roadmap are stale
and should be reconciled) or an accidental over-pin from the cookiecutter `python_version`. Either
way the artifact and the constraints disagree, which is a correctness-of-decision defect for a
decision-grade phase.

**Fix:** Decide explicitly and make the artifact and docs agree. If the floor really is 3.14, record
that reversal in the phase decision log / CLAUDE.md and drop the `uuid-utils` plan. If the floor
stays 3.11, set `requires-python = ">=3.11"`, add the dev-only `uuid-utils` shim, and import
`uuid7` through a guarded shim in tests:

```python
try:
    from uuid import uuid7  # py3.14+
except ImportError:
    from uuid_utils import uuid7  # dev shim, 3.11-3.13
```

### WR-03: `ImpactResult.reached` is a mutable `list` inside a "frozen" model, defeating immutability

**File:** `src/doxastica/models.py:120`
**Issue:** `ImpactResult` is `frozen=True` and the docstring presents it as an immutable result value
object, but `reached: list[BeliefState]` is a mutable container. pydantic `frozen=True` blocks field
*reassignment* (`result.reached = [...]`) but does NOT freeze the list contents — `result.reached.append(x)`
and `result.reached.clear()` both mutate a "frozen" result in place. `frontier: frozenset[UUID]`
(line 121) is correctly immutable, so the mutable `list` is an inconsistency within the same model.
For a value object whose whole point is that a bounded cascade "never silently under-reports," a
mutable `reached` lets a caller corrupt the reported set after the fact.

**Fix:** Use an immutable sequence type for the field so the frozen guarantee is real:

```python
from collections.abc import Sequence

class ImpactResult(BaseModel, frozen=True):
    reached: tuple[BeliefState, ...]   # or Sequence[BeliefState] coerced to tuple
    frontier: frozenset[UUID]
    truncated: bool
```

Note `test_models_frozen.py:88-90` asserts `result.reached == []`; switching to `tuple` requires
updating that assertion to `== ()`.

## Info

### IN-01: Identity representation is inconsistent — `belief_id`/`scope_id` are bare `str` in `BeliefState` but wrapped in `Belief`/`Scope` elsewhere

**File:** `src/doxastica/models.py:67, 74, 89-90`
**Issue:** `Belief.belief_id: str` (71-74) and `Scope.scope_id: str` (58-67) wrap the identifiers in
typed value objects, yet `BeliefState.belief_id`/`scope_id` (89-90) and the `BeliefStore` Protocol
signatures (e.g. `revise(self, scope_id: str, belief_id: str, ...)`) pass bare `str`. The same
logical identity is sometimes a model and sometimes a raw string. This is a taxonomy-coherence wart
for a decision-grade model layer: it invites accidental cross-assignment (any `str` is a valid
`belief_id`) and makes the `Belief`/`Scope` wrappers look vestigial.
**Fix:** Decide one representation. Either drop `Belief`/`Scope` to bare-`str` everywhere, or
introduce `BeliefId`/`ScopeId` `NewType`/`StrEnum`-style aliases used consistently across models and
the Protocol. At minimum, document why the asymmetry is intentional.

### IN-02: `query_scope` parameter named `filter` shadows the builtin

**File:** `src/doxastica/protocol.py:114`
**Issue:** The parameter `filter: BeliefFilter` shadows the Python builtin `filter`. In a Protocol
signature it is mostly cosmetic, but it propagates into every implementer's method body and any
keyword call site (`store.query_scope(s, filter=...)`), where it shadows `filter()` for the rest of
the scope.
**Fix:** Rename to `belief_filter` (or `criteria`). Note ruff rule `A` (builtins-shadowing) is not in
the configured rule set (`pyproject.toml:50`), so this will not be caught automatically.

### IN-03: Backend-contract doc references a `CURRENT_STATE` pointer the model layer never defines

**File:** `docs/backend-contract.md:53-55`
**Issue:** Section 2 describes `revise` as "append a new `BeliefState` and re-point the
`CURRENT_STATE` pointer," and section 4 mentions structural edges, but `CURRENT_STATE` /
`HAS_REVISION` are explicitly *excluded* from `EdgeType` (`models.py:43-55`, "separate structural
constants") and no structural-edge constants exist yet in the reviewed code. The doc thus forward-
references a structural-pointer mechanism that Phase 1 has not introduced. Not wrong (it is a forward
contract), but a reader of Phase-1 code alone cannot locate `CURRENT_STATE`, and the doc does not
flag it as deferred to Phase 3. Minor consistency gap.
**Fix:** Add a one-line note that `CURRENT_STATE`/`HAS_REVISION` are structural constants introduced
in Phase 3, distinct from the consumer-facing `EdgeType`, to keep the doc self-locating.

### IN-04: `tests/conftest.py` is an empty placeholder

**File:** `tests/conftest.py:1-3`
**Issue:** The file contains only a docstring and a `# Add your fixtures here` comment. Harmless for a
phase with no DB fixtures, but it is dead scaffolding. Not a defect; noting for cleanup tracking.
**Fix:** Leave as-is if fixtures are imminent in Phase 2; otherwise remove until needed.

---

_Reviewed: 2026-06-14T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
