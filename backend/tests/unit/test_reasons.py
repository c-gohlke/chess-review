import io

import chess
import chess.pgn

from chess_review.db import PositionAnalysis
from chess_review.themes.reasons import Step, build_steps, clocks, diagnose, win_percent

SCHOLARS_MATE = "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0"
MISSED_MATE = "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. d3 d6 1/2-1/2"


def steps_for(pgn: str, overrides: dict[int, PositionAnalysis]) -> list[Step]:
    """Every position is level with no line, except the plies listed in `overrides`."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game is not None
    board = game.board()
    positions = [board.epd()]
    for move in game.mainline_moves():
        board.push(move)
        positions.append(board.epd())
    analyses = {position: PositionAnalysis(position, 0, None, "") for position in positions}
    for ply, analysis in overrides.items():
        analyses[positions[ply]] = PositionAnalysis(positions[ply], analysis.cp, analysis.mate, analysis.pv)
    return build_steps(pgn, analyses)


MATE_THREAT = {6: PositionAnalysis("", None, 1, "h5f7")}
ALLOWED = MATE_THREAT


def test_win_percent_follows_lichess_curve_and_mate() -> None:
    board = chess.Board()
    level = PositionAnalysis("", 0, None, "")
    assert win_percent(level, board, chess.WHITE) == 50
    assert win_percent(PositionAnalysis("", None, 3, ""), board, chess.BLACK) == 0
    assert round(win_percent(PositionAnalysis("", 300, None, ""), board, chess.WHITE)) == 75


def test_build_steps_is_empty_while_a_position_is_unanalysed() -> None:
    assert build_steps(SCHOLARS_MATE, {}) == []


def test_clocks_are_read_in_seconds() -> None:
    assert clocks("1. e4 {[%clk 0:03:00.5]} e5 {[%clk 0:02:59]}") == [180.5, 179.0]


def test_allowing_mate_in_one_is_the_primary_reason() -> None:
    steps = steps_for(SCHOLARS_MATE, ALLOWED)
    diagnosis = diagnose(steps, chess.BLACK, "bob", "alice won by checkmate", 180)
    assert diagnosis.primary == "allowed_mate"
    assert "allowed_mate_in_1" in diagnosis.tags
    assert diagnosis.decisive_move == 3


def test_winner_has_no_decisive_error() -> None:
    steps = steps_for(SCHOLARS_MATE, ALLOWED)
    assert diagnose(steps, chess.WHITE, "alice", "alice won by checkmate", 180).primary == "gradual_decline"


def test_not_taking_a_mate_in_one_is_a_missed_mate() -> None:
    steps = steps_for(MISSED_MATE, MATE_THREAT)
    diagnosis = diagnose(steps, chess.WHITE, "alice", "Game drawn by agreement", 180)
    assert diagnosis.primary == "missed_mate"
    assert "missed_mate_in_1" in diagnosis.tags


def test_flagging_in_a_good_position_overrides_the_board_reason() -> None:
    steps = steps_for(MISSED_MATE, {})
    diagnosis = diagnose(steps, chess.WHITE, "alice", "bob won on time", 180)
    assert diagnosis.primary == "lost_on_time_while_ok"


def test_the_flag_winner_gets_no_time_tag() -> None:
    steps = steps_for(MISSED_MATE, {})
    assert "lost_on_time" not in diagnose(steps, chess.BLACK, "bob", "bob won on time", 180).tags


WING_PAWN = "1. e4 e5 2. Nf3 Nc6 3. h4 Nf6 1/2-1/2"
# Ply 4 is before White's 3. h4, ply 5 after it.
H4_COSTS = {5: PositionAnalysis("", -200, None, "")}


def white_tags(pgn: str, overrides: dict[int, PositionAnalysis]) -> list[str]:
    return diagnose(steps_for(pgn, overrides), chess.WHITE, "alice", "Game drawn by agreement", 180).tags


def timing_tags(tags: list[str]) -> set[str]:
    return {tag for tag in tags if "_pawns_" in tag}


def test_a_costly_wing_pawn_push_the_engine_did_not_want_is_early() -> None:
    tags = white_tags(WING_PAWN, {**H4_COSTS, 4: PositionAnalysis("", 0, None, "f1c4")})

    assert timing_tags(tags) == {"kingside_pawns_early"}


def test_skipping_the_engines_wing_pawn_push_is_late() -> None:
    tags = white_tags(WING_PAWN, {**H4_COSTS, 4: PositionAnalysis("", 0, None, "a2a4")})

    assert timing_tags(tags) == {"kingside_pawns_early", "queenside_pawns_late"}


def test_a_cheap_wing_pawn_push_gets_no_timing_tag() -> None:
    tags = white_tags(WING_PAWN, {4: PositionAnalysis("", 0, None, "a2a4"), 5: PositionAnalysis("", -50, None, "")})

    assert timing_tags(tags) == set()


def test_a_pawn_capture_is_not_a_push() -> None:
    # Ply 2 is before White's 2. bxc5, ply 3 after it.
    tags = white_tags(
        "1. b4 c5 2. bxc5 Nc6 1/2-1/2",
        {2: PositionAnalysis("", 0, None, "g1f3"), 3: PositionAnalysis("", -200, None, "")},
    )

    assert timing_tags(tags) == set()
