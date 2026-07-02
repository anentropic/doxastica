# Editor Report

**Generated:** 2026-07-01
**Files reviewed:** 21 (docs/src: index, backend-contract, changelog, 2 tutorials, 8 how-to, 8 explanation)
**Changes made:** 108
  - BLOCKING: 2
  - SUGGESTION: 98
  - NITPICK: 8

## Summary

The documentation was already well-structured, accurate against source, and diataxis-clean. The dominant issue was heavy em-dash overuse (an LLM stylistic tic) across every prose file, which was the author's stated priority; 96 in-sentence em dashes were replaced with commas, colons, semicolons, or sentence breaks while preserving five protected inline-header list items in the reference page and all in-code-block dashes. Terminology was already consistent (no normalizations needed), and only two broken cross-reference anchors required fixing.

---

## Pass Summary

| Pass | Result |
|------|--------|
| 1. Terminology consistency | No normalizations needed; canonical terms already applied uniformly (`LadybugDB` prose vs `ladybug` code, `Kùzu`, `UUID7`, `revise`/`expand`/`contract`, `BeliefStore`/`BackendPort`, `MemoryCore`). terminology.yaml unchanged. |
| 2. Diataxis type integrity | No type blur. Tutorials teach with verification, how-tos are task-scoped with consistent Requirements/steps/Verification/Troubleshooting/Related structure, explanations link out instead of embedding instructions, backend-contract is reference. Cross-type linking already strong. |
| 3. Humanizer (main deliverable) | 96 em-dash replacements + 2 filler/rhetoric rewrites across all prose files. No promotional adjectives, significance inflation, copula-avoidance filler, synonym cycling, curly quotes, transition-word padding, or superficial -ing trailers found. |
| 4. Cross-reference linking | 2 broken `WORLD_SCOPE_ID` anchors fixed (module anchor -> symbol anchor). All other inline public-symbol mentions already linked on first use. |
| Post-processing | 17 `INTERNAL NOTES FOR EDITOR` HTML comment blocks stripped; no other HTML comments touched. |

---

## Accuracy verification (pre-processing)

All implementation claims spot-checked against source code were confirmed accurate. No mismatches found.

- `revise` and `expand` both delegate to the shared `_append` with `Status.active` (`src/doxastica/core.py`) — "mechanically identical" claim verified.
- `LadybugBackend.open(":memory:"/"")` yields an in-memory DB; `open` owns its connection, `from_connection` does not — verified.
- `BackendDependencyError` is raised at import time and subclasses `ImportError` — verified; the fallback `except ImportError` pattern in the docs is correct.
- `get_scope_at` inclusive cut, `query_scope` DROP-vs-`get_scope_at` REWIND, `get_impact` walks against stored arrows excluding the start — all verified against docstrings.
- `add_edge(from_state_id, to_state_id, edge_type)` signature matches doc examples.

No BLOCKING accuracy items. No missing referenced source files.

---

## docs/src/how-to/contract-a-belief.md

### BLOCKING

| Section | Description | Fix |
|---------|-------------|-----|
| The world-scope guard | Inline `WORLD_SCOPE_ID` link pointed at the bare module anchor `#doxastica.models` instead of the symbol. | Retargeted to `#doxastica.models.WORLD_SCOPE_ID`. |

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 4 in-sentence instances. | Replaced with colons/semicolons/commas. |

---

## docs/src/explanation/scopes-and-world-scope.md

### BLOCKING

| Section | Description | Fix |
|---------|-------------|-----|
| The reserved world scope | Inline `WORLD_SCOPE_ID` link pointed at bare module anchor `#doxastica.models`. | Retargeted to `#doxastica.models.WORLD_SCOPE_ID`. |

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 3 in-sentence instances. | Replaced with commas/colons/semicolons. |

---

## docs/src/index.md

### NITPICK (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| Quick Start | Em dash: 1 prose instance (code-block comments left untouched). | Replaced with a sentence break. |

---

## docs/src/tutorials/index.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| Intro | Em dash: 1 instance. | Replaced with a colon. |

---

## docs/src/how-to/index.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| frontmatter description | Em dash: 1 instance. | Replaced with a colon. |

---

## docs/src/explanation/index.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| frontmatter + intro | Em dashes: 2 instances. | Description reworded; intro dash replaced with a sentence break. |

---

## docs/src/tutorials/first-belief-store.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 13 prose instances (Prerequisites, admonition, annotations, Steps 2/3/4/5/6). Code-block comment dashes left untouched. | Replaced with colons/semicolons/commas/sentence breaks. |

---

## docs/src/how-to/inspect-revision-history.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 3 instances, including a "question dash" list restructured. | Replaced with semicolons and "answers" phrasing. |

---

## docs/src/how-to/ladybug-backend.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 5 prose instances (intro, Requirements, annotation, namespace note, close section). | Replaced with commas/colons/semicolons/sentence breaks. |

---

