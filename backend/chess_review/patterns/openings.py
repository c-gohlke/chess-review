import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from chess_review.db import Game, Result

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


def _stats(name: str, results: list[Result], variations: list[OpeningStats]) -> OpeningStats:
    wins = results.count(Result.WIN)
    losses = results.count(Result.LOSS)
    return OpeningStats(
        name=name,
        games=len(results),
        wins=wins,
        draws=results.count(Result.DRAW),
        losses=losses,
        net=(wins - losses) / 2,
        variations=variations,
    )


def _families(games: list[Game]) -> list[OpeningStats]:
    grouped: defaultdict[str, defaultdict[str, list[Result]]] = defaultdict(lambda: defaultdict(list))
    for game in games:
        family, variation = parse_opening(game.pgn)
        grouped[family][variation].append(game.result)

    families = []
    for family, variations in grouped.items():
        stats = [_stats(name, results, []) for name, results in variations.items()]
        stats.sort(key=lambda variation: -variation.games)
        all_results = [result for results in variations.values() for result in results]
        families.append(_stats(family, all_results, stats))
    return sorted(families, key=lambda family: (family.net, -family.games))


def summarize_openings(games: list[Game]) -> OpeningSummary:
    as_white = [game for game in games if colour_played(game) == "white"]
    as_black = [game for game in games if colour_played(game) == "black"]
    return OpeningSummary(white=_families(as_white), black=_families(as_black))
