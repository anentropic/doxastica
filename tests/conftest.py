"""
Shared pytest fixtures — the parametrized throwaway-backend fixture (FORMAL-06 / D-05).

The single ``backend`` fixture is the mechanism that keeps the ladybug adapter and the
in-memory oracle honest: every test that consumes it runs once per backend
(``["memory", "ladybug"]``), so a parity test comparing each backend's output to an
expected literal already proves cross-backend agreement (D-05 / BACK-03).

Load-bearing decisions encoded here:

- **Plain ``params=[...]`` list, NOT a lookup table (D-01a):** the two first-party
  backends are named directly; there is no URL/scheme indirection.
- **Fresh throwaway ``:memory:`` DB per fixture call (FORMAL-06, Pitfall 5):** the ladybug
  param constructs a brand-new ``lb.Database()`` (None path = in-memory) for every example,
  so there is no shared-path lock contention and no cross-example state bleed.
- **``importorskip`` skips (never errors) when the driver is absent (D-03 base-CI Job 1):**
  the ladybug param is skipped — not failed — when the optional driver is not installed.
- **Function-local imports:** the backend imports live inside the fixture body so this module
  loads even when ladybug is absent (the memory param still runs).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

    from doxastica.ports import BackendPort


@pytest.fixture(params=["memory", "ladybug"])
def backend(request: pytest.FixtureRequest) -> Iterator[BackendPort]:
    """
    Yield a fresh throwaway backend per example over both adapters (FORMAL-06 / D-05).

    For ``"ladybug"``: skip when the driver is absent, else build a brand-new in-memory
    ``lb.Database()`` + ``Connection`` (fresh per call — no state bleed / lock errors) wrapped
    in a self-owning ``LadybugBackend`` that is closed on teardown. For ``"memory"``: yield a
    fresh zero-dependency ``InMemoryBackend``.
    """
    if request.param == "ladybug":
        lb = pytest.importorskip("ladybug")  # skip the param when the driver is absent (Job 1)
        from doxastica.backends.ladybug import LadybugBackend

        conn = lb.Connection(lb.Database())  # fresh in-memory DB per example (FORMAL-06)
        be = LadybugBackend(conn, namespace="dx", owns_conn=True)
        yield be
        be.close()
    else:
        from doxastica.backends.memory import InMemoryBackend

        yield InMemoryBackend()
