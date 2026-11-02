from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from chess_review.api.games import Db
from chess_review.db import count_games, count_unanalysed_games
from chess_review.themes.runs import AnalysisRuns, Phase

router = APIRouter()


class AnalysisState(BaseModel):
    games: int
    unanalysed: int
    phase: Phase
    done: int
    total: int
    error: str | None
    running_player: str | None


def _runs(request: Request) -> AnalysisRuns:
    runs: AnalysisRuns = request.app.state.analysis_runs
    return runs


@router.get("/api/analysis")
def get_analysis(request: Request, conn: Db, username: str) -> AnalysisState:
    runs = _runs(request)
    status = runs.status(username)
    return AnalysisState(
        games=count_games(conn, username),
        unanalysed=count_unanalysed_games(conn, username),
        phase=status.phase,
        done=status.done,
        total=status.total,
        error=status.error,
        running_player=runs.running_player,
    )


@router.post("/api/analysis")
def start_analysis(request: Request, conn: Db, username: str) -> AnalysisState:
    if not _runs(request).start(username):
        raise HTTPException(status_code=409, detail="another player's engine run is in progress")
    return get_analysis(request, conn, username)
