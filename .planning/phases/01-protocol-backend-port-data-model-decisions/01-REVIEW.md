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
  info: 3
  total: 6
status: issues_found
---

# Phase 1: Code Review Report (re-review)

**Reviewed:** 2026-06-14T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Re-review after commit `c3a5a3b`. This is a decision-grade, zero-storage-code phase: typed
`Protocol`/port/model skeletons plus a backend-contract doc. Judged against that intent the
implementation is clean.

**Prior warnings confirmed RESOLVED (verified in source, not just claimed):**

- **WR-01 (prior, resolved):** all five frozen pydantic models now declare `extra="forbid"`
  (`models.py:58, 71, 77, 96, 111`). Construction with unknown kwargs raises `ValidationError`,
  and rejection tests were added (`test_models_frozen.py:102-119`). The "triple-structure leak
  unrepresentable" claim is now mechanical on construction, not only on read-back.
- **WR-03 (prior, resolved):** `ImpactResult.reached` is now `tuple[BeliefState, ...]`
  (`models.py:120`) with an `isinstance(..., tuple)` guard (`test_models_frozen.py:95-99`). The
  frozen guarantee is complete; the matching assertion was updated to `== ()`.
- **WR-02 (prior):** the `>=3.14` floor (`pyproject.toml:9`) is a locked CONTEXT decision (native
  `uuid7`) and is NOT re-flagged as a code defect. Verified `python3 --version` = 3.14.3 and
  `from uuid import uuid7` resolves. Only the residual CLAUDE.md doc drift is carried forward (IN-02).

**New / still-open findings.** The most material is **WR-01 (new): the backend-blind AST guard is
asymmetric** — `ports.py` carries the identical "never import `ladybug`" contract as `protocol.py`
but no test enforces it, so half the seam discipline is a comment, not a build failure. There is
also a genuine **type-domain inconsistency in `traverse`** (WR-02) worth pinning before Phase 2/3
build against the signature, and the long-standing `filter`-shadows-builtin wart (WR-03, previously
filed as info, raised because it sits in the public contract every implementer inherits).

## Warnings

### WR-01: `ports.py` backend-blind contract is not mechanically enforced (asymmetric AST guard)

**File:** `tests/test_import_purity.py:17-30`; `src/doxastica/ports.py:37-40`
**Issue:** `ports.py` explicitly states (lines 37-40) that it "imports only `contextlib`, `typing`,
`uuid` and `doxastica.models` — never `ladybug`". That is the same backend-blind invariant the AST
scan enforces for `protocol.py`. But `test_import_purity.py` hard-codes a single path
(`src/doxastica/protocol.py`, line 19) and never scans `ports.py`. The enforcement is therefore
asymmetric: a future `import ladybug` added to `ports.py` (the internal core↔backend seam) would be
a silent contract leak — a build pass, not the build failure the test promises. The module docstring
even advertises the guarantee as if guarded, making the gap easy to miss. Both seams claim to be
backend-blind; only one is mechanically held to it.
**Fix:** Parameterize the scan over both modules so the guard is symmetric:
```python
import ast
import pathlib

import pytest


@pytest.mark.parametrize("module", ["protocol", "ports"])
def test_seam_does_not_import_ladybug(module: str) -> None:
    """The backend-blind seams must import no ``ladybug`` module (DATA-01 / BACK-01)."""
    source = pathlib.Path(f"src/doxastica/{module}.py").read_text()
    tree = ast.parse(source)

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    offenders = [name for name in imported if name.split(".")[0] == "ladybug"]
    assert not offenders, f"{module}.py must not import ladybug; found: {offenders}"
```

### WR-02: `traverse` frontier type is narrower than its node-id domain (`UUID | str` in, `frozenset[UUID]` out)

**File:** `src/doxastica/ports.py:96-101`
**Issue:** `traverse` accepts `start: UUID | str` and the port's node ids are uniformly `UUID | str`
(`upsert_node` line 72; `add_edge` lines 81-82), and the backend contract explicitly permits a
`node_id` to be "a `UUID` or `str`" (`docs/backend-contract.md:21`). But `traverse`'s return type is
`tuple[list[dict[str, Any]], frozenset[UUID]]` — the `frontier` element type is `UUID` only. A
conforming backend that keys nodes by `str` cannot represent a `str`-keyed unexpanded boundary node
in `frontier` without violating the declared type. This is an internal contradiction in the
just-decided contract: the id domain is `UUID | str` everywhere except the one place that reports
boundary ids. Because this is a decision-grade signature that "must not regress," it should be
reconciled now, before Phase 2 adapters and Phase 3 composition depend on it. (The public
`ImpactResult.frontier` at `models.py:121` is legitimately `frozenset[UUID]` because `state_id` is
always a UUID — the mismatch is specifically at the generic LPG port, whose id domain is wider.)
**Fix:** Make the frontier element type match the node-id domain:
```python
    def traverse(
        self,
        start: UUID | str,
        edge_types: frozenset[EdgeType | str],
        max_depth: int | None,
    ) -> tuple[list[dict[str, Any]], frozenset[UUID | str]]:
```
If the real intent is that the port only ever traverses UUID-keyed nodes, narrow `start` to `UUID`
instead and document why — but do not leave the input domain wider than the frontier output.

