---
phase: 7
slug: agm-hansson-conformance-suite
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-19
---

# Phase 7 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Phase 7 ships a test/proof conformance suite for an embedded, single-process,
> zero-network belief-revision core. The only production change is a pure,
> driver-blind `_current_tails` helper in `core.py`. The realistic threat surface
> is minimal — there is no network, no auth, no session, and no untrusted-input
> boundary in scope.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| test harness → `MemoryCore` → `BackendPort` | The only boundary in scope. All inputs are test-generated (Hypothesis strategies over fixed id/event pools, plus hand-built deterministic ops and synthetic writes). | Opaque belief `value`/`belief_id`/`scope_id`/UUID7 event ids — test-authored, never external |
| (N/A) network / auth / session / multi-user | None — an embedded single-process library test suite. No listener, no credentials, no tenancy beyond the in-process namespace prefix. | — |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-07-01 | Tampering | Extracted `core.py` `_current_tails` helper + the divergence join | mitigate | Helper composes ONLY `_order_key`/`Status` + stdlib; the divergence join uses ONLY `match_nodes` (property-equality, one round-trip — verified `grep -c match_nodes == 1`) + a Python join. No `ladybug` import, no string-built/constructed Cypher in `core.py`. Statically guarded by `tests/test_import_purity.py`. | closed |
| T-07-02 | Tampering | Per-example / per-test backend DBs | mitigate | Throwaway `:memory:`/in-memory DB per fixture call (conftest `backend` fixture); ladybug capped via `max_db_size` + `teardown` close; `importorskip` skips (never errors) when the driver is absent. No shared-path lock, no cross-example state bleed. | closed |
| T-07-IV | Information Disclosure | Driver/dialect/narrative leak across the core seam | mitigate | Core stays driver-blind (no `ladybug` symbol, no Cypher) and narrative-free — `grep -niE 'irony\|dramatic\|\bactor\b' src/doxastica/core.py` → none. The divergence-join helper stays TEST-LEVEL with neutral naming (D-03a); only the generic `rows→tails` helper lives in core. | closed |
| T-07-04 | Repudiation / Integrity | Silent drift away from belief-base (Hansson) semantics | mitigate | AGM Recovery encoded as `@pytest.mark.xfail(strict=True, …)` with `strict=True` ON THE MARK (`tests/test_recovery_xfail.py:43-44`); `pyproject.toml` has only `addopts = "-v"` and NO global `xfail_strict`, so the mark-level flag is load-bearing. Any drift to satisfying Recovery XPASSes → suite goes red. Confirmed: test reports `xfailed`, not `xpassed`. | closed |
| T-07-WEB | Spoofing / Tampering / Repudiation / Information Disclosure / DoS / Elevation (web-app threat classes) | — | accept | N/A for an embedded, zero-network, zero-auth, single-process belief-revision library test suite — no realistic attack surface exists. See Accepted Risks Log. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-07-01 | T-07-WEB | Standard web-application STRIDE threats (spoofing, session/auth tampering, repudiation logging, network info-disclosure, DoS, privilege elevation) have no surface in this phase: doxastica is an embedded library and Phase 7 adds only in-process test code plus one pure helper. No network listener, no authentication, no sessions, no multi-user tenancy, no untrusted input (all inputs are test-authored). Re-evaluate only if a future phase introduces a network/IPC boundary or untrusted input source. | ego@anentropic.com | 2026-06-19 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-19 | 5 | 5 | 0 | /gsd-secure-phase (orchestrator, codebase-evidence verification) |

Verification method (State B, `register_authored_at_plan_time: true`, `threats_open: 0` short-circuit): each plan-time mitigation was confirmed directly against the shipped code —
- T-07-01/T-07-IV: `grep` confirmed no `ladybug` import, no string-built Cypher, no narrative naming in `src/doxastica/core.py`; `tests/test_import_purity.py` present; irony join uses exactly one `match_nodes`.
- T-07-02: conftest `backend` fixture throwaway-`:memory:` + `importorskip` + size cap/teardown confirmed.
- T-07-04: `strict=True` confirmed on the xfail mark (`tests/test_recovery_xfail.py:43-44`); no global `xfail_strict` in `pyproject.toml`; `pytest -rxX` reports `xfailed`.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-19
