from pathlib import Path

from chess_review.db import Game, connect, get_game, insert_games, list_games


def test_insert_games_is_idempotent(tmp_path: Path, game_1: Game, game_2: Game) -> None:
    conn = connect(tmp_path / "db.sqlite3")

    assert insert_games(conn, [game_1, game_2]) == 2
    assert insert_games(conn, [game_1, game_2]) == 0


def test_list_games_newest_first(tmp_path: Path, game_1: Game, game_2: Game) -> None:
    conn = connect(tmp_path / "db.sqlite3")
    insert_games(conn, [game_1, game_2])

    games = list_games(conn)

    assert [game.source_id for game in games] == [game_2.source_id, game_1.source_id]


def test_get_game_by_id(tmp_path: Path, game_1: Game) -> None:
    conn = connect(tmp_path / "db.sqlite3")
    insert_games(conn, [game_1])
    (stored,) = list_games(conn)

    assert stored.id is not None
    assert get_game(conn, stored.id) == stored


def test_get_missing_game_returns_none(tmp_path: Path) -> None:
    conn = connect(tmp_path / "db.sqlite3")

    assert get_game(conn, 999) is None
