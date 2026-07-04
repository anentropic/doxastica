"""
The FORMAL-05 showcase — two scopes diverging on a proposition (``belief_id``), Wave 2.

This is the "irony join" of the roadmap (the name is informal; nothing narrative leaks into
core — D-03a): two belief scopes that have a different CURRENT value for the SAME
scope-independent proposition. The demonstration is computed as exactly ONE port round-trip
(a single full-label ``BeliefState`` node scan) and compared against a plain-Python
expected oracle built directly from the known synthetic writes (D-03).

Load-bearing decisions encoded here:

- **The divergence join is TEST-LEVEL (D-03a / RESEARCH Open Q3).** The narrative-adjacent
  demonstration stays out of ``core.py``; only the generic ``_current_tails`` rows->tails
  helper (extracted in 07-01) lives in core. No ``irony``/``actor``/``world_truth``/
  ``dramatic_irony`` symbol appears as a core name — an "actor" scope is just any non-world
  scope, and ``WORLD_SCOPE_ID`` already exists.
- **ONE port round-trip (D-01/D-01a/D-02).** "Single query" means one round-trip: a single
  full-label ``BeliefState`` node scan (the synthetic data is small so the scan
  is cheap and honest), then both scopes are filtered SEPARATELY in Python and each reduced to
  its current tails by reusing the 07-01 ``_current_tails`` helper (single-sourcing the
  ``_order_key`` group-by-max + retracted-tail collapse). NOT two scan calls and NOT
  two scope-query calls — that is two round-trips, the Anti-Pattern; the port's
  AND-equality filter cannot express ``scope_id IN {a, b}``.
- **Inner-join on ``belief_id`` (D-02).** ``belief_id`` IS the scope-independent proposition id;
  the SUPERSEDED ARCHITECTURE.md ``CURRENT_STATE``/``HOLDS``/``belief_id_logical`` Cypher does
  not exist (current is derived; there is no ``belief_id_logical``). Emit a row only where BOTH
  scopes hold the proposition (inner join) AND the DECODED values differ.
- **Cross-backend parity (D-03 / BACK-05).** The ``backend`` fixture runs each test once per
  backend (``["memory", "ladybug"]``), with identical core logic; comparison to the same
  plain-Python expected already proves cross-backend agreement. The ladybug param SKIPS (not
  fails) when the driver is absent.

Driver-blind: NO ``ladybug`` import, NO constructed query string, NO port widening — the join
composes only the public/``_decode_value`` surface plus the 07-01 ``_current_tails`` helper.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from doxastica import WORLD_SCOPE_ID, MemoryCore
from doxastica.core import _current_tails  # the 07-01 extracted rows->tails helper (D-01a)
from doxastica.models import Status

if TYPE_CHECKING:
    from doxastica.ports import BackendPort


def _event_id() -> uuid.UUID:
    """Mint a fresh caller-side ``source_event_id`` (UUID7, time-ordered, RFC 9562 section 5.7)."""
    return uuid.uuid7()


# --------------------------------------------------------------------------------------------
# The TEST-LEVEL divergence join (D-03a — kept out of core; reuses only `_current_tails`).
# --------------------------------------------------------------------------------------------


def diverging_beliefs(
    core: MemoryCore,
    scope_a: str,
    scope_b: str,
) -> list[tuple[str, Any, Any]]:
    """
    Return ``(belief_id, value_a, value_b)`` rows where ``scope_a`` and ``scope_b`` DIVERGE.

    The FORMAL-05 join, computed as exactly ONE port round-trip (D-01/D-01a/D-02): a single
    full-label ``BeliefState`` node scan, then both scopes filtered SEPARATELY in
    Python and reduced to their active current tails via the 07-01 ``_current_tails`` helper
    (single-sourcing the ``_order_key`` group-by-max + retracted-tail collapse — a retracted
    current tail means the belief is ABSENT, so it cannot diverge). Inner-joins on ``belief_id``
    (D-02: the scope-independent proposition id) and emits a row only where the DECODED values
    differ. Driver-blind — composes only the node scan / ``_current_tails`` / ``_decode_value``;
    no second round-trip, no constructed query, no ``ladybug`` import (T-07-01 / T-07-IV).
    """
    # ONE round-trip: the full-label scan ("single query" = one round-trip, D-01a). The port's
    # AND-equality filter cannot express `scope_id IN {a, b}`, so we filter both scopes in Python
    # below — NOT a second scan and NOT two scope-query calls (the Anti-Pattern, D-01a).
    rows = core._backend.match_nodes("BeliefState", {})  # pyright: ignore[reportPrivateUsage]
    active = frozenset({Status.active})
    rows_a = [r for r in rows if r["scope_id"] == scope_a]
    rows_b = [r for r in rows if r["scope_id"] == scope_b]
    # reuse the 07-01 extracted helper per scope (D-01a single-source): group-by-belief_id ->
    # per-belief ordering-MAX over ALL statuses -> active-tail filter AFTER the max (Pitfall 2).
    tails_a = _current_tails(rows_a, active)
    tails_b = _current_tails(rows_b, active)
    out: list[tuple[str, Any, Any]] = []
    for belief_id in tails_a.keys() & tails_b.keys():  # inner join on belief_id (D-02)
        value_a = MemoryCore._decode_value(tails_a[belief_id]["value"])  # pyright: ignore[reportPrivateUsage]
        value_b = MemoryCore._decode_value(tails_b[belief_id]["value"])  # pyright: ignore[reportPrivateUsage]
        if value_a != value_b:
            out.append((belief_id, value_a, value_b))
    return out


# --------------------------------------------------------------------------------------------
# FORMAL-05 — two scopes diverge on a proposition; one round-trip vs a plain-Python oracle.
# --------------------------------------------------------------------------------------------


def test_irony_join_two_scopes_diverge(backend: BackendPort) -> None:
    """
    Two scopes diverging on ``belief_id`` are recovered from ONE round-trip (FORMAL-05, D-01..D-03).

    Synthetic writes (D-03) into a world scope and one actor (non-world) scope cover every join
    edge case: a shared proposition with DIFFERING current values (must appear), a shared
    proposition with EQUAL values (must NOT appear), propositions present in only ONE scope (must
    NOT appear — inner join), and a shared proposition whose actor-scope current tail is RETRACTED
    (must NOT appear — a retracted tail is absent, so it cannot diverge). The expected divergent
    rows are computed by a plain-Python oracle directly from the known writes — NOT by re-running
    ``diverging_beliefs`` — and compared order-insensitively. Because the ``backend`` fixture runs
    this once per backend with identical core logic, the comparison to the plain-Python expected
    already proves cross-backend parity (BACK-05).
    """
    core = MemoryCore(backend)
    world = WORLD_SCOPE_ID
    actor = "scope:observer"  # an "actor" scope is just any non-world scope (D-03a)

    # --- known synthetic writes (the plain-Python oracle below mirrors exactly these) --------
    # p_diverge: shared, DIFFERING current values -> the one expected divergent row.
    core.revise(world, "p_diverge", "raining", _event_id())
    core.revise(actor, "p_diverge", "sunny", _event_id())
    # p_agree: shared, EQUAL current values -> excluded (no divergence).
    core.revise(world, "p_agree", "tuesday", _event_id())
    core.revise(actor, "p_agree", "tuesday", _event_id())
    # p_world_only / p_actor_only: present in ONE scope only -> excluded (inner join).
    core.revise(world, "p_world_only", "secret", _event_id())
    core.revise(actor, "p_actor_only", "hunch", _event_id())
    # p_retracted: shared and would diverge, BUT the actor's current tail is RETRACTED ->
    # excluded (a retracted current tail is absent, so the proposition cannot diverge).
    core.revise(world, "p_retracted", "alive", _event_id())
    core.revise(actor, "p_retracted", "alive", _event_id())
    core.revise(actor, "p_retracted", "dead", _event_id())  # actor diverges momentarily...
    core.contract(actor, "p_retracted", _event_id())  # ...then retracts -> absent in actor

    # --- plain-Python expected oracle (D-03): computed independently from the writes above ----
    # The ONLY belief shared by both scopes whose ACTIVE current values differ is p_diverge.
    expected: set[tuple[str, Any, Any]] = {("p_diverge", "raining", "sunny")}

    got = diverging_beliefs(core, world, actor)

    # order-insensitive compare (the join's row order is non-contractual).
    assert set(got) == expected
    assert len(got) == len(expected), f"no duplicate/extra rows; got {got!r}"
