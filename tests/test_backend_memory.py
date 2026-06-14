"""
Standalone exercise of the five ``InMemoryBackend`` primitives (BACK-03 / D-05).

Small, focused functions in the ``test_port_distinct.py`` house style: a docstring naming
the behaviour/decision and direct ``assert``s with actionable messages. These prove the
in-memory oracle satisfies the ``BackendPort`` contract — idempotent ``upsert_node`` /
``add_edge``, AND-exact ``match_nodes``, cycle-safe ``traverse`` with the
``(reached, frontier)`` shape (empty frontier when unbounded, boundary frontier when
bounded), and snapshot/restore ``unit_of_work`` rollback. Also pins
``BackendDependencyError``'s dual-catch base (D-02).
"""

import pytest

from doxastica.backends.memory import InMemoryBackend
from doxastica.errors import BackendDependencyError, DoxasticaError


def _value(props: dict[str, object]) -> object:
    """Pull the stable ``id`` field used to identify a returned node row in assertions."""
    return props["id"]


def test_upsert_node_is_idempotent() -> None:
    """Re-upserting the same ``node_id`` yields one node; props SET-update (BACK-03)."""
    be = InMemoryBackend()
    be.upsert_node("Belief", "n1", {"id": "n1", "v": 1})
    be.upsert_node("Belief", "n1", {"id": "n1", "v": 2})
    rows = be.match_nodes("Belief", {})
    assert len(rows) == 1, f"expected one node after double upsert; got {rows}"
    assert rows[0]["v"] == 2, "re-upsert must SET-update props"


def test_add_edge_is_idempotent() -> None:
    """Adding the same (edge_type, from, to) twice yields one edge (BACK-03)."""
    be = InMemoryBackend()
    be.upsert_node("Belief", "a", {"id": "a"})
    be.upsert_node("Belief", "b", {"id": "b"})
    be.add_edge("DEPENDS_ON", "a", "b")
    be.add_edge("DEPENDS_ON", "a", "b")
    reached, _ = be.traverse("a", frozenset({"DEPENDS_ON"}), None)
    assert [_value(r) for r in reached] == ["b"], (
        f"double add_edge must not duplicate the successor; got {reached}"
    )


def test_match_nodes_and_exact_match() -> None:
    """``match_nodes`` AND-exact-matches the where map; empty where returns all (BACK-03)."""
    be = InMemoryBackend()
    be.upsert_node("Belief", "a", {"id": "a", "k": "x", "j": 1})
    be.upsert_node("Belief", "b", {"id": "b", "k": "x", "j": 2})
    be.upsert_node("Belief", "c", {"id": "c", "k": "y", "j": 1})
    assert len(be.match_nodes("Belief", {})) == 3, "empty where returns all of the label"
    matched = be.match_nodes("Belief", {"k": "x", "j": 1})
    assert [_value(r) for r in matched] == ["a"], f"AND-match must be exact; got {matched}"


def test_match_nodes_label_scoped() -> None:
    """``match_nodes`` returns only nodes of the requested label (BACK-03)."""
    be = InMemoryBackend()
    be.upsert_node("Belief", "a", {"id": "a"})
    be.upsert_node("Scope", "s", {"id": "s"})
    assert [_value(r) for r in be.match_nodes("Scope", {})] == ["s"]


def test_traverse_is_cycle_safe() -> None:
    """``traverse`` terminates on a 3-node cycle, de-duplicating the reachable set (D-05)."""
    be = InMemoryBackend()
    for nid in ("a", "b", "c"):
        be.upsert_node("Belief", nid, {"id": nid})
    be.add_edge("DEPENDS_ON", "a", "b")
    be.add_edge("DEPENDS_ON", "b", "c")
    be.add_edge("DEPENDS_ON", "c", "a")  # closes the cycle
    reached, frontier = be.traverse("a", frozenset({"DEPENDS_ON"}), None)
    assert sorted(_value(r) for r in reached) == ["b", "c"], (
        f"cycle traverse returns the de-duplicated reachable set (no start); got {reached}"
    )
    assert frontier == frozenset(), "unbounded traverse has an empty frontier"


