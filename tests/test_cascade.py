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

import json
import uuid
from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from doxastica import MemoryCore
from doxastica.models import BeliefState, EdgeType, ImpactResult

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


# ============================================================================================
# get_impact mechanism + property tests (EDGE-02, D-01..D-05) — plan 05-03.
#
# get_impact(X) returns the transitive set of BeliefStates that DEPEND ON X (its downstream
# dependents, D-01), reached EXCLUDES X (D-02), over EXACTLY {DEPENDS_ON, DERIVED_FROM} (D-03 —
# SUPERSEDES excluded), via the direction="in" walk (D-04/D-05). The single most likely parity
# bug (RESEARCH Pitfall 1): ladybug `traverse` returns state_id-only rows while in-memory returns
# full props, so get_impact MUST re-fetch full props via match_nodes before hydrating — the
# full-hydration parity case below is the guard. The asymmetric dependents-only case is the
# direction guard (RESEARCH Pitfall 2 — a successor/predecessor swap).
# ============================================================================================


def _impact_ids(impact: ImpactResult) -> list[str]:
    """Normalize an ``ImpactResult.reached`` tuple to a sorted list of ``str`` state_ids."""
    return sorted(str(s.state_id) for s in impact.reached)


def _chain_of_dependents(core: MemoryCore, n: int) -> list[BeliefState]:
    """
    Build a DEPENDS_ON chain of ``n`` beliefs where each later state depends on the prior.

    Lays ``s[1] --DEPENDS_ON--> s[0]``, ``s[2] --DEPENDS_ON--> s[1]``, … so that the dependency
    arrows point BACKWARD (dependent → dependency). ``get_impact(s[0])`` therefore walks INTO
    ``s[0]`` (direction="in") and reaches every later state ``s[1..n-1]`` (its transitive
    dependents). Returns the list of states in chain order.
    """
    states = [core.revise("s", f"b{i}", i, uuid.uuid7()) for i in range(n)]
    for i in range(1, n):
        core.add_edge(states[i].state_id, states[i - 1].state_id, EdgeType.DEPENDS_ON)
    return states


def test_get_impact_dependents_only_parity() -> None:
    """B depends on A (A<-B): get_impact(A) == {B}; get_impact(B) == {} — on both backends."""
    results: dict[str, tuple[list[str], list[str]]] = {}
    for name, be in _both_backends():
        core = MemoryCore(be)
        a = core.revise("s", "ba", 1, uuid.uuid7())
        b = core.revise("s", "bb", 2, uuid.uuid7())
        core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)  # B --DEPENDS_ON--> A
        impact_a = core.get_impact(a.state_id)
        impact_b = core.get_impact(b.state_id)
        results[name] = (_impact_ids(impact_a), _impact_ids(impact_b))
        assert results[name] == ([str(b.state_id)], []), (
            f"[{name}] A's dependent is B; B has none; got {results[name]}"
        )
    assert results["memory"] == results["ladybug"], (
        f"both backends must agree on the dependents-only shape; got {results}"
    )


def test_get_impact_derived_from_included_parity(backend: BackendPort) -> None:
    """A positive DERIVED_FROM case: get_impact crosses DERIVED_FROM edges too (D-03 REQUIRED)."""
    core = MemoryCore(backend)
    a = core.revise("s", "ba", 1, uuid.uuid7())
    b = core.revise("s", "bb", 2, uuid.uuid7())
    core.add_edge(b.state_id, a.state_id, EdgeType.DERIVED_FROM)  # B --DERIVED_FROM--> A
    assert _impact_ids(core.get_impact(a.state_id)) == [str(b.state_id)], (
        "DERIVED_FROM is a cascade edge (D-03) — A's dependent B must be reached"
    )


def test_get_impact_excludes_start(backend: BackendPort) -> None:
    """Reached never contains the start node itself (D-02)."""
    core = MemoryCore(backend)
    states = _chain_of_dependents(core, 3)
    for s in states:
        impact = core.get_impact(s.state_id)
        assert s.state_id not in {r.state_id for r in impact.reached}, (
            f"get_impact({s.state_id}) must EXCLUDE the start node (D-02)"
        )


def test_get_impact_supersedes_excluded_parity(backend: BackendPort) -> None:
    """A SUPERSEDES-only revision spine contributes NOTHING to get_impact (D-03 — excluded)."""
    core = MemoryCore(backend)
    # lay a revision spine: three revisions of the same belief link via internal SUPERSEDES edges.
    s1 = core.revise("s", "spine", 1, uuid.uuid7())
    s2 = core.revise("s", "spine", 2, uuid.uuid7())
    s3 = core.revise("s", "spine", 3, uuid.uuid7())
    # the SUPERSEDES chain (s3 -> s2 -> s1) exists, but it is NOT a cascade edge: get_impact over
    # any spine node returns () — following SUPERSEDES would report a belief's own version history.
    for s in (s1, s2, s3):
        assert core.get_impact(s.state_id).reached == (), (
            f"SUPERSEDES is excluded from the cascade (D-03); get_impact({s.state_id}) must be ()"
        )


