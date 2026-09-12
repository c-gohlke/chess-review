import json
from pathlib import Path

from chess_review.db import Game
from chess_review.importers.chesscom import parse_game

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "chesscom_month.json").read_text())
GAMES = FIXTURE["games"]


def test_parse_win_as_white() -> None:
    game = parse_game(GAMES[0], "alice")

    assert game == Game(
        source="chesscom",
        source_id="https://www.chess.com/game/live/1000000001",
        username="alice",
        white="alice",
        black="bobcat",
        result="win",
        time_class="blitz",
        played_at="2023-11-14T22:13:20+00:00",
        pgn=GAMES[0]["pgn"],
    )


def test_parse_loss_as_black_is_case_insensitive() -> None:
    game = parse_game(GAMES[1], "alice")

    assert game is not None
    assert game.white == "carla"
    assert game.black == "Alice"
    assert game.result == "loss"
    assert game.username == "alice"


def test_parse_draw() -> None:
    game = parse_game(GAMES[2], "alice")

    assert game is not None
    assert game.result == "draw"
    assert game.time_class == "blitz"


def test_parse_skips_variant_games() -> None:
    assert parse_game(GAMES[3], "alice") is None
