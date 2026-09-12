# TODO: add Stockfish to this image once analysis lands.

FROM node:26-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS backend
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/chess_review/ ./chess_review/
RUN uv sync --locked --no-dev
COPY --from=frontend /app/dist /app/static

ENV CHESS_REVIEW_STATIC_DIR=/app/static
ENV CHESS_REVIEW_DB=/data/chess-review.sqlite3
VOLUME /data
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "chess_review.api.app:create_app_from_env", "--factory", "--host", "0.0.0.0", "--port", "8000"]
