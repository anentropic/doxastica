# Deferred Items — Phase 02

Discoveries surfaced during execution that are out of the current plan's authored scope.
Logged for the owning future plan/phase; NOT fixed here.

## DEF-02-01 — ladybug coerces brace/bracket-shaped STRING params (value-opacity hazard)

**Found during:** Plan 02-02, Task 2 (LadybugBackend primitives spike).
**Severity:** High for Phase 3+ (value storage); zero impact on Phase 2 scope (no value
fidelity is asserted in this phase — ids/edges/traverse only).

**What:** `ladybug` 0.17.1 parameter type-inference parses a Python `str` whose entire content
is a valid Cypher struct/list literal and binds it as a STRUCT / LIST rather than a STRING.
Stored into a STRING column it is re-serialized in Cypher literal form, stripping JSON quotes —
the value does NOT round-trip verbatim.

Verified live (Python 3.14.2 / ladybug 0.17.1):

| Input (json.dumps)        | Round-trips? | Stored as              |
|---------------------------|--------------|------------------------|
| `'{"x": 2}'`              | NO           | `'{x: 2}'`             |
| `'{"a": {"b": 1}}'`       | NO           | `'{a: {b: 1}}'`        |
| `'[1, 2, 3]'`             | NO           | `'[1,2,3]'`            |
| `'"hello"'` (json string) | YES          | `'"hello"'`            |
| `'42'`, `'true'`          | YES          | verbatim               |
| `' {"x":2}'` (leading sp) | YES          | verbatim (parse fails) |
| `'{garbage !!!}'`         | YES          | verbatim (parse fails) |

Root cause exposed by the binder error `+(STRING, STRUCT(x INT8))` — the param is typed STRUCT
at bind time. There is no driver-side typed-Value API in 0.17.1 (`lb.Value` does not exist);
`prepare()` is deprecated and does not change inference; `cast($v AS STRING)` runs AFTER the
param is already a STRUCT and does not help.

**Why it matters:** BACK-04 §6 requires the backend to store/return `value` blobs verbatim.
The core JSON-encodes belief `value`s (BACK-04 §6) — object/array values are exactly the
brace/bracket shapes that get coerced. This WILL bite when real belief values are written
(Phase 3 `revise`/`expand`).

**Disposition:** Defer the fix to the Phase 3 value-encoding contract (the core owns value
encoding per BACK-04 §6, which is explicitly OUT of Phase 2 scope). Candidate fixes for the
owning plan to choose among (adapter-internal, port unchanged):
  - core/backend wraps the opaque `value` in a coercion-proof envelope before binding (e.g. a
    sentinel prefix the backend strips on read), OR
  - the backend applies a reversible STRING-forcing transform to the `value` column only.
The parity suite in Plan 02-03 should add a value-round-trip case so this is caught mechanically
and the chosen Phase-3 fix is locked by a regression test.

**Threat link:** Relates to T-02-02 (value opacity) — opacity is currently violated by the
driver's inference, not by interpolation; the mitigation moves from "always $param" to
"$param + coercion-proof value encoding".

## DEF-02-02 — pre-existing basedpyright errors in tests/test_backend_memory.py

**Found during:** Plan 02-02 full-project basedpyright run.
**Severity:** Low (test-only; tests pass at runtime).

`tests/test_backend_memory.py` lines 75, 90, 103 raise
`reportArgumentType: Argument of type "Generator[object, None, None]" cannot be assigned to
... "sorted"` — `sorted(_value(r) for r in reached)` where `_value` is typed `-> object`.
These pre-date Plan 02-02 (the file is from Plan 02-01 and is unchanged by 02-02), so they are
OUT of this plan's scope (SCOPE BOUNDARY: only auto-fix issues directly caused by the current
task). Fix by typing `_value` to return a comparable (e.g. `str`) or annotating the
comprehension. Owning plan: a 02-01 follow-up or the 02-03 parity work that also touches the
memory backend tests.

## DEF-02-03 — pre-existing prek formatting nits in `.gitignore` + `backends/ladybug.py`

**Found during:** Plan 02-04, Task 2 (`prek run --all-files` while preparing the CI/CLAUDE.md commit).
**Severity:** Low (cosmetic; no runtime/typing impact).

`prek run --all-files` auto-fixes two files NOT in this plan's authored file set:
  - `.gitignore` — `trailing-whitespace` on two template comment lines (lines ~198, ~200 of the
    GitHub Python `.gitignore` boilerplate).
  - `src/doxastica/backends/ladybug.py` — `ruff-format` rejoins a `frozenset(...)` generator that
    was hand-wrapped in Plan 02-03; the joined form is under the 100-col line length.

Both pre-date Plan 02-04 (they exist at the plan's base commit, unrelated to the dependency
reclassification / CI / CLAUDE.md edits). Per the SCOPE BOUNDARY they were NOT bundled into the
02-04 commits and were reverted to HEAD. **Note for CI:** Job 2's `prek run --all-files` will
flag these until fixed. Owning plan: any future plan touching `backends/ladybug.py` (or a quick
`prek run --all-files && git commit` housekeeping pass). Fix is a no-op apply of the prek
auto-fixes — zero behavior change.
