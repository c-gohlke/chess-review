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
)
"""


class Result(StrEnum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"


@dataclass(frozen=True)
class Game:
    source: str
    source_id: str
    username: str
    white: str
    black: str
    result: Result
    time_class: str
    played_at: datetime
    pgn: str
    id: int | None = None


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
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
                "time_class": game.time_class,
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
        time_class=row["time_class"],
        played_at=datetime.fromisoformat(row["played_at"]),
        pgn=row["pgn"],
    )


def list_games(conn: sqlite3.Connection) -> list[Game]:
    rows = conn.execute("SELECT * FROM games ORDER BY id DESC").fetchall()
    return [_row_to_game(row) for row in rows]


def get_game(conn: sqlite3.Connection, game_id: int) -> Game | None:
    row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    return _row_to_game(row) if row is not None else None
