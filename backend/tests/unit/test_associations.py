from dataclasses import replace

import pytest

from chess_review.patterns.associations import (
    Association,
    Outcome,
    adjusted_residuals,
    associate,
    expected_score,
    with_q_values,
)
from chess_review.themes.classify import pre_game_gap


def test_expected_score_is_even_at_equal_ratings_and_stronger_above() -> None:
    assert expected_score(1500, 1500) == 0.5
    assert expected_score(1900, 1500) == pytest.approx(10 / 11)


def test_residuals_are_centred_within_each_stratum() -> None:
    outcomes = [
        Outcome(1.0, 0.5, "white", {}),
        Outcome(0.0, 0.5, "white", {}),
        Outcome(1.0, 0.5, "black", {}),
        Outcome(1.0, 0.5, "black", {}),
    ]
    assert adjusted_residuals(outcomes) == [0.5, -0.5, 0.0, 0.0]


def test_a_feature_that_costs_points_has_a_negative_effect() -> None:
    harmful = [Outcome(float(i % 4 == 0), 0.5, "all", {"habit": True}) for i in range(40)]
    neutral = [Outcome(float(i % 2 == 0), 0.5, "all", {"habit": False}) for i in range(40)]
    [association] = associate(harmful + neutral)
    assert association.games_with == 40
    assert association.effect == pytest.approx(-0.25)
    assert association.score_with == pytest.approx(0.25)


def test_a_small_group_is_not_reported() -> None:
    outcomes = [Outcome(1.0, 0.5, "all", {"habit": i < 5}) for i in range(100)]
    assert associate(outcomes) == []


def test_q_values_scale_p_values_by_rank() -> None:
    base = Association("a", 40, 40, 0.5, 0.5, 0.0, 0.1, 0.01)
    adjusted = with_q_values([base, replace(base, feature="b", p_value=0.04)])
    assert {item.feature: item.q_value for item in adjusted} == {"a": 0.02, "b": 0.04}


def test_pre_game_gap_removes_the_result_from_stored_ratings() -> None:
    from datetime import UTC, datetime

    from chess_review.db import Game, Result, TimeClass

    def game(own: int, opponent: int) -> Game:
        pgn = f'[WhiteElo "{own}"]\n[BlackElo "{opponent}"]\n'
        return Game("c", "1", "me", "me", "them", Result.WIN, TimeClass.BLITZ, datetime.now(UTC), pgn)

    assert pre_game_gap(game(1510, 1490), game(1500, 1400)) == 0
