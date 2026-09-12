import sqlite3
from collections.abc import Generator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from chess_review.db import Result, TimeClass, connect, get_game, list_games
from chess_review.importers.chesscom import import_games

router = APIRouter()


class GameSummary(BaseModel):
    id: int
    white: str
    black: str
    result: Result
    time_class: TimeClass
    played_at: datetime


class GameDetail(GameSummary):
    pgn: str


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


@router.get("/api/games")
def get_games(conn: Db) -> list[GameSummary]:
    return [GameSummary.model_validate(game, from_attributes=True) for game in list_games(conn)]


@router.get("/api/games/{game_id}")
def get_game_detail(game_id: int, conn: Db) -> GameDetail:
    game = get_game(conn, game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    return GameDetail.model_validate(game, from_attributes=True)
