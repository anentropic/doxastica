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
from typing import TYPE_CHECKING, Any, cast

import pytest
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    initialize,
    invariant,
    precondition,
    rule,
)

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


# ============================================================================================
# HALF B — the operational-fold property (D-07, the SPEC). The correctness deliverable.
# ============================================================================================
#
# A pure-Python operational-fold oracle (`fold`) replays the recorded revise/expand/contract op
# sequence and folds it to the active base AS OF a cut. A Hypothesis `RuleBasedStateMachine` drives
# the real `revise`/`expand`/`contract` ops, mirrors each into the oracle's op-log, then asserts
# `get_scope_at(scope, cut) == fold(scope, cut)` at EVERY cut in the event pool (+ a maximal
# sentinel). This is the D-07 SPEC: SC1 (get_scope_at(latest) == query_scope(current)) falls out at
# the maximal cut, SC2 is the cut stepped across the pool, SC3 is the colliding/out-of-order ids.
#
# ANTI-TAUTOLOGY (Pitfall 6, the WHOLE point): the oracle folds OPERATIONS — it has its OWN
# `(source_event_id_str, append_seq)` winner selection and NEVER calls `get_scope_at` /
# `_current_tail` / `_current` or any production reconstruction helper. `append_seq` is the
# monotonic stand-in for the core-minted `state_id` tiebreak (both increase with append order),
# faithfully mirroring `_order_key` = `(str(source_event_id), str(state_id))`. If the oracle
# called the code under test, the proof
# would be a restatement, not a cross-check (the `_chain_tail` independence lesson,
# tests/test_invariants.py:87-104).
#
# The idiom is copied verbatim from tests/test_invariants.py's `_SpineMachine` (the fixed
# collision pool, `_make_backend` bounded-ladybug builder, `_record` op-log, the write rules,
# `teardown`, and the two `.TestCase` subclasses), renamed for this phase and extended with the
# `<= as_of` cut + the op_kind-carrying entry so `fold` can drop a contract winner (D-06).

# A small FIXED pool of pre-minted UUID7 source_event_ids. Drawing from this pool (rather than a
# fresh uuid7() per op) GUARANTEES intra-millisecond collisions AND out-of-order reuse (SC3): the
# same source_event_id recurs across ops, so the `(source_event_id, append_seq)` tiebreak in both
# the core's _order_key and the oracle's winner selection is actually exercised under adversarial id
# ordering. The pool is deliberately small so collisions are frequent within a bounded op sequence.
_EVENT_POOL: tuple[uuid.UUID, ...] = tuple(uuid.uuid7() for _ in range(3))

# A maximal sentinel cut strictly >= every pooled id (UUID7 max canonical string). Stepping the cut
# across every pooled id PLUS this sentinel is SC2; the sentinel case is SC1 (get_scope_at(latest)
# agrees with query_scope's "now").
_MAX_CUT: uuid.UUID = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

# Small fixed id pools so rules draw REAL, colliding ids (not random misses) — the same scope +
# belief get revised/contracted repeatedly, building real cut-windows the fold can step across.
_SCOPE_POOL: tuple[str, ...] = ("alice", "bob", "carol")
_BELIEF_POOL: tuple[str, ...] = ("b1", "b2", "b3")

# JSON-serializable values, including brace/bracket-shaped ones that exercise the DEF-02-01
# encode/decode boundary inside MemoryCore (the value must round-trip byte-identically on both
# backends, so the fold's verbatim Python value compares equal to get_scope_at's hydrated value).
_values = st.one_of(
    st.integers(min_value=-100, max_value=100),
    st.text(max_size=8),
    st.booleans(),
    st.lists(st.integers(min_value=0, max_value=9), max_size=3),
    st.dictionaries(st.text(min_size=1, max_size=3), st.integers(), max_size=3),
)
_event_ids = st.sampled_from(_EVENT_POOL)
_scope_ids = st.sampled_from(_SCOPE_POOL)
_belief_ids = st.sampled_from(_BELIEF_POOL)


