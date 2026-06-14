"""
Typed exception surface for the doxastica core.

Phase 1 only *types* the surface; enforcement (raising ``WorldScopeContractionError``
when ``contract()`` is called on a world scope) lands in Phase 3 (SCOPE-02).

Phase 2 adds ``BackendDependencyError`` (D-02): a backend's optional driver is missing.
It subclasses BOTH ``DoxasticaError`` and ``ImportError`` so callers can catch it as
either — a domain error or the stdlib import failure it stands in for.
"""


class DoxasticaError(Exception):
    """Base class for all doxastica errors."""


class WorldScopeContractionError(DoxasticaError):
    """Raised when ``contract()`` is attempted on a privileged world scope."""


class BackendDependencyError(DoxasticaError, ImportError):
    """Raised when a backend's optional driver is not installed (e.g. ``doxastica[ladybug]``)."""
