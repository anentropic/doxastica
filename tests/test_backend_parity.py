"""
The oracle-parity suite (D-05 / BACK-03 / FORMAL-06) — both backends must agree exactly.

This is the hard parity guarantee, a first-class Phase-2 test and NOT deferred to Phase 7:
the ladybug reference adapter and the in-memory oracle must return IDENTICAL
``(reached, frontier)`` and ``match_nodes`` results on the same inserts. Drift between them
is the exact failure the parametrized ``backend`` fixture (conftest) is built to catch.

Two complementary shapes are used:

1. Tests that consume the parametrized ``backend`` fixture and compare each backend's output
   to an expected literal — because the fixture runs once per backend, agreement with the
   literal already proves cross-backend parity (RESEARCH Open Question 1).
2. An in-process test that builds BOTH backends and asserts byte-identical sorted
   ``(reached_ids, frontier)`` / ``match_nodes`` directly from each, so the two are compared
   to each other, not only to a literal.

Graphs (RESEARCH Open Question 1): diamond (which depth wins for the frontier), cycle
(termination + de-dup), and an over-bound chain (boundary frontier vs. empty full-closure
frontier). All ids are normalized to ``str`` and sorted before comparison — the port leaves
ordering to the core (BACK-04 §5).

DEF-02-01: a value-round-trip regression pins ladybug 0.17.1's brace/bracket-shaped-string
coercion. The in-memory oracle MUST round-trip such a value byte-identically; the ladybug
case is ``xfail`` because the driver coerces JSON-object-shaped strings (deferred to the
Phase 3 value-encoding contract). The regression stays visible, not masked.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

    from doxastica.ports import BackendPort

# A structural edge type the ladybug BeliefState schema ships (02-02). Parity graphs use
# DEPENDS_ON so both backends accept the same edges over the same rel table.
_DEPENDS_ON = "DEPENDS_ON"


def _node(backend: BackendPort, state_id: str, **props: Any) -> None:
    """
    Upsert a BeliefState node keyed by ``state_id`` (the PK), mirroring the id into props.

    ``state_id`` is the ladybug ``BeliefState`` PRIMARY KEY: it is set from the MERGE key
    (``node_id``) and cannot be re-SET as an ordinary property (ladybug raises). So the PK is
    NOT passed in the props dict for the ladybug backend. The in-memory oracle stores props
    verbatim and does not derive ``state_id`` from ``node_id``, so it gets ``state_id`` mirrored
    into props — giving both backends a ``state_id`` field in ``match_nodes`` rows for parity.
    """
    from doxastica.backends.memory import InMemoryBackend

    if isinstance(backend, InMemoryBackend):
        backend.upsert_node("BeliefState", state_id, {"state_id": state_id, **props})
    else:
        backend.upsert_node("BeliefState", state_id, dict(props))


def _reached_ids(reached: list[dict[str, Any]]) -> list[str]:
    """Normalize a ``reached`` row list to a sorted list of ``str`` state_ids (order-agnostic)."""
    return sorted(str(row["state_id"]) for row in reached)


def _frontier_ids(frontier: frozenset[Any]) -> list[str]:
    """Normalize a ``frontier`` frozenset to a sorted list of ``str`` ids (order-agnostic)."""
    return sorted(str(node_id) for node_id in frontier)


def _build_diamond(backend: BackendPort) -> None:
    """A→B, A→C, B→D, C→D — the diamond; D is reachable at depth 2 down two paths."""
    for nid in ("A", "B", "C", "D"):
        _node(backend, nid)
    backend.add_edge(_DEPENDS_ON, "A", "B")
    backend.add_edge(_DEPENDS_ON, "A", "C")
    backend.add_edge(_DEPENDS_ON, "B", "D")
    backend.add_edge(_DEPENDS_ON, "C", "D")


def _build_cycle(backend: BackendPort) -> None:
    """A→B→C→A — a 3-cycle; traverse must terminate and de-duplicate."""
    for nid in ("A", "B", "C"):
        _node(backend, nid)
    backend.add_edge(_DEPENDS_ON, "A", "B")
    backend.add_edge(_DEPENDS_ON, "B", "C")
    backend.add_edge(_DEPENDS_ON, "C", "A")


def _build_chain(backend: BackendPort) -> None:
    """A→B→C→D — a linear chain to exercise the over-bound (max_depth) frontier."""
    for nid in ("A", "B", "C", "D"):
        _node(backend, nid)
    backend.add_edge(_DEPENDS_ON, "A", "B")
    backend.add_edge(_DEPENDS_ON, "B", "C")
    backend.add_edge(_DEPENDS_ON, "C", "D")


# --------------------------------------------------------------------------------------------
# Parametrized-over-the-fixture parity: each backend's output must match the expected literal.
# --------------------------------------------------------------------------------------------


def test_diamond_full_closure_parity(backend: BackendPort) -> None:
    """Diamond, unbounded: both backends reach {B,C,D} with an empty frontier (D-05)."""
    _build_diamond(backend)
    reached, frontier = backend.traverse("A", frozenset({_DEPENDS_ON}), None)
    assert _reached_ids(reached) == ["B", "C", "D"], (
        f"diamond full closure must reach B,C,D; got {_reached_ids(reached)}"
    )
    assert _frontier_ids(frontier) == [], "unbounded traverse has an empty frontier"


def test_diamond_bounded_depth_one_parity(backend: BackendPort) -> None:
    """Diamond, max_depth=1: reach {B,C}; both B and C are on the frontier (D's parents)."""
    _build_diamond(backend)
    reached, frontier = backend.traverse("A", frozenset({_DEPENDS_ON}), 1)
    assert _reached_ids(reached) == ["B", "C"], (
        f"depth-1 diamond reaches only B,C; got {_reached_ids(reached)}"
    )
    assert _frontier_ids(frontier) == ["B", "C"], (
        f"B and C sit at the bound with unexpanded successor D; got {_frontier_ids(frontier)}"
    )


def test_diamond_d_depth_wins_parity(backend: BackendPort) -> None:
    """Diamond, max_depth=2: D is found at its MIN depth (2) on both — D not on frontier."""
    _build_diamond(backend)
    reached, frontier = backend.traverse("A", frozenset({_DEPENDS_ON}), 2)
    assert _reached_ids(reached) == ["B", "C", "D"], (
        f"depth-2 diamond reaches B,C,D; got {_reached_ids(reached)}"
    )
    # D has no successor, so even at the bound it is NOT on the frontier (both backends agree).
    assert _frontier_ids(frontier) == [], (
        f"D at the bound has no unexpanded successor; frontier empty; got {_frontier_ids(frontier)}"
    )


def test_cycle_terminates_and_dedupes_parity(backend: BackendPort) -> None:
    """Cycle A→B→C→A, unbounded: both reach the de-duplicated {B,C}; empty frontier (D-05)."""
    _build_cycle(backend)
    reached, frontier = backend.traverse("A", frozenset({_DEPENDS_ON}), None)
    assert _reached_ids(reached) == ["B", "C"], (
        f"cycle traverse returns the de-duped reachable set (no start); got {_reached_ids(reached)}"
    )
    assert _frontier_ids(frontier) == [], "unbounded traverse over a cycle has an empty frontier"


def test_over_bound_chain_frontier_parity(backend: BackendPort) -> None:
    """Chain A→B→C→D, max_depth=2: reach {B,C}; C is the boundary frontier on both (D-05)."""
    _build_chain(backend)
    reached, frontier = backend.traverse("A", frozenset({_DEPENDS_ON}), 2)
    assert _reached_ids(reached) == ["B", "C"], (
        f"over-bound chain reaches within the bound; got {_reached_ids(reached)}"
    )
    assert _frontier_ids(frontier) == ["C"], (
        f"C sits at exactly max_depth with unexpanded successor D; got {_frontier_ids(frontier)}"
    )


def test_chain_full_closure_empty_frontier_parity(backend: BackendPort) -> None:
    """Chain, max_depth=None: full closure {B,C,D} with an EMPTY frontier on both (D-05)."""
    _build_chain(backend)
    reached, frontier = backend.traverse("A", frozenset({_DEPENDS_ON}), None)
    assert _reached_ids(reached) == ["B", "C", "D"]
    assert _frontier_ids(frontier) == [], "full closure has an empty frontier on both backends"


def test_match_nodes_and_exact_parity(backend: BackendPort) -> None:
    """``match_nodes`` AND-exact results are identical across backends, sorted (D-05)."""
    _node(backend, "n1", status="active")
    _node(backend, "n2", status="active")
    _node(backend, "n3", status="retracted")
    all_ids = sorted(str(r["state_id"]) for r in backend.match_nodes("BeliefState", {}))
    assert all_ids == ["n1", "n2", "n3"], f"empty where returns all; got {all_ids}"
    active = sorted(
        str(r["state_id"]) for r in backend.match_nodes("BeliefState", {"status": "active"})
    )
    assert active == ["n1", "n2"], f"AND-exact status match; got {active}"


# --------------------------------------------------------------------------------------------
# In-process both-backends comparison: build BOTH and assert they agree with EACH OTHER.
# --------------------------------------------------------------------------------------------


def _both_backends() -> Iterator[tuple[str, BackendPort]]:
    """Yield memory + ladybug backends in-process (ladybug skipped if the driver is absent)."""
    from doxastica.backends.memory import InMemoryBackend

    yield "memory", InMemoryBackend()

    lb = pytest.importorskip("ladybug")
    from doxastica.backends.ladybug import LadybugBackend

    conn = lb.Connection(lb.Database())
    yield "ladybug", LadybugBackend(conn, namespace="dx", owns_conn=True)


def test_both_backends_diamond_byte_identical() -> None:
    """Build BOTH backends and assert byte-identical sorted (reached, frontier) on the diamond."""
    results: dict[str, tuple[list[str], list[str]]] = {}
    for name, be in _both_backends():
        _build_diamond(be)
        reached, frontier = be.traverse("A", frozenset({_DEPENDS_ON}), 1)
        results[name] = (_reached_ids(reached), _frontier_ids(frontier))
    assert results["memory"] == results["ladybug"], (
        f"diamond (reached, frontier) must be byte-identical across backends; got {results}"
    )


def test_both_backends_match_nodes_byte_identical() -> None:
    """Build BOTH backends and assert byte-identical match_nodes results on the same inserts."""
    results: dict[str, list[str]] = {}
    for name, be in _both_backends():
        _node(be, "n1", status="active")
        _node(be, "n2", status="retracted")
        results[name] = sorted(
            str(r["state_id"]) for r in be.match_nodes("BeliefState", {"status": "active"})
        )
    assert results["memory"] == results["ladybug"], (
        f"match_nodes must be byte-identical across backends; got {results}"
    )


# --------------------------------------------------------------------------------------------
# DEF-02-01 regression: JSON-object-shaped STRING value round-trip.
# --------------------------------------------------------------------------------------------


_SHAPED_VALUE = '{"x": 2}'  # a JSON-object-shaped STRING (the value-opacity hazard, DEF-02-01)


def _assert_value_round_trips(backend: BackendPort) -> None:
    """Store ``_SHAPED_VALUE`` as a node ``value`` and assert it round-trips byte-identically."""
    _node(backend, "n1", value=_SHAPED_VALUE)
    rows = backend.match_nodes("BeliefState", {"state_id": "n1"})
    assert len(rows) == 1, f"expected exactly one node; got {rows}"
    assert rows[0]["value"] == _SHAPED_VALUE, (
        f"value must round-trip byte-identically; got {rows[0]['value']!r}"
    )


def test_value_string_round_trips_memory() -> None:
    """The in-memory oracle round-trips a JSON-object-shaped STRING value verbatim (DEF-02-01)."""
    from doxastica.backends.memory import InMemoryBackend

    _assert_value_round_trips(InMemoryBackend())


@pytest.mark.xfail(
    reason="DEF-02-01: ladybug STRUCT/LIST coercion, deferred to Phase 3 value-encoding contract",
    strict=False,
)
def test_value_string_round_trips_ladybug() -> None:
    """
    Ladybug 0.17.1 coerces brace/bracket-shaped string params to STRUCT/LIST (DEF-02-01).

    Tracked, not masked: the regression is a visible ``xfail`` until the Phase 3 value-encoding
    contract resolves it. The in-memory oracle (the test above) MUST pass the same assertion.
    """
    lb = pytest.importorskip("ladybug")
    from doxastica.backends.ladybug import LadybugBackend

    be = LadybugBackend(lb.Connection(lb.Database()), namespace="dx", owns_conn=True)
    try:
        _assert_value_round_trips(be)
    finally:
        be.close()
