---
id: SEED-002
status: actionable
planted: 2026-07-05
planted_during: v0.2.0 milestone completion (post-ship release)
trigger_when: Before the next release / at the next milestone close — fold into the
  milestone-complete or a pre-release checklist so the version bump precedes the tag.
scope: Small
---

# SEED-002: add an explicit "bump package version" step to the release flow

> **Status:** actionable process fix. Recorded from a real v0.2.0 release failure so the
> next release doesn't repeat it.

## What Happened (the motivating failure)

`pyproject.toml` carries a **static** `version = "..."` (build backend `uv_build`, not a
VCS-derived dynamic version). At v0.2.0 close the milestone was archived and tagged `v0.2.0`,
but the package version was never bumped from `0.1.0`. The tag-triggered `release.yml` built
`doxastica-0.1.0` again and PyPI rejected it with `400 File already exists` (0.1.0 had already
published on 2026-07-04). Fix required: bump `pyproject.toml` + re-run `uv lock`, push to main,
then delete and re-point the `v0.2.0` tag to the bumped commit to re-trigger the release.

## The Fix To Institutionalize

Add a **"bump version"** step that runs *before* the milestone tag is created, updating both:

- `pyproject.toml` → `[project] version`
- `uv.lock` (via `uv lock`) — the self-entry `name = "doxastica"` version must match

Natural homes for the step:

1. **`/gsd-complete-milestone`** — insert a version-bump gate before `git_tag` (the workflow
   currently tags without touching the package version).
2. **A pre-release checklist** in the repo (e.g. `docs` or `CONTRIBUTING`) — "bump version,
   `uv lock`, run full `prek`, then tag."

Optionally consider making the version **dynamic** (derive from the git tag at build time) so a
tag is the single source of truth and this class of drift becomes impossible — but that is a
larger change to the `uv_build` config and should be weighed separately.

## Guardrails Learned

- A release that reuses an existing version fails hard at PyPI (`400`, not a silent overwrite) —
  good, but only surfaces post-tag.
- `skip_existing: false` in the publish action means a duplicate is a hard failure (intended).
- Moving/force-pushing a milestone tag is safe **only** because the failed release consumed
  nothing; do it before anything downstream depends on the tag.
