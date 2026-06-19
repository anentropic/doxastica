---
phase: 06
slug: structural-time-travel
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-19
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Phase 6 adds one read-only method (`MemoryCore.get_scope_at`, HIST-03) plus a
test-only operational-fold oracle. It is an **embedded-library temporal read**: no
network, no auth, no session, no free user input. The sole new argument beyond the
existing `scope_id: str` is a typed `UUID` cut (`as_of_event_id`), normalized to its
canonical `str` form for the comparison — it cannot carry free text or a Cypher
fragment. No new `BackendPort` method, no new Cypher interpolation, and zero new
dependencies/imports are introduced. The applicable control is V5
input-validation-by-construction, already satisfied by the closed signature.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| caller (NVM / postulate test) → `MemoryCore.get_scope_at` | The sole new argument is a typed `UUID` cut (`as_of_event_id`) plus the existing `scope_id: str`. No free query string, no Cypher fragment. | `scope_id: str` (validated identifier), `as_of_event_id: UUID` (canonical id, not secret) |
| `MemoryCore` → `BackendPort.match_nodes` | Already-shipped read primitive; `$param`-bound values + adapter-validated identifiers (ladybug `_validate_identifier`). Phase 6 adds NO new port method and NO new interpolation. | `$param`-bound node-match values |
| test harness → `MemoryCore.get_scope_at` (06-02) | Test-only; the Hypothesis property drives the already-shipped read with typed `UUID` cuts from a fixed pool. No new production surface. | test-only typed `UUID` cuts |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-06-01 | Tampering / Info-disclosure | `get_scope_at` cut argument | accept | Designed out by construction: `as_of_event_id` is a typed `UUID`, normalized to its canonical `str` form for the cut; cannot carry free text or a Cypher fragment. V5 input-validation-by-construction (closed signature) is the sole applicable control. No high-severity threat. | closed |
| T-06-02 | Info-disclosure | result hydration | accept | `get_scope_at` returns frozen `BeliefState` models via `_hydrate`; no raw dict / internal `_`-prefixed key escapes. No new leak surface. | closed |
| T-06-03 | Info-disclosure | temporal visibility (reading a past state) | accept | Out of the core's remit: temporal-visibility/access policy is NVM-layer (R19/R21). The core faithfully reconstructs the structural as-of base; *who may call it with which `as_of`* is the consumer's policy. | closed |
| T-06-SC | Tampering | package installs | accept | No package install in this phase (RESEARCH §Package Legitimacy Audit: zero new deps, zero new imports). Phase-2 ladybug audit stands. | closed |
| T-06-02-01 | Tampering / Info-disclosure | test-only fold oracle + property (06-02) | accept | Adds NO production code — only a test-only pure-Python oracle + Hypothesis machine over the already-injection-proofed `get_scope_at`/`match_nodes` path. No new network/auth/input surface; cut is a typed `UUID`. | closed |
| T-06-02-SC | Tampering | package installs (06-02) | accept | No package install (`pytest`/`hypothesis` already in the dev group). Phase-2 audit stands. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-01 | Cut argument is a typed `UUID` (closed signature) — no free text / Cypher can cross the boundary. Input-validation-by-construction. | Phase 6 plan-time threat model | 2026-06-19 |
| AR-06-02 | T-06-02 | Return surface is frozen `BeliefState` models via `_hydrate`; no internal keys escape. | Phase 6 plan-time threat model | 2026-06-19 |
| AR-06-03 | T-06-03 | Temporal-visibility/access policy is NVM-layer (R19/R21), not the core's remit. The core reconstructs faithfully; authorization is the consumer's. | Phase 6 plan-time threat model | 2026-06-19 |
| AR-06-04 | T-06-SC / T-06-02-SC | Zero new runtime/dev dependencies and zero new imports introduced this phase; the Phase-2 ladybug supply-chain audit stands. | Phase 6 plan-time threat model | 2026-06-19 |
| AR-06-05 | T-06-02-01 | 06-02 is test-only (pure-Python oracle + Hypothesis machine); no production surface added. | Phase 6 plan-time threat model | 2026-06-19 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-19 | 6 | 6 | 0 | gsd-secure-phase (short-circuit: plan-time register, threats_open=0) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-19
