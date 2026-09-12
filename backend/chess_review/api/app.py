import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from chess_review.api.games import router as games_router


def create_app(static_dir: Path, db_path: Path | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(games_router)

    if db_path is None:
        env_db_path = os.environ.get("CHESS_REVIEW_DB")
        db_path = Path(env_db_path) if env_db_path else Path("data/chess-review.sqlite3")
    app.state.db_path = db_path

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/", StaticFiles(directory=static_dir, html=True))
    return app


def create_app_from_env() -> FastAPI:
    return create_app(Path(os.environ["CHESS_REVIEW_STATIC_DIR"]))
