---
phase: 03-append-only-revision-spine-keystone
fixed_at: 2026-06-16T00:00:00Z
review_path: .planning/phases/03-append-only-revision-spine-keystone/03-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-06-16
**Source review:** .planning/phases/03-append-only-revision-spine-keystone/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (the WARNING tier — WR-01..WR-05; INFO findings out of scope)
- Fixed: 5
- Skipped: 0

All five in-scope warnings were fixed. After fixes the full suite stays green on BOTH
backends (`UV_NO_SYNC=1 uv run --extra ladybug pytest -q` → 105 passed), basedpyright-strict
reports 0 errors, and ruff lint + format are clean.

## Fixed Issues

### WR-01: `contract()` vacuity is documented as a "silent no-op" but writes a Scope node

**Files modified:** `src/doxastica/core.py`
**Commit:** 97b9ace
**Applied fix:** Reordered `contract` so the read-only `_current` vacuity probe runs BEFORE
`_ensure_scope`. A vacuous contraction (`prior is None`) now returns immediately and leaks no
write — no `Scope` node is materialised. The D-03 world-scope structural guard is preserved as
the FIRST statement (it still fires before `unit_of_work` and before any backend access, per the
guardrail), so guard ordering is unchanged; only the scope-create moved below the vacuity check.
Docstring updated to describe the genuine-no-op semantics and the preserved guard ordering.

### WR-02: `chain_is_immutable` invariant asserts `>=` but the docstring promises exact equality

**Files modified:** `tests/test_invariants.py`
**Commit:** e1661dd
**Applied fix:** Tightened the assertion from `total >= self._state_count` to
`total == self._state_count`, with the strengthened message from the review. The shadow oracle's
`_state_count` increments exactly once per real append (revise/expand and the contract acting-
branch via `_record`); the vacuous-contract path is gated out by `@precondition` and
`world_contract_raises` records nothing, so exact equality holds across every op sequence the
stateful machine generates. Verified green on both backends (the WR-01 reorder does not affect
this — the machine's `contract` rule only runs on existing-current keys, never the vacuous path).

### WR-03: `traverse` interpolates `edge_types` into the Cypher rel pattern without validation

**Files modified:** `src/doxastica/backends/ladybug.py`
**Commit:** ba82d8d
**Applied fix:** Before building the interpolated rel pattern, each `edge_type` is constrained to
the known `_EDGE_ENDPOINTS` set (`raise ValueError` on an unknown type, mirroring `add_edge`'s
implicit guard), and an empty `edge_types` frozenset is rejected (it would otherwise yield
`rels == ""` and a malformed `[:* ...]` pattern). The rel-pattern interpolation now sits inside
the same injection-safety story as the sanctioned namespace interpolation.

### WR-04: `match_nodes` / `upsert_node` interpolate prop/where KEYS into Cypher unvalidated

**Files modified:** `src/doxastica/backends/ladybug.py`
**Commit:** ba82d8d
**Applied fix:** Added a `_validate_identifier` helper (reusing the existing bare-identifier
`_NS_RE`) and call it on every interpolated prop key in `upsert_node` and every predicate key in
`match_nodes`, before the key reaches `n.{key}`. Values remain `$param`-bound; this extends the
"by-construction injection-proof" guarantee to the column-identifier surface for any future
key-splatting caller.

### WR-05: `traverse` mutates shared connection state (`var_length_extend_max_depth`) and never restores it

**Files modified:** `src/doxastica/backends/ladybug.py`
**Commit:** ba82d8d
**Applied fix:** Introduced a `_DEFAULT_HOP_CAP = 30` constant. `traverse` now raises the cap only
when the requested `bound` actually exceeds the default (a shallow walk never touches connection
state at all), and restores the default in a `try/finally` around the traversal query. An injected
tenant connection (`owns_conn=False`, R19) is therefore never left with a changed ceiling behind
the port — a subsequent unrelated query on the tenant's handle sees the original 30-hop cap.

## Notes on commit grouping

WR-03, WR-04, and WR-05 all touch interleaved regions of the single `ladybug.py` adapter (the
file header for the new constant + helper, and the shared `traverse` method body). They were
committed together as one atomic backend-port-hardening commit (ba82d8d) to keep the module
compilable at every commit boundary; per-hunk splitting would have produced fragile intermediate
states that did not parse/import cleanly. WR-01 and WR-02 are independent single-file commits.

## INFO findings (out of scope)

IN-01..IN-04 are INFO-tier and outside the `critical_warning` fix scope; they were not addressed.

---

_Fixed: 2026-06-16_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
