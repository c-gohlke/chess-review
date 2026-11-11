from fastapi import APIRouter

from chess_review.api.games import Db
from chess_review.db import list_game_reasons, list_loss_reasons, list_win_reasons
from chess_review.patterns.forks import ForkSummary, summarize_forks
from chess_review.patterns.pawn_pushes import PawnPushSummary, summarize_pawn_pushes
from chess_review.patterns.result_reasons import ReasonSummary, summarize_result_reasons

router = APIRouter()


@router.get("/api/statistics/forks")
def get_fork_statistics(conn: Db, username: str) -> ForkSummary:
    return summarize_forks(list_loss_reasons(conn, username))


@router.get("/api/statistics/pawn-pushes")
def get_pawn_push_statistics(conn: Db, username: str) -> PawnPushSummary:
    return summarize_pawn_pushes(list_game_reasons(conn, username))


@router.get("/api/statistics/reasons")
def get_reason_statistics(conn: Db, username: str) -> ReasonSummary:
    return summarize_result_reasons(list_loss_reasons(conn, username), list_win_reasons(conn, username))
