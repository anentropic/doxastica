"""
The Wave-0 behavior scaffold for the Phase-4 retrieval/observation surface (the Nyquist target).

One named test per HIST-01 + CHAIN-04 row from ``04-VALIDATION.md``'s Per-Task Verification Map,
written against the LOCKED public surface only (``MemoryCore.query_scope`` + the closed
``BeliefFilter`` + the already-shipped ``get_revision_chain``). It is meaningful RED *before* plan
04-02 fills the ``query_scope`` body and GREEN *after*.

Two load-bearing conventions, both inherited verbatim from ``tests/test_revision_spine.py``:

1. **Parametrized over the ``backend`` fixture** (``conftest.py`` ``params=["memory", "ladybug"]``):
   every test takes ``backend: BackendPort`` and runs once per backend, so each behavior is proven
   on BOTH the in-memory oracle and the ladybug reference adapter (D-05 / D-07 parity). The ladybug
   param is skipped — not failed — when the optional driver is absent.
2. **Construct ``MemoryCore(backend)`` from the INJECTED fixture port** — NOT the zero-dependency
   in-memory factory classmethod — so the ladybug backend is exercised at all.

The closed ``BeliefFilter`` is the ONLY filter argument anywhere in this file (DATA-02 — no free
query string). The two *superseded* cells of the four-cell matrix (D-04/D-05) are reached SOLELY
through ``get_revision_chain`` (non-tail entries) + ``SUPERSEDES`` edges — never by asking
``query_scope`` for them: ``query_scope`` only ever returns *current* tails.

RED-until-04-02 is the correct, intended state: ``MemoryCore.query_scope`` has no body yet. Do NOT
weaken these tests to make them pass and do NOT implement the body here — that is plan 04-02.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, cast

from doxastica import BeliefFilter, BeliefStore, MemoryCore, Status

if TYPE_CHECKING:
    from doxastica.models import BeliefState
    from doxastica.ports import BackendPort


def _event_id() -> uuid.UUID:
    """Mint a fresh caller-side ``source_event_id`` (UUID7, time-ordered, RFC 9562 section 5.7)."""
    return uuid.uuid7()


def _core(backend: BackendPort) -> BeliefStore:
    """
    Build a ``MemoryCore`` over the injected fixture port, typed as the public ``BeliefStore``.

    ``cast`` is a RUNTIME no-op (it returns the object unchanged), so ``query_scope`` type-checks
    against its ``-> list[BeliefState]`` Protocol signature while the test still fails RED at
    RUNTIME with ``AttributeError`` until plan 04-02 fills the body. ``MemoryCore`` does not yet
    fully satisfy ``BeliefStore`` (``add_edge`` / ``get_impact`` / ``get_scope_at`` land in later
    phases), so a direct annotated assignment would (correctly) fail strict typing — the ``cast``
    narrows only the one surface this scaffold exercises, keeping basedpyright + ruff clean.
    """
    return cast("BeliefStore", MemoryCore(backend))


def _ids(states: list[BeliefState]) -> set[str]:
    """Project the ``belief_id`` set out of a ``query_scope`` result (order-insensitive compare)."""
    return {s.belief_id for s in states}


# --------------------------------------------------------------------------------------------
# HIST-01 / D-01 / D-02 — default returns only current+active, exactly one state per belief.
# --------------------------------------------------------------------------------------------


def test_query_scope_active_only(backend: BackendPort) -> None:
    """HIST-01: the default query returns only current+active beliefs, one state per belief."""
    core = _core(backend)
    core.revise("s", "A", "v0", _event_id())
    core.revise("s", "B", "w0", _event_id())
    # Contract B: its current tail becomes retracted, so it must DROP from the default result.
    core.contract("s", "B", _event_id())

    result = core.query_scope("s", BeliefFilter())
    assert _ids(result) == {"A"}, "default query_scope returns only active-current beliefs"
    assert all(s.status is Status.active for s in result), "every returned tail is active"
    assert len(result) == 1, "exactly one current state per belief (D-01)"


# --------------------------------------------------------------------------------------------
# HIST-01 / D-02 — include_retracted=True ALSO surfaces current+retracted (Pitfall-1 guard).
# --------------------------------------------------------------------------------------------


def test_query_scope_include_retracted(backend: BackendPort) -> None:
    """HIST-01 / D-02: include_retracted=True ALSO returns current+retracted; one per belief."""
    core = _core(backend)
    core.revise("s", "A", "v0", _event_id())
    core.revise("s", "B", "w0", _event_id())
    core.contract("s", "B", _event_id())  # B's current tail is now retracted

    without = core.query_scope("s", BeliefFilter(), include_retracted=False)
    with_retracted = core.query_scope("s", BeliefFilter(), include_retracted=True)

    # Pitfall-1: the contracted belief is ABSENT with the flag off and PRESENT with it on.
    assert _ids(without) == {"A"}, "flag off: the contracted belief B is absent"
    assert _ids(with_retracted) == {"A", "B"}, "flag on: the contracted belief B reappears"
    # Still exactly one state per belief in the include_retracted mode.
    assert len(with_retracted) == 2, "one current state per belief even with retracted included"
    b_tail = next(s for s in with_retracted if s.belief_id == "B")
    assert b_tail.status is Status.retracted, "B's surfaced tail is the retracted current"


# --------------------------------------------------------------------------------------------
# HIST-01 / D-03 — an explicit BeliefFilter.status OVERRIDES the include_retracted sugar.
# --------------------------------------------------------------------------------------------


def test_status_filter_precedence(backend: BackendPort) -> None:
    """D-03: an explicit ``filter.status`` governs and overrides the include_retracted flag."""
    core = _core(backend)
    core.revise("s", "A", "v0", _event_id())
    core.revise("s", "B", "w0", _event_id())
    core.contract("s", "B", _event_id())  # B retracted, A active

    # Explicit status={retracted} must win even though include_retracted=False would say {active}.
    only_retracted = core.query_scope(
        "s", BeliefFilter(status=frozenset({Status.retracted})), include_retracted=False
    )
    assert _ids(only_retracted) == {"B"}, "explicit status={retracted} overrides the flag-off sugar"

    # Explicit status={active} must win even though include_retracted=True would add retracted.
    only_active = core.query_scope(
        "s", BeliefFilter(status=frozenset({Status.active})), include_retracted=True
    )
    assert _ids(only_active) == {"A"}, "explicit status={active} overrides the flag-on sugar"


# --------------------------------------------------------------------------------------------
# HIST-01 — belief_ids narrows the result set (closed-filter pre-filter).
# --------------------------------------------------------------------------------------------


def test_belief_ids_filter(backend: BackendPort) -> None:
    """HIST-01: ``BeliefFilter(belief_ids=...)`` narrows the result to the named beliefs."""
    core = _core(backend)
    core.revise("s", "A", "v0", _event_id())
    core.revise("s", "B", "w0", _event_id())
    core.revise("s", "C", "x0", _event_id())

    result = core.query_scope("s", BeliefFilter(belief_ids=frozenset({"A", "C"})))
    assert _ids(result) == {"A", "C"}, "belief_ids restricts the result to the named beliefs"


# --------------------------------------------------------------------------------------------
# HIST-01 / D-06 — event_id_min/max POST-FILTER the current tails; newer-than-max is ABSENT.
# --------------------------------------------------------------------------------------------


def test_event_range_postfilter(backend: BackendPort) -> None:
    """D-06: the event range drops tails outside [min,max]; a newer-than-max tail is ABSENT."""
    core = _core(backend)
    e_a = _event_id()
    e_b_old = _event_id()
    e_b_new = _event_id()  # B's CURRENT tail — strictly newer than e_b_old
    core.revise("s", "A", "v0", e_a)
    core.revise("s", "B", "w_old", e_b_old)
    core.revise("s", "B", "w_new", e_b_new)  # B's current tail carries e_b_new

    # Cap the window just below B's current tail: B must be ABSENT (D-06), NOT shown at "w_old".
    result = core.query_scope("s", BeliefFilter(event_id_max=e_b_old))
    assert _ids(result) == {"A"}, "a belief whose current tail is newer than max is absent (D-06)"
    assert all(s.value != "w_old" for s in result), (
        "the range never rewinds a belief to an older superseded value (that is get_scope_at)"
    )


# --------------------------------------------------------------------------------------------
# HIST-01 / A1 — the event range is INCLUSIVE at the exact min and max boundaries.
# --------------------------------------------------------------------------------------------


def test_event_range_boundary_inclusive(backend: BackendPort) -> None:
    """A1: a tail whose ``source_event_id`` equals event_id_min (or event_id_max) is INCLUDED."""
    core = _core(backend)
    e_lo = _event_id()
    e_mid = _event_id()
    e_hi = _event_id()
    core.revise("s", "LO", "l", e_lo)
    core.revise("s", "MID", "m", e_mid)
    core.revise("s", "HI", "h", e_hi)

    # Inclusive [e_lo, e_hi] must keep BOTH boundary tails plus the middle one.
    inclusive = core.query_scope("s", BeliefFilter(event_id_min=e_lo, event_id_max=e_hi))
    assert _ids(inclusive) == {"LO", "MID", "HI"}, "both [min,max] boundaries are inclusive (A1)"

    # Tightening to exactly the boundary keeps that single boundary belief.
    just_lo = core.query_scope("s", BeliefFilter(event_id_min=e_lo, event_id_max=e_lo))
    assert _ids(just_lo) == {"LO"}, "min==max==e_lo keeps exactly the e_lo boundary tail"


# --------------------------------------------------------------------------------------------
# HIST-01 / D-08 — a never-created scope returns [] and creates NO Scope node (pure read).
# --------------------------------------------------------------------------------------------


def test_empty_scope_returns_empty(backend: BackendPort) -> None:
    """D-08: querying an absent scope returns ``[]`` and auto-creates nothing (pure read)."""
    core = _core(backend)
    first = core.query_scope("never_created", BeliefFilter())
    assert first == [], "an absent scope yields an empty belief base"
    # A follow-up query must STILL be empty — the first read created no Scope node (pure read).
    second = core.query_scope("never_created", BeliefFilter())
    assert second == [], "query_scope is a pure read; it never auto-creates the scope (D-08)"


# --------------------------------------------------------------------------------------------
# HIST-01 / D-07 — the result is sorted by the (source_event_id, state_id) ordering contract.
# --------------------------------------------------------------------------------------------


def test_query_scope_deterministic_order(backend: BackendPort) -> None:
    """D-07: the result is monotonic in the ``(source_event_id, state_id)`` ordering."""
    core = _core(backend)
    # Insert out of event order to prove the sort, not insertion order, governs.
    e1 = _event_id()
    e2 = _event_id()
    e3 = _event_id()
    core.revise("s", "C", "c", e3)
    core.revise("s", "A", "a", e1)
    core.revise("s", "B", "b", e2)

    result = core.query_scope("s", BeliefFilter())
    keys = [(str(s.source_event_id), str(s.state_id)) for s in result]
    assert keys == sorted(keys), "query_scope returns states in (source_event_id, state_id) order"


# --------------------------------------------------------------------------------------------
# HIST-01 / SC3 / D-01 — exactly one state per (scope, belief): no duplicate beliefs.
# --------------------------------------------------------------------------------------------


def test_no_duplicate_beliefs(backend: BackendPort) -> None:
    """SC3 / D-01: even after many revises, exactly one current state per ``(scope, belief)``."""
    core = _core(backend)
    core.revise("s", "A", "v0", _event_id())
    core.revise("s", "A", "v1", _event_id())
    core.revise("s", "A", "v2", _event_id())  # three revises of A → still ONE current
    core.revise("s", "B", "w0", _event_id())

    result = core.query_scope("s", BeliefFilter())
    bids = [s.belief_id for s in result]
    assert sorted(bids) == ["A", "B"], "one current state per belief — no duplicates (SC3)"
    assert len(bids) == len(set(bids)), "no belief_id appears twice in the result"
    a_tail = next(s for s in result if s.belief_id == "A")
    assert a_tail.value == "v2", "the single A state is the latest revision (the current tail)"


# --------------------------------------------------------------------------------------------
# CHAIN-04 / SC2 / D-04 / D-05 — the four-cell retracted-vs-superseded matrix.
# --------------------------------------------------------------------------------------------


def test_retracted_superseded_matrix(backend: BackendPort) -> None:
    """CHAIN-04 / D-04/D-05: all four cells distinguishable via query_scope + get_revision_chain."""
    core = _core(backend)
    # A: revise -> revise -> contract → current+retracted (tail) + superseded+active (below tail).
    core.revise("s", "A", "v0", _event_id())
    core.revise("s", "A", "v1", _event_id())
    core.contract("s", "A", _event_id())
    # B: revise -> revise → current+active + superseded+active.
    core.revise("s", "B", "w0", _event_id())
    core.revise("s", "B", "w1", _event_id())
    # C: revise -> contract -> revise → current+active + superseded+retracted (retraction, revived).
    core.revise("s", "C", "x0", _event_id())
    core.contract("s", "C", _event_id())
    core.revise("s", "C", "x1", _event_id())

    f = BeliefFilter()
    active_now = _ids(core.query_scope("s", f, include_retracted=False))
    with_retracted = _ids(core.query_scope("s", f, include_retracted=True))

    # CURRENT row (observed through query_scope, D-05):
    assert active_now == {"B", "C"}, "current+active cell: B and C are live; A (contracted) is not"
    assert with_retracted == {"A", "B", "C"}, "current+retracted cell: A reappears with flag on"

    # SUPERSEDED cells (observed ONLY through get_revision_chain non-tail entries, not query_scope):
    a_below_tail = core.get_revision_chain("A")[:-1]
    assert any(s.status is Status.active for s in a_below_tail), (
        "superseded+active cell: A's overwritten value sits below its retracted tail"
    )
    c_below_tail = core.get_revision_chain("C")[:-1]
    assert any(s.status is Status.retracted for s in c_below_tail), (
        "superseded+retracted cell: C's earlier retraction was itself later superseded by revive"
    )


# --------------------------------------------------------------------------------------------
# CHAIN-04 / D-05 — query_scope NEVER returns a non-tail (superseded) state.
# --------------------------------------------------------------------------------------------


def test_query_scope_excludes_superseded(backend: BackendPort) -> None:
    """D-05: after revise -> revise, query_scope returns only the newer tail, not the superseded."""
    core = _core(backend)
    core.revise("s", "A", "old", _event_id())
    core.revise("s", "A", "new", _event_id())  # supersedes "old"

    result = core.query_scope("s", BeliefFilter())
    values = {s.value for s in result}
    assert values == {"new"}, "query_scope returns only the current tail, never a superseded value"
    # Cross-check: the full chain DOES still hold the superseded "old" state (history is preserved).
    chain_values = {s.value for s in core.get_revision_chain("A")}
    assert chain_values == {"old", "new"}, "the superseded value survives in the chain, not query"
