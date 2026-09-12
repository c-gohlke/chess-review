from pathlib import Path

from chess_review.db import Game, connect, get_game, insert_games, list_games

GAME_1 = Game(
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
GAME_2 = Game(
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


def test_insert_games_is_idempotent(tmp_path: Path) -> None:
    conn = connect(tmp_path / "db.sqlite3")

    assert insert_games(conn, [GAME_1, GAME_2]) == 2
    assert insert_games(conn, [GAME_1, GAME_2]) == 0


def test_list_games_newest_first(tmp_path: Path) -> None:
    conn = connect(tmp_path / "db.sqlite3")
    insert_games(conn, [GAME_1, GAME_2])

    games = list_games(conn)

    assert [game.source_id for game in games] == [GAME_2.source_id, GAME_1.source_id]


def test_get_game_by_id(tmp_path: Path) -> None:
    conn = connect(tmp_path / "db.sqlite3")
    insert_games(conn, [GAME_1])
    (stored,) = list_games(conn)

    assert stored.id is not None
    assert get_game(conn, stored.id) == stored


def test_get_missing_game_returns_none(tmp_path: Path) -> None:
    conn = connect(tmp_path / "db.sqlite3")

    assert get_game(conn, 999) is None
