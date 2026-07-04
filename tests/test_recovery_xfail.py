"""
The single deliberate AGM exclusion — Recovery as a loud, named, *strict* xfail (FORMAL-04).

doxastica implements Hansson belief-*base* contraction (NOT closed-set AGM): the base is a
flat set of explicit beliefs, not a logically-closed theory. AGM **Recovery**
(``K ⊆ (K ÷ p) + p`` — re-adding ``p`` after contracting it restores the whole original
theory) is the one postulate Hansson drops for belief bases, and the one doxastica
deliberately excludes (CLAUDE.md: "one deliberate exclusion (AGM *recovery*, replaced by
superseded-chain semantics)"). This module records that exclusion *mechanically*:

1. ``test_recovery_does_not_hold_for_belief_bases`` — a deterministic, hand-built
   counterexample that ASSERTS Recovery's (closed-set) conclusion against the correct
   engine. Because the superseded chain does NOT resurrect superseded content, the assertion
   FAILS → the test reports ``xfailed`` (GREEN). The mark carries ``strict=True`` so that if
   the engine ever *drifts* toward satisfying Recovery, the test XPASSes → the suite goes RED
   (the drift guard). pyproject has only ``addopts = "-v"`` and NO global ``xfail_strict``,
   so ``strict=True`` MUST live on the mark itself.

2. ``test_superseded_chain_replaces_recovery`` — the D-05 PASSING positives that fill
   Recovery's slot: after ``contract(p)`` then ``revise(p, v')`` the chain reads
   ``active → retracted → active``, current resolves to ``v'`` (the old value is NOT
   silently restored), and the contracted state is RETAINED (append-only — nothing deleted).

**Boundary (D-05 / Pitfall 5):** AGM *Recovery* (the postulate, excluded here) is DISTINCT
from temporal *history* recoverability (the as-of scope reconstruction / revision-chain can
reconstruct any past state — Phase 6, a separate held property). The two are never conflated:
no test in this module performs an as-of/time-travel scope reconstruction.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from doxastica import BeliefFilter, InMemoryBackend, MemoryCore

if TYPE_CHECKING:
    from doxastica.ports import BackendPort


@pytest.mark.xfail(
    strict=True,
    reason="AGM Recovery excluded — belief base (not closed set); Hansson; "
    "replaced by superseded-chain semantics",
)
def test_recovery_does_not_hold_for_belief_bases() -> None:
    """
    Recovery's closed-set conclusion is FALSE for doxastica's superseded chain (strict xfail).

    AGM Recovery (``K ⊆ (K ÷ p) + p``) is excluded because doxastica is a Hansson belief
    *base* (a flat set of explicit beliefs), not a logically-closed theory — Hansson drops
    Recovery for bases and replaces it with Relevance + Core-Retainment. The superseded-chain
    engine REPLACES Recovery: contracting then re-asserting ``p`` does NOT restore the
    pre-contraction value; it appends a fresh active value on top of the retracted one.

    Ratified counterexample base (resolves Open Q1 / Pitfall 1 — the naive ``{p, q}`` base
    does NOT bite, because an independent ``q`` survives contraction of ``p`` and yields an
    erroneous XPASS). A SINGLE belief ``p`` re-asserted at a NEW value is the honest base:
    ``revise(p, "v") → contract(p) → revise(p, "vprime")``. Closed-set Recovery would DEMAND
    the observed base equal the pre-contraction base ``{"p": "v"}``; the superseded chain
    correctly DENIES it (the observed base is ``{"p": "vprime"}`` — superseded content is
    never resurrected). The assertion below states the Recovery conclusion, so it FAILS
    against the correct engine → this test is ``xfailed`` (GREEN).

    ``strict=True`` on the mark (no global ``xfail_strict`` exists) is the DRIFT GUARD: if the
    engine ever satisfies Recovery, this assertion PASSES → the strict xfail XPASSes → the
    suite goes RED, loudly announcing the semantics moved away from belief-base.

    DISTINCT from temporal recoverability (Pitfall 5): this is the AGM Recovery *postulate*,
    not history replay — as-of/time-travel scope reconstruction is a SEPARATE held property
    and is NOT exercised here.
    """
    core = MemoryCore(InMemoryBackend())  # the memory backend is the AGM oracle (zero-dep)

    def e() -> uuid.UUID:
        return uuid.uuid7()

    core.revise("s", "p", "v", e())
    core.contract("s", "p", e())
    core.revise("s", "p", "vprime", e())  # re-assert p at a NEW value

    base = {s.belief_id: s.value for s in core.query_scope("s", BeliefFilter())}

    # Closed-set Recovery would restore the pre-contraction content ({"p": "v"}); the
    # superseded chain yields {"p": "vprime"}, so this assertion FAILS → xfail GREEN.
    assert base == {"p": "v"}


def test_superseded_chain_replaces_recovery(backend: BackendPort) -> None:
    """
    The D-05 superseded-chain REPLACEMENT positives (PASS on both backends — BACK-05).

    In Recovery's place, the engine guarantees: after ``contract(p)`` then ``revise(p, v')``
    the cross-scope chain reads ``active(v) → retracted → active(v')``; current resolves to
    ``v'`` (the old value is NOT silently restored, contra Recovery); and the contracted
    (retracted) state is RETAINED in the chain (append-only — nothing is ever deleted). This
    is the documented behaviour that REPLACES the excluded Recovery postulate.

    Runs over the ``conftest.py`` ``backend`` fixture, so it executes on BOTH backends
    (ladybug SKIPS when the driver is absent). Values are compared via the public decoded
    surface (``BeliefState.value`` / ``query_scope`` are already decoded — DEF-02-01 codec).

    DISTINCT from temporal recoverability (Pitfall 5): this asserts the live superseded-chain
    replacement, not as-of/time-travel history replay — no as-of scope reconstruction is
    performed here.
    """
    core = MemoryCore(backend)  # injected fixture port (test_scope_at.py precedent)

    def e() -> uuid.UUID:
        return uuid.uuid7()

    core.revise("s", "p", "v", e())
    core.contract("s", "p", e())
    core.revise("s", "p", "vprime", e())

    chain = core.get_revision_chain("p")  # cross-scope, _order_key-sorted

    # (a) the documented superseded-chain read: active → retracted → active
    assert [s.status.value for s in chain] == ["active", "retracted", "active"]
    # (b) current resolves to v', not v
    assert chain[-1].value == "vprime"
    # (c) the contracted state is retained (append-only — nothing deleted)
    assert any(s.status.value == "retracted" for s in chain)

    # (d) the observed base maps p → "vprime"; the old value is NOT silently restored
    base = {s.belief_id: s.value for s in core.query_scope("s", BeliefFilter())}
    assert base.get("p") == "vprime"
