"""
BACK-01 guard — the internal ``BackendPort`` is a distinct, primitives-only seam.

Two assertions encode the BACK-01 decision mechanically:

1. ``BackendPort`` (the internal backend port) and ``BeliefStore`` (the public NVM↔core
   seam) are **separate** Protocol classes — distinct objects, not the same symbol. The two
   seams must be explicit and distinct in code.
2. ``BackendPort`` exposes **no** ``run`` / ``query`` / ``execute`` method — the
   declined Cypher / query-string passthrough anti-pattern. The port is LPG-primitive; a
   query-string method would re-open the dialect-coupling / injection surface the design
   removed.
"""

from typing import get_protocol_members

from doxastica.ports import BackendPort
from doxastica.protocol import BeliefStore


def test_backend_port_is_distinct_from_belief_store() -> None:
    """``BackendPort`` and ``BeliefStore`` are separate Protocol classes (BACK-01)."""
    assert BackendPort is not BeliefStore
    assert BackendPort.__name__ != BeliefStore.__name__


def test_backend_port_exposes_no_query_string_method() -> None:
    """The port exposes only LPG primitives — no ``run`` / ``query`` / ``execute`` (BACK-01)."""
    for forbidden in ("run", "query", "execute"):
        assert not hasattr(BackendPort, forbidden), (
            f"BackendPort must expose no query-string method; found: {forbidden}"
        )


def test_backend_port_exposes_the_five_primitives() -> None:
    """
    The port surface is EXACTLY the five decided LPG primitives — no more, no less.

    Asserts the full declared protocol surface via ``typing.get_protocol_members`` (the set
    of member names a structural implementer must satisfy), so a sixth primitive sneaking
    onto the seam — the dialect-coupling / query-string regression BACK-01 designed out —
    fails here, not just a missing one.
    """
    five = {"upsert_node", "add_edge", "match_nodes", "traverse", "unit_of_work"}
    members = get_protocol_members(BackendPort)
    assert members == five, (
        f"BackendPort surface must be exactly the five primitives; got {sorted(members)}"
    )
