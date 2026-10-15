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

import contextlib

import pytest

lb = pytest.importorskip("ladybug")

from doxastica.backends import ladybug as ladybug_backend  # noqa: E402  (after importorskip gate)
from doxastica.backends.ladybug import LadybugBackend  # noqa: E402

# Ladybug maps 8 TiB per database by default, and a test's caught exceptions can keep its
# database alive until the garbage collector runs: a few dozen of those exhaust a 47-bit address
# space ("Buffer manager exception: Mmap ... failed"). 1 GiB is ample for these tests.
_MAPPING = 2**30


def test_ownership() -> None:
    """Injected connections survive ``close()``; self-managed ones are closed (CONN-01 / R19)."""
    # Injected (owns_conn=False): the backend must NOT close the tenant's connection.
    injected_db = lb.Database(max_db_size=_MAPPING)
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
    db = lb.Database(max_db_size=_MAPPING)
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
    conn = lb.Connection(lb.Database(max_db_size=_MAPPING))
    with pytest.raises(ValueError, match="namespace must match"):
        LadybugBackend(conn, namespace=bad, owns_conn=False)


def test_bootstrap_idempotent() -> None:
    """Re-running bootstrap on a shared DB (same namespace) raises no error (CONN-03)."""
    db = lb.Database(max_db_size=_MAPPING)
    conn = lb.Connection(db)
    first = LadybugBackend(conn, namespace="dx", owns_conn=False)
    # Constructing a second backend on the same DB + namespace re-runs CREATE ... IF NOT EXISTS.
    second = LadybugBackend(lb.Connection(db), namespace="dx", owns_conn=False)
    assert first is not second  # both constructed without error — the bootstrap is idempotent.


def _memory() -> LadybugBackend:
    """A throwaway in-memory backend over a bounded mapping (see :data:`_MAPPING`)."""
    return LadybugBackend(
        lb.Connection(lb.Database(max_db_size=_MAPPING)), namespace="dx", owns_conn=True
    )


def _ids(rows: list[dict[str, object]]) -> list[str]:
    """Return the sorted ``state_id``s of a row list for order-independent assertions."""
    return sorted(str(r["state_id"]) for r in rows)


def test_five_primitives() -> None:
    """upsert, add_edge, match_nodes, traverse work end-to-end over LadybugDB (BACK-02)."""
    be = _memory()
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
    be = _memory()
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
    be = _memory()
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
    be = _memory()
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
    be = _memory()
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


def test_upsert_scope_and_belief_use_their_own_pk() -> None:
    """Scope/Belief upsert+match on their real PK columns, not a hardcoded state_id (CR-01)."""
    be = _memory()
    # Scope's PK is `scope_id`; Belief's is `belief_id`. Before CR-01 these MERGEd on a
    # non-existent `state_id` column and errored (or silently lost the PK uniqueness guarantee).
    be.upsert_node("Scope", "world", {"is_world": True})
    be.upsert_node("Scope", "world", {"is_world": True})  # idempotent on the real PK
    be.upsert_node("Belief", "b1", {})

    scopes = sorted(str(r["scope_id"]) for r in be.match_nodes("Scope", {}))
    assert scopes == ["world"], f"double Scope upsert must yield one node on scope_id; got {scopes}"
    beliefs = sorted(str(r["belief_id"]) for r in be.match_nodes("Belief", {}))
    assert beliefs == ["b1"], f"Belief upsert keys on belief_id; got {beliefs}"
    be.close()


def test_upsert_tolerates_pk_in_props() -> None:
    """Passing the PK inside props is safe — it is the merge key, never re-SET (WR-01)."""
    be = _memory()
    # Before WR-01 this raised: `SET n.state_id = $p0` re-SETs the merge key. Now the PK is
    # excluded from the SET loop, so the call (and a re-upsert) succeed.
    be.upsert_node("BeliefState", "s1", {"state_id": "s1", "status": "active"})
    be.upsert_node("BeliefState", "s1", {"state_id": "s1", "status": "retracted"})
    rows = be.match_nodes("BeliefState", {})
    assert _ids(rows) == ["s1"], f"PK-in-props re-upsert must stay one node; got {rows}"
    assert rows[0]["status"] == "retracted", "non-PK props still SET-update on re-upsert"
    be.close()


