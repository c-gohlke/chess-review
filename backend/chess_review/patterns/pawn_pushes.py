from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from chess_review.db import GameReason

Wing = Literal["queenside", "kingside"]
Timing = Literal["early", "late"]
WINGS: list[Wing] = ["queenside", "kingside"]
TIMINGS: list[Timing] = ["early", "late"]


@dataclass(frozen=True)
class PawnPushCount:
    wing: Wing
    timing: Timing
    games: int


@dataclass(frozen=True)
class PawnPushSummary:
    analysed_games: int
    counts: list[PawnPushCount]


def summarize_pawn_pushes(reasons: Sequence[GameReason]) -> PawnPushSummary:
    """Counts games, so several costly pushes on one wing in a game count once."""
    return PawnPushSummary(
        analysed_games=len(reasons),
        counts=[
            PawnPushCount(wing, timing, sum(1 for reason in reasons if f"{wing}_pawns_{timing}" in reason.tags))
            for wing in WINGS
            for timing in TIMINGS
        ],
    )
