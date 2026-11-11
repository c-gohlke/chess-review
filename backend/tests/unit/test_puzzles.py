import csv
from dataclasses import replace
from pathlib import Path

import chess

from chess_review.analysis.positions import game_boards
from chess_review.db import Game, GameMoment, PositionAnalysis, connect, insert_games, insert_position_analyses
from chess_review.puzzles.build import (
    build_puzzles,
    game_puzzles,
    merge_duplicates,
    solution,
    themes_for,
    write_dataset,
)
from chess_review.themes.reasons import build_steps

# Black's 3...Nf6 lets White mate on f7; in the second game White misses it with 4. d3.
MATED = "1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7#"
MISSED = "1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. d3"
BEFORE_NF6 = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3"


def _analyses(pgn: str, lines: dict[int, str]) -> dict[str, PositionAnalysis]:
    """Level positions everywhere, with `lines[ply]` as the engine line from the position before move `ply`."""
    boards = game_boards(pgn)
    return {board.epd(): PositionAnalysis(board.epd(), 0, None, lines.get(ply, "")) for ply, board in enumerate(boards)}


def _game(game: Game, pgn: str) -> Game:
    return replace(game, id=7, pgn=pgn)


def test_mate_themes_name_the_length() -> None:
    assert themes_for("allowed_mate_in_2") == ["mate", "mate_in_2"]
    assert themes_for("mate_in_1") == ["mate", "mate_in_1"]


def test_forks_are_grouped_with_their_piece() -> None:
    assert themes_for("fork_knight_royal") == ["fork", "fork_knight_royal"]


def test_errors_with_no_tactic_make_no_puzzle() -> None:
    assert themes_for("positional") == []
    assert themes_for("pawn_loss") == []
    assert themes_for("allowed_long_mate") == []


def test_a_material_tactic_stops_once_the_material_is_won() -> None:
    board = chess.Board("4k3/8/8/3q4/8/8/8/3RK3 w - - 0 1")
    line = [chess.Move.from_uci(uci) for uci in ["d1d5", "e8e7", "d5d1", "e7e6"]]

    assert solution(board, line, ["hanging_piece"]) == line[:1]


def test_a_mate_that_the_line_does_not_reach_is_dropped() -> None:
    board = chess.Board("4k3/8/8/3q4/8/8/8/3RK3 w - - 0 1")
    line = [chess.Move.from_uci("d1d5")]

    assert solution(board, line, ["mate", "mate_in_1"]) == []


def test_an_illegal_line_is_dropped() -> None:
    board = chess.Board("4k3/8/8/3q4/8/8/8/3RK3 w - - 0 1")

    assert solution(board, [chess.Move.from_uci("e8e7")], ["hanging_piece"]) == []


def test_an_allowed_mate_is_solved_by_the_other_side(game_2: Game) -> None:
    game = _game(game_2, MATED)
    steps = build_steps(game.pgn, _analyses(game.pgn, {6: "h5f7"}))
    moment = GameMoment(7, 5, True, 60, ["allowed_mate_in_1"])

    [puzzle] = game_puzzles(game, steps, [moment])

    assert puzzle.fen == BEFORE_NF6
    assert puzzle.moves == ["g8f6", "h5f7"]
    assert puzzle.themes == ["mate", "mate_in_1"]
    assert puzzle.solved_by == "opponent"
    assert puzzle.game_url == game.source_id


def test_a_missed_mate_starts_from_the_opponents_move(game_1: Game) -> None:
    game = _game(game_1, MISSED)
    steps = build_steps(game.pgn, _analyses(game.pgn, {6: "h5f7"}))
    moment = GameMoment(7, 6, False, 40, ["positional", "missed_mate_in_1"])

    [puzzle] = game_puzzles(game, steps, [moment])

    assert puzzle.fen == BEFORE_NF6
    assert puzzle.moves == ["g8f6", "h5f7"]
    assert puzzle.solved_by == "you"


def test_the_same_puzzle_from_both_sides_is_kept_once(game_1: Game) -> None:
    game = _game(game_1, MISSED)
    steps = build_steps(game.pgn, _analyses(game.pgn, {6: "h5f7"}))
    moments = [
        GameMoment(7, 5, False, 30, ["allowed_mate_in_1", "back_rank_mate"]),
        GameMoment(7, 6, False, 40, ["positional", "missed_mate_in_1"]),
    ]

    [puzzle] = merge_duplicates(game_puzzles(game, steps, moments))

    assert puzzle.themes == ["mate", "mate_in_1", "back_rank_mate"]
    assert puzzle.win_lost == 40


def test_the_dataset_has_a_file_per_theme(tmp_path: Path, game_2: Game) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(conn, [replace(game_2, pgn=MATED)])
    analyses = _analyses(MATED, {6: "h5f7"})
    insert_position_analyses(conn, list(analyses.values()))
    conn.execute("INSERT INTO game_moments VALUES (1, 5, 1, 60, 'allowed_mate_in_1')")
    conn.commit()

    counts = write_dataset(tmp_path / "out", build_puzzles(conn, "alice"))

    assert counts == {"mate": 1, "mate_in_1": 1}
    with (tmp_path / "out" / "mate_in_1.csv").open() as file:
        [row] = list(csv.DictReader(file))
    assert row["FEN"] == BEFORE_NF6
    assert row["Moves"] == "g8f6 h5f7"
    assert row["Themes"] == "mate mate_in_1"
