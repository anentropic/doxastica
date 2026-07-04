---
phase: 02-backend-adapters-schema-bootstrap-de-risking-spike
reviewed: 2026-06-15T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - src/doxastica/core.py
  - src/doxastica/errors.py
  - src/doxastica/__init__.py
  - src/doxastica/backends/__init__.py
  - src/doxastica/backends/memory.py
  - src/doxastica/backends/ladybug.py
  - tests/conftest.py
  - tests/test_backend_memory.py
  - tests/test_backend_ladybug.py
  - tests/test_backend_parity.py
  - tests/test_import_purity.py
  - pyproject.toml
  - .github/workflows/quality.yml
  - .github/workflows/pr.yml
findings:
  critical: 1
  warning: 5
  info: 4
  total: 10
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-06-15
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the Phase 2 backend-adapter wave: the driver-blind `MemoryCore` engine, the
typed error surface, the in-memory oracle, the LadybugDB reference adapter, and the
parity/isolation test suite plus CI.

The project-specific lenses largely hold up: parameterized Cypher is respected (all belief
data flows through `$param`; the only interpolations are the validated namespace, the
non-bindable label/edge-type, and the validated-int hop bound); `core.py` /
`__init__.py` / `backends/__init__.py` stay driver-blind with sanctioned function-local
imports; connection ownership (CONN-01/R19) is correctly gated on `owns_conn`; no AGM
operation bodies leaked into Phase 2.

The headline defect is in `LadybugBackend.upsert_node`: it hardcodes `state_id` as the
MERGE key for **every** label, but the schema declares different primary keys for `Scope`
(`scope_id`) and `Belief` (`belief_id`). This is a real correctness/parity bug masked only
because every test exercises `BeliefState` exclusively. Several traverse edge cases
(`max_depth=0`, the interpolated `CALL` ceiling) are untested and at least one diverges
from the oracle.

## Critical Issues

### CR-01: `upsert_node` hardcodes `state_id` MERGE key for all labels — breaks `Scope`/`Belief` upserts and oracle parity

**File:** `src/doxastica/backends/ladybug.py:187`
**Issue:**
The MERGE key column is hardcoded regardless of `label`:

```python
cypher = f"MERGE (n:{labelled} {{state_id: $id}})"
```

But `_bootstrap_schema` (lines 148-159) declares three node tables with **different**
primary keys:
- `{ns}_Scope` → PK `scope_id`
- `{ns}_Belief` → PK `belief_id`
- `{ns}_BeliefState` → PK `state_id`

`upsert_node("Scope", id, ...)` compiles to `MERGE (n:{ns}_Scope {state_id: $id})`, which
references a column (`state_id`) that does not exist on the `Scope` table — ladybug will
error, or (worse) MERGE on a non-PK property and silently lose the idempotency/uniqueness
guarantee the PK is supposed to enforce (CONN-03). The same defect hits `Belief`.

This is also a direct **oracle-parity divergence (D-05)**: `InMemoryBackend.upsert_node`
keys on `node_id` for any label, so memory and ladybug only agree for `BeliefState`. The
parity suite's `_node` helper (`tests/test_backend_parity.py:45-60`) even encodes a
workaround — it strips `state_id` from props for ladybug — which papers over the deeper
problem rather than exposing it. The bug is latent today only because every Phase 2 test
uses `BeliefState`; it becomes a live failure the moment Phase 3 upserts `Scope`/`Belief`
nodes.

**Fix:** Derive the PK column from the label instead of hardcoding it:

```python
_PK_BY_LABEL = {"Scope": "scope_id", "Belief": "belief_id", "BeliefState": "state_id"}

def upsert_node(self, label, node_id, props):
    pk = _PK_BY_LABEL[label]
    labelled = f"{self._ns}_{label}"
    params: dict[str, Any] = {"id": str(node_id)}
    set_clauses: list[str] = []
    for i, (key, value) in enumerate(props.items()):
        if key == pk:
            continue  # never SET the PK (ladybug rejects re-SET of the merge key)
        pname = f"p{i}"
        params[pname] = value
        set_clauses.append(f"n.{key} = ${pname}")
    cypher = f"MERGE (n:{labelled} {{{pk}: $id}})"
    if set_clauses:
        cypher += " SET " + ", ".join(set_clauses)
    self._exec(cypher, params)
```
Add a test that upserts a `Scope` and a `Belief` node through the ladybug backend (not just
`BeliefState`) so the parity suite would have caught this.

## Warnings

### WR-01: `upsert_node` will attempt to `SET` the primary key, raising on re-upsert

