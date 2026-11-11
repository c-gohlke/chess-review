import math
import re
import statistics
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import Literal

import chess

from chess_review.db import Game, PositionAnalysis, Result

Colour = Literal["white", "black"]

NO_VARIATION = "No named variation"
UNKNOWN_OPENING = "Unknown opening"
LONDON = "London System"
LONDON_WORDS = re.compile(r" ?London(?: System)?")

ECO_URL = re.compile(r'^\[ECOUrl ".*/openings/(.+)"\]$', re.MULTILINE)
# Everything after the first move number is a move list, not part of the opening's name.
MOVES = re.compile(r"(?: with)?[ .]+\d.*$")
FAMILY = re.compile(r".*?\b(?:Defense|Opening|Game|Gambit|Attack|System)\b")
# Chess.com slugs drop apostrophes.
# The position after Black's 10th move.
MOVE_10_PLY = 20
# In pawns. Mates count as the cap, and one crushing game can't swamp an opening's mean.
EVAL_CAP = 10.0
# Comments, move numbers and the result, leaving only the SAN moves.
MOVE_TEXT_NOISE = re.compile(r"\{[^}]*\}|\d+\.+|1-0|0-1|1/2-1/2|\*")
POSSESSIVES = {
    "Alekhines": "Alekhine's",
    "Birds": "Bird's",
    "Bishops": "Bishop's",
    "Kings": "King's",
    "Owens": "Owen's",
    "Petrovs": "Petrov's",
    "Queens": "Queen's",
}


@dataclass(frozen=True)
class OpeningStats:
    name: str
    games: int
    wins: int
    draws: int
    losses: int
    net: float  # points above or below scoring 50%
    # Engine evaluation after move 10 in pawns, from the player's side; None when no game has one.
    eval_mean: float | None
    eval_median: float | None
    variations: list["OpeningStats"]


@dataclass(frozen=True)
class OpeningSummary:
    white: list[OpeningStats]
    black: list[OpeningStats]


def colour_played(game: Game) -> Colour:
    return "white" if game.white.lower() == game.username else "black"


def parse_opening(pgn: str) -> tuple[str, str]:
    match = ECO_URL.search(pgn)
    if match is None or match.group(1) == "Undefined":
        return UNKNOWN_OPENING, NO_VARIATION

    name = MOVES.sub("", match.group(1).replace("-", " "))
    name = " ".join(POSSESSIVES.get(word, word) for word in name.split())
    family_match = FAMILY.match(name)
    family = family_match.group() if family_match else name
    variation = name.removeprefix(family).strip()

    # Chess.com files London games under the Queen's Pawn and Indian Game families.
    if "London" in variation:
        family = LONDON
        variation = LONDON_WORDS.sub("", variation).strip()

    return family, variation or NO_VARIATION


@cache
def position_after_move_10(pgn: str) -> str | None:
    """EPD after Black's 10th move, or None for a shorter game.

    Pushes only the first moves instead of parsing the whole PGN, which is several times slower; cached because the
    openings page needs it for every game on each request.
    """
    sans = MOVE_TEXT_NOISE.sub(" ", pgn.split("\n\n", 1)[-1]).split()[:MOVE_10_PLY]
    if len(sans) < MOVE_10_PLY:
        return None
    board = chess.Board()
    for san in sans:
        board.push_san(san)
    return board.epd()


def eval_after_move_10(game: Game, analyses: Mapping[str, PositionAnalysis]) -> float | None:
    position = position_after_move_10(game.pgn)
    analysis = analyses.get(position) if position is not None else None
    if analysis is None:
        return None
    if analysis.mate == 0:
        # Checkmate on the board, with White to move after move 10: Black has mated.
        white_pawns = -EVAL_CAP
    elif analysis.mate is not None:
        white_pawns = math.copysign(EVAL_CAP, analysis.mate)
    else:
        assert analysis.cp is not None
        white_pawns = max(-EVAL_CAP, min(EVAL_CAP, analysis.cp / 100))
    return white_pawns if colour_played(game) == "white" else -white_pawns


Outcome = tuple[Result, float | None]


def _stats(name: str, outcomes: list[Outcome], variations: list[OpeningStats]) -> OpeningStats:
    results = [result for result, _ in outcomes]
    evals = [evaluation for _, evaluation in outcomes if evaluation is not None]
    wins = results.count(Result.WIN)
    losses = results.count(Result.LOSS)
    return OpeningStats(
        name=name,
        games=len(results),
        wins=wins,
        draws=results.count(Result.DRAW),
        losses=losses,
        net=(wins - losses) / 2,
        eval_mean=statistics.mean(evals) if evals else None,
        eval_median=statistics.median(evals) if evals else None,
        variations=variations,
    )


def _families(games: list[Game], analyses: Mapping[str, PositionAnalysis]) -> list[OpeningStats]:
    grouped: defaultdict[str, defaultdict[str, list[Outcome]]] = defaultdict(lambda: defaultdict(list))
    for game in games:
        family, variation = parse_opening(game.pgn)
        grouped[family][variation].append((game.result, eval_after_move_10(game, analyses)))

    families = []
    for family, variations in grouped.items():
        stats = [_stats(name, outcomes, []) for name, outcomes in variations.items()]
        stats.sort(key=lambda variation: -variation.games)
        all_outcomes = [outcome for outcomes in variations.values() for outcome in outcomes]
        families.append(_stats(family, all_outcomes, stats))
    return sorted(families, key=lambda family: (-family.games, family.net))


def summarize_openings(games: list[Game], analyses: Mapping[str, PositionAnalysis]) -> OpeningSummary:
    as_white = [game for game in games if colour_played(game) == "white"]
    as_black = [game for game in games if colour_played(game) == "black"]
    return OpeningSummary(white=_families(as_white, analyses), black=_families(as_black, analyses))
