"""
The Phase-9 headline proof: ``stance`` survives write → persist → read byte-stable (SC4/SC5).

Plan 09-01 landed all the production plumbing (the required ``BeliefState.stance`` field, the
write-spine threading through ``revise``/``expand``/``contract``, and the name-token DDL) and
proved nothing regressed — but it did NOT assert stance is actually *preserved* (the pre-stance
suite predates the field). This suite supplies that proof, across the ``memory`` + ``ladybug``
parity fixture, so byte-stability is proven at the core boundary on both substrates.

Two load-bearing conventions, both inherited from ``tests/test_revision_spine.py`` /
``tests/test_backend_parity.py``:

1. **Parametrized over the ``backend`` fixture** (``conftest.py`` ``params=["memory", "ladybug"]``):
   every test takes ``backend: BackendPort`` and runs once per backend, so each guarantee is proven
   on BOTH the in-memory oracle and the ladybug reference adapter (D-05). The ladybug param is
   SKIPPED — never failed — when the optional driver is absent (``importorskip`` in the fixture).
2. **Drive assertions through ``MemoryCore(backend)``, NOT the bare port** — the serialize/hydrate
   discipline lives in ``core.py`` (``_append`` writes ``stance.name``; ``_hydrate`` reconstructs
   via the ``Stance[...]`` NAME-lookup), so byte-stability must be proven at the core boundary.

Every assertion is member-identity (``is``): a value-vs-name hydrate regression (09 Pitfall 1 —
``Stance(props["stance"])`` instead of ``Stance[props["stance"]]``) would raise on read rather than
silently pass, so ``is`` makes the guarantee loud. No Hypothesis / oracle machinery here — the
K*6-Extensionality oracle widening is STANCE-07 (Phase 10), explicitly out of scope.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from doxastica import MemoryCore
from doxastica.models import BeliefFilter, Stance, Status

if TYPE_CHECKING:
    from doxastica.ports import BackendPort


def _event_id() -> uuid.UUID:
    """Mint a fresh caller-side ``source_event_id`` (UUID7, time-ordered, RFC 9562 section 5.7)."""
    return uuid.uuid7()


# --------------------------------------------------------------------------------------------
# STANCE-03 / D-08 — EVERY stance member round-trips byte-stable through query_scope, both
# backends. Exhaustive over ``list(Stance)`` × the ``backend`` fixture = 8 cases (4 members ×
# 2 backends). Parametrize (NOT a Hypothesis ``given`` decorator) is the correct tool: combining
# Hypothesis with the function-scoped ``backend`` fixture would trip the ``function_scoped_fixture``
# health check and bleed state across examples (RESEARCH Pitfall 2). A single pinned witness would
# let a member-specific hydrate bug (e.g. ``doubted``-only) sail through — exhaustive enumeration
# is the proof (D-05/D-07).
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("stance", list(Stance))
def test_stance_round_trips_byte_stable(backend: BackendPort, stance: Stance) -> None:
    """STANCE-03/D-08: every member survives revise → query_scope unchanged (both backends)."""
    core = MemoryCore(backend)
    core.revise("alice", "b1", "v", _event_id(), stance=stance)
    [state] = core.query_scope("alice", BeliefFilter())
    assert state.stance is stance, (
        "the queried stance must be the exact member (name-hydrated, not value-hydrated)"
    )
    assert state.stance.name == stance.name, "the stored wire token is the member NAME (D-02)"


# --------------------------------------------------------------------------------------------
# STANCE-03 — omitting stance defaults to certain (existing callers unaffected).
# --------------------------------------------------------------------------------------------


def test_stance_defaults_to_certain(backend: BackendPort) -> None:
    """STANCE-03: omitting the stance arg on revise yields ``certain`` on both backends."""
    core = MemoryCore(backend)
    core.revise("alice", "b1", "v", _event_id())
    [state] = core.query_scope("alice", BeliefFilter())
    assert state.stance is Stance.certain, "the omitted default must round-trip as CERTAIN"


# --------------------------------------------------------------------------------------------
# STANCE-04 / D-08 — contract copies EVERY prior stance VERBATIM onto the retracted tail, both
# backends. Exhaustive over ``list(Stance)`` × the ``backend`` fixture (8 cases). A member-specific
# hydrate bug (``Stance(props["stance"])`` value-lookup instead of ``Stance[...]`` name-lookup)
# makes the ``is``-identity assertion RAISE for that member alone (VALIDATION SC3 vacuous-pass).
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("stance", list(Stance))
def test_contract_preserves_stance_verbatim(backend: BackendPort, stance: Stance) -> None:
    """STANCE-04/D-08: the retracted tail carries the active stance unchanged, every member."""
    core = MemoryCore(backend)
    active = core.revise("alice", "p", "v", _event_id(), stance=stance)
    core.contract("alice", "p", _event_id())
    retracted = core.get_revision_chain("p")[-1]
    assert retracted.status is Status.retracted, "the appended tail state must be RETRACTED"
    assert retracted.stance is active.stance, (
        "contract must copy the stored stance token VERBATIM — no decode/re-encode drift (D-02)"
    )


# --------------------------------------------------------------------------------------------
# STANCE-05 / D-08 — get_scope_at reconstructs EVERY stance member unchanged along with the rest
# of the state, both backends. Exhaustive over ``list(Stance)`` × the ``backend`` fixture (8 cases).
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("stance", list(Stance))
def test_get_scope_at_reconstructs_stance(backend: BackendPort, stance: Stance) -> None:
    """STANCE-05/D-08: time-travel round-trips every stance member with the rest of the state."""
    core = MemoryCore(backend)
    s = core.revise("alice", "p", "v", _event_id(), stance=stance)
    [state] = core.get_scope_at("alice", s.source_event_id)
    assert state.stance is stance, (
        "get_scope_at must reconstruct the exact member — _hydrate's name-lookup does it"
    )
