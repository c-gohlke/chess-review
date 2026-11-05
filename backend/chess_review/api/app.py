import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

from chess_review.api.analysis import router as analysis_router
from chess_review.api.evaluation import router as evaluation_router
from chess_review.api.games import router as games_router
from chess_review.api.openings import router as openings_router
from chess_review.api.statistics import router as statistics_router
from chess_review.themes.runs import AnalysisRuns, engine_job, game_engine


class AppFiles(StaticFiles):
    """Serves the built frontend; the page is revalidated on every load, so a deploy shows at once."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if not path.startswith("assets/"):
            response.headers["Cache-Control"] = "no-cache"
        return response


def create_app(static_dir: Path, db_path: Path, stockfish_path: Path) -> FastAPI:
    app = FastAPI()
    app.include_router(games_router)
    app.include_router(openings_router)
    app.include_router(evaluation_router)
    app.include_router(statistics_router)
    app.include_router(analysis_router)
    app.state.db_path = db_path
    app.state.stockfish_path = stockfish_path
    # Leaves two cores free, so the app stays responsive during a run.
    workers = max(1, (os.cpu_count() or 1) - 2)
    app.state.analysis_runs = AnalysisRuns(engine_job(db_path, stockfish_path, workers))
    app.state.analyse_game = game_engine(db_path, stockfish_path, workers)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/", AppFiles(directory=static_dir, html=True))
    return app


def create_app_from_env() -> FastAPI:
    return create_app(
        Path(os.environ["CHESS_REVIEW_STATIC_DIR"]),
        Path(os.environ["CHESS_REVIEW_DB"]),
        Path(os.environ["CHESS_REVIEW_STOCKFISH"]),
    )
