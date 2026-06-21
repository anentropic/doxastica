"""
``MemoryCore`` — the backend-agnostic engine that composes a ``BackendPort`` (D-01 / D-02).

Follows the SQLAlchemy ``Engine`` pattern MINUS pool, two-tier, and registry (D-01):

- The SOLE constructor takes the PORT, never a raw connection:
  ``MemoryCore(backend: BackendPort)`` — pure dependency injection. ``MemoryCore`` is
  backend-agnostic and never holds a raw connection directly (maps to ``Engine`` holding a
  ``Dialect``). It NEVER names a backend.
- Construction is pure DI: the caller builds the backend and passes it in. ``InMemoryBackend()``
  is the zero-dependency default; ``LadybugBackend.open(path)`` /
  ``LadybugBackend.from_connection(conn)`` build the ladybug reference backend. Connection / path
  handling lives ON the backend (in ``doxastica.backends``), NEVER here — ``MemoryCore`` stays
  pure DI and never names or imports a backend.
- DROPPED from SQLAlchemy: the connection pool (the embedded reference backend is single-writer)
  and the Engine-vs-Connection two-tier (collapsed to one object; no ``core.connect()``). No
  URL/scheme registry and no plugin system (D-01a).

Driver-blind (D-02): this module imports NO driver and names NO backend. The ``BackendPort``
import is type-only (under ``TYPE_CHECKING``), used solely for the ``__init__`` annotation; there
is no module-level OR ``TYPE_CHECKING`` backend import, so importing ``MemoryCore`` never
chain-loads the optional driver. The only module that names + imports a backend driver is
``doxastica.backends.ladybug`` (a guarded module-level import, outside this blind spine).
``tests/test_import_purity.py`` proves this by scanning module-level imports only.

Phase 3 lands the append-only revision-spine op bodies here (the keystone): the scope
helpers, the DERIVED-current selection (D-01 — no stored ``CURRENT_STATE`` pointer), the
shared ``revise`` ≡ ``expand`` append (D-04), ``contract`` (D-05 vacuity + retracted-copy,
D-03 structural world-scope guard), and ``get_revision_chain`` (HIST-02). The remaining AGM
read surface (``query_scope`` / ``get_impact`` / ``get_scope_at``) lands in Phases 4-6. All
bodies compose ONLY the five ``BackendPort`` primitives and stay driver-blind — the opaque
``value`` is encoded ONCE on write (``_encode_value``) and decoded on hydrate
(``_decode_value``) so it round-trips byte-identically on BOTH backends (DEF-02-01). The
encoding is base64-over-JSON rather than bare ``json.dumps``: a brace/bracket-shaped JSON
string (``{"x": 2}`` / ``[1, 2, 3]``) is silently coerced by a graph ``STRING`` column on a
backend that parses the literal as a STRUCT/LIST and re-stringifies it, dropping the inner
quotes (the inherited brace-coercion corruption, T-03-03). base64 yields an alnum/``+/=`` token
that NEVER starts with a brace, so a STRING-column backend stores it verbatim; the in-memory
backend stores it verbatim too, keeping the two backends byte-identical. The encode/decode
boundary lives here in ``core.py`` (NOT in either adapter), applied identically on both, so the
oracle stays value-verbatim and parity holds. ``contract`` copies the already-encoded stored
token VERBATIM (no re-encode — Pitfall 2). ``json`` / ``base64`` / ``uuid`` are stdlib (allowed
at module top); the only forbidden module-level import remains the optional driver.
"""

from __future__ import annotations

import base64
import json
import uuid
from typing import TYPE_CHECKING, Any

from doxastica.errors import WorldScopeContractionError
from doxastica.models import (
    WORLD_SCOPE_ID,
    BeliefFilter,
    BeliefState,
    EdgeType,
    ImpactResult,
    Scope,
    Status,
)

if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from uuid import UUID

    from doxastica.ports import BackendPort


_CASCADE_EDGE_TYPES: frozenset[EdgeType] = frozenset({EdgeType.DEPENDS_ON, EdgeType.DERIVED_FROM})
"""
The cascade edge set ``get_impact`` traverses (D-03 — the ONE place this set is defined).

EXACTLY ``{DEPENDS_ON, DERIVED_FROM}``. ``DERIVED_FROM`` is REQUIRED — NVM's invalidation edges
(``INFERRED_FROM``/``TOLD_BY``/``WITNESSED_BY``) are all ``DERIVED_FROM`` specialisations, so
omitting it makes NVM's real cascade structurally invisible at the core level. ``SUPERSEDES`` is
EXCLUDED by construction: it is the internal revision-spine edge ``_append_state`` lays on every
``revise``/``expand``/``contract``; following it would report a belief's own version history as
"impact" for every belief.
"""


