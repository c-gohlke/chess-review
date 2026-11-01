from pathlib import Path

import chess
import pytest
from fastapi.testclient import TestClient

from chess_review.api.app import create_app
from chess_review.db import Evaluation, connect, get_evaluation, insert_evaluation

START = chess.STARTING_FEN
# The same position reached with different move counters.
START_LATER = START.replace("0 1", "4 3")
NO_KINGS = "8/8/8/8/8/8/8/8 w - - 0 1"


@pytest.fixture
def engine_calls(monkeypatch: pytest.MonkeyPatch) -> list[chess.Board]:
    calls: list[chess.Board] = []

    def fake_evaluate(_stockfish_path: Path, board: chess.Board) -> Evaluation:
        calls.append(board)
        return Evaluation(cp=35, mate=None)

    monkeypatch.setattr("chess_review.api.evaluation.evaluate", fake_evaluate)
    return calls


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path, tmp_path / "db.sqlite3", Path("stockfish")))


def test_evaluation_returns_engine_result(client: TestClient, engine_calls: list[chess.Board]) -> None:
    response = client.get("/api/evaluation", params={"fen": START})

    assert response.status_code == 200
    assert response.json() == {"cp": 35, "mate": None}
    assert [board.fen() for board in engine_calls] == [START]


def test_evaluation_is_stored_per_position(client: TestClient, engine_calls: list[chess.Board]) -> None:
    first = client.get("/api/evaluation", params={"fen": START})
    second = client.get("/api/evaluation", params={"fen": START_LATER})

    assert second.json() == first.json()
    assert len(engine_calls) == 1


def test_stored_mate_survives_a_new_connection(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_evaluation(conn, "position", Evaluation(cp=None, mate=-3))
    conn.close()

    conn = connect(db_path)
    assert get_evaluation(conn, "position") == Evaluation(cp=None, mate=-3)
    assert get_evaluation(conn, "other") is None


@pytest.mark.parametrize("fen", ["not a fen", NO_KINGS])
def test_evaluation_rejects_invalid_positions(client: TestClient, engine_calls: list[chess.Board], fen: str) -> None:
    assert client.get("/api/evaluation", params={"fen": fen}).status_code == 422
    assert engine_calls == []
