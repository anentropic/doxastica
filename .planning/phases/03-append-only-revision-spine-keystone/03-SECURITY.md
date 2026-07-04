---
phase: 03-append-only-revision-spine-keystone
audited_at: 2026-06-16
asvs_level: 1
block_on: high
threats_total: 12
threats_closed: 12
threats_open: 0
status: SECURED
---

# Phase 3: Security Audit — Append-Only Revision Spine (Keystone)

**Audited:** 2026-06-16
**ASVS Level:** 1 (zero-LLM, zero-network, embedded library — surface kept proportional)
**Disposition:** register authored at plan time; this audit VERIFIES each declared mitigation
exists in the implemented code/tests — it does not build a fresh STRIDE register.
**Result:** 12/12 threats CLOSED. No blockers. No unregistered flags.

The full suite for the verification surface (`tests/test_revision_spine.py`,
`tests/test_invariants.py`, `tests/test_backend_parity.py`) was executed during this audit:
**50 passed, 0 xfail/xpass** on both backends (memory + ladybug). The integrity and append-only
controls are not merely present in source — they are mechanically green.

## Threat Verification (mitigate)

| Threat ID | Category | Evidence |
|-----------|----------|----------|
| T-03-01 | Tampering (DDL) | `src/doxastica/backends/ladybug.py:187-216` — `_bootstrap_schema` interpolates ONLY `{ns}` (validated by `_validate_namespace` / `_NS_RE` at `__init__`, line 151). The new `HAS_REVISION` DDL (`:213-216`) is fixed structural text `FROM {ns}_Belief TO {ns}_BeliefState`; no caller data is interpolated. |
| T-03-02 | Tampering (add_edge) | `ladybug.py:257-286` — `from_id`/`to_id` are `$param` binds (`{"from": str(from_id), "to": str(to_id)}`, line 285). Endpoint labels resolve from the closed `_EDGE_ENDPOINTS` map (`:100-105`, `:276`); only validated namespace + fixed labels + edge-type label are interpolated. An endpoint id of `"; DROP …"` is inert bind data. |
| T-03-03 | Tampering (value round-trip, DEF-02-01) | `core.py:184-199` (`_encode_value`/`_decode_value`) + `:248` (encode once on write) + `:214` (`_hydrate` decode on read) + `:326` (contract copies the already-encoded stored token VERBATIM, no double-encode). Implemented as base64-over-JSON — the documented deviation from bare `json.dumps` because ladybug's STRING column coerces brace/bracket-leading literals. Identical on both backends. Proven by `test_brace_value_round_trips` (`test_revision_spine.py:195`) and the flipped `test_value_string_round_trips_ladybug` (`test_backend_parity.py:316`), both green. |
| T-03-04 | Tampering/Elevation (value as exec surface) | `core.py` — the opaque `value` is ONLY `json.dumps`-encoded (`:194`) and base64-wrapped, then handed to the port as a STRING bind via `upsert_node` props (`:248-251`). No `eval`/`exec`; the core builds NO query from the value (the port exposes no query-string method — `ports.py:56-116`). Pure data. |
| T-03-06 | Tampering (append-only bypass) | `core.py` — `revise`/`expand`/`_append` (`:219-282`) and `contract` (`:284-332`) are pure appends: `upsert_node` on a never-reused `uuid.uuid7()` `state_id` (`:242`, `:320`) + `add_edge` MERGE. `ports.py:56-116` exposes NO delete/replace primitive. World-scope contract is structurally refused FIRST, before any backend access (`core.py:308-311`), verified by `test_world_contract_raises` asserting an empty chain after the raise (`test_revision_spine.py:66-74`). |
| T-03-07 | Tampering (integrity verification tests) | `test_revision_spine.py:195` (`test_brace_value_round_trips`) and `:211` (`test_retracted_value_byte_identical_to_superseded`) — regression tests pinning the value-encoding + no-double-encode controls. Both green on both backends. |
| T-03-08 | Information disclosure (negative test) | `test_revision_spine.py:66-74` (`test_world_contract_raises`) — asserts `WorldScopeContractionError` is raised AND `get_revision_chain("b") == []` afterward, proving no write leaked before the guard fired (D-03). |
| T-03-09 | Tampering (append-only @invariant) | `test_invariants.py:297-315` (`chain_is_immutable`) — stateful `RuleBasedStateMachine` asserts total `BeliefState` count `== self._state_count` (EXACT equality, tightened by WR-02; `:311`). Catches deletes, mutations, AND duplicate writes across arbitrary op sequences on both backends. |
| T-03-10 | Tampering (derived-current consistency + DEF-02-01 flip) | `test_invariants.py:258-295` (`current_is_total_single_valued_and_chain_tail`) — `_current` proven total, single-valued, and ≡ the independently-computed HAS_REVISION chain tail (`_chain_tail`, `:87`) over arbitrary sequences. DEF-02-01 flip: `test_backend_parity.py:316` no longer carries `@pytest.mark.xfail` (grep confirmed zero `pytest.mark.xfail` in file) and asserts the brace round-trip through `MemoryCore.revise` + `get_revision_chain`. |

