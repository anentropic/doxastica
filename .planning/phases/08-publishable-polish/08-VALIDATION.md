---
phase: 8
slug: publishable-polish
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-19
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Docs/packaging phase: validation is "the strict docs build publishes the contract page",
> "a fresh wheel installs + imports + ships py.typed", and "the configured git-cliff renders
> the changelog". The existing Phase-7 conformance suite is the frozen "don't regress" gate.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (existing conformance suite — unchanged) + shell/CLI smoke gates for packaging & docs |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `git-cliff --config .cliff.toml -o CHANGELOG.md && uv run --no-sync mkdocs build --strict` |
| **Full suite command** | `uv run pytest && uv build && uv run --no-sync mkdocs build --strict` |
| **Estimated runtime** | ~60 seconds (pytest conformance suite dominates; docs build ~5s, wheel build ~5s) |

---

## Sampling Rate

- **After every task commit:** docs tasks → `uv run --no-sync mkdocs build --strict`; packaging tasks → `uv build` smoke; changelog task → `git-cliff --config .cliff.toml -o CHANGELOG.md`
- **After every plan wave:** Full suite — `uv run pytest` (Phase-7 conformance MUST stay green), strict docs build with contract page, fresh wheel import
- **Before `/gsd-verify-work`:** All three packaging/docs gates green AND the conformance suite green
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 8-PKG02-a | TBD | 1 | PKG-02 | — | Required dep = pydantic only; ladybug is an extra | smoke | `unzip -p dist/*.whl '*/METADATA' \| grep -E 'Requires-Dist: pydantic'` then confirm ladybug only under `extra == 'ladybug'` | ✅ (build) | ✅ green |
| 8-PKG02-b | TBD | 1 | PKG-02 | — | No NVM imports; import-purity intact | unit | `uv run pytest` (existing import-purity scan) | ✅ existing | ✅ green |
| 8-PKG02-c | TBD | 1 | PKG-02 | — | CI matrix is 3.14-only (decided bar) | grep | `grep -rh 'python-version' .github/workflows` → only `["3.14"]` | ✅ verified | ✅ green |
| 8-PKG03-a | TBD | 1 | PKG-03 | — | MIT LICENSE present | smoke | `head -1 LICENSE \| grep -q "MIT License"` | ✅ | ✅ green |
| 8-PKG03-b | TBD | 1 | PKG-03 | — | README leads with Kumiho framing | grep | `grep -q "reference implementation of Kumiho" README.md && grep -q "multi-scope" README.md && grep -q "no recovery" README.md` | ✅ done | ✅ green |
| 8-PKG04-a | TBD | 1 | PKG-04 | — | Docs build green AND contract page published | smoke | `uv run --no-sync mkdocs build --strict && test -f site/backend-contract/index.html` | ✅ done | ✅ green |
| 8-PKG04-b | TBD | 1 | PKG-04 | — | Changelog renders from configured git-cliff | smoke | `git-cliff --config .cliff.toml -o CHANGELOG.md && grep -q 'docs-include-start' CHANGELOG.md` | ✅ done | ✅ green |
| 8-PKG04-c | TBD | 1 | PKG-04 | — | Fresh wheel imports + ships py.typed | smoke | `uv build && unzip -l dist/*.whl \| grep py.typed && python -c "import doxastica"` | ✅ (build) | ✅ green |
| 8-PKG04-d | TBD | 1 | PKG-04 | — | PyPI-ready metadata (license/classifiers/urls) | smoke | `unzip -p dist/*.whl '*/METADATA' \| grep -E 'License\|Classifier\|Project-URL'` | ✅ done | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `README.md` — leads with PKG-03 Kumiho framing ("standalone reference implementation of Kumiho (arXiv 2603.17244), multi-scope extension, no recovery") — 08-02
- [x] `docs/src/backend-contract.md` + mkdocs `nav` entry — port contract published into the site (PKG-04) — 08-03
- [x] `docs/src/index.md` — runnable Quick Start; "TODO" removed — 08-02
- [x] `pyproject.toml` — `license`, `classifiers`, `keywords`, `[project.urls]` added (PyPI-ready) — 08-01
- [x] `.github/workflows/docs.yml` + `release.yml` — git-cliff pinned to `.cliff.toml` — 08-03
- [x] `.planning/REQUIREMENTS.md` (PKG-02) + `.planning/ROADMAP.md` (Phase 8 SC1) — stale "exactly ladybug+pydantic" / "3.11 floor" wording corrected to the decided bar — 08-01
- [x] (Optional) `dist/` confirmed already gitignored + untracked; orphan `docs/changelog.md` deleted — 08-03

*Existing pytest conformance suite (Phase 7) covers all behavioral regression — no new test framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Published docs site renders the contract page in the live nav | PKG-04 | Full GitHub Pages publish requires Pages "GitHub Actions" source set in repo settings (out-of-band) | After merge to main, confirm the Docs workflow deploys and the contract page is reachable from the site nav |
| PyPI release actually publishes | PKG-04 | Tag-triggered, OUT of scope this phase (pipeline-ready ≠ published) | Not exercised — `release.yml` fires only on a `v*` tag push |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-19

---

## Validation Audit 2026-06-19

| Metric | Count |
|--------|-------|
| Requirements audited | 3 (PKG-02, PKG-03, PKG-04) |
| Automated (COVERED) | 3 (CLI/smoke gates + existing pytest import-purity) |
| Manual-only | 2 (live GitHub Pages publish; actual PyPI tag publish — both out-of-band / out-of-scope by design) |
| Gaps found | 0 |
| Tests generated | 0 (packaging/docs validation is CLI smoke; no pytest files needed) |
| Escalated | 0 |

`/gsd-validate-phase 8` (State A audit): all 9 Per-Task rows confirmed green this session
(grep gates re-run live: README framing, MIT LICENSE, contract page in `docs/src/` + nav,
git-cliff `--config .cliff.toml` in both workflows, CI 3.14-only, index.md TODO-free,
orphan changelog absent). Build/wheel gates corroborated by `08-VERIFICATION.md` (13/13
live evidence). The 2 manual-only items (Pages publish, PyPI tag) are deliberately
out-of-scope (pipeline-ready ≠ published). No gaps; metadata-completion only.
