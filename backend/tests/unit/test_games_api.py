from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chess_review.api.app import create_app
from chess_review.db import Game, connect, insert_games


@pytest.fixture
def client(tmp_path: Path, game_1: Game, game_2: Game) -> TestClient:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(conn, [game_1, game_2])
    conn.close()
    return TestClient(create_app(tmp_path, db_path))


def test_list_games_returns_newest_first(client: TestClient) -> None:
    response = client.get("/api/games")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 2,
            "white": "carla",
            "black": "alice",
            "result": "loss",
            "time_class": "rapid",
            "played_at": "2023-11-15T22:13:20Z",
        },
        {
            "id": 1,
            "white": "alice",
            "black": "bob",
            "result": "win",
            "time_class": "blitz",
            "played_at": "2023-11-14T22:13:20Z",
        },
    ]


def test_get_game_returns_pgn(client: TestClient) -> None:
    response = client.get("/api/games/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "white": "alice",
        "black": "bob",
        "result": "win",
        "time_class": "blitz",
        "played_at": "2023-11-14T22:13:20Z",
        "pgn": "1. e4 e5",
    }


def test_get_missing_game_returns_404(client: TestClient) -> None:
    response = client.get("/api/games/999")

    assert response.status_code == 404
