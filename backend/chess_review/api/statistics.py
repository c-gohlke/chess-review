from fastapi import APIRouter

from chess_review.api.games import Db
from chess_review.db import list_loss_reasons
from chess_review.patterns.forks import ForkSummary, summarize_forks

router = APIRouter()


@router.get("/api/statistics/forks")
def get_fork_statistics(conn: Db, username: str) -> ForkSummary:
    return summarize_forks(list_loss_reasons(conn, username))
