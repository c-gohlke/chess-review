# Architecture

chess-review is two deployable units: a Python backend that does the chess work, and a
TypeScript web app that presents it. They talk over an HTTP API described by an OpenAPI schema.

```
Lichess / Chess.com / PGN
          |
          v
  +-----------------+   OpenAPI    +---------------------+
  |  backend (py)   | <----------> |  frontend (ts)      |
  |  FastAPI        |              |  Vite + React       |
  |  python-chess   |              |  Tailwind CSS       |
  |  Stockfish      |              |  react-chessboard   |
  |  SQLite         |              |                     |
  +-----------------+              +---------------------+
```

The frontend is a single responsive web app. It runs in desktop browsers and on phones without a
separate mobile codebase. If store distribution is ever needed, the same app can be wrapped with
Capacitor; nothing in the current design depends on that.

In production the backend also serves the built frontend, so there is a single process and a
single origin.

## Documents

| File | Covers |
|------|--------|
| [backend.md](backend.md) | Python runtime: API, chess analysis, engine, storage |
| [frontend.md](frontend.md) | Web app: framework, styling, board, API client |
| [tooling.md](tooling.md) | Linting, formatting, type checking, testing on both sides |

## Repository layout

```
backend/    Python package, tests, engine config
frontend/   Vite project
docs/       this folder
```

## Principles

- The backend owns all chess logic. The frontend never evaluates positions; it only validates
  legal moves locally so the board feels responsive.
- Types cross the boundary once, through the OpenAPI schema. No hand-written API types on the
  frontend.
- One tool per job. A dependency has to replace code we would otherwise write ourselves.
