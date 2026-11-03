"""Engine runs requested from the app. One at a time, because a run takes most of the machine's cores."""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from chess_review.analysis.positions import analyse_games
from chess_review.db import Game, connect, list_unanalysed_games
from chess_review.themes.classify import classify_games, classify_unanalysed

Phase = Literal["idle", "preparing", "analysing", "classifying", "failed"]
Report = Callable[[Phase, int, int], None]
Job = Callable[[str, Report], None]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunStatus:
    phase: Phase = "idle"
    done: int = 0
    total: int = 0
    error: str | None = None


def engine_job(db_path: Path, stockfish_path: Path, workers: int) -> Job:
    def run(username: str, report: Report) -> None:
        report("preparing", 0, 0)
        conn = connect(db_path)
        games = list_unanalysed_games(conn, username)
        conn.close()
        analyse_games(db_path, games, stockfish_path, workers, lambda done, total: report("analysing", done, total))
        report("classifying", 0, 0)
        classify_unanalysed(db_path, username)

    return run


def game_engine(db_path: Path, stockfish_path: Path, workers: int) -> Callable[[Game], None]:
    def analyse(game: Game) -> None:
        analyse_games(db_path, [game], stockfish_path, workers, lambda _done, _total: None)
        classify_games(db_path, [game])

    return analyse


class AnalysisRuns:
    def __init__(self, job: Job) -> None:
        self._job = job
        self._lock = threading.Lock()
        self._running: str | None = None
        self._statuses: dict[str, RunStatus] = {}
        self._thread: threading.Thread | None = None

    @property
    def running_player(self) -> str | None:
        with self._lock:
            return self._running

    def status(self, username: str) -> RunStatus:
        with self._lock:
            return self._statuses.get(username, RunStatus())

    def start(self, username: str) -> bool:
        """False when another player's run is in progress. Asking again for the same player is harmless."""
        with self._lock:
            if self._running is not None:
                return self._running == username
            self._running = username
            self._statuses[username] = RunStatus("preparing")
        self._thread = threading.Thread(target=self._run, args=(username,), daemon=True)
        self._thread.start()
        return True

    def wait(self) -> None:
        if self._thread is not None:
            self._thread.join()

    def _report(self, username: str, phase: Phase, done: int, total: int) -> None:
        with self._lock:
            self._statuses[username] = RunStatus(phase, done, total)

    def _run(self, username: str) -> None:
        final = RunStatus()
        try:
            self._job(username, lambda phase, done, total: self._report(username, phase, done, total))
        except Exception as error:
            # A background thread has nobody to raise to, so the failure goes to the status the page polls.
            logger.exception("engine run for %s failed", username)
            final = RunStatus("failed", error=str(error) or type(error).__name__)
        with self._lock:
            self._statuses[username] = final
            self._running = None
