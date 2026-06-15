"""
LadybugDB reference-adapter tests — ownership, isolation, bootstrap, and SC4 confirmations.

House style copied from ``test_port_distinct.py`` / ``test_backend_memory.py``: small focused
functions, a docstring naming the requirement/decision ID, and direct ``assert``s with
actionable messages. The whole module is gated on ``pytest.importorskip("ladybug")`` so the
base-install CI job (ladybug ABSENT) skips it cleanly while the full job exercises it.

Task 1: ``test_ownership`` (CONN-01 / R19), ``test_namespace_isolation`` (CONN-02),
``test_namespace_rejects_unsafe`` (D-04 / T-02-01), ``test_bootstrap_idempotent`` (CONN-03).

Task 2 (SC4 confirmations): ``test_five_primitives`` (BACK-02),
``test_upsert_and_edge_idempotent``, ``test_traverse_cycle_safe`` (Pitfall 3),
``test_traverse_unbounded_empty_frontier`` (Pitfall 1), ``test_traverse_bounded_frontier``,
``test_unit_of_work_rollback`` (A2) — port unchanged, SC4 confirmed.
"""

import pytest

lb = pytest.importorskip("ladybug")

from doxastica.backends.ladybug import LadybugBackend  # noqa: E402  (after importorskip gate)


def test_ownership() -> None:
    """Injected connections survive ``close()``; self-managed ones are closed (CONN-01 / R19)."""
    # Injected (owns_conn=False): the backend must NOT close the tenant's connection.
    injected_db = lb.Database()
    injected_conn = lb.Connection(injected_db)
    injected_backend = LadybugBackend(injected_conn, namespace="dx", owns_conn=False)
    injected_backend.close()
    # Still usable after close() — proves the injected handle was left open (R19).
    injected_conn.execute("RETURN 1 AS one")

    # Self-managed (owns_conn=True via open()): the backend owns and closes its connection.
    owned_backend = LadybugBackend.open(":memory:", namespace="dx")
    owned_conn = owned_backend._conn  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    owned_backend.close()
    with pytest.raises(RuntimeError, match="closed"):
        owned_conn.execute("RETURN 1 AS one")


def test_namespace_isolation() -> None:
    """Two namespaces coexist in one DB with no cross-reads (CONN-02)."""
    db = lb.Database()
    conn_a = lb.Connection(db)
    conn_b = lb.Connection(db)
    backend_a = LadybugBackend(conn_a, namespace="a", owns_conn=False)
    backend_b = LadybugBackend(conn_b, namespace="b", owns_conn=False)

    # Write a node into each namespace's own BeliefState table.
    conn_a.execute("MERGE (n:a_BeliefState {state_id:$id})", parameters={"id": "in_a"})
    conn_b.execute("MERGE (n:b_BeliefState {state_id:$id})", parameters={"id": "in_b"})

    res_a = conn_a.execute("MATCH (n:a_BeliefState) RETURN n.state_id AS s")
    res_b = conn_b.execute("MATCH (n:b_BeliefState) RETURN n.state_id AS s")
    ids_a = [r["s"] for r in res_a.rows_as_dict().get_all()]
    ids_b = [r["s"] for r in res_b.rows_as_dict().get_all()]
    assert ids_a == ["in_a"], f"namespace 'a' must see only its own node; got {ids_a}"
    assert ids_b == ["in_b"], f"namespace 'b' must see only its own node; got {ids_b}"
    # The closed subgraphs do not bleed: namespace 'a' has no row written under 'b'.
    assert "in_b" not in ids_a, "namespaces must not cross-read"

    backend_a.close()
    backend_b.close()


@pytest.mark.parametrize("bad", ["has space", "with'quote", "with-hyphen", "1leading_digit", ""])
def test_namespace_rejects_unsafe(bad: str) -> None:
    """An unsafe namespace raises ValueError BEFORE any DDL runs (D-04 / T-02-01)."""
    conn = lb.Connection(lb.Database())
    with pytest.raises(ValueError, match="namespace must match"):
        LadybugBackend(conn, namespace=bad, owns_conn=False)


def test_bootstrap_idempotent() -> None:
    """Re-running bootstrap on a shared DB (same namespace) raises no error (CONN-03)."""
    db = lb.Database()
    conn = lb.Connection(db)
    first = LadybugBackend(conn, namespace="dx", owns_conn=False)
    # Constructing a second backend on the same DB + namespace re-runs CREATE ... IF NOT EXISTS.
    second = LadybugBackend(lb.Connection(db), namespace="dx", owns_conn=False)
    assert first is not second  # both constructed without error — the bootstrap is idempotent.


def _ids(rows: list[dict[str, object]]) -> list[str]:
    """Return the sorted ``state_id``s of a row list for order-independent assertions."""
    return sorted(str(r["state_id"]) for r in rows)


def test_five_primitives() -> None:
    """upsert, add_edge, match_nodes, traverse work end-to-end over LadybugDB (BACK-02)."""
    be = LadybugBackend.open(":memory:", namespace="dx")
    be.upsert_node("BeliefState", "s1", {"status": "active"})
    be.upsert_node("BeliefState", "s2", {"status": "active"})
    be.add_edge("DEPENDS_ON", "s1", "s2")

    matched = be.match_nodes("BeliefState", {"state_id": "s1"})
    assert _ids(matched) == ["s1"], f"match_nodes must find s1 by its primary id; got {matched}"
    assert matched[0]["status"] == "active", "match_nodes returns the stored props (D-04)"

    reached, _ = be.traverse("s1", frozenset({"DEPENDS_ON"}), None)
    assert _ids(reached) == ["s2"], f"traverse from s1 must reach s2; got {reached}"
    be.close()


