"""
DATA-05 / DATA-06 guards — frozen-ness and the closed taxonomy.

These tests mechanically prove the value layer is immutable and that the
core-vs-extension taxonomy is *closed*: the enums have exactly the sanctioned
members and the models expose exactly the sanctioned fields. No DB fixtures —
this phase carries zero storage code.
"""

from uuid import uuid7

import pytest
from pydantic import ValidationError

from doxastica.models import (
    BeliefFilter,
    BeliefState,
    EdgeType,
    ImpactResult,
    Stance,
    Status,
)


def _make_belief_state() -> BeliefState:
    return BeliefState(
        state_id=uuid7(),
        belief_id="b1",
        scope_id="s1",
        source_event_id=uuid7(),
        value={"opaque": "blob"},
        status=Status.active,
        stance=Stance.certain,
    )


def test_belief_state_is_frozen() -> None:
    state = _make_belief_state()
    with pytest.raises(ValidationError):
        state.belief_id = "mutated"  # type: ignore[misc]


def test_status_membership_is_exactly_active_and_retracted() -> None:
    assert set(Status) == {Status.active, Status.retracted}


def test_edge_type_membership_is_exactly_the_three_generic_types() -> None:
    assert set(EdgeType) == {
        EdgeType.SUPERSEDES,
        EdgeType.DEPENDS_ON,
        EdgeType.DERIVED_FROM,
    }


def test_edge_type_excludes_structural_edges() -> None:
    members = {member.value for member in EdgeType}
    assert "HAS_REVISION" not in members
    assert "CURRENT_STATE" not in members


def test_belief_state_field_set_is_the_closed_seven() -> None:
    assert set(BeliefState.model_fields) == {
        "state_id",
        "belief_id",
        "scope_id",
        "source_event_id",
        "value",
        "status",
        "stance",
    }


def test_belief_filter_field_set_is_the_closed_four() -> None:
    assert set(BeliefFilter.model_fields) == {
        "belief_ids",
        "status",
        "event_id_min",
        "event_id_max",
    }


def test_belief_filter_constructs_with_all_none_defaults() -> None:
    f = BeliefFilter()
    assert f.belief_ids is None
    assert f.status is None
    assert f.event_id_min is None
    assert f.event_id_max is None


def test_impact_result_constructs_and_exposes_three_fields() -> None:
    result = ImpactResult(reached=(), frontier=frozenset(), truncated=False)
    assert result.reached == ()
    assert result.frontier == frozenset()
    assert result.truncated is False
    assert set(ImpactResult.model_fields) == {"reached", "frontier", "truncated"}


def test_impact_result_reached_is_an_immutable_tuple() -> None:
    # WR-03: reached must be a tuple so the frozen guarantee is complete —
    # a mutable list would allow result.reached.append(...) past frozen=True.
    result = ImpactResult(reached=(), frontier=frozenset(), truncated=False)
    assert isinstance(result.reached, tuple)


def test_belief_filter_rejects_unknown_field() -> None:
    # WR-01: extra="forbid" makes the "triple-structure leak unrepresentable"
    # claim mechanical — an unknown kwarg must raise, not be silently discarded.
    with pytest.raises(ValidationError):
        BeliefFilter(bogus=1)  # type: ignore[call-arg]


def test_belief_state_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        BeliefState(
            state_id=uuid7(),
            belief_id="b1",
            scope_id="s1",
            source_event_id=uuid7(),
            value={"opaque": "blob"},
            status=Status.active,
            stance=Stance.certain,
            provenance="leaked",  # type: ignore[call-arg]
        )
