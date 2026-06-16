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

Phase 3 lands the append-only revision-spine op bodies here (the keystone): the scope
helpers, the DERIVED-current selection (D-01 — no stored ``CURRENT_STATE`` pointer), the
shared ``revise`` ≡ ``expand`` append (D-04), ``contract`` (D-05 vacuity + retracted-copy,
D-03 structural world-scope guard), and ``get_revision_chain`` (HIST-02). The remaining AGM
read surface (``query_scope`` / ``get_impact`` / ``get_scope_at``) lands in Phases 4-6. All
bodies compose ONLY the five ``BackendPort`` primitives and stay driver-blind — the opaque
``value`` is encoded ONCE on write (``_encode_value``) and decoded on hydrate
(``_decode_value``) so it round-trips byte-identically on BOTH backends (DEF-02-01). The
encoding is base64-over-JSON rather than bare ``json.dumps``: a brace/bracket-shaped JSON
string (``{"x": 2}`` / ``[1, 2, 3]``) is silently coerced by the ladybug ``STRING`` column
(it parses the literal as a STRUCT/LIST and re-stringifies, dropping the inner quotes — the
inherited brace-coercion corruption, T-03-03). base64 yields an alnum/``+/=`` token that
NEVER starts with a brace, so ladybug stores it verbatim; the in-memory backend stores it
verbatim too, keeping the two backends byte-identical. The encode/decode boundary lives here
in ``core.py`` (NOT in either adapter), applied identically on both, so the oracle stays
value-verbatim and parity holds. ``contract`` copies the already-encoded stored token
VERBATIM (no re-encode — Pitfall 2). ``json`` / ``base64`` / ``uuid`` are stdlib (allowed at
module top); the only forbidden module-level import remains ``ladybug``.
"""

from __future__ import annotations

import base64
import json
import uuid
from typing import TYPE_CHECKING, Any, cast

from doxastica.errors import WorldScopeContractionError
from doxastica.models import WORLD_SCOPE_ID, BeliefState, Scope, Status

if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from uuid import UUID

    from doxastica.ports import BackendPort
    # NOTE (D-02): do NOT import ladybug here, even under TYPE_CHECKING — the open() /
    # from_connection() factories use function-local imports to keep this module driver-blind.


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
    def _current(self, scope_id: str, belief_id: str) -> dict[str, Any] | None:
        """
        Return the DERIVED current state for ``(scope_id, belief_id)`` — or ``None`` (D-01).

        Current is the ordering-MAX state under the UUID7 ordering contract
        ``(str(source_event_id), str(state_id))`` (DATA-03 — primary key ``source_event_id``,
        ``state_id`` tiebreak) — equivalently the state with no incoming ``SUPERSEDES`` (D-04). If
        that ordering-max tail is ``retracted`` the belief has NO active current and the result is
        ``None`` (D-05: a contraction appends a retracted tail that supersedes the prior current,
        clearing it without mutating any earlier state). The max is taken over ALL statuses — NOT
        pre-filtered to ``active`` — so a retracted tail correctly clears the current rather than
        the now-superseded active state below it remaining visible. There is NO stored
        ``CURRENT_STATE`` pointer; the selection is computed over the immutable append-only states,
        scoped to the exact ``(scope, belief)`` (SCOPE-03 cross-scope divergence). The port has no
        ORDER-BY/aggregate primitive, so the max is taken core-side.
        """
        states = self._backend.match_nodes(
            "BeliefState",
            {"scope_id": scope_id, "belief_id": belief_id},
        )
        if not states:
            return None
        tail = max(states, key=_order_key)  # IN-03: the ONE ordering contract
        if tail["status"] == Status.retracted.value:  # D-05: retracted tail ⇒ no active current
            return None
        return tail

    # --- Value encode/decode boundary (DEF-02-01, identical on both backends) -
    @staticmethod
    def _encode_value(value: Any) -> str:
        """
        Encode the opaque ``value`` to a coercion-proof stored token (the write boundary).

        JSON-serialize, then base64 the UTF-8 bytes. The base64 token is alnum/``+/=`` only and
        never starts with ``{`` / ``[``, so the ladybug ``STRING`` column cannot mis-parse it as a
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
        append (Pitfall 3); mint a fresh ``state_id`` (stdlib ``uuid.uuid7()``); ``json.dumps``
        the opaque value once (DEF-02-01); append the active ``BeliefState``; lay the
        ``HAS_REVISION`` hub edge (raw string — NOT an ``EdgeType`` member, D-07); and, when a
        prior current existed, lay ``SUPERSEDES new → prior`` (raw string). Returns the hydrated
        new state.
        """
        with self._backend.unit_of_work():  # exactly one (CHAIN-03)
            self._ensure_scope(scope_id)  # D-06
            self._backend.upsert_node("Belief", belief_id, {"belief_id": belief_id})  # D-06
            prior = self._current(scope_id, belief_id)  # derived, BEFORE append (Pitfall 3)
            state_id = uuid.uuid7()
            props: dict[str, Any] = {
                "state_id": str(state_id),
                "belief_id": belief_id,
                "scope_id": scope_id,
                "source_event_id": str(source_event_id),
                "value": self._encode_value(value),  # encode once on write (DEF-02-01)
                "status": status.value,
            }
            self._backend.upsert_node("BeliefState", state_id, props)
            self._backend.add_edge("HAS_REVISION", belief_id, str(state_id))  # hub form (D-07)
            if prior is not None:
                self._backend.add_edge("SUPERSEDES", str(state_id), prior["state_id"])
            return self._hydrate(props)

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
            state_id = uuid.uuid7()
            props: dict[str, Any] = {
                "state_id": str(state_id),
                "belief_id": belief_id,
                "scope_id": scope_id,
                "source_event_id": str(source_event_id),
                "value": prior["value"],  # D-05: copy STORED form verbatim (no re-dumps, Pitfall 2)
                "status": Status.retracted.value,
            }
            self._backend.upsert_node("BeliefState", state_id, props)
            self._backend.add_edge("HAS_REVISION", belief_id, str(state_id))
            self._backend.add_edge("SUPERSEDES", str(state_id), prior["state_id"])
            return None

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
