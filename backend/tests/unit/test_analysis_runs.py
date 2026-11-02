import threading
from dataclasses import replace
from pathlib import Path

import chess
from fastapi.testclient import TestClient

from chess_review.api.app import create_app
from chess_review.db import (
    Game,
    PositionAnalysis,
    Result,
    connect,
    get_game_reason,
    insert_games,
    insert_position_analyses,
    list_loss_reasons,
)
from chess_review.themes.classify import classify_unanalysed
from chess_review.themes.runs import AnalysisRuns, Report


def client_with(tmp_path: Path, games: list[Game], runs: AnalysisRuns) -> TestClient:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(conn, games)
    conn.close()
    app = create_app(tmp_path, db_path, Path("stockfish"))
    app.state.analysis_runs = runs
    return TestClient(app)


def test_status_counts_games_without_analysis(tmp_path: Path, game_1: Game, game_2: Game) -> None:
    client = client_with(tmp_path, [game_1, game_2], AnalysisRuns(lambda _username, _report: None))

    assert client.get("/api/analysis", params={"username": "alice"}).json() == {
        "games": 2,
        "unanalysed": 2,
        "phase": "idle",
        "done": 0,
        "total": 0,
        "error": None,
        "running_player": None,
    }


def test_starting_a_run_reports_progress_until_it_finishes(tmp_path: Path, game_1: Game) -> None:
    reached = threading.Event()
    release = threading.Event()

    def job(_username: str, report: Report) -> None:
        report("analysing", 5, 20)
        reached.set()
        release.wait(5)

    runs = AnalysisRuns(job)
    client = client_with(tmp_path, [game_1], runs)

    client.post("/api/analysis", params={"username": "alice"})
    reached.wait(5)
    running = client.get("/api/analysis", params={"username": "alice"}).json()
    release.set()
    runs.wait()

    assert (running["phase"], running["done"], running["total"]) == ("analysing", 5, 20)
    assert running["running_player"] == "alice"
    finished = client.get("/api/analysis", params={"username": "alice"}).json()
    assert (finished["phase"], finished["running_player"]) == ("idle", None)


def test_only_one_run_at_a_time(tmp_path: Path, game_1: Game) -> None:
    release = threading.Event()

    def job(_username: str, _report: Report) -> None:
        release.wait(5)

    runs = AnalysisRuns(job)
    client = client_with(tmp_path, [game_1], runs)

    assert client.post("/api/analysis", params={"username": "alice"}).status_code == 200
    assert client.post("/api/analysis", params={"username": "alice"}).status_code == 200
    assert client.post("/api/analysis", params={"username": "bob"}).status_code == 409
    release.set()
    runs.wait()


def test_a_failed_run_is_reported_and_can_be_retried(tmp_path: Path, game_1: Game) -> None:
    def job(_username: str, _report: Report) -> None:
        raise RuntimeError("stockfish not found")

    runs = AnalysisRuns(job)
    client = client_with(tmp_path, [game_1], runs)

    client.post("/api/analysis", params={"username": "alice"})
    runs.wait()

    state = client.get("/api/analysis", params={"username": "alice"}).json()
    assert (state["phase"], state["error"]) == ("failed", "stockfish not found")
    assert state["running_player"] is None
    assert client.post("/api/analysis", params={"username": "alice"}).status_code == 200
    runs.wait()


def test_classifying_covers_analysed_games_and_settles_games_without_moves(
    tmp_path: Path, game_1: Game, game_2: Game
) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    no_moves = replace(game_2, pgn='[Result "0-1"]\n\n0-1', result=Result.LOSS)
    insert_games(conn, [game_1, no_moves])
    board = chess.Board()
    positions = [board.epd()]
    for san in ("e4", "e5"):
        board.push_san(san)
        positions.append(board.epd())
    insert_position_analyses(conn, [PositionAnalysis(position, 0, None, "") for position in positions])

    classify_unanalysed(db_path, "alice")

    assert get_game_reason(conn, 1) is not None
    assert get_game_reason(conn, 2) is not None
    assert list_loss_reasons(conn, "alice") == []
    assert (
        TestClient(create_app(tmp_path, db_path, Path("stockfish")))
        .get("/api/analysis", params={"username": "alice"})
        .json()["unanalysed"]
        == 0
    )


def test_a_game_waiting_for_the_engine_stays_unanalysed(tmp_path: Path, game_1: Game) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(conn, [game_1])

    classify_unanalysed(db_path, "alice")

    assert get_game_reason(conn, 1) is None