class _ScopeAtMachine(RuleBasedStateMachine):
    """
    Drive ``revise``/``expand``/``contract`` against an op-log; verify ``get_scope_at == fold``.

    Subclasses bind ``backend_kind`` (``"memory"`` / ``"ladybug"``); ``@initialize`` builds the
    matching fresh throwaway backend per example. ``self.entries`` is the op-log shadow: per
    ``(scope, belief)`` the ordered list of recorded ops, each an ``Entry``
    ``(source_event_id_str, append_seq, value, op_kind)``. The ``fold`` oracle replays THAT log —
    never the materialized ``BeliefState`` nodes — so the equivalence is a real cross-check.
    """

    backend_kind: str = "memory"

    scopes: Bundle[str] = Bundle("scopes")
    beliefs: Bundle[str] = Bundle("beliefs")

    # Per (scope, belief): every recorded op as (source_event_id_str, append_seq, value, op_kind).
    # The DERIVED active base as-of a cut is, per (scope, belief), the op with the max
    # ``(source_event_id_str, append_seq)`` key among ops ``<= as_of`` — faithfully mirroring the
    # core's ``_order_key`` = ``(str(source_event_id), str(state_id))`` ordering contract
    # (``append_seq`` stands in for the monotonic core-minted ``state_id`` tiebreak, since both
    # increase with append order). The belief is PRESENT at the winner's value when the winner is a
    # ``revise``/``expand`` (op_kind ``"revise"``), ABSENT when the winner is a ``"contract"``
    # (retracted-as-of, D-06). This models out-of-order / colliding ``source_event_id``s correctly:
    # a contraction recorded against an EARLIER event than the assertion it targets does NOT win the
    # ordering and so leaves the assertion present at the cut (SC3 / Pitfall 6).
    Entry = tuple[str, int, Any, str]

    def _make_backend(self) -> BackendPort:
        """Construct a fresh throwaway backend for ``backend_kind`` (mirrors ``conftest.py``)."""
        if self.backend_kind == "ladybug":
            lb = pytest.importorskip("ladybug")  # skip the ladybug machine when driver absent
            from doxastica.backends.ladybug import LadybugBackend

            # Fresh in-memory DB per example (FORMAL-06). A bounded ``max_db_size`` caps the per-DB
            # mmap reservation: each ladybug in-memory DB otherwise reserves ~8 TiB of virtual
            # address space, and Hypothesis creates one DB PER EXAMPLE, so the default reservation
            # exhausts the process address space ("Buffer manager exception: Mmap … failed"). The
            # cap is a test-harness concern only — the conftest fixture creates one DB per test and
            # never hits this; the stateful machine creates dozens.
            db = lb.Database(max_db_size=2**30)  # 1 GiB cap is ample for a bounded op sequence
            return LadybugBackend(lb.Connection(db), namespace="dx", owns_conn=True)
        from doxastica.backends.memory import InMemoryBackend

        return InMemoryBackend()

    @initialize()
    def _setup(self) -> None:
        """Spin up a fresh backend + core and the empty op-log once per example."""
        self._be = self._make_backend()
        self.core = MemoryCore(self._be)
        # Per (scope, belief): the ordered list of recorded ops (source_event_id, seq, value, kind).
        self.entries: dict[tuple[str, str], list[_ScopeAtMachine.Entry]] = {}
        self._seq = 0  # monotonic append counter — the oracle's state_id-tiebreak stand-in

    def _record(
        self, scope_id: str, belief_id: str, value: Any, source_event_id: uuid.UUID, op_kind: str
    ) -> None:
        """Append one op to the op-log, bumping the monotonic append seq (the state_id stand-in)."""
        self._seq += 1
        self.entries.setdefault((scope_id, belief_id), []).append(
            (str(source_event_id), self._seq, value, op_kind)
        )

    def fold(self, scope_id: str, as_of: str) -> dict[str, Any]:
        """
        Pure-Python operational fold: the active base of ``scope_id`` AS OF ``as_of`` (D-07).

        INDEPENDENT of the core (anti-tautology, Pitfall 6): folds the recorded OP sequence with
        its OWN ``(source_event_id_str, append_seq)`` winner selection — it MUST NOT call
        ``get_scope_at`` / ``_current_tail`` / ``_current``. Mirrors ``get_scope_at`` structurally
        over the ops: keep ops with ``source_event_id_str <= as_of`` (the SAME inclusive cut,
        str-vs-str), per (scope, belief) take the winner by ``(source_event_id_str, append_seq)``
        (mirrors ``_order_key``), and DROP a belief whose winning op is a ``contract``
        (retracted-as-of, D-06). Returns ``{belief_id: value}`` for the scope.
        """
        base: dict[str, Any] = {}
        for (entry_scope, belief_id), ops in self.entries.items():
            if entry_scope != scope_id:
                continue
            eligible = [e for e in ops if e[0] <= as_of]  # the SAME inclusive str-vs-str cut (D-04)
            if not eligible:
                continue
            winner = max(eligible, key=lambda e: (e[0], e[1]))  # mirror _order_key (src, seq)
            if winner[3] == "contract":  # retracted-as-of ⇒ absent (D-06)
                continue
            base[belief_id] = winner[2]
        return base

    # --- bundle feeders: register real ids so later rules draw hits, not misses --------------
    @rule(target=scopes, scope_id=_scope_ids)
    def add_scope(self, scope_id: str) -> str:
        """Create an ordinary (non-world) scope and register it for later draws (SCOPE-01)."""
        self.core.get_or_create_scope(scope_id)
        return scope_id

    @rule(target=beliefs, belief_id=_belief_ids)
    def add_belief(self, belief_id: str) -> str:
        """Register a belief_id for later draws (the Belief node is auto-created on first write)."""
        return belief_id

    # --- write rules: each mirrors the op into the op-log (drawing ids from the collision pool) ---
    @rule(
        scope_id=scopes,
        belief_id=beliefs,
        value=_values,
        source_event_id=_event_ids,
    )
    def revise(self, scope_id: str, belief_id: str, value: Any, source_event_id: uuid.UUID) -> None:
        """Append an active state via ``revise`` and mirror it into the op-log (op_kind revise)."""
        self.core.revise(scope_id, belief_id, value, source_event_id)
        self._record(scope_id, belief_id, value, source_event_id, "revise")

    @rule(
        scope_id=scopes,
        belief_id=beliefs,
        value=_values,
        source_event_id=_event_ids,
    )
    def expand(self, scope_id: str, belief_id: str, value: Any, source_event_id: uuid.UUID) -> None:
        """Append an active state via ``expand`` (mechanically identical to revise) into the log."""
        self.core.expand(scope_id, belief_id, value, source_event_id)
        self._record(scope_id, belief_id, value, source_event_id, "revise")

    def _active_keys(self) -> list[tuple[str, str]]:
        """Return (scope, belief) pairs whose CURRENT (max-cut) fold winner is a non-contract op."""
        max_cut = str(_MAX_CUT)
        active: list[tuple[str, str]] = []
        for scope_id, belief_id in self.entries:
            if belief_id in self.fold(scope_id, max_cut):
                active.append((scope_id, belief_id))
        return sorted(active)

    @precondition(lambda self: bool(self._active_keys()))
    @rule(
        data=st.data(),
        source_event_id=_event_ids,
    )
    def contract(self, data: st.DataObject, source_event_id: uuid.UUID) -> None:
        """
        Contract a currently-active (scope, belief) and mirror it as a ``contract`` op (D-06).

        ``@precondition``-gated to keys the op-log currently derives as active "now" (the maximal
        cut), so the acting branch is exercised. The ``contract`` op is recorded with the SAME
        ordering key the core uses — so whether it actually clears the belief AT A GIVEN CUT is
        decided by the ``(source_event_id, append_seq)`` ordering, not assumed (a contraction
        recorded against an earlier ``source_event_id`` does not win, SC3 / Pitfall 6).
        """
        key = data.draw(st.sampled_from(self._active_keys()))
        scope_id, belief_id = key
        self.core.contract(scope_id, belief_id, source_event_id)
        self._record(scope_id, belief_id, None, source_event_id, "contract")

    # --- the invariant checked after EVERY step ----------------------------------------------
    @invariant()
    def scope_at_equals_fold_for_every_cut(self) -> None:
        """
        D-07 SPEC: ``get_scope_at(scope, cut) == fold(scope, cut)`` at EVERY cut, both backends.

        For each scope in the pool, for each cut in (every pooled id + the maximal sentinel), the
        ``{belief_id: value}`` projection of ``get_scope_at`` must equal the independent operational
        ``fold``. Stepping the cut across the pool is SC2; the maximal-cut case is SC1 (agreement
        with ``query_scope``'s "now"). The colliding/out-of-order pooled ids are SC3.
        """
        for scope_id in _SCOPE_POOL:
            for cut in (*_EVENT_POOL, _MAX_CUT):
                got = {s.belief_id: s.value for s in self.core.get_scope_at(scope_id, cut)}
                expected = self.fold(scope_id, str(cut))
                assert got == expected, (
                    f"get_scope_at != fold for scope {scope_id!r} at cut {cut!s}: "
                    f"get_scope_at={got!r} fold={expected!r}"
                )

    def teardown(self) -> None:
        """
        Release the per-example backend (ladybug owns a native in-memory DB handle).

        Hypothesis runs many examples per test; an owning ``LadybugBackend`` must be closed each
        time so the native DB resource is freed (an unclosed handle per example exhausts the native
        layer). The in-memory backend has no ``close`` — the ``getattr`` guard makes this a no-op
        there.
        """
        close = getattr(getattr(self, "_be", None), "close", None)
        if callable(close):
            close()


