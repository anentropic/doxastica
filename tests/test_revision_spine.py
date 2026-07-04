"""
The Wave-0 behavior scaffold for the Phase-3 append-only revision spine (the Nyquist target).

This suite is the sampling target plan 03-02 verifies against: one named test per Phase-3
behavior requirement (SCOPE-01/02/03, CHAIN-01, OPS-01/02/03, HIST-02) plus three integrity
regressions (DEF-02-01 brace round-trip, Pitfall 2 retracted byte-identity, Pitfall 4 world-scope
``is_world`` bool). It is written against the LOCKED public surface only — ``protocol.py``
signatures + the exported ``WORLD_SCOPE_ID`` / ``WorldScopeContractionError`` — so it is meaningful
RED *before* 03-02 fills the ``MemoryCore`` op bodies and GREEN *after*.

Two load-bearing conventions, both inherited from ``tests/test_backend_parity.py``:

1. **Parametrized over the ``backend`` fixture** (``conftest.py`` ``params=["memory", "ladybug"]``):
   every test takes ``backend: BackendPort`` and runs once per backend, so each behavior is proven
   on BOTH the in-memory oracle and the ladybug reference adapter (D-05). The ladybug param is
   skipped — not failed — when the optional driver is absent.
2. **Construct ``MemoryCore(backend)`` from the injected fixture port** — NOT
   the zero-dependency in-memory factory classmethod. This is the ONE deliberate deviation from the
   bare-port parity tests: those exercise the port directly, but the spine behaviors live on
   ``MemoryCore``'s op bodies, so the core must be composed over the *parametrized* port for the
   ladybug backend to be exercised at all (03-PATTERNS test_revision_spine.py section).

RED-until-03-02 is the correct, intended state: the op bodies (``get_or_create_scope`` / ``revise``
/ ``expand`` / ``contract`` / ``get_revision_chain``) do not exist on ``MemoryCore`` yet. Do NOT
weaken these tests to make them pass and do NOT implement the bodies here — that is plan 03-02.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from doxastica import WORLD_SCOPE_ID, MemoryCore, WorldScopeContractionError

if TYPE_CHECKING:
    from doxastica.ports import BackendPort


def _event_id() -> uuid.UUID:
    """Mint a fresh caller-side ``source_event_id`` (UUID7, time-ordered, RFC 9562 section 5.7)."""
    return uuid.uuid7()


# --------------------------------------------------------------------------------------------
# SCOPE-01 — scope creation is idempotent.
# --------------------------------------------------------------------------------------------


def test_get_or_create_scope(backend: BackendPort) -> None:
    """SCOPE-01: creating "alice" yields a non-world Scope; a second call is idempotent."""
    core = MemoryCore(backend)
    first = core.get_or_create_scope("alice")
    assert first.scope_id == "alice"
    assert first.is_world is False
    second = core.get_or_create_scope("alice")
    assert second == first, "get_or_create_scope must be idempotent — same scope on re-call"


# --------------------------------------------------------------------------------------------
# SCOPE-02 — world-scope contraction is a structural error raised BEFORE any write.
# --------------------------------------------------------------------------------------------


def test_world_contract_raises(backend: BackendPort) -> None:
    """SCOPE-02 / D-03: world-scope contract raises and leaks no write before the guard fires."""
    core = MemoryCore(backend)
    with pytest.raises(WorldScopeContractionError):
        core.contract(WORLD_SCOPE_ID, "b", _event_id())
    # The guard is structural and fires BEFORE any backend access — no retracted state leaked.
    assert core.get_revision_chain("b") == [], (
        "world-scope contract must raise before any write — the chain must stay empty"
    )


# --------------------------------------------------------------------------------------------
# SCOPE-03 — the same belief_id diverges independently across scopes.
# --------------------------------------------------------------------------------------------


def test_cross_scope_divergence(backend: BackendPort) -> None:
    """SCOPE-03: revising one belief_id in two scopes keeps each scope's value independent."""
    core = MemoryCore(backend)
    alice = core.revise("alice", "sky_color", "blue", _event_id())
    bob = core.revise("bob", "sky_color", "grey", _event_id())
    assert alice.value == "blue"
    assert bob.value == "grey"
    assert alice.scope_id == "alice"
    assert bob.scope_id == "bob"
    assert alice.state_id != bob.state_id, "each scope's revision is a distinct BeliefState"


# --------------------------------------------------------------------------------------------
# CHAIN-01 — two revises of one belief_id produce two distinct, linked BeliefStates.
# --------------------------------------------------------------------------------------------


def test_belief_state_split(backend: BackendPort) -> None:
    """CHAIN-01: two revises of one belief_id share belief_id but split into two state_ids."""
    core = MemoryCore(backend)
    first = core.revise("alice", "mood", "happy", _event_id())
    second = core.revise("alice", "mood", "sad", _event_id())
    assert first.belief_id == second.belief_id == "mood"
    assert first.state_id != second.state_id, "each revision mints a distinct state_id"
    chain = core.get_revision_chain("mood")
    assert len(chain) == 2, f"the chain must hold both revisions; got {len(chain)}"


# --------------------------------------------------------------------------------------------
# OPS-01 — revise supersedes the prior current state.
# --------------------------------------------------------------------------------------------


