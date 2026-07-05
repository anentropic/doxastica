---
phase: 10-stance-formal-proof-docs
plan: 04
subsystem: docs
tags: [stance, docs, tutorial, mkdocs, packaging, agm, belief-revision, ladybug, memory-backend]

# Dependency graph
requires:
  - phase: 09-stance
    provides: "Stance type on models.py, revise/expand stance threading, BeliefState.stance"
  - phase: 10-stance-formal-proof-docs (10-01)
    provides: "widened oracle + SKIP-not-fail backend fixture (conftest)"
  - phase: 10-stance-formal-proof-docs (10-02)
    provides: "order-law + no-arithmetic proofs"
  - phase: 10-stance-formal-proof-docs (10-03)
    provides: "stance-quantified persistence proofs (both backends)"
provides:
  - "Stance exported from the package root (from doxastica import Stance)"
  - "Cluedo tutorial teaches the within-scope stance gradient + one reader-side ordinal decision + stance/scope reconciliation"
  - "SC4 dual-env parity confirmation: green WITH extra, SKIP-not-fail WITHOUT"
affects: [verification, code-review, publishable-docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Package-root re-export of a public parameter type (Stance) alongside its sibling Status — avoids an internal-path leak in public docs (D-13)"
    - "Tutorial threads stance on repeated same-value revises to show a within-scope epistemic gradient; the reader owns the ordinal comparison (D-10)"

key-files:
  created: []
  modified:
    - "src/doxastica/__init__.py"
    - "docs/src/tutorials/cluedo-detective.md"

key-decisions:
  - "Exported Stance from __init__.py (import block + __all__, alphabetical near Status) — the ONE deliberate behavior-neutral src change of the phase (D-13)"
  - "Threaded the gradient onto the existing culprit belief: Plum enters suspected after Contradiction #1, then hardens believed -> certain as evidence lands — reuses the narrative rather than adding a parallel belief"
  - "Single reader-side decision gate (if culprit.stance >= Stance.believed) in the new Step 6; the consolidated script asserts stance identity (is Stance.certain) to keep exactly ONE decision-driving comparison"
  - "Reconciliation delivered as an admonition callout ('A certain stance is not the certain scope') holding within-scope degree apart from the cross-scope certain/provisional split (D-09)"
  - "Renumbered downstream steps (old 6-9 -> 7-10) and refreshed the two forward Step-N cross-references; verification section stays Step 11"

patterns-established:
  - "Pattern: docs code blocks are executed end-to-end before committing (consolidated script run under uv) so a tutorial snippet cannot silently drift from the API"
  - "Pattern: signature-ref refresh is a grep-then-verify — live core.revise(...) calls that omit stance stay valid (RESEARCH A3); only prose enumerating the roster would need editing, and none exists"

requirements-completed: [DOCS-01, STANCE-07]

# Metrics
duration: 25min
completed: 2026-07-05
---

# Phase 10 Plan 04: Stance Export, Tutorial & Dual-Backend Parity Summary

**Exported `Stance` from the package root (the one deliberate behavior-neutral `src/` change), extended the Cluedo tutorial with a within-scope `suspected → believed → certain` gradient plus a single reader-side ordinal decision gate and a stance-vs-scope reconciliation callout, and confirmed the widened M0 conformance suite stays green on both backends with correct SKIP-not-fail behavior when the ladybug driver is absent.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-05T00:52:00Z
- **Completed:** 2026-07-05T01:17:00Z

## What Was Built

### Task 1 — Export `Stance` (D-13)
Added `Stance` to the `from doxastica.models import (...)` block and to `__all__` in
`src/doxastica/__init__.py`, alphabetically alongside `Status`. `Stance` was already a public
parameter type on `revise`/`expand`, yet — unlike `Status` — it was not importable from the
package root, forcing an internal-path import in the tutorial. This is packaging surface only: no
new behavior, no signature change. `from doxastica import Stance` now works. The change is limited
to `__init__.py` (`git diff --name-only src/` lists only that file).

### Task 2 — Stance narrative in the Cluedo tutorial (SC5 / DOCS-01)
Extended `docs/src/tutorials/cluedo-detective.md`:
- **Gradient (D-10):** after Contradiction #1 supersedes Mustard, `culprit="Plum"` now enters at
  `stance=Stance.suspected`; a new **Step 6** hardens the *same value* up the ladder
  (`believed`, then `certain`) as evidence lands — confidence rises without changing who is
  accused. All three members (`suspected`, `believed`, `certain`) appear.
- **One reader-side decision (D-10):** a single `if culprit.stance >= Stance.believed:`
  accuse/keep-gathering gate, with prose stating the comparison is the *reader's* policy — the
  core stores and returns stance and never interprets it.
- **Reconciliation (D-09):** a `!!! warning "A certain *stance* is not the certain *scope*"`
  callout holds the *within-scope* epistemic degree apart from the *cross-scope*
  certain/provisional scope split; a `"theory"` belief at `Stance.certain` is still provisional
  and revisable, never promoted into the world scope.
- **Import + signature refs (D-11):** both code blocks use `from doxastica import Stance`; the
  consolidated Step 11 program was refreshed and runs green. A grep confirmed no prose enumerates
  the `revise`/`expand` parameter roster (RESEARCH A3), and live calls that omit `stance` stay
  valid — so no other doc file needed editing; reference-page signatures auto-render from source.
- Downstream steps renumbered (old 6–9 → 7–10) with the two forward `Step N` cross-references
  refreshed; the mapping table and both learning-outcome lists gained a stance entry.

### Task 3 — Dual-backend parity confirmation (SC4 / D-12)
No code written — this is the phase-gate confirmation over the fully-widened Wave-1 suite.

## SC4 Dual-Env Parity Result (D-12)

| Environment | Command | Result |
|-------------|---------|--------|
| **WITH** `--extra ladybug` | `uv sync --locked --dev --extra ladybug && uv run pytest -q` | **573 passed, 1 xfailed** — both backends green, exit 0 |
| **WITHOUT** the extra | `uv sync --locked --dev && uv run pytest -q -rs` | **467 passed, 88 skipped, 1 xfailed** — exit 0 |

- **Skip count without the extra: 88** — every skip is a `pytest.importorskip('ladybug')`
  SKIP-not-fail, surfaced explicitly in the `-rs` summary (e.g. `tests/test_scope_at.py`,
  `tests/test_revision_spine.py`, `tests/test_stance_persistence.py`). **Zero ladybug failures,
  zero silent passes** — skips are surfaced, never counted as passes (auto-memory: skipped tests
  are a red flag).
- CI-parity restored afterward with `uv sync --locked --dev --extra ladybug` (ladybug 0.17.1
  reinstalled).

## Verification / Phase Gate

All acceptance criteria and the phase gate pass:

- `uv run python -c "from doxastica import Stance"` → exits 0; `Stance.certain.name == 'certain'`.
- Tutorial grep: `Stance.suspected`/`Stance.believed`/`Stance.certain` all present;
  `stance >= Stance.believed` decision gate = 1; `from doxastica import` = 2; internal-path
  import `from doxastica.models import Stance` = 0; `within-scope`/`cross-scope` reconciliation
  present.
- The consolidated tutorial program runs green end-to-end under `uv run python`
  (`Accuse Plum.` → `All checks passed.`).
- **Process-ID leakage grep — clean:** zero matches for `D-0`, `STANCE-`, `DOCS-`, `Phase [0-9]`,
  `SC[0-9]` in both the tutorial source and the built site
  (`site/tutorials/cluedo-detective/index.html`).
- **`prek run --all-files` — all Passed** under CI-parity env (`uv sync --locked --dev --extra
  ladybug`): trailing-whitespace, end-of-file, toml, yaml, ruff, ruff-format, uv-lock,
  basedpyright, blacken-docs.
- **`uv run mkdocs build --strict` — green** (docs group synced): no broken cross-refs/nav.

## Deviations from Plan

None — plan executed exactly as written. Rules 1–3 were not triggered. One expected env nuance:
the mkdocs `--strict` gate is a separate CI job from `prek`, so `--group docs` must be synced to
run it (the prek CI-parity sync `--dev --extra ladybug` does not include mkdocs); handled by
syncing `--dev --group docs --extra ladybug` for that gate.

## Known Stubs

None. `Stance` is a shipped, fully-wired public type (Phase 9); the tutorial code executes against
the real core with real data.

## Threat Flags

None. The `Stance` export is packaging surface (no new external input reaches `src/`); the docs
leakage check (T-10-04-SC, disposition `mitigate`) was applied and is clean.

## Self-Check: PASSED

All modified files exist on disk; both task commits (562fb8a, b84f5f5) are present in git history.