**File:** `src/doxastica/backends/ladybug.py:183-189`
**Issue:**
The SET loop iterates over **all** `props` entries with no exclusion of the PK column. If a
caller passes the PK in props (e.g. `upsert_node("BeliefState", "s1", {"state_id": "s1"})`),
the generated Cypher is `MERGE (n {state_id: $id}) SET n.state_id = $p0` — ladybug raises
because the merge key cannot be re-SET as an ordinary property. The parity test helper
(`test_backend_parity.py:45-60`) documents exactly this hazard and works around it by not
passing `state_id` to the ladybug backend. The adapter itself should be robust to it rather
than relying on every caller knowing the rule.
**Fix:** Skip the PK column in the SET loop (see CR-01 fix — `if key == pk: continue`).

### WR-02: `traverse` with `max_depth=0` produces invalid Cypher and diverges from the oracle

**File:** `src/doxastica/backends/ladybug.py:264-271`
**Issue:**
`bound = max_depth` when not None, and the only guard is `assert bound >= 0`. For
`max_depth=0`, `bound=0` and the var-length pattern becomes `*1..0`, an empty/degenerate
range. The in-memory oracle handles `max_depth=0` coherently: layer 0 is `start`, every
out-edge exceeds the bound, so it returns `reached=[]`, `frontier={start}` (when start has
any successor) — see `memory.py:122-124`. The two backends therefore disagree at
`max_depth=0`, violating D-05. The port signature (`ports.py:96-101`) types `max_depth` as
`int | None` with no stated lower bound, so `0` is a reachable input.
**Fix:** Either reject `max_depth=0` explicitly at the port boundary (document it as
invalid in `ports.py` and raise `ValueError` in both backends), or special-case `bound == 0`
in the ladybug adapter to return `([], frozenset({start}) if start has an out-edge else frozenset())`
to match the oracle. Add a parity test for `max_depth=0`.

### WR-03: `assert` statements used for runtime validation are stripped under `python -O`

**File:** `src/doxastica/backends/ladybug.py:266`, `src/doxastica/backends/ladybug.py:321-323`
**Issue:**
Two `assert`s do load-bearing work at the driver boundary:
- Line 266 `assert bound >= 0` is the *only* guard that the interpolated hop bound is
  non-negative before it is string-interpolated into Cypher. The comment calls it
  "belt-and-braces ... the bound is interpolated, never $param" — i.e. it is part of the
  injection-safety story. Under `python -O` (asserts disabled) a negative bound would be
  interpolated unchecked.
- Lines 321-323 `assert isinstance(result, lb.QueryResult)` narrows the
  `QueryResult | list[QueryResult]` union; if stripped, the function silently returns a
  `list` and downstream `.rows_as_dict()` / `.items()` calls fail with a confusing
  `AttributeError` far from the cause.

`assert` is appropriate for invariants you fully control, but a value interpolated into a
query string and a driver-return-type narrowing are better expressed as real checks.
**Fix:** Replace the bound guard with an explicit raise:
```python
if bound < 0:
    raise ValueError(f"max_depth must be non-negative; got {bound}")
```
and raise `TypeError`/`RuntimeError` for the non-`QueryResult` case instead of asserting.

### WR-04: Isolation CI job runs an unrepresentative test subset, weakening the D-02 guarantee

**File:** `.github/workflows/quality.yml:42-43`
**Issue:**
The "ladybug absent" isolation job runs only
`tests/test_import_purity.py tests/test_backend_memory.py`. It does **not** run
`tests/test_backend_parity.py`, which contains memory-only tests
(`test_value_string_round_trips_memory`, the parametrized `backend` fixture's `memory`
param) that exercise the driver-free path and should also pass with ladybug uninstalled.
More importantly, hardcoding a file list means a newly added driver-free test file is
silently excluded from the isolation guarantee — the CI proves isolation only for the two
files someone remembered to list. The whole value of the isolation job is "the driver-free
spine works with the driver gone"; an explicit allowlist erodes that over time.
**Fix:** Run the full suite in the isolation job and rely on `pytest.importorskip` to skip
the ladybug-dependent tests (the suite is already built for this — every ladybug test gates
on `importorskip`). E.g. `uv run pytest` with no file list; the ladybug params/modules skip
cleanly, and any new driver-free test is automatically covered.

### WR-05: `_validate_namespace` permits arbitrarily long / shadowing identifiers; no reserved-word or length guard