def test_upsert_and_edge_idempotent() -> None:
    """Double upsert = 1 node; double add_edge = 1 edge (BACK-02; MERGE, not CREATE)."""
    be = LadybugBackend.open(":memory:", namespace="dx")
    be.upsert_node("BeliefState", "s1", {"status": "active"})
    be.upsert_node("BeliefState", "s1", {"status": "retracted"})  # re-upsert SET-updates props
    rows = be.match_nodes("BeliefState", {})
    assert _ids(rows) == ["s1"], f"double upsert must yield one node; got {rows}"
    assert rows[0]["status"] == "retracted", "re-upsert must SET-update props"

    be.upsert_node("BeliefState", "s2", {})
    be.add_edge("DEPENDS_ON", "s1", "s2")
    be.add_edge("DEPENDS_ON", "s1", "s2")  # idempotent
    reached, _ = be.traverse("s1", frozenset({"DEPENDS_ON"}), None)
    assert _ids(reached) == ["s2"], (
        f"double add_edge must not duplicate the successor; got {reached}"
    )
    be.close()


def test_traverse_cycle_safe() -> None:
    """A 3-node cycle terminates with the de-duplicated reachable set (SC4 / Pitfall 3)."""
    be = LadybugBackend.open(":memory:", namespace="dx")
    for nid in ("a", "b", "c"):
        be.upsert_node("BeliefState", nid, {})
    be.add_edge("DEPENDS_ON", "a", "b")
    be.add_edge("DEPENDS_ON", "b", "c")
    be.add_edge("DEPENDS_ON", "c", "a")  # closes the cycle
    reached, frontier = be.traverse("a", frozenset({"DEPENDS_ON"}), None)
    assert _ids(reached) == ["b", "c"], (
        f"ACYCLIC cycle traverse returns the reachable set without start; got {reached}"
    )
    assert frontier == frozenset(), "unbounded traverse has an empty frontier"
    be.close()


def test_traverse_unbounded_empty_frontier() -> None:
    """``max_depth=None`` returns the full closure with an EMPTY frontier (SC4 / Pitfall 1)."""
    be = LadybugBackend.open(":memory:", namespace="dx")
    for nid in ("a", "b", "c", "d"):
        be.upsert_node("BeliefState", nid, {})
    be.add_edge("DEPENDS_ON", "a", "b")
    be.add_edge("DEPENDS_ON", "b", "c")
    be.add_edge("DEPENDS_ON", "c", "d")
    reached, frontier = be.traverse("a", frozenset({"DEPENDS_ON"}), None)
    assert _ids(reached) == ["b", "c", "d"], (
        f"unbounded traverse must return the full closure (cap raised); got {reached}"
    )
    assert frontier == frozenset(), "unbounded traverse has an empty frontier"
    be.close()


def test_traverse_bounded_frontier() -> None:
    """A chain longer than ``max_depth`` yields the boundary frontier (SC4)."""
    be = LadybugBackend.open(":memory:", namespace="dx")
    for nid in ("a", "b", "c", "d"):
        be.upsert_node("BeliefState", nid, {})
    be.add_edge("DEPENDS_ON", "a", "b")
    be.add_edge("DEPENDS_ON", "b", "c")
    be.add_edge("DEPENDS_ON", "c", "d")
    reached, frontier = be.traverse("a", frozenset({"DEPENDS_ON"}), 2)
    assert _ids(reached) == ["b", "c"], (
        f"bounded traverse returns nodes within max_depth; got {reached}"
    )
    assert frontier == frozenset({"c"}), (
        f"frontier = node at exactly max_depth with an unexpanded successor; got {frontier}"
    )
    be.close()


def test_unit_of_work_rollback() -> None:
    """A write inside a ``unit_of_work`` that raises is discarded (A2 / BACK-02)."""
    be = LadybugBackend.open(":memory:", namespace="dx")
    be.upsert_node("BeliefState", "a", {})
    with pytest.raises(RuntimeError, match="boom"), be.unit_of_work():
        be.upsert_node("BeliefState", "b", {})
        be.add_edge("DEPENDS_ON", "a", "b")
        raise RuntimeError("boom")
    assert _ids(be.match_nodes("BeliefState", {})) == ["a"], (
        "writes inside a failed unit_of_work must be rolled back"
    )
    reached, _ = be.traverse("a", frozenset({"DEPENDS_ON"}), None)
    assert reached == [], "edges written in a failed unit_of_work must be rolled back"
    be.close()


def test_unit_of_work_persists_on_success() -> None:
    """A ``unit_of_work`` that completes normally commits its writes (BACK-02)."""
    be = LadybugBackend.open(":memory:", namespace="dx")
    with be.unit_of_work():
        be.upsert_node("BeliefState", "a", {})
    assert _ids(be.match_nodes("BeliefState", {})) == ["a"]
    be.close()
