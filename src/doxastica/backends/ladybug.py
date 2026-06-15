"""
The LadybugDB ``BackendPort`` reference adapter (BACK-02 / CONN-01..03 / D-02 / D-04).

This is the SINGLE module that imports the ``ladybug`` driver (D-02). The import is guarded
so that, when the optional driver is absent, importing this module raises a friendly
:class:`doxastica.errors.BackendDependencyError` (``pip install doxastica[ladybug]``) rather
than a raw ``ModuleNotFoundError``. Every other module in the package stays driver-blind;
``MemoryCore`` reaches this adapter only via FUNCTION-LOCAL imports in its factories.

What this adapter realizes
--------------------------
- **Flexible connection ownership (CONN-01 / R19):** ``__init__`` records an ``owns_conn``
  flag. A connection this backend opened itself (via :meth:`LadybugBackend.open`) is owned and
  closed on :meth:`close`; an INJECTED connection (``MemoryCore.from_connection``) is a
  tenant's handle and is NEVER closed.
- **Namespaced, idempotent schema bootstrap (CONN-02 / CONN-03 / D-04):** the backend is the
  sole writer of its ``{ns}_*`` closed subgraph. Bootstrap runs ``CREATE NODE/REL TABLE IF
  NOT EXISTS`` on construction; re-running against a fresh OR shared injected DB is a safe
  no-op.
- **Namespace-identifier safety (D-04, mitigates T-02-01):** DDL table identifiers cannot be
  ``$param``-bound, so the namespace MUST be string-interpolated. It is therefore validated
  against ``^[A-Za-z_][A-Za-z0-9_]*$`` BEFORE any interpolation — the one sanctioned
  interpolation guard. All belief DATA flows through ``$param`` binds.
- **The five LPG primitives in Cypher (BACK-02):** ``upsert_node`` (``MERGE ... SET``),
  ``add_edge`` (``MERGE`` edge), ``match_nodes`` (AND-exact ``$param`` predicates),
  ``traverse`` (the SC4 resolution — see below), and ``unit_of_work``
  (``BEGIN``/``COMMIT``/``ROLLBACK``). Each returns raw ``list[dict]`` below the model layer
  (D-04); ``MemoryCore`` hydrates frozen pydantic models above the port.

The SC4 confirmation (port unchanged)
-------------------------------------
The live Phase-2 spike (``02-RESEARCH.md``) confirmed the Phase-1 ``BackendPort`` survives the
real ladybug API unchanged. The two adapter-internal details that make this work:

1. Variable-length patterns cap the upper hop bound at 30 by default; ``traverse`` issues
   ``CALL var_length_extend_max_depth=<bound>`` to raise that ceiling. ``max_depth=None``
   ("full closure") compiles to the literal :data:`_DEPTH_CEILING`, not a truly-infinite walk.
2. ``$param`` is rejected inside the var-length bound (``*1..$d`` is a parser error), so the
   bound is interpolated as a validated ``int``. ``ACYCLIC`` (node-distinct) is the honest,
   cycle-safe expression of the port's "de-duplicated reachable set". The ``(reached,
   frontier)`` shape is computed in ONE query via ``min(length(p))`` + an ``EXISTS{}`` subquery.

These are documented adapter details, NOT port-signature changes — "port unchanged, SC4
confirmed".

This module holds NO AGM operation bodies (``revise`` / ``expand`` / ``contract`` are
Phases 3-6). The ``HAS_REVISION`` / ``CURRENT_STATE`` edge tables arrive in Phase 3.
"""

from __future__ import annotations

import re
from typing import Any

from doxastica import errors

try:
    import ladybug as lb
except ImportError as exc:  # pragma: no cover - exercised in the base-install CI job
    raise errors.BackendDependencyError(
        "The ladybug backend requires the 'ladybug' package. "
        "Install it with:  pip install doxastica[ladybug]"
    ) from exc


# The single sanctioned identifier guard (D-04): DDL table names cannot be $param-bound, so the
# namespace is string-interpolated and therefore MUST be validated before any interpolation.
_NS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# The literal hop bound compiled in for max_depth=None ("full closure"). No real belief graph
# approaches a million deep, so the unbounded frontier is empty in practice (A1, RESEARCH).
_DEPTH_CEILING = 1_000_000


def _validate_namespace(ns: str) -> None:
    """Reject a namespace that is not a safe bare identifier (D-04, mitigates T-02-01)."""
    if not _NS_RE.match(ns):
        raise ValueError(f"namespace must match {_NS_RE.pattern!r}; got {ns!r}")


