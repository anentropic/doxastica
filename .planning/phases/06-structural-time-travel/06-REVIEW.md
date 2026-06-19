---
phase: 06-structural-time-travel
reviewed: 2026-06-19T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/doxastica/core.py
  - tests/test_scope_at.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-06-19T00:00:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Phase 06 (HIST-03) adds one production method — `MemoryCore.get_scope_at` in
`src/doxastica/core.py` — plus an example-test suite and a Hypothesis operational-fold
property machine in `tests/test_scope_at.py`. I reviewed the new method body and the test
file adversarially, traced the ordering/cut/retracted-collapse logic, verified the UUID7
tiebreak assumption empirically, and ran the full sub-suite on BOTH backends.

**Assessment: the implementation is correct.** The central trap of the phase — placing the
inclusive `<= as_of` cut BEFORE the per-belief ordering-max (cut-then-max = REWIND) rather
than after it (`query_scope`'s max-then-filter = DROP) — is implemented correctly (lines
657-662). I specifically verified the load-bearing assumptions that could have hidden a bug:

- **UUID7 string-monotonicity (the oracle's `append_seq` ↔ `state_id` tiebreak):** empirically
  confirmed `str(uuid.uuid7())` is strictly increasing in mint order, so the oracle's monotonic
  `append_seq` faithfully mirrors the production `state_id` tiebreak. The anti-tautology design
  (the `fold` oracle never calls `get_scope_at`/`_current`) is intact (lines 367-390).
- **Inclusive cut + retracted-as-of collapse computed over the cut window** (lines 658, 664):
  correct — a `contract` op drawn from `_EVENT_POOL` is recorded with the same `(source_event_id,
  tiebreak)` key the core uses, so whether it wins at a given cut is decided, not assumed (SC3).
- **`_MAX_CUT` sentinel** (`ffffffff-…`): a real UUID7 (version nibble `7`, variant bits) can
  never reach all-`f`, so the sentinel is a valid `>=`-everything cut for the SC1 case.
- **Driver-blindness / append-only / parameterized-Cypher:** no `ladybug` import, no Cypher,
  no mutation — `get_scope_at` composes only `match_nodes` (pure read, no `_ensure_scope`, no
  `unit_of_work`, no world-scope guard), exactly as a pure-read temporal query should.

Both backends (`memory` + `ladybug`) genuinely ran (ladybug installed locally) — all 16 cases
pass. Findings below are quality/robustness only; none block.

## Warnings

### WR-01: `get_scope_at` reads outside a `unit_of_work` while `query_scope`'s sibling `get_impact` wraps its multi-call read in one

**File:** `src/doxastica/core.py:651-667`
**Issue:** `get_scope_at` issues a single `match_nodes` scan with no enclosing `unit_of_work()`.
For a single round-trip this is harmless — there is no second call to interleave. However, the
docstring (line 643-647) justifies the bare read as "Composes ONLY `match_nodes` — no
`traverse`, no edge walk," which is true *today*. The adjacent `get_impact` (line 480-497)
explicitly documents (WR-02) that wrapping even a pure read in `unit_of_work` is required on the
ladybug single-writer model whenever MORE THAN ONE backend call must share a snapshot, because a
concurrent append can land between two auto-committed reads. `get_scope_at` is one call so it is
correct now, but the asymmetry is a latent trap: if a future change adds a second backend call
(e.g. a scope-existence probe, or splitting the scan), the single-snapshot guarantee silently
disappears with no compile-time signal. `query_scope` shares this same single-call exemption, so
this is a pre-existing pattern — but the new method inherits the risk without the WR-02-style
note that flags it.
**Fix:** Either (a) add a one-line comment mirroring `get_impact`'s WR-02 note making the
single-call snapshot assumption explicit ("one `match_nodes` ⇒ one auto-committed snapshot; if a
second backend call is ever added here, wrap both in `unit_of_work` per WR-02"), or (b) if a
phase budget allows, wrap the scan in `self._backend.unit_of_work()` for symmetry with
`get_impact`. Option (a) is sufficient; the goal is to make the snapshot assumption a documented
invariant rather than an accident of the current single-call shape.

## Info

### IN-01: Retracted-status check uses raw string compare while `query_scope` uses enum-membership — divergent if the closed taxonomy ever grows

**File:** `src/doxastica/core.py:664`
**Issue:** `get_scope_at` collapses retracted tails with a raw value compare:
`t["status"] != Status.retracted.value`. The sibling `query_scope` instead rebuilds the enum and
tests set membership: `Status(t["status"]) in allowed` (line 594). Both are correct under the
closed `{active, retracted}` taxonomy (DATA-06, confirmed in `models.py:45-46`). But the two
methods would diverge if a third `Status` member were ever added: `get_scope_at` would silently
INCLUDE the new status (anything not-retracted passes), whereas `query_scope`'s explicit
allow-set would EXCLUDE it. The taxonomy is documented closed, so this is not a live bug — only a
maintenance asymmetry that hides which method to update if DATA-06 is ever revisited.
**Fix:** For symmetry and future-proofing, express the keep-rule positively against the active
status — `t["status"] == Status.active.value` — which fails-closed (a hypothetical new status is
excluded, matching `query_scope`). Alternatively add a comment pinning the raw compare to the
closed-taxonomy assumption (`# DATA-06: closed {active, retracted}, so != retracted ≡ == active`).

### IN-02: `_active_keys` recomputes the full `fold` once per op-log entry (test helper)

**File:** `tests/test_scope_at.py:427-434`
**Issue:** `_active_keys` loops over every `(scope, belief)` in `self.entries` and calls
`self.fold(scope_id, max_cut)` inside the loop, so `fold` is re-run once per entry even though
its result for a given `scope_id` is identical across that scope's beliefs. This is a test-helper
inefficiency, not a correctness defect (performance is out of v1 scope, and the bounded op
sequence keeps it cheap). Noted only because it slightly obscures the intent — the helper reads
as if `fold` were per-belief when it is per-scope.
**Fix:** Memoize `fold` per `scope_id` within the call, e.g. compute
`folded = {sc: self.fold(sc, max_cut) for sc in {s for s, _ in self.entries}}` once, then test
`belief_id in folded[scope_id]`. Cosmetic; skip if not touching this helper.

### IN-03: Example suite never exercises `expand` through `get_scope_at`

**File:** `tests/test_scope_at.py:87-243`
**Issue:** The seven example tests drive only `revise` (and `contract`); none call `expand`. The
operational-fold machine does drive `expand` (line 422-425) and records it as op_kind `"revise"`,
mirroring the production `expand` ≡ `revise` equivalence (core.py:350-364), so the path IS covered
by the property machine. The gap is only in the human-readable example layer, where a reader
cannot see at a glance that `expand` participates in as-of reconstruction identically to `revise`.
Low value — the mechanical identity is already proven by `_append` delegation and the fold
machine — but worth a one-line example for documentation parity with `test_query_scope.py`.
**Fix:** Optionally add a small example asserting `get_scope_at` after an `expand` returns the
expanded value at the cut, mirroring `test_cut_is_inclusive_at_boundary` but via `expand`. Skip if
the fold-machine coverage is considered sufficient (it is, for correctness).

---

_Reviewed: 2026-06-19T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
