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
2. ``$param`` is rejected inside the var-length hop range (a parser error), so the bound is
   interpolated as a validated ``int``. ``ACYCLIC`` (node-distinct) is the honest,
   cycle-safe expression of the port's "de-duplicated reachable set". The ``(reached,
   frontier)`` shape is computed in ONE query via ``min(length(p))`` + an ``EXISTS{}`` subquery.

These are documented adapter details, NOT port-signature changes — "port unchanged, SC4
confirmed".

This module holds NO AGM operation bodies (``revise`` / ``expand`` / ``contract`` are
Phases 3-6). The ``HAS_REVISION`` / ``CURRENT_STATE`` edge tables arrive in Phase 3.
"""

from __future__ import annotations

import contextlib
import re
from typing import TYPE_CHECKING, Any, Literal

from doxastica import errors

try:
    import ladybug as lb
except ImportError as exc:  # pragma: no cover - exercised in the base-install CI job
    raise errors.BackendDependencyError(
        "The ladybug backend requires the 'ladybug' package. "
        "Install it with:  pip install doxastica[ladybug]"
    ) from exc

if TYPE_CHECKING:
    from collections.abc import Generator
    from uuid import UUID

    from doxastica.models import EdgeType


# The single sanctioned identifier guard (D-04): DDL table names cannot be $param-bound, so the
# namespace is string-interpolated and therefore MUST be validated before any interpolation.
_NS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# The literal hop bound compiled in for max_depth=None ("full closure"). This is a hard TRUNCATION
# limit, NOT a true infinity: ladybug var-length patterns need a concrete upper bound, so "full
# closure" compiles to `*1.._DEPTH_CEILING`. No real belief graph approaches ten thousand hops deep,
# so in practice the walk closes before the limit (A1, RESEARCH). If a walk ever DOES reach this
# depth, `traverse` raises rather than passing off a truncated set as a complete closure (WR-03,
# DATA-04 — never silently under-report).
#
# SIZE RATIONALE (ladybug-cycle-traverse-oom): the bound is interpolated into the var-length pattern
# `*1..N` AND lifted via `var_length_extend_max_depth=N`. Ladybug's recursive-join operator
# PRE-ALLOCATES buffer-pool memory LINEARLY in N (~18 KB per hop), independent of the actual graph
# size — so the original 1_000_000 reserved ~18 GB and OOM'd the buffer pool on ANY unbounded walk,
# even a 3-node cycle ("buffer pool is full and no memory could be freed"). This stayed latent
# because the [ladybug] extra is not synced in the dev env (those tests skip locally); CI is the
# first real execution. 10_000 caps the pre-allocation at ~290 MB peak (safe on any default,
# GB-scale buffer pool) while remaining astronomically beyond any plausible belief-revision chain —
# so the DATA-04 truncation-raise below is still a never-fires-in-practice safety net, not a limit a
# real closure approaches. Measured: bound 100->~98 MB, 1k->~124 MB, 10k->~290 MB, 50k+ -> OOM.
_DEPTH_CEILING = 10_000

# Ladybug's default var-length upper-hop cap, used ONLY as the fallback when the live cap cannot be
# read (it always can on 0.17.1). `traverse` raises the cap only when the requested bound exceeds
# the connection's CURRENT value, and restores that saved value afterward (WR-01) — so a shallow
# walk never mutates the connection's global config and even a deep walk leaves an INJECTED tenant
# connection (R19) with the EXACT ceiling it started with, default or not (WR-05).
_DEFAULT_HOP_CAP = 30

# Label -> PRIMARY KEY column. The SINGLE source of truth for each node table's PK: the
# bootstrap DDL (``_bootstrap_schema``) and the ``upsert_node`` MERGE key both read from here,
# so a schema change cannot silently diverge from the upsert key (CR-01). The port keys upsert
# on ``node_id`` for ANY label, so the MERGE key is always this PK bound to ``$id`` (matching
# the in-memory oracle, which keys on ``node_id`` regardless of label — D-05 parity).
_PK_BY_LABEL = {"Scope": "scope_id", "Belief": "belief_id", "BeliefState": "state_id"}

# Edge-type string -> (FROM label, TO label). The closed map (PATTERNS flag 1) that lets
# ``add_edge`` resolve per-edge-type endpoint labels + PK columns instead of hardcoding both
# endpoints to ``BeliefState``. ``HAS_REVISION`` is the hub-form structural edge (D-07): its FROM
# endpoint is a ``Belief`` (keyed ``belief_id``), NOT a ``BeliefState``. The three consumer-facing
# ``EdgeType`` members stay ``BeliefState -> BeliefState``. Keys are RAW STRINGS — ``HAS_REVISION``
# arrives as a string, never an ``EdgeType`` enum member (D-07), and ``str(EdgeType.X) == "X"``.
_EDGE_ENDPOINTS = {
    "HAS_REVISION": ("Belief", "BeliefState"),
    "SUPERSEDES": ("BeliefState", "BeliefState"),
    "DEPENDS_ON": ("BeliefState", "BeliefState"),
    "DERIVED_FROM": ("BeliefState", "BeliefState"),
}


def _validate_namespace(ns: str) -> None:
    """Reject a namespace that is not a safe bare identifier (D-04, mitigates T-02-01)."""
    if not _NS_RE.match(ns):
        raise ValueError(f"namespace must match {_NS_RE.pattern!r}; got {ns!r}")


def _validate_identifier(name: str) -> None:
    """
    Reject a property/column name that is not a safe bare identifier (WR-04).

    Column identifiers cannot be ``$param``-bound, so ``upsert_node`` / ``match_nodes`` interpolate
    prop/where KEYS directly into ``n.{key}``. Every such key is validated against the SAME bare-
    identifier regex the namespace uses, so the column-identifier surface is part of the data path's
    by-construction injection-proofing — not just the values.
    """
    if not _NS_RE.match(name):
        raise ValueError(f"property name must match {_NS_RE.pattern!r}; got {name!r}")


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
        Phase 3 adds ONLY the hub-form ``HAS_REVISION`` REL table (``FROM Belief TO BeliefState``,
        D-07); no ``CURRENT_STATE`` table is created — current is DERIVED, not a stored edge (D-01).
        """
        ns = self._ns
        # PK columns are read from `_PK_BY_LABEL` so the DDL and `upsert_node`'s MERGE key
        # cannot diverge (CR-01: one source of truth for each table's primary key).
        self._exec(
            f"CREATE NODE TABLE IF NOT EXISTS {ns}_Scope"
            f"({_PK_BY_LABEL['Scope']} STRING, is_world BOOLEAN, "
            f"PRIMARY KEY({_PK_BY_LABEL['Scope']}))"
        )
        self._exec(
            f"CREATE NODE TABLE IF NOT EXISTS {ns}_Belief"
            f"({_PK_BY_LABEL['Belief']} STRING, PRIMARY KEY({_PK_BY_LABEL['Belief']}))"
        )
        self._exec(
            f"CREATE NODE TABLE IF NOT EXISTS {ns}_BeliefState"
            f"({_PK_BY_LABEL['BeliefState']} STRING, belief_id STRING, scope_id STRING, "
            f"source_event_id STRING, value STRING, status STRING, "
            f"PRIMARY KEY({_PK_BY_LABEL['BeliefState']}))"
        )
        for edge_type in ("SUPERSEDES", "DEPENDS_ON", "DERIVED_FROM"):
            self._exec(
                f"CREATE REL TABLE IF NOT EXISTS {ns}_{edge_type}"
                f"(FROM {ns}_BeliefState TO {ns}_BeliefState)"
            )
        # The hub-form HAS_REVISION structural edge (D-07): FROM is a Belief (keyed belief_id),
        # NOT a BeliefState — so it is its own statement, not part of the BeliefState->BeliefState
        # loop above. No CURRENT_STATE table (D-01: current is derived, not a stored edge).
        self._exec(
            f"CREATE REL TABLE IF NOT EXISTS {ns}_HAS_REVISION"
            f"(FROM {ns}_Belief TO {ns}_BeliefState)"
        )

    def upsert_node(
        self,
        label: str,
        node_id: UUID | str,
        props: dict[str, Any],
    ) -> None:
        """
        Insert-or-update a node keyed by ``node_id``; idempotent (BACK-02).

        Compiles to ``MERGE (n:{ns}_{label} {pk:$id}) SET ...`` — ``MERGE`` (NOT ``CREATE``)
        is idempotent by construction (verified: double-MERGE = 1 node). The MERGE key column is
        the label's PRIMARY KEY, derived from ``_PK_BY_LABEL`` (CR-01) so ``Scope``/``Belief``
        nodes key on their real PK (``scope_id``/``belief_id``), not a hardcoded ``state_id``.
        The PK column is EXCLUDED from the SET loop (WR-01): ladybug rejects re-SETting the merge
        key as an ordinary property, so a caller passing the PK in ``props`` would otherwise raise
        on re-upsert. The node id and every prop value flow through ``$param`` binds (T-02-02);
        only the validated namespace and the label are interpolated (a Cypher label cannot be
        ``$param``-bound).
        """
        pk = _PK_BY_LABEL[label]
        labelled = f"{self._ns}_{label}"
        params: dict[str, Any] = {"id": str(node_id)}
        set_clauses: list[str] = []
        for i, (key, value) in enumerate(props.items()):
            if key == pk:
                continue  # never SET the PK — it is the MERGE key (ladybug rejects re-SET).
            # WR-04: prop KEYS are interpolated into `n.{key}` (column identifiers cannot be
            # $param-bound), so each must be a safe bare identifier — the same guard the namespace
            # uses. Values are still $param-bound; this defends the column-identifier surface so the
            # data path stays injection-proof even for a future key-splatting caller.
            _validate_identifier(key)
            pname = f"p{i}"
            params[pname] = value
            set_clauses.append(f"n.{key} = ${pname}")
        cypher = f"MERGE (n:{labelled} {{{pk}: $id}})"
        if set_clauses:
            cypher += " SET " + ", ".join(set_clauses)
        self._exec(cypher, params)

    def add_edge(
        self,
        edge_type: EdgeType | str,
        from_id: UUID | str,
        to_id: UUID | str,
        props: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a typed directed edge; idempotent — a repeated edge yields exactly one (BACK-02).

        Matches both endpoints then ``MERGE (a)-[:{ns}_{edge_type}]->(b)`` (verified:
        double-MERGE = 1 edge; double-CREATE = 2). The endpoint LABELS + PK columns are resolved
        per edge type from ``_EDGE_ENDPOINTS`` (+ ``_PK_BY_LABEL``), NOT hardcoded to
        ``BeliefState``/``state_id`` — so the hub-form ``HAS_REVISION`` matches its FROM endpoint
        as a ``Belief`` (keyed ``belief_id``) while the structural family stays
        ``BeliefState``->``BeliefState`` (keyed ``state_id``). ``HAS_REVISION`` arrives as a raw
        string, never an ``EdgeType`` member (D-07). Endpoint ids are ``$param`` binds; only the
        validated namespace + fixed endpoint labels + edge-type label are interpolated.

        Edge properties are NOT yet implemented (no Phase-3 edge carries any). ``props`` stays in
        the signature for port parity, but a non-empty ``props`` is REJECTED with
        ``NotImplementedError`` rather than silently dropped (IN-01) — a silent no-op would mask a
        future consumer-facing edge that expects its properties stored.
        """
        if props:
            raise NotImplementedError(
                "add_edge does not yet store edge properties; got non-empty props"
            )
        from_label, to_label = _EDGE_ENDPOINTS[str(edge_type)]
        rel = f"{self._ns}_{edge_type}"
        a_node = f"{self._ns}_{from_label}"
        b_node = f"{self._ns}_{to_label}"
        a_pk = _PK_BY_LABEL[from_label]
        b_pk = _PK_BY_LABEL[to_label]
        self._exec(
            f"MATCH (a:{a_node} {{{a_pk}: $from}}), (b:{b_node} {{{b_pk}: $to}}) "
            f"MERGE (a)-[:{rel}]->(b)",
            {"from": str(from_id), "to": str(to_id)},
        )

    def match_nodes(
        self,
        label: str,
        where: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Return nodes of ``label`` whose props exact-match the AND-combined ``where`` (BACK-02).

        Empty ``where`` returns all nodes of that label. Each predicate value is a ``$param``
        bind (T-02-02); only the namespace + label are interpolated. Returns raw ``list[dict]``
        below the model layer (D-04).
        """
        labelled = f"{self._ns}_{label}"
        params: dict[str, Any] = {}
        predicates: list[str] = []
        for i, (key, value) in enumerate(where.items()):
            # WR-04: predicate KEYS are interpolated into `n.{key}` (column identifiers cannot be
            # $param-bound), so each must be a safe bare identifier. Values stay $param-bound.
            _validate_identifier(key)
            pname = f"p{i}"
            params[pname] = value
            predicates.append(f"n.{key} = ${pname}")
        cypher = f"MATCH (n:{labelled})"
        if predicates:
            cypher += " WHERE " + " AND ".join(predicates)
        cypher += " RETURN n"
        # `RETURN n` yields a node-object dict per row; unwrap it and strip ladybug's internal
        # `_ID` / `_LABEL` keys so the row is the plain prop map the oracle returns (D-04 parity).
        return [
            {k: v for k, v in row["n"].items() if not k.startswith("_")}
            for row in self._rows(self._exec(cypher, params))
        ]

    def traverse(
        self,
        start: UUID | str,
        edge_types: frozenset[EdgeType | str],
        max_depth: int | None,
        direction: Literal["in", "out"] = "out",
    ) -> tuple[list[dict[str, Any]], frozenset[UUID | str]]:
        """
        The single graph-walk primitive — the SC4 resolution, in ONE query (BACK-02 / SC4).

        ``ACYCLIC`` var-length traversal returns the de-duplicated, cycle-safe reachable set
        (excluding ``start`` itself, matching the in-memory oracle). ``max_depth=None`` compiles
        to the literal :data:`_DEPTH_CEILING` (a hard truncation limit, NOT a true infinity) with
        ``var_length_extend_max_depth`` raised to lift the default 30-hop cap (Pitfall 1) — so the
        unbounded frontier is empty in practice. A full-closure walk that actually reaches the
        ceiling RAISES rather than silently reporting a truncated set as complete (WR-03, DATA-04).
        The
        depth bound is a validated ``int`` interpolated into ``*1..N`` (``$param`` is rejected
        there — Pitfall 2); ``$start`` is a ``$param`` bind. The ``(reached, frontier)`` shape is
        computed in one query via ``min(length(p))`` + an ``EXISTS{}`` subquery: a node is on the
        frontier iff its min depth equals the bound AND it has an unexpanded neighbour (parity
        with the oracle, asserted in plan 02-03).

        ``direction`` (D-05) selects which edges to follow: ``"out"`` (default) walks edges FROM
        ``start`` (the original outgoing query); ``"in"`` walks edges INTO ``start`` (the cascade
        ``get_impact`` needs). It flips the relationship arrow in exactly three places — the main
        var-length query, its ``EXISTS{}`` frontier subquery, and the ``bound==0`` probe — by
        deriving an ``(lhs, rhs)`` arrow pair from the closed ``Literal``. ``direction`` is a
        validated, closed-``Literal`` internal token (like the namespace), NEVER a ``$param``
        position and NEVER caller free-text, so it stays inside the one sanctioned-interpolation
        story; ``$start`` stays ``$param``-bound, ``edge_types`` stays ``_EDGE_ENDPOINTS``-checked,
        ``bound`` stays the runtime-guarded interpolated int. The ``var_length_extend_max_depth``
        cap-raise/restore is direction-AGNOSTIC and wraps BOTH directions identically (Pitfall 4).
        """
        # IN-02: make the port's MAY-raise validation surface real — an out-of-set direction (the
        # Literal is only statically enforced) must not silently fall through to the outgoing walk
        # below; it would also be an unvalidated value steering the arrow interpolation.
        if direction not in ("in", "out"):
            raise ValueError(f"direction must be 'in' or 'out'; got {direction!r}")
        # D-05: derive the reverse/forward arrow pair ONCE from the closed Literal. For "in" the
        # pattern becomes (a)<-[:rels]-(b); for "out" it stays (a)-[:rels]->(b). This is the ONLY
        # direction-dependent interpolation; everything else below is direction-agnostic.
        lhs, rhs = ("<-", "-") if direction == "in" else ("-", "->")
        ns = self._ns
        bound = max_depth if max_depth is not None else _DEPTH_CEILING
        # Runtime guard on the typed int (WR-03): the bound is INTERPOLATED into `*1..N`, never
        # $param-bound, so it is part of the injection-safety story (T-02-03). A real `raise`
        # (not `assert`) keeps the check alive under `python -O`.
        if bound < 0:
            raise ValueError(f"max_depth must be non-negative; got {bound}")
        # WR-03: `edge_types` members are INTERPOLATED into the rel pattern (`[:{rels}* ...]`),
        # never $param-bound — so each must be constrained to the known edge-type set before
        # interpolation, mirroring `add_edge`'s `_EDGE_ENDPOINTS` lookup. An empty `edge_types`
        # would also yield `rels == ""` and a malformed `[:* ...]` pattern, so reject it too.
        # This keeps the rel-pattern interpolation inside the same injection-safety story as the
        # namespace (the one sanctioned interpolation) rather than a second unvalidated surface.
        if not edge_types:
            raise ValueError("traverse requires at least one edge type")
        for et in edge_types:
            if str(et) not in _EDGE_ENDPOINTS:
                raise ValueError(f"unknown edge type for traverse: {et!r}")
        rels = "|".join(f"{ns}_{edge_type}" for edge_type in edge_types)
        node = f"{ns}_BeliefState"
        # WR-02: `max_depth=0` would compile to the degenerate var-length range `*1..0`. Match the
        # in-memory oracle (memory.py:122-124): layer 0 is `start`, every neighbour-edge exceeds the
        # bound, so nothing is reached and `start` is on the frontier iff it has any neighbour edge
        # in the walked direction. FLIP 1: the probe arrow flips with `direction` (an out-edge for
        # "out", an in-edge for "in") so max_depth=0 reports the correct directional frontier.
        if bound == 0:
            has_neighbour_edge = bool(
                self._rows(
                    self._exec(
                        f"MATCH (a:{node} {{{_PK_BY_LABEL['BeliefState']}: $start}})"
                        f"{lhs}[:{rels}]{rhs}() RETURN a LIMIT 1",
                        {"start": str(start)},
                    )
                )
            )
            frontier_zero: frozenset[UUID | str] = (
                frozenset({str(start)}) if has_neighbour_edge else frozenset()
            )
            return [], frontier_zero
        # WR-01: read the BeliefState PK from `_PK_BY_LABEL` (the SINGLE source of truth) rather
        # than hardcoding the literal `state_id`, matching the max_depth=0 fast-path above and the
        # CR-01 discipline — so a future PK rename in `_PK_BY_LABEL`/DDL stays in lockstep with the
        # main traversal query instead of silently diverging. The interpolated identifier is a
        # fixed internal constant (not caller input), so this stays inside the sanctioned-
        # interpolation story (no untrusted value reaches the Cypher text; `$start` stays bound).
        pk = _PK_BY_LABEL["BeliefState"]
        # FLIP 2 (main var-length pattern) + FLIP 3 (EXISTS frontier subquery): both arrows flip
        # with `direction` via the (lhs, rhs) pair. Flipping only some would leave a direction
        # inconsistency (Pitfall 3) — the frontier probe must match the walk direction.
        # WR-03: keep `d` in the returned rows so a `max_depth=None` (full-closure) walk can be
        # audited for the truncation ceiling below. For a true full closure NO node reaches
        # `_DEPTH_CEILING`; if any does, the closure was silently truncated by the literal cap and
        # we must NOT report it as complete (DATA-04 — never silently under-report).
        cypher = (
            f"MATCH p=(a:{node} {{{pk}: $start}}){lhs}[:{rels}* ACYCLIC 1..{bound}]{rhs}(b:{node}) "
            f"WHERE b.{pk} <> $start "
            f"WITH b, min(length(p)) AS d "
            f"RETURN b.{pk} AS state_id, d, "
            f"(d = {bound} AND EXISTS {{ MATCH (b){lhs}[:{rels}]{rhs}() }}) AS at_frontier"
        )
        # WR-05/WR-01: `var_length_extend_max_depth` is a connection-GLOBAL config. Only raise it
        # when the requested bound exceeds the cap the connection CURRENTLY holds (a shallow walk
        # never touches tenant state). The prior value is READ before lifting and restored verbatim
        # in a `finally`, so an INJECTED tenant connection (R19, owns_conn=False) that deliberately
        # set its own non-default cap (say 100) is left EXACTLY as it was — not reset to the literal
        # default 30 (WR-01). The cap is a per-connection int; reading it is the cheap, correct way
        # to make the port's side effect truly invisible behind the seam.
        prior_cap = self._read_var_length_cap()
        lifted = bound > prior_cap
        if lifted:
            self._exec(f"CALL var_length_extend_max_depth={bound}")  # lift the cap for this walk
        try:
            rows = self._rows(self._exec(cypher, {"start": str(start)}))
        finally:
            if lifted:
                # restore the tenant's ORIGINAL cap (not a literal) so the connection is unchanged
                self._exec(f"CALL var_length_extend_max_depth={prior_cap}")
        # WR-03 (DATA-04): `max_depth=None` is "full closure", compiled to the literal
        # `_DEPTH_CEILING` hop cap. That cap is a hard TRUNCATION limit, not a true infinity — a
        # graph deeper than it would otherwise be reported as a complete closure when it is not (the
        # silent under-report DATA-04 exists to prevent). A node whose min depth equals the ceiling
        # means the walk hit that limit, so refuse to pass off a truncated set as a full closure.
        # In practice no real belief graph approaches the ceiling, so this never fires; when it
        # would, the caller gets a loud signal instead of a silently short answer. (A FINITE
        # `max_depth` surfaces truncation through the `at_frontier`/`frontier` channel instead, so
        # this guard is scoped to the unbounded case only.)
        if max_depth is None and any(r["d"] >= _DEPTH_CEILING for r in rows):
            raise RuntimeError(
                "full-closure traverse hit the internal depth ceiling "
                f"({_DEPTH_CEILING}); the cascade exceeds the adapter's unbounded-walk limit and "
                "cannot be reported as a complete closure (pass an explicit max_depth to bound it)"
            )
        reached = [{"state_id": r["state_id"]} for r in rows]
        frontier: frozenset[UUID | str] = frozenset(r["state_id"] for r in rows if r["at_frontier"])
        return reached, frontier

    @contextlib.contextmanager
    def unit_of_work(self) -> Generator[None]:
        """
        Atomic (all-or-nothing) write scope via ``BEGIN``/``COMMIT``/``ROLLBACK`` (BACK-02 / A2).

        Issues ``BEGIN TRANSACTION`` on entry; on any exception inside the block it issues
        ``ROLLBACK`` (re-raising), otherwise ``COMMIT`` (serializable WAL — verified: ROLLBACK
        discards the write). Matches the in-memory adapter's logical snapshot/restore semantics.
        """
        self._exec("BEGIN TRANSACTION")
        try:
            yield
        except BaseException:
            self._exec("ROLLBACK")
            raise
        else:
            self._exec("COMMIT")

    def _read_var_length_cap(self) -> int:
        """
        Read the connection's CURRENT ``var_length_extend_max_depth`` cap (WR-01).

        ``traverse`` lifts this connection-global setting only when a deep walk needs it, then must
        restore whatever the connection held BEFORE — not a hardcoded default — so an injected
        tenant (R19) that set its own non-default cap is left untouched behind the port. Ladybug
        exposes the live value via ``CALL current_setting('var_length_extend_max_depth') RETURN *``,
        which yields a single row ``{'var_length_extend_max_depth': '<n>'}`` with the value as a
        STRING; we coerce to ``int``. If the setting is ever absent or unreadable (it always exists
        on ladybug 0.17.1, default ``30``), fall back to :data:`_DEFAULT_HOP_CAP` so the restore
        still targets a sane value rather than raising mid-traverse.
        """
        rows = self._rows(
            self._exec("CALL current_setting('var_length_extend_max_depth') RETURN *")
        )
        if rows and "var_length_extend_max_depth" in rows[0]:
            return int(rows[0]["var_length_extend_max_depth"])
        return _DEFAULT_HOP_CAP

    def _rows(self, result: lb.QueryResult) -> list[dict[str, Any]]:
        """Extract a ``QueryResult`` as raw ``list[dict]`` (the canonical port return, D-04)."""
        # rows_as_dict() guarantees dict rows; get_all() is typed as the wider list|dict union.
        return [dict(row) for row in result.rows_as_dict().get_all()]

    def _exec(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> lb.QueryResult:
        """
        Execute a single Cypher statement and narrow the result to a single ``QueryResult``.

        ``Connection.execute`` is typed ``QueryResult | list[QueryResult]`` (the list form is
        only for multi-statement scripts, which this adapter never issues). The explicit
        ``isinstance`` narrows the union — the one genuine typing task at the driver boundary
        (Pitfall 4: ladybug ships ``py.typed``, so no missing-type-stub suppression is needed).
        A real ``raise`` (not ``assert``, WR-03) keeps the narrowing alive under ``python -O``;
        otherwise a stripped assert would let a ``list`` leak out and fail with a confusing
        ``AttributeError`` far from here.
        """
        result = self._conn.execute(cypher, parameters=parameters or {})
        if not isinstance(result, lb.QueryResult):
            raise TypeError(
                f"single-statement execute must return one QueryResult; got {type(result)!r}"
            )
        return result
