"""
The in-memory ``BackendPort`` adapter — first-class product AND the Phase 7 oracle.

Realizes D-05 / BACK-03: a complete :class:`doxastica.ports.BackendPort` implementation
using the standard library plus pydantic only — zero extra runtime dependency. It ships as
the dependency-light default backend (``pip install doxastica``) and doubles as the
semantic ORACLE the parametrized parity suite checks the ladybug adapter against. Its
``traverse`` is the visited-set BFS the port doc names as the reference implementation; its
``(reached, frontier)`` semantics MUST equal the ladybug backend's exactly, or Phase 7's
shadow-model comparison is built on sand.

Storage is intentionally trivial: a ``dict`` of node props keyed by ``str(node_id)`` and a
``dict`` of per-edge-type adjacency lists. All node/edge keys are normalized via ``str(...)``
so ``UUID`` and ``str`` ids interoperate (the port signature is ``UUID | str``).

Model-blind below the model layer (D-04): every primitive returns raw ``list[dict]`` — no
pydantic hydration happens here. ``MemoryCore`` hydrates frozen models above the port.

This module holds NO AGM operation bodies (``revise`` / ``expand`` / ``contract`` are
Phases 3-6). It is the storage mechanism only. It imports nothing from ``ladybug`` and is
ALWAYS importable.
"""

from __future__ import annotations

import contextlib
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Generator
    from uuid import UUID

    from doxastica.models import EdgeType