def test_revise_supersedes(backend: BackendPort) -> None:
    """OPS-01: the first revise lays no supersede; the second supersedes it (chain grows 1 -> 2)."""
    core = MemoryCore(backend)
    core.revise("alice", "loc", "home", _event_id())
    assert len(core.get_revision_chain("loc")) == 1, "first revise: a single-state chain"
    core.revise("alice", "loc", "work", _event_id())
    chain = core.get_revision_chain("loc")
    assert len(chain) == 2, "second revise supersedes the first — chain length 2"
    assert chain[-1].value == "work", "the tail of the chain is the latest revision"


# --------------------------------------------------------------------------------------------
# OPS-02 — expand is structurally identical to revise.
# --------------------------------------------------------------------------------------------


def test_expand_equals_revise(backend: BackendPort) -> None:
    """OPS-02 / D-04: expand and revise produce structurally identical results on fresh inputs."""
    core = MemoryCore(backend)
    revised = core.revise("alice", "via_revise", "v", _event_id())
    expanded = core.expand("bob", "via_expand", "v", _event_id())
    assert revised.status == expanded.status, "both ops produce an active state (D-04)"
    assert revised.value == expanded.value == "v"
    assert len(core.get_revision_chain("via_revise")) == 1
    assert len(core.get_revision_chain("via_expand")) == 1, "expand grows the chain like revise"


# --------------------------------------------------------------------------------------------
# OPS-03 — contract vacuity (never-asserted) + contract-after-revise appends one retracted state.
# --------------------------------------------------------------------------------------------


def test_contract_vacuity_and_acts(backend: BackendPort) -> None:
    """OPS-03 / D-05: contract is a vacuous no-op when nothing is asserted; else it retracts."""
    core = MemoryCore(backend)
    # Vacuity: contracting a never-asserted belief returns None and leaves the chain empty.
    assert core.contract("alice", "unknown", _event_id()) is None
    assert core.get_revision_chain("unknown") == [], "vacuous contract leaves no state"
    # Acts: contract after a revise returns None and appends exactly one retracted state whose
    # value equals the prior current value (the retracted copy, D-05).
    core.revise("alice", "fact", "asserted", _event_id())
    assert core.contract("alice", "fact", _event_id()) is None
    chain = core.get_revision_chain("fact")
    assert len(chain) == 2, f"contract appends one retracted state; got {len(chain)}"
    retracted = chain[-1]
    assert retracted.status.value == "retracted", "the appended tail state is retracted"
    assert retracted.value == "asserted", "the retracted state copies the prior current value"


# --------------------------------------------------------------------------------------------
# HIST-02 — the revision chain returns in (source_event_id, state_id) order, incl. the tiebreak.
# --------------------------------------------------------------------------------------------


def test_revision_chain_order(backend: BackendPort) -> None:
    """HIST-02 / Pitfall 6: the chain is ordered by (source_event_id, state_id tiebreak)."""
    core = MemoryCore(backend)
    e1 = _event_id()
    e2 = _event_id()
    shared = _event_id()  # a colliding source_event_id pair to exercise the state_id tiebreak
    core.revise("alice", "seq", "first", e1)
    core.revise("alice", "seq", "second", e2)
    core.revise("alice", "seq", "third", shared)
    core.revise("alice", "seq", "fourth", shared)
    chain = core.get_revision_chain("seq")
    assert len(chain) == 4, f"all four revisions present; got {len(chain)}"
    expected = sorted(
        chain,
        key=lambda s: (str(s.source_event_id), str(s.state_id)),
    )
    assert chain == expected, (
        "get_revision_chain must return states in (source_event_id, state_id) order"
    )


# --------------------------------------------------------------------------------------------
# DEF-02-01 — a JSON-object-shaped (brace) value round-trips byte-identically through the core.
# --------------------------------------------------------------------------------------------


def test_brace_value_round_trips(backend: BackendPort) -> None:
    """DEF-02-01: a ``{"x": 2}`` value survives the round-trip (ladybug otherwise corrupts it)."""
    core = MemoryCore(backend)
    returned = core.revise("alice", "brace", {"x": 2}, _event_id())
    assert returned.value == {"x": 2}, "the returned BeliefState.value preserves the brace shape"
    chain = core.get_revision_chain("brace")
    assert chain[-1].value == {"x": 2}, (
        "the round-tripped chain value preserves the brace shape on both backends"
    )


# --------------------------------------------------------------------------------------------
# Pitfall 2 — the retracted value is byte-identical to the superseded value (no double-encode).
# --------------------------------------------------------------------------------------------


def test_retracted_value_byte_identical_to_superseded(backend: BackendPort) -> None:
    """Pitfall 2: contract copies the stored value verbatim — no re-encode artifacts."""
    core = MemoryCore(backend)
    active = core.revise("alice", "payload", {"nested": [1, 2, 3]}, _event_id())
    core.contract("alice", "payload", _event_id())
    chain = core.get_revision_chain("payload")
    retracted = chain[-1]
    assert retracted.status.value == "retracted"
    assert retracted.value == active.value, (
        "the retracted value must equal the superseded value — no double-encode drift"
    )


# --------------------------------------------------------------------------------------------
# Pitfall 4 — the world scope round-trips is_world as a real bool True on both backends.
# --------------------------------------------------------------------------------------------


def test_world_scope_is_world_bool(backend: BackendPort) -> None:
    """Pitfall 4 / D-02: get_or_create_scope(WORLD_SCOPE_ID) yields is_world as a real bool True."""
    core = MemoryCore(backend)
    world = core.get_or_create_scope(WORLD_SCOPE_ID)
    assert world.scope_id == WORLD_SCOPE_ID
    assert world.is_world is True, "the reserved world scope flags is_world as a real bool True"
    assert isinstance(world.is_world, bool), "is_world must be a Python bool on both backends"
