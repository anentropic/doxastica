"""
Convenience constructors for :class:`doxastica.core.MemoryCore` — the ``create_engine`` layer.

``MemoryCore.__init__(backend: BackendPort)`` is pure dependency injection: it takes an
already-built port and never names a backend. This module is the SQLAlchemy ``create_engine``
analog (D-01) that sits ON TOP of that DI seam — the three named convenience constructors that
DO know how to wire the two first-party backends (path/connection handling lives here, never in
``__init__``):

- ``in_memory()`` wires the always-works, zero-dependency ``InMemoryBackend`` (D-01/D-05).
- ``open(path, ...)`` builds a self-managing ``LadybugBackend`` that opens and OWNS its own
  connection (``owns_conn=True``).
- ``from_connection(conn, ...)`` wraps a tenant-supplied ``lb.Connection`` it NEVER closes
  (``owns_conn=False``; R19/CONN-01 tenancy). The roadmap's literal
  ``MemoryCore(conn, namespace=...)`` IS ``from_connection`` — NOT ``__init__``.

DROPPED from SQLAlchemy (D-01): the connection pool (ladybug is single-writer embedded) and the
Engine-vs-Connection two-tier (collapsed to one object; no ``core.connect()``). There is NO
URL/scheme registry and NO entry-point plugin system (D-01a) — just these named free functions,
for the two first-party backends.

This module is the ONLY place outside the ``doxastica.backends`` package that names a backend, so
the driver-blindness contract (D-02) is concentrated here. ``factories.py`` joins the
backend-blind spine and MUST pass the ``tests/test_import_purity.py`` module-level scan: the
``InMemoryBackend`` import in ``in_memory`` may be module-local (the memory backend is zero-dep),
but the ``ladybug`` imports in ``open`` / ``from_connection`` are FUNCTION-LOCAL — inside the
function bodies, never at module top and never under ``TYPE_CHECKING`` — so ``import doxastica``
(and ``import doxastica.factories``) never chain-loads the optional ``ladybug`` driver. The
``BackendPort`` import is type-only (under ``TYPE_CHECKING``); the ``cast("BackendPort", ...)``
in each ladybug factory pins the composed core's type statically WITHOUT importing the driver at
module scope.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from doxastica.core import MemoryCore

if TYPE_CHECKING:
    from doxastica.ports import BackendPort
    # NOTE (D-02): do NOT import ladybug here, even under TYPE_CHECKING — open() /
    # from_connection() use function-local imports to keep this module driver-blind.


def in_memory() -> MemoryCore:
    """Build a core over the zero-dependency in-memory backend (always works, D-01/D-05)."""
    from doxastica.backends.memory import InMemoryBackend  # function-local (D-02)

    return MemoryCore(InMemoryBackend())


def open(path: str, *, namespace: str = "dx") -> MemoryCore:
    """
    Build a core over a self-managing ladybug backend (``owns_conn=True``, D-01).

    Opens and owns its own LadybugDB connection for ``path`` (or ``":memory:"``). The
    ``LadybugBackend.open`` classmethod is the wave-2 ladybug adapter (plan 02-02); this
    wiring references it by name. The driver import is FUNCTION-LOCAL (D-02). (``open``
    deliberately shadows the builtin — the public factory name is part of the contract; the
    ruff ``A`` rule is not enabled, so the shadow is acceptable here.)
    """
    # function-local (D-02) — keeps this module driver-blind; the cast pins the BackendPort
    # type so the composed core is statically typed without importing the driver here.
    from doxastica.backends import ladybug

    backend = cast("BackendPort", ladybug.LadybugBackend.open(path, namespace=namespace))
    return MemoryCore(backend)


def from_connection(conn: object, *, namespace: str = "dx") -> MemoryCore:
    """
    Build a core over an INJECTED ladybug connection it never closes (R19/CONN-01).

    Wraps a tenant-supplied ``lb.Connection`` with ``owns_conn=False`` — the core is a
    tenant and must not close someone else's handle. The driver import is FUNCTION-LOCAL
    (D-02); ``LadybugBackend`` is the wave-2 ladybug adapter (plan 02-02).
    """
    # function-local (D-02) — keeps this module driver-blind. The cast pins the BackendPort
    # type; ``conn`` is typed ``object`` (not ``lb.Connection``) so this module never imports
    # the driver, hence the reportArgumentType suppression on the LadybugBackend construction.
    from doxastica.backends import ladybug

    backend = cast(
        "BackendPort",
        ladybug.LadybugBackend(conn, namespace=namespace, owns_conn=False),  # pyright: ignore[reportArgumentType]
    )
    return MemoryCore(backend)
