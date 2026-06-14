# Demo concept (post-v1 / post-M0)

> **Status:** parked idea, not part of M0 scope. Build *after* the v1 library (M0 exit
> gate) is green. Recorded here so it isn't lost and can lightly inform M0 decisions
> (esp. the in-memory backend and API ergonomics). Flesh out scenario scripts later with
> `/gsd:explore` or mock the UI with `/gsd:sketch`.

## What it is

**`doxastica-demo`** — a terminal **TUI** (Textual) "belief inspector" that shows off
doxastica's *novel, non-retrieval* capabilities to an "AI agents for business" audience.
The reframe it sells: every agent-memory product today is a **retrieval** system; doxastica
is a **belief** system — it knows what an agent holds true, what's *actually* true, what the
agent got *wrong*, *why*, and what *changes* when a fact is retracted. None of those are
retrieval questions; a RAG agent cannot answer them.

The LLM (if any) is just glue that turns scenario events into belief operations
(`revise`/`expand`/`add_edge`). The novel capability on stage is doxastica's.

## Constraints (from the user)

- **Simple but surprising.**
- **Exercises both extensions** — multi-scope **and** time-travel (`get_scope_at`).
- **Easy to run locally**, no hosted server. Minimal input: pick a predefined example, hit **Play**.

## Form & run model

- **Terminal TUI (Textual)** — `uvx doxastica-demo`; no browser, no server.
- Runs on the **in-memory backend** — so the demo *also* exercises the pluggable-backend
  extension, and needs no LadybugDB file or external service. (Nice three-for-one: the demo
  that shows extensions #1 multi-scope and #2 time-travel *runs on* extension #3 backends.)

## The two controls ARE the two extensions

- **Scope-compare** (multi-scope) — pick scope A vs scope B → divergence / irony panel
  ("everything scope X believes that scope Y / the world scope contradicts"). Realised by
  `query_scope` across two scopes joined on `belief_id`.
- **Timeline scrubber** (time-travel) — drag to any past event → belief state *as of then*
  via `get_scope_at`; watch a belief flip at the event that flipped it.
- **Mark-false / retract** action — `get_impact` lights up dependent beliefs/recommendations
  as invalidated (the contrast with RAG, which silently keeps stale conclusions).

## Canned scenarios (ship as data; same app)

1. **Account agent that admits + propagates its mistakes** (B2B customer success).
   Account scope vs. world scope (verified billing/usage truth). Surprises: "what's it wrong
   about?" panel (irony join); retract "champion is Alice" → dependent recommendations
   invalidate (cascade); rewind 30 days (time-travel). *Lead/flagship.*
2. **Boardroom of disagreeing analysts** (due-diligence; N agents = N scopes). Surfaces the
   contested-claims map + evidence instead of a blended answer. Purest multi-scope showcase.
3. **Compliance recall engine** (lending/insurance/hiring). Retract a bad data source →
   auto-generate the list of past decisions to revisit (cascade); reconstruct the agent's
   state-of-mind at decision time (time-travel). Same engine as #1, risk/regulator skin.
4. **Unreliable-source tracer** (threat-intel / supply chain). Flag one compromised feed →
   compute the blast radius of dependent beliefs (`DERIVED_FROM` cascade). Closest to NVM's
   provenance roots.

## Forward-implications for M0 (small — keep in mind, don't expand scope)

- The **in-memory backend** (BACK-03) should be ergonomic enough to seed a scripted scenario
  quickly and to support the demo's read patterns — it already must exist for the Phase 7
  conformance oracle, so the demo adds no M0 work, only a reason to keep its API pleasant.
- A clean way to **replay a scripted event stream** into belief ops, and to ask for
  "state as of event N," makes both the demo and the test harness nicer — `get_scope_at`
  already covers the latter.
- Nothing here changes the M0 exit gate; do not add demo requirements to REQUIREMENTS.md.
