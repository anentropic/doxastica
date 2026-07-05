---
id: FEAT-001
title: Stance — the ordinal epistemic enum on BeliefState (R21)
status: proposed
raised: 2026-07-04
raised_by: NVM M0 milestone review (narrative-vm _design/v2/15-nvm-milestones.md)
scope: Medium
touches: [models.py, protocol.py, core.py, ports.py, backends/memory.py, backends/ladybug.py, tests]
governing_decision: NVM R21 (RATIFIED 2026-06-12) — narrative-vm _design/v2/16-nvm-decision-register.md §281
blocks: NVM M0 core-API freeze ("R21 unblocks M0; the M0 core API ships `stance`")
---

# FEAT-001: Stance — the ordinal epistemic enum on `BeliefState`

> **Why this is a gap, not a nice-to-have.** NVM decision **R21** is RATIFIED and its
> Consequences line reads: *"the M0 core API ships `stance` (the freeze is unblocked)."*
> The milestones doc names the decision register as the input that *fixes M0's boundary*.
> doxastica currently ships a six-field `BeliefState` with **no `stance`** and no ordinal
> primitive — so a ratified M0 core deliverable is missing. Cheaper to land now, while the
> frozen value layer is still under active M0 work, than to retrofit once NVM depends on it.

## Summary

Add **`stance`** — an **ordinal epistemic enum** — as a first-class, core-visible field on
`BeliefState`, with **comparison as the only permitted operation** (no arithmetic anywhere).
The canonical ordering lives in doxastica because doxastica is the formally-tested,
LLM-free layer; every *policy* that reads or writes stance (assignment, propagation,
contradiction handling) stays **out** of the core in the NVM consumer.

```
certain  >  believed  >  suspected  >  doubted
```

## Background — what stance is (from NVM R21)

R21 retires numeric `confidence` in favour of this four-level ordinal. The rationale:
numeric confidence invites fake-precision arithmetic (multiply by a die roll, average two
witnesses, decay by 0.1) over a quantity nobody can calibrate. Four **behavioural** anchors
instead — displacing a `certain` requires certain-grade evidence, which makes
broken-certainty moments structurally rare and therefore dramatically loud.

The load-bearing invariant for **our** layer: **comparison (`>`, `==`, ordering) is the only
operation performed on stance anywhere in the system.** There is deliberately no `+`, no
scaling, no numeric decay. That is exactly why stance can live in the formally-grounded core:
an ordered enum with a total order is a testable, closed structure.

## The core / consumer split

doxastica owns **storage + the canonical ordering**; the NVM consumer owns **all policy**.

| Concern | Layer |
|---|---|
| The canonical `Stance` ordinal enum + total order | **doxastica (core)** |
| `stance` field on `BeliefState` | **doxastica (core)** |
| Ordinal comparison exposed as the only stance operation | **doxastica (core)** |
| Property-tested guarantee: ordering is total; no arithmetic path exists | **doxastica (core)** |
| Assignment rules (observed→certain, told-cap, trust modulation, inferred≤weakest premise) | consumer (NVM) — **out** |
| Weakest-link propagation + step-down | consumer (NVM) — **out** |
| Contradiction policy (higher displaces; ties → both capped at `suspected`, `CONTRADICTS`-linked "torn mind") | consumer (NVM) — **out** |
| Dice→uptake gate, persuasion inertia, verb routing, host-system DC adapters | consumer (NVM) — **out** |

Keeping the policy out is not a simplification we are choosing — R21 assigns it to the NVM
layer explicitly. The core "stores and compares," nothing more.

### Ratified 2026-07-04: stance lands on `BeliefState` only, not on core edges

R21 says *"beliefs **and epistemic edges** carry stance,"* which could read as a mandate to
put stance on edges too. It is not — once projected through the two-layer split:

- doxastica's core edges are **generic** (`SUPERSEDES`/`DEPENDS_ON`/`DERIVED_FROM`). The
  *epistemic* edges R21 means (`WITNESSED_BY`/`TOLD_BY`/`INFERRED_FROM`) are **NVM
  specialisations of `DERIVED_FROM`** and **do not exist in the core**. Storing stance on
  "epistemic edges" in the core would first require teaching the core what an epistemic edge
  is — the exact narrative leak the seam exists to prevent.
- The only stance comparison the core owes is **between competing belief states** (the
  displacement/contradiction inputs). Edge stance, where used, feeds **weakest-link
  propagation**, which R21 assigns to **NVM** — so the core never needs to compare it.
- `add_edge` carries **no property payload** today. Widening the port across both backends for
  a field only NVM would populate is speculative generality (the memory-core doc's named
  failure mode). NVM already attaches metadata to its specialised edges (source actor,
  tell-event id — memory-core §4); **edge stance is just one more such NVM attribute**, needing
  zero core change.

**Decision (RATIFIED 2026-07-04):** belief-state stance is core; **edge stance is NVM metadata
on the specialised edge, out of scope for doxastica.** R21's "edges carry stance" is thereby
*satisfied at the NVM layer*, not dropped. `add_edge` keeps its property-free signature — no
port change. Scope for v0.2.0 is therefore `BeliefState.stance` only; the edge question is
closed, not deferred.