### WR-03: `query_scope` parameter `filter` shadows the `filter` builtin (in the public contract)

**File:** `src/doxastica/protocol.py:113`
**Issue:** `query_scope` uses `filter: BeliefFilter`, shadowing the builtin `filter`. Re-classified
from info to warning because this is not cosmetic at the skeleton stage: the name propagates into
every Phase-3 implementer body and every keyword call site (`store.query_scope(s, filter=...)`),
where a subsequent use of the builtin `filter(...)` silently resolves to the `BeliefFilter` instance
and raises `TypeError` at call time rather than at type-check time. Ruff rule `A002`
(builtin-argument-shadowing) is not in the selected set (`pyproject.toml:50` selects
`E,F,W,I,UP,B,SIM,TCH,D`), so it passes lint silently. For a "provably correct" core this is a latent
footgun planted in the public contract that every implementer inherits.
**Fix:** Rename to `belief_filter` (or `criteria`/`spec`) before any implementation depends on the
name:
```python
    def query_scope(
        self,
        scope_id: str,
        belief_filter: BeliefFilter,
        include_deprecated: bool = False,
    ) -> list[BeliefState]: ...
```
Optionally add `A` to the ruff `select` set to catch this class mechanically.

## Info

### IN-01: Identity representation is inconsistent — bare `str` vs `Belief`/`Scope` wrappers

**File:** `src/doxastica/models.py:67, 74, 89-90`; `src/doxastica/protocol.py:66-98`
**Issue:** `Belief.belief_id: str` (71-74) and `Scope.scope_id: str` (58-67) wrap identifiers in typed
value objects, yet `BeliefState.belief_id`/`scope_id` (89-90) and every `BeliefStore` signature (e.g.
`revise(self, scope_id: str, belief_id: str, ...)`) pass bare `str`. The same logical identity is
sometimes a model and sometimes a raw string. For a decision-grade model layer this is a coherence
wart: any `str` is a valid `belief_id`, so the `Belief`/`Scope` wrappers look vestigial and invite
accidental cross-assignment.
**Fix:** Decide one representation — drop `Belief`/`Scope` to bare-`str` everywhere, or introduce
`BeliefId`/`ScopeId` `NewType` aliases used consistently across models and the Protocol. At minimum
document why the asymmetry is intentional.

### IN-02: CLAUDE.md `requires-python>=3.11` text is stale vs the locked `>=3.14` floor

**File:** project `CLAUDE.md` vs `pyproject.toml:9`
**Issue:** The `>=3.14` floor is a deliberate locked decision (native `uuid7`) and is correctly NOT a
code defect. Flagging only the residual documentation drift: CLAUDE.md still asserts
`requires-python>=3.11`, prescribes a "3.11 and 3.14" CI matrix, and describes a `uuid-utils` dev-group
shim that is correctly absent from `pyproject.toml`. The authoritative manifest and CLAUDE.md now
disagree on the supported floor, so a future contributor could reintroduce the (now-forbidden) third
dev dependency or lower the floor. Doc drift only — the code is correct.
**Fix:** Update CLAUDE.md's "Python version posture" and "UUID7 decision" sections to state the
`>=3.14` floor and that no UUID shim is used, reconciling the prose with the locked decision.

### IN-03: Backend-contract doc forward-references `CURRENT_STATE`/`HAS_REVISION` not yet in the model layer

**File:** `docs/backend-contract.md:53-55`
**Issue:** Section 2 describes `revise` as "append a new `BeliefState` and re-point the `CURRENT_STATE`
pointer," but `CURRENT_STATE`/`HAS_REVISION` are explicitly *excluded* from `EdgeType`
(`models.py:43-55`, "separate structural constants") and no structural-edge constants exist in the
Phase-1 code. A reader of Phase-1 code alone cannot locate `CURRENT_STATE`, and the doc does not flag
it as deferred. Minor self-locating gap (the doc is a forward contract, not wrong).
**Fix:** Add a one-line note that `CURRENT_STATE`/`HAS_REVISION` are structural constants introduced in
Phase 3, distinct from the consumer-facing `EdgeType`.

---

_Reviewed: 2026-06-14T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
