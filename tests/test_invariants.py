"""
The Phase-3 keystone consistency check — a Hypothesis stateful proof of the spine invariants.

This is the SC3 / FORMAL-03 invariant test, REFRAMED by D-01 (03-CONTEXT.md): because current
is DERIVED (the ordering-max active ``BeliefState`` for a ``(scope, belief)``, never a stored
``CURRENT_STATE`` pointer), "exactly one current per belief-in-scope" is no longer an edge count
to maintain — it is a THEOREM to verify over arbitrary append-only op sequences. A
``RuleBasedStateMachine`` drives ``revise`` / ``expand`` / ``contract`` against a shadow-dict
oracle and asserts two ``@invariant``s after every step:

1. **Derived-current consistency (CHAIN-03 / SC3 / D-01, the keystone):** for every
   ``(scope, belief)`` the shadow model says is currently asserted, ``MemoryCore._current`` is
   non-``None``, decodes to the shadow value (TOTAL + SINGLE-VALUED), AND equals the
   ``HAS_REVISION`` chain tail (the ordering-max active state for that exact scope). For every
   ``(scope, belief)`` the shadow says is retracted/absent, ``_current`` is ``None``. Uniqueness
   holds as a property of a unique ``max`` under a unique ``state_id`` tiebreak — not a pointer a
   buggy write could corrupt.
2. **Chain immutability (CHAIN-02):** the total ``BeliefState`` count is monotonic
   non-decreasing across every step, and per-belief chain length never shrinks — no op ever
   deletes or mutates a ``BeliefState`` or ``HAS_REVISION`` edge (there is no edge-delete
   primitive; append-only is verified mechanically, not just asserted by construction).

Two load-bearing conventions, both inherited from the rest of the suite:

- **Run on BOTH backends** (D-05): the machine's backend construction is parametrized exactly
  like ``conftest.py`` (``["memory", "ladybug"]`` + ``importorskip``), exposed to pytest via two
  auto-collected ``TestCase`` classes. The ladybug case SKIPS — not fails — when the optional
  driver is absent.
- **Colliding ``source_event_id``s** (Pitfall 6): the ``source_event_id`` strategy draws from a
  small FIXED pool of pre-minted UUID7s so the same ``source_event_id`` recurs across appends,
  forcing the ``state_id`` tiebreak in ``_current`` / ``get_revision_chain`` to actually decide
  the ordering-max (a fresh ``uuid7()`` per append would make the primary key alone sufficient and
  never exercise the tiebreak).

This file has NO in-repo analog (Hypothesis is a dev dep but unused so far); the structure follows
CLAUDE.md's "Testing stack — Hypothesis stateful" notes + the ``conftest.py`` backend idiom. It
contains no production code.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

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

from doxastica import WORLD_SCOPE_ID, MemoryCore, WorldScopeContractionError

if TYPE_CHECKING:
    from doxastica.ports import BackendPort

# A small FIXED pool of pre-minted UUID7 source_event_ids. Drawing from this pool (rather than a
# fresh uuid7() per append) GUARANTEES collisions, which is what exercises the state_id tiebreak in
# the derived-current selection (Pitfall 6). The pool is deliberately small so collisions are
# frequent within a bounded op sequence.
_EVENT_POOL: tuple[uuid.UUID, ...] = tuple(uuid.uuid7() for _ in range(3))

# Small fixed id pools so rules draw REAL, colliding ids (not random misses) — the same scope +
# belief get revised repeatedly, building real HAS_REVISION chains the invariants can check.
_SCOPE_POOL: tuple[str, ...] = ("alice", "bob", "carol")
_BELIEF_POOL: tuple[str, ...] = ("b1", "b2", "b3")

# JSON-serializable values, including brace/bracket-shaped ones that exercise the DEF-02-01
# encode/decode boundary inside MemoryCore (the value must round-trip byte-identically).
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


def _chain_tail(core: MemoryCore, scope_id: str, belief_id: str) -> dict[str, Any] | None:
    """
    Recompute the derived current for ``(scope, belief)`` from the PUBLIC ``get_revision_chain``.

    Independently of ``_current``: take the full cross-scope revision chain (already ordered by the
    UUID7 ``(source_event_id, state_id)`` contract), filter to the exact scope, take the LAST entry
    (the ordering-max ``HAS_REVISION`` chain tail), and return it UNLESS it is ``retracted`` (a
    retracted tail ⇒ no active current, D-05). This MUST agree with ``_current`` (the keystone
    consistency check); recomputing it via the public history surface rather than re-using
    ``_current`` makes the agreement a real cross-check, not a tautology.
    """
    scoped = [s for s in core.get_revision_chain(belief_id) if s.scope_id == scope_id]
    if not scoped:
        return None
    tail = scoped[-1]  # get_revision_chain is already (source_event_id, state_id)-ordered
    if tail.status.value == "retracted":
        return None
    return {"state_id": str(tail.state_id), "value": tail.value}


class _SpineMachine(RuleBasedStateMachine):
    """
    Drive ``revise``/``expand``/``contract`` against a shadow oracle; verify the spine invariants.

    Subclasses bind ``backend_kind`` (``"memory"`` / ``"ladybug"``); ``@initialize`` builds the
    matching fresh throwaway backend per example. ``self.model`` is the shadow oracle: the current
    asserted value per ``(scope, belief)`` (a key absent ⇒ no active current there).
    """

    backend_kind: str = "memory"

    scopes: Bundle[str] = Bundle("scopes")
    beliefs: Bundle[str] = Bundle("beliefs")

    # The shadow oracle. Per (scope, belief) it records every append as a tuple
    # ``(source_event_id_str, append_seq, value, status)``. The DERIVED current is the entry with
    # the max ``(source_event_id_str, append_seq)`` key — faithfully mirroring core ``_current``'s
    # ``(source_event_id, state_id)`` ordering contract (``append_seq`` stands in for the monotonic
    # core-minted ``state_id`` tiebreak, since both increase with append order). The current VALUE
    # is the winner's value when the winner is ``active``, else ``None`` (a retracted ordering-max
    # tail ⇒ no active current, D-05). This models out-of-order / colliding ``source_event_id``s
    # correctly: a contraction recorded against an EARLIER event than the assertion it targets does
    # NOT win the ordering and so leaves the assertion current (Pitfall 6).
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
        """Spin up a fresh backend + core and the empty shadow oracle once per example."""
        self._be = self._make_backend()
        self.core = MemoryCore(self._be)
        # Per (scope, belief): the ordered list of appends (source_event_id, seq, value, status).
        self.entries: dict[tuple[str, str], list[_SpineMachine.Entry]] = {}
        self._seq = 0  # monotonic append counter — the oracle's state_id-tiebreak stand-in
        self._state_count = 0  # monotonic-state-count watermark (CHAIN-02)

    def _record(
        self, scope_id: str, belief_id: str, value: Any, source_event_id: uuid.UUID, status: str
    ) -> None:
        """Append one entry to the shadow oracle, bumping the monotonic append seq + state count."""
        self._seq += 1
        self.entries.setdefault((scope_id, belief_id), []).append(
            (str(source_event_id), self._seq, value, status)
        )
        self._state_count += 1

    def _shadow_current(self, scope_id: str, belief_id: str) -> tuple[bool, Any]:
        """
        Compute the oracle's derived current for (scope, belief): ``(has_current, value)``.

        The winner is the entry with max ``(source_event_id, seq)`` — the same ordering contract
        ``_current`` applies. ``has_current`` is ``True`` only when that winning entry is active.
        """
        entries = self.entries.get((scope_id, belief_id))
        if not entries:
            return (False, None)
        _src, _seq, value, status = max(entries, key=lambda e: (e[0], e[1]))
        if status == "retracted":
            return (False, None)
        return (True, value)

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

    # --- write rules: each mirrors the op into the shadow oracle ------------------------------
    @rule(
        scope_id=scopes,
        belief_id=beliefs,
        value=_values,
        source_event_id=_event_ids,
    )
    def revise(self, scope_id: str, belief_id: str, value: Any, source_event_id: uuid.UUID) -> None:
        """Append an active state via ``revise`` and mirror it into the shadow oracle (OPS-01)."""
        self.core.revise(scope_id, belief_id, value, source_event_id)
        self._record(scope_id, belief_id, value, source_event_id, "active")

    @rule(
        scope_id=scopes,
        belief_id=beliefs,
        value=_values,
        source_event_id=_event_ids,
    )
    def expand(self, scope_id: str, belief_id: str, value: Any, source_event_id: uuid.UUID) -> None:
        """Append an active state via ``expand`` (mechanically identical to revise, D-04/OPS-02)."""
        self.core.expand(scope_id, belief_id, value, source_event_id)
        self._record(scope_id, belief_id, value, source_event_id, "active")

    def _asserted_keys(self) -> list[tuple[str, str]]:
        """Return the (scope, belief) pairs the oracle currently derives an active current for."""
        return sorted(k for k in self.entries if self._shadow_current(*k)[0])

    @precondition(lambda self: bool(self._asserted_keys()))
    @rule(
        data=st.data(),
        source_event_id=_event_ids,
    )
    def contract(self, data: st.DataObject, source_event_id: uuid.UUID) -> None:
        """
        Contract an EXISTING current (OPS-03, D-05): append a retracted state copying its value.

        Gated by ``@precondition`` to (scope, belief) pairs that currently DERIVE an active current
        (so the acting branch, not the vacuous no-op, is exercised). The retracted copy carries the
        prior current value and is mirrored into the oracle with the SAME ordering key the core
        uses — so whether it actually clears the current is decided by the ordering contract, not
        assumed (a contraction recorded against an earlier ``source_event_id`` does not win,
        Pitfall 6).
        """
        key = data.draw(st.sampled_from(self._asserted_keys()))
        scope_id, belief_id = key
        _has, prior_value = self._shadow_current(scope_id, belief_id)
        self.core.contract(scope_id, belief_id, source_event_id)
        self._record(scope_id, belief_id, prior_value, source_event_id, "retracted")

    @rule(belief_id=beliefs, source_event_id=_event_ids)
    def world_contract_raises(self, belief_id: str, source_event_id: uuid.UUID) -> None:
        """
        World-scope contraction is a STRUCTURAL error raised before any write (SCOPE-02 / D-03).

        Routed to its own assertion (per the CLAUDE.md ``@precondition`` note): it must raise and
        leak no state, so the shadow oracle and the state-count watermark are left untouched.
        """
        with pytest.raises(WorldScopeContractionError):
            self.core.contract(WORLD_SCOPE_ID, belief_id, source_event_id)

    # --- invariants checked after EVERY step -------------------------------------------------
    @invariant()
    def current_is_total_single_valued_and_chain_tail(self) -> None:
        """
        Keystone (CHAIN-03 / SC3 / D-01): derived-current is total, single-valued, ≡ chain tail.

        For EVERY (scope, belief) in the pools, ``_current`` must agree with the shadow oracle's
        derived current (computed under the identical ordering contract): where the oracle derives
        an active current, ``_current`` is non-``None`` and decodes to that value AND equals the
        independently-recomputed ``HAS_REVISION`` chain tail (TOTAL + SINGLE-VALUED); where the
        oracle derives no current (never asserted, or the ordering-max tail is retracted),
        ``_current`` is ``None``. Uniqueness holds as a verified theorem over immutable data — the
        unique ordering-max under a unique ``state_id`` tiebreak — not a maintained pointer.
        """
        for scope_id in _SCOPE_POOL:
            for belief_id in _BELIEF_POOL:
                has_current, expected = self._shadow_current(scope_id, belief_id)
                current = self.core._current(scope_id, belief_id)
                if not has_current:
                    assert current is None, (
                        f"({scope_id}, {belief_id}) has no active current in the oracle but "
                        f"_current returned a state — derived-current is not single-valued"
                    )
                    continue
                assert current is not None, (
                    f"derived-current must be TOTAL: ({scope_id}, {belief_id}) is asserted in the "
                    f"oracle but _current returned None"
                )
                decoded = MemoryCore._decode_value(current["value"])
                assert decoded == expected, (
                    f"derived-current must be SINGLE-VALUED and match the oracle for "
                    f"({scope_id}, {belief_id}): expected {expected!r}, got {decoded!r}"
                )
                tail = _chain_tail(self.core, scope_id, belief_id)
                assert tail is not None and tail["state_id"] == current["state_id"], (
                    f"derived-current must equal the HAS_REVISION chain tail for "
                    f"({scope_id}, {belief_id}): _current state_id {current['state_id']} != "
                    f"chain-tail {tail['state_id'] if tail else None}"
                )

    @invariant()
    def chain_is_immutable(self) -> None:
        """
        Chain immutability (CHAIN-02): total BeliefState count EQUALS the appends performed.

        Every op is a pure append (or the contract no-op / world-scope raise); no op deletes,
        mutates, OR duplicates a state, so the total ``BeliefState`` count must equal the number of
        appends the rules performed EXACTLY. The exact-equality form (WR-02) catches the
        append-only/duplication defects this keystone invariant exists to detect — a ``>=`` form
        would silently pass a double-append or an over-write. The monotonic-watermark intent is
        already covered by ``_state_count`` only ever incrementing; this store-side check is the
        strong one.
        """
        total = len(self._be.match_nodes("BeliefState", {}))
        assert total == self._state_count, (
            f"BeliefState count must equal the number of appends performed exactly "
            f"(no deletes AND no duplicate writes, CHAIN-02): "
            f"store has {total} states but {self._state_count} appends were performed"
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


# Bounded settings so the sub-suite stays fast under shrinking/replay.
_SETTINGS = settings(max_examples=50, stateful_step_count=20, deadline=None)


class MemorySpineMachine(_SpineMachine):
    """The spine machine bound to the in-memory backend (D-05)."""

    backend_kind = "memory"


class LadybugSpineMachine(_SpineMachine):
    """The spine machine bound to the ladybug backend; SKIPS when the driver is absent (D-05)."""

    backend_kind = "ladybug"


# ``.TestCase`` is the auto-collected pytest entry point each subclass generates; ``settings`` is
# attached so each runs with the bounded step/example budget. Two classes ⇒ both backends covered.
# Hypothesis generates ``.TestCase`` dynamically (untyped), so the unittest-shim assignments and
# re-exports are narrowly ignored — the single boundary where the dynamic attribute is touched.
MemorySpineMachine.TestCase.settings = _SETTINGS  # pyright: ignore[reportUnknownMemberType]
LadybugSpineMachine.TestCase.settings = _SETTINGS  # pyright: ignore[reportUnknownMemberType]

MemorySpineTest = MemorySpineMachine.TestCase  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
LadybugSpineTest = LadybugSpineMachine.TestCase  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
