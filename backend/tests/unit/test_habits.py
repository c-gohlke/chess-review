from datetime import UTC, datetime, timedelta

from chess_review.db import Game, Result, TimeClass
from chess_review.patterns.habits import base_seconds, opening_habits, session_context

SHUFFLE = " ".join(
    f"{number}. {white} {black}"
    for number, white, black in zip(
        range(2, 13),
        ["Nf3", "Ng1"] * 6,
        ["Ng8", "Nf6"] * 6,
        strict=False,
    )
)
AIMLESS = f"1. a3 Nf6 {SHUFFLE} *"
PURPOSEFUL = (
    "1. e4 e5 2. Nf3 Bb4 3. a3 Ba5 4. Ng1 Nf6 5. Nf3 Ng8 6. Ng1 Nf6 7. Nf3 Ng8 8. Ng1 Nf6 "
    "9. Nf3 Ng8 10. Ng1 Nf6 11. Nf3 Ng8 12. Ng1 Nf6 *"
)


def game(played_at: datetime, result: Result, game_id: int) -> Game:
    return Game("chess.com", str(game_id), "me", "me", "them", result, TimeClass.BLITZ, played_at, "", game_id)


def test_a3_with_nothing_on_b4_has_no_reason() -> None:
    habits = opening_habits(AIMLESS, white=True)
    assert habits is not None
    assert habits["a_pawn_no_reason"]
    assert habits["few_pawn_moves"]
    assert habits["no_pawn_past_centre"]
    assert habits["undeveloped_minors"]
    assert habits["not_castled_by_12"]


def test_a3_against_a_bishop_on_b4_has_a_reason() -> None:
    habits = opening_habits(PURPOSEFUL, white=True)
    assert habits is not None
    assert not habits["a_pawn_no_reason"]
    assert habits["rook_pawn_step"]


def test_clock_habits_compare_time_spent_with_the_opponent() -> None:
    own_clock = "{[%clk 0:02:00]}"
    enemy_clock = "{[%clk 0:03:00]}"
    moves = " ".join(
        f"{n}. Nf3 {own_clock} Nf6 {enemy_clock} {n + 1}. Ng1 {own_clock} Ng8 {enemy_clock}" for n in range(1, 25, 2)
    )
    habits = opening_habits(f'[TimeControl "180"]\n\n{moves} *', white=True)
    assert habits is not None
    assert habits["slow_opening"]
    assert habits["behind_on_clock"]
    assert not habits["instant_opening"]


def test_short_games_have_no_habits() -> None:
    assert opening_habits("1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0", white=True) is None


def test_base_seconds_reads_time_control() -> None:
    assert base_seconds('[TimeControl "180+2"]\n') == 180
    assert base_seconds('[TimeControl "1/86400"]\n') is None


def test_session_context_tracks_losses_and_resets_after_a_break() -> None:
    start = datetime(2026, 1, 1, 12, tzinfo=UTC)
    games = [
        game(start, Result.LOSS, 1),
        game(start + timedelta(minutes=5), Result.LOSS, 2),
        game(start + timedelta(minutes=10), Result.WIN, 3),
        game(start + timedelta(hours=3), Result.WIN, 4),
    ]
    context = session_context(games)
    assert context[2]["after_a_loss"]
    assert context[3]["after_two_losses"]
    assert not context[4]["after_a_loss"]
