---
phase: 08-publishable-polish
plan: 01
subsystem: infra
tags: [packaging, pyproject, pypi, uv_build, pep639, classifiers, metadata]

# Dependency graph
requires:
  - phase: 02-backend-adapters
    provides: "D-03 packaging split (pydantic sole required dep; ladybug the [ladybug] extra)"
  - phase: 01-foundation
    provides: "CONTEXT #2 3.14-floor lock; requires-python = '>=3.14'"
provides:
  - "PyPI-ready [project] metadata (license=MIT, license-files, keywords, classifiers, [project.urls]) emitted into wheel METADATA"
  - "REQUIREMENTS PKG-02 + ROADMAP Phase-8 SC1 prose reconciled to the decided D-03 / 3.14-only bar"
affects: [08-02, 08-03, publish, release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PEP 639 SPDX license expression (license = \"MIT\") emitted by uv_build as License-Expression in wheel METADATA"

key-files:
  created:
    - .planning/phases/08-publishable-polish/08-01-SUMMARY.md
  modified:
    - pyproject.toml
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "PyPI metadata added additively to [project]; dependencies, optional-dependencies, and requires-python left untouched (D-03 split + 3.14 floor are LOCKED)"
  - "Used PEP 639 SPDX `license = \"MIT\"` (uv_build supports it) rather than a deprecated license-classifier-only approach; the MIT OSI classifier is also retained for PyPI faceting"

patterns-established:
  - "Pattern: PyPI-readiness metadata lives in [project] (license/license-files/keywords/classifiers) + a [project.urls] table; verified by grepping the fresh wheel METADATA, never the committed dist/"

requirements-completed: [PKG-02, PKG-04]

# Metrics
duration: 2min
completed: 2026-06-19
---

# Phase 8 Plan 01: PyPI Metadata + Acceptance-Prose Reconciliation Summary

**Added PEP 639 license / classifiers / keywords / project URLs to pyproject.toml so the fresh wheel METADATA is PyPI-ready, and corrected the stale REQUIREMENTS PKG-02 + ROADMAP SC1 prose to the decided D-03 (pydantic-sole-required, ladybug-extra) and 3.14-only bar.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-19T15:08:08Z
- **Completed:** 2026-06-19T15:09:37Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `pyproject.toml [project]` now declares `license = "MIT"` (PEP 639 SPDX), `license-files = ["LICENSE"]`, `keywords`, five PyPI `classifiers`, and a new `[project.urls]` table (Homepage/Documentation/Repository) — additive only.
- A fresh `uv build` wheel METADATA renders `License-Expression: MIT`, all five `Classifier:` lines, three `Project-URL:` lines, `Requires-Dist: pydantic>=2.11,<3` (required), and ladybug ONLY under `extra == 'ladybug'` / `extra == 'all'`; `Requires-Python: >=3.14` unchanged — proving the D-03 dependency contract intact (T-08-01 / T-08-SC mitigations hold).
- CI matrix verified 3.14-only across all `.github/workflows` (no `3.11`), satisfying the PKG-02 CI-matrix bar (verify-only; no workflow edit).
- REQUIREMENTS PKG-02 and ROADMAP Phase-8 SC1 now read the decided bar (pydantic sole required dep, ladybug the `[ladybug]` extra, 3.14-only matrix) with inline D-03 / CONTEXT #2 citations; no stale `exactly ladybug + pydantic` / `3.11 (floor)` strings remain. Requirement IDs, checkbox states, and the Traceability table are unchanged.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add PyPI-ready metadata to pyproject.toml; verify the D-03/3.14 bar holds (PKG-04 metadata, PKG-02)** - `641c49b` (feat)
2. **Task 2: Correct stale PKG-02 / SC1 prose to the decided bar (D-02)** - `3904e33` (docs)

**Plan metadata:** see final docs commit below.

## Files Created/Modified
- `pyproject.toml` - Added `license`, `license-files`, `keywords`, `classifiers` to `[project]` and a new `[project.urls]` table; dependency/version declarations untouched.
- `.planning/REQUIREMENTS.md` - Corrected PKG-02 bullet to the decided bar with D-03 / CONTEXT #2 citations.
- `.planning/ROADMAP.md` - Corrected Phase-8 Success-Criterion-1 to the same decided bar with citations.
- `.planning/phases/08-publishable-polish/08-01-SUMMARY.md` - This summary.

## Decisions Made
- Followed the plan as specified. Used PEP 639 SPDX `license = "MIT"` (the modern uv_build-supported form) which emits `License-Expression: MIT` in METADATA; the OSI MIT classifier is also retained for PyPI faceting. No runtime dependency added (CLAUDE.md: pydantic is the sole required dep).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `uv build` panics under the local macOS command sandbox (documented uv-sandbox issue). Re-ran the verification with the sandbox disabled per the plan's sandbox note; the build succeeded and all METADATA assertions passed. CI (ubuntu) is unaffected.

## User Setup Required
None - no external service configuration required. (Actual PyPI publish remains out of scope this phase — pipeline-ready != published.)

## Next Phase Readiness
- PyPI-ready metadata is in place; remaining Phase-8 plans (08-02 docs/contract-page + index Quick Start; 08-03 README framing, git-cliff `--config` wiring, orphan-changelog cleanup, fresh-wheel proof) are unaffected and can proceed.
- The runtime dependency contract (pydantic sole required, ladybug extra) is provably intact in the built artifact — no blockers introduced.

## Threat Surface
No new security-relevant surface introduced. The threat register's `mitigate` items hold: T-08-01 (slipped required dep) and T-08-SC (`ladybugdb` slopsquat) are asserted clean by the METADATA grep (pydantic required, ladybug only under the extra, name preserved as `ladybug`); T-08-02 (URLs) hardcoded to the canonical `github.com/anentropic/doxastica` + `anentropic.github.io/doxastica`. No secrets added (T-08-03 accept).

## Self-Check: PASSED

All created/modified files exist on disk (pyproject.toml, REQUIREMENTS.md, ROADMAP.md, 08-01-SUMMARY.md) and both task commits are present in git history (`641c49b`, `3904e33`).

---
*Phase: 08-publishable-polish*
*Completed: 2026-06-19*
