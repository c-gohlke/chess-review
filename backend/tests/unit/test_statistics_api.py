from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from chess_review.api.app import create_app
from chess_review.db import (
    NO_MOVES,
    Game,
    GameReason,
    Result,
    connect,
    insert_games,
    replace_game_reasons,
    replace_opponent_reasons,
)
from chess_review.patterns.forks import ForkKind, fork_label, summarize_forks
from chess_review.patterns.pawn_pushes import PawnPushCount, summarize_pawn_pushes
from chess_review.patterns.result_reasons import ReasonCount, ResultReasons, summarize_result_reasons


def reason(decided_by: str, *tags: str) -> GameReason:
    return GameReason(game_id=1, decided_by=decided_by, tags=list(tags))


def test_fork_label_names_the_forking_piece_and_the_family() -> None:
    assert fork_label("fork_knight") == "Knight fork"
    assert fork_label("fork_rook_royal") == "Rook fork, royal (king and queen)"
    assert fork_label("fork_knight_family") == "Knight fork, family (king, queen and more)"
    assert fork_label("fork_queen_grand") == "Queen fork, grand (king, queen and two rooks)"


def test_summary_counts_each_loss_once_per_kind_and_most_common_first() -> None:
    summary = summarize_forks(
        [
            reason("fork", "fork_knight", "fork_pawn", "hanging_piece"),
            reason("endgame", "fork_knight"),
            reason("hanging_piece", "hanging_piece", "missed_fork_queen"),
        ]
    )

    assert summary.analysed_losses == 3
    assert summary.losses_with_fork == 2
    assert summary.decided_by_fork == 1
    assert summary.kinds == [ForkKind("Knight fork", 2), ForkKind("Pawn fork", 1)]


def test_statistics_only_count_that_players_analysed_losses(tmp_path: Path, game_1: Game, game_2: Game) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    won = replace(game_1, result=Result.WIN)
    lost = replace(game_2, result=Result.LOSS)
    other_player = replace(game_2, source_id="other", username="carol", result=Result.LOSS)
    insert_games(conn, [won, lost, other_player])
    replace_game_reasons(
        conn,
        [
            GameReason(1, "fork", ["fork_bishop"]),
            GameReason(2, "fork", ["fork_knight"]),
            GameReason(3, "fork", ["fork_queen"]),
        ],
    )
    conn.close()
    client = TestClient(create_app(tmp_path, db_path, Path("stockfish")))

    response = client.get("/api/statistics/forks", params={"username": "alice"})

    assert response.json() == {
        "analysed_losses": 1,
        "losses_with_fork": 1,
        "decided_by_fork": 1,
        "kinds": [{"name": "Knight fork", "losses": 1}],
    }


def test_pawn_push_summary_counts_each_game_once_per_wing_and_timing() -> None:
    summary = summarize_pawn_pushes(
        [
            reason("gradual_decline", "kingside_pawns_early", "queenside_pawns_late"),
            reason("hanging_piece", "kingside_pawns_early", "hanging_piece"),
            reason("opening"),
        ]
    )

    assert summary.analysed_games == 3
    assert summary.counts == [
        PawnPushCount("queenside", "early", 0),
        PawnPushCount("queenside", "late", 1),
        PawnPushCount("kingside", "early", 2),
        PawnPushCount("kingside", "late", 0),
    ]


def test_pawn_push_statistics_count_that_players_analysed_games_of_any_result(
    tmp_path: Path, game_1: Game, game_2: Game
) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    other_player = replace(game_2, source_id="other", username="carol")
    no_moves = replace(game_2, source_id="empty")
    insert_games(conn, [replace(game_1, result=Result.WIN), game_2, other_player, no_moves])
    replace_game_reasons(
        conn,
        [
            GameReason(1, "gradual_decline", ["kingside_pawns_late"]),
            GameReason(2, "opening", ["kingside_pawns_late", "queenside_pawns_early"]),
            GameReason(3, "opening", ["kingside_pawns_late"]),
            GameReason(4, NO_MOVES, []),
        ],
    )
    conn.close()
    client = TestClient(create_app(tmp_path, db_path, Path("stockfish")))

    summary = client.get("/api/statistics/pawn-pushes", params={"username": "alice"}).json()

    assert summary["analysed_games"] == 2
    assert {(row["wing"], row["timing"]): row["games"] for row in summary["counts"]} == {
        ("queenside", "early"): 1,
        ("queenside", "late"): 0,
        ("kingside", "early"): 0,
        ("kingside", "late"): 2,
    }


def test_reason_summary_counts_deciding_reasons_and_groups_forks() -> None:
    summary = summarize_result_reasons(
        [
            reason("hanging_piece", "hanging_piece", "fork_knight", "fork_queen_royal", "missed_fork_bishop"),
            reason("hanging_piece", "hanging_piece", "low_clock_blunder"),
            reason("endgame", "endgame_rook"),
        ],
        [],
    )

    assert summary.losses.games == 3
    assert summary.losses.deciding == [ReasonCount("Hung a piece", 2), ReasonCount("Endgame error", 1)]
    assert summary.losses.tags == [
        ReasonCount("Hung a piece", 2),
        ReasonCount("Allowed a fork", 1),
        ReasonCount("Endgame error with rooks", 1),
        ReasonCount("Low on time", 1),
        ReasonCount("Missed a fork", 1),
    ]
    assert summary.wins == ResultReasons(0, [], [])


def test_reasons_endpoint_explains_losses_by_own_errors_and_wins_by_the_opponents(
    tmp_path: Path, game_1: Game, game_2: Game
) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    draw = replace(game_2, source_id="draw", result=Result.DRAW)
    insert_games(conn, [replace(game_1, result=Result.WIN), replace(game_2, result=Result.LOSS), draw])
    replace_game_reasons(
        conn,
        [
            GameReason(1, "positional", ["had_winning_position"]),
            GameReason(2, "allowed_mate", ["allowed_mate_in_1"]),
            GameReason(3, "pin", ["pin"]),
        ],
    )
    replace_opponent_reasons(
        conn,
        [
            GameReason(1, "fork", ["fork_knight"]),
            GameReason(2, "positional", []),
            GameReason(3, "skewer", ["skewer"]),
        ],
    )
    conn.close()
    client = TestClient(create_app(tmp_path, db_path, Path("stockfish")))

    summary = client.get("/api/statistics/reasons", params={"username": "alice"}).json()

    assert summary["losses"] == {
        "games": 1,
        "deciding": [{"name": "Allowed a mate", "games": 1}],
        "tags": [{"name": "Allowed mate in 1", "games": 1}],
    }
    assert summary["wins"] == {
        "games": 1,
        "deciding": [{"name": "Fork", "games": 1}],
        "tags": [{"name": "Allowed a fork", "games": 1}],
    }