# Bounded settings so the sub-suite stays fast under shrinking/replay (the test_invariants budget).
_SETTINGS = settings(max_examples=50, stateful_step_count=20, deadline=None)


class MemoryScopeAtFoldMachine(_ScopeAtMachine):
    """The operational-fold machine bound to the in-memory backend (D-07)."""

    backend_kind = "memory"


class LadybugScopeAtFoldMachine(_ScopeAtMachine):
    """The operational-fold machine bound to ladybug; SKIPS when the driver is absent (D-07)."""

    backend_kind = "ladybug"


# ``.TestCase`` is the auto-collected pytest entry point each subclass generates; ``settings`` is
# attached so each runs with the bounded step/example budget. Two classes ⇒ both backends covered.
# The class/test names carry ``Fold`` so ``-k Fold`` selects exactly this property (per VALIDATION).
# Hypothesis generates ``.TestCase`` dynamically (untyped), so the unittest-shim assignments and
# re-exports are narrowly ignored — the single boundary where the dynamic attribute is touched.
MemoryScopeAtFoldMachine.TestCase.settings = _SETTINGS  # pyright: ignore[reportUnknownMemberType]
LadybugScopeAtFoldMachine.TestCase.settings = _SETTINGS  # pyright: ignore[reportUnknownMemberType]

MemoryScopeAtFoldTest = MemoryScopeAtFoldMachine.TestCase  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
LadybugScopeAtFoldTest = LadybugScopeAtFoldMachine.TestCase  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
