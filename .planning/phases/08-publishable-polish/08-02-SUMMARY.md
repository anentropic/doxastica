---
phase: 08-publishable-polish
plan: 02
subsystem: docs
tags: [readme, docs, quickstart, pkg-03, framing]
requires: []
provides:
  - "PKG-03 README Kumiho reference-implementation framing (multi-scope extension, no recovery)"
  - "Runnable docs Quick Start (MemoryCore.in_memory -> revise -> query_scope)"
affects:
  - README.md
  - docs/src/index.md
tech-stack:
  added: []
  patterns:
    - "D-03 install split documented (pip install doxastica vs doxastica[ladybug])"
key-files:
  created: []
  modified:
    - README.md
    - docs/src/index.md
decisions:
  - "README links to the docs site Quick Start rather than duplicating the full example (lean README)"
  - "Quick Start uses MemoryCore.in_memory() + uuid.uuid7() so it runs under the base install with zero ladybug dependency"
metrics:
  duration: "~3 min"
  completed: 2026-06-19
  tasks: 2
  files: 2
---

# Phase 8 Plan 02: README Framing & Docs Quick Start Summary

Rewrote the stub `README.md` to lead with the PKG-03 Kumiho reference-implementation
framing and replaced the `docs/src/index.md` Quick Start TODO with a runnable, verified
zero-dependency example.

## What Was Built

### Task 1: README.md PKG-03 Kumiho framing (commit 61d2521)
Replaced the 2-line README stub with a framed document:
- **Lead paragraph** containing the literal phrases "reference implementation of Kumiho",
  "multi-scope", and "no recovery", retaining the arXiv 2603.17244 + Young Bin Park
  attribution.
- **What it is** note: standalone, append-only, zero narrative/LLM concepts, provable
  correctness via AGM/Hansson postulates as a backend conformance suite.
- **Installation** section reflecting the D-03 split: `pip install doxastica` (in-memory
  core, pydantic only) and `pip install doxastica[ladybug]` (adds the LadybugDB reference
  backend), with the uv equivalents.
- **Quick Start** pointer linking to the docs site (no example duplication).
- **License** line stating MIT and linking the LICENSE file.

The MIT `LICENSE` file was verified present (`head -1 LICENSE` -> "MIT License"); not edited.

### Task 2: docs/src/index.md runnable Quick Start (commit 14d23e4)
Replaced "TODO: Add usage examples here." with a single runnable `python` block plus prose:
- Builds the zero-dependency core via `MemoryCore.in_memory()`.
- `revise(scope_id, belief_id, value, source_event_id=uuid7())` using native `uuid.uuid7()`.
- Reads the current base with `query_scope(scope_id, BeliefFilter())`.
- A second `revise` of the same `belief_id` demonstrates append-only supersession —
  `query_scope` returns exactly the new current tail (one entry, no duplicate).

The example imports only public symbols from `doxastica.__init__` (`MemoryCore`,
`BeliefFilter`) and `uuid.uuid7`. No ladybug-specific symbol, no `.open()` — it runs under
`pip install doxastica` alone.

## Verification

All plan acceptance criteria pass:
- `grep -q "reference implementation of Kumiho" README.md` — matches.
- `grep -q "multi-scope" README.md` — matches.
- `grep -qi "no recovery" README.md` — matches.
- `grep -q "doxastica\[ladybug\]" README.md` — matches.
- `grep -c "ladybugdb" README.md` — 0 (no typosquat token; T-08-04 mitigated).
- `head -1 LICENSE | grep -q "MIT License"` — matches.
- `grep -ci "TODO" docs/src/index.md` — 0.
- `docs/src/index.md` references `MemoryCore`, `revise`, `query_scope`, `uuid7`,
  `MemoryCore.in_memory()`.
- `grep -c "ladybugdb" docs/src/index.md` — 0.

**T-08-05 (Quick Start correctness) mitigated by execution:** the example was run end-to-end
via `uv run python`, producing `{'sky-colour': 'blue'}` then `{'sky-colour': 'grey'}` with a
single-entry tail (asserted `len(base) == 1`) — confirming the inline comments and the
append-only supersession illustration are accurate before commit.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- README.md — FOUND, contains the three required framing phrases and the D-03 extra.
- docs/src/index.md — FOUND, no TODO, references MemoryCore/query_scope/uuid7.
- LICENSE — FOUND, first line "MIT License" (verified only, not edited).
- Commit 61d2521 (README) — FOUND in git log.
- Commit 14d23e4 (index.md) — FOUND in git log.
