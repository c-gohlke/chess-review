import sqlite3
from datetime import UTC, datetime

import httpx2

from chess_review.db import Game, insert_games

API = "https://api.chess.com/pub/player"
# Chess.com rejects requests without a descriptive User-Agent.
HEADERS = {"User-Agent": "chess-review (https://github.com/c-gohlke/chess-review)"}


def get(client: httpx2.Client, url: str) -> httpx2.Response:
    # The API occasionally stalls on a single request; one retry is enough in practice.
    for attempt in range(2):
        try:
            response = client.get(url)
        except httpx2.TimeoutException:
            if attempt == 1:
                raise
            continue
        response.raise_for_status()
        return response
    raise AssertionError("unreachable")


def archive_urls(client: httpx2.Client, username: str) -> list[str]:
    urls: list[str] = get(client, f"{API}/{username}/games/archives").json()["archives"]
    return urls


def parse_game(raw: dict[str, object], username: str) -> Game | None:
    pgn = raw.get("pgn")
    if not pgn or raw.get("rules") != "chess":
        return None

    white = raw["white"]
    black = raw["black"]
    assert isinstance(white, dict) and isinstance(black, dict)

    if str(white["username"]).lower() == username.lower():
        own, opponent = white, black
    else:
        own, opponent = black, white

    if own["result"] == "win":
        result = "win"
    elif opponent["result"] == "win":
        result = "loss"
    else:
        result = "draw"

    end_time = raw["end_time"]
    assert isinstance(end_time, int)
    played_at = datetime.fromtimestamp(end_time, tz=UTC).isoformat()

    return Game(
        source="chesscom",
        source_id=str(raw["url"]),
        username=username.lower(),
        white=str(white["username"]),
        black=str(black["username"]),
        result=result,
        time_class=str(raw["time_class"]),
        played_at=played_at,
        pgn=str(pgn),
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
