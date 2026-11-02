"""Why a game was decided, for each side, from the engine pass over its positions.

Thresholds are in win-percentage points on Lichess's curve. A blunder costs at least 15 points, which
is Lichess's 0.3 on its -1 to 1 winning-chances scale.
"""

import io
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

import chess
import chess.pgn

from chess_review.db import PositionAnalysis
from chess_review.themes.motifs import is_back_rank_mate, promotes, tactic_name

BLUNDER = 15
MISTAKE = 10
# Below this a side was already losing, so another error did not decide anything.
STILL_IN_GAME = 30
HOLDING = 45
WINNING = 85
OPENING_MOVES = 12
ENDGAME_PIECES = 6
DIRECT_MATE = 3
LOW_CLOCK_SECONDS = 10
LOW_CLOCK_SHARE = 0.05

CLOCK = re.compile(r"\[%clk (\d+):(\d+):(\d+(?:\.\d+)?)\]")


@dataclass(frozen=True)
class Step:
    """One move. Both win percentages are from the mover's point of view."""

    index: int
    board: chess.Board
    after: chess.Board
    move: chess.Move
    before_win: float
    after_win: float
    before: PositionAnalysis
    following: PositionAnalysis
    clock: float | None

    @property
    def loss(self) -> float:
        return self.before_win - self.after_win

    @property
    def move_number(self) -> int:
        return self.index // 2 + 1


@dataclass(frozen=True)
class Diagnosis:
    primary: str
    tags: list[str]
    decisive_move: int | None
    decisive_ply: int | None = None
    moments: dict[int, list[str]] = field(default_factory=dict)


def win_percent(analysis: PositionAnalysis, board: chess.Board, color: chess.Color) -> float:
    if board.is_checkmate():
        return 0.0 if board.turn == color else 100.0
    if analysis.mate is not None:
        return 100.0 if (analysis.mate > 0) == (color == chess.WHITE) else 0.0
    white = 50 + 50 * (2 / (1 + math.exp(-0.00368208 * (analysis.cp or 0))) - 1)
    return white if color == chess.WHITE else 100 - white


def _mate_for(analysis: PositionAnalysis, color: chess.Color) -> int | None:
    """Moves to mate if `color` is the side delivering it."""
    if not analysis.mate or (analysis.mate > 0) != (color == chess.WHITE):
        return None
    return abs(analysis.mate)


def _line(analysis: PositionAnalysis) -> list[chess.Move]:
    return [chess.Move.from_uci(uci) for uci in analysis.pv.split()]


def clocks(pgn: str) -> list[float]:
    return [int(hours) * 3600 + int(minutes) * 60 + float(seconds) for hours, minutes, seconds in CLOCK.findall(pgn)]


def build_steps(pgn: str, analyses: Mapping[str, PositionAnalysis]) -> list[Step]:
    """Returns no steps if any position has not been analysed yet."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game is not None
    remaining = clocks(pgn)
    board = game.board()
    steps = []
    for index, move in enumerate(game.mainline_moves()):
        after = board.copy(stack=False)
        after.push(move)
        before = analyses.get(board.epd())
        following = analyses.get(after.epd())
        if before is None or following is None:
            return []
        steps.append(
            Step(
                index=index,
                board=board,
                after=after,
                move=move,
                before_win=win_percent(before, board, board.turn),
                after_win=win_percent(following, after, board.turn),
                before=before,
                following=following,
                clock=remaining[index] if index < len(remaining) else None,
            )
        )
        board = after
    return steps


def _pieces_left(board: chess.Board) -> int:
    return chess.popcount(board.occupied & ~board.kings & ~board.pawns)


def _is_endgame(step: Step) -> bool:
    return _pieces_left(step.board) <= ENDGAME_PIECES


def endgame_kind(board: chess.Board) -> str:
    if board.queens:
        return "endgame_queen"
    if board.rooks:
        return "endgame_rook"
    return "endgame_minor" if board.knights or board.bishops else "endgame_pawn"


def _error_tags(step: Step, side: chess.Color) -> list[str]:
    """What a costly move allowed, then what it missed. The allowed tactic always comes first."""
    enemy = not side
    tags = []
    allowed = _mate_for(step.following, enemy)
    if allowed is not None and _mate_for(step.before, enemy) is None:
        if allowed <= DIRECT_MATE:
            tags.append(f"allowed_mate_in_{allowed}")
            if is_back_rank_mate(step.after, _line(step.following)):
                tags.append("back_rank_mate")
        else:
            tags.append("allowed_long_mate")
    else:
        tags.append(tactic_name(step.after, _line(step.following), enemy))
    missed = tactic_name(step.board, _line(step.before), side)
    if missed not in ("positional", "pawn_loss"):
        tags.append(f"missed_{missed}")
    return tags


def _missed_mate(step: Step, side: chess.Color) -> str | None:
    mate = _mate_for(step.before, side)
    if mate is None or mate > DIRECT_MATE or step.after.is_checkmate():
        return None
    return None if _mate_for(step.following, side) is not None else f"missed_mate_in_{mate}"


def _decisive(own: list[Step], curve: list[float]) -> Step | None:
    """The side's costliest move after the last moment it was still holding."""
    last_holding = max((index for index, win in enumerate(curve) if win >= HOLDING), default=0)
    candidates = [step for step in own if step.index >= last_holding - 1]
    worst = max(candidates, key=lambda step: step.loss, default=None)
    return worst if worst is not None and worst.loss >= MISTAKE else None


