import sqlite3

from fastapi import APIRouter
from pydantic import AwareDatetime

from chess_review.api.games import Db, GameListItem, list_item
from chess_review.db import Game, TimeClass, get_position_analyses, list_games
from chess_review.patterns.openings import (
    Colour,
    OpeningSummary,
    colour_played,
    parse_opening,
    position_after_move_10,
    summarize_openings,
)

router = APIRouter()


def _filtered_games(
    conn: sqlite3.Connection, username: str, since: AwareDatetime | None, time_class: TimeClass | None
) -> list[Game]:
    return [
        game
        for game in list_games(conn, username)
        if (since is None or game.played_at >= since) and (time_class is None or game.time_class == time_class)
    ]


@router.get("/api/openings")
def get_openings(
    conn: Db, username: str, since: AwareDatetime | None = None, time_class: TimeClass | None = None
) -> OpeningSummary:
    games = _filtered_games(conn, username, since, time_class)
    positions = [position for game in games if (position := position_after_move_10(game.pgn)) is not None]
    return summarize_openings(games, get_position_analyses(conn, positions))


@router.get("/api/openings/games")
def get_opening_games(
    conn: Db,
    username: str,
    family: str,
    variation: str,
    colour: Colour,
    since: AwareDatetime | None = None,
    time_class: TimeClass | None = None,
) -> list[GameListItem]:
    return [
        list_item(conn, game)
        for game in _filtered_games(conn, username, since, time_class)
        if colour_played(game) == colour and parse_opening(game.pgn) == (family, variation)
    ]
