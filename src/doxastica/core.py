"""
``MemoryCore`` — the backend-agnostic engine that composes a ``BackendPort`` (D-01 / D-02).

Follows the SQLAlchemy ``Engine`` pattern MINUS pool, two-tier, and registry (D-01):

- The canonical constructor takes the PORT, never a raw connection:
  ``MemoryCore(backend: BackendPort)``. ``MemoryCore`` is backend-agnostic and never holds
  an ``lb.Connection`` directly (maps to ``Engine`` holding a ``Dialect``).
- Connection / path handling lives in named factory classmethods (maps to ``create_engine``):
  ``in_memory()`` wires the always-works ``InMemoryBackend``; ``open(path, ...)`` builds a
  self-managing ``LadybugBackend`` (``owns_conn=True``); ``from_connection(conn, ...)`` wraps
  an injected connection it NEVER closes (``owns_conn=False``; R19/CONN-01 tenancy). The
  roadmap's literal ``MemoryCore(conn, namespace=...)`` IS ``from_connection`` — NOT ``__init__``.
- DROPPED from SQLAlchemy: the connection pool (ladybug is single-writer embedded) and the
  Engine-vs-Connection two-tier (collapsed to one object; no ``core.connect()``). No URL/scheme
  registry (D-01a) — named classmethods only, for two first-party backends.

Driver-blind (D-02): this module imports NO driver. The ``BackendPort`` import is type-only
(under ``TYPE_CHECKING``); the ``LadybugBackend`` imports in ``open`` / ``from_connection`` are
FUNCTION-LOCAL — inside the method bodies, never at module top and never under
``TYPE_CHECKING`` — so importing ``MemoryCore`` never chain-loads ``ladybug``. The extended
``tests/test_import_purity.py`` proves this by scanning module-level imports only.

Phase 3 lands the append-only revision-spine op bodies here (the keystone): the scope
helpers, the DERIVED-current selection (D-01 — no stored ``CURRENT_STATE`` pointer), the
shared ``revise`` ≡ ``expand`` append (D-04), ``contract`` (D-05 vacuity + retracted-copy,
D-03 structural world-scope guard), and ``get_revision_chain`` (HIST-02). The remaining AGM
read surface (``query_scope`` / ``get_impact`` / ``get_scope_at``) lands in Phases 4-6. All
bodies compose ONLY the five ``BackendPort`` primitives and stay driver-blind — the opaque
``value`` is ``json.dumps``-encoded on write and ``json.loads``-decoded on hydrate so it
round-trips byte-identically on BOTH backends (DEF-02-01). ``json`` / ``uuid`` are stdlib
(allowed at module top); the only forbidden module-level import remains ``ladybug``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

from doxastica.models import WORLD_SCOPE_ID, BeliefState, Scope, Status

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from doxastica.ports import BackendPort
    # NOTE (D-02): do NOT import ladybug here, even under TYPE_CHECKING — the open() /
    # from_connection() factories use function-local imports to keep this module driver-blind.


class MemoryCore:
    """
    Backend-agnostic AGM engine composing a :class:`doxastica.ports.BackendPort` (D-01).

    Construct via the factory classmethods — ``in_memory()`` for the zero-dependency default,
    ``open(path, ...)`` / ``from_connection(conn, ...)`` for the ladybug reference backend. The
    canonical ``__init__`` takes an already-built port and never a raw connection.
    """

    def __init__(self, backend: BackendPort) -> None:
        """Wrap an already-built ``BackendPort`` (D-01: the port, never a raw connection)."""
        self._backend = backend

    @classmethod
    def in_memory(cls) -> MemoryCore:
        """Build a core over the zero-dependency in-memory backend (always works, D-01/D-05)."""
        from doxastica.backends.memory import InMemoryBackend  # function-local (D-02)

        return cls(InMemoryBackend())

    @classmethod
    def open(cls, path: str, *, namespace: str = "dx") -> MemoryCore:
        """
        Build a core over a self-managing ladybug backend (``owns_conn=True``, D-01).

        Opens and owns its own LadybugDB connection for ``path`` (or ``":memory:"``). The
        ``LadybugBackend.open`` classmethod is the wave-2 ladybug adapter (plan 02-02); this
        wiring references it by name. The driver import is FUNCTION-LOCAL (D-02).
        """
        # function-local (D-02) — keeps this module driver-blind; the cast pins the BackendPort
        # type so the composed core is statically typed without importing the driver here.
        from doxastica.backends import ladybug

        backend = cast("BackendPort", ladybug.LadybugBackend.open(path, namespace=namespace))
        return cls(backend)

    @classmethod
    def from_connection(cls, conn: object, *, namespace: str = "dx") -> MemoryCore:
        """
        Build a core over an INJECTED ladybug connection it never closes (R19/CONN-01).

        Wraps a tenant-supplied ``lb.Connection`` with ``owns_conn=False`` — the core is a
        tenant and must not close someone else's handle. The driver import is FUNCTION-LOCAL
        (D-02); ``LadybugBackend`` is the wave-2 ladybug adapter (plan 02-02).
        """
        # function-local (D-02) — keeps this module driver-blind. The cast pins the BackendPort
        # type; ``conn`` is typed ``object`` (not ``lb.Connection``) so core.py never imports the
        # driver, hence the reportArgumentType suppression on the LadybugBackend construction.
        from doxastica.backends import ladybug

        backend = cast(
            "BackendPort",
            ladybug.LadybugBackend(conn, namespace=namespace, owns_conn=False),  # pyright: ignore[reportArgumentType]
        )
        return cls(backend)

    def unit_of_work(self) -> AbstractContextManager[None]:
        """Return the composed backend's atomic write scope (the only port use in Phase 2)."""
        return self._backend.unit_of_work()

    # --- Scope management ----------------------------------------------------
    def get_or_create_scope(self, scope_id: str) -> Scope:
        """
        Return the scope ``scope_id``, creating it if absent (SCOPE-01, D-02/D-06).

        ``is_world`` is the reserved-id rule (``scope_id == WORLD_SCOPE_ID``), DERIVED in the
        core and never read back from the stored column (Pitfall 4 — a backend that coerces the
        bool must not corrupt the returned model). Idempotent: a second call returns an equal
        ``Scope`` and never duplicates the node.
        """
        is_world = scope_id == WORLD_SCOPE_ID  # D-02 reserved-id rule
        existing = self._backend.match_nodes("Scope", {"scope_id": scope_id})
        if not existing:
            self._backend.upsert_node(
                "Scope", scope_id, {"scope_id": scope_id, "is_world": is_world}
            )
        return Scope(scope_id=scope_id, is_world=is_world)  # derive is_world, do not trust col

    def _ensure_scope(self, scope_id: str) -> None:
        """
        Create the scope if absent — the create-if-absent half of ``get_or_create_scope`` (D-06).

        Called INSIDE each write's ``unit_of_work``. Applies the same reserved-id rule and never
        flips an existing scope's ``is_world`` (``is_world`` is a pure function of ``scope_id``).
        """
        if not self._backend.match_nodes("Scope", {"scope_id": scope_id}):
            self._backend.upsert_node(
                "Scope",
                scope_id,
                {"scope_id": scope_id, "is_world": scope_id == WORLD_SCOPE_ID},
            )

    # --- Derived current (the ONE place the ordering contract lives) ---------
    def _current(self, scope_id: str, belief_id: str) -> dict[str, Any] | None:
        """
        Return the DERIVED current state for ``(scope_id, belief_id)`` — or ``None`` (D-01).

        Current is the ordering-MAX active state under the UUID7 ordering contract
        ``(str(source_event_id), str(state_id))`` (DATA-03 — primary key ``source_event_id``,
        ``state_id`` tiebreak). There is NO stored ``CURRENT_STATE`` pointer; the selection is
        computed over the immutable append-only states, scoped to the exact ``(scope, belief)``
        (SCOPE-03 cross-scope divergence). The port has no ORDER-BY/aggregate primitive, so the
        max is taken core-side.
        """
        states = self._backend.match_nodes(
            "BeliefState",
            {"scope_id": scope_id, "belief_id": belief_id, "status": "active"},
        )
        if not states:
            return None
        return max(states, key=lambda s: (str(s["source_event_id"]), str(s["state_id"])))

    # --- Value-decode boundary ----------------------------------------------
    def _hydrate(self, props: dict[str, Any]) -> BeliefState:
        """
        Build a frozen ``BeliefState`` from raw port props — the ``json.loads`` decode boundary.

        Inverse of the ``json.dumps`` encode in ``_append``: ``value`` is decoded back to the
        opaque object; pydantic coerces the ``state_id`` / ``source_event_id`` strings to ``UUID``
        at the seam, and ``status`` is rebuilt as a ``Status`` member.
        """
        return BeliefState(
            state_id=props["state_id"],
            belief_id=props["belief_id"],
            scope_id=props["scope_id"],
            source_event_id=props["source_event_id"],
            value=json.loads(props["value"]),
            status=Status(props["status"]),
        )