def _order_key(state: dict[str, Any]) -> tuple[str, str]:
    """
    The ONE UUID7 ordering contract — ``(str(source_event_id), str(state_id))`` (IN-03).

    Centralized here so ``_current`` (the ordering-``max``) and ``get_revision_chain`` (the full
    ``sort``) cannot drift apart: they MUST agree on the primary key (``source_event_id``) and the
    ``state_id`` tiebreak, or the derived-current selection would desynchronise from the history
    chain (DATA-03 / the keystone invariant). Previously the lambda was written inline in two
    places; this is now the single definition both call.
    """
    return (str(state["source_event_id"]), str(state["state_id"]))


def _is_active_tail(tail: dict[str, Any]) -> bool:
    """
    The ONE "retracted tail ⇒ absent" rule — ``True`` iff ``tail`` is not a retracted winner.

    Sibling to ``_order_key``: the ordering contract picks the winner, this predicate decides
    whether that winner clears the belief. Centralized here so ``_current`` (the "now" collapse)
    and ``get_scope_at`` (the same collapse over the as-of cut window) cannot drift apart — both
    implement the identical D-05/D-06 rule that an ordering-max tail with ``status == retracted``
    means the belief has NO active state and is absent. Comparison form is byte-identical to the
    prior inline sites (raw ``!= Status.retracted.value`` on the stored token); under the closed
    ``{active, retracted}`` taxonomy (DATA-06) this is exactly equivalent to ``Status(...) in
    {active}``.
    """
    return tail["status"] != Status.retracted.value


def _current_tails(
    rows: list[dict[str, Any]],
    allowed: frozenset[Status],
) -> dict[str, dict[str, Any]]:
    """
    Group already-scoped ``rows`` by ``belief_id`` → per-belief ordering-MAX → status filter.

    The pure, driver-blind heart of the derived-current pipeline (D-01a): the ONE
    group-by-``belief_id`` + per-group ``_order_key`` ordering-MAX (over ALL statuses) + status
    filter, single-sourced so ``query_scope`` and the Wave-2 diverging-beliefs join cannot drift
    on the ``_order_key`` contract. ``rows`` is the already scope-filtered ``match_nodes`` scan;
    ``allowed`` is the resolved status set. Returns ``{belief_id: tail}`` — the per-belief current
    tail surviving the status filter, keyed by ``belief_id``.

    CRITICAL (Pitfall 2): the status filter runs AFTER the per-belief max, NEVER before —
    pre-filtering to ``active`` would leak a stale active value below a retracted ordering-max tail.
    The max is taken status-AGNOSTICALLY first; only the surviving winner is then status-filtered.

    Driver-blind: composes ONLY stdlib + the module-level ``_order_key`` / ``Status`` (no
    driver import, no Cypher), so ``tests/test_import_purity.py`` stays green (T-07-01).
    """
    by_belief: dict[str, dict[str, Any]] = {}
    for row in rows:
        current = by_belief.get(row["belief_id"])
        if current is None or _order_key(row) > _order_key(current):
            by_belief[row["belief_id"]] = row  # the status-agnostic current tail
    # status filter AFTER the max (Pitfall 2) — Status(...) rebuilds the enum (like hydrate)
    return {
        belief_id: tail
        for belief_id, tail in by_belief.items()
        if Status(tail["status"]) in allowed
    }


