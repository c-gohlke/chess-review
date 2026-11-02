from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from chess_review.db import GameReason

PREFIX = "fork_"
FAMILIES = {
    "royal": "royal (king and queen)",
    "family": "family (king, queen and more)",
    "grand": "grand (king, queen and two rooks)",
}


@dataclass(frozen=True)
class ForkKind:
    name: str
    losses: int


@dataclass(frozen=True)
class ForkSummary:
    analysed_losses: int
    losses_with_fork: int
    decided_by_fork: int
    kinds: list[ForkKind]


def fork_label(tag: str) -> str:
    piece, _, family = tag.removeprefix(PREFIX).partition("_")
    name = f"{piece.capitalize()} fork"
    return f"{name}, {FAMILIES[family]}" if family else name


def summarize_forks(losses: Sequence[GameReason]) -> ForkSummary:
    """A game with two kinds of fork counts once for each kind, but once in `losses_with_fork`."""
    forks_by_game = [[tag for tag in set(reason.tags) if tag.startswith(PREFIX)] for reason in losses]
    counts = Counter(fork_label(tag) for forks in forks_by_game for tag in forks)
    return ForkSummary(
        analysed_losses=len(losses),
        losses_with_fork=sum(1 for forks in forks_by_game if forks),
        decided_by_fork=sum(1 for reason in losses if reason.decided_by == "fork"),
        kinds=[ForkKind(name, count) for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))],
    )