**File:** `src/doxastica/backends/ladybug.py:82-85`
**Issue:**
The regex `^[A-Za-z_][A-Za-z0-9_]*$` correctly blocks injection-shaped namespaces (the
sanctioned guard, D-04). However it places no upper bound on length and does not reject a
namespace that would collide with an unprefixed system/table name or another tenant's
prefix (e.g. `namespace="dx"` vs a tenant table already named `dx_BeliefState`). For a
library that is explicitly a *tenant in a shared embedded DB*, an unvalidated-collision
namespace is a real foot-gun: two cores with the same namespace on the same DB will share
tables (the `test_bootstrap_idempotent` test actually relies on this). This is not an
injection hole, but it is a correctness/robustness gap in the one interpolation the design
hangs its safety on.
**Fix:** Keep the regex (it is sufficient for injection), but consider documenting the
collision semantics explicitly and optionally adding a sane length cap (ladybug/Kùzu
identifier limits) so a pathological namespace fails fast with a clear message rather than
at DDL time.

## Info

### IN-01: `add_edge` / `match_nodes` interpolate the edge-type and prop-key without validation

**File:** `src/doxastica/backends/ladybug.py:206`, `src/doxastica/backends/ladybug.py:232`, `src/doxastica/backends/ladybug.py:268`
**Issue:**
The namespace is validated before interpolation, but the `edge_type` (interpolated into the
rel label at lines 206 and 268) and the prop `key` (interpolated into `n.{key}` at lines
186 and 232) are interpolated verbatim. In Phase 2 these come from a closed
`EdgeType`/schema set, so this is not currently exploitable. But the lens that justifies
the namespace guard ("DDL identifiers cannot be `$param`-bound, so validate before
interpolating") applies equally to these identifiers. If a later phase ever lets a
caller-influenced string reach `edge_type` or a prop `key`, this becomes an injection
surface with no guard. Worth a defensive note or a shared identifier-validation helper.
**Fix:** Route `edge_type` and prop keys through the same `_NS_RE`-style validation (or an
enum membership check) so the safety invariant is uniform across all interpolation points.

### IN-02: `from_connection` types the connection as `object`, deferring all type safety to a runtime cast

**File:** `src/doxastica/core.py:78-95`
**Issue:**
`conn: object` plus a `# pyright: ignore[reportArgumentType]` means a caller can pass
literally anything to `MemoryCore.from_connection`; the mistake surfaces only deep inside
`LadybugBackend.__init__`/`_bootstrap_schema` as an opaque attribute error. The driver-blind
constraint (D-02) genuinely forces `object` here (typing it as `lb.Connection` would import
the driver), so this is an accepted tradeoff, not a defect — but it is worth an explicit
runtime guard (e.g. `hasattr(conn, "execute")`) to fail fast with an actionable message
instead of a `QueryResult` `AttributeError` three frames down.
**Fix:** Add a minimal duck-type check in `LadybugBackend.__init__` before bootstrap:
`if not hasattr(conn, "execute"): raise TypeError("conn must be an lb.Connection")`.

### IN-03: `add_edge` accepts `props` but silently discards it on both backends

**File:** `src/doxastica/backends/ladybug.py:197`, `src/doxastica/backends/memory.py:76`
**Issue:**
Both adapters take `props: dict[str, Any] | None` and ignore it (`# noqa: ARG002 ... kept
for port parity`). This is intentional for Phase 2, but a silently-discarded argument is a
latent surprise: a Phase-3 caller who passes edge props expecting them to persist gets no
error and no data. Acceptable as a documented stub, flagged so it is not forgotten when
edge properties become real (HAS_REVISION in Phase 3).
**Fix:** No action in Phase 2. When edge props land, ensure both backends actually persist
them and that a parity test covers it; consider a transitional `assert props is None` if
edge props are not yet supported, so a premature caller fails loudly.

### IN-04: `_value` helper / private-attribute access pattern duplicated across test modules

**File:** `tests/test_backend_memory.py:175`, `tests/test_backend_ladybug.py:37`, `tests/test_backend_parity.py:55-60`
**Issue:**
Tests reach into `core._backend` and `backend._conn` (with `# noqa: SLF001` /
`reportPrivateUsage` suppressions) and re-implement small id-extraction helpers
(`_value`, `_ids`, `_reached_ids`) per module. The duplication is minor and the private
access is justified for white-box backend tests, but the repeated normalization helpers
could live in `conftest.py` to keep the parity contract in one place and reduce drift
between the memory and ladybug suites.
**Fix:** Hoist `_ids` / `_reached_ids` / `_frontier_ids` into a shared test helper module
or `conftest.py`. Low priority.

---

_Reviewed: 2026-06-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