## Requirements

### MUST
- **STANCE-01** — Define a canonical ordinal `Stance` enum with members
  `doubted < suspected < believed < certain` and a **total order**. The order is the
  contract; encode it so comparison is unambiguous (e.g. `IntEnum`, or a `StrEnum` plus an
  explicit rank map — decide under Open Questions).
- **STANCE-02** — Add `stance: Stance` to `BeliefState` (the frozen value model). This is a
  change to the "reversal-is-a-rewrite" taxonomy — treat it as a decision-grade edit.
- **STANCE-03** — Accept stance on the write surface (`revise` / `expand`) so a caller can
  set it; the value round-trips byte-stable on **both** backends (same encode/hydrate
  discipline as `value`). `contract`'s retracted copy carries the prior stance verbatim
  (mirrors the existing verbatim-value copy).
- **STANCE-04** — Expose ordinal **comparison** as the only core operation over stance. No
  core code path performs arithmetic on it.
- **STANCE-05** — Property tests (Hypothesis, both backends, oracle-independent, in the style
  of `test_invariants.py`): the enum order is total and antisymmetric; stance survives
  revise→query and get_scope_at round-trips unchanged; `contract` preserves the prior stance
  on its retracted tail; **no arithmetic operator is reachable** on the type (assert the
  negative — e.g. the enum does not support `+`/`*`, or the public surface offers no such op).

### MUST NOT
- **STANCE-N1** — No assignment logic, no weakest-link propagation, no contradiction/torn-mind
  policy, no dice/uptake/trust machinery in core. Those are NVM. A `certain`/`believed`/… name
  appearing in a *policy* role is the leak this boundary exists to prevent (cf. the existing
  `test_import_purity.py` discipline — same spirit, different axis).
- **STANCE-N2** — No numeric confidence field, ever. Stance replaces it.

## Concrete touchpoints in the current code

- `src/doxastica/models.py` — new `Stance` enum next to `Status`/`EdgeType`; add the field to
  `BeliefState` (currently exactly six fields — this makes seven). Keep the closed-taxonomy
  docstring honest about the new member.
- `src/doxastica/protocol.py` — `revise`/`expand` signatures gain the stance parameter; update
  the `BeliefStore` contract prose.
- `src/doxastica/core.py` — thread stance through `_append` / `_append_state` and the
  `_hydrate` boundary; `contract` copies the prior stored stance verbatim (Pitfall-2 sibling).
- `src/doxastica/backends/{memory,ladybug}.py` — persist the new property; ladybug schema
  bootstrap + parity oracle updated. Confirm base64/STRING-column coercion rules don't bite a
  short enum token (it won't start with `{`/`[`, so it's safe as a bare STRING).
- `tests/` — extend `test_backend_parity.py`, `test_models_frozen.py`, `test_revision_spine.py`,
  `test_scope_at.py`, and add the STANCE-05 property tests.

## Open questions / decisions to make on the doxastica side

1. **Enum representation.** `IntEnum` (ordering for free, but stores as int) vs `StrEnum` +
   explicit rank map (stores human-readable, matches `Status`/`EdgeType` house style, needs a
   rank lookup for `<`). House style leans `StrEnum` — confirm.
2. **Write-API shape & default.** Optional param on `revise`/`expand` with a default, or
   required? Assignment is an NVM concern, so the core needs a *neutral* default when the
   caller doesn't specify. Candidate: default `certain` (matches world-scope authored-canon
   and observed facts, the common M0 synthetic case) — but a default is mildly policy-flavoured,
   so pick deliberately and document it as "core default, NVM overrides."
3. **`query_scope` filtering by stance?** Not required by R21 (comparison is a primitive, not a
   query predicate). Leave `BeliefFilter` closed as-is unless a real need appears; a stance
   predicate would widen the injection-hardened filter and should clear its own bar.

## Non-goals

Everything in the "consumer (NVM) — out" table above. This feature is purely: *the field, the
ordering, the comparison, and the tests that prove them.*

## Acceptance

- `Stance` enum with a property-tested total order.
- `BeliefState.stance` persisted and round-trip-stable on in-memory **and** ladybug backends.
- `revise`/`expand` accept stance; `contract` preserves it; `get_scope_at` reconstructs it.
- STANCE-05 property suite green on both backends; no arithmetic path over stance exists.
- Zero policy logic added to core; `test_import_purity`-style boundary intact.

## References

- NVM R21 — `narrative-vm/_design/v2/16-nvm-decision-register.md` §281 (RATIFIED 2026-06-12)
- NVM memory-core seam §5a — `narrative-vm/_design/v2/05-nvm-memory-core.md` (core "stores and compares")
- NVM M0 milestone — `narrative-vm/_design/v2/15-nvm-milestones.md` §27–51
- Existing house patterns to mirror: `tests/test_invariants.py` (Hypothesis, dual-backend,
  oracle-independent), `tests/test_import_purity.py` (mechanically-enforced boundary),
  `src/doxastica/models.py` (closed frozen taxonomy).
