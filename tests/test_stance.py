"""
STANCE-01 / STANCE-06 guards — the ordinal ``Stance`` taxonomy, type-level.

These are pure type-level unit proofs (no backend fixture): the total order is
genuine, comparison is the ONLY reachable operation (``+`` / ``*`` / cross-type
``<`` / ``>`` each raise ``TypeError``), and the serialize-via-``.name`` /
hydrate-via-``Stance[token]`` discipline holds (value-lookup on the token fails
loud). The write/persist/read round-trip lives in ``test_stance_persistence.py``.
"""

import pytest

from doxastica.models import Stance


def test_stance_total_order() -> None:
    # STANCE-01: a genuine total order doubted < suspected < believed < certain.
    assert Stance.doubted < Stance.suspected < Stance.believed < Stance.certain
    # total_ordering synthesizes the reflected operators from the single __lt__.
    assert Stance.certain > Stance.doubted
    assert Stance.certain >= Stance.certain
    assert Stance.doubted <= Stance.certain
    # sortability follows from the total order (rank-ordered, not lexical/name order).
    assert sorted([Stance.certain, Stance.doubted]) == [Stance.doubted, Stance.certain]


def test_stance_membership_is_exactly_the_four_ranks() -> None:
    assert set(Stance) == {
        Stance.doubted,
        Stance.suspected,
        Stance.believed,
        Stance.certain,
    }


def test_stance_arithmetic_and_cross_type_raise() -> None:
    # STANCE-06: comparison is the ONLY reachable operation. The plain-Enum base leaves no
    # numeric protocol (so `+` / `*` raise), and __lt__ returns NotImplemented for a
    # non-Stance operand (so cross-type `<` / `>` raise) — all TypeError at the type level.
    # basedpyright-strict statically rejects each of these operations; that static rejection
    # is itself part of the STANCE-06 guarantee, hence the narrow per-line ignores.
    with pytest.raises(TypeError):
        _ = Stance.certain + Stance.doubted  # pyright: ignore[reportOperatorIssue, reportUnknownVariableType]
    with pytest.raises(TypeError):
        _ = Stance.certain * 2  # pyright: ignore[reportOperatorIssue, reportUnknownVariableType]
    with pytest.raises(TypeError):
        _ = Stance.believed < 5  # pyright: ignore[reportOperatorIssue]
    with pytest.raises(TypeError):
        _ = Stance.believed > 5  # pyright: ignore[reportOperatorIssue]


def test_stance_hydration_is_name_based() -> None:
    # Guards Pitfall 1 directly: the wire form is the .name token, so hydration MUST be
    # name-lookup. Value-lookup on the token fails because .value is the integer rank.
    assert Stance["certain"] is Stance.certain
    with pytest.raises(ValueError, match="certain"):
        Stance("certain")  # value-lookup on the token must fail — proves the .name discipline


def test_stance_name_is_the_wire_token() -> None:
    # The serialized wire form is the .name token; the integer .value is the rank
    # (used only inside __lt__), never the persisted form.
    assert Stance.certain.name == "certain"
    assert Stance.certain.value == 3
    assert Stance(3) is Stance.certain  # value-lookup by rank works; by token does not
