---
phase: 01-protocol-backend-port-data-model-decisions
fixed_at: 2026-06-14T00:00:00Z
review_path: .planning/phases/01-protocol-backend-port-data-model-decisions/01-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 1: Code Review Fix Report

**Fixed at:** 2026-06-14T00:00:00Z
**Source review:** .planning/phases/01-protocol-backend-port-data-model-decisions/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (0 critical, 3 warning; 3 info findings out of scope — no `--all`)
- Fixed: 3
- Skipped: 0

All three Warning findings were applied cleanly. The full verification suite is green
after the fixes:

- `uv run pytest -q` -> 17 passed (the import-purity test now contributes 2 parameterized
  cases instead of 1)
- `uv run basedpyright` -> 0 errors, 0 warnings, 0 notes
- `uv run ruff check .` -> all checks passed
- `uv run ruff format --check .` -> 12 files already formatted

## Fixed Issues

### WR-01: `ports.py` backend-blind contract is not mechanically enforced (asymmetric AST guard)

**Files modified:** `tests/test_import_purity.py`
**Commit:** 4756d38
**Applied fix:** Replaced the single-path `test_protocol_does_not_import_ladybug` with a
`@pytest.mark.parametrize("module", ["protocol", "ports"])`-driven
`test_seam_does_not_import_ladybug`, so the AST scan now enforces the "never import
`ladybug`" contract symmetrically over BOTH `src/doxastica/protocol.py` (DATA-01) and
`src/doxastica/ports.py` (BACK-01). The AST approach was kept (no regression to a grep):
the scan still walks the whole tree, so a `ladybug` import hidden in a `TYPE_CHECKING`
block or function body in either module is now a build failure. The module docstring was
updated to describe both seams. Verified the new test produces 2 passing cases.

### WR-02: `traverse` frontier type is narrower than its node-id domain

**Files modified:** `src/doxastica/ports.py`
**Commit:** c05cd16
**Applied fix:** Widened `BackendPort.traverse`'s return type from
`tuple[list[dict[str, Any]], frozenset[UUID]]` to
`tuple[list[dict[str, Any]], frozenset[UUID | str]]`, so the unexpanded-boundary node-id
domain matches the rest of the port (`upsert_node`/`add_edge`/`traverse.start` all use
`UUID | str`, and `docs/backend-contract.md` line 21 explicitly permits a `node_id` to be
"a `UUID` or `str`"). The `traverse` docstring needed no change (it speaks of "nodes"
type-agnostically).

**Reasoning on scope (per fix guidance):** `ImpactResult.frontier` in `models.py` was
deliberately LEFT as `frozenset[UUID]`. That is the CORE-level shape where the `state_id`
handle is always a core-minted UUID; the str-keyed-id domain is a BACKEND-port concern,
not a core-model concern. The backend-contract doc reinforces this distinction (str node
ids are a generic-LPG-port property), so only the port boundary was widened, matching the
reviewer's own note that the public `ImpactResult.frontier` is "legitimately
`frozenset[UUID]`".

### WR-03: `query_scope` parameter `filter` shadows the `filter` builtin

**Files modified:** `src/doxastica/protocol.py`
**Commit:** 354e77f
**Applied fix:** Renamed the `BeliefStore.query_scope` parameter from `filter:
BeliefFilter` to `belief_filter: BeliefFilter`, removing the shadow of the `filter`
builtin in the public contract every Phase-3 implementer inherits. The parameter remains a
closed `BeliefFilter` (never a free `str`), preserving DATA-02. The docstring references
(`matching ... belief_filter`, `belief_filter is a closed ... BeliefFilter`, `An explicit
belief_filter.status governs`) were updated to the new name. No test or `__init__.py`
referenced the parameter by keyword, so no call-site updates were needed. (The summary
line was kept to a single physical line to satisfy ruff D205.)

The optional ruff `A` (`flake8-builtins`) select-set addition suggested in the review was
NOT applied — it is a tooling-config change beyond the narrow scope of this finding and is
better decided explicitly by the maintainer; the shadowing footgun itself is now removed
at the source.

## Out-of-Scope (not attempted)

The three Info findings (IN-01 identity representation, IN-02 CLAUDE.md `>=3.11` doc
drift, IN-03 backend-contract forward-reference note) were OUT of scope for this run
(`fix_scope: critical_warning`, no `--all`) and were not touched.

---

_Fixed: 2026-06-14T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
