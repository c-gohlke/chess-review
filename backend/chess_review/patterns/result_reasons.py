from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from chess_review.db import GameReason
from chess_review.patterns.forks import PREFIX
from chess_review.patterns.game_analysis import LABELS, tag_label


@dataclass(frozen=True)
class ReasonCount:
    name: str
    games: int


@dataclass(frozen=True)
class ResultReasons:
    games: int
    deciding: list[ReasonCount]  # one per game, so the counts add up to `games`
    tags: list[ReasonCount]  # a game counts once under each of its tags


@dataclass(frozen=True)
class ReasonSummary:
    losses: ResultReasons  # the player's own errors
    wins: ResultReasons  # the opponent's errors


def _tag_name(tag: str) -> str:
    # The Forks section already breaks forks down by kind.
    if tag.startswith(PREFIX):
        return "Allowed a fork"
    if tag.startswith(f"missed_{PREFIX}"):
        return "Missed a fork"
    return tag_label(tag)


def _most_common_first(names: Iterable[str]) -> list[ReasonCount]:
    counts = Counter(names)
    return [ReasonCount(name, games) for name, games in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _result_reasons(reasons: Sequence[GameReason]) -> ResultReasons:
    return ResultReasons(
        games=len(reasons),
        deciding=_most_common_first(LABELS[reason.decided_by] for reason in reasons),
        tags=_most_common_first(name for reason in reasons for name in {_tag_name(tag) for tag in reason.tags}),
    )


def summarize_result_reasons(losses: Sequence[GameReason], wins: Sequence[GameReason]) -> ReasonSummary:
    return ReasonSummary(losses=_result_reasons(losses), wins=_result_reasons(wins))
