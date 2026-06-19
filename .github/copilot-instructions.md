# GitHub Copilot Instructions

doxastica is a standalone, zero-LLM Python library implementing an append-only AGM
belief-revision core (the Kumiho architecture) behind a clean `BeliefStore` Protocol.
Review should focus on the library source under `src/` and its test suite under `tests/`.

## Do not review `.planning/`

Do not review, summarize, or comment on any files under `.planning/` — these are GSD
process and planning artifacts (ROADMAP, REQUIREMENTS, STATE, PROJECT, and per-phase
CONTEXT/PLAN/SUMMARY/VERIFICATION/VALIDATION docs, plus `.planning/quick/`), not
application code.

- This directive applies explicitly to GitHub Copilot code review: **skip** everything
  under `.planning/` and raise no review comments on it.
- Keep automated review focused on the actual library code and tests, not on planning prose.
