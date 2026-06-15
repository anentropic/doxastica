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

This module holds NO AGM operation bodies (``revise`` / ``expand`` / ``contract`` /
``query_scope`` / ``get_impact`` are Phases 3-6). Phase 2 writes only the constructor, the
three factories, and a ``unit_of_work`` passthrough that exercises the composed port.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

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
