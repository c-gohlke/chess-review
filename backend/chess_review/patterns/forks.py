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
    # Forks the player could have played but didn't.
    losses_with_missed_fork: int
    missed_kinds: list[ForkKind]


def fork_label(tag: str) -> str:
    piece, _, family = tag.removeprefix(PREFIX).partition("_")
    name = f"{piece.capitalize()} fork"
    return f"{name}, {FAMILIES[family]}" if family else name


def _kinds(losses: Sequence[GameReason], prefix: str) -> tuple[int, list[ForkKind]]:
    """A game with two kinds of fork counts once for each kind, but once in the total."""
    forks_by_game = [
        [tag.removeprefix("missed_") for tag in set(reason.tags) if tag.startswith(prefix)] for reason in losses
    ]
    counts = Counter(fork_label(tag) for forks in forks_by_game for tag in forks)
    kinds = [ForkKind(name, count) for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
    return sum(1 for forks in forks_by_game if forks), kinds


def summarize_forks(losses: Sequence[GameReason]) -> ForkSummary:
    with_fork, kinds = _kinds(losses, PREFIX)
    with_missed_fork, missed_kinds = _kinds(losses, f"missed_{PREFIX}")
    return ForkSummary(
        analysed_losses=len(losses),
        losses_with_fork=with_fork,
        decided_by_fork=sum(1 for reason in losses if reason.decided_by == "fork"),
        kinds=kinds,
        losses_with_missed_fork=with_missed_fork,
        missed_kinds=missed_kinds,
    )