def _is_low_clock(step: Step, base_seconds: int | None) -> bool:
    if step.clock is None or base_seconds is None:
        return False
    return step.clock <= max(LOW_CLOCK_SECONDS, base_seconds * LOW_CLOCK_SHARE)


def _primary(step: Step | None, step_tags: list[str]) -> str:
    """One headline reason: mates first, then the endgame, then the tactic, then the phase."""
    if step is None:
        return "gradual_decline"
    for tag in step_tags:
        if tag.startswith(("missed_mate", "allowed_mate")):
            return tag.split("_in_")[0]
    allowed = step_tags[0] if step_tags else "positional"
    if _is_endgame(step):
        return "endgame_passed_pawn" if "promotion" in step_tags else "endgame"
    if allowed.startswith("fork"):
        return "fork"
    if allowed != "positional":
        return allowed
    if step.move_number <= OPENING_MOVES:
        return "opening"
    return "missed_tactic" if len(step_tags) > 1 else "positional"


def _endgame_tags(steps: list[Step], own: list[Step], side: chess.Color) -> set[str]:
    tags = set()
    enemy = not side
    for step in own:
        if _is_endgame(step) and step.loss >= BLUNDER and step.before_win >= STILL_IN_GAME:
            tags.add(endgame_kind(step.board))
            enemy_promoted = any(later.board.turn == enemy and later.move.promotion for later in steps[step.index :])
            if enemy_promoted or promotes(step.after, _line(step.following), enemy):
                tags.add("endgame_passed_pawn")
    return tags


def _termination_tags(termination: str, side_name: str, final_win: float) -> set[str]:
    """How the game ended for a side that did not win it."""
    if side_name.lower() in termination.lower() or " won " not in termination:
        return set()
    if "on time" in termination:
        return {"lost_on_time_while_ok" if final_win >= HOLDING else "lost_on_time"}
    if "abandoned" in termination:
        return {"abandoned"}
    return {"resigned_while_ok"} if "resignation" in termination and final_win >= HOLDING else set()


def diagnose(
    steps: list[Step], side: chess.Color, side_name: str, termination: str, base_seconds: int | None
) -> Diagnosis:
    """Why `side` lost ground. Run for both players, so it explains losses and, through the opponent, wins."""
    own = [step for step in steps if step.board.turn == side]
    curve = [step.after_win if step.board.turn == side else 100 - step.after_win for step in steps]
    by_move: dict[int, list[str]] = {}
    for step in own:
        if step.loss >= BLUNDER and step.before_win >= STILL_IN_GAME:
            by_move[step.index] = _error_tags(step, side)
            if _is_low_clock(step, base_seconds):
                by_move[step.index].append("low_clock_blunder")
        if missed := _missed_mate(step, side):
            by_move.setdefault(step.index, []).append(missed)

    decisive = _decisive(own, curve)
    if decisive is not None and decisive.index not in by_move:
        by_move[decisive.index] = _error_tags(decisive, side)

    tags = {tag for step_tags in by_move.values() for tag in step_tags}
    tags |= _endgame_tags(steps, own, side)
    tags |= _termination_tags(termination, side_name, curve[-1] if curve else 50.0)
    if curve and max(curve) >= WINNING:
        tags.add("had_winning_position")
    after_opening = [curve[step.index] for step in own if step.move_number == OPENING_MOVES]
    if after_opening and after_opening[0] <= STILL_IN_GAME:
        tags.add("opening")
    if decisive is not None and _is_low_clock(decisive, base_seconds):
        tags.add("decisive_low_clock")

    primary = _primary(decisive, by_move.get(decisive.index, []) if decisive else [])
    for ending in ("lost_on_time_while_ok", "resigned_while_ok", "abandoned"):
        if ending in tags:
            primary = ending
    if primary == "gradual_decline" and "opening" in tags:
        primary = "opening"
    return Diagnosis(
        primary,
        sorted(tags),
        decisive.move_number if decisive else None,
        decisive.index if decisive else None,
        by_move,
    )
