import sqlite3
from datetime import UTC, datetime
from typing import Any

import httpx2
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from chess_review.db import Game, Result, TimeClass, insert_games

API = "https://api.chess.com/pub/player"
# Chess.com rejects requests without a descriptive User-Agent.
HEADERS = {"User-Agent": "chess-review (https://github.com/c-gohlke/chess-review)"}


# The API occasionally stalls on a single request; one retry is enough in practice.
@retry(retry=retry_if_exception_type(httpx2.TimeoutException), stop=stop_after_attempt(2), reraise=True)
def get(client: httpx2.Client, url: str) -> httpx2.Response:
    response = client.get(url)
    response.raise_for_status()
    return response


def archive_urls(client: httpx2.Client, username: str) -> list[str]:
    # Chess.com only serves lowercase usernames; other casings get a 301 that httpx2 does not follow.
    urls: list[str] = get(client, f"{API}/{username.lower()}/games/archives").json()["archives"]
    return urls


def parse_game(raw: dict[str, Any], username: str) -> Game | None:
    pgn = raw.get("pgn")
    if not pgn or raw.get("rules") != "chess":
        return None

    white = raw["white"]
    black = raw["black"]

    if white["username"].lower() == username.lower():
        own, opponent = white, black
    else:
        own, opponent = black, white

    if own["result"] == "win":
        result = Result.WIN
    elif opponent["result"] == "win":
        result = Result.LOSS
    else:
        result = Result.DRAW

    played_at = datetime.fromtimestamp(raw["end_time"], tz=UTC)

    return Game(
        source="chesscom",
        source_id=raw["url"],
        username=username.lower(),
        white=white["username"],
        black=black["username"],
        result=result,
        time_class=TimeClass(raw["time_class"]),
        played_at=played_at,
        pgn=pgn,
    )


def import_games(conn: sqlite3.Connection, username: str) -> int:
    with httpx2.Client(headers=HEADERS, timeout=60) as client:
        urls = archive_urls(client, username)
        games = []
        for url in urls:
            raw_games = get(client, url).json()["games"]
            for raw in raw_games:
                game = parse_game(raw, username)
                if game is not None:
                    games.append(game)
    return insert_games(conn, games)
