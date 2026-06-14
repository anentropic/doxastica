"""
The internal ``BackendPort`` seam — the LPG-primitive backend port (BACK-01).

This is the *second*, distinct ``typing.Protocol`` of the architecture, sitting BELOW the
public :class:`doxastica.protocol.BeliefStore`. The backend-agnostic core writes against
this port; a concrete backend (the LadybugDB reference adapter, the in-memory oracle —
both Phase 2) implements it. The two seams are deliberately separate objects:

- :class:`doxastica.protocol.BeliefStore` — the public NVM↔core contract (AGM operations,
  closed ``BeliefFilter``, ``ImpactResult``); what consumers code against.
- :class:`BackendPort` — the internal core↔backend contract (graph primitives only); what
  storage adapters code against.

Decided granularity (BACK-01): LPG-PRIMITIVE, not Cypher-level
--------------------------------------------------------------
The port exposes ONLY labelled-property-graph primitives — ``upsert_node`` / ``add_edge`` /
``match_nodes`` / a single generic ``traverse`` / ``unit_of_work``. It deliberately exposes
**no** ``run``/``query``/``execute`` method and **no** method taking a Cypher or query
string. A query-string passthrough would (a) re-open the injection / triple-leak surface
DATA-02 designed out at the public seam, and (b) couple the "backend-agnostic" core to a
single dialect — making the LPG-vs-Cypher decision unrepresentable instead of decided.
Choosing LPG-primitive here is a decision whose reversal is a rewrite; this module makes it
real in the types. ``traverse`` is the SINGLE graph-walk primitive — ``get_impact`` and
``get_scope_at`` compose from it in Phases 3+, never via a hand-written query.

Named tension — flagged for the Phase 2 ladybug spike (SC4)
-----------------------------------------------------------
Under LPG-primitive granularity, composing ``get_impact`` / ``get_scope_at`` from the
generic ``traverse`` primitive may cost MORE round-trips than one hand-written, dialect-
specific Cypher query would. This is the accepted, named cost of keeping the core backend-
agnostic. It is NOT resolved here: the Phase 2 LadybugDB de-risking spike (SC4) confirms the
traversal round-trip budget is acceptable against the real ``ladybug`` API; if the spike
demands it, the port adjusts THEN. The contract written now (``traverse`` returning the
``(reached, frontier)`` shape, ``max_depth=None`` ⇒ full closure) is the target; the
in-memory backend's visited-set BFS is the trivial reference implementation.

Backend-blind, like the public seam: this module imports only ``contextlib``, ``typing``,
``uuid`` and ``doxastica.models`` — never ``ladybug``. The signatures use only generic LPG
vocabulary (``label`` / ``node_id`` / ``props`` / ``edge_types``); no storage dialect leaks
upward across the seam.

Pure interface; no behavior, no storage code (adapters are Phase 2).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from uuid import UUID

    from doxastica.models import EdgeType


class BackendPort(Protocol):
    """
    The internal LPG-primitive backend seam (structural typing).

    A backend adapter satisfies this port by implementing exactly the five graph
    primitives below; it need not inherit. Distinct from the public ``BeliefStore``
    Protocol — that is enforced mechanically by ``tests/test_port_distinct.py``.

    The full constraints a conforming backend must satisfy (idempotency, append-only
    safety, cycle-safe traversal, atomic ``unit_of_work``, value opacity, conformance via
    the Phase 7 suite) are written up in ``docs/backend-contract.md`` (BACK-04).
    """

    def upsert_node(
        self,
        label: str,
        node_id: UUID | str,
        props: dict[str, Any],
    ) -> None:
        """Insert-or-update a node keyed by ``node_id``; idempotent (never duplicates)."""
        ...

    def add_edge(
        self,
        edge_type: EdgeType | str,
        from_id: UUID | str,
        to_id: UUID | str,
        props: dict[str, Any] | None = None,
    ) -> None:
        """Add a typed directed edge; append-only in practice (the core never deletes)."""
        ...

    def match_nodes(
        self,
        label: str,
        where: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Return nodes of ``label`` whose props exact-match the AND-combined ``where``."""
        ...

    def traverse(
        self,
        start: UUID | str,
        edge_types: frozenset[EdgeType | str],
        max_depth: int | None,
    ) -> tuple[list[dict[str, Any]], frozenset[UUID]]:
        """
        The single generic graph-walk primitive — returns ``(reached, frontier)``.

        Follows only ``edge_types`` from ``start``, returning the de-duplicated, cycle-safe
        set of reachable nodes (``reached``) plus the ``frontier`` of nodes left unexpanded
        when ``max_depth`` is reached. ``max_depth=None`` ⇒ full transitive closure with an
        empty frontier. ``get_impact`` and ``get_scope_at`` compose from this primitive
        (Phases 3+) — there is no separate query method.
        """
        ...

    def unit_of_work(self) -> AbstractContextManager[None]:
        """Return an atomic (all-or-nothing) write-transaction context manager."""
        ...