## docs/src/how-to/lease-shared-connection.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 6 prose instances (intro, Requirements, ownership warning, namespace rules x2, troubleshooting). Code-block dashes left untouched. | Replaced with commas/colons/semicolons. |

---

## docs/src/how-to/query-with-belief-filter.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 5 prose instances (intro, four-fields note, event-range, admonition, precedence tip). | Replaced with colons/semicolons/commas. |

---

## docs/src/how-to/reconstruct-scope-at.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 3 prose instances (intro, retracted-cut note, "no include_retracted" admonition). | Replaced with colons/semicolons. |

---

## docs/src/how-to/trace-dependency-cascade.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 4 prose instances (mermaid intro, get_impact description, frontier explanation, cycle-safe tip). Code-block comment dashes left untouched. | Replaced with commas/colons/"so" clause. |

---

## docs/src/explanation/agm-belief-revision.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 9 prose instances (description, epistemic problem, belief-set/base definitions, expansion, contraction, recovery, audit trail, postulates). | Replaced with colons/commas. |
| Postulates | Informal-tone rhetoric "These are not vibes; they are precise mathematical conditions." | Rewritten to "These are precise mathematical conditions, not informal guidelines." |

---

## docs/src/explanation/kumiho-architecture.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 4 prose instances (buildable-on-own, structural answers, append-only spine, multi-scope). | Replaced with colons/semicolons/commas. |

---

## docs/src/explanation/beliefstore-vs-backendport.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 11 prose instances (public seam, structural protocol, promises, five-primitives x2, why-two-seams x2, audience table, backend-author task, driver-blind, pluggable, takeaways). | Replaced with colons/semicolons/commas/sentence breaks. |

---

## docs/src/explanation/derived-current-uuid7-ordering.md

### BLOCKING

_None._

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 6 prose instances (ordering contract, primary key, intra-ms note, tiebreak, how-current step 3, no-CURRENT_STATE x2). | Replaced with colons/semicolons/commas. |
| Why there is no CURRENT_STATE edge | Filler phrase "It is worth stating the omission plainly, because..." | Rewritten to lead with the substantive clause: "The omission surprises people... so it is worth stating plainly." |

---

## docs/src/explanation/superseded-chain-no-recovery.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 9 prose instances (lost-update, contraction pattern, auditing, current-trustworthy, recovery undo, tautology, spine-is-feature, time-travel, takeaway). | Replaced with colons/semicolons/commas. |

---

## docs/src/backend-contract.md

### SUGGESTION (humanizer)

| Section | Description | Fix |
|---------|-------------|-----|
| (whole file) | Em dashes: 11 in-sentence instances (intro seam, no-query-string, traverse cycle note, single-primitive, direction out/in x2, no-CURRENT_STATE, uniqueness PRIMARY KEY, ordering, value opacity, conformance). | Replaced with commas/colons/semicolons. |

### Preserved (not changed)

| Section | Description | Reason |
|---------|-------------|--------|
| §2 Primitive operations | 5 inline-header list items (`` **`upsert_node(...)`** — ... ``, `add_edge`, `match_nodes`, `traverse`, `unit_of_work`). | Protected inline-header vertical-list pattern (bold code header + definition); humanizer rule keeps these. |
| §1 intro | Inline internal path `` `src/doxastica/ports.py` ``. | This is the backend-author contract document whose audience is backend implementers; the source-location reference is deliberate and in-scope for this specialized page, not a Rule 1 leak into end-user docs. |

---

## docs/src/changelog.md

No changes. File is a single `--8<--` snippet include of the root `CHANGELOG.md`; no editable prose.

---

## Terminology Changes

No normalizations were required. All canonical terms were already applied consistently across every file:

| Term | Status |
|------|--------|
| LadybugDB (prose) / `ladybug` (code) | Consistent; no bare "Ladybug" in prose. |
| Kùzu | Correctly accented everywhere. |
| UUID7 | Consistent; no `UUID-7` variants. |
| `revise` / `expand` / `contract` | Consistent. |
| `BeliefStore` (public) / `BackendPort` (internal) | Consistent; seam distinction preserved. |
| `MemoryCore`, `InMemoryBackend`, `LadybugBackend`, `BeliefFilter`, `ImpactResult`, `EdgeType`, `WORLD_SCOPE_ID`, `WorldScopeContractionError`, `BackendDependencyError` | Consistent. |

`.doc-writer/terminology.yaml` left unchanged (no new variants detected).

---

## Notes for the Author

- No structural type blur, no accuracy mismatches, and no Rule 1 leaks into end-user pages were found. The set is in good shape.
- The three "X, not Y" antithesis constructions ("enforced, not merely conventional"; "checked, not merely intended"; "mechanically verified, not merely asserted in prose") were intentionally kept — they are precise engineering contrasts, not the AI "not only X but also Y" negative-parallelism template.
- All em dashes remaining in the docs are inside fenced code blocks (Python comments) or are the five protected inline-header list items in `backend-contract.md`.