def test_traverse_max_depth_zero() -> None:
    """max_depth=0 reaches nothing; start is the frontier iff it has an out-edge (WR-02)."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    be.upsert_node("BeliefState", "b", {})
    be.add_edge("DEPENDS_ON", "a", "b")
    reached, frontier = be.traverse("a", frozenset({"DEPENDS_ON"}), 0)
    assert reached == [], f"max_depth=0 reaches nothing; got {reached}"
    assert frontier == frozenset({"a"}), (
        f"start sits at the bound with unexpanded successor b; got {frontier}"
    )

    # A node with no out-edge is NOT on the max_depth=0 frontier.
    reached2, frontier2 = be.traverse("b", frozenset({"DEPENDS_ON"}), 0)
    assert reached2 == [] and frontier2 == frozenset(), (
        f"a node with no out-edge has empty reached+frontier at max_depth=0; "
        f"got {reached2}, {frontier2}"
    )
    be.close()


def test_traverse_negative_depth_raises_valueerror() -> None:
    """A negative max_depth raises ValueError (WR-03: a real raise survives python -O)."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    with pytest.raises(ValueError, match="max_depth must be non-negative"):
        be.traverse("a", frozenset({"DEPENDS_ON"}), -1)
    be.close()


def test_unit_of_work_rollback() -> None:
    """A write inside a ``unit_of_work`` that raises is discarded (A2 / BACK-02)."""
    be = _memory()
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


@pytest.mark.parametrize(
    ("statement", "failure"),
    [
        ("CREATE (n:dx_BeliefState {state_id:'a'})", "duplicated primary key"),
        ("RETURN 1/0", "Divide by zero"),
    ],
)
def test_unit_of_work_reports_the_failure_not_the_rollback(statement: str, failure: str) -> None:
    """A statement Ladybug fails at run time is the error raised, not the ROLLBACK after it."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    with pytest.raises(RuntimeError, match=failure) as raised, be.unit_of_work():
        be.upsert_node("BeliefState", "b", {})
        be._exec(statement)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    # Ladybug already rolled it back: nothing to add, and nothing written.
    assert not getattr(raised.value, "__notes__", [])
    assert _ids(be.match_nodes("BeliefState", {})) == ["a"]
    with be.unit_of_work():
        be.upsert_node("BeliefState", "c", {})
    assert _ids(be.match_nodes("BeliefState", {})) == ["a", "c"]
    be.close()


def test_unit_of_work_notes_writes_after_a_failure_it_caught() -> None:
    """A block that catches a failed statement and goes on is told its unit wasn't undone."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="duplicated primary key"):
            be._exec("CREATE (n:dx_BeliefState {state_id:'a'})")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        # Ladybug ended the transaction: this write commits on its own.
        be.upsert_node("BeliefState", "c", {})
        raise RuntimeError("boom")
    assert any("not undone" in note for note in raised.value.__notes__)
    assert _ids(be.match_nodes("BeliefState", {})) == ["a", "c"]
    be.close()


