"""
STANCE-01 / STANCE-06 guards — the ordinal ``Stance`` taxonomy, type-level.

These are pure type-level unit proofs (no backend fixture): the total order is
genuine, comparison is the ONLY reachable operation (``+`` / ``*`` / cross-type
``<`` / ``>`` each raise ``TypeError``), and the serialize-via-``.name`` /
hydrate-via-``Stance[token]`` discipline holds (value-lookup on the token fails
loud). The write/persist/read round-trip lives in ``test_stance_persistence.py``.
"""

import itertools

import pytest

from doxastica.models import Stance

# Exhaustive enumeration of the 4-member domain (D-05): a complete enumeration is a
# proof, a sample is an anecdote. 16 ordered pairs, 64 ordered triples.
_PAIRS = list(itertools.product(Stance, repeat=2))  # 16
_TRIPLES = list(itertools.product(Stance, repeat=3))  # 64


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


# --- Order-law enumeration (SC2, D-04/D-05) -------------------------------------------
# The order axioms proven EXHAUSTIVELY over the whole 4-member domain, not sampled.
# ``test_stance_total_order`` above is a scaffold (one fixed chain); THESE are the laws.


@pytest.mark.parametrize("a", list(Stance))
def test_irreflexivity(a: Stance) -> None:
    # No member is strictly less/greater than itself; every member equals itself.
    assert not (a < a)
    assert not (a > a)
    assert a == a


@pytest.mark.parametrize("a,b", _PAIRS)
def test_totality_trichotomy(a: Stance, b: Stance) -> None:
    # Trichotomy: EXACTLY one of ``a < b``, ``a == b``, ``b < a`` holds for every ordered
    # pair. This single law proves totality (at least one holds) AND antisymmetry +
    # irreflexivity (at most one holds) simultaneously over all 16 pairs.
    #
    # NOTE (deliberate deviation from the plan's literal ``a > b`` term): the third term is
    # the PRIMITIVE ``b < a``, NOT the derived ``a > b``. ``@total_ordering`` synthesizes
    # ``>`` as ``not (a < b) and a != b``, so a broken ``__lt__`` (e.g. always ``False``)
    # leaves ``a > b`` reading ``a != b`` and the sum still equals 1 — the law would pass
    # VACUOUSLY against exactly the mutation SC2 says it must catch. Expressing trichotomy
    # over the primitive ``<`` in both directions makes a broken order genuinely FAIL here
    # (see test_reflected_operators_consistent for the ``>``/``>=``/``<=`` proof).
    assert (a < b) + (a == b) + (b < a) == 1


@pytest.mark.parametrize("a,b", _PAIRS)
def test_reflected_operators_consistent(a: Stance, b: Stance) -> None:
    # ``@total_ordering`` derives ``>`` / ``>=`` / ``<=`` from the single ``__lt__``; prove
    # each derived operator agrees with the primitive ``<`` for every ordered pair. A broken
    # ``__lt__`` makes the derived ``>`` diverge from ``b < a`` and FAILS here (non-vacuous).
    assert (a > b) == (b < a)
    assert (a <= b) == (a < b or a == b)
    assert (a >= b) == (b < a or a == b)


@pytest.mark.parametrize("a,b", _PAIRS)
def test_antisymmetry(a: Stance, b: Stance) -> None:
    # The named D-04 artifact — antisymmetry was literally unasserted before this.
    # a < b  ⟹  not (b < a)  and  a != b, over every ordered pair.
    if a < b:
        assert not (b < a)
        assert a != b


@pytest.mark.parametrize("a,b,c", _TRIPLES)
def test_transitivity(a: Stance, b: Stance, c: Stance) -> None:
    # a < b and b < c  ⟹  a < c, over all 64 ordered triples.
    if a < b and b < c:
        assert a < c


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
