---
phase: 04-retrieval-observation-surface
reviewed: 2026-06-18T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/doxastica/core.py
  - src/doxastica/protocol.py
  - tests/test_query_scope.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-06-18
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the Phase-4 retrieval/observation surface: the new `query_scope` body and
`_current_tail` factor in `core.py`, the `include_deprecated`→`include_retracted` rename in
`protocol.py`, and the parametrized two-backend test scaffold in `tests/test_query_scope.py`.

The implementation is correct against every behavior it tests. I verified the load-bearing
invariants directly:

- **Ordering contract is faithful.** `query_scope` compares `str(source_event_id)` /
  `str(state_id)` lexicographically. I empirically confirmed (20k random UUIDs) that
  lexicographic ordering of the canonical UUID string is identical to big-endian byte order,
  so the str-based `_order_key` honors the documented `(source_event_id byte-order, state_id
  tiebreak)` contract on `protocol.py:50-51`. No drift between `_current`/`_current_tail`/
  `get_revision_chain`/`query_scope` — all four route through the single `_order_key`.
- **`_current_tail` factor preserved the write-side contract.** `_current` still applies the
  retracted-tail→`None` collapse on top of the status-agnostic max; the full suite (128 tests
  incl. the Phase-3 spine + invariant machines) passes, confirming no regression.
- **Pure-read discipline holds.** `query_scope` has no `_ensure_scope`/`unit_of_work`; an absent
  scope returns `[]` and creates no node (proven by `test_empty_scope_returns_empty`).
- **Closed-filter / no-interpolation discipline holds.** Only the four `BeliefFilter` fields are
  consumed; both backends bind belief data through `$param` (ladybug) or dict-equality (memory).
- **Rename is clean.** No stale `include_deprecated` reference survives anywhere in `src/`,
  `tests/`, or `docs/`.

No Critical issues. Two Warnings concern **test-coverage gaps for a "provably correct" core** —
the implementation is right today, but a future regression in two specific paths would pass the
current suite silently. Three Info items are minor.

## Warnings

### WR-01: `query_scope` cross-scope isolation is never tested

**File:** `tests/test_query_scope.py` (all tests), `src/doxastica/core.py:445`
**Issue:** Multi-scope is the project's single deliberate extension over single-agent Kumiho, and
`query_scope` is the surface where scope isolation must hold. Yet every test in the file writes and
reads under exactly one scope id (`"s"`, plus `"never_created"`). The correctness of scope
isolation rests entirely on the `{"scope_id": scope_id}` predicate at `core.py:445`. If that
predicate regressed — e.g. a future refactor scanned all `BeliefState` rows and dropped the
scope filter, or filtered on the wrong key — **no test in this file would catch it**: every
assertion would still pass because only one scope is ever populated. For a core whose value
proposition is mechanically-verifiable correctness, the absence of an isolation test is a real
robustness defect, not a style nit.
**Fix:** Add a test that populates two scopes and asserts non-leakage, e.g.:
```python
def test_query_scope_isolates_scopes(backend: BackendPort) -> None:
    core = _core(backend)
    core.revise("s1", "A", "v", _event_id())
    core.revise("s2", "B", "w", _event_id())
    assert _ids(core.query_scope("s1", BeliefFilter())) == {"A"}
    assert _ids(core.query_scope("s2", BeliefFilter())) == {"B"}
```

### WR-02: Combined-filter and `event_id_min`-only paths are untested

**File:** `tests/test_query_scope.py:136-191`, `src/doxastica/core.py:456-464`
**Issue:** The four `BeliefFilter` narrowing steps (`status`, `belief_ids`, `event_id_min`,
`event_id_max`) are exercised only in isolation or as a min+max pair. Two reachable code paths
have zero coverage: (a) `event_id_min` supplied **without** `event_id_max` — the `>= event_min`
branch at `core.py:459-461` runs on its own only in this configuration, and (b) several filters
AND-combined in one call (e.g. `belief_ids` + `status` + an event bound). Because each filter is an
independent list comprehension, a regression that, say, accidentally made `event_id_min` use `>`
instead of `>=`, or shadowed `tails` between two filter stages, could slip through the current
single-axis tests.
**Fix:** Add a lower-bound-only test and a multi-axis combination test:
```python
def test_event_range_min_only(backend: BackendPort) -> None:
    core = _core(backend)
    e_lo, e_hi = _event_id(), _event_id()
    core.revise("s", "LO", "l", e_lo)
    core.revise("s", "HI", "h", e_hi)
    # min == e_hi drops LO, keeps HI (inclusive lower bound, no upper bound)
    assert _ids(core.query_scope("s", BeliefFilter(event_id_min=e_hi))) == {"HI"}
```

## Info

### IN-01: Empty `status` frozenset silently yields `[]`

**File:** `src/doxastica/core.py:436-437`
**Issue:** `BeliefFilter(status=frozenset())` is `not None`, so `allowed = frozenset()` and step 4
filters out every tail, returning `[]`. This is defensible ("caller asked for no statuses"), but it
is undocumented and untested, so the behavior is implicit rather than decided. A caller who builds
the status set programmatically and accidentally empties it gets a silent empty result instead of
an error or the `include_retracted` default.
**Fix:** Either document the empty-set semantics in the `query_scope` docstring (one line: "an
empty `status` set matches nothing") or add an assertion/test pinning the chosen behavior so it
cannot silently change.

### IN-02: Inverted event range produces a silent empty result

**File:** `src/doxastica/core.py:459-464`
**Issue:** `BeliefFilter(event_id_min=hi, event_id_max=lo)` with `hi > lo` applies both filters and
returns `[]` (empty intersection). Correct as set semantics, but undocumented and likely surprising
to a caller who transposed the arguments. No test pins it.
**Fix:** Optional — a one-line docstring note that an inverted range yields `[]`, or a guard that
raises on `min > max` if a loud failure is preferred. Low priority.

### IN-03: `_order_key` recomputed for the incumbent on every group-by comparison

**File:** `src/doxastica/core.py:450`
**Issue:** `if current is None or _order_key(row) > _order_key(current):` recomputes
`_order_key(current)` for the stored incumbent on each row. This is a clarity/duplication note, not
a correctness issue (the result is identical) and performance is explicitly out of v1 scope. Flagged
only because the surrounding code is otherwise meticulous about computing the ordering key once.
**Fix:** If touched later, store `(key, row)` tuples in `by_belief` so the incumbent key is not
recomputed. No action required for v1.

---

_Reviewed: 2026-06-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
