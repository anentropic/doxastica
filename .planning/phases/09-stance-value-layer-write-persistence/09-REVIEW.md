---
phase: 09-stance-value-layer-write-persistence
reviewed: 2026-07-04T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/doxastica/models.py
  - src/doxastica/core.py
  - src/doxastica/protocol.py
  - src/doxastica/backends/ladybug.py
  - tests/test_stance.py
  - tests/test_stance_persistence.py
  - tests/test_models_frozen.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-07-04
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 9 threads the `Stance` ordinal enum through the full write-read spine. The
implementation is correct on all the key invariants: hydration uses `Stance[name]`
(name-lookup) not `Stance(value)` (line 282, `core.py`); `contract` copies
`prior["stance"]` verbatim without re-encoding (line 443); the default `Stance.certain`
lives on the `revise`/`expand` API surface, not on the model (lines 370, 387, 83, 91
in protocol.py); the DDL adds `stance STRING` to `{ns}_BeliefState`; and the ladybug
injection boundary remains clean (all data values are `$param`-bound).

One genuine schema-migration gap affects persistent-file-path databases that pre-date
Phase 9. Two informational notes are recorded below.

## Warnings

### WR-01: `_bootstrap_schema` cannot add `stance STRING` to an existing `{ns}_BeliefState` table

**File:** `src/doxastica/backends/ladybug.py:232-235`
**Issue:** `CREATE NODE TABLE IF NOT EXISTS {ns}_BeliefState (... stance STRING ...)` is a
no-op when the table already exists. Any file-path LadybugDB created by pre-Phase-9 code
(before `stance` was in the DDL) will have the `{ns}_BeliefState` table without the
`stance` column. Phase-9 code then fails in two ways against such a database:

1. **Writes:** `upsert_node` compiles to `... SET n.stance = $p6`. Ladybug is
   schema-first, so setting a column that does not exist in the table schema raises a
   runtime error.
2. **Reads:** `match_nodes("BeliefState", ...)` returns row dicts without a `stance` key;
   `_hydrate` then raises `KeyError: 'stance'` at `Stance[props["stance"]]` (line 282).

The docstring's claim that bootstrap is "a safe no-op when re-run against a fresh OR
shared injected DB" is accurate for deployments that were always on Phase-9 schema, but
is misleading for in-place upgrades. The failure is loud (not silent), so it surfaces
immediately — but there is no migration path in the codebase.

This does not affect in-memory databases (the fixture pattern and the normal CI path),
which are always freshly bootstrapped. It only matters for persistent file-path deployments
being upgraded.

**Fix:** Either add an explicit `ALTER TABLE` (if LadybugDB supports it) or bump the
schema version and drop+recreate the table. For M0 pre-release, the minimum acceptable
guard is a comment noting that `IF NOT EXISTS` is not a migration mechanism, and that
upgrading a persistent database from a pre-`stance` schema requires a manual recreate.
A code-level guard that detects the missing column and raises a descriptive error early
(rather than letting `upsert_node` or `_hydrate` fail with an opaque error) would make
the failure boundary more actionable:

```python
# In _bootstrap_schema, after CREATE NODE TABLE IF NOT EXISTS:
rows = self._exec(
    f"CALL table_info('{ns}_BeliefState') RETURN *"
)
columns = {r["name"] for r in self._rows(rows)}
if "stance" not in columns:
    raise RuntimeError(
        f"Schema mismatch: {ns}_BeliefState exists but has no 'stance' column. "
        "This database predates Phase 9. Drop and recreate to upgrade."
    )
```

(The exact `CALL table_info` syntax should be verified against LadybugDB 0.17.1; adapt
if the introspection API differs.)

## Info

### IN-01: `test_stance_persistence.py` has no direct test of `expand` with a non-default stance

**File:** `tests/test_stance_persistence.py`
**Issue:** The persistence test suite proves `revise`, `contract`, and `get_scope_at`
preserve stance byte-stably, but `expand` is never called with an explicit stance argument.
Because `revise` and `expand` both delegate to `_append` (which serializes via `stance.name`
identically for both), the guarantee holds transitively. However, a dedicated test would
close the explicit gap and protect against a future divergence where `expand`'s signature
or default is changed independently.

**Fix:** Add a test analogous to `test_stance_round_trips_byte_stable` that calls
`core.expand(...)` with `stance=Stance.doubted` and asserts the round-tripped member
identity.

### IN-02: `Stance.__lt__` return annotation is technically imprecise

**File:** `src/doxastica/models.py:91-98`
**Issue:** The method is annotated `-> bool` but the non-`Stance` branch returns
`NotImplemented` (type `NotImplementedType`, not `bool`). This is the standard Python
comparison-method protocol for "I cannot handle this operand type," and both pyright and
basedpyright give a special pass to `NotImplemented` returns in comparison methods even
when the annotation says `-> bool` — so the type checker will not flag it. Runtime
behaviour is correct (Python raises `TypeError` for cross-type comparisons, satisfying
STANCE-06). No fix is required, but the annotation could be made self-documenting:

```python
# In Python 3.14 the canonical annotation for __lt__ returning NotImplemented is:
def __lt__(self, other: object) -> bool:   # NotImplemented propagates TypeError via Python protocol
```

The current code is already correct; this note is purely for completeness.

---

_Reviewed: 2026-07-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
