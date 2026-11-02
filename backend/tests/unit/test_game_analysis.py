from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chess_review.api.app import create_app
from chess_review.db import (
    Game,
    GameMoment,
    GameReason,
    Result,
    connect,
    insert_games,
    replace_game_moments,
    replace_game_reasons,
    replace_opponent_reasons,
)
from chess_review.patterns.game_analysis import build_game_analysis, tag_label

OWN = GameReason(1, "fork", ["fork_knight"])
OPPONENT = GameReason(1, "hanging_piece", ["hanging_piece"])
MOMENTS = [
    GameMoment(1, 12, False, 20, ["pawn_loss"]),
    GameMoment(1, 21, True, 59, ["fork_knight_royal", "low_clock_blunder"]),
]


@pytest.mark.parametrize(
    ("tag", "label"),
    [
        ("hanging_piece", "Hung a piece"),
        ("allowed_mate_in_2", "Allowed mate in 2"),
        ("missed_mate_in_1", "Missed mate in 1"),
        ("fork_knight", "Allowed a knight fork"),
        ("missed_fork_queen_royal", "Missed a queen fork, royal (king and queen)"),
    ],
)
def test_tag_label(tag: str, label: str) -> None:
    assert tag_label(tag) == label


def test_analysis_names_the_player_and_move_of_each_moment(game_1: Game) -> None:
    analysis = build_game_analysis(replace(game_1, result=Result.LOSS), OWN, OPPONENT, MOMENTS)

    assert analysis.decided_by == "Fork"
    assert [(item.ply, item.move_number, item.player) for item in analysis.moments] == [
        (12, 7, "alice"),
        (21, 11, "bob"),
    ]
    assert analysis.moments[1].is_decisive
    assert analysis.moments[1].win_lost == 59
    assert analysis.moments[1].labels == ["Allowed a knight fork, royal (king and queen)", "Low on time"]


def test_a_win_is_explained_by_the_opponents_error(game_1: Game) -> None:
    assert build_game_analysis(game_1, OWN, OPPONENT, []).decided_by == "Hung a piece"


def client_with(tmp_path: Path, game: Game) -> TestClient:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(conn, [game])
    return TestClient(create_app(tmp_path, db_path, Path("stockfish")))


def test_game_detail_has_no_analysis_before_the_engine_pass(tmp_path: Path, game_1: Game) -> None:
    assert client_with(tmp_path, game_1).get("/api/games/1").json()["analysis"] is None


def test_game_detail_returns_stored_analysis_in_move_order(tmp_path: Path, game_1: Game) -> None:
    client = client_with(tmp_path, game_1)
    conn = connect(tmp_path / "db.sqlite3")
    replace_game_reasons(conn, [OWN])
    replace_opponent_reasons(conn, [OPPONENT])
    replace_game_moments(conn, list(reversed(MOMENTS)))
    replace_game_moments(conn, [MOMENTS[0]])
    conn.close()

    analysis = client.get("/api/games/1").json()["analysis"]

    assert analysis["decided_by"] == "Hung a piece"
    assert [moment["ply"] for moment in analysis["moments"]] == [12]
