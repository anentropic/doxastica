---
phase: 02-backend-adapters-schema-bootstrap-de-risking-spike
plan: 04
subsystem: infra
tags: [uv, packaging, optional-dependencies, github-actions, ci, ladybug, pydantic]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: BackendPort seam (ladybug is the reference backend behind the port, not the substrate)
  - phase: 02 (plans 01-03)
    provides: backends/memory.py + backends/ladybug.py + test_import_purity + parametrized conftest
provides:
  - "Option B packaging: pydantic is the only REQUIRED runtime dep; ladybug is the doxastica[ladybug] extra"
  - "Re-resolved uv.lock consistent with the reclassified pyproject"
  - "Two-environment CI: isolation job (ladybug ABSENT) + full job (--extra ladybug, both backends)"
  - "pr.yml coverage exercises both backends via --extra ladybug"
  - "Decision-grade CLAUDE.md reversal of the runtime-dep + pinned-storage constraints (D-03)"
affects: [phase-03-revise-expand, future-backend-extras, ci, packaging, release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Opt-in backend extras: [project.optional-dependencies] ladybug + all; future backends slot in here"
    - "Two-environment CI asymmetry: a base-isolation job that proves a driver is genuinely uninstalled"

key-files:
  created:
    - .planning/phases/02-backend-adapters-schema-bootstrap-de-risking-spike/02-04-SUMMARY.md
  modified:
    - pyproject.toml
    - uv.lock
    - .github/workflows/quality.yml
    - .github/workflows/pr.yml
    - CLAUDE.md

key-decisions:
  - "D-03 Option B: pydantic is the sole required runtime dep; ladybug demoted to an opt-in extra (doxastica[ladybug]) with an `all` extra; future neo4j/surrealdb extras slot in the same table."
  - "[BLOCKING] CLAUDE.md constraint reversal recorded as decision-grade (sibling to the Phase 1 3.14-floor decision): 'exactly ladybug+pydantic' -> pydantic-required/ladybug-reference-extra; 'pinned to LadybugDB / no storage abstraction' marked SUPERSEDED by the Phase-1 BackendPort (the port is the seam; the no-repository-abstraction non-goal still holds)."
  - "CI proves D-02 import isolation with teeth: Job 1 syncs dev tools WITHOUT the ladybug extra, asserts ladybug is absent, and runs import-purity + the in-memory subset; Job 2 syncs --extra ladybug and runs the full both-backend suite."

patterns-established:
  - "Backend extras pattern: a new backend is added ONLY as a further [project.optional-dependencies] extra, never as a new required dep."
  - "Isolation-CI pattern: an explicit 'assert ladybug absent' step plus a dev-only (no-extra) sync makes the two-env asymmetry mechanically real rather than implied."

requirements-completed: [BACK-03, FORMAL-06]

# Metrics
duration: 15min
completed: 2026-06-15
---

# Phase 2 Plan 04: Option B Packaging + Two-Env CI + CLAUDE.md Reversal Summary

**Demoted `ladybug` from a required runtime dep to the `doxastica[ladybug]` reference-backend extra (pydantic-only base install), re-resolved `uv.lock`, split CI into an isolation job (ladybug genuinely absent) plus a full both-backend job, and recorded the [BLOCKING] CLAUDE.md constraint reversal as a decision-grade edit.**

## Performance

- **Duration:** ~15 min (active; wall-clock spans an idle overnight boundary)
- **Started:** 2026-06-15T00:25:14Z
- **Completed:** 2026-06-15T10:12:36Z
- **Tasks:** 2
- **Files modified:** 5 (+ this SUMMARY)

## Accomplishments
- `pyproject.toml`: `[project.dependencies]` reduced to `pydantic>=2.11,<3` only; added `[project.optional-dependencies]` with `ladybug = ["ladybug>=0.17,<0.18"]`, `all = ["doxastica[ladybug]"]`, and a placeholder note for future `neo4j`/`surrealdb` extras.
- `uv.lock` re-resolved (72 packages) and consistent: `uv lock --check` exits 0; the prek `uv-lock` hook passes.
- Verified the install-surface asymmetry is REAL: a dev-only `uv sync --no-default-groups --group dev` leaves `ladybug` genuinely uninstalled (`importlib.util.find_spec('ladybug') is None`); `MemoryCore.in_memory()` works with ladybug absent; importing `doxastica.backends.ladybug` then raises `BackendDependencyError`.
- `quality.yml`: split into a `isolation` job (no ladybug extra, asserts ladybug absent, runs `tests/test_import_purity.py` + `tests/test_backend_memory.py`) and a `full` job (`uv sync --locked --dev --extra ladybug`, prek gates, full suite).
- `pr.yml`: coverage sync now uses `--extra ladybug` so coverage exercises both backends.
- `CLAUDE.md`: the runtime-dep and pinned-storage prose reversed and marked as a recorded Phase 2 D-03 decision (3 mentions of "reference-backend extra"); the "exactly ladybug+pydantic" and "pinned to LadybugDB" framings no longer read as absolute current constraints.
- Full both-backend suite green: `68 passed, 1 xfailed` (the xfail is the pre-existing value-coercion case, DEF-02-01).

## Task Commits

Each task was committed atomically:

1. **Task 1: Option B pyproject restructure + uv.lock re-resolve** - `089c048` (build)
2. **Task 2: Two-environment CI + [BLOCKING] CLAUDE.md reversal** - `9d4bbe7` (ci)

**Plan metadata:** see final docs commit (this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md + deferred-items.md)

## Files Created/Modified
- `pyproject.toml` - pydantic-only required dep; `[project.optional-dependencies]` ladybug + all extras
- `uv.lock` - re-resolved after the ladybug demotion (consistent with `uv lock --check`)
- `.github/workflows/quality.yml` - two-env CI: `isolation` (ladybug absent) + `full` (`--extra ladybug`)
- `.github/workflows/pr.yml` - coverage syncs `--extra ladybug` for both-backend coverage
- `CLAUDE.md` - decision-grade reversal of the runtime-dep + pinned-storage constraints (D-03)
- `.planning/.../deferred-items.md` - logged DEF-02-03 (out-of-scope prek nits)

## Decisions Made
- See `key-decisions` frontmatter. In short: D-03 Option B (pydantic-only required, ladybug extra), the recorded CLAUDE.md constraint reversal, and the explicit "assert ladybug absent" isolation-CI step that makes the two-env asymmetry mechanical rather than implied.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `PyYAML` absent in the project venv broke the plan's YAML-lint verify command**
- **Found during:** Task 2 (workflow YAML validation)
- **Issue:** The plan's verify command `uv run python -c "import yaml; ..."` failed with `ModuleNotFoundError: No module named 'yaml'` — PyYAML is not a project dependency (correctly so; adding it would violate the runtime-dep posture).
- **Fix:** Validated both workflow YAMLs via `uvx --from pyyaml python -c "import yaml; [yaml.safe_load(open(p)) for p in (...)]; print('yaml-ok')"` (ephemeral, no new project dep). Both files parse: `yaml-ok`.
- **Files modified:** none (verification-only)
- **Verification:** `uvx --from pyyaml` parse prints `yaml-ok`; prek's `check yaml` hook also passes on the two workflow files.
- **Committed in:** n/a (no source change)

---

**Total deviations:** 1 auto-fixed (1 blocking, verification-only).
**Impact on plan:** No source change; the verify mechanism was substituted to avoid introducing a forbidden dependency. No scope creep.

## Issues Encountered
- **macOS uv sandbox panic (known repo issue).** `uv lock` / `uv sync` panicked under the sandbox (`system_configuration` NULL-object panic). Per the documented repo workaround (user memory: `uv-sandbox-panic-workaround`), re-ran the specific uv lock/sync commands with the sandbox disabled; everything else stayed sandboxed. Resolved cleanly.
- **prek `git stash` worktree hazard.** A `git stash`/`stash pop` used to test the HEAD state of out-of-scope files left my Task-2 working edits in the stash on pop (conflict retained the entry). Recovered by reverting the out-of-scope prek auto-fixes to HEAD, then `git stash pop` applied my three task-file edits cleanly; stash dropped. All Task-2 edits verified present afterward (`reference-backend extra`=3, `isolation:`=1, `extra ladybug` in pr.yml=1). No work lost.
- **Out-of-scope prek auto-fixes (deferred, NOT bundled).** `prek run --all-files` auto-fixes `.gitignore` (trailing whitespace on template comments) and `src/doxastica/backends/ladybug.py` (a `ruff-format` line-rejoin). Both pre-date this plan and are outside its authored file set; reverted to HEAD and logged as `DEF-02-03` in `deferred-items.md`. CI Job 2's `prek run --all-files` will flag them until a future housekeeping pass applies the no-op fixes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Packaging now matches the Phase-1 `BackendPort` seam: pydantic-only base install ships a working in-memory AGM core; `doxastica[ladybug]` adds the reference backend. Phase 3 (`revise`/`expand`/`contract`) can build on a clean, dependency-light core.
- D-02 import isolation now has CI teeth (the base-isolation job proves the in-memory spine works with ladybug uninstalled) — the foundation for the Phase-7 oracle-parity guarantee.
- Note for CI: `DEF-02-03` (pre-existing prek nits in `.gitignore` + `ladybug.py`) should be cleared in a quick housekeeping commit so Job 2's `prek run --all-files` stays green.

## Self-Check: PASSED

All claimed files exist on disk (pyproject.toml, uv.lock, quality.yml, pr.yml, CLAUDE.md, 02-04-SUMMARY.md) and both task commits are in git history (`089c048`, `9d4bbe7`).

---
*Phase: 02-backend-adapters-schema-bootstrap-de-risking-spike*
*Completed: 2026-06-15*
