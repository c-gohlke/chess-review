"""Habits measured before a game is decided, so they can be compared with its result.

Everything comes from the first moves or from earlier games. A feature read from the whole game would
leak the result: "never castled" is more common in short losses simply because they are short.
"""

import io
import re
from collections.abc import Sequence
from datetime import timedelta
from zoneinfo import ZoneInfo

import chess
import chess.pgn

from chess_review.db import Game, Result
from chess_review.patterns.openings import colour_played
from chess_review.themes.reasons import clocks

HABIT_MOVES = 12
DEVELOPED_BY = 10
EARLY_QUEEN_BY = 6
REPEAT_MOVES_BY = 8
SESSION_GAP = timedelta(minutes=30)
LONG_SESSION = 6
TIMEZONE = ZoneInfo("Europe/Paris")
TIME_CONTROL = re.compile(r'^\[TimeControl "(\d+)(?:\+\d+)?"\]$', re.MULTILINE)

# The rook-pawn move, and the square whose control would justify it.
QUIET_ROOK_PAWN = {
    chess.Move(chess.A2, chess.A3): chess.B4,
    chess.Move(chess.H2, chess.H3): chess.G4,
    chess.Move(chess.A7, chess.A6): chess.B5,
    chess.Move(chess.H7, chess.H6): chess.G5,
}
RIM_FILES = (0, 7)


def base_seconds(pgn: str) -> int | None:
    match = TIME_CONTROL.search(pgn)
    return int(match.group(1)) if match else None


def _is_purposeless(board: chess.Board, move: chess.Move, later: list[chess.Move]) -> bool:
    """A rook-pawn step with no enemy piece on or eyeing the next square, and no pawn push to it soon after."""
    target = QUIET_ROOK_PAWN[move]
    enemy = not board.turn
    pawns = board.pieces(chess.PAWN, enemy)
    has_enemy_piece = board.color_at(target) == enemy
    is_contested = bool(board.attackers(enemy, target) - pawns)
    supports_push = any(next_move.to_square == target for next_move in later)
    return not (has_enemy_piece or is_contested or supports_push)


def _own_moves(game: chess.pgn.Game, white: bool) -> list[tuple[chess.Board, chess.Move]]:
    board = game.board()
    moves = []
    for ply, move in enumerate(game.mainline_moves()):
        if ply >= HABIT_MOVES * 2:
            break
        if board.turn == white:
            moves.append((board.copy(stack=False), move))
        board.push(move)
    return moves


def _pawn_habits(own: list[tuple[chess.Board, chess.Move]], white: bool) -> dict[str, bool]:
    pawn_moves = [move for board, move in own if board.piece_type_at(move.from_square) == chess.PAWN]
    crossed_rank = 4 if white else 3
    is_past_centre = [
        chess.square_rank(move.to_square) >= crossed_rank
        if white
        else chess.square_rank(move.to_square) <= crossed_rank
        for move in pawn_moves
    ]
    return {
        "few_pawn_moves": len(pawn_moves) <= 3,
        "many_pawn_moves": len(pawn_moves) >= 8,
        "no_pawn_past_centre": not any(is_past_centre),
    }


def _rook_pawn_habits(own: list[tuple[chess.Board, chess.Move]]) -> dict[str, bool]:
    moves = [move for _, move in own]
    habits = {"a_pawn_no_reason": False, "h_pawn_no_reason": False}
    for index, (board, move) in enumerate(own):
        if move in QUIET_ROOK_PAWN and _is_purposeless(board, move, moves[index + 1 :]):
            is_a_file = chess.square_file(move.from_square) == 0
            habits["a_pawn_no_reason" if is_a_file else "h_pawn_no_reason"] = True
    habits["rook_pawn_no_reason"] = habits["a_pawn_no_reason"] or habits["h_pawn_no_reason"]
    habits["rook_pawn_step"] = any(move in QUIET_ROOK_PAWN for move in moves)
    return habits


def _development_habits(own: list[tuple[chess.Board, chess.Move]], white: bool) -> dict[str, bool]:
    home = [chess.B1, chess.C1, chess.F1, chess.G1] if white else [chess.B8, chess.C8, chess.F8, chess.G8]
    after_ten = own[DEVELOPED_BY - 1][0].copy(stack=False)
    after_ten.push(own[DEVELOPED_BY - 1][1])
    color = chess.WHITE if white else chess.BLACK
    undeveloped = sum(after_ten.piece_at(square) in _minor_pieces(color) for square in home)
    mover_squares = [move.from_square for _, move in own[:REPEAT_MOVES_BY]]
    arrived = [move.to_square for _, move in own[:REPEAT_MOVES_BY]]
    return {
        "undeveloped_minors": undeveloped >= 2,
        "not_castled_by_12": not any(board.is_castling(move) for board, move in own),
        "early_queen": any(
            board.piece_type_at(move.from_square) == chess.QUEEN for board, move in own[:EARLY_QUEEN_BY]
        ),
        "knight_on_rim": any(
            board.piece_type_at(move.from_square) == chess.KNIGHT and chess.square_file(move.to_square) in RIM_FILES
            for board, move in own
        ),
        "repeated_piece_moves": sum(square in arrived for square in mover_squares) >= 2,
    }


def _minor_pieces(color: chess.Color) -> tuple[chess.Piece, chess.Piece]:
    return chess.Piece(chess.KNIGHT, color), chess.Piece(chess.BISHOP, color)


def _clock_habits(pgn: str, white: bool) -> dict[str, bool]:
    base = base_seconds(pgn)
    all_clocks = clocks(pgn)
    own_clocks = all_clocks[0 if white else 1 :: 2]
    enemy_clocks = all_clocks[1 if white else 0 :: 2]
    if base is None or min(len(own_clocks), len(enemy_clocks)) < HABIT_MOVES:
        return {}
    share_spent = (base - own_clocks[DEVELOPED_BY - 1]) / base
    deficit = (enemy_clocks[HABIT_MOVES - 1] - own_clocks[HABIT_MOVES - 1]) / base
    return {
        "slow_opening": share_spent >= 0.25,
        "instant_opening": share_spent <= 0.05,
        "behind_on_clock": deficit >= 0.1,
    }


def opening_habits(pgn: str, white: bool) -> dict[str, bool] | None:
    """None for games too short to show the habits, which would otherwise count as not having them."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game is not None
    own = _own_moves(game, white)
    if len(own) < HABIT_MOVES:
        return None
    return (
        _pawn_habits(own, white) | _rook_pawn_habits(own) | _development_habits(own, white) | _clock_habits(pgn, white)
    )


def session_context(games: Sequence[Game]) -> dict[int, dict[str, bool]]:
    """Context for each game id. `games` must be one player's, oldest first."""
    context = {}
    session_length = 0
    losses_in_a_row = 0
    previous: Game | None = None
    for game in games:
        assert game.id is not None
        is_same_session = previous is not None and game.played_at - previous.played_at < SESSION_GAP
        session_length = session_length + 1 if is_same_session else 1
        if not is_same_session:
            losses_in_a_row = 0
        hour = game.played_at.astimezone(TIMEZONE).hour
        context[game.id] = {
            "after_a_loss": losses_in_a_row == 1,
            "after_two_losses": losses_in_a_row >= 2,
            "long_session": session_length >= LONG_SESSION,
            "late_night": hour < 6,
        }
        losses_in_a_row = losses_in_a_row + 1 if game.result == Result.LOSS else 0
        previous = game
    return context


def is_white(game: Game) -> bool:
    return colour_played(game) == "white"
