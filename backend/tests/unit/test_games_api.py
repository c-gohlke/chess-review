from pathlib import Path

from fastapi.testclient import TestClient

from chess_review.api.app import create_app
from chess_review.db import Game, connect, insert_games


def make_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(
        conn,
        [
            Game(
                source="chesscom",
                source_id="https://www.chess.com/game/live/1",
                username="alice",
                white="alice",
                black="bob",
                result="win",
                time_class="blitz",
                played_at="2023-11-14T22:13:20+00:00",
                pgn="1. e4 e5",
            ),
            Game(
                source="chesscom",
                source_id="https://www.chess.com/game/live/2",
                username="alice",
                white="carla",
                black="alice",
                result="loss",
                time_class="rapid",
                played_at="2023-11-15T22:13:20+00:00",
                pgn="1. d4 d5",
            ),
        ],
    )
    conn.close()
    return TestClient(create_app(tmp_path, db_path=db_path))


def test_list_games_returns_newest_first(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.get("/api/games")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 2,
            "white": "carla",
            "black": "alice",
            "result": "loss",
            "time_class": "rapid",
            "played_at": "2023-11-15T22:13:20+00:00",
        },
        {
            "id": 1,
            "white": "alice",
            "black": "bob",
            "result": "win",
            "time_class": "blitz",
            "played_at": "2023-11-14T22:13:20+00:00",
        },
    ]


def test_get_game_returns_pgn(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.get("/api/games/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "white": "alice",
        "black": "bob",
        "result": "win",
        "time_class": "blitz",
        "played_at": "2023-11-14T22:13:20+00:00",
        "pgn": "1. e4 e5",
    }


def test_get_missing_game_returns_404(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.get("/api/games/999")

    assert response.status_code == 404
