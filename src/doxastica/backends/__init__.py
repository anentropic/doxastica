"""
Backend adapters behind the ``BackendPort`` seam (Phase 2).

This subpackage holds the concrete implementations of the internal LPG-primitive
:class:`doxastica.ports.BackendPort`. Per the driver-isolation discipline (D-02), this
``__init__`` re-exports ONLY the zero-dependency :class:`InMemoryBackend` — it MUST NEVER
``from .ladybug import ...``. Doing so would chain-load the optional ``ladybug`` driver on
every ``import doxastica.backends``, defeating the isolation the seam exists to provide.
The driver-backed adapter is imported directly by the caller from
``doxastica.backends.ladybug`` (``LadybugBackend.open(...)`` / ``.from_connection(...)``)
and injected into ``MemoryCore`` — pure DI, so ``MemoryCore`` itself stays driver-blind and
never names or imports a backend.
"""

from doxastica.backends.memory import InMemoryBackend

__all__ = ["InMemoryBackend"]
