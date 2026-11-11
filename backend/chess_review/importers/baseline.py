"""Samples rapid Chess.com games of players in a rating band, as a baseline to compare a player against.

Chess.com has no random-game endpoint. Country player lists give a few seeds per band; rapid pairing is by rating, so
their opponents are mostly in the band too, and the rest of the sample comes from picking among those at random.
"""

import argparse
import random
import time
from pathlib import Path
from typing import Any

import httpx2

from chess_review.analysis.positions import analyse_games
from chess_review.db import Game, connect, insert_games, list_all_games
from chess_review.importers.chesscom import HEADERS, archive_urls, get, parse_game
from chess_review.themes.classify import classify_games

COUNTRY_API = "https://api.chess.com/pub/country"
STATS_API = "https://api.chess.com/pub/player"
# Lowest rating of each sampled band.
BANDS = [1600, 1900]
WIDTH = 100
# A few games each, so no single player's habits dominate a band.
GAMES_PER_PLAYER = 5
SEEDS = 10
# A seed whose last rapid game is older than this has a stale rating.
SEED_ACTIVE_DAYS = 90
COUNTRIES = ["US", "IN", "GB", "DE", "FR", "ES", "BR", "RU", "NL", "SE", "PL", "IT", "CA", "AU", "TR", "AR", "MX", "PH"]

Raw = dict[str, Any]


def baseline_path(db_path: Path, band: int) -> Path:
    return db_path.with_name(f"baseline-{band}.sqlite3")


def _in_band(rating: int, band: int) -> bool:
    return band <= rating < band + WIDTH


def _sides(raw: Raw, username: str) -> tuple[Raw, Raw]:
    white, black = raw["white"], raw["black"]
    return (white, black) if white["username"].lower() == username.lower() else (black, white)


def _rapid(raws: list[Raw]) -> list[Raw]:
    return [raw for raw in raws if raw.get("time_class") == "rapid" and raw.get("rules") == "chess"]


def band_games(raws: list[Raw], username: str, band: int) -> list[Game]:
    """The player's most recent rapid games played while rated in the band."""
    games = []
    for raw in sorted(_rapid(raws), key=lambda raw: -int(raw["end_time"])):
        game = parse_game(raw, username)
        if game is not None and _in_band(_sides(raw, username)[0]["rating"], band):
            games.append(game)
    return games[:GAMES_PER_PLAYER]


def band_opponents(raws: list[Raw], username: str, band: int) -> set[str]:
    opponents = (_sides(raw, username)[1] for raw in _rapid(raws))
    return {opponent["username"].lower() for opponent in opponents if _in_band(opponent["rating"], band)}


def _latest_month(client: httpx2.Client, username: str) -> list[Raw]:
    urls = archive_urls(client, username)
    games: list[Raw] = get(client, urls[-1]).json()["games"] if urls else []
    return games


def _is_active_in_band(client: httpx2.Client, username: str, band: int) -> bool:
    try:
        rapid = get(client, f"{STATS_API}/{username}/stats").json().get("chess_rapid", {}).get("last")
    except httpx2.HTTPStatusError:
        # Closed accounts stay on the country lists.
        return False
    return (
        rapid is not None and _in_band(rapid["rating"], band) and time.time() - rapid["date"] < SEED_ACTIVE_DAYS * 86400
    )


def find_seeds(client: httpx2.Client, band: int, rng: random.Random) -> list[str]:
    """At most one seed per country, so the sample does not grow out of one country's circle."""
    seeds = []
    for country in rng.sample(COUNTRIES, len(COUNTRIES)):
        try:
            players: list[str] = get(client, f"{COUNTRY_API}/{country}/players").json()["players"]
        except httpx2.HTTPStatusError:
            # Chess.com answers 404 for some countries' lists, the US among them.
            print(f"no player list for {country}", flush=True)
            continue
        candidates = (
            player for player in rng.sample(players, len(players)) if _is_active_in_band(client, player, band)
        )
        seed = next(candidates, None)
        if seed is None:
            continue
        print(f"seed {seed} from {country}", flush=True)
        seeds.append(seed)
        if len(seeds) == SEEDS:
            break
    return seeds


def sample_band(client: httpx2.Client, band: int, target: int, rng: random.Random, exclude: set[str]) -> list[Game]:
    pool = [seed for seed in find_seeds(client, band, rng) if seed not in exclude]
    seen = exclude | set(pool)
    games: list[Game] = []
    while pool and len(games) < target:
        username = pool.pop(rng.randrange(len(pool)))
        try:
            raws = _latest_month(client, username)
        except httpx2.HTTPStatusError:
            continue
        games.extend(band_games(raws, username, band))
        new = band_opponents(raws, username, band) - seen
        seen |= new
        pool.extend(new)
        print(f"{len(games)}/{target} games, {len(pool)} players queued", flush=True)
    return games[:target]


def sample(db_path: Path, band: int, target: int, exclude: set[str]) -> None:
    with httpx2.Client(headers=HEADERS, timeout=60) as client:
        games = sample_band(client, band, target, random.Random(), exclude)
    conn = connect(baseline_path(db_path, band))
    print(f"{insert_games(conn, games)} games stored", flush=True)
    conn.close()


def analyse(db_path: Path, band: int, stockfish_path: Path, workers: int) -> None:
    path = baseline_path(db_path, band)
    conn = connect(path)
    games = list_all_games(conn)
    conn.close()
    analyse_games(path, games, stockfish_path, workers, lambda done, total: print(f"{done}/{total}", flush=True))
    classify_games(path, games)


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    sample_parser = commands.add_parser("sample")
    analyse_parser = commands.add_parser("analyse")
    for command in (sample_parser, analyse_parser):
        command.add_argument("db_path", type=Path, help="the main database; the baseline is stored next to it")
        command.add_argument("band", type=int, choices=BANDS, help="lowest rating of the band, e.g. 1600 for 1600-1699")
    sample_parser.add_argument("--games", type=int, required=True)
    sample_parser.add_argument("--exclude", nargs="*", default=[], help="players never to sample, e.g. the app's own")
    analyse_parser.add_argument("stockfish_path", type=Path)
    analyse_parser.add_argument("--workers", type=int, required=True)
    args = parser.parse_args()
    if args.command == "sample":
        sample(args.db_path, args.band, args.games, {name.lower() for name in args.exclude})
    else:
        analyse(args.db_path, args.band, args.stockfish_path, args.workers)


if __name__ == "__main__":
    main()
