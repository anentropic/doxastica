"""
``MemoryCore.add_edge`` mechanism tests (EDGE-01, D-06/D-07) — both backends.

This file is the mechanism suite for the public edge-creation seam. It is a NEW file that
composes two existing idioms rather than re-scaffolding them:

- the parametrized ``backend`` fixture (``tests/conftest.py``) and the ``_both_backends`` /
  ``_reached_ids`` normalization idiom (``tests/test_backend_parity.py``), so every case runs
  on BOTH the in-memory oracle and the ladybug reference backend;
- ``MemoryCore.in_memory()`` (``core.py``) for zero-dependency construction.

Scope (this plan, 05-02): ``add_edge`` ONLY. ``get_impact`` lands in plan 05-03 and will EXTEND
this file. The AGM Relevance/Core-Retainment POSTULATE tests are Phase 7 — NOT here; these tests
pin the MECHANISM (idempotency, the closed-``EdgeType`` seam, and the D-07 silent-no-op).

D-06: ``add_edge`` is a near-passthrough to the backend's idempotent ``add_edge`` inside exactly
ONE ``unit_of_work``; the public signature takes the closed ``EdgeType`` enum (only the three
generic types are layable via the public seam). D-07: NO endpoint-existence validation — a
missing endpoint is a SILENT NO-OP (the port's MATCH...MERGE matches nothing); it is the INTENDED
mechanism, pinned here by ``test_add_edge_missing_endpoint_is_silent_no_op``, NOT a bug to fix.

Observation note (independent of plan 05-01's ``direction`` param): the primary observation of a
laid edge uses a ``direction="out"`` traverse FROM the dependent node (``traverse(b, {DEPENDS_ON},
None)`` reaches ``a``), which composes only on pre-existing outgoing-traversal behaviour. A
``direction="in"`` cross-check (``traverse(a, ..., direction="in")`` reaches ``b``) is included
too — plan 05-01 already landed the kwarg, so both assertions hold now.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import pytest

from doxastica import MemoryCore
from doxastica.models import EdgeType

if TYPE_CHECKING:
    from collections.abc import Iterator

    from doxastica.ports import BackendPort


def _both_backends() -> Iterator[tuple[str, BackendPort]]:
    """Yield memory + ladybug backends in-process (ladybug skipped if the driver is absent)."""
    from doxastica.backends.memory import InMemoryBackend

    yield "memory", InMemoryBackend()

    lb = pytest.importorskip("ladybug")
    from doxastica.backends.ladybug import LadybugBackend

    conn = lb.Connection(lb.Database())
    yield "ladybug", LadybugBackend(conn, namespace="dx", owns_conn=True)


def _reached_ids(reached: list[dict[str, Any]]) -> list[str]:
    """Normalize a ``reached`` row list to a sorted list of ``str`` state_ids (order-agnostic)."""
    return sorted(str(row["state_id"]) for row in reached)


def _two_beliefs(core: MemoryCore) -> tuple[Any, Any]:
    """Revise two real BeliefStates ``a`` (belief ``ba``) and ``b`` (belief ``bb``)."""
    a = core.revise("s", "ba", 1, uuid.uuid7())
    b = core.revise("s", "bb", 2, uuid.uuid7())
    return a, b


# --------------------------------------------------------------------------------------------
# Parametrized-over-the-fixture: each backend runs the case; agreement with the literal is
# already cross-backend parity (the fixture runs once per backend).
# --------------------------------------------------------------------------------------------


def test_add_edge_lays_typed_edge(backend: BackendPort) -> None:
    """``add_edge(b, a, DEPENDS_ON)`` lays an edge ``b --DEPENDS_ON--> a`` observable both ways."""
    core = MemoryCore(backend)
    a, b = _two_beliefs(core)
    core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)
    # direction-independent observation: outgoing traverse FROM the dependent b reaches a.
    out_reached, _ = backend.traverse(str(b.state_id), frozenset({EdgeType.DEPENDS_ON}), None)
    assert _reached_ids(out_reached) == [str(a.state_id)], (
        f"out-traverse from b must reach a; got {_reached_ids(out_reached)}"
    )
    # cross-check (plan 05-01 direction kwarg, already landed): in-traverse INTO a reaches b.
    in_reached, _ = backend.traverse(
        str(a.state_id), frozenset({EdgeType.DEPENDS_ON}), None, direction="in"
    )
    assert _reached_ids(in_reached) == [str(b.state_id)], (
        f"in-traverse into a must reach b (the dependent); got {_reached_ids(in_reached)}"
    )


def test_add_edge_is_idempotent(backend: BackendPort) -> None:
    """Double-add with identical args yields exactly one edge (no dup, no raise) — D-06."""
    core = MemoryCore(backend)
    a, b = _two_beliefs(core)
    core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)
    core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)  # must NOT raise, must NOT dup
    reached, _ = backend.traverse(str(b.state_id), frozenset({EdgeType.DEPENDS_ON}), None)
    assert _reached_ids(reached) == [str(a.state_id)], (
        f"a is reached exactly once after a double-add; got {_reached_ids(reached)}"
    )


@pytest.mark.parametrize(
    "edge_type", [EdgeType.SUPERSEDES, EdgeType.DEPENDS_ON, EdgeType.DERIVED_FROM]
)
def test_add_edge_each_generic_type(backend: BackendPort, edge_type: EdgeType) -> None:
    """Each of the three generic ``EdgeType`` members lays an observable edge (closed seam)."""
    core = MemoryCore(backend)
    a, b = _two_beliefs(core)
    core.add_edge(b.state_id, a.state_id, edge_type)
    reached, _ = backend.traverse(str(b.state_id), frozenset({edge_type}), None)
    assert _reached_ids(reached) == [str(a.state_id)], (
        f"{edge_type} edge b->a must be observable; got {_reached_ids(reached)}"
    )


def test_add_edge_missing_endpoint_is_silent_no_op(backend: BackendPort) -> None:
    """add_edge to a non-existent endpoint creates no edge and raises nothing (D-07 PIN)."""
    core = MemoryCore(backend)
    real = core.revise("s", "b", 1, uuid.uuid7())
    ghost = uuid.uuid7()  # never created
    core.add_edge(real.state_id, ghost, EdgeType.DEPENDS_ON)  # must NOT raise (D-07)
    # no usable edge was laid — out-traverse from real reaches nothing (the MERGE matched nothing).
    reached, _ = backend.traverse(str(real.state_id), frozenset({EdgeType.DEPENDS_ON}), None)
    assert _reached_ids(reached) == [], (
        f"a missing endpoint lays no usable edge (silent no-op); got {_reached_ids(reached)}"
    )


# --------------------------------------------------------------------------------------------
# In-process both-backends comparison: build BOTH and assert they agree with EACH OTHER.
# --------------------------------------------------------------------------------------------


def test_add_edge_idempotency_both_backends_agree() -> None:
    """
    Double-add yields the SAME edge STRUCTURE across both backends (one edge: b -> a).

    The two backends mint independent ``state_id`` UUID7s (the core mints them per construction),
    so the raw ids differ by design — this case compares the STRUCTURE the idempotent double-add
    produces, normalized to ``dependent reaches its single dependency``: exactly one reached node,
    and that node is the dependency ``a``. Both backends must agree on that shape.
    """
    results: dict[str, bool] = {}
    for name, be in _both_backends():
        core = MemoryCore(be)
        a, b = _two_beliefs(core)
        core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)
        core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)
        reached, _ = be.traverse(str(b.state_id), frozenset({EdgeType.DEPENDS_ON}), None)
        # normalize to the structural shape: b reaches exactly its dependency a (one edge).
        results[name] = _reached_ids(reached) == [str(a.state_id)] and len(reached) == 1
    assert results["memory"] and results["ladybug"], (
        f"both backends must lay exactly one idempotent edge b->a; got {results}"
    )
