import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def create_app(static_dir: Path) -> FastAPI:
    app = FastAPI()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/", StaticFiles(directory=static_dir, html=True))
    return app


def create_app_from_env() -> FastAPI:
    return create_app(Path(os.environ["CHESS_REVIEW_STATIC_DIR"]))
