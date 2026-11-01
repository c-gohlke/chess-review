from fastapi import APIRouter
from pydantic import AwareDatetime

from chess_review.api.games import Db
from chess_review.db import TimeClass, list_games
from chess_review.patterns.openings import OpeningSummary, summarize_openings

router = APIRouter()


@router.get("/api/openings")
def get_openings(conn: Db, since: AwareDatetime | None = None, time_class: TimeClass | None = None) -> OpeningSummary:
    games = [
        game
        for game in list_games(conn)
        if (since is None or game.played_at >= since) and (time_class is None or game.time_class == time_class)
    ]
    return summarize_openings(games)
