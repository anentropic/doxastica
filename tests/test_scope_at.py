"""
The Wave-0 example-test scaffold for HIST-03 — ``MemoryCore.get_scope_at`` (Phase 6).

``get_scope_at(scope, as_of_event_id)`` reconstructs the active belief base of a scope AS OF an
event, purely structurally from the immutable ``source_event_id``-ordered ``BeliefState`` nodes.
It is the temporal sibling of ``query_scope`` with ONE structural change (D-02/D-03): the inclusive
``source_event_id <= as_of`` CUT is applied to the candidate states BEFORE the per-belief
ordering-max (cut-then-max = REWIND), in place of ``query_scope``'s ``event_id_max`` POST-filter
(max-then-filter = DROP). An OLDER value must resurface for a since-revised belief.

Two load-bearing conventions, inherited verbatim from ``tests/test_query_scope.py``:

1. **Parametrized over the ``backend`` fixture** (``conftest.py`` ``params=["memory", "ladybug"]``):
   every test takes ``backend: BackendPort`` and runs once per backend, so each behavior is proven
   on BOTH the in-memory oracle and the ladybug reference adapter. The ladybug param is skipped —
   not failed — when the optional driver is absent.
2. **Construct ``MemoryCore(backend)`` from the INJECTED fixture port** — NOT the zero-dependency
   in-memory factory classmethod — so the ladybug backend is exercised at all.

This is the example-test HALF (the cut-rewind regression guard for the central trap). The
operational-fold ``RuleBasedStateMachine`` + the ``fold(ops, as_of)`` oracle (D-07) are added to
THIS file by plan 06-02.

RED-until-06-02-impl is the correct, intended state: ``MemoryCore.get_scope_at`` has no body yet
(the protocol stub returns ``...``). Do NOT weaken these tests to make them pass — the body lands in
Task 2 of this plan.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, cast

from doxastica import WORLD_SCOPE_ID, BeliefFilter, BeliefStore, MemoryCore

if TYPE_CHECKING:
    from doxastica.models import BeliefState
    from doxastica.ports import BackendPort


def _event_id() -> uuid.UUID:
    """Mint a fresh caller-side ``source_event_id`` (UUID7, time-ordered, RFC 9562 section 5.7)."""
    return uuid.uuid7()


def _core(backend: BackendPort) -> BeliefStore:
    """
    Build a ``MemoryCore`` over the injected fixture port, typed as the public ``BeliefStore``.

    ``cast`` is a RUNTIME no-op (it returns the object unchanged), so ``get_scope_at``
    type-checks against its ``-> list[BeliefState]`` Protocol signature while the test still
    fails RED at RUNTIME until Task 2 fills the body. ``MemoryCore`` does not yet fully satisfy
    ``BeliefStore`` (``add_edge`` lands in a later phase), so a direct annotated assignment would
    (correctly) fail strict typing — the ``cast`` narrows only the one surface this scaffold
    exercises, keeping basedpyright + ruff clean.
    """
    return cast("BeliefStore", MemoryCore(backend))


def _ids(states: list[BeliefState]) -> set[str]:
    """Project the ``belief_id`` set out of a result (order-insensitive compare)."""
    return {s.belief_id for s in states}


def _value_of(states: list[BeliefState], belief_id: str) -> object:
    """Return the single ``value`` for ``belief_id`` in ``states`` (assumes exactly one tail)."""
    return next(s.value for s in states if s.belief_id == belief_id)


# --------------------------------------------------------------------------------------------
# HIST-03 / D-03 — the central trap: the cut REWINDS (re-derives the tail), it does NOT drop.
# --------------------------------------------------------------------------------------------


def test_cut_rewinds_to_older_value(backend: BackendPort) -> None:
    """
    D-03: revise→revise, ``get_scope_at(scope, first_event)`` returns the OLDER value.

    The Phase-6 mirror of ``test_query_scope.py::test_event_range_postfilter`` — SAME revise→revise
    setup, but the cut REWINDS (returns ``"w_old"``) where ``query_scope``'s ``event_id_max`` DROPS
    (returns nothing). An older value resurfaces for a since-revised belief.
    """
    core = _core(backend)
    e_a = _event_id()
    e_b_old = _event_id()
    e_b_new = _event_id()  # B's CURRENT tail — strictly newer than e_b_old
    core.revise("s", "A", "v0", e_a)
    core.revise("s", "B", "w_old", e_b_old)
    core.revise("s", "B", "w_new", e_b_new)  # B's current tail carries e_b_new

    # Cut just AT B's older event: B must REWIND to "w_old" (NOT absent, NOT "w_new").
    result = core.get_scope_at("s", e_b_old)
    assert _ids(result) == {"A", "B"}, "the cut rewinds B rather than dropping it (D-03)"
    assert _value_of(result, "B") == "w_old", "B resurfaces at its older value current at the cut"
    assert _value_of(result, "A") == "v0", "A is unchanged at the cut"


# --------------------------------------------------------------------------------------------
# HIST-03 / D-04 — the cut is INCLUSIVE: source_event_id == as_of IS included.
# --------------------------------------------------------------------------------------------


def test_cut_is_inclusive_at_boundary(backend: BackendPort) -> None:
    """D-04: a state whose ``source_event_id == as_of`` IS included (inclusive cut)."""
    core = _core(backend)
    e_first = _event_id()
    e_b = _event_id()  # B written exactly at the cut boundary
    core.revise("s", "A", "v0", e_first)
    core.revise("s", "B", "w0", e_b)

    # Cut == B's exact write event: B is INCLUDED (boundary is inclusive).
    result = core.get_scope_at("s", e_b)
    assert _ids(result) == {"A", "B"}, "a belief written at exactly the cut is present (D-04)"
    assert _value_of(result, "B") == "w0", "the boundary belief carries its written value"


# --------------------------------------------------------------------------------------------
# HIST-03 / SC1 / D-04 — get_scope_at(latest) == query_scope(current).
# --------------------------------------------------------------------------------------------


def test_scope_at_latest_equals_query_scope_now(backend: BackendPort) -> None:
    """SC1: for a cut >= every written event, get_scope_at(latest) == query_scope(current)."""
    core = _core(backend)
    core.revise("s", "A", "v0", _event_id())
    core.revise("s", "B", "w0", _event_id())
    core.revise("s", "B", "w1", _event_id())
    core.contract("s", "B", _event_id())  # B retracted "now"
    core.revise("s", "C", "x0", _event_id())
    latest = _event_id()  # strictly newer than every written source_event_id
    core.revise("s", "C", "x1", latest)

    at_latest = {(s.belief_id, s.value) for s in core.get_scope_at("s", latest)}
    now = {(s.belief_id, s.value) for s in core.query_scope("s", BeliefFilter())}
    assert at_latest == now, "an as-of cut at/after the latest event equals the current base (SC1)"


# --------------------------------------------------------------------------------------------
# HIST-03 / D-06 — retracted-as-of collapse, computed over the cut window not "now".
# --------------------------------------------------------------------------------------------


def test_retracted_as_of_collapse(backend: BackendPort) -> None:
    """
    D-06: a belief contracted AT/BEFORE the cut is ABSENT; one contracted only AFTER is PRESENT.

    The retracted collapse is computed over the ``<= as_of`` window, not "now": belief B's
    retraction lies before the cut (B absent), belief C's retraction lies after the cut (C present
    at its as-of value).
    """
    core = _core(backend)
    core.revise("s", "B", "wb", _event_id())
    e_b_retract = _event_id()
    core.contract("s", "B", e_b_retract)  # B retracted at/before the cut

    core.revise("s", "C", "wc", _event_id())
    cut = _event_id()  # the as-of cut: after B's retraction, before C's later retraction
    e_c_retract = _event_id()
    core.contract("s", "C", e_c_retract)  # C retracted AFTER the cut

    result = core.get_scope_at("s", cut)
    assert _ids(result) == {"C"}, "B (retracted before cut) absent; C (retracted after) present"
    assert _value_of(result, "C") == "wc", "C is present at its as-of value (retraction is later)"


# --------------------------------------------------------------------------------------------
# HIST-03 / D-05 — a single multi-belief event folds ALL its writes inclusively.
# --------------------------------------------------------------------------------------------


def test_single_event_multi_belief_inclusive(backend: BackendPort) -> None:
    """D-05: two beliefs sharing ONE source_event_id both appear when the cut == that event id."""
    core = _core(backend)
    e_shared = _event_id()  # ONE event id reused across two different belief_ids
    core.revise("s", "A", "va", e_shared)
    core.revise("s", "B", "vb", e_shared)

    # Cut == the shared event: BOTH writes of that event fold into the base inclusively.
    result = core.get_scope_at("s", e_shared)
    assert _ids(result) == {"A", "B"}, "a single multi-belief event folds ALL its writes (D-05)"
    assert _value_of(result, "A") == "va"
    assert _value_of(result, "B") == "vb"


# --------------------------------------------------------------------------------------------
# HIST-03 / D-02 / D-08 — absent/empty scope → [], no Scope node; world is a valid read.
# --------------------------------------------------------------------------------------------


def test_empty_scope_and_world_read(backend: BackendPort) -> None:
    """D-02/D-08: never-created scope → [] (no Scope node); world is a valid read target."""
    core = _core(backend)

    # A never-created scope: pure read returns [] and creates NO Scope node.
    empty = core.get_scope_at("never_created", _event_id())
    assert empty == [], "an absent scope reconstructs to the empty base"
    assert backend.match_nodes("Scope", {"scope_id": "never_created"}) == [], (
        "get_scope_at is a pure read — it creates no Scope node (D-08)"
    )

    # The world scope is a valid read target (reads never trigger the world-scope guard).
    world_empty = core.get_scope_at(WORLD_SCOPE_ID, _event_id())
    assert world_empty == [], "an empty world scope reconstructs to [] without raising (D-02)"

    core.revise(WORLD_SCOPE_ID, "fact", "true", _event_id())
    world = core.get_scope_at(WORLD_SCOPE_ID, _event_id())
    assert _ids(world) == {"fact"}, "get_scope_at(world, e) reads the world base without a guard"


# --------------------------------------------------------------------------------------------
# HIST-03 / D-01 — result is _order_key-sorted, byte-identical across both backends.
# --------------------------------------------------------------------------------------------


def test_scope_at_deterministic_order(backend: BackendPort) -> None:
    """D-01: the result is ``_order_key``-sorted (source_event_id, then state_id), both backends."""
    core = _core(backend)
    # Write in a deliberately non-sorted belief order; the result must come back ordered.
    e1 = _event_id()
    e2 = _event_id()
    e3 = _event_id()
    core.revise("s", "C", "vc", e3)
    core.revise("s", "A", "va", e1)
    core.revise("s", "B", "vb", e2)
    cut = _event_id()

    result = core.get_scope_at("s", cut)
    keys = [(str(s.source_event_id), str(s.state_id)) for s in result]
    assert keys == sorted(keys), "the result is _order_key-sorted (no traverse consulted, D-01)"
    # The same byte-identical sequence on whichever backend the fixture supplied.
    assert [s.belief_id for s in result] == ["A", "B", "C"], "sorted by ascending source_event_id"
