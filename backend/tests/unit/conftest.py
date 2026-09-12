from datetime import UTC, datetime

import pytest

from chess_review.db import Game, Result


@pytest.fixture
def game_1() -> Game:
    return Game(
        source="chesscom",
        source_id="https://www.chess.com/game/live/1",
        username="alice",
        white="alice",
        black="bob",
        result=Result.WIN,
        time_class="blitz",
        played_at=datetime(2023, 11, 14, 22, 13, 20, tzinfo=UTC),
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
        result=Result.LOSS,
        time_class="rapid",
        played_at=datetime(2023, 11, 15, 22, 13, 20, tzinfo=UTC),
        pgn="1. d4 d5",
    )
