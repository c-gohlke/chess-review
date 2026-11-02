import sqlite3
from collections.abc import Generator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from chess_review.db import (
    Game,
    Result,
    TimeClass,
    connect,
    get_game,
    get_game_reason,
    get_opponent_reason,
    list_game_moments,
    list_games_page,
    list_usernames,
    previous_game,
)
from chess_review.importers.chesscom import import_games
from chess_review.patterns.game_analysis import GameAnalysis, build_game_analysis
from chess_review.patterns.openings import Colour, colour_played, parse_opening
from chess_review.patterns.ratings import rating_change

router = APIRouter()


class GameSummary(BaseModel):
    id: int
    white: str
    black: str
    result: Result
    time_class: TimeClass
    played_at: datetime


class GameListItem(GameSummary):
    opening: str
    rating_change: int | None


class GameDetail(GameSummary):
    pgn: str
    colour: Colour
    analysis: GameAnalysis | None


class ImportResult(BaseModel):
    imported: int


def get_db(request: Request) -> Generator[sqlite3.Connection, None, None]:
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


Db = Annotated[sqlite3.Connection, Depends(get_db)]


@router.post("/api/import/chesscom/{username}")
def import_chesscom(username: str, conn: Db) -> ImportResult:
    return ImportResult(imported=import_games(conn, username))


def list_item(conn: sqlite3.Connection, game: Game) -> GameListItem:
    family, _ = parse_opening(game.pgn)
    return GameListItem(
        **GameSummary.model_validate(game, from_attributes=True).model_dump(),
        opening=family,
        rating_change=rating_change(game, previous_game(conn, game)),
    )


@router.get("/api/users")
def get_users(conn: Db) -> list[str]:
    return list_usernames(conn)


@router.get("/api/games")
def get_games(
    conn: Db, username: str, limit: Annotated[int, Query(ge=1, le=200)], offset: Annotated[int, Query(ge=0)]
) -> list[GameListItem]:
    return [list_item(conn, game) for game in list_games_page(conn, username, limit, offset)]


def _analysis(conn: sqlite3.Connection, game: Game, game_id: int) -> GameAnalysis | None:
    own = get_game_reason(conn, game_id)
    opponent = get_opponent_reason(conn, game_id)
    if own is None or opponent is None:
        return None
    return build_game_analysis(game, own, opponent, list_game_moments(conn, game_id))


@router.get("/api/games/{game_id}")
def get_game_detail(game_id: int, conn: Db) -> GameDetail:
    game = get_game(conn, game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    return GameDetail(
        **GameSummary.model_validate(game, from_attributes=True).model_dump(),
        pgn=game.pgn,
        colour=colour_played(game),
        analysis=_analysis(conn, game, game_id),
    )