class MemoryCore:
    """
    Backend-agnostic AGM engine composing a :class:`doxastica.ports.BackendPort` (D-01).

    The SOLE constructor is ``__init__(backend: BackendPort)`` — pure dependency injection over an
    already-built port; it never names a backend or takes a raw connection. The caller builds the
    backend and injects it: ``MemoryCore(InMemoryBackend())`` for the zero-dependency default, or
    ``MemoryCore(LadybugBackend.open(path))`` / ``MemoryCore(LadybugBackend.from_connection(conn))``
    for the ladybug reference backend. Backend construction lives ON the backend classes (in
    ``doxastica.backends``), so this class stays driver-blind (D-02).
    """

    def __init__(self, backend: BackendPort) -> None:
        """Wrap an already-built ``BackendPort`` (D-01: the port, never a raw connection)."""
        self._backend = backend

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
    def _current_tail(self, scope_id: str, belief_id: str) -> dict[str, Any] | None:
        """
        Return the status-AGNOSTIC ordering-MAX tail for ``(scope_id, belief_id)`` — or ``None``.

        The raw derived current tail under the UUID7 ordering contract
        ``(str(source_event_id), str(state_id))`` (DATA-03 — primary key ``source_event_id``,
        ``state_id`` tiebreak), taken over ALL statuses — BEFORE the retracted→``None`` collapse.
        ``_current`` applies that collapse on top (write-side: a retracted tail means NO ACTIVE
        current, D-05); ``query_scope`` needs THIS raw tail so ``include_retracted=True`` can
        surface a belief whose current tail is ``retracted`` (D-02). Reuses the ONE ``_order_key``
        contract — never a second ordering (D-07) — so the read surface cannot desynchronise from
        the write spine. There is NO stored ``CURRENT_STATE`` pointer; the selection is computed
        over the immutable append-only states, scoped to the exact ``(scope, belief)``. The port
        has no ORDER-BY/aggregate primitive, so the max is taken core-side.
        """
        states = self._backend.match_nodes(
            "BeliefState",
            {"scope_id": scope_id, "belief_id": belief_id},
        )
        if not states:
            return None
        return max(states, key=_order_key)  # IN-03: the ONE ordering contract

    def _current(self, scope_id: str, belief_id: str) -> dict[str, Any] | None:
        """
        Return the DERIVED ACTIVE current state for ``(scope_id, belief_id)`` — or ``None`` (D-01).

        Delegates the ordering-MAX selection to the status-agnostic ``_current_tail`` (the ONE
        ordering contract lives there), then applies ONLY the retracted→``None`` collapse on top: if
        the ordering-max tail is ``retracted`` the belief has NO active current and the result is
        ``None`` (D-05: a contraction appends a retracted tail that supersedes the prior current,
        clearing it without mutating any earlier state). Taking the max over ALL statuses (in
        ``_current_tail``) — NOT pre-filtering to ``active`` — is what lets a retracted tail
        correctly clear the current rather than the now-superseded active state below it remaining
        visible. This is the unchanged Phase-3 write-side contract every ``revise``/``expand``/
        ``contract`` ``prior`` computation depends on.
        """
        tail = self._current_tail(scope_id, belief_id)
        if tail is None or not _is_active_tail(tail):
            return None  # D-05: retracted tail ⇒ no active current (the ONE active-tail predicate)
        return tail

    # --- Value encode/decode boundary (DEF-02-01, identical on both backends) -
    @staticmethod
    def _encode_value(value: Any) -> str:
        """
        Encode the opaque ``value`` to a coercion-proof stored token (the write boundary).

        JSON-serialize, then base64 the UTF-8 bytes. The base64 token is alnum/``+/=`` only and
        never starts with ``{`` / ``[``, so a graph ``STRING`` column cannot mis-parse it as a
        STRUCT/LIST literal (the inherited brace-coercion corruption, T-03-03 / DEF-02-01). Applied
        identically on both backends, so the stored form is byte-identical everywhere.
        """
        return base64.b64encode(json.dumps(value).encode("utf-8")).decode("ascii")

    @staticmethod
    def _decode_value(stored: str) -> Any:
        """Inverse of :meth:`_encode_value` — base64-decode then ``json.loads`` (read boundary)."""
        return json.loads(base64.b64decode(stored.encode("ascii")).decode("utf-8"))

    def _hydrate(self, props: dict[str, Any]) -> BeliefState:
        """
        Build a frozen ``BeliefState`` from raw port props — the value-decode boundary.

        Inverse of the ``_encode_value`` write encode: ``value`` is decoded back to the opaque
        object; pydantic coerces the ``state_id`` / ``source_event_id`` strings to ``UUID`` at the
        seam, and ``status`` is rebuilt as a ``Status`` member.
        """
        return BeliefState(
            state_id=props["state_id"],
            belief_id=props["belief_id"],
            scope_id=props["scope_id"],
            source_event_id=props["source_event_id"],
            value=self._decode_value(props["value"]),
            status=Status(props["status"]),
        )

    # --- Shared revise/expand append (D-04) ---------------------------------
    def _append_state(
        self,
        scope_id: str,
        belief_id: str,
        encoded_value: str,
        source_event_id: UUID,
        status: Status,
        prior: dict[str, Any] | None,
    ) -> BeliefState:
        """
        The shared node + edge-laying body for ``_append`` and ``contract`` (IN-02, D-07).

        Mints a fresh ``state_id`` (stdlib ``uuid.uuid7()``); builds the ``BeliefState`` props with
        the ALREADY-ENCODED ``value`` (the caller owns the encode policy — ``_append`` passes
        ``_encode_value(value)``; ``contract`` passes the prior STORED token VERBATIM, Pitfall 2);
        upserts the ``BeliefState``; lays the ``HAS_REVISION`` hub edge (raw string — NOT an
        ``EdgeType`` member, D-07); and, when ``prior`` is non-``None``, lays ``SUPERSEDES new →
        prior`` (raw string). Returns the hydrated new state. Centralizing this body means a future
        fix to the ``HAS_REVISION``/``SUPERSEDES`` wiring lands in ONE place, not two that drift.

        The caller owns everything that genuinely differs between the two ops: the enclosing
        ``unit_of_work``, the scope/``Belief`` materialization order, the vacuity probe, and how
        ``prior`` is computed — so this helper is behavior-preserving for both call sites.
        """
        state_id = uuid.uuid7()
        props: dict[str, Any] = {
            "state_id": str(state_id),
            "belief_id": belief_id,
            "scope_id": scope_id,
            "source_event_id": str(source_event_id),
            "value": encoded_value,  # caller-supplied stored form (encode policy is the caller's)
            "status": status.value,
        }
        self._backend.upsert_node("BeliefState", state_id, props)
        self._backend.add_edge("HAS_REVISION", belief_id, str(state_id))  # hub form (D-07)
        if prior is not None:
            self._backend.add_edge("SUPERSEDES", str(state_id), prior["state_id"])
        return self._hydrate(props)

    def _append(
        self,
        scope_id: str,
        belief_id: str,
        value: Any,
        source_event_id: UUID,
        status: Status,
    ) -> BeliefState:
        """
        The shared ``revise`` ≡ ``expand`` body (D-04) — one append, inside ONE unit_of_work.

        Steps (CHAIN-02/03, D-06, D-07, DEF-02-01), all composing the port primitives:
        auto-create the scope and ``Belief`` node (D-06); compute ``prior`` BEFORE the new
        append (Pitfall 3); ``json.dumps`` the opaque value once (DEF-02-01); then delegate the
        node + ``HAS_REVISION`` + optional ``SUPERSEDES`` body to the shared ``_append_state``
        helper (IN-02). Returns the hydrated new state.
        """
        with self._backend.unit_of_work():  # exactly one (CHAIN-03)
            self._ensure_scope(scope_id)  # D-06
            self._backend.upsert_node("Belief", belief_id, {"belief_id": belief_id})  # D-06
            prior = self._current(scope_id, belief_id)  # derived, BEFORE append (Pitfall 3)
            return self._append_state(
                scope_id,
                belief_id,
                self._encode_value(value),  # encode once on write (DEF-02-01)
                source_event_id,
                status,
                prior,
            )

    # --- Core belief operations ---------------------------------------------
    def revise(
        self,
        scope_id: str,
        belief_id: str,
        value: Any,
        source_event_id: UUID,
    ) -> BeliefState:
        """AGM revision: append a new active ``BeliefState`` for ``belief_id`` (OPS-01)."""
        return self._append(scope_id, belief_id, value, source_event_id, Status.active)

    def expand(
        self,
        scope_id: str,
        belief_id: str,
        value: Any,
        source_event_id: UUID,
    ) -> BeliefState:
        """
        AGM expansion — MECHANICALLY IDENTICAL to ``revise`` (D-04, OPS-02).

        A one-line delegate to the shared ``_append`` (not a bare ``expand = revise`` class-body
        alias) so basedpyright-strict keeps the bound-method type; both names stay on the public
        surface (``protocol.py`` requires both; Phase 7 exercises both AGM families).
        """
        return self._append(scope_id, belief_id, value, source_event_id, Status.active)

    def contract(
        self,
        scope_id: str,
        belief_id: str,
        source_event_id: UUID,
    ) -> None:
        """
        AGM contraction (OPS-03, D-03/D-05): structural world-scope guard, vacuity, retracted-copy.

        The world-scope guard (D-03) is the FIRST statement — it fires BEFORE ``unit_of_work`` and
        before any backend access, so ``contract(WORLD_SCOPE_ID, …)`` leaks no write even if the
        world node was never created. Otherwise, inside ONE unit_of_work: probe the prior current
        FIRST (a read-only ``_current``); if absent, return ``None`` (D-05 vacuity — a TRUE silent
        no-op that leaks NO write, scope node included — WR-01); else materialise the scope (D-06)
        and append exactly one ``retracted`` state copying the prior STORED value VERBATIM (already
        json-encoded — do NOT re-encode, Pitfall 2) and lay ``HAS_REVISION`` + ``SUPERSEDES
        new(retracted) → prior``. Always returns ``None``.

        Ordering note (WR-01): the world-scope structural guard (D-03) stays FIRST, before the
        vacuity probe and before any backend access — only AFTER it passes do we read ``_current``,
        and only AFTER a non-vacuous probe do we ``_ensure_scope``. ``_current`` is read-only, so
        probing before scope creation is safe and a vacuous contract on an absent belief/scope is a
        genuine no-op (no ``Scope`` node leaks).
        """
        if scope_id == WORLD_SCOPE_ID:  # D-03 STRUCTURAL guard, before any backend access
            raise WorldScopeContractionError(
                "contract() is forbidden on the privileged world scope"
            )
        with self._backend.unit_of_work():  # exactly one (CHAIN-03)
            # WR-01: probe vacuity BEFORE creating the scope — `_current` only reads, so a vacuous
            # contract on an absent belief leaks NO write (Scope node included). D-03 guard above
            # still fires first; this only reorders the scope-create relative to the vacuity check.
            prior = self._current(scope_id, belief_id)
            if prior is None:
                return None  # D-05 vacuity: genuine silent no-op, no Scope/BeliefState write
            self._ensure_scope(scope_id)  # D-06 — only materialise the scope on the acting branch
            # IN-02: delegate the node + HAS_REVISION + SUPERSEDES body to the shared helper,
            # passing the prior STORED value VERBATIM (already encoded — no re-encode, Pitfall 2).
            self._append_state(
                scope_id,
                belief_id,
                prior["value"],  # D-05: copy STORED form verbatim (no re-dumps, Pitfall 2)
                source_event_id,
                Status.retracted,
                prior,
            )

    # --- Edge operations ----------------------------------------------------
    def add_edge(
        self,
        from_state_id: UUID,
        to_state_id: UUID,
        edge_type: EdgeType,
    ) -> None:
        """
        Lay a consumer-facing typed edge between two belief states (EDGE-01, D-06/D-07).

        A near-passthrough to the backend's idempotent ``add_edge`` primitive wrapped in exactly
        ONE ``unit_of_work`` (D-06): the core adds nothing beyond the passthrough. Idempotency
        (double-add ⇒ one edge) is ALREADY guaranteed by both backends, so the core does NOT
        re-implement it. The public signature takes the CLOSED ``EdgeType`` enum — only the three
        generic types (``SUPERSEDES``/``DEPENDS_ON``/``DERIVED_FROM``) are layable via this seam;
        the structural ``HAS_REVISION``/internal-``SUPERSEDES`` wiring stays inside
        ``_append_state``. basedpyright-strict rejects a raw string at this boundary (T-05-04).

        D-07 (mechanism, not policy): NO endpoint-existence validation. The port's
        ``MATCH ... MERGE`` silently no-ops if an endpoint is missing — the edge simply is not
        laid and NOTHING is raised. This is the INTENDED behaviour, pinned by
        ``test_add_edge_missing_endpoint_is_silent_no_op``; the core adds no raise.

        Both UUIDs are stringified (``str(...)``) so they match the stored STRING PKs on a
        STRING-keyed backend — the same UUID-at-the-boundary convention every other backend call
        in this module follows (``_append_state`` precedent). Driver-blind (D-02): no Cypher, no
        driver import; the backend owns the edge storage.
        """
        with self._backend.unit_of_work():  # exactly one atomic scope (D-06)
            # passthrough — the port MERGE is idempotent and silently no-ops on a missing
            # endpoint (D-07). Arg order is (edge_type, from_id, to_id) per the port contract.
            self._backend.add_edge(edge_type, str(from_state_id), str(to_state_id))

    # --- Cascade ------------------------------------------------------------
    def get_impact(
        self,
        belief_state_id: UUID,
        depth: int | None = None,
    ) -> ImpactResult:
        """
        Return the dependency cascade reachable from ``belief_state_id`` (EDGE-02, D-01..D-05).

        ``get_impact(X)`` returns the transitive set of ``BeliefState``s that DEPEND ON ``X`` — its
        downstream dependents (D-01), the contraction-cascade impact set a consumer marks for
        revision. It is called ON the retracted/contracted node and returns what is AFFECTED; it
        does NOT return "what ``X`` depends on." The walk runs over EXACTLY
        ``_CASCADE_EDGE_TYPES`` = ``{DEPENDS_ON, DERIVED_FROM}`` (D-03 — ``SUPERSEDES`` excluded),
        in the ``direction="in"`` sense (D-04/D-05): the core's edge-storage convention is
        dependent → source, so the impact walk runs AGAINST the arrows (INTO ``X``). ``reached``
        EXCLUDES ``X`` itself (D-02 — the port ``traverse`` contract already excludes the start).

        ``depth=None`` (default) walks to full transitive closure with an empty frontier and
        ``truncated=False``; a finite ``depth`` bounds the BFS and ``truncated = len(frontier) >
        0`` — so a bounded cascade can never silently under-report (DATA-04). ``depth=0`` ⇒ empty
        ``reached`` with ``X`` on the frontier (when it has an in-edge). The walk is cycle-safe and
        de-duplicating (inherited from the ``traverse`` visited-set), so a cyclic dependency graph
        terminates.

        HYDRATION GAP (RESEARCH Pitfall 1, the single most likely parity bug): the reference
        ``traverse`` returns ``reached`` rows shaped ``{"state_id": ...}`` ONLY, while the in-memory
        backend returns full props — so ``reached`` CANNOT be hydrated directly (``_hydrate`` needs
        all six ``BeliefState`` fields). Option A (driver-blind, parity-clean): take each reached
        row's ``state_id`` and RE-FETCH its full props via the already-parity-tested
        ``match_nodes("BeliefState", {"state_id": sid})``, then ``_hydrate`` — identical on both
        backends. A re-fetch that returns nothing is skipped defensively (it should not happen for a
        reached node; the core does not raise).

        ATOMIC READ SCOPE (WR-02): the ``traverse`` + the per-reached-node ``match_nodes`` re-fetch
        loop run inside ONE ``unit_of_work`` so they share a single serializable snapshot. Without
        it, the re-fetches are N separate auto-committed reads on the reference backend, and the
        single-writer model permits a concurrent append BETWEEN two of them — yielding a
        ``reached``/``frontier`` pair that never existed at a single instant. Wrapping a pure READ
        in ``unit_of_work`` is safe on both backends: the reference backend runs a
        ``BEGIN``/``COMMIT`` with no writes, and the in-memory adapter snapshots on entry and
        (absent an exception) leaves state untouched on exit. Driver-blind (D-02): NO Cypher, NO
        driver import, NO ``direction``
        logic — the core composes only ``unit_of_work`` / ``traverse`` / ``match_nodes`` and passes
        the literal ``direction="in"`` so both backends own the arrow flip. The hydrated ``reached``
        tuple is sorted by the ONE ``_order_key`` contract for deterministic output (``reached``
        order is non-contractual per BACK-04 §5, but determinism keeps cross-backend parity
        assertions stable).
        """
        # WR-02: one read snapshot covers BOTH the traverse and every re-fetch, so the hydrated
        # `reached` set is consistent with the `frontier` the traverse derived (no interleaved
        # write).
        with self._backend.unit_of_work():
            reached_rows, frontier = self._backend.traverse(
                str(belief_state_id),  # stringify to match the stored STRING PKs
                _CASCADE_EDGE_TYPES,  # D-03 — SUPERSEDES excluded by construction
                depth,  # depth=None ⇒ full closure, empty frontier (D-02)
                direction="in",  # D-04/D-05: walk AGAINST the arrows (X's dependents)
            )
            # close the hydration gap (Option A): re-fetch full props per reached state_id, then
            # _hydrate — both backends agree because match_nodes props are already parity-tested.
            props: list[dict[str, Any]] = []
            for row in reached_rows:
                fetched = self._backend.match_nodes(
                    "BeliefState", {"state_id": str(row["state_id"])}
                )
                # IN-01: traverse only reaches REAL nodes via REAL edges, so an empty re-fetch is
                # a reached/store divergence (the parity invariant the hydration guard exists to
                # protect) — fail loud rather than silently dropping it and hiding the breach.
                if not fetched:
                    raise RuntimeError(
                        f"reached state_id {row['state_id']!r} has no stored BeliefState node "
                        "(reached/store divergence)"
                    )
                props.append(fetched[0])
        props.sort(key=_order_key)  # deterministic order (reuse the ONE ordering contract)
        # the port frontier carries opaque state_id handles (str on both backends); coerce each to
        # UUID for the typed ImpactResult.frontier (frozenset[UUID]) — uuid.UUID(str(...)) is the
        # str→UUID boundary, identical to pydantic's seam coercion on the hydrated reached states.
        return ImpactResult(
            reached=tuple(self._hydrate(p) for p in props),  # excludes start X (D-02)
            frontier=frozenset(uuid.UUID(str(f)) for f in frontier),
            truncated=len(frontier) > 0,  # D-02 derivation
        )

    # --- History ------------------------------------------------------------
    def get_revision_chain(self, belief_id: str) -> list[BeliefState]:
        """
        Return every ``BeliefState`` for ``belief_id`` (cross-scope) in ordering order (HIST-02).

        Cross-scope by signature (Open Q2 A2 — only ``belief_id``); ordered by the same UUID7
        contract as ``_current`` (``(source_event_id, state_id)``) but a full ``sort`` rather than
        a ``max``. The chain is the immutable append-only history (D-07).
        """
        states = self._backend.match_nodes("BeliefState", {"belief_id": belief_id})
        states.sort(key=_order_key)  # IN-03: the same ONE ordering contract as `_current`
        return [self._hydrate(s) for s in states]

    # --- Observation surface (the AGM belief base B, observed "as of now") ----
    def query_scope(
        self,
        scope_id: str,
        belief_filter: BeliefFilter,
        include_retracted: bool = False,
    ) -> list[BeliefState]:
        """
        Return the current belief base of ``scope_id`` under ``belief_filter`` (HIST-01).

        ``query_scope`` *is* the AGM belief base B observed "as of now": exactly ONE current tail
        per ``(scope, belief)`` (D-01 — never the full history; the no-duplicate property falls out
        of the per-belief ordering-max, not a dedup pass), never a superseded (non-tail) state
        (D-05). A single scope-wide ``match_nodes`` scan → group-by-``belief_id`` → per-group
        ordering-MAX (the status-agnostic current tail) → status filter → ``belief_ids`` narrow →
        event-range post-filter → ``_order_key`` sort → ``_hydrate``.

        The status set resolves with the locked precedence (D-02/D-03): an explicit
        ``belief_filter.status`` GOVERNS; otherwise ``include_retracted`` is sugar —
        ``False`` ≡ ``{active}``, ``True`` ≡ ``{active, retracted}``. The status filter runs AFTER
        the per-belief max (Pitfall 2: pre-filtering to ``active`` would leak a stale active value
        below a retracted tail).

        ``event_id_min``/``event_id_max`` POST-FILTER the derived tails inclusively (D-06, A1): a
        belief whose current tail is newer than ``event_id_max`` is simply ABSENT — never rewound to
        an older value (that is ``get_scope_at``, Phase 6). Comparison is str-vs-str, the SAME form
        ``_order_key`` uses (Pitfall 3 — never str-vs-UUID).

        A pure read (D-08): a non-existent or empty scope returns ``[]`` and creates NO ``Scope``
        node — no ``_ensure_scope``, no ``unit_of_work``, no error surface. Consumes ONLY the four
        closed ``BeliefFilter`` fields (DATA-02 — no free query string).
        """
        # 1. resolve the allowed status set — explicit filter.status WINS over the flag (D-02/D-03)
        if belief_filter.status is not None:
            allowed = belief_filter.status
        else:
            allowed = (
                frozenset({Status.active, Status.retracted})
                if include_retracted
                else frozenset({Status.active})
            )
        # 2. ONE scope-wide round-trip; absent scope → [] (D-08: pure read, no auto-create)
        rows = self._backend.match_nodes("BeliefState", {"scope_id": scope_id})
        # 3+4. group by belief_id → per-belief ordering-MAX over ALL statuses → status filter AFTER
        #      the max (Pitfall 2), single-sourced in the pure `_current_tails` helper (D-01a) so
        #      this read surface and the Wave-2 diverging-beliefs join share the ONE `_order_key`.
        tails = list(_current_tails(rows, allowed).values())
        # 5. belief_ids narrowing
        if belief_filter.belief_ids is not None:
            tails = [t for t in tails if t["belief_id"] in belief_filter.belief_ids]
        # 6. event-range POST-filter (D-06: drop, never rewind) — str-vs-str, inclusive (Pitfall 3)
        if belief_filter.event_id_min is not None:
            event_min = str(belief_filter.event_id_min)
            tails = [t for t in tails if t["source_event_id"] >= event_min]
        if belief_filter.event_id_max is not None:
            event_max = str(belief_filter.event_id_max)
            tails = [t for t in tails if t["source_event_id"] <= event_max]
        # 7. deterministic order (D-07: reuse the ONE _order_key) then 8. hydrate
        tails.sort(key=_order_key)
        return [self._hydrate(t) for t in tails]

    # --- Temporal reconstruction (HIST-03) -----------------------------------
    def get_scope_at(
        self,
        scope_id: str,
        as_of_event_id: UUID,
    ) -> list[BeliefState]:
        """
        Reconstruct the active belief base of ``scope_id`` AS OF ``as_of_event_id`` (HIST-03).

        The temporal sibling of ``query_scope`` with ONE structural change (D-02/D-03): the
        inclusive ``source_event_id <= as_of`` CUT is applied to the candidate states BEFORE the
        per-belief ordering-MAX (cut-then-max = REWIND), in place of ``query_scope``'s
        ``event_id_max`` POST-filter on derived tails (max-then-filter = DROP). So an OLDER value
        RESURFACES for a since-revised belief — the value current AT the cut — rather than the
        belief going absent. Conflating this cut with ``query_scope``'s ``event_id_max`` is the
        central trap of the phase (D-03): the placement of the cut relative to the max is the whole
        difference.

        Pipeline: ONE scope-wide ``match_nodes`` scan → INCLUSIVE ``<= as_of`` cut as a PRE-filter
        inside the group-by loop → per-group ``_order_key`` ordering-MAX over the surviving rows
        (the cut-window current tail, ``state_id``-tiebroken, D-05) → retracted-as-of collapse
        (D-06: a belief whose as-of tail is ``retracted`` is ABSENT — the ``_current`` rule computed
        over the cut window, not "now") → ``_order_key`` sort → ``_hydrate``. There is NO
        ``include_retracted`` flag and NO status-set resolution; the base is always active-as-of.

        The cut is INCLUSIVE (D-04): a state whose ``source_event_id == as_of`` IS included — this
        is what makes ``get_scope_at(latest) == query_scope(current)`` hold (SC1). Comparison is
        ``str``-vs-``str`` on ``source_event_id`` (normalized ONCE to the SAME form ``_order_key``
        uses — never ``str``-vs-``UUID``, Pitfall 2). The ONE ``_order_key`` contract is reused for
        the cut key form, the per-group max, and the final sort — never a second ordering (D-05).

        A single multi-belief event shares one ``source_event_id``, so the inclusive cut folds ALL
        of that event's writes into the base, tiebroken by ``state_id``.

        A pure read (D-08): a non-existent or empty scope returns ``[]`` and creates NO ``Scope``
        node — no ``_ensure_scope``, no ``unit_of_work``, no world-scope guard
        (``get_scope_at(world, e)`` is a valid read). Composes ONLY ``match_nodes`` — no
        ``traverse``, no edge walk: the chain order is implicit in the
        ``(source_event_id, state_id)`` ordering (D-01).
        """
        # Normalize the cut bound ONCE to the _order_key str form (D-04: never str-vs-UUID).
        as_of = str(as_of_event_id)
        # 1. ONE scope-wide round-trip; absent scope → [] (D-08: pure read, no auto-create)
        #    WR-01 snapshot invariant: this is a SINGLE `match_nodes` ⇒ one auto-committed snapshot,
        #    so no `unit_of_work` is needed (cf. `get_impact`'s WR-02 wrap, which is required only
        #    because it makes MORE THAN ONE backend call). If a second backend call is ever added
        #    here (e.g. a scope-existence probe, or splitting the scan), wrap BOTH in
        #    `self._backend.unit_of_work()` per WR-02 — otherwise a concurrent append on a
        #    single-writer backend can land between the two auto-committed reads and break the
        #    single-snapshot guarantee with no compile-time signal.
        rows = self._backend.match_nodes("BeliefState", {"scope_id": scope_id})
        # 2. INCLUSIVE cut as a PRE-filter, then per-group ordering-MAX over the surviving rows.
        #    The cut runs BEFORE the max (cut-then-max = REWIND, D-02/D-03) — NOT a post-filter on
        #    derived tails (that is query_scope's DROP). This placement is the whole phase.
        by_belief: dict[str, dict[str, Any]] = {}
        for row in rows:
            if row["source_event_id"] > as_of:  # D-04 inclusive cut: keep <= as_of, drop newer
                continue
            current = by_belief.get(row["belief_id"])
            if current is None or _order_key(row) > _order_key(current):
                by_belief[row["belief_id"]] = row  # cut-window status-agnostic tail (D-05 tiebreak)
        # 3. retracted-as-of collapse (D-06: the _current rule over the cut window, not "now")
        tails = [t for t in by_belief.values() if _is_active_tail(t)]
        # 4. deterministic order (D-05: reuse the ONE _order_key) then 5. hydrate
        tails.sort(key=_order_key)
        return [self._hydrate(t) for t in tails]