def test_traverse_unbounded_empty_frontier() -> None:
    """``max_depth=None`` returns the full closure with an EMPTY frontier (D-05)."""
    be = InMemoryBackend()
    for nid in ("a", "b", "c", "d"):
        be.upsert_node("Belief", nid, {"id": nid})
    be.add_edge("DEPENDS_ON", "a", "b")
    be.add_edge("DEPENDS_ON", "b", "c")
    be.add_edge("DEPENDS_ON", "c", "d")
    reached, frontier = be.traverse("a", frozenset({"DEPENDS_ON"}), None)
    assert sorted(_value(r) for r in reached) == ["b", "c", "d"]
    assert frontier == frozenset(), "unbounded traverse has an empty frontier"


def test_traverse_bounded_frontier() -> None:
    """Finite ``max_depth`` returns nodes within depth + the boundary frontier (D-05)."""
    be = InMemoryBackend()
    for nid in ("a", "b", "c", "d"):
        be.upsert_node("Belief", nid, {"id": nid})
    be.add_edge("DEPENDS_ON", "a", "b")
    be.add_edge("DEPENDS_ON", "b", "c")
    be.add_edge("DEPENDS_ON", "c", "d")
    reached, frontier = be.traverse("a", frozenset({"DEPENDS_ON"}), 2)
    assert sorted(_value(r) for r in reached) == ["b", "c"], (
        f"bounded traverse returns nodes within max_depth; got {reached}"
    )
    assert frontier == frozenset({"c"}), (
        f"frontier = node at exactly max_depth with an unexpanded successor; got {frontier}"
    )


def test_traverse_follows_only_named_edge_types() -> None:
    """``traverse`` follows only the requested ``edge_types`` (D-05)."""
    be = InMemoryBackend()
    for nid in ("a", "b", "c"):
        be.upsert_node("Belief", nid, {"id": nid})
    be.add_edge("DEPENDS_ON", "a", "b")
    be.add_edge("SUPERSEDES", "a", "c")
    reached, _ = be.traverse("a", frozenset({"DEPENDS_ON"}), None)
    assert [_value(r) for r in reached] == ["b"], (
        f"only DEPENDS_ON should be followed; got {reached}"
    )


def test_unit_of_work_rolls_back_on_error() -> None:
    """``unit_of_work`` restores the snapshot when the block raises (BACK-03)."""
    be = InMemoryBackend()
    be.upsert_node("Belief", "a", {"id": "a"})
    with pytest.raises(RuntimeError), be.unit_of_work():
        be.upsert_node("Belief", "b", {"id": "b"})
        be.add_edge("DEPENDS_ON", "a", "b")
        raise RuntimeError("boom")
    assert [_value(r) for r in be.match_nodes("Belief", {})] == ["a"], (
        "writes inside a failed unit_of_work must be rolled back"
    )
    reached, _ = be.traverse("a", frozenset({"DEPENDS_ON"}), None)
    assert reached == [], "edges written in a failed unit_of_work must be rolled back"


def test_unit_of_work_persists_on_success() -> None:
    """``unit_of_work`` keeps writes when the block completes normally (BACK-03)."""
    be = InMemoryBackend()
    with be.unit_of_work():
        be.upsert_node("Belief", "a", {"id": "a"})
    assert [_value(r) for r in be.match_nodes("Belief", {})] == ["a"]


def test_backend_dependency_error_dual_catch() -> None:
    """``BackendDependencyError`` is both a ``DoxasticaError`` and an ``ImportError`` (D-02)."""
    err = BackendDependencyError("missing driver")
    assert isinstance(err, DoxasticaError)
    assert isinstance(err, ImportError)
