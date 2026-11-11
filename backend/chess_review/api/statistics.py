import sqlite3
from collections.abc import Callable

from fastapi import APIRouter, Request
from pydantic import BaseModel

from chess_review.api.games import Db
from chess_review.db import GameReason, connect, list_game_reasons, list_loss_reasons, list_usernames, list_win_reasons
from chess_review.importers.baseline import BANDS, baseline_path
from chess_review.patterns.forks import ForkSummary, summarize_forks
from chess_review.patterns.pawn_pushes import PawnPushSummary, summarize_pawn_pushes
from chess_review.patterns.result_reasons import ReasonSummary, summarize_result_reasons

router = APIRouter()


class BaselineStatistics(BaseModel):
    band: int  # lowest rating of the band
    games: int  # analysed games
    forks: ForkSummary
    pawn_pushes: PawnPushSummary
    reasons: ReasonSummary


@router.get("/api/statistics/forks")
def get_fork_statistics(conn: Db, username: str) -> ForkSummary:
    return summarize_forks(list_loss_reasons(conn, username))


@router.get("/api/statistics/pawn-pushes")
def get_pawn_push_statistics(conn: Db, username: str) -> PawnPushSummary:
    return summarize_pawn_pushes(list_game_reasons(conn, username))


@router.get("/api/statistics/reasons")
def get_reason_statistics(conn: Db, username: str) -> ReasonSummary:
    return summarize_result_reasons(list_loss_reasons(conn, username), list_win_reasons(conn, username))


def _everyone(
    conn: sqlite3.Connection, list_reasons: Callable[[sqlite3.Connection, str], list[GameReason]]
) -> list[GameReason]:
    return [reason for username in list_usernames(conn) for reason in list_reasons(conn, username)]


def _baseline(band: int, conn: sqlite3.Connection) -> BaselineStatistics:
    losses = _everyone(conn, list_loss_reasons)
    games = _everyone(conn, list_game_reasons)
    return BaselineStatistics(
        band=band,
        games=len(games),
        forks=summarize_forks(losses),
        pawn_pushes=summarize_pawn_pushes(games),
        reasons=summarize_result_reasons(losses, _everyone(conn, list_win_reasons)),
    )


@router.get("/api/statistics/baselines")
def get_baselines(request: Request) -> list[BaselineStatistics]:
    """Every band that has been sampled; see importers/baseline.py."""
    baselines = []
    for band in BANDS:
        path = baseline_path(request.app.state.db_path, band)
        if path.exists():
            conn = connect(path)
            baselines.append(_baseline(band, conn))
            conn.close()
    return baselines
