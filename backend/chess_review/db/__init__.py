import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL,
    white TEXT NOT NULL,
    black TEXT NOT NULL,
    result TEXT NOT NULL,
    time_class TEXT NOT NULL,
    played_at TEXT NOT NULL,
    pgn TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluations (
    position TEXT PRIMARY KEY,
    cp INTEGER,
    mate INTEGER
);

CREATE TABLE IF NOT EXISTS position_analyses (
    position TEXT PRIMARY KEY,
    cp INTEGER,
    mate INTEGER,
    pv TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS games_by_rating_pool ON games (username, time_class, played_at);
"""


class Result(StrEnum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"


class TimeClass(StrEnum):
    DAILY = "daily"
    RAPID = "rapid"
    BLITZ = "blitz"
    BULLET = "bullet"


@dataclass(frozen=True)
class Game:
    source: str
    source_id: str
    username: str
    white: str
    black: str
    result: Result
    time_class: TimeClass
    played_at: datetime
    pgn: str
    id: int | None = None


@dataclass(frozen=True)
class Evaluation:
    """From White's point of view. Exactly one of the two is set; mate 0 means the position is checkmate."""

    cp: int | None
    mate: int | None


@dataclass(frozen=True)
class PositionAnalysis:
    """A fast engine pass, from White's point of view. `pv` is space-separated UCI moves, best move first."""

    position: str
    cp: int | None
    mate: int | None
    pv: str


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def insert_games(conn: sqlite3.Connection, games: list[Game]) -> int:
    cursor = conn.executemany(
        """
        INSERT OR IGNORE INTO games
            (source, source_id, username, white, black, result, time_class, played_at, pgn)
        VALUES (:source, :source_id, :username, :white, :black, :result, :time_class, :played_at, :pgn)
        """,
        [
            {
                "source": game.source,
                "source_id": game.source_id,
                "username": game.username,
                "white": game.white,
                "black": game.black,
                "result": game.result.value,
                "time_class": game.time_class.value,
                "played_at": game.played_at.isoformat(),
                "pgn": game.pgn,
            }
            for game in games
        ],
    )
    conn.commit()
    return cursor.rowcount


def _row_to_game(row: sqlite3.Row) -> Game:
    return Game(
        id=row["id"],
        source=row["source"],
        source_id=row["source_id"],
        username=row["username"],
        white=row["white"],
        black=row["black"],
        result=Result(row["result"]),
        time_class=TimeClass(row["time_class"]),
        played_at=datetime.fromisoformat(row["played_at"]),
        pgn=row["pgn"],
    )


def list_usernames(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT username FROM games GROUP BY username ORDER BY MIN(id)").fetchall()
    return [row["username"] for row in rows]


def list_games(conn: sqlite3.Connection, username: str) -> list[Game]:
    rows = conn.execute("SELECT * FROM games WHERE username = ? ORDER BY id DESC", (username,)).fetchall()
    return [_row_to_game(row) for row in rows]


def list_games_page(conn: sqlite3.Connection, username: str, limit: int, offset: int) -> list[Game]:
    rows = conn.execute(
        "SELECT * FROM games WHERE username = ? ORDER BY id DESC LIMIT ? OFFSET ?", (username, limit, offset)
    ).fetchall()
    return [_row_to_game(row) for row in rows]


def previous_game(conn: sqlite3.Connection, game: Game) -> Game | None:
    """The same player's game before this one in the same time control, which has its own rating."""
    row = conn.execute(
        """
        SELECT * FROM games
        WHERE username = ? AND time_class = ? AND played_at < ?
        ORDER BY played_at DESC
        LIMIT 1
        """,
        (game.username, game.time_class.value, game.played_at.isoformat()),
    ).fetchone()
    return _row_to_game(row) if row is not None else None


def get_game(conn: sqlite3.Connection, game_id: int) -> Game | None:
    row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    return _row_to_game(row) if row is not None else None


def get_evaluation(conn: sqlite3.Connection, position: str) -> Evaluation | None:
    row = conn.execute("SELECT cp, mate FROM evaluations WHERE position = ?", (position,)).fetchone()
    return Evaluation(cp=row["cp"], mate=row["mate"]) if row is not None else None


def insert_evaluation(conn: sqlite3.Connection, position: str, evaluation: Evaluation) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO evaluations (position, cp, mate) VALUES (?, ?, ?)",
        (position, evaluation.cp, evaluation.mate),
    )
    conn.commit()


def stored_positions(conn: sqlite3.Connection) -> set[str]:
    return {row["position"] for row in conn.execute("SELECT position FROM position_analyses")}


def load_position_analyses(conn: sqlite3.Connection) -> dict[str, PositionAnalysis]:
    rows = conn.execute("SELECT position, cp, mate, pv FROM position_analyses")
    return {row["position"]: PositionAnalysis(row["position"], row["cp"], row["mate"], row["pv"]) for row in rows}


def insert_position_analyses(conn: sqlite3.Connection, analyses: list[PositionAnalysis]) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO position_analyses (position, cp, mate, pv) VALUES (?, ?, ?, ?)",
        [(analysis.position, analysis.cp, analysis.mate, analysis.pv) for analysis in analyses],
    )
    conn.commit()
