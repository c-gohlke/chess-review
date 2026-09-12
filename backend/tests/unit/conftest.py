import pytest

from chess_review.db import Game


@pytest.fixture
def game_1() -> Game:
    return Game(
        source="chesscom",
        source_id="https://www.chess.com/game/live/1",
        username="alice",
        white="alice",
        black="bob",
        result="win",
        time_class="blitz",
        played_at="2023-11-14T22:13:20+00:00",
        pgn="1. e4 e5",
    )


@pytest.fixture
def game_2() -> Game:
    return Game(
        source="chesscom",
        source_id="https://www.chess.com/game/live/2",
        username="alice",
        white="carla",
        black="alice",
        result="loss",
        time_class="rapid",
        played_at="2023-11-15T22:13:20+00:00",
        pgn="1. d4 d5",
    )
