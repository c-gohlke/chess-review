from pathlib import Path
from typing import Any

from chess_review.importers.baseline import GAMES_PER_PLAYER, band_games, band_opponents, baseline_path


def raw(
    game_id: int, opponent: str, own_rating: int, opponent_rating: int, time_class: str = "rapid", rules: str = "chess"
) -> dict[str, Any]:
    return {
        "url": f"https://www.chess.com/game/live/{game_id}",
        "pgn": "1. e4 e5",
        "time_class": time_class,
        "rules": rules,
        "end_time": 1700000000 + game_id,
        "white": {"username": "Alice", "rating": own_rating, "result": "win"},
        "black": {"username": opponent, "rating": opponent_rating, "result": "resigned"},
    }


def test_band_games_keep_rapid_games_played_while_rated_in_the_band() -> None:
    raws = [
        raw(1, "bob", 1650, 1640),
        raw(2, "carol", 1700, 1690),  # the band's upper bound is exclusive
        raw(3, "dave", 1599, 1610),
        raw(4, "erin", 1620, 1630, time_class="blitz"),
        raw(5, "frank", 1620, 1630, rules="chess960"),
    ]

    games = band_games(raws, "alice", 1600)

    assert [game.black for game in games] == ["bob"]
    assert games[0].username == "alice"


def test_band_games_take_the_most_recent_few_per_player() -> None:
    raws = [raw(game_id, "bob", 1650, 1650) for game_id in range(GAMES_PER_PLAYER + 3)]

    games = band_games(raws, "alice", 1600)

    assert [game.source_id[-1] for game in games] == [str(n) for n in range(GAMES_PER_PLAYER + 2, 2, -1)]


def test_band_opponents_are_rapid_opponents_rated_in_the_band() -> None:
    raws = [
        raw(1, "Bob", 1500, 1650),
        raw(2, "carol", 1650, 1720),
        raw(3, "dave", 1650, 1610, time_class="bullet"),
    ]

    assert band_opponents(raws, "alice", 1600) == {"bob"}


def test_baseline_lives_next_to_the_main_database() -> None:
    assert baseline_path(Path("/data/analysis.sqlite3"), 1900) == Path("/data/baseline-1900.sqlite3")
