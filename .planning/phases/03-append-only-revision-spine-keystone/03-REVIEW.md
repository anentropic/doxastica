---
phase: 03-append-only-revision-spine-keystone
reviewed: 2026-06-16T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/doxastica/__init__.py
  - src/doxastica/backends/ladybug.py
  - src/doxastica/core.py
  - src/doxastica/models.py
  - tests/test_backend_parity.py
  - tests/test_invariants.py
  - tests/test_revision_spine.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-06-16
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed the Phase-3 append-only revision-spine keystone: the `WORLD_SCOPE_ID` constant,
the ladybug `HAS_REVISION` hub table + endpoint-aware `add_edge`, the `MemoryCore` op bodies
(`get_or_create_scope`, derived `_current`, `_append`, `revise`/`expand`, `contract`,
`get_revision_chain`), the base64-over-JSON value codec, and the Hypothesis stateful
consistency test.

The four flagged hot-spots largely hold up under tracing:

- **Cypher injection (data path):** all belief DATA flows through `$param` binds; the
  namespace is regex-validated before the one sanctioned interpolation. The data-injection
  surface is closed.
- **Derived-current ordering:** the `(str(source_event_id), str(state_id))` sort key was
  verified to match the documented big-endian byte-order contract (UUID string form is
  fixed-width lowercase hex, so lexicographic `str` order == byte order). `_current` correctly
  takes the max over ALL statuses and returns `None` on a retracted tail.
- **Value round-trip:** base64-over-JSON correctly defeats the ladybug brace/bracket
  STRING-coercion hazard; `contract` copies the stored token verbatim (no double-encode).
- **Append-only:** no edge/node delete primitive is composed; all ops are pure appends.

However, the adversarial pass surfaced one real append-only/no-op contract violation
(`contract` vacuity creates a Scope node), a weakened keystone invariant whose docstring
claims a stronger guarantee than it asserts, and several latent interpolation surfaces in the
backend port primitives that are safe only because today's in-package callers happen to pass
literal/enum values. None are BLOCKER-tier for the current closed call graph, but the
invariant weakening and the vacuity write-leak both undercut stated correctness guarantees and
should be fixed before this keystone is relied on by Phases 4-6.

## Warnings

### WR-01: `contract()` vacuity is documented as a "silent no-op" but writes a Scope node

