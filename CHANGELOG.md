# Changelog

All notable changes to this project will be documented in this file.

<!-- docs-include-start -->

## Unreleased

### Bug Fixes

- Forbid extra fields on frozen models (WR-01) and make ImpactResult.reached an immutable tuple (WR-03)
- WR-01 enforce backend-blind import guard on ports.py too
- WR-02 widen traverse frontier to frozenset[UUID | str]
- WR-03 rename query_scope filter param to belief_filter
- Module-level import-purity scan in plan 02-03 + PATTERNS
- Unbreak core.py type-check now that LadybugBackend types resolve
- Annotate _value -> str so sorted() typechecks (DEF-02-02)
- WR-04 run full suite in ladybug-absent isolation CI job
- CR-01 WR-01 derive upsert MERGE key from label PK, exclude PK from SET
- WR-02 WR-03 coherent max_depth=0 traverse, runtime guards over asserts
- Resolve Open Questions marker + populate VALIDATION
- WR-01 make vacuous contract a true no-op (no Scope write)
- WR-02 assert exact BeliefState count in chain-immutability invariant
- WR-03/WR-04/WR-05 harden ladybug BackendPort interpolation + tenancy
- WR-01 read BeliefState PK from _PK_BY_LABEL in traverse
- WR-02 pin is_world boolean round-trip on production write path
- IN-01 reject non-empty edge props instead of dropping silently
- IN-03 centralize UUID7 ordering key into _order_key helper
- IN-02 DRY append/edge body into _append_state; IN-04 drop redundant return None
- WR-02 wrap get_impact traverse + re-fetch in one read unit_of_work
- WR-01 restore tenant's prior var_length cap, not literal default
- WR-03 raise on full-closure depth-ceiling hit instead of silent truncation
- IN-01 fail loud on reached/store divergence; IN-02 validate traverse direction on both backends
- WR-01 document single-call snapshot invariant in get_scope_at
- IN-01 extract _is_active_tail predicate for retracted-tail collapse
- IN-01 correct stale RED/unimplemented docstring in test_scope_at.py
- IN-02 reconcile stale Wave-0/plan-06-02 framing to present tense
- Pass --config .cliff.toml to git-cliff in CI; rm orphan changelog stub
- Cap ladybug full-closure traverse depth to avoid buffer-pool OOM
- Address PR #1 review findings

### Features

- Add frozen pydantic taxonomy and typed exceptions
- Add public BeliefStore Protocol with UUID7 ordering contract
- Add DATA-01 import-purity guard and public re-export barrel
- Author LPG-primitive BackendPort Protocol
- Draft backend-port contract spec and distinctness guard
- Add BackendDependencyError and InMemoryBackend oracle
- MemoryCore engine + driver-blind factories + package exports
- LadybugBackend ownership, namespace guard, idempotent bootstrap
- Five LPG primitives + SC4 traverse confirmation in LadybugBackend
- Parametrized backend fixture + oracle-parity suite (D-05/FORMAL-06)
- Add reserved WORLD_SCOPE_ID constant (D-02)
- Add HAS_REVISION REL table + endpoint-aware add_edge (D-07)
- Scope + derived-current + hydrate helpers (SCOPE-01/02/03, CHAIN-01, D-01/D-02/D-06)
- Revise/expand/contract + get_revision_chain spine ops (OPS-01/02/03, CHAIN-02/03, HIST-02, D-03/D-04/D-05/D-07)
- Implement query_scope (group-by-belief max -> filter -> sort -> hydrate)
- Add keyword-only direction param to BackendPort.traverse + BACK-04
- Route in-memory traverse on direction via reverse-adjacency _in_edges
- Make ladybug traverse direction-aware via a 3-arrow flip
- Implement MemoryCore.add_edge passthrough (EDGE-01, D-06/D-07)
- Implement MemoryCore.get_impact (EDGE-02 cascade)
- Implement MemoryCore.get_scope_at temporal reconstruction
- Add PyPI-ready metadata to pyproject.toml (PKG-04)
- Relocate backend contract into docs_dir and add nav entry

### Miscellaneous

- Add project config
- Add workflow.ai_integration_phase key
- Render cookiecutter scaffold under import name doxastica
- Pin runtime deps to ladybug + pydantic, add hypothesis to dev
- Add GitHub Copilot instructions to ignore .planning/

### Refactoring

- Rename include_deprecated -> include_retracted (D-03)
- Factor status-agnostic _current_tail; _current delegates to it
- Extract pure _current_tails rows->tails helper (D-01a)
- Move factory classmethods to factories.py
- Remove factories layer for pure-DI construction

### Testing

- Guard frozen-ness and closed taxonomy
- Extend import-purity to driver-blind core + memory (D-02)
- Add Wave-0 revision-spine behavior scaffold over both backends
- Add Hypothesis spine consistency machine + fix derived-current after contract
- Flip DEF-02-01 xfail to a passing core-routed regression
- Add failing Wave-0 query_scope behavior scaffold (both backends)
- Add failing reverse-direction (direction='in') parity cases
- Add failing add_edge mechanism tests (idempotency, closed enum, D-07 no-op)
- Add failing get_impact mechanism + property tests
- Add failing example tests for get_scope_at cut-rewind
- Operational-fold oracle + get_scope_at==fold property (D-07)
- Add AGM revision postulates to _SpineMachine (FORMAL-01, BACK-05)
- Add Hansson contraction postulates + FORMAL-03 registry (FORMAL-02/03, BACK-05)
- Register get_scope_at ≡ replay into FORMAL-03 conformance set
- Add Recovery strict-xfail + superseded-chain positives
- Two-scope divergence demo, one round-trip (FORMAL-05, BACK-05)
- Repoint factory callers to doxastica factories
- Repoint tests off removed factories layer

### Build

- Demote ladybug to opt-in extra (D-03 Option B)

### Ci

- Two-env CI + reverse CLAUDE.md dep constraint (D-03)

### Style

- Wrap WR-02 comment to satisfy ruff E501
- Apply ruff format and fix .gitignore trailing whitespace
