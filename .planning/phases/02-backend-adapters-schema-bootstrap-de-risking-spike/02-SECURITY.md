---
phase: 2
slug: backend-adapters-schema-bootstrap-de-risking-spike
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-15
---

# Phase 2 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
>
> doxastica is an in-process, append-only AGM belief-revision core. There is **no network, no
> authentication, and no untrusted external input**. The only trust boundary is in-process,
> caller-supplied data (namespace, node ids, props, depth bound) flowing into Cypher
> strings/parameters at the `LadybugBackend` seam. The `InMemoryBackend` has no query language
> at all, so its data is opaque by construction.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| consumer code → MemoryCore / InMemoryBackend | In-process API calls; stays in-process (no DB, no network). | node_id / props / value (opaque, no query language) |
| MemoryCore / caller → LadybugBackend → Cypher → `lb.Connection` | Caller-supplied namespace, node ids, props, depth bound become a Cypher string + parameters; embedded DB is in-process (no network/auth). | namespace, node ids, props, depth bound |
| test harness → both backends | Tests construct backends with fixed safe namespaces and synthetic graphs. | synthetic graph data only |
| CI runner → dependency install | CI installs declared deps/extras from the lock; base job omits the ladybug extra to prove isolation. | declared package set (no untrusted input) |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-02-IM-01 | Tampering | InMemoryBackend value storage | accept | `value` opaque blob, never eval'd / never used to build a query — no in-memory query language (`backends/memory.py:65,69`). See Accepted Risks. | closed |
| T-02-IM-02 | DoS | InMemoryBackend.traverse on cyclic graphs | mitigate | `seen`-set BFS terminates on cycles; returns a node SET, not paths (`backends/memory.py:115,118-131`; guard `:126`). Test `tests/test_backend_memory.py:74` `test_traverse_is_cycle_safe`. | closed |
| T-02-01 | Tampering | namespace interpolated into DDL/Cypher | mitigate | `_validate_namespace` enforces `^[A-Za-z_][A-Za-z0-9_]*$` (`ladybug.py:75,89-92`) at `__init__` `:119` BEFORE `_bootstrap_schema()` `:123`. Test `tests/test_backend_ladybug.py:68-73` `test_namespace_rejects_unsafe`. | closed |
| T-02-02 | Tampering | belief values / node ids in Cypher | mitigate | Structural mitigation complete: all data via `$param` binds, never string-interpolated — `upsert_node` `:199-210`, `add_edge` `:228-232`, `match_nodes` `:247-262`, `traverse` `:317`. Driver-coercion residue → DEF-02-01 (value-fidelity, not injection). | closed |
| T-02-03 | Tampering | var-length depth bound interpolated into `*1..N` | mitigate | `bound` is validated `int` (`ladybug.py:284`), runtime `raise ValueError` if `< 0` (`:288-289`, real `raise` survives `python -O`), interpolated at `:311`. Test `tests/test_backend_ladybug.py:226` `test_traverse_negative_depth_raises_valueerror`. | closed |
| T-02-04 | DoS | unbounded var-length traversal cost | mitigate | `ACYCLIC` node-distinct traversal returns a node SET (`ladybug.py:311`); `var_length_extend_max_depth={bound}` bounds engine recursion (`:309`); `None` → finite `_DEPTH_CEILING` (`:79,:284`). Tests `:126,:142,:158`. | closed |
| T-02-05 | Repudiation/Tampering | partial multi-write inconsistency | mitigate | `unit_of_work` wraps `BEGIN`/`COMMIT`/`ROLLBACK` (`ladybug.py:322-338`; rollback + re-raise on `BaseException`). Tests `tests/test_backend_ladybug.py:235` rollback, `:251` persist-on-success. | closed |
| T-02-PAR-01 | Tampering | oracle parity drift between backends | mitigate | Parametrized `backend` fixture (`conftest.py:34-55`, `params=["memory","ladybug"]`) asserts identical `(reached, frontier)` / `match_nodes`; byte-identical cross-backend `tests/test_backend_parity.py:248,260`. | closed |
| T-02-PAR-02 | Info Disclosure (test integrity) | hidden ladybug coupling in driver-free spine | mitigate | Module-level AST scan over `protocol`/`ports`/`core`/`backends.memory` (`tests/test_import_purity.py:71-79`), non-vacuous negative control `:82`, subprocess `ladybug`-blocked import `:124`. `backends/memory.py:21` carries no ladybug import. | closed |
| T-02-PKG-01 | Tampering | stale uv.lock vs reclassified pyproject | mitigate | prek `uv-lock` hook (`.pre-commit-config.yaml:19-22`) + `uv sync --locked` in CI (`quality.yml:34,77`, `pr.yml:33`, `release.yml:33`, `docs.yml:42`). Plan named `uv lock --check`; `--locked` provides the equivalent stale-lock rejection. | closed |
| T-02-PKG-02 | Spoofing | `ladybugdb` slopsquat (wrong package name) | mitigate | `pyproject.toml:19` pins `ladybug>=0.17,<0.18`; `uv.lock:366` `name = "ladybug"`; zero `ladybugdb` in `pyproject.toml`/`src/`. RESEARCH audit `02-RESEARCH.md:133,136`. | closed |
| T-02-SC | Tampering | npm/pip/cargo installs | accept | Zero new packages; `ladybug` reclassified to extra (D-03); pre-installed and audited (`02-RESEARCH.md:129-139`). See Accepted Risks. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-IM-01 | `value` is an opaque blob stored verbatim (`backends/memory.py:65,69`), never `eval`'d and never used to build a query — no query language exists in the in-memory backend. BACK-04 §6 opacity holds by construction; no in-process exploit path. | gsd-security-auditor | 2026-06-15 |
| AR-02-02 | T-02-SC | Zero new packages this phase; `ladybug` 0.17.1 was already installed and only RECLASSIFIED from a required dep to the `[ladybug]` extra (D-03). RESEARCH Package Legitimacy Audit records the audit and zero new packages. | gsd-security-auditor | 2026-06-15 |

*Accepted risks do not resurface in future audit runs.*

---

## Deferred Items (tracked, not masked)

| ID | Description | Disposition |
|----|-------------|-------------|
| DEF-02-01 | ladybug 0.17.1 coerces brace/bracket-shaped STRING params to STRUCT/LIST, breaking byte-identical round-trip of JSON-object/array `value`s. This is a **value-fidelity** defect of the driver's type inference, NOT a Cypher-injection vector — data still flows through `$param`, never string interpolation, so the T-02-02 structural mitigation is intact. No value fidelity is asserted in Phase 2 scope. Regression is visible, not masked: `tests/test_backend_parity.py:292` in-memory passes the round-trip; `:299-317` ladybug case is an explicit `xfail`. **Deferred to the Phase 3 value-encoding contract** (the core owns value encoding per BACK-04 §6). |

---

## Threat Flags from SUMMARY (`## Threat Flags`)

| Flag | Maps to | Status |
|------|---------|--------|
| value-opacity (`backends/ladybug.py`, DEF-02-01) | T-02-02 | Mapped to a registered threat. Structural injection mitigation verified present; driver-coercion residue tracked as DEF-02-01 and deferred to Phase 3. Not an unregistered flag. |

*Unregistered flags: none. Every SUMMARY threat flag maps to a registered threat ID.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-15 | 12 | 12 | 0 | gsd-security-auditor (opus) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-15
