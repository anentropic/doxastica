"""
The public ``BeliefStore`` seam (the structural NVM-core ``typing.Protocol``).

This is the structural ``typing.Protocol`` NVM (and any other consumer) codes against.

This module is the contract boundary and it is deliberately *backend-blind*: it imports
ONLY ``typing``, ``uuid`` and ``doxastica.models``. It MUST NEVER ``import ladybug`` —
the storage dialect, topology, or triple-structure of the backend must not leak across
this seam (DATA-01). That rule is not a review note: it is mechanically enforced by
``tests/test_import_purity.py`` (an AST scan), so a ``ladybug`` import here is a build
failure.

Two locked refinements over the recovered NVM sketch are encoded in the signatures and
must not regress:

- DATA-02: ``query_scope`` accepts a CLOSED ``BeliefFilter``, never a free ``str``. A free
  query string was the #1 injection / triple-leak risk; the typed filter makes it
  unrepresentable at the seam.
- DATA-04: ``get_impact`` returns an ``ImpactResult`` (carrying ``frontier`` + ``truncated``
  so a bounded cascade can never silently under-report) with ``depth: int | None = None``
  defaulting to an unbounded walk — not a bare ``list`` and not a magic ``depth=5``.

Pure interface; no behavior, no storage code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    from doxastica.models import (
        BeliefFilter,
        BeliefState,
        EdgeType,
        ImpactResult,
        Scope,
    )


class BeliefStore(Protocol):
    """
    The public belief-revision seam consumers implement against (structural typing).

    Implementers need not inherit; satisfying the method signatures is enough.

    UUID7 ordering contract (DATA-03)
    ---------------------------------
    Belief states expose a *total, deterministic* order keyed on
    ``(source_event_id byte-order, state_id tiebreak)``:

    - The primary key is the caller-supplied ``source_event_id`` compared in big-endian
      byte order (UUID7 is time-ordered by construction, RFC 9562 section 5.7).
    - When two states share a ``source_event_id`` — callers may collide intra-millisecond
      because intra-ms monotonicity is NOT demanded of the caller — the core-minted
      ``state_id`` breaks the tie. Because ``state_id`` is minted write-monotonically by the
      core, the tiebreak reflects true insertion order.

    The pair therefore yields a stable total order even under caller ``source_event_id``
    collisions. This is the ordering ``get_scope_at`` and ``get_revision_chain`` honour;
    see ``get_scope_at`` for the as-of cut semantics.
    """

    # --- Scope management ---------------------------------------------------
    def get_or_create_scope(self, scope_id: str) -> Scope:
        """Return the scope ``scope_id``, creating it if it does not yet exist."""
        ...

    # --- Core belief operations ---------------------------------------------
    def revise(
        self,
        scope_id: str,
        belief_id: str,
        value: Any,
        source_event_id: UUID,
    ) -> BeliefState:
        """AGM revision: append a new current ``BeliefState`` for ``belief_id``."""
        ...

    def expand(
        self,
        scope_id: str,
        belief_id: str,
        value: Any,
        source_event_id: UUID,
    ) -> BeliefState:
        """AGM expansion: append a ``BeliefState`` without consistency enforcement."""
        ...

    def contract(
        self,
        scope_id: str,
        belief_id: str,
        source_event_id: UUID,
    ) -> None:
        """AGM contraction: retract ``belief_id``. World-scope contraction is an error."""
        ...

    # --- Edge operations ----------------------------------------------------
    def add_edge(
        self,
        from_state_id: UUID,
        to_state_id: UUID,
        edge_type: EdgeType,
    ) -> None:
        """Add a consumer-facing edge between two belief states (closed ``EdgeType``)."""
        ...

    # --- Retrieval ----------------------------------------------------------
    def query_scope(
        self,
        scope_id: str,
        belief_filter: BeliefFilter,
        include_deprecated: bool = False,
    ) -> list[BeliefState]:
        """
        Return the belief states in ``scope_id`` matching ``belief_filter`` (DATA-02).

        ``belief_filter`` is a closed, AND-combined ``BeliefFilter`` — never a free query
        string.

        ``include_deprecated`` is ergonomic sugar over the filter's ``status`` field:
        ``False`` means ``{active}`` and ``True`` means ``{active, retracted}``. An explicit
        ``belief_filter.status`` governs — when the caller sets ``status`` it takes
        precedence over the ``include_deprecated`` shorthand.
        """
        ...

    # --- Cascade ------------------------------------------------------------
    def get_impact(
        self,
        belief_state_id: UUID,
        depth: int | None = None,
    ) -> ImpactResult:
        """
        Return the dependency cascade reachable from ``belief_state_id`` (DATA-04).

        ``depth=None`` (the default) walks to full closure; a finite ``depth`` bounds the
        walk and the returned ``ImpactResult.frontier`` / ``truncated`` report exactly what
        was left unexpanded, so a bounded cascade never silently under-reports.
        """
        ...

    # --- History ------------------------------------------------------------
    def get_revision_chain(self, belief_id: str) -> list[BeliefState]:
        """Return every revision of ``belief_id`` in ordering-contract order (DATA-03)."""
        ...

    def get_scope_at(
        self,
        scope_id: str,
        as_of_event_id: UUID,
    ) -> list[BeliefState]:
        """
        Return the belief states current in ``scope_id`` as of ``as_of_event_id``.

        The as-of cut uses the UUID7 ordering contract documented on this class: states are
        ordered by ``(source_event_id byte-order, state_id tiebreak)``, giving a total
        deterministic order even when caller ``source_event_id`` values collide
        intra-millisecond (intra-ms monotonicity is NOT demanded of the caller, RFC 9562
        section 5.7). The core-minted ``state_id`` is write-monotonic, so the tiebreak
        reflects true insertion order.
        """
        ...