class InMemoryBackend:
    """
    Stdlib + pydantic ``BackendPort`` adapter (the oracle, D-05 / BACK-03).

    Satisfies the port structurally — it implements the five LPG primitives without
    inheriting. Idempotent ``upsert_node`` / ``add_edge``, AND-exact ``match_nodes``,
    cycle-safe visited-set ``traverse``, and a snapshot/restore atomic ``unit_of_work``.
    """

    def __init__(self) -> None:
        # node label -> { str(node_id) -> props dict } ; props store node_id verbatim.
        self._nodes: dict[str, dict[str, dict[str, Any]]] = {}
        # edge type (str) -> { str(from_id) -> list[str(to_id)] } adjacency.
        self._edges: dict[str, dict[str, list[str]]] = {}
        # str(node_id) -> the original node props (label-agnostic lookup for traverse).
        self._node_index: dict[str, dict[str, Any]] = {}

    def upsert_node(
        self,
        label: str,
        node_id: UUID | str,
        props: dict[str, Any],
    ) -> None:
        """Insert-or-update a node keyed by ``node_id``; idempotent (never duplicates)."""
        key = str(node_id)
        bucket = self._nodes.setdefault(label, {})
        existing = bucket.get(key)
        if existing is None:
            stored: dict[str, Any] = dict(props)
            bucket[key] = stored
            self._node_index[key] = stored
        else:
            existing.update(props)  # SET-style merge on re-upsert.

    def add_edge(
        self,
        edge_type: EdgeType | str,
        from_id: UUID | str,
        to_id: UUID | str,
        props: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a typed directed edge; idempotent — a repeated edge yields exactly one.

        Edge properties are NOT yet implemented (IN-01): ``props`` stays in the signature for port
        parity, but a non-empty ``props`` is REJECTED with ``NotImplementedError`` rather than
        silently dropped — matching the ladybug adapter so both backends fail identically on a
        caller that expects edge properties stored.

        Endpoint-existence (D-07, oracle parity): the edge is laid ONLY when BOTH endpoints are
        already known nodes. A missing endpoint is a SILENT NO-OP — no edge, no raise — exactly
        mirroring the ladybug adapter's ``MATCH ... MERGE`` (which matches nothing, so MERGEs
        nothing, when an endpoint row is absent). Without this guard the oracle would
        unconditionally append a dangling adjacency entry to a phantom key, diverging from the
        reference backend on the documented D-07 missing-endpoint behaviour.
        """
        if props:
            raise NotImplementedError(
                "add_edge does not yet store edge properties; got non-empty props"
            )
        et = str(edge_type)
        src, dst = str(from_id), str(to_id)
        if src not in self._node_index or dst not in self._node_index:
            return  # D-07: silent no-op on a missing endpoint (mirror ladybug MATCH...MERGE)
        adjacency = self._edges.setdefault(et, {}).setdefault(src, [])
        if dst not in adjacency:
            adjacency.append(dst)

    def match_nodes(
        self,
        label: str,
        where: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Return nodes of ``label`` whose props exact-match the AND-combined ``where``."""
        bucket = self._nodes.get(label, {})
        return [
            dict(props)
            for props in bucket.values()
            if all(props.get(field) == value for field, value in where.items())
        ]

    def traverse(
        self,
        start: UUID | str,
        edge_types: frozenset[EdgeType | str],
        max_depth: int | None,
        direction: Literal["in", "out"] = "out",
    ) -> tuple[list[dict[str, Any]], frozenset[UUID | str]]:
        """
        Visited-set BFS over ``edge_types`` from ``start`` — the reference implementation.

        Returns the de-duplicated, cycle-safe set of reachable nodes (``reached``, excluding
        ``start`` itself) plus the ``frontier``: nodes at exactly ``max_depth`` that still
        have an unexpanded neighbour. ``max_depth=None`` ⇒ full transitive closure with an
        empty frontier. Terminates on cycles via the ``seen`` set.

        ``direction`` (D-05) selects the neighbour relation: ``"out"`` (default) walks edges
        FROM ``start`` (successors, via :meth:`_out_edges`); ``"in"`` walks edges INTO
        ``start`` (predecessors, via :meth:`_in_edges`) — the cascade ``get_impact`` needs.
        The layer/frontier/seen BFS logic is otherwise direction-agnostic.
        """
        start_key = str(start)
        reached: dict[str, dict[str, Any]] = {}
        frontier: set[str] = set()
        seen: set[str] = {start_key}
        layer: list[tuple[str, int]] = [(start_key, 0)]
        neighbours = self._in_edges if direction == "in" else self._out_edges

        while layer:
            nxt: list[tuple[str, int]] = []
            for node_key, depth in layer:
                for to_key in neighbours(node_key, edge_types):
                    if max_depth is not None and depth + 1 > max_depth:
                        # node_key sits at the bound with an unexpanded neighbour (a successor
                        # under direction="out", a predecessor under direction="in").
                        frontier.add(node_key)
                        continue
                    if to_key in seen:
                        continue
                    seen.add(to_key)
                    reached[to_key] = dict(self._node_index.get(to_key, {}))
                    nxt.append((to_key, depth + 1))
            layer = nxt

        return list(reached.values()), frozenset(frontier)

    @contextlib.contextmanager
    def unit_of_work(self) -> Generator[None]:
        """
        Atomic (all-or-nothing) write scope via snapshot/restore.

        Snapshots node + edge state on entry; on an exception inside the block the snapshot
        is restored (logical rollback), so partial writes never persist. On success the
        writes stay (no-op restore). The in-memory transaction is logical, matching the
        ladybug adapter's ``BEGIN``/``COMMIT``/``ROLLBACK`` semantics.
        """
        snapshot_nodes = deepcopy(self._nodes)
        snapshot_edges = deepcopy(self._edges)
        try:
            yield
        except BaseException:
            self._nodes = snapshot_nodes
            self._edges = snapshot_edges
            self._reindex()
            raise

    def _out_edges(
        self,
        node_key: str,
        edge_types: frozenset[EdgeType | str],
    ) -> list[str]:
        """Successor node keys reachable from ``node_key`` over any of ``edge_types``."""
        out: list[str] = []
        for edge_type in edge_types:
            adjacency = self._edges.get(str(edge_type), {})
            out.extend(adjacency.get(node_key, ()))
        return out

    def _in_edges(
        self,
        node_key: str,
        edge_types: frozenset[EdgeType | str],
    ) -> list[str]:
        """
        Predecessor node keys with an edge INTO ``node_key`` over any of ``edge_types``.

        The mirror of :meth:`_out_edges` for ``direction="in"`` (D-05). The edge store is
        ``edge_type -> {src -> [dst, ...]}``, so this scans each edge-type adjacency for any
        ``src`` whose destination list contains ``node_key``. The scan is O(edges) per node —
        acceptable per the D-05 discretion area for in-scope belief-graph sizes; no reverse
        index is maintained (so ``_reindex`` / ``unit_of_work`` need no extension).
        """
        out: list[str] = []
        for edge_type in edge_types:
            adjacency = self._edges.get(str(edge_type), {})
            for src, dsts in adjacency.items():
                if node_key in dsts:
                    out.append(src)
        return out

    def _reindex(self) -> None:
        """Rebuild the label-agnostic node index after a snapshot restore."""
        self._node_index = {
            key: props for bucket in self._nodes.values() for key, props in bucket.items()
        }
