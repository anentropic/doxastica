---
status: complete
phase: quick-260619-put
plan: 01
subsystem: repo-config
tags: [github, copilot, code-review, repo-config]
requires: []
provides: ["Copilot custom instructions: ignore .planning/ during review"]
affects: [.github/]
tech-stack:
  added: []
  patterns: []
key-files:
  created: [.github/copilot-instructions.md]
  modified: []
decisions: []
metrics:
  duration: 1min
  completed: 2026-06-19
---

# Phase quick-260619-put Plan 01: Add GitHub Copilot Instructions Summary

Added `.github/copilot-instructions.md` directing GitHub Copilot (and its automated code
review) to skip files under `.planning/`, with a one-paragraph project-context framing so
review stays focused on the zero-LLM AGM library source.

## What Was Built

A single new repo-config file, `.github/copilot-instructions.md`:

- Opens with a short project-context paragraph: doxastica is a standalone, zero-LLM Python
  library implementing an append-only AGM belief-revision core (the Kumiho architecture)
  behind a clean `BeliefStore` Protocol; review should focus on `src/` and `tests/`.
- States the operative directive in plain language, with the literal `.planning` token
  present: do not review, summarize, or comment on files under `.planning/` (GSD process
  and planning artifacts — ROADMAP, REQUIREMENTS, STATE, PROJECT, per-phase
  CONTEXT/PLAN/SUMMARY/VERIFICATION/VALIDATION docs, plus `.planning/quick/`).
- Makes the ignore directive apply explicitly to Copilot code review.

No source, tests, or packaging were touched. `dependabot.yml` and `workflows/` were left
untouched.

## Tasks Completed

| Task | Name                                                    | Commit  | Files                           |
| ---- | ------------------------------------------------------- | ------- | ------------------------------- |
| 1    | Create .github/copilot-instructions.md (.planning/ ignore) | 4c999a7 | .github/copilot-instructions.md |

## Verification

- `test -f .github/copilot-instructions.md` — PASS
- `grep -q ".planning" .github/copilot-instructions.md` — PASS
- `grep -qiE "not (be )?review|do not review|skip|ignore"` — PASS
- `git status` shows only the new `.github/copilot-instructions.md` staged/committed (no
  source/test/packaging changes); no file deletions in the commit.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: .github/copilot-instructions.md
- FOUND: commit 4c999a7
