"""
Typed exception surface for the doxastica core.

Phase 1 only *types* the surface; enforcement (raising ``WorldScopeContractionError``
when ``contract()`` is called on a world scope) lands in Phase 3 (SCOPE-02).
"""


class DoxasticaError(Exception):
    """Base class for all doxastica errors."""


class WorldScopeContractionError(DoxasticaError):
    """Raised when ``contract()`` is attempted on a privileged world scope."""