class LadybugBackend:
    """
    LadybugDB reference ``BackendPort`` adapter — the single guarded driver boundary (D-02).

    Satisfies the port structurally (implements the five LPG primitives without inheriting).
    Distinguishes an owned connection from an injected one (CONN-01 / R19); bootstraps a
    namespaced, idempotent schema (CONN-02 / CONN-03); validates the namespace before the one
    sanctioned interpolation (D-04). Belief data always flows through ``$param`` binds.
    """

    def __init__(
        self,
        conn: lb.Connection,
        *,
        namespace: str,
        owns_conn: bool,
    ) -> None:
        """
        Wrap a ladybug ``Connection`` under ``namespace`` and bootstrap its schema.

        ``owns_conn`` records whether this backend opened the connection (and may close it) or
        is a tenant of an injected one it must never close (R19). The namespace is validated
        BEFORE any DDL interpolation (D-04), then the idempotent bootstrap runs (CONN-03).
        """
        _validate_namespace(namespace)
        self._conn = conn
        self._ns = namespace
        self._owns_conn = owns_conn
        self._bootstrap_schema()

    @classmethod
    def open(cls, path: str, *, namespace: str = "dx") -> LadybugBackend:
        """
        Open a self-managing backend over ``path`` (or ``":memory:"`` / ``""`` for in-memory).

        Constructs its own ``lb.Database`` + ``lb.Connection`` and takes ownership
        (``owns_conn=True``) — :meth:`close` will close the connection. This is what
        ``MemoryCore.open`` wires to. A ``:memory:`` / ``""`` path yields a fresh in-memory DB.
        """
        db_path = None if path in (":memory:", "") else path
        db = lb.Database(db_path) if db_path is not None else lb.Database()
        conn = lb.Connection(db)
        return cls(conn, namespace=namespace, owns_conn=True)

    def close(self) -> None:
        """Close the connection ONLY if owned (R19: never close an injected handle)."""
        if self._owns_conn:
            self._conn.close()  # idempotent — double-close is a no-op (verified live)

    def _bootstrap_schema(self) -> None:
        """
        Idempotently create the namespaced node/rel tables (CONN-02 / CONN-03).

        ``CREATE ... IF NOT EXISTS`` is a safe no-op when re-run against a fresh OR shared
        injected DB. ``{self._ns}`` is the ONLY interpolated identifier (validated in
        ``__init__``); everything else is structural DDL. ``state_id`` is a STRING PK holding
        the UUID7 text form (the core mints + stringifies; CONN-03 uniqueness via PRIMARY KEY).
        ``HAS_REVISION`` / ``CURRENT_STATE`` arrive in Phase 3.
        """
        ns = self._ns
        self._exec(
            f"CREATE NODE TABLE IF NOT EXISTS {ns}_Scope"
            f"(scope_id STRING, is_world BOOLEAN, PRIMARY KEY(scope_id))"
        )
        self._exec(
            f"CREATE NODE TABLE IF NOT EXISTS {ns}_Belief(belief_id STRING, PRIMARY KEY(belief_id))"
        )
        self._exec(
            f"CREATE NODE TABLE IF NOT EXISTS {ns}_BeliefState"
            f"(state_id STRING, belief_id STRING, scope_id STRING, "
            f"source_event_id STRING, value STRING, status STRING, PRIMARY KEY(state_id))"
        )
        for edge_type in ("SUPERSEDES", "DEPENDS_ON", "DERIVED_FROM"):
            self._exec(
                f"CREATE REL TABLE IF NOT EXISTS {ns}_{edge_type}"
                f"(FROM {ns}_BeliefState TO {ns}_BeliefState)"
            )

    def _exec(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> lb.QueryResult:
        """
        Execute a single Cypher statement and narrow the result to a single ``QueryResult``.

        ``Connection.execute`` is typed ``QueryResult | list[QueryResult]`` (the list form is
        only for multi-statement scripts, which this adapter never issues). The single
        ``isinstance`` narrows the union — the one genuine typing task at the driver boundary
        (Pitfall 4: ladybug ships ``py.typed``, so no missing-type-stub suppression is needed).
        """
        result = self._conn.execute(cypher, parameters=parameters or {})
        assert isinstance(result, lb.QueryResult), (
            "single-statement execute must return one QueryResult"
        )
        return result
