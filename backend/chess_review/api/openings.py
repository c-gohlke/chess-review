from fastapi import APIRouter

from chess_review.api.games import Db
from chess_review.db import list_games
from chess_review.patterns.openings import OpeningSummary, summarize_openings

router = APIRouter()


@router.get("/api/openings")
def get_openings(conn: Db) -> OpeningSummary:
    return summarize_openings(list_games(conn))
