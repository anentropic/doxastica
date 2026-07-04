"""
Frozen typed value layer for the closed core-vs-extension taxonomy.

These models ARE the decision-grade taxonomy whose reversal would be a rewrite.
The closed property set is the opaque-value ACL boundary between the core and
downstream NVM extensions: ``value`` stays ``Any`` (opaque, JSON-encoded, never
inspected by the core) and ``source_event_id`` is a caller-supplied opaque,
non-unique handle. No storage code, no behavior — typed, frozen, validated-at-the-seam
value objects.

Encodes the Phase-1 data-model decisions:

- DATA-02: ``BeliefFilter`` is a *closed* typed filter over exactly four core-owned
  fields (no free ``str`` — the injection mitigation by construction).
- DATA-04: ``ImpactResult`` carries ``frontier`` + ``truncated`` so a bounded cascade
  can never silently under-report.
- DATA-05: belief states are finite explicit value objects — no deductive-closure or
  inference machinery (enforced negatively by the closed field set).
- DATA-06: the taxonomy is closed — ``Status`` is exactly ``{active, retracted}`` and
  ``EdgeType`` exactly the three generic consumer-facing types; narrative/temporal/
  epistemic concepts belong to the NVM layer, never here.
"""

from enum import StrEnum
from typing import Any
from uuid import UUID  # noqa: TC003  (pydantic resolves field annotations at runtime)

from pydantic import BaseModel

# The reserved world-scope id (D-02). Deliberately dunder-wrapped — chosen over a bare
# ``"world"`` so it cannot collide with a caller-chosen scope literally named "world". This is
# the single id for which ``get_or_create_scope`` yields ``Scope(is_world=True)``; the signature
# ``get_or_create_scope(scope_id: str) -> Scope`` is unchanged (no ``is_world`` parameter).
WORLD_SCOPE_ID: str = "__world__"


class Status(StrEnum):
    """
    Belief-state status — the closed core taxonomy (DATA-06).

    Exactly two members. ``invalidated``/``under_revision`` are NVM extensions and
    deliberately excluded: they carry narrative meaning the core never models.
    """

    active = "active"
    retracted = "retracted"


class EdgeType(StrEnum):
    """
    Generic consumer-facing edge types (DATA-06).

    Exactly the three domain-agnostic types ``add_edge`` accepts. The structural
    ``HAS_REVISION`` / ``CURRENT_STATE`` edges are deliberately NOT members (Open Q1
    resolved: separate structural constants), so ``add_edge`` cannot accept a
    structural edge.
    """

    SUPERSEDES = "SUPERSEDES"
    DEPENDS_ON = "DEPENDS_ON"
    DERIVED_FROM = "DERIVED_FROM"


class Scope(BaseModel, frozen=True, extra="forbid"):
    """
    A named belief-holder.

    ``is_world`` flags the privileged world scope; enforcement (world-scope
    ``contract()`` is an error) lands in Phase 3 — Phase 1 only ensures the model
    does not preclude a privileged world scope.
    """

    scope_id: str
    is_world: bool = False


class Belief(BaseModel, frozen=True, extra="forbid"):
    """Stable logical identity — one per ``Belief`` node."""

    belief_id: str


class BeliefState(BaseModel, frozen=True, extra="forbid"):
    """
    An immutable, append-only revision of a belief.

    Carries EXACTLY the closed six-field set — the DATA-05/DATA-06 boundary. No
    provenance/temporal/epistemic fields: those live in the opaque ``value`` or on
    downstream NVM labels. ``state_id`` is the core-minted UUID7 primary-key handle;
    ``source_event_id`` is a caller-supplied opaque, non-unique handle; ``value`` is
    opaque (the core never inspects it).
    """

    state_id: UUID
    belief_id: str
    scope_id: str
    source_event_id: UUID
    value: Any
    status: Status


class BeliefFilter(BaseModel, frozen=True, extra="forbid"):
    """
    A closed, AND-combined typed filter over core-owned fields (DATA-02).

    Exactly four fields, all defaulting to ``None`` (``None`` = unconstrained). There
    is no free ``str`` and no arbitrary-property predicate: the model makes a
    triple-structure leak or query injection unrepresentable.
    """

    belief_ids: frozenset[str] | None = None
    status: frozenset[Status] | None = None
    event_id_min: UUID | None = None
    event_id_max: UUID | None = None


class ImpactResult(BaseModel, frozen=True, extra="forbid"):
    """
    A bounded-cascade result that never silently under-reports (DATA-04).

    ``frontier`` holds the boundary ``state_id`` handles left unexpanded (empty when
    the traversal ran to completion); ``truncated`` is ``True`` exactly when the depth
    bound stopped the walk early.
    """

    reached: tuple[BeliefState, ...]
    frontier: frozenset[UUID]
    truncated: bool
