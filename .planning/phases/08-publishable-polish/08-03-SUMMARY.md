---
phase: 08-publishable-polish
plan: 03
subsystem: docs-and-packaging
tags: [docs, mkdocs, git-cliff, ci, packaging, PKG-04]
requires:
  - "Phase-1 BACK-04 backend port contract (docs/backend-contract.md)"
  - ".cliff.toml repo changelog config (group headers + docs-include-start marker)"
provides:
  - "Backend port contract published INSIDE docs_dir and rendered into the site (site/backend-contract/index.html)"
  - "Both CI changelog invocations honor .cliff.toml (docs.yml --config, release.yml config input)"
  - "Verified: fresh wheel imports and ships py.typed (9 modules, not the stale scaffold)"
affects:
  - "Published docs site nav"
  - ".github/workflows/docs.yml and release.yml changelog steps"
tech-stack:
  added: []
  patterns:
    - "Relocate-into-docs_dir (Option A) over snippet-include for publishing repo docs"
    - "Pin git-cliff to the dot-prefixed config explicitly (--config / config: input) since git-cliff's default search path is cliff.toml not .cliff.toml"
key-files:
  created:
    - docs/src/backend-contract.md
  modified:
    - mkdocs.yml
    - .github/workflows/docs.yml
    - .github/workflows/release.yml
  deleted:
    - docs/backend-contract.md
    - docs/changelog.md
decisions:
  - "Used git mv (relocation) not duplication for the contract file — no copy left at old path"
  - "release.yml uses git-cliff-action's explicit `config: .cliff.toml` input (preferred over GIT_CLIFF_CONFIG env)"
  - "Task 3 is verification-only — no edit to docs/src/backend-contract.md (no-op file-ownership anchor; Task 1 owns its relocation)"
metrics:
  duration: "~15m"
  completed: "2026-06-19"
  tasks: 3
  files-changed: 5
---

# Phase 8 Plan 03: PKG-04 Docs-and-Changelog Wiring Fixes Summary

Closed the three PKG-04 wiring defects a green build silently hid — the backend contract
now lives inside `docs_dir` and renders into the published site, both CI git-cliff calls
honor the repo's `.cliff.toml`, and a fresh wheel is proven to import and ship `py.typed`
— plus removed the orphaned sphinx/myst changelog stub.

## What Was Built

### Task 1 — Relocate backend contract into docs_dir + nav entry (PKG-04)
- `git mv docs/backend-contract.md docs/src/backend-contract.md` (Option A relocation, content preserved exactly; the file has 0 internal markdown links so `--strict` link checking is unaffected).
- Added `Backend Contract: backend-contract.md` to the mkdocs `nav:` between Home and API Reference (docs_dir-relative path, NOT `src/...`). Final nav order: Home, Backend Contract, API Reference, Changelog.
- Verified: `git-cliff --config .cliff.toml -o CHANGELOG.md` (snippet resolves under `check_paths: true`) then `mkdocs build --strict` exits 0 and `site/backend-contract/index.html` exists.
- Commit: `9ee0c35`

### Task 2 — git-cliff `--config .cliff.toml` in both workflows + delete orphan stub (PKG-04)
- `.github/workflows/docs.yml`: `uvx git-cliff -o CHANGELOG.md` → `uvx git-cliff --config .cliff.toml -o CHANGELOG.md`.
- `.github/workflows/release.yml`: added `config: .cliff.toml` input to the `orhun/git-cliff-action@v4` step (`args: --latest`, `OUTPUT`, `GITHUB_TOKEN` left unchanged).
- Deleted orphaned `docs/changelog.md` (sphinx/myst `{include}` stub outside docs_dir); `docs/src/changelog.md` (the live page) untouched.
- Verified: both greps match; configured render emits `docs-include-start` in `CHANGELOG.md` (the default config would drop it).
- Commit: `3e43bf8`

### Task 3 — Prove a fresh wheel imports and ships py.typed (PKG-04 distribution gate)
- Verification-only, no production-code edit, no workflow edit (mirrors release.yml's build+validate jobs locally).
- `uv build --out-dir /tmp/dx-dist-03` → built `doxastica-0.1.0-py3-none-any.whl`.
- Wheel ships `doxastica/py.typed` and contains 9 `doxastica/*.py` modules (a real package, not the stale 71-byte Phase-1 scaffold in the committed `dist/`).
- `import doxastica` exposes `MemoryCore` and `BeliefStore` on `__all__`.
- No tag pushed, no PyPI publish invoked (D-05 scope boundary: pipeline-ready ≠ published).
- No commit (verification-only).

## Verification Evidence

- PKG-04 publish gate: `mkdocs build --strict` green AND `site/backend-contract/index.html` present.
- `grep -q -- "--config .cliff.toml" .github/workflows/docs.yml` ✓; `grep -q ".cliff.toml" .github/workflows/release.yml` ✓.
- `grep -q 'docs-include-start' CHANGELOG.md` after configured render ✓.
- `unzip -l /tmp/dx-dist-03/*.whl | grep doxastica/py.typed` ✓; import of `MemoryCore`/`BeliefStore` ✓.
- `! test -f docs/changelog.md` ✓; `! test -f docs/backend-contract.md` ✓; `docs/src/changelog.md` present ✓.
- Wave gate: `uv run pytest` → 102 passed, 74 skipped (ladybug-extra parametrizations), 1 xfailed. Phase-7 conformance stays green.

## Threat Mitigations Applied

- T-08-07 (contract page absent from site): mitigated — gate asserts `site/backend-contract/index.html` under `--strict`.
- T-08-08 (CI git-cliff wrong config): mitigated — both workflows pinned to `.cliff.toml`; the `docs-include-start` marker (only the repo config emits it) is grepped.
- T-08-09 (stale committed dist shipped): mitigated — fresh build into `/tmp`, real modules + py.typed asserted.
- T-08-10 (PyPI publish creds): accepted/transferred — no publish performed (D-05); release.yml's OIDC path unchanged.
- T-08-SC (`ladybugdb` slopsquat): mitigated — no package install added; only `ladybug`/`uvx git-cliff`/pinned actions referenced.

## Deviations from Plan

None — plan executed exactly as written. The only "deviations" were two intentional file
deletions explicitly mandated by the plan (the contract relocation via `git mv`, and the
orphan `docs/changelog.md` removal); both are documented above and in the threat mitigations.

## Notes

- `CHANGELOG.md` (repo root) was generated locally for the gates and is gitignored — not committed (per plan).
- `site/` is gitignored — not committed.
- Local sandbox note honored: `git-cliff`, `mkdocs`, and `uv build` were run with the sandbox disabled (documented uv-sandbox panic on this macOS host); CI (ubuntu) unaffected.
- The benign mkdocs-material v2 vendor warning appeared during `--strict` build — it is NOT a `--strict` failure (RESEARCH "State of the Art").

## Self-Check: PASSED

- FOUND: docs/src/backend-contract.md
- FOUND: .planning/phases/08-publishable-polish/08-03-SUMMARY.md
- FOUND commit: 9ee0c35 (Task 1)
- FOUND commit: 3e43bf8 (Task 2)
- Task 3: verification-only, no commit (by design)
