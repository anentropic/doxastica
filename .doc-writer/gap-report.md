# Gap Detection Report

**Source root:** src/
**Language:** Python
**Total exported symbols:** 25 (15 public API names in `doxastica.__all__` + 10 `BeliefStore`/`BackendPort` protocol methods)
**Documented symbols:** 25
**Undocumented symbols:** 0

> Supersedes the 2026-06-22 gap report, which predated the current prose doc set
> (tutorials/, how-to/, explanation/). The operation and concept gaps it listed are
> now filled by dedicated pages.

## Undocumented Exports

| Symbol | File | Type |
|--------|------|------|
| _(none)_ | — | — |

Every public export in `doxastica.__all__` and every method on the `BeliefStore`
and `BackendPort` protocols is referenced in at least one documentation file.

## Notes

- Coverage is well-distributed across the four Diataxis buckets: the tutorial and
  how-to guides carry the operation verbs (`revise`, `contract`, `query_scope`,
  `get_revision_chain`, `get_scope_at`, `get_impact`), and the explanation set
  carries the conceptual types (`BeliefState`, `EdgeType`, `Status`, `WORLD_SCOPE_ID`).
- Thinner (single-file) coverage — worth a glance for depth, not a true gap:
  `DoxasticaError`, `WORLD_SCOPE_ID`, `ImpactResult`, `WorldScopeContractionError`,
  `BackendDependencyError`. These are edge/error types, so light coverage is expected.
- `BackendPort` and its methods (`upsert_node`, `add_edge`, `match_nodes`,
  `traverse`, `unit_of_work`) are internal-seam symbols; they appear in
  `backend-contract.md` and the ladybug how-to, which is the right altitude.
