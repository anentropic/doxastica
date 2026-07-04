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
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    initialize,
    invariant,
    precondition,
    rule,
)

from doxastica import (
    WORLD_SCOPE_ID,
    BeliefFilter,
    MemoryCore,
    WorldScopeContractionError,
)
from doxastica.models import Stance

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
    # ``tail.stance`` is a ``Stance`` MEMBER (get_revision_chain returns hydrated BeliefStates),
    # carried so the keystone can cross-check the chain-tail stance against the oracle (SC1/D-02).
    return {"state_id": str(tail.state_id), "value": tail.value, "stance": tail.stance}


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
    #
    # SC1/D-02 widening: each entry ALSO carries the ``Stance`` MEMBER as its 5th slot, so the
    # oracle's derived base key widens ``{belief_id: value}`` → ``{belief_id: (value, stance)}``.
    # The MEMBER (not the ``.name`` token) is stored so ``_observed_base == _shadow_base`` is a
    # direct tuple-equality (``BeliefState.stance`` is also a member). ``contract`` mirrors the
    # prior stance VERBATIM (STANCE-04), matching the SUT — a default here false-positives K*2/K*3.
    Entry = tuple[str, int, Any, str, Stance]

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
        self,
        scope_id: str,
        belief_id: str,
        value: Any,
        source_event_id: uuid.UUID,
        status: str,
        stance: Stance,
    ) -> None:
        """Append one entry to the shadow oracle, bumping the monotonic append seq + state count."""
        self._seq += 1
        self.entries.setdefault((scope_id, belief_id), []).append(
            (str(source_event_id), self._seq, value, status, stance)
        )
        self._state_count += 1

    def _shadow_current(self, scope_id: str, belief_id: str) -> tuple[bool, Any, Stance | None]:
        """
        Compute the oracle's derived current for (scope, belief): ``(has_current, value, stance)``.

        The winner is the entry with max ``(source_event_id, seq)`` — the same ordering contract
        ``_current`` applies. ``has_current`` is ``True`` only when that winning entry is active;
        the third slot is the winner's ``Stance`` member (``None`` when there is no active current).
        """
        entries = self.entries.get((scope_id, belief_id))
        if not entries:
            return (False, None, None)
        _src, _seq, value, status, stance = max(entries, key=lambda e: (e[0], e[1]))
        if status == "retracted":
            return (False, None, None)
        return (True, value, stance)

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
        stance=st.sampled_from(Stance),
    )
    def revise(
        self,
        scope_id: str,
        belief_id: str,
        value: Any,
        source_event_id: uuid.UUID,
        stance: Stance,
    ) -> None:
        """Append an active state via ``revise`` and mirror it into the shadow oracle (OPS-01)."""
        self.core.revise(scope_id, belief_id, value, source_event_id, stance)
        self._record(scope_id, belief_id, value, source_event_id, "active", stance)

    @rule(
        scope_id=scopes,
        belief_id=beliefs,
        value=_values,
        source_event_id=_event_ids,
        stance=st.sampled_from(Stance),
    )
    def expand(
        self,
        scope_id: str,
        belief_id: str,
        value: Any,
        source_event_id: uuid.UUID,
        stance: Stance,
    ) -> None:
        """Append an active state via ``expand`` (mechanically identical to revise, D-04/OPS-02)."""
        self.core.expand(scope_id, belief_id, value, source_event_id, stance)
        self._record(scope_id, belief_id, value, source_event_id, "active", stance)

    def _asserted_keys(self) -> list[tuple[str, str]]:
        """Return the (scope, belief) pairs the oracle currently derives an active current for."""
        return sorted(k for k in self.entries if self._shadow_current(*k)[0])

    def _shadow_base(self, scope_id: str) -> dict[str, tuple[Any, Stance]]:
        """
        The oracle's belief base for ``scope_id``: ``{belief_id: (value, stance)}`` of active currents.

        This IS the AGM belief base ``K`` for ``scope_id``, computed INDEPENDENTLY from
        ``self.entries`` via the oracle's own ``(source_event_id, seq)`` winner selection — it never
        reads ``query_scope`` / ``_current`` (Pitfall 2, the anti-tautology rule). Every AGM
        postulate ``@invariant`` compares the SUT's observed base against this oracle-computed base.
        SC1/D-02: the base value widens to ``(value, stance)`` so two currents agreeing on value but
        differing on stance are DISTINCT — K*2/K*3/K*6 now compare stance, not just value.
        """
        base: dict[str, tuple[Any, Stance]] = {}
        for s, b in self.entries:
            if s != scope_id:
                continue
            has_current, value, stance = self._shadow_current(s, b)
            if has_current:
                assert stance is not None  # has_current ⇒ an active winner ⇒ a stance member
                base[b] = (value, stance)
        return base

    def _observed_base(self, scope_id: str) -> dict[str, tuple[Any, Stance]]:
        """
        The SUT's observed belief base for ``scope_id`` via ``query_scope`` (the AGM ``K``).

        ``query_scope(scope, BeliefFilter())`` IS the observed belief base. Returned as
        ``{belief_id: (decoded value, stance)}`` for direct comparison against ``_shadow_base`` (the
        oracle). ``s.stance`` is a hydrated ``Stance`` MEMBER, so the tuple compares directly against
        the oracle's stored member (SC1/D-02). This is the SINGLE SUT read; the expected side is
        always the independent oracle.
        """
        return {
            s.belief_id: (s.value, s.stance)
            for s in self.core.query_scope(scope_id, BeliefFilter())
        }

    @precondition(lambda self: bool(self._asserted_keys()))
    @rule(
        data=st.data(),
        source_event_id=_event_ids,
    )
    def contract(self, data: st.DataObject, source_event_id: uuid.UUID) -> None:
        """
        Contract an EXISTING current (OPS-03, D-05); assert the Hansson base-contraction postulates.

        Gated by ``@precondition`` to (scope, belief) pairs that currently DERIVE an active current
        (so the acting branch, not the vacuous no-op, is exercised). The retracted copy carries the
        prior current value and is mirrored into the oracle with the SAME ordering key the core
        uses — so whether it actually clears the current is decided by the ordering contract, not
        assumed (a contraction recorded against an earlier ``source_event_id`` does not win,
        Pitfall 6).

        FORMAL-02 (Hansson, D-07 superseded-chain phrasing): capture the oracle's belief base for
        the affected scope BEFORE and AFTER the contraction (computed independently from
        ``self.entries`` — never a second SUT read), confirm the SUT's observed base agrees with the
        oracle on BOTH sides, then assert the four Hansson base-contraction postulates over the
        oracle-derived bases — Success, Inclusion, Relevance, Core-Retainment. There is NO
        value-semantic derivation engine (D-07), so Relevance and Core-Retainment collapse to the
        ONE surgical claim — contraction retracts EXACTLY the named belief and nothing else — but
        are asserted as TWO distinctly named methods for proof completeness (RESEARCH A2).
        """
        key = data.draw(st.sampled_from(self._asserted_keys()))
        scope_id, belief_id = key
        _has, prior_value, prior_stance = self._shadow_current(scope_id, belief_id)
        assert prior_stance is not None  # precondition guarantees an active current here

        # Oracle bases BEFORE the contract (independent of the SUT, D-06/Pitfall 2).
        base_before = self._shadow_base(scope_id)
        assert self._observed_base(scope_id) == base_before  # SUT agrees with the oracle BEFORE

        self.core.contract(scope_id, belief_id, source_event_id)
        # STANCE-04 verbatim-copy mirror (D-02): the retracted tail carries the PRIOR stance, exactly
        # as the SUT's contract copies ``prior["stance"]``. Recording a default here would make the
        # oracle disagree with the SUT and false-positive K*2/K*3.
        self._record(scope_id, belief_id, prior_value, source_event_id, "retracted", prior_stance)

        # Oracle bases AFTER the contract (independent).
        base_after = self._shadow_base(scope_id)
        assert self._observed_base(scope_id) == base_after  # SUT agrees with the oracle AFTER

        self._assert_hansson_success_inclusion(scope_id, belief_id, base_before, base_after)
        self._assert_hansson_relevance(belief_id, base_before, base_after)
        self._assert_hansson_core_retainment(belief_id, base_before, base_after)

    def _assert_hansson_success_inclusion(
        self,
        scope_id: str,
        belief_id: str,
        base_before: dict[str, Any],
        base_after: dict[str, Any],
    ) -> None:
        """
        Hansson Contraction Success + Inclusion over the oracle-derived bases (FORMAL-02, D-07).

        Success: when the contraction WINS the ordering (the retracted tail is the ordering-max,
        which the oracle decides), ``belief_id`` is ABSENT from the post-contraction base. When the
        contraction does NOT win (a colliding earlier ``source_event_id``, Pitfall 6), it is a
        vacuous no-op and the base is unchanged — the oracle correctly predicts both, so Success is
        asserted exactly when the oracle drops the belief.
        Inclusion (``A÷p ⊆ A``): every ``belief_id`` present after the contract was present
        before — contraction introduces NO new asserted belief.
        """
        # Inclusion: keys(after) ⊆ keys(before)
        assert set(base_after) <= set(base_before), (
            f"Hansson Inclusion: contract({scope_id}, {belief_id}) introduced a belief absent "
            f"before: {set(base_after) - set(base_before)}"
        )
        # Success: the belief is dropped exactly when the oracle's ordering-max tail is retracted
        has_current, _value, _stance = self._shadow_current(scope_id, belief_id)
        if not has_current:
            assert belief_id not in base_after, (
                f"Hansson Success: contract({scope_id}, {belief_id}) won the ordering but the "
                f"belief is still present in the post-contraction base"
            )

    def _assert_hansson_relevance(
        self,
        belief_id: str,
        base_before: dict[str, Any],
        base_after: dict[str, Any],
    ) -> None:
        """
        Hansson Relevance, superseded-chain phrasing (FORMAL-02, D-07): symmetric difference ⊆ {p}.

        With no value-semantic derivation engine (D-07), the ONLY belief a ``contract(p)`` may
        remove is ``p`` itself — nothing irrelevant is lost. Asserted as: the symmetric difference
        of the bases across the contraction is a subset of ``{belief_id}`` (it is exactly
        ``{belief_id}`` when the contraction wins, and empty when it is a vacuous no-op). Does NOT
        fabricate a derivation relation the core lacks (Anti-Pattern).
        """
        symdiff = set(base_before) ^ set(base_after)
        assert symdiff <= {belief_id}, (
            f"Hansson Relevance: contraction changed the membership of beliefs other than "
            f"{belief_id!r}: {symdiff - {belief_id}}"
        )

    def _assert_hansson_core_retainment(
        self,
        belief_id: str,
        base_before: dict[str, Any],
        base_after: dict[str, Any],
    ) -> None:
        """
        Hansson Core-Retainment, superseded-chain phrasing (FORMAL-02, D-07): every other tail held.

        The engine-free re-statement (sibling to Relevance): for EVERY ``belief_id ≠ p`` the current
        tail is byte-identical before and after ``contract(p)`` — no collateral retraction or value
        change. A distinct named method from Relevance for proof completeness (RESEARCH A2), though
        both collapse to the same surgical-contraction claim under D-07.
        """
        for other, value in base_before.items():
            if other == belief_id:
                continue
            assert other in base_after and base_after[other] == value, (
                f"Hansson Core-Retainment: contract({belief_id}) collaterally changed belief "
                f"{other!r}: was {value!r}, now {base_after.get(other)!r}"
            )

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
                has_current, expected, expected_stance = self._shadow_current(scope_id, belief_id)
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
                # SC1/D-02: the derived-current stance matches the oracle. ``current["stance"]`` is
                # the stored ``.name`` TOKEN, so it is hydrated via ``Stance[...]`` NAME-lookup (NOT
                # ``Stance(...)`` value-lookup, which raises on the token — Pitfall 3).
                assert Stance[current["stance"]] is expected_stance, (
                    f"derived-current stance must match the oracle for ({scope_id}, {belief_id}): "
                    f"expected {expected_stance!r}, got {current['stance']!r}"
                )
                tail = _chain_tail(self.core, scope_id, belief_id)
                assert tail is not None and tail["state_id"] == current["state_id"], (
                    f"derived-current must equal the HAS_REVISION chain tail for "
                    f"({scope_id}, {belief_id}): _current state_id {current['state_id']} != "
                    f"chain-tail {tail['state_id'] if tail else None}"
                )
                # The independently-recomputed chain tail carries a ``Stance`` MEMBER — it must
                # agree with the oracle's expected stance too (cross-check, not a tautology).
                assert tail["stance"] is expected_stance, (
                    f"HAS_REVISION chain-tail stance must match the oracle for "
                    f"({scope_id}, {belief_id}): expected {expected_stance!r}, got {tail['stance']!r}"
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

    # --- AGM revision postulates (FORMAL-01) — @invariants over the op sequence ---------------
    #
    # The shadow oracle's active-current set per scope (`_shadow_base`) IS the AGM belief base K.
    # Each postulate compares the SUT's observed base (`query_scope` = `_observed_base`) against the
    # oracle — NEVER the SUT against a second SUT read (Pitfall 2, anti-tautology, D-06). The
    # doxastica phrasings (RESEARCH Pattern 3): `revise` ≡ `expand` (no consistency engine), so
    # K*3/K*4 collapse to expansion identities; K*1 Closure is DROPPED by construction (belief
    # bases are not deductively closed). BACK-05 is satisfied transversally — the Memory*/Ladybug*
    # `.TestCase` subclasses run every @invariant on both backends with no per-backend assertion.

    @invariant()
    def agm_k2_success(self) -> None:
        """
        K*2 Success (``p ∈ K*p``): every belief the oracle currently asserts is present in the base.

        After a sequence of ``revise``/``expand`` writes, every ``(scope, belief)`` the oracle
        derives an active current for MUST be present in ``query_scope(scope)`` decoding to exactly
        that value — the latest ``revise(scope, p, v)`` succeeds in making ``p`` present at ``v``.
        Expected comes ONLY from ``_shadow_base`` (the oracle); the SUT is read once via
        ``_observed_base``.
        """
        for scope_id in _SCOPE_POOL:
            expected = self._shadow_base(scope_id)  # oracle, independent
            observed = self._observed_base(scope_id)  # SUT, single read
            for belief_id, value in expected.items():
                assert belief_id in observed, (
                    f"K*2 Success: ({scope_id}, {belief_id}) is asserted in the oracle but "
                    f"absent from the observed base"
                )
                assert observed[belief_id] == value, (
                    f"K*2 Success: ({scope_id}, {belief_id}) must be present at {value!r}, "
                    f"got {observed[belief_id]!r}"
                )

    @invariant()
    def agm_k3_inclusion(self) -> None:
        """
        K*3 Inclusion (``K*p ⊆ K+p``): the observed base never holds a belief the oracle does not.

        Since ``revise ≡ expand`` (no value-semantic consistency engine, D-04), revision adds
        exactly the new tail and removes nothing except the superseded prior tail of the SAME
        ``belief_id`` — so the observed base keys equal the oracle (expand-)base keys: the observed
        base introduces NO belief the oracle's independent expansion model does not also derive.
        Phrased as ``keys(observed) ⊆ keys(oracle)`` (the ⊇ direction is K*2 Success above; together
        they pin equality). Expected from the oracle only.
        """
        for scope_id in _SCOPE_POOL:
            expected_keys = set(self._shadow_base(scope_id))  # oracle, independent
            observed_keys = set(self._observed_base(scope_id))  # SUT, single read
            assert observed_keys <= expected_keys, (
                f"K*3 Inclusion: observed base for {scope_id} holds beliefs the oracle does not "
                f"derive: {observed_keys - expected_keys}"
            )

    @invariant()
    def agm_k5_consistency(self) -> None:
        """
        K*5 Consistency: the observed base is SINGLE-VALUED — no ``belief_id`` appears twice.

        For a belief base, "consistency" is the structural property that ``query_scope`` yields
        exactly one current tail per ``(scope, belief)`` — no ``belief_id`` resolves to two states.
        This is checked directly against the SUT projection (a duplicate would be a structural
        defect, not an oracle disagreement); it complements the keystone single-valued-derived-
        current theorem already asserted at the ``_current`` level.
        """
        for scope_id in _SCOPE_POOL:
            states = self.core.query_scope(scope_id, BeliefFilter())
            belief_ids = [s.belief_id for s in states]
            assert len(belief_ids) == len(set(belief_ids)), (
                f"K*5 Consistency: query_scope({scope_id}) is not single-valued — a belief_id "
                f"appears more than once: {belief_ids}"
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


# === Single-operation AGM postulates (D-06a) — standalone @given tests over both backends ======
#
# Vacuity (K*4) and Extensionality (K*6) are single-operation properties; a full op SEQUENCE is
# overkill (CLAUDE.md testing note / D-06a), so they are plain `@given` property tests rather than
# rules on the spine machine. They CANNOT consume the function-scoped `conftest.py` `backend`
# fixture: Hypothesis does not reset a function-scoped fixture between generated inputs (the
# `function_scoped_fixture` health check), and reusing one backend across examples would bleed
# state between them. Instead each test is parametrized over the backend KIND and builds a FRESH
# throwaway backend per Hypothesis example via `_build_backend` — mirroring `_make_backend` /
# `conftest.py` (ladybug SKIPS, not fails, when the driver is absent). Running both kinds satisfies
# BACK-05 transversally exactly as the dual `.TestCase` idiom does for the stateful invariants.


def _build_backend(backend_kind: str) -> BackendPort:
    """Build a fresh throwaway backend for ``backend_kind`` (mirrors ``_make_backend``)."""
    if backend_kind == "ladybug":
        lb = pytest.importorskip("ladybug")  # SKIP, not fail, when the driver is absent
        from doxastica.backends.ladybug import LadybugBackend

        db = lb.Database(max_db_size=2**30)  # 1 GiB cap — one DB per Hypothesis example (Pitfall 4)
        return LadybugBackend(lb.Connection(db), namespace="dx", owns_conn=True)
    from doxastica.backends.memory import InMemoryBackend

    return InMemoryBackend()


def _base_of(core: MemoryCore, scope_id: str) -> dict[str, Any]:
    """The observed belief base ``{belief_id: value}`` of ``scope_id`` (one query_scope read)."""
    return {s.belief_id: s.value for s in core.query_scope(scope_id, BeliefFilter())}


@pytest.mark.parametrize("backend_kind", ["memory", "ladybug"])
@given(value=_values)
@settings(max_examples=50, deadline=None)
def test_vacuity_k4(backend_kind: str, value: Any) -> None:
    """
    K*4 Vacuity: revising a FRESH ``belief_id`` equals expanding it (no negation/consistency).

    With no consistency machinery (``revise ≡ expand``, D-04), revising a ``belief_id`` NOT
    currently asserted equals expanding it: the post-base is the prior base ∪ ``{(p, v)}``. The
    EXPECTED base is computed in plain Python from the known prior writes (the independent oracle),
    never by a second ``query_scope`` projection used as the source of truth. A FRESH backend per
    example proves the identity on both backends (BACK-05).
    """
    be = _build_backend(backend_kind)
    try:
        core = MemoryCore(be)
        e = uuid.uuid7
        # prior base, established by writes the test fully controls — the independent expectation
        core.revise("alice", "b1", 1, e())
        core.revise("alice", "b2", 2, e())
        prior_expected = {"b1": 1, "b2": 2}
        assert _base_of(core, "alice") == prior_expected
        # revise a FRESH belief_id (b3 is not asserted) — Vacuity says this equals expansion
        core.revise("alice", "b3", value, e())
        assert _base_of(core, "alice") == {**prior_expected, "b3": value}
    finally:
        close = getattr(be, "close", None)
        if callable(close):
            close()


@pytest.mark.parametrize("backend_kind", ["memory", "ladybug"])
@given(value=_values)
@settings(max_examples=50, deadline=None)
def test_extensionality_k6(backend_kind: str, value: Any) -> None:
    """
    K*6 Extensionality: ``revise(s, p, v)`` and ``expand(s, p, v)`` yield byte-identical bases.

    The core treats ``belief_id`` and ``value`` opaquely; "logically equivalent inputs" =
    identical ``(belief_id, value)`` writes. Extensionality is asserted by comparing the
    ``query_scope`` projection produced by ``revise`` against the one produced by ``expand`` on a
    SEPARATE scope — the two derived bases must be byte-identical (modulo the differing scope_id).
    Both projections are SUT reads of DISTINCT operations, not a tautological re-read of one op. A
    FRESH backend per example covers both backends (BACK-05).
    """
    be = _build_backend(backend_kind)
    try:
        core = MemoryCore(be)
        src = uuid.uuid7()  # identical inputs (same belief_id, value, source_event_id) into both
        core.revise("alice", "b1", value, src)
        core.expand("bob", "b1", value, src)
        revised = _base_of(core, "alice")
        expanded = _base_of(core, "bob")
        assert revised == expanded == {"b1": value}
    finally:
        close = getattr(be, "close", None)
        if callable(close):
            close()


@pytest.mark.parametrize("backend_kind", ["memory", "ladybug"])
@given(value=_values)
@settings(max_examples=50, deadline=None)
def test_uniformity(backend_kind: str, value: Any) -> None:
    """
    Hansson Uniformity (D-06a / D-05): re-contracting the same key is idempotent at the base level.

    With opaque values and no derivation engine (D-07), two ``contract`` calls on the SAME
    ``(scope, belief_id)`` produce identical bases: the first retracts ``p`` (dropping it from the
    base); the second is a vacuous no-op (its ``_current`` probe finds the already-retracted tail
    and returns ``None`` — D-05), so the base after the second contract equals the base after the
    first. The EXPECTED base is computed in plain Python (the independent oracle); both backends
    prove the idempotence (BACK-05).
    """
    be = _build_backend(backend_kind)
    try:
        core = MemoryCore(be)
        e = uuid.uuid7
        core.revise("alice", "p", value, e())
        core.revise("alice", "q", "kept", e())
        core.contract("alice", "p", e())
        base_after_first = _base_of(core, "alice")
        assert base_after_first == {"q": "kept"}  # p dropped, q surgically retained
        core.contract("alice", "p", e())  # second contract on the SAME key — vacuous no-op (D-05)
        assert _base_of(core, "alice") == base_after_first  # idempotent at the base level
    finally:
        close = getattr(be, "close", None)
        if callable(close):
            close()


# === FORMAL-03 named structural-invariant conformance set (D-08) ================================
#
# The full FORMAL-03 structural-invariant set is REGISTERED here (the `test_invariants.py` half).
# All three members are ALREADY implemented on `_SpineMachine` (D-08 routes them into the named set
# rather than re-implementing); they ride BOTH backends via the Memory*/Ladybug* `.TestCase`
# subclasses (BACK-05). The `get_scope_at ≡ replay` member of FORMAL-03 lives in
# `tests/test_scope_at.py::scope_at_equals_fold_for_every_cut` (the Phase-6 operational-fold
# property, already a registered dual-backend conformance invariant — D-08, not re-implemented).
#
#   FORMAL-03 conformance set (this file):
#     1. current_is_total_single_valued_and_chain_tail  — the CURRENT_STATE-uniqueness THEOREM:
#        there is NO stored pointer edge (Phase-3 D-01); single-valued derived-current holds as the
#        unique ordering-max under a unique state_id tiebreak (`_SpineMachine`, @invariant).
#     2. chain_is_immutable                             — append-only: total BeliefState count
#        equals the appends performed exactly; no op deletes/mutates/duplicates (`_SpineMachine`).
#     3. world_contract_raises                          — world-scope no-contraction: contract() on
#        WORLD_SCOPE_ID is a structural error raised before any write (`_SpineMachine`, @rule).
#   FORMAL-03 conformance set (sibling file):
#     4. scope_at_equals_fold_for_every_cut             — get_scope_at ≡ replay over every cut
#        (tests/test_scope_at.py, the lifted Phase-6 fold property — D-08).
_FORMAL_03_CONFORMANCE_SET: tuple[str, ...] = (
    "current_is_total_single_valued_and_chain_tail",
    "chain_is_immutable",
    "world_contract_raises",
    "scope_at_equals_fold_for_every_cut",  # tests/test_scope_at.py (D-08)
)