def test_unit_of_work_notes_writes_before_a_second_failure() -> None:
    """The note follows the first failure that may have ended the transaction, not the last."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    with pytest.raises(RuntimeError, match="Divide by zero") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="duplicated primary key"):
            be._exec("CREATE (n:dx_BeliefState {state_id:'a'})")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        be.upsert_node("BeliefState", "c", {})
        be._exec("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    assert any("not undone" in note for note in raised.value.__notes__)
    assert _ids(be.match_nodes("BeliefState", {})) == ["a", "c"]
    be.close()


@pytest.mark.parametrize("cause", ["from", "context", "none"])
def test_unit_of_work_reports_a_wrapped_failure_silently(cause: str) -> None:
    """However the block wraps the failure, nothing ran after it, so nothing is noted."""
    be = _memory()
    with pytest.raises(LookupError) as raised, be.unit_of_work():
        try:
            be._exec("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        except RuntimeError as failure:
            if cause == "from":
                raise LookupError("wrapped") from failure
            if cause == "none":
                raise LookupError("wrapped") from None
            raise LookupError("wrapped")  # noqa: B904
    assert not getattr(raised.value, "__notes__", [])
    be.close()


def test_unit_of_work_counts_no_reads_after_a_failure_it_caught() -> None:
    """Reads after the failure, a deep walk's cap lift and restore among them, write nothing."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="Divide by zero"):
            be._exec("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        be.match_nodes("BeliefState", {})
        be.traverse("a", frozenset({"DEPENDS_ON"}), None)  # lifts the cap past the default
        raise RuntimeError("boom")
    assert not getattr(raised.value, "__notes__", [])
    be.close()


def test_unit_of_work_that_finishes_after_a_caught_failure_says_why_commit_fails() -> None:
    """Ladybug's COMMIT error carries the failure that ended the unit and what came after."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    with (
        pytest.raises(RuntimeError, match="No active transaction for COMMIT") as raised,
        be.unit_of_work(),
    ):
        with pytest.raises(RuntimeError, match="duplicated primary key"):
            be._exec("CREATE (n:dx_BeliefState {state_id:'a'})")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        be.upsert_node("BeliefState", "c", {})
    assert any(
        "duplicated primary key" in note and "1 write(s)" in note for note in raised.value.__notes__
    )
    be.close()


def test_unit_of_work_that_finishes_after_a_caught_failure_says_nothing_came_after() -> None:
    """With nothing written after the failure, the COMMIT error's note says so."""
    be = _memory()
    with (
        pytest.raises(RuntimeError, match="No active transaction for COMMIT") as raised,
        be.unit_of_work(),
    ):
        be.upsert_node("BeliefState", "a", {})
        with pytest.raises(RuntimeError, match="Divide by zero"):
            be._exec("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    assert any(
        "Divide by zero" in note and "nothing was written after it" in note
        for note in raised.value.__notes__
    )
    assert _ids(be.match_nodes("BeliefState", {})) == []
    be.close()


def test_unit_of_work_counts_writes_through_every_backend_on_its_connection() -> None:
    """Tenants share the connection, so a write through another one is counted too (R19)."""
    db = lb.Database(max_db_size=_MAPPING)
    conn = lb.Connection(db)
    a = LadybugBackend(conn, namespace="a", owns_conn=False)
    b = LadybugBackend(conn, namespace="b", owns_conn=False)
    with pytest.raises(RuntimeError, match="boom") as raised, a.unit_of_work():
        with pytest.raises(RuntimeError, match="Divide by zero"):
            a._exec("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        b.upsert_node("BeliefState", "c", {})
        raise RuntimeError("boom")
    assert any("not undone" in note for note in raised.value.__notes__)
    assert _ids(b.match_nodes("BeliefState", {})) == ["c"]


def test_unit_of_work_notes_a_failure_on_the_bare_connection() -> None:
    """A statement failed outside any backend still shows the unit wasn't undone."""
    be = _memory()
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="Divide by zero"):
            be._conn.execute("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        be.upsert_node("BeliefState", "c", {})
        raise RuntimeError("boom")
    assert any("already ended" in note and "1 write(s)" in note for note in raised.value.__notes__)
    assert _ids(be.match_nodes("BeliefState", {})) == ["c"]
    be.close()


def test_unit_of_work_passes_a_failure_on_the_bare_connection_with_no_writes_silently() -> None:
    """With nothing written, nothing can have escaped the unit, whenever the failure came."""
    be = _memory()
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="Divide by zero"):
            be._conn.execute("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        be.match_nodes("BeliefState", {})
        raise RuntimeError("boom")
    assert not getattr(raised.value, "__notes__", [])
    be.close()


@pytest.mark.parametrize(("write", "note"), [(True, "1 write(s)"), (False, "it wrote nothing")])
def test_unit_of_work_that_finishes_after_a_failure_on_the_bare_connection_says_why(
    write: bool,
    note: str,
) -> None:
    """Ladybug's COMMIT error says the transaction ended at a failure no backend saw."""
    be = _memory()
    with (
        pytest.raises(RuntimeError, match="No active transaction for COMMIT") as raised,
        be.unit_of_work(),
    ):
        with pytest.raises(RuntimeError, match="Divide by zero"):
            be._conn.execute("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        if write:
            be.upsert_node("BeliefState", "c", {})
    assert any("already ended" in text and note in text for text in raised.value.__notes__)
    be.close()


def test_unit_of_work_keeps_a_transaction_a_parameter_it_cant_bind_left_open() -> None:
    """A parameter Ladybug can't bind leaves the transaction open: what follows rolls back."""
    be = _memory()
    with pytest.raises(RuntimeError, match="Divide by zero") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="Unknown parameter type"):
            be._exec(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                "CREATE (n:dx_BeliefState {state_id:$x})", {"x": object()}
            )
        be.upsert_node("BeliefState", "c", {})
        be._exec("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    assert not getattr(raised.value, "__notes__", [])
    assert _ids(be.match_nodes("BeliefState", {})) == []
    be.close()


def test_unit_of_work_counts_what_a_unit_inside_it_wrote() -> None:
    """A unit opened once the outer transaction is gone commits on its own: it is counted."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="duplicated primary key"):
            be._exec("CREATE (n:dx_BeliefState {state_id:'a'})")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        with be.unit_of_work():
            be.upsert_node("BeliefState", "c", {})
        be.upsert_node("BeliefState", "d", {})
        raise RuntimeError("boom")
    assert any("2 write(s)" in note for note in raised.value.__notes__)
    assert _ids(be.match_nodes("BeliefState", {})) == ["a", "c", "d"]
    be.close()


def test_unit_of_work_counts_nothing_a_unit_inside_it_rolled_back() -> None:
    """Neither the inner unit's BEGIN nor its rolled-back write is a write of the outer one."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="duplicated primary key"):
            be._exec("CREATE (n:dx_BeliefState {state_id:'a'})")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        with pytest.raises(LookupError), be.unit_of_work():
            be.upsert_node("BeliefState", "c", {})
            raise LookupError("inner")
        raise RuntimeError("boom")
    assert not getattr(raised.value, "__notes__", [])
    assert _ids(be.match_nodes("BeliefState", {})) == ["a"]
    be.close()


def test_unit_of_work_counts_only_what_a_failed_unit_inside_it_kept() -> None:
    """A failure in the nested unit rolled back its writes before it; those after are kept."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="duplicated primary key"):
            be._exec("CREATE (n:dx_BeliefState {state_id:'a'})")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        with pytest.raises(LookupError), be.unit_of_work():
            be.upsert_node("BeliefState", "c", {})
            with pytest.raises(RuntimeError, match="Divide by zero"):
                be._exec("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            be.upsert_node("BeliefState", "d", {})
            raise LookupError("inner")
        raise RuntimeError("boom")
    assert any("the 1 write(s)" in note for note in raised.value.__notes__)
    assert _ids(be.match_nodes("BeliefState", {})) == ["a", "d"]
    be.close()


def test_unit_of_work_counts_a_unit_inside_it_that_failed_unseen() -> None:
    """A nested unit whose transaction a bare-connection failure ended may have kept it all."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="duplicated primary key"):
            be._exec("CREATE (n:dx_BeliefState {state_id:'a'})")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        with pytest.raises(LookupError), be.unit_of_work():
            be.upsert_node("BeliefState", "c", {})
            with pytest.raises(RuntimeError, match="Divide by zero"):
                be._conn.execute("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            raise LookupError("inner")
        raise RuntimeError("boom")
    assert any("the 1 write(s)" in note for note in raised.value.__notes__)
    be.close()


def test_unit_of_work_counts_all_of_a_unit_inside_it_that_committed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A nested unit that commits after a failure kept everything: the failure didn't end it."""
    # Stands in for a failure not yet known to leave the transaction open.
    monkeypatch.setattr(ladybug_backend, "_KEEPS_TRANSACTION", ("Parser exception",))
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="duplicated primary key"):
            be._exec("CREATE (n:dx_BeliefState {state_id:'a'})")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        with be.unit_of_work():
            be.upsert_node("BeliefState", "c", {})
            with pytest.raises(RuntimeError, match="Unknown parameter type"):
                be._exec(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                    "CREATE (n:dx_BeliefState {state_id:$x})", {"x": object()}
                )
            be.upsert_node("BeliefState", "d", {})
        raise RuntimeError("boom")
    assert any("the 2 write(s)" in note for note in raised.value.__notes__)
    assert _ids(be.match_nodes("BeliefState", {})) == ["a", "c", "d"]
    be.close()


def test_unit_of_work_exited_out_of_order_leaves_no_unit_open() -> None:
    """A unit that exits before one nested in it isn't put back when the nested one exits."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    outer, inner = be.unit_of_work(), be.unit_of_work()
    outer.__enter__()
    with pytest.raises(RuntimeError, match="duplicated primary key"):
        be._exec("CREATE (n:dx_BeliefState {state_id:'a'})")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    inner.__enter__()
    with contextlib.suppress(RuntimeError):
        outer.__exit__(None, None, None)
    with contextlib.suppress(RuntimeError):
        inner.__exit__(None, None, None)
    assert be._conn not in ladybug_backend._UNITS  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    be.close()


def test_unit_of_work_counts_what_a_unit_exited_out_of_order_kept() -> None:
    """A unit that exits before one nested in it still counts its writes in its outer unit."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    duplicate = "CREATE (n:dx_BeliefState {state_id:'a'})"
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="duplicated primary key"):
            be._exec(duplicate)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        middle, inner = be.unit_of_work(), be.unit_of_work()
        middle.__enter__()
        with pytest.raises(RuntimeError, match="duplicated primary key"):
            be._exec(duplicate)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        be.upsert_node("BeliefState", "c", {})
        inner.__enter__()
        with contextlib.suppress(RuntimeError):
            middle.__exit__(None, None, None)
        with contextlib.suppress(RuntimeError):
            inner.__exit__(None, None, None)
        raise RuntimeError("boom")
    assert any("write(s)" in note for note in raised.value.__notes__)
    be.close()


def test_unit_of_work_counts_no_schema_as_writes() -> None:
    """A tenant set up on the connection mid-unit creates tables, not data: nothing is noted."""
    db = lb.Database(max_db_size=_MAPPING)
    conn = lb.Connection(db)
    be = LadybugBackend(conn, namespace="a", owns_conn=False)
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="Divide by zero"):
            be._exec("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        LadybugBackend(conn, namespace="b", owns_conn=False)
        raise RuntimeError("boom")
    assert not getattr(raised.value, "__notes__", [])


def test_unit_of_work_keeps_a_transaction_a_parameter_it_cant_convert_left_open() -> None:
    """An int past int64 fails in the binding, before Ladybug: what follows rolls back."""
    be = _memory()
    with pytest.raises(RuntimeError, match="Divide by zero") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="Unable to cast Python instance"):
            be._exec(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                "CREATE (n:dx_BeliefState {state_id:$x})", {"x": 2**70}
            )
        be.upsert_node("BeliefState", "c", {})
        be._exec("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    assert not getattr(raised.value, "__notes__", [])
    assert _ids(be.match_nodes("BeliefState", {})) == []
    be.close()


def test_unit_of_work_counts_nothing_kept_by_a_unit_inside_it_whose_commit_failed() -> None:
    """A COMMIT that fails for its own reason found its transaction: nothing ran outside it."""
    be = _memory()
    be.upsert_node("BeliefState", "a", {})
    outer = be.unit_of_work()
    outer.__enter__()
    with pytest.raises(RuntimeError, match="duplicated primary key"):
        be._exec("CREATE (n:dx_BeliefState {state_id:'a'})")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    unit = ladybug_backend._UNITS[be._conn]  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(RuntimeError), be.unit_of_work():
        be.upsert_node("BeliefState", "c", {})
        be._conn.close()  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    assert unit.writes_after == 0
    with contextlib.suppress(RuntimeError):
        outer.__exit__(None, None, None)


def test_unit_of_work_notes_a_commit_failure_only_when_the_transaction_is_gone() -> None:
    """A COMMIT that fails for its own reason isn't blamed on an earlier failure."""
    be = _memory()
    with pytest.raises(RuntimeError) as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="Divide by zero"):
            be._exec("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        be._conn.close()  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    assert "No active transaction" not in str(raised.value)
    assert not getattr(raised.value, "__notes__", [])


def test_unit_of_work_keeps_a_transaction_a_syntax_error_left_open() -> None:
    """A statement that doesn't parse leaves the transaction open: what follows rolls back."""
    be = _memory()
    with pytest.raises(RuntimeError, match="Divide by zero") as raised, be.unit_of_work():
        with pytest.raises(RuntimeError, match="Parser exception"):
            be._exec("NOT CYPHER")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        be.upsert_node("BeliefState", "c", {})
        be._exec("RETURN 1/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    assert not getattr(raised.value, "__notes__", [])
    assert _ids(be.match_nodes("BeliefState", {})) == []
    be.close()


def test_unit_of_work_notes_a_rollback_that_fails() -> None:
    """A ROLLBACK that fails for another reason is noted on the block's error, not raised."""
    be = _memory()
    with pytest.raises(RuntimeError, match="boom") as raised, be.unit_of_work():
        be._conn.close()  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        raise RuntimeError("boom")
    assert any("ROLLBACK after it failed too" in note for note in raised.value.__notes__)


def test_unit_of_work_persists_on_success() -> None:
    """A ``unit_of_work`` that completes normally commits its writes (BACK-02)."""
    be = _memory()
    with be.unit_of_work():
        be.upsert_node("BeliefState", "a", {})
    assert _ids(be.match_nodes("BeliefState", {})) == ["a"]
    be.close()
