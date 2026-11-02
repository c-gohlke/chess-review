import re
from dataclasses import dataclass

from chess_review.db import Game, GameMoment, GameReason, Result
from chess_review.patterns.forks import PREFIX, fork_label

LABELS = {
    "abandoned": "Abandoned the game",
    "allowed_long_mate": "Allowed a forced mate",
    "allowed_mate": "Allowed a mate",
    "back_rank_mate": "Back-rank mate",
    "discovered_attack": "Allowed a discovered attack",
    "endgame": "Endgame error",
    "endgame_passed_pawn": "Passed pawn in the endgame",
    "fork": "Fork",
    "gradual_decline": "Gradual decline",
    "hanging_piece": "Hung a piece",
    "lost_on_time_while_ok": "Lost on time in an OK position",
    "low_clock_blunder": "Low on time",
    "missed_discovered_attack": "Missed a discovered attack",
    "missed_hanging_piece": "Missed a free piece",
    "missed_mate": "Missed a mate",
    "missed_other_tactic": "Missed a tactic",
    "missed_pin": "Missed a pin",
    "missed_promotion": "Missed a promotion",
    "missed_skewer": "Missed a skewer",
    "missed_tactic": "Missed a tactic",
    "opening": "Opening error",
    "other_tactic": "Allowed a tactic",
    "pawn_loss": "Lost a pawn",
    "pin": "Allowed a pin",
    "positional": "No immediate tactic",
    "promotion": "Allowed a promotion",
    "resigned_while_ok": "Resigned in an OK position",
    "skewer": "Allowed a skewer",
}
MATE = re.compile(r"(allowed|missed)_mate_in_(\d+)")


@dataclass(frozen=True)
class Moment:
    ply: int  # index of the move in the game, from 0
    move_number: int
    player: str
    is_decisive: bool
    win_lost: int  # win-percentage points this move gave away
    labels: list[str]


@dataclass(frozen=True)
class GameAnalysis:
    decided_by: str
    moments: list[Moment]


def tag_label(tag: str) -> str:
    if match := MATE.fullmatch(tag):
        return f"{match.group(1).capitalize()} mate in {match.group(2)}"
    if tag.startswith(PREFIX):
        return f"Allowed a {fork_label(tag).lower()}"
    if tag.startswith(f"missed_{PREFIX}"):
        return f"Missed a {fork_label(tag.removeprefix('missed_')).lower()}"
    return LABELS[tag]


def build_game_analysis(game: Game, own: GameReason, opponent: GameReason, moments: list[GameMoment]) -> GameAnalysis:
    """The headline is the error that explains the result, so a win shows the opponent's."""
    deciding = opponent if game.result == Result.WIN else own
    return GameAnalysis(
        decided_by=tag_label(deciding.decided_by),
        moments=[
            Moment(
                ply=moment.ply,
                move_number=moment.ply // 2 + 1,
                player=game.black if moment.ply % 2 else game.white,
                is_decisive=moment.is_decisive,
                win_lost=moment.win_lost,
                labels=[tag_label(tag) for tag in moment.tags],
            )
            for moment in moments
        ],
    )
