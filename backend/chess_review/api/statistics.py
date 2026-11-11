from fastapi import APIRouter

from chess_review.api.games import Db
from chess_review.db import list_game_reasons, list_loss_reasons
from chess_review.patterns.forks import ForkSummary, summarize_forks
from chess_review.patterns.pawn_pushes import PawnPushSummary, summarize_pawn_pushes

router = APIRouter()


@router.get("/api/statistics/forks")
def get_fork_statistics(conn: Db, username: str) -> ForkSummary:
    return summarize_forks(list_loss_reasons(conn, username))


@router.get("/api/statistics/pawn-pushes")
def get_pawn_push_statistics(conn: Db, username: str) -> PawnPushSummary:
    return summarize_pawn_pushes(list_game_reasons(conn, username))
