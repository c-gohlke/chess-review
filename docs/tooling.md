# Tooling

Same rules on both sides: one linter, one formatter, strict types, tests that assert on output.

## Backend

| Tool | Role |
|------|------|
| uv | Dependency and virtualenv management. |
| Ruff | Linter and formatter. Line length 120. |
| MyPy strict | Type checking. No untyped code merged. |
| pytest | Test runner. |
| freezegun | Time control for scheduling tests. |
| httpx2 | HTTP client. |
| tenacity | Retries. |

Tests are split by what they need:

| Directory | Contents |
|-----------|----------|
| `backend/tests/unit` | Pure logic. No I/O, no network, no engine. |
| `backend/tests/integration` | Real Stockfish or real Lichess/Chess.com API. |

## Frontend

| Tool | Role |
|------|------|
| npm | Package management. |
| Biome | Linter and formatter in one tool. |
| TypeScript strict | Type checking. |
| Vitest | Unit tests for non-UI logic. |
| Playwright | End-to-end tests, run at both a desktop and a phone viewport. |
| openapi-typescript | Generates TypeScript types from the backend's OpenAPI schema so the two sides cannot drift. |

## Deployment

| Tool | Role |
|------|------|
| Docker | Single image that builds the frontend and runs the backend serving it, so the app deploys as one unit. |

## Shared

The OpenAPI schema is the contract. CI regenerates the frontend types from the backend and fails
if the result differs from what is committed, so the two sides cannot drift.
