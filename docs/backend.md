# Backend

Python 3.12+, one package under `backend/`.

## Tools

| Tool | Role |
|------|------|
| FastAPI | HTTP API. Serves the OpenAPI schema the frontend client is generated from. |
| uvicorn | ASGI server that runs the FastAPI app. |
| python-chess | PGN parsing, board state, move generation, UCI engine driver. |
| Stockfish | Position evaluation. Run as a subprocess through python-chess's UCI interface. |
| SQLite | Storage for imported games, analysed mistakes and puzzle schedule. Single file, no server. |
| httpx | Client for the Lichess and Chess.com APIs. |

## Modules

Mirrors the pipeline in the README.

```
backend/chess_review/
  importers/    Lichess, Chess.com, PGN file -> Game records
  analysis/     Stockfish evaluation, mistake detection
  themes/       Classify a mistake into a beginner theme
  patterns/     Aggregate mistakes across games
  puzzles/      Build puzzles from positions, schedule review
  api/          FastAPI routers, one per pipeline stage
  db/           SQLite schema and queries
```

Each stage takes plain data in and returns plain data out. The engine is only touched from
`analysis/`, and the network only from `importers/`, so everything else is unit-testable without
mocks.

## Engine

Stockfish is a required external binary. Its path comes from an environment variable read at
startup, never at import time. Analysis is the slow part of the system, so results are stored
per position and never recomputed.

## Run

```
uv run --directory backend uvicorn chess_review.api.app:create_app --factory --reload
uv run --directory backend pytest
```
