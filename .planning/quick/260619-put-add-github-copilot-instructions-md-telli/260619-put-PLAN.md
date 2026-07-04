---
phase: quick-260619-put
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [.github/copilot-instructions.md]
autonomous: true
requirements: [QUICK-COPILOT-IGNORE-PLANNING]
must_haves:
  truths:
    - "GitHub Copilot custom-instructions file exists at .github/copilot-instructions.md"
    - "The file instructs Copilot (and Copilot code review) not to review, summarize, or comment on files under .planning/"
    - "The file briefly states what the project is, for review context"
  artifacts:
    - path: ".github/copilot-instructions.md"
      provides: "Copilot custom instructions: ignore .planning/ during review"
      contains: ".planning"
  key_links: []
---

<objective>
Add a GitHub Copilot custom-instructions file at `.github/copilot-instructions.md` that tells GitHub Copilot — especially its automated code review — to ignore/skip files under `.planning/`. Those are GSD process/planning artifacts (ROADMAP, REQUIREMENTS, STATE, PROJECT, per-phase CONTEXT/PLAN/SUMMARY/VERIFICATION/VALIDATION docs, and `.planning/quick/`), not application code, and should not be reviewed or commented on.

Purpose: Keep Copilot review focused on the actual zero-LLM AGM library source, not on GSD planning prose that will otherwise generate noisy, irrelevant review comments.
Output: A new repo-config doc file, `.github/copilot-instructions.md`. No source, tests, or packaging touched.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create .github/copilot-instructions.md with the .planning/ ignore directive</name>
  <files>.github/copilot-instructions.md</files>
  <action>Create the new file `.github/copilot-instructions.md` (the `.github/` directory already exists; do not touch `dependabot.yml` or `workflows/`). Write concise GitHub-Copilot custom-instructions Markdown. Open with one short paragraph of project context for review framing: doxastica is a standalone, zero-LLM Python library implementing an append-only AGM belief-revision core (the Kumiho architecture) behind a clean `BeliefStore` Protocol — review should focus on the library source under `src/` and `tests/`. Then state the operative directive in plain language with the literal token `.planning` present, e.g. a sentence such as "Do not review, summarize, or comment on any files under `.planning/` — these are GSD process and planning artifacts (ROADMAP, REQUIREMENTS, STATE, PROJECT, and per-phase CONTEXT/PLAN/SUMMARY/VERIFICATION/VALIDATION docs, plus `.planning/quick/`), not application code." Make the ignore directive apply explicitly to Copilot code review. Keep the file short (a heading plus a few sentences/bullets); do not add unrelated coding-style rules. Use Write (no heredoc).</action>
  <verify>
    <automated>test -f .github/copilot-instructions.md && grep -q ".planning" .github/copilot-instructions.md && grep -qiE "not (be )?review|do not review|skip|ignore" .github/copilot-instructions.md</automated>
  </verify>
  <done>`.github/copilot-instructions.md` exists, contains the literal `.planning` token, and states in plain language that Copilot (including code review) must not review/comment on files under `.planning/`. No other repo files changed.</done>
</task>

</tasks>

<verification>
- `test -f .github/copilot-instructions.md` passes.
- `grep -q ".planning" .github/copilot-instructions.md` passes.
- The file expresses the ignore-during-review directive in plain language and applies it to Copilot code review.
- `git status` shows only the new `.github/copilot-instructions.md` (no source/test/packaging changes).
</verification>

<success_criteria>
A single new file `.github/copilot-instructions.md` that (1) briefly states what doxastica is for review context and (2) directs GitHub Copilot and its automated code review to ignore/skip files under `.planning/`. Pure repo-config change.
</success_criteria>

<output>
Create `.planning/quick/260619-put-add-github-copilot-instructions-md-telli/260619-put-SUMMARY.md` when done
</output>