def test_get_impact_full_closure_parity() -> None:
    """depth=None ⇒ full closure {all later dependents}, empty frontier, truncated=False (D-02)."""
    results: dict[str, tuple[list[str], bool, list[str]]] = {}
    for name, be in _both_backends():
        core = MemoryCore(be)
        states = _chain_of_dependents(core, 4)  # s0 <- s1 <- s2 <- s3
        impact = core.get_impact(states[0].state_id)  # depth=None default
        results[name] = (
            _impact_ids(impact),
            impact.truncated,
            sorted(str(f) for f in impact.frontier),
        )
        expected = sorted(str(s.state_id) for s in states[1:])
        assert results[name] == (expected, False, []), (
            f"[{name}] full closure reaches s1..s3, empty frontier, truncated=False; "
            f"got {results[name]}"
        )
    assert results["memory"] == results["ladybug"], (
        f"both backends must agree on full-closure get_impact; got {results}"
    )


def test_get_impact_depth_bounded_frontier_parity() -> None:
    """depth=2 on s0<-s1<-s2<-s3: reach {s1,s2}; s2 on frontier; truncated=True (both backends)."""
    results: dict[str, tuple[list[str], bool, list[str]]] = {}
    for name, be in _both_backends():
        core = MemoryCore(be)
        states = _chain_of_dependents(core, 4)  # s0 <- s1 <- s2 <- s3
        impact = core.get_impact(states[0].state_id, 2)
        results[name] = (
            _impact_ids(impact),
            impact.truncated,
            sorted(str(f) for f in impact.frontier),
        )
        reached_expected = sorted(str(s.state_id) for s in states[1:3])  # s1, s2
        frontier_expected = [str(states[2].state_id)]  # s2 sits at the bound with s3 unexpanded
        assert results[name] == (reached_expected, True, frontier_expected), (
            f"[{name}] depth-2 reaches s1,s2; s2 frontier; truncated=True; got {results[name]}"
        )
    assert results["memory"] == results["ladybug"], (
        f"both backends must agree on the depth-bounded cut-off; got {results}"
    )


def test_get_impact_depth_zero_parity() -> None:
    """depth=0 ⇒ empty reached, start on the frontier, truncated=True (both backends)."""
    results: dict[str, tuple[list[str], bool, list[str]]] = {}
    for name, be in _both_backends():
        core = MemoryCore(be)
        states = _chain_of_dependents(core, 3)  # s0 <- s1 <- s2
        impact = core.get_impact(states[0].state_id, 0)
        results[name] = (
            _impact_ids(impact),
            impact.truncated,
            sorted(str(f) for f in impact.frontier),
        )
        assert results[name] == ([], True, [str(states[0].state_id)]), (
            f"[{name}] depth-0 reaches nothing; start is the frontier; truncated=True; "
            f"got {results[name]}"
        )
    assert results["memory"] == results["ladybug"], (
        f"both backends must agree on the depth-0 frontier; got {results}"
    )


@given(depth=st.one_of(st.none(), st.integers(min_value=0, max_value=10)))
def test_get_impact_terminates_on_cycle(depth: int | None) -> None:
    """Mutual dependency (A<-B and B<-A) ⇒ get_impact terminates and de-dupes (cycle-safe)."""
    core = MemoryCore.in_memory()
    a = core.revise("s", "a", 1, uuid.uuid7())
    b = core.revise("s", "b", 2, uuid.uuid7())
    core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)  # A <- B
    core.add_edge(a.state_id, b.state_id, EdgeType.DEPENDS_ON)  # B <- A (cycle)
    result = core.get_impact(a.state_id, depth)  # must terminate
    ids = [s.state_id for s in result.reached]
    assert a.state_id not in ids, "reached excludes the start (D-02) even through a cycle"
    assert len(ids) == len(set(ids)), "reached is de-duplicated even through a cycle"


@given(depth=st.integers(min_value=0, max_value=6))
def test_get_impact_exact_reachable_within_depth(depth: int) -> None:
    """On a linear dependency chain, reached is EXACTLY the dependents within ``depth`` hops."""
    core = MemoryCore.in_memory()
    states = _chain_of_dependents(core, 6)  # s0 <- s1 <- s2 <- s3 <- s4 <- s5
    impact = core.get_impact(states[0].state_id, depth)
    # within `depth` hops of s0 (walking INTO s0): s1..s[depth] (capped at the chain length).
    expected = {str(s.state_id) for s in states[1 : depth + 1]}
    assert {str(s.state_id) for s in impact.reached} == expected, (
        f"depth={depth} must reach exactly s1..s{depth}; got {_impact_ids(impact)}"
    )


def test_get_impact_full_hydration_parity() -> None:
    """Reached items are FULL BeliefStates (all six fields populated), identical across backends."""
    results: dict[str, list[tuple[str, str, str, str]]] = {}
    for name, be in _both_backends():
        core = MemoryCore(be)
        a = core.revise("scope-x", "ba", {"v": 1}, uuid.uuid7())
        b = core.revise("scope-x", "bb", {"v": 2}, uuid.uuid7())
        core.add_edge(b.state_id, a.state_id, EdgeType.DEPENDS_ON)
        impact = core.get_impact(a.state_id)
        assert len(impact.reached) == 1, f"[{name}] exactly one dependent expected"
        s: BeliefState = impact.reached[0]
        # the hydration gap guard: every field is populated (not just state_id), not empty.
        assert s.belief_id == "bb"
        assert s.scope_id == "scope-x"
        assert s.value == {"v": 2}
        assert s.status is b.status
        assert s.source_event_id == b.source_event_id
        # capture a backend-stable projection (state_id varies per backend mint, so drop it).
        results[name] = [
            (st_.belief_id, st_.scope_id, st_.status.value, json.dumps(st_.value, sort_keys=True))
            for st_ in impact.reached
        ]
    assert results["memory"] == results["ladybug"], (
        f"hydrated reached fields must be identical across backends; got {results}"
    )