### Code-review hardening (verified landed — register footnote)

| Item | Evidence |
|------|----------|
| WR-02 (exact-equality) | `test_invariants.py:311` — `assert total == self._state_count` (was `>=`). |
| WR-03 (traverse edge-type validation + reject empty) | `ladybug.py:353-357` — empty `edge_types` raises; each `et` constrained to `_EDGE_ENDPOINTS` before interpolation. |
| WR-04 (prop/where key validation) | `ladybug.py:114-124` (`_validate_identifier`) called at `:248` (`upsert_node`) and `:306` (`match_nodes`). |
| WR-05 (var_length_extend_max_depth try/finally restore) | `ladybug.py:384-397` — cap raised only when `bound > _DEFAULT_HOP_CAP` (`:389`) and restored in `finally` (`:394-397`), so an injected tenant connection (R19, `owns_conn=False`) is never left mutated. |

## Accepted Risks (accept — premise re-verified)

| Threat ID | Category | Premise verification |
|-----------|----------|----------------------|
| T-03-05 | Tampering (scope_id/belief_id injection) | **Premise holds.** `core.py` writes NO Cypher; ids cross to the port and become `$param` binds (`ladybug.py:239`, `:285`, `:307-309`). A scope named `"; DROP …"` is inert data. Accepted as a by-construction property of the port. |
| T-03-AO | Tampering (append-only bypass via new REL table/add_edge) | **Premise holds.** No edge-delete/replace primitive added — `ports.py:56-116` (BackendPort) exposes only `upsert_node`/`add_edge`/`match_nodes`/`traverse`/`unit_of_work`. `HAS_REVISION` is MERGE-append-only (`ladybug.py:282-286`; `memory.py:71-83`). |
| T-03-05/SC | Tampering (supply chain — npm/pip/cargo) | **Premise holds.** Zero new runtime deps this phase. `pyproject.toml:10-19` — `pydantic` is the sole required dep; `ladybug` is the only optional extra. Phase 3 adds only stdlib `json`/`uuid`/`base64` (`core.py:46-48`). Package Legitimacy Audit unchanged. |

## Threat Flags (from SUMMARY ## Threat Flags / ## Threat Surface)

All four plan SUMMARYs declare **None** beyond the plan threat models:
- 03-01 `## Threat Surface`: none (namespace remains the only interpolated identifier; no edge-delete primitive; no installs).
- 03-02 `## Threat Flags`: None (T-03-03 mitigated via base64-over-JSON; core writes no Cypher, never evals value).
- 03-03 `## Threat Surface`: none (test-only; authors the integrity regressions).
- 03-04 `## Threat Flags`: None (T-03-09/T-03-10 now mechanically verified; test-only + a read-path correctness fix to `_current`).

**Unregistered flags:** none. No new attack surface appeared during implementation that lacks a threat mapping.

### Note on the in-flight `_current` fix (03-04)

03-04 caught and fixed a real `_current` defect (a contracted belief still reporting an active
current). This is a **correctness** fix on the derived-current read path, not a new security
surface — it strengthens the append-only/consistency story rather than opening one, and is now
locked by the keystone consistency `@invariant`. No threat reclassification required.

## Audit Conclusion

All 12 register entries resolve: **9 mitigate → CLOSED** (evidence located in the cited
implementation/test files and confirmed green), **3 accept → premise re-verified and holding**.
The four code-review hardening items (WR-02..WR-05) are confirmed present. The implementation files
were not modified by this audit. **Phase 3 is cleared to ship from a security standpoint.**

---
_Audited: 2026-06-16 — gsd-security-auditor (verify-only; register authored at plan time)_
