from pathlib import Path

from fastapi.testclient import TestClient

from chess_review.analysis.positions import game_boards
from chess_review.api.app import create_app
from chess_review.db import Game, PositionAnalysis, connect, insert_games, insert_position_analyses
from chess_review.themes.classify import classify_games


def client_with(tmp_path: Path, games: list[Game]) -> tuple[TestClient, list[Game]]:
    """The fake engine scores every position level, then classifies like the real one."""
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(conn, games)
    conn.close()
    analysed: list[Game] = []

    def analyse(game: Game) -> None:
        analysed.append(game)
        conn = connect(db_path)
        boards = game_boards(game.pgn)
        insert_position_analyses(conn, [PositionAnalysis(board.epd(), 0, None, "") for board in boards])
        conn.close()
        classify_games(db_path, [game])

    app = create_app(tmp_path, db_path, Path("stockfish"))
    app.state.analyse_game = analyse
    return TestClient(app), analysed


def test_analysing_a_game_returns_it_with_its_analysis(tmp_path: Path, game_1: Game) -> None:
    client, analysed = client_with(tmp_path, [game_1])
    assert client.get("/api/games/1").json()["analysis"] is None

    response = client.post("/api/games/1/analysis")

    assert response.status_code == 200
    assert response.json()["analysis"] is not None
    assert response.json()["pgn"] == game_1.pgn
    assert [game.source_id for game in analysed] == [game_1.source_id]
    assert client.get("/api/games/1").json()["analysis"] == response.json()["analysis"]


def test_an_analysed_game_is_not_analysed_again(tmp_path: Path, game_1: Game) -> None:
    client, analysed = client_with(tmp_path, [game_1])
    client.post("/api/games/1/analysis")

    client.post("/api/games/1/analysis")

    assert len(analysed) == 1


def test_analysing_an_unknown_game_is_not_found(tmp_path: Path) -> None:
    client, analysed = client_with(tmp_path, [])

    assert client.post("/api/games/9/analysis").status_code == 404
    assert analysed == []