**File:** `src/doxastica/core.py:301-309`
**Issue:** The `contract` docstring states vacuity is a "silent no-op, no state appended" and
the world-scope guard comment elevates write-leak-freedom to a design value ("leaks no write
even if the world node was never created"). But for a non-world scope, `_ensure_scope(scope_id)`
runs *inside* the `unit_of_work` and *before* the `prior is None` vacuity check. Calling
`contract("fresh_scope", "never_asserted", ...)` therefore creates a `Scope` node as a
side effect of an operation documented as a no-op. The behavior tests only assert no
`BeliefState` leaked (`get_revision_chain(...) == []`), so this side-effect write is uncaught.
**Fix:** Move the vacuity probe before scope creation so a vacuous contract is a true no-op:
```python
with self._backend.unit_of_work():
    prior = self._current(scope_id, belief_id)
    if prior is None:
        return None  # D-05 vacuity: genuine no-op, no Scope write
    self._ensure_scope(scope_id)
    ...
```
`_current` only reads, so probing before `_ensure_scope` is safe. (If a missing scope must
still be materialised on contract, then the docstring's "no-op / leaks no write" language
should be corrected instead — but the two cannot both stand.)

### WR-02: `chain_is_immutable` invariant asserts `>=` but the docstring promises exact equality

**File:** `tests/test_invariants.py:304-310`
**Issue:** The docstring says "The watermark equals the number of appends the rules performed,
which the store must match exactly," but the assertion is `total >= self._state_count`. Because
every op mints a fresh `uuid.uuid7()` `state_id`, the store count should be *exactly*
`self._state_count`. The `>=` form silently passes if an op duplicates a state, double-appends,
or otherwise over-writes — i.e. it fails to catch the exact class of append-only/duplication
defect this keystone invariant exists to detect. The monotonic-watermark intent is already
covered by `_state_count` only ever incrementing; the store-side check should be the strong one.
**Fix:**
```python
assert total == self._state_count, (
    f"BeliefState count must equal the number of appends performed exactly "
    f"(no deletes AND no duplicate writes, CHAIN-02): "
    f"store has {total} states but {self._state_count} appends were performed"
)
```

### WR-03: `traverse` interpolates `edge_types` into the Cypher rel pattern without validation

**File:** `src/doxastica/backends/ladybug.py:320, 339-346`
**Issue:** `rels = "|".join(f"{ns}_{edge_type}" for edge_type in edge_types)` interpolates each
`edge_type` directly into the rel pattern. Unlike `add_edge` (which is implicitly validated by
the `_EDGE_ENDPOINTS[str(edge_type)]` lookup raising `KeyError` on an unknown type) and unlike
the regex-validated `namespace`, `traverse` applies *no* validation. The port signature accepts
`frozenset[EdgeType | str]`, so a caller passing an attacker-controlled raw string would inject
arbitrary Cypher into the rel pattern. Today this is unreached (no in-package `traverse` call
exists yet — it lands in Phases 4-6), so the surface is latent, but the project's stated
discipline is "the namespace is the one sanctioned interpolation; all else is `$param`," and
this is a second unvalidated interpolation that contradicts that invariant before the consumer
arrives.
**Fix:** Constrain each member to the known edge-type set before interpolation, mirroring the
`add_edge` guard:
```python
for et in edge_types:
    if str(et) not in _EDGE_ENDPOINTS:
        raise ValueError(f"unknown edge type for traverse: {et!r}")
```
Also guard `edge_types` being empty (yielding `rels == ""` and a malformed `[:* ...]` pattern).

### WR-04: `match_nodes` / `upsert_node` interpolate prop/where KEYS into Cypher unvalidated

**File:** `src/doxastica/backends/ladybug.py:222-227, 279-282`
**Issue:** Both primitives interpolate dict keys directly: `set_clauses.append(f"n.{key} = ${pname}")`
and `predicates.append(f"n.{key} = ${pname}")`. Values are correctly `$param`-bound, but the
keys are not validated. Every in-package caller in `core.py` passes hardcoded literal keys
(`scope_id`, `belief_id`, `state_id`, `source_event_id`, `value`, `status`), so the surface is
not currently exploitable. But the `BackendPort` is a general primitive; a future caller (or a
test like the parity helpers that splat `**props`) passing a caller-influenced key would inject
Cypher. Given the project treats the data path as "by-construction injection-proof," column
identifiers are part of that story and should be defended.
**Fix:** Validate keys against the same bare-identifier regex used for the namespace, or
whitelist against the known columns for the label, before interpolation:
```python
if not _NS_RE.match(key):
    raise ValueError(f"unsafe property name: {key!r}")
```

### WR-05: `traverse` mutates shared connection state (`var_length_extend_max_depth`) and never restores it

**File:** `src/doxastica/backends/ladybug.py:339`
**Issue:** `self._exec(f"CALL var_length_extend_max_depth={bound}")` sets a connection-global
config to lift the 30-hop cap, but it is never reset to the default afterward. For an *injected*
connection (the `from_connection` tenant path, `owns_conn=False`), this permanently mutates a
handle the core explicitly contracts never to own/disturb (R19 tenancy). A subsequent traverse
with `max_depth=None` leaves the ceiling at 1,000,000 for the tenant's other queries on that
connection. The append-only and tenancy disciplines both argue against leaving connection state
changed behind the port.
**Fix:** Restore the prior/default value after the query (try/finally), or scope the `CALL` to
the minimum needed and document the tenant-visible side effect. At minimum, only raise the cap
when `bound` actually exceeds the default 30, to avoid needlessly mutating tenant state for
shallow walks.

## Info

### IN-01: `add_edge` accepts `props` it silently discards

**File:** `src/doxastica/backends/ladybug.py:238` and `src/doxastica/backends/memory.py:76`
**Issue:** Both adapters accept `props: dict[str, Any] | None` (with `# noqa: ARG002`) and
discard it entirely. A caller passing edge properties gets no error and no stored data — a
silent no-op that could mask a future bug when consumer-facing edges (Phase 4+) start carrying
properties. The port-parity rationale is documented, so this is informational, but a `raise
NotImplementedError` (or an explicit assertion that `props` is falsy) until edge props are
actually supported would fail loudly instead of silently dropping data.
**Fix:** Until edge props are implemented, reject non-empty `props` rather than dropping them.

### IN-02: `contract` and `_append` duplicate the append/edge-laying body

**File:** `src/doxastica/core.py:238-255` and `src/doxastica/core.py:305-322`
**Issue:** The `props` construction, `upsert_node("BeliefState", ...)`, `add_edge("HAS_REVISION", ...)`,
and `add_edge("SUPERSEDES", new, prior)` sequence is duplicated between `_append` and `contract`,
differing only in `status` and whether the value is re-encoded vs copied verbatim. The two
copies can drift (e.g. a future fix to the HAS_REVISION wiring applied to only one). Consider a
shared private helper that takes the already-resolved `value` token and `status` and lays the
node + both edges, with `_append` passing the encoded value and `contract` passing the verbatim
stored token.
**Fix:** Extract a `_append_state(scope_id, belief_id, encoded_value, source_event_id, status, prior)`
helper composing the node + HAS_REVISION + optional SUPERSEDES.

### IN-03: `_current` and `get_revision_chain` duplicate the ordering key inline

**File:** `src/doxastica/core.py:178` and `src/doxastica/core.py:334`
**Issue:** The ordering contract `lambda s: (str(s["source_event_id"]), str(s["state_id"]))` is
written out in two places (the `max` in `_current` and the `sort` in `get_revision_chain`). The
class docstrings repeatedly stress this is "the ONE place the ordering contract lives," yet it
lives in two. A change to the tiebreak in one and not the other would silently desynchronise
`_current` from `get_revision_chain` — the exact agreement the keystone invariant relies on.
**Fix:** Define a module-level `_ORDER_KEY = lambda s: (str(s["source_event_id"]), str(s["state_id"]))`
(or a named function) and use it in both call sites.

### IN-04: `contract` ends with an explicit `return None` inside a `with` block (redundant)

**File:** `src/doxastica/core.py:322`
**Issue:** The trailing `return None` at the end of the `unit_of_work` block is redundant (the
function returns `None` implicitly), and pairing it with the earlier `return None` at line 309
inside the same context manager is slightly noisy. Purely stylistic; the explicit returns do
document the always-`None` contract, so this is borderline. No behavioral impact.
**Fix:** Optional — drop the trailing `return None` or keep for documentation symmetry.

---

_Reviewed: 2026-06-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
