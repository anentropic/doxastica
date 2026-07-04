# Phase 8: Publishable Polish - Research

**Researched:** 2026-06-19
**Domain:** Python OSS packaging & publication (uv build / PyPI metadata, mkdocs-material + mkdocstrings docs site, git-cliff changelog, GitHub Actions release pipeline)
**Confidence:** HIGH (all findings verified empirically against the live tree this session)

## Summary

Phase 8 is a **verify-and-wire** phase, not a build-from-scratch phase. The cookiecutter
template plus Phases 1–7 already front-loaded almost all the publication infrastructure:
`pyproject.toml` already encodes the D-03 packaging split and the 3.14 floor correctly,
`mkdocs.yml` is fully wired (mkdocs-material + mkdocstrings auto-API-reference + a
git-cliff-fed changelog page), all seven GitHub Actions workflows exist (ci, quality,
release, docs, pr, weekly, dependabot), the MIT `LICENSE` is present, `py.typed` ships, and
a `mkdocs build --strict` **passes today** (verified this session — the only output is a
benign mkdocs-material v2 vendor warning, not a build error).

The genuine gaps are content + four concrete wiring defects, not infrastructure. The single
most important correction is that **the acceptance bar in ROADMAP SC1 and REQUIREMENTS PKG-02
is stale** — it still says "exactly ladybug + pydantic" runtime deps and "Python 3.11 floor +
3.14", both of which two locked decisions (D-03 packaging reversal; CONTEXT #2 3.14-floor
lock) already superseded and which `pyproject.toml` and every workflow already encode
correctly. Correcting that stale prose is in-scope for this phase. The other gaps: the
README is a 2-line stub (needs the PKG-03 Kumiho framing), `docs/backend-contract.md` lives
*outside* `docs_dir` and is absent from the published site (PKG-04 "publishes the port
contract" is currently **not** satisfied), `docs/src/index.md` has a "TODO" Quick Start, the
committed `dist/` wheel is a stale 71-byte Phase-1 scaffold (a fresh `uv build` packages all
9 modules correctly — verified), `pyproject.toml` lacks PyPI-readiness metadata
(`license`, `classifiers`, `[project.urls]`), and the changelog workflows invoke git-cliff
**without** `--config .cliff.toml` so the repo's custom config (with the docs-include marker)
is silently ignored.

**Primary recommendation:** Treat this phase as four wiring fixes (contract page → docs_dir +
nav; git-cliff `--config` flag; PyPI metadata fields; fresh dist rebuild) plus two content
fills (README, index.md Quick Start) plus the stale-text corrections, then prove the bar with
three validation gates: `mkdocs build --strict` green *with the contract page in nav*, a fresh
`uv build` wheel that imports, and a `git-cliff --config .cliff.toml` changelog that renders in
the docs.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Runtime dependency declaration | Packaging (`pyproject.toml`) | — | D-03 split lives in `[project.dependencies]` + `[project.optional-dependencies]` |
| Distribution build (wheel/sdist) | Build backend (`uv_build`) | CI (`release.yml` build job) | uv_build reads pyproject; release.yml automates it on tag |
| API reference docs | Docs site (mkdocstrings) | `docs/scripts/gen_ref_pages.py` | Auto-generated from `src/` docstrings at build time |
| Backend port contract publication | Docs site (mkdocs nav) | `docs/src/backend-contract.md` | Must be reachable from the built site, not just a repo file |
| Changelog generation | Tooling (git-cliff) | CI (`docs.yml`, `release.yml`) | git-cliff reads `.cliff.toml` + git history; CI runs it pre-build / on-tag |
| Publish to PyPI | CI (`release.yml` publish job) | PyPI trusted publishing | Tag-triggered; OUT of scope to actually fire (pipeline-ready ≠ published) |
| Docs deploy | CI (`docs.yml`) | GitHub Pages | Push-to-main triggered |

## Standard Stack

> No new packages are introduced in Phase 8. All tooling already exists, is pinned in
> `pyproject.toml`, and is locked in `uv.lock`. Versions verified against the live env this
> session.

### Core (already present — verify, do not add)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.13.4 (pin `>=2.11,<3`) | Sole REQUIRED runtime dep (D-03) | `[VERIFIED: uv run python -c import pydantic]` |
| ladybug | 0.17.1 (pin `>=0.17,<0.18`) | Reference-backend OPTIONAL extra `[ladybug]` (D-03) | `[VERIFIED: uv.lock name = "ladybug"; ladybugdb absent (0 matches)]` |
| hypothesis | 6.155.2 (pin `>=6.155`) | Dev group — property suite | `[VERIFIED: uv run python -c import hypothesis]` |

### Supporting (docs + build + changelog tooling — already in groups)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mkdocs | `>=1.6.0` | Docs site generator | docs group |
| mkdocs-material | 9.7.x (pin `>=9.7.0`) | Theme | docs group `[VERIFIED: mkdocs build ran]` |
| mkdocstrings[python] | `>=0.26.0` | Auto API reference from docstrings | docs group |
| mkdocs-gen-files | `>=0.5.0` | Runs `gen_ref_pages.py` to emit reference pages | docs group `[VERIFIED: 7 reference pages built]` |
| mkdocs-literate-nav | `>=0.6.0` | `SUMMARY.md`-driven reference nav | docs group |
| mkdocs-section-index | `>=0.3.0` | Section landing pages | docs group |
| uv_build | `>=0.9.18,<1.0.0` | Build backend (wheel/sdist) | `[VERIFIED: uv build packaged all 9 modules]` |
| git-cliff | 2.12.0 (local homebrew + `uvx`) | Conventional-commits changelog | `[VERIFIED: git-cliff --version 2.12.0]` |

**Installation:** No new installs. `uv sync --locked --group docs` for docs work,
`uv sync --locked --dev --extra ladybug` for the full test env (both already in CI).

## Package Legitimacy Audit

> All packages were verified and pinned in Phases 1–2 (HIGH confidence in CLAUDE.md sources).
> The `package-legitimacy check` seam returned all-null signals this session (no PyPI network
> in sandbox — `exists: null` means "could not reach registry", NOT a SUS finding). Legitimacy
> rests on the prior-phase verification + uv.lock pinning, not a fresh registry call.

| Package | Registry | Pin | Source Repo | Verdict | Disposition |
|---------|----------|-----|-------------|---------|-------------|
| pydantic | PyPI | `>=2.11,<3` (2.13.4) | github.com/pydantic/pydantic | OK (prior-phase HIGH) | Approved — unchanged |
| ladybug | PyPI | `>=0.17,<0.18` (0.17.1) | github.com/LadybugDB/ladybug | OK (prior-phase HIGH) | Approved — `ladybug` NOT `ladybugdb` |
| hypothesis | PyPI | `>=6.155` (6.155.2) | github.com/HypothesisWorks/hypothesis | OK (prior-phase HIGH) | Approved — dev group |
| mkdocs-material | PyPI | `>=9.7.0` | github.com/squidfunk/mkdocs-material | OK (build succeeded) | Approved — docs group |
| git-cliff | crates/PyPI | `uvx` / homebrew | github.com/orhun/git-cliff | OK (ran 2.12.0) | Approved — tooling |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious:** none
**`ladybugdb` slopsquat guard:** `[VERIFIED: grep -c 'name = "ladybugdb"' uv.lock → 0]` — the
brand name `ladybugdb` is absent from the lock; the installable is `ladybug`. This is the
single most-likely scaffolding bug per CLAUDE.md and is confirmed clean.

## Phase Requirements

| ID | Description (DECIDED bar, not stale text) | Current Status | Research Support |
|----|-------------------------------------------|----------------|------------------|
| PKG-02 | Runtime deps per **D-03**: `pydantic` SOLE required, `ladybug` the `[ladybug]` extra (NOT "exactly ladybug+pydantic"); zero NVM imports; `hypothesis` in dev group; CI matrix **3.14-only** (NOT 3.11+3.14) | **SATISFIED in code, stale in REQUIREMENTS/ROADMAP text** | `pyproject.toml` lines 9–20, 27–36 verified; all workflows are `python-version: ["3.14"]`; correcting REQUIREMENTS PKG-02 + ROADMAP SC1 text is in-scope |
| PKG-03 | MIT license file; README leads with "standalone reference implementation of Kumiho (arXiv 2603.17244), multi-scope extension, no recovery" | **PARTIAL** — `LICENSE` present (MIT); README is a 2-line stub missing the framing | `LICENSE` verified MIT; `README.md` = 2 lines (gap) |
| PKG-04 | mkdocs-material site that **publishes the "how to write a backend" port contract**; GitHub Actions CI+release pipeline; PyPI-ready packaging; CHANGELOG via git-cliff | **PARTIAL** — site builds + 7 API pages + changelog page render; **contract page NOT in site**; pipelines exist but git-cliff config + PyPI metadata defects; stale dist | Verified `mkdocs build --strict` green; contract page absent from `site/`; see Gaps |

## Architecture Patterns

### System Architecture Diagram (publication data flow)

```
                    git history + .cliff.toml
                            │
                            ▼
   ┌──────────────────────────────────────────────────────┐
   │ git-cliff --config .cliff.toml -o CHANGELOG.md         │  (root, generated, NOT committed)
   └──────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴────────────────┐
            ▼                                 ▼
   docs/src/changelog.md                 release.yml github-release
   --8<-- "CHANGELOG.md"                  body_path: CHANGELOG.md
   (pymdownx.snippets,                          │
    base_path=".", check_paths=true)            ▼
            │                              GitHub Release notes
            ▼
   ┌──────────────────────────────────────────────────────┐
   │ mkdocs build --strict  (docs_dir = docs/src)           │
   │   • index.md (Home)                                    │
   │   • backend-contract.md  ◀── MUST be moved INTO        │
   │     docs/src/ + added to nav (PKG-04 gap)              │
   │   • reference/*  ◀── gen_ref_pages.py from src/ (auto) │
   │   • changelog.md ◀── snippet of root CHANGELOG.md      │
   └──────────────────────────────────────────────────────┘
            │                                 │
            ▼ (docs.yml, push→main)           ▼ (release.yml, tag→build)
     GitHub Pages site                  uv build → wheel+sdist → PyPI publish
                                        (Requires-Python>=3.14, pydantic req, ladybug extra)
```

The reader can trace: a conventional commit lands → git-cliff renders the changelog → the
docs snippet embeds it AND the release notes use it → the site (incl. the contract) deploys to
Pages while a tag drives a wheel build to PyPI. The two arrows that are currently broken are
the **contract-page → site** arrow (the page is outside `docs_dir`) and the **`.cliff.toml`
→ git-cliff** arrow (workflows omit `--config`).

### Recommended Project Structure (docs — target state)
```
docs/
├── src/                     # docs_dir (mkdocs builds ONLY from here)
│   ├── index.md             # Home — fill the TODO Quick Start
│   ├── backend-contract.md  # ◀── RELOCATE here from docs/ (or include) + add to nav
│   └── changelog.md         # snippet of root CHANGELOG.md (already correct)
├── scripts/
│   └── gen_ref_pages.py     # auto API reference (already correct)
└── changelog.md             # ◀── ORPHANED sphinx/myst stub OUTSIDE docs_dir — delete or ignore
```

### Pattern 1: Publishing a repo-root doc into the mkdocs site
**What:** mkdocs builds *only* from `docs_dir` (`docs/src`). A file at `docs/backend-contract.md`
is invisible to the site. Two valid fixes:
**When to use:** PKG-04 requires the contract reachable from the published site.
**Option A (relocate — recommended):** `git mv docs/backend-contract.md docs/src/backend-contract.md`
and add a nav entry. Cleanest; the file becomes a first-class page.
**Option B (snippet include):** keep the file where it is and create
`docs/src/backend-contract.md` containing `--8<-- "docs/backend-contract.md"` with
`base_path: ["."]` (already set). Works, but adds an indirection and a `check_paths` dependency.
Prefer Option A — the contract has no markdown links (verified `grep -E '\]\(' → 0 matches`),
so relocating it cannot break `--strict` on internal links.
```yaml
# mkdocs.yml nav (target)
nav:
  - Home: index.md
  - Backend Contract: backend-contract.md   # NEW (PKG-04)
  - API Reference: reference/
  - Changelog: changelog.md
```

### Pattern 2: git-cliff with a dot-prefixed config
**What:** git-cliff's default config path is `cliff.toml` (no dot). The repo uses `.cliff.toml`.
A bare `git-cliff` / `uvx git-cliff` will NOT auto-discover it.
**When to use:** every changelog invocation in CI and locally.
```bash
# Source: git-cliff --help (verified: --config default "cliff.toml"; env GIT_CLIFF_CONFIG)
git-cliff --config .cliff.toml -o CHANGELOG.md          # explicit flag (recommended)
# OR set the env var in the workflow:
#   env: { GIT_CLIFF_CONFIG: .cliff.toml }
# OR rename .cliff.toml → cliff.toml (changes the repo convention; least preferred)
```

### Pattern 3: PyPI-ready project metadata
**What:** uv_build emits METADATA from `[project]`. Verified the fresh wheel METADATA has
`Name`, `Version`, `Requires-Python: >=3.14`, `Requires-Dist: pydantic>=2.11,<3`, the
`ladybug`/`all` extras — but **no `License`, no `Classifier`, no `Project-URL`, no
`Description`/`Keywords`**.
**When to use:** PyPI listings render license, classifiers, and project links from these.
```toml
# pyproject.toml [project] additions for PyPI readiness
license = "MIT"                    # PEP 639 SPDX expression (uv_build supports it)
license-files = ["LICENSE"]
keywords = ["belief-revision", "agm", "kumiho", "graph", "epistemic", "memory"]
classifiers = [
  "Development Status :: 4 - Beta",
  "License :: OSI Approved :: MIT License",
  "Programming Language :: Python :: 3.14",
  "Typing :: Typed",
  "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
[project.urls]
Homepage = "https://github.com/anentropic/doxastica"
Documentation = "https://anentropic.github.io/doxastica/"
Repository = "https://github.com/anentropic/doxastica"
```

### Anti-Patterns to Avoid
- **Editing `docs/changelog.md`** (the orphaned sphinx/myst stub with `{include}` /
  `myst_parser` directives). It is OUTSIDE `docs_dir`, unused by mkdocs, and its myst syntax is
  wrong for mkdocs-material. The live changelog page is `docs/src/changelog.md` (pymdownx
  snippet). Delete the orphan or leave it; never wire it in.
- **Committing `CHANGELOG.md`** to the repo. It is generated at build/release time. Generating
  it locally for a strict build is fine, but it should stay untracked (the workflows regenerate it).
- **Trusting the committed `dist/` wheel.** It is the stale 71-byte Phase-1 scaffold (only
  `__init__.py` + `py.typed`). Any release MUST `uv build` fresh — verified a fresh build packages
  all 9 modules (core.py 41KB, ladybug.py 30KB, etc.).
- **Re-litigating the 3.11 floor or "exactly ladybug+pydantic".** Both are superseded; the code
  is already correct. Only the *prose* needs fixing.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API reference docs | Hand-written per-module .md | mkdocstrings + `gen_ref_pages.py` (present) | Auto-generated from docstrings; 7 pages already build |
| Changelog | Hand-edited CHANGELOG | git-cliff + `.cliff.toml` (present) | Conventional-commits → grouped sections, verified working |
| Wheel/sdist build | setup.py / manual zip | `uv build` (uv_build backend, present) | PEP 621 metadata + py.typed inclusion verified |
| PyPI auth | API token in secrets | `pypa/gh-action-pypi-publish` trusted publishing (present in release.yml) | OIDC, no long-lived token |
| Embedding the changelog in docs | Copy-paste | pymdownx.snippets `--8<--` (present) | Single source of truth; verified rendering |

**Key insight:** Every hand-roll temptation here is already solved by a wired tool. Phase 8's
job is to *connect and verify* those tools, not author their outputs by hand.

## Runtime State Inventory

> Phase 8 includes a rename-like sub-task (correcting stale REQUIREMENTS/ROADMAP prose) but it
> is **documentation text only** — no stored data, services, or registrations carry the stale
> strings. Inventory included for completeness.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no datastore stores "3.11" or "exactly ladybug+pydantic" as keys. Verified: this is prose in `.planning/*.md` only. | none |
| Live service config | None — no external service config references the floor/dep wording. CI workflows already encode 3.14-only + D-03 (verified). | none |
| OS-registered state | None — no OS task/process embeds these strings. | none |
| Secrets/env vars | `release.yml` uses `GITHUB_TOKEN` (git-cliff-action) + PyPI trusted-publishing OIDC (no token). No secret carries the stale wording. | none |
| Build artifacts | **Stale `dist/` wheel** (71-byte Phase-1 scaffold, built 2026-06-14) — does NOT reflect current src. | `uv build` fresh before any release; optionally regenerate or gitignore committed `dist/` |

**Canonical question — after the prose is corrected, what still has the old wording?** Only
the two `.planning` docs themselves (the targets of the correction). The code, workflows, and
metadata are already on the decided bar. Verified.

## Common Pitfalls

### Pitfall 1: `mkdocs build --strict` fails locally because CHANGELOG.md is missing
**What goes wrong:** `docs/src/changelog.md` uses `--8<-- "CHANGELOG.md"` with
`pymdownx.snippets` `check_paths: true` + `base_path: ["."]`. If root `CHANGELOG.md` doesn't
exist, the strict build **errors** (`check_paths=true` ⇒ build fails when a snippet file is
missing). `[CITED: facelessuser.github.io/pymdown-extensions/extensions/snippets]`
**Why it happens:** `CHANGELOG.md` is generated, not committed. The `docs.yml` workflow runs
`git-cliff -o CHANGELOG.md` *before* `mkdocs build`, so CI passes; a naive local build fails.
**How to avoid:** Always run `git-cliff --config .cliff.toml -o CHANGELOG.md` before
`mkdocs build --strict` locally (this session reproduced both the failure and the fix).
**Warning signs:** `Error: ... CHANGELOG.md ... not found` on a clean checkout.

### Pitfall 2: git-cliff silently uses the DEFAULT config (ignoring `.cliff.toml`)
**What goes wrong:** Workflows call `uvx git-cliff -o CHANGELOG.md` (docs.yml) and
`git-cliff-action args: --latest` (release.yml) **without** `--config .cliff.toml`. git-cliff's
default search path is `cliff.toml` (no dot), so it prints `"cliff.toml" is not found, using the
default configuration` and produces a changelog WITHOUT the repo's commit-parser groups and
WITHOUT the `<!-- docs-include-start -->` marker. `[VERIFIED: git-cliff --help → --config default "cliff.toml"; bare git-cliff emits the not-found warning; --config output contains the marker, default output does not (grep -c → 1 vs 0)]`
**Why it happens:** Cookiecutter named the config `.cliff.toml` but the workflows assume default discovery.
**How to avoid:** Add `--config .cliff.toml` to every invocation (or `GIT_CLIFF_CONFIG=.cliff.toml`
in the workflow env, or rename to `cliff.toml`). Fix in `docs.yml` AND `release.yml`.
**Warning signs:** Changelog lacks the configured group headers / the docs-include marker.

### Pitfall 3: The published site silently omits the backend contract
**What goes wrong:** `docs/backend-contract.md` is OUTSIDE `docs_dir` (`docs/src`). mkdocs never
sees it — no warning, no error, the build is green, but PKG-04's "publishes the port contract"
is **unmet**. `[VERIFIED: site/ contains no backend-contract page after a green --strict build]`
**Why it happens:** The file was authored in Phase 1 at `docs/` (the repo doc location), not the
mkdocs source root.
**How to avoid:** Relocate into `docs/src/` and add to nav (Pattern 1). Re-run `--strict` and
assert the page appears in `site/`.
**Warning signs:** A green build that nonetheless has no contract page in `site/`.

### Pitfall 4: Shipping the stale dist/ wheel to PyPI
**What goes wrong:** The committed `dist/doxastica-0.1.0-py3-none-any.whl` contains only the
empty Phase-1 `__init__.py` (71 bytes) + `py.typed` — none of the actual implementation. A
release that reused it would publish an empty package.
**Why it happens:** `dist/` was built once in Phase 1 and committed; src grew across Phases 1–7.
**How to avoid:** `release.yml` already rebuilds via `uv build` on tag (verified job exists), so
the *pipeline* is safe. But never treat committed `dist/` as authoritative; rebuild for any
manual check. A fresh `uv build` was verified to package all 9 modules + correct METADATA.
**Warning signs:** `unzip -l dist/*.whl` shows a 71-byte `__init__.py`.

### Pitfall 5: Missing PyPI metadata (license/classifiers/urls)
**What goes wrong:** `pyproject.toml [project]` declares no `license`, `classifiers`, or
`[project.urls]`. The MIT LICENSE file exists but the wheel METADATA has no `License-Expression`
and PyPI shows no classifiers or project links. `[VERIFIED: fresh wheel METADATA has Name/Version/Requires-Python/Requires-Dist only; grep of pyproject → none of license/classifier/urls/keywords]`
**Why it happens:** Cookiecutter left these optional fields unset.
**How to avoid:** Add `license = "MIT"`, `license-files`, `classifiers`, `keywords`, and
`[project.urls]` (Pattern 3). uv_build supports PEP 639 SPDX license expressions.
**Warning signs:** PyPI preview / `twine check` flags missing classifiers; no license badge.

## Code Examples

### Reproduce the full local publication dry-run (verified this session)
```bash
# 1. Changelog (MUST pass --config for the dot-prefixed file)
git-cliff --config .cliff.toml -o CHANGELOG.md      # verified: renders grouped Features/Bug Fixes

# 2. Docs (strict) — requires CHANGELOG.md from step 1 (snippet check_paths=true)
uv sync --locked --group docs
uv run --no-sync mkdocs build --strict              # verified GREEN; assert backend-contract page after relocation:
test -f site/backend-contract/index.html

# 3. Distribution — fresh build (NOT the stale committed dist/)
uv build --out-dir /tmp/dist                        # verified packages all 9 modules
unzip -l /tmp/dist/*.whl | grep py.typed            # verified present
uv run python -c "import doxastica; print(doxastica.__all__)"   # import smoke
```

### README target lead (PKG-03 framing)
```markdown
# doxastica

A standalone reference implementation of **Kumiho** (arXiv 2603.17244, Young Bin Park) —
a graph-native AGM belief-revision core — with one deliberate **multi-scope extension**
(Kumiho is single-agent) and one deliberate exclusion (**no AGM recovery**; superseded-chain
semantics replace it). Zero narrative/LLM concepts; correctness is *provable* (AGM/Hansson
postulates verified mechanically as a backend conformance suite).
```

## State of the Art

| Old Approach (stale bar) | Current Approach (decided bar) | When Changed | Impact |
|--------------------------|--------------------------------|--------------|--------|
| Runtime deps "exactly ladybug + pydantic" | pydantic SOLE required; ladybug the `[ladybug]` extra; `all` extra | Phase 2 D-03 | PKG-02 text in REQUIREMENTS/ROADMAP is stale — correct it |
| Python floor 3.11 + 3.14 matrix | floor 3.14; CI matrix 3.14-only | CONTEXT #2 (Phase 1) | PKG-02/ROADMAP SC1 text stale; workflows already 3.14-only |
| Backend contract drafted at `docs/` | Must be published in the mkdocs site (`docs/src/` + nav) | Phase 8 (this) | PKG-04 not yet satisfied |

**Deprecated/outdated in the live tree:**
- `docs/changelog.md` (sphinx/myst `{include}` stub) — superseded by `docs/src/changelog.md`
  (pymdownx snippet). Orphaned; do not wire.
- Committed `dist/` wheel — superseded by any fresh `uv build`.
- mkdocs-material emits a "MkDocs 2.0 / switch to ProperDocs" vendor warning at build — it is
  NOT an error and does NOT fail `--strict`; ignore it (or set `DISABLE_MKDOCS_2_WARNING=true`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Relocating `backend-contract.md` into `docs/src/` + nav keeps `--strict` green (no internal md links to break) | Pattern 1 | LOW — verified the file has 0 markdown links this session; risk only if links are added |
| A2 | `release.yml` git-cliff-action honours `.cliff.toml` if `--config` is added; the action default also misses the dot-file | Pitfall 2 | LOW — same default-path behaviour as the CLI; planner should add the config arg/env to be safe |
| A3 | Suggested classifiers/SPDX license are the right PyPI metadata for an MIT reference lib | Pattern 3 | LOW — standard set; user may want different Development Status |

**Note:** All other findings are `[VERIFIED]` (reproduced against the live tree) or `[CITED]`
(pymdownx snippets docs). The stale-text corrections and gaps are facts, not assumptions.

## Open Questions (RESOLVED)

1. **Commit `dist/` or gitignore it?**
   - What we know: the committed `dist/` is stale; `release.yml` rebuilds on tag.
   - **RESOLVED (2026-06-19, verified):** `dist/` is ALREADY gitignored (`.gitignore:13`) and untracked (`git ls-files dist/` → empty). There is nothing to commit or change. No plan task needed — the stale on-disk wheel is local-only and is never version-controlled; `release.yml` is the authoritative build. 08-03 Task 3 proves wheel correctness via a fresh `/tmp` build, bypassing the stale local copy.
2. **Delete the orphaned `docs/changelog.md`?**
   - What we know: it's an unused sphinx/myst stub outside `docs_dir`.
   - **RESOLVED:** Delete it — implemented as a task in plan 08-03 (it has no consumer; removing it avoids confusion with `docs/src/changelog.md`).
3. **PyPI publish trigger — confirm OUT of scope.**
   - What we know: `release.yml` has a `publish` job (trusted publishing) gated on a `v*` tag.
   - **RESOLVED:** OUT of scope (locked decision D-05). The pipeline is left ready; no plan pushes a tag (pipeline-ready ≠ published). 08-03 enforces this as an explicit non-action.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv (+ uv_build) | build, sync | ✓ | 0.9.18 | — |
| git-cliff | changelog | ✓ (homebrew) | 2.12.0 | `uvx git-cliff` (note: panics in *this* sandbox; CI uses ubuntu, fine) |
| mkdocs + material + mkdocstrings | docs site | ✓ | mkdocs 1.6+, material 9.7.x | — |
| Python 3.14 | runtime floor | ✓ | 3.14 | — (floor locked) |
| PyPI network | publish/legitimacy check | ✗ (sandbox) | — | CI (ubuntu) has network; not needed for planning |

**Missing dependencies with no fallback:** none for planning/execution. PyPI publish requires
network only in CI, which has it.
**Sandbox note:** `uv sync`/`uv build`/`uvx git-cliff` panic under the local macOS sandbox
(documented `uv sandbox panic` in MEMORY); they succeed with the sandbox disabled and in CI.
This does NOT block the phase — it only affects local dry-runs.

## Validation Architecture

> nyquist_validation is enabled (config.json: true). This is a docs/packaging phase: validation
> is "the docs build passes --strict (with the contract page)", "a fresh wheel installs and
> imports", and "git-cliff produces the configured changelog".

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x (existing suite — unchanged) + shell/CLI gates for packaging |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `git-cliff --config .cliff.toml -o CHANGELOG.md && uv run --no-sync mkdocs build --strict` |
| Full suite command | `uv run pytest && uv build && mkdocs build --strict` (the existing conformance suite must stay green — Phase 7 frozen) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PKG-02 | Required dep = pydantic only; ladybug is an extra | smoke | `unzip -p dist/*.whl '*/METADATA' \| grep -E 'Requires-Dist: pydantic'` and `grep "extra == 'ladybug'"` | ✅ (build) |
| PKG-02 | No NVM imports; import-purity intact | unit | `uv run pytest` (existing import-purity scan) | ✅ existing |
| PKG-02 | CI matrix is 3.14-only | manual/grep | `grep -r 'python-version' .github/workflows` → only `["3.14"]` | ✅ verified |
| PKG-03 | MIT LICENSE present | smoke | `head -1 LICENSE \| grep -q "MIT License"` | ✅ |
| PKG-03 | README leads with Kumiho framing | manual | grep README.md for "reference implementation of Kumiho", "multi-scope", "no recovery" | ❌ Wave 0 (README is a stub) |
| PKG-04 | Docs build green AND contract page published | smoke | `mkdocs build --strict && test -f site/backend-contract/index.html` | ❌ Wave 0 (contract not in nav yet) |
| PKG-04 | Changelog renders from configured git-cliff | smoke | `git-cliff --config .cliff.toml -o CHANGELOG.md && grep -q 'docs-include-start' CHANGELOG.md` | ✅ tool works; ❌ workflows miss `--config` |
| PKG-04 | Fresh wheel imports + ships py.typed | smoke | `uv build && unzip -l dist/*.whl \| grep py.typed && python -c "import doxastica"` | ✅ (build) |
| PKG-04 | PyPI-ready metadata (license/classifiers/urls) | smoke | `unzip -p dist/*.whl '*/METADATA' \| grep -E 'License|Classifier|Project-URL'` | ❌ Wave 0 (pyproject lacks them) |

### Sampling Rate
- **Per task commit:** `git-cliff --config .cliff.toml -o CHANGELOG.md && uv run --no-sync mkdocs build --strict` (docs tasks); `uv build` smoke (packaging tasks).
- **Per wave merge:** full `uv run pytest` (Phase-7 conformance must stay green) + docs strict build + fresh wheel import.
- **Phase gate:** all three gates green — strict docs build with contract page, fresh wheel imports, configured changelog renders — before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] README content (PKG-03 framing) — `README.md` is a 2-line stub.
- [ ] `docs/src/backend-contract.md` + nav entry — contract not yet in the site (PKG-04).
- [ ] `docs/src/index.md` Quick Start — replace "TODO: Add usage examples here".
- [ ] `pyproject.toml` PyPI metadata — add `license`, `classifiers`, `keywords`, `[project.urls]`.
- [ ] `docs.yml` + `release.yml` — add `--config .cliff.toml` (or `GIT_CLIFF_CONFIG`) to git-cliff.
- [ ] Stale-text corrections — REQUIREMENTS PKG-02 + ROADMAP Phase 8 SC1 to the decided bar.
- [ ] (Optional) gitignore/refresh stale committed `dist/`; delete orphan `docs/changelog.md`.

*No new test framework needed — the existing pytest conformance suite is reused as the
"don't regress" gate; packaging/docs validation is CLI smoke checks.*

## Sources

### Primary (HIGH confidence — verified against the live tree this session)
- `pyproject.toml`, `mkdocs.yml`, `.cliff.toml`, all `.github/workflows/*.yml`, `LICENSE`,
  `README.md`, `docs/src/index.md`, `docs/src/changelog.md`, `docs/backend-contract.md`,
  `docs/scripts/gen_ref_pages.py`, `src/doxastica/__init__.py`, `uv.lock` — read directly
- `mkdocs build --strict` → GREEN, 7 reference pages, no contract page (reproduced)
- `uv build` → fresh wheel packages all 9 modules + correct D-03/3.14 METADATA (reproduced)
- `git-cliff --version` 2.12.0; `git-cliff --config .cliff.toml` vs bare default (reproduced;
  default ignores `.cliff.toml`, drops the docs-include marker)
- `uv run python -c "import pydantic/hypothesis"` → 2.13.4 / 6.155.2

### Secondary (MEDIUM confidence — official docs)
- pymdownx Snippets docs — `check_paths: true` fails the build on a missing snippet file;
  `base_path` resolution: https://facelessuser.github.io/pymdown-extensions/extensions/snippets/

### Tertiary (LOW confidence)
- mkdocs-material v2 / ProperDocs vendor warning observed at build — informational only, not a gate.

## Metadata

**Confidence breakdown:**
- Requirement status mapping: HIGH — every file inspected, builds reproduced
- Gaps (README, contract-in-nav, index TODO, metadata, git-cliff config, stale dist): HIGH — each verified directly
- Validation gates: HIGH — commands run successfully this session
- PyPI classifier/license recommendations: MEDIUM — standard set, user-tunable (A3)

**Research date:** 2026-06-19
**Valid until:** 2026-07-19 (stable tooling; mkdocs-material v2 transition is the one watch item)
