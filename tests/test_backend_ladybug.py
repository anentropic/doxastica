"""
LadybugDB reference-adapter tests — ownership, isolation, bootstrap, and SC4 confirmations.

House style copied from ``test_port_distinct.py`` / ``test_backend_memory.py``: small focused
functions, a docstring naming the requirement/decision ID, and direct ``assert``s with
actionable messages. The whole module is gated on ``pytest.importorskip("ladybug")`` so the
base-install CI job (ladybug ABSENT) skips it cleanly while the full job exercises it.

Task 1 (this commit): ``test_ownership`` (CONN-01 / R19), ``test_namespace_isolation``
(CONN-02), ``test_namespace_rejects_unsafe`` (D-04 / T-02-01), ``test_bootstrap_idempotent``
(CONN-03). The five-primitive + traverse SC4 confirmations are added in Task 2.
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
