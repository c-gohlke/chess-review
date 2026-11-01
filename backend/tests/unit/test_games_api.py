from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chess_review.api.app import create_app
from chess_review.db import Game, TimeClass, connect, insert_games


@pytest.fixture
def client(tmp_path: Path, game_1: Game, game_2: Game) -> TestClient:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(conn, [game_1, game_2])
    conn.close()
    return TestClient(create_app(tmp_path, db_path, Path("stockfish")))


@pytest.mark.parametrize(
    ("limit", "offset", "ids"),
    [(1, 0, [2]), (1, 1, [1]), (5, 0, [2, 1]), (5, 2, [])],
)
def test_list_games_returns_one_page(client: TestClient, limit: int, offset: int, ids: list[int]) -> None:
    response = client.get("/api/games", params={"limit": limit, "offset": offset})

    assert [game["id"] for game in response.json()] == ids


@pytest.mark.parametrize("params", [{"limit": 0, "offset": 0}, {"limit": 201, "offset": 0}, {"limit": 1, "offset": -1}])
def test_list_games_rejects_out_of_range_pages(client: TestClient, params: dict[str, int]) -> None:
    assert client.get("/api/games", params=params).status_code == 422


def test_list_games_returns_newest_first(client: TestClient) -> None:
    response = client.get("/api/games", params={"limit": 50, "offset": 0})

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 2,
            "white": "carla",
            "black": "alice",
            "result": "loss",
            "time_class": "rapid",
            "played_at": "2023-11-15T22:13:20Z",
            "opening": "Unknown opening",
            "rating_change": None,
        },
        {
            "id": 1,
            "white": "alice",
            "black": "bob",
            "result": "win",
            "time_class": "blitz",
            "played_at": "2023-11-14T22:13:20Z",
            "opening": "Unknown opening",
            "rating_change": None,
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


def with_rating(game: Game, index: int, white_elo: int, black_elo: int) -> Game:
    eco_url = "https://www.chess.com/openings/Sicilian-Defense-Open"
    headers = f'[WhiteElo "{white_elo}"]\n[BlackElo "{black_elo}"]\n[ECOUrl "{eco_url}"]'
    return replace(
        game,
        source_id=f"game-{index}",
        played_at=game.played_at + timedelta(days=index),
        pgn=f"{headers}\n\n1. e4 c5",
    )


def test_list_games_adds_opening_and_rating_change(tmp_path: Path, game_1: Game, game_2: Game) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    as_white = with_rating(game_1, 0, 1000, 900)
    # Alice's own rating is White's here, and Black's in the next game.
    as_black = with_rating(game_2, 1, 2000, 1012)
    as_black = replace(as_black, time_class=game_1.time_class)
    other_pool = replace(with_rating(game_1, 2, 1500, 900), time_class=TimeClass.RAPID)
    insert_games(conn, [as_white, as_black, other_pool])
    conn.close()
    client = TestClient(create_app(tmp_path, db_path, Path("stockfish")))

    games = client.get("/api/games", params={"limit": 5, "offset": 0}).json()

    assert [(game["id"], game["opening"], game["rating_change"]) for game in games] == [
        (3, "Sicilian Defense", None),
        (2, "Sicilian Defense", 12),
        (1, "Sicilian Defense", None),
    ]
