import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def create_app(static_dir: Path | None = None) -> FastAPI:
    app = FastAPI()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    if static_dir is None:
        env_static_dir = os.environ.get("CHESS_REVIEW_STATIC_DIR")
        static_dir = Path(env_static_dir) if env_static_dir else None

    if static_dir is not None:
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
