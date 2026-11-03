"""Engine pass over every position of a player's games.

Slow and resumable: results are saved in batches and analysed positions are skipped on the next run.
Newest games go first, so a partial run already covers the games that matter most.
"""

import argparse
import io
from collections.abc import Callable, Iterator, Sequence
from multiprocessing import get_context
from pathlib import Path

import chess
import chess.engine
import chess.pgn

from chess_review.db import Game, PositionAnalysis, connect, insert_position_analyses, list_games, stored_positions

NODES = 100_000
PV_MOVES = 8
HASH_MB = 32
# Small, so progress moves steadily; each worker keeps its engine open, so batches cost little.
BATCH = 4
SAVE_EVERY = 400

_engine: chess.engine.SimpleEngine | None = None
_stockfish_path = ""


def game_boards(pgn: str) -> Iterator[chess.Board]:
    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game is not None
    board = game.board()
    yield board.copy(stack=False)
    for move in game.mainline_moves():
        board.push(move)
        yield board.copy(stack=False)


def _open_engine() -> chess.engine.SimpleEngine:
    engine = chess.engine.SimpleEngine.popen_uci(_stockfish_path)
    engine.configure({"Threads": 1, "Hash": HASH_MB})
    return engine


def _init_worker(stockfish_path: str) -> None:
    global _stockfish_path
    _stockfish_path = stockfish_path


def analyse_board(engine: chess.engine.SimpleEngine, fen: str) -> PositionAnalysis:
    board = chess.Board(fen)
    info = engine.analyse(board, chess.engine.Limit(nodes=NODES))
    score = info["score"].white()
    pv = [move.uci() for move in info.get("pv", [])[:PV_MOVES]]
    return PositionAnalysis(position=board.epd(), cp=score.score(), mate=score.mate(), pv=" ".join(pv))


def _analyse_batch(fens: list[str]) -> list[PositionAnalysis]:
    global _engine
    if _engine is None:
        _engine = _open_engine()
    results = []
    for fen in fens:
        try:
            results.append(analyse_board(_engine, fen))
        except chess.engine.EngineError:
            # A crashed engine costs one position; the next run retries it.
            _engine = _open_engine()
    return results


def pending_positions(db_path: Path, games: Sequence[Game]) -> list[str]:
    conn = connect(db_path)
    done = stored_positions(conn)
    pending: dict[str, str] = {}
    for game in games:
        for board in game_boards(game.pgn):
            position = board.epd()
            if position not in done:
                pending.setdefault(position, board.fen())
    conn.close()
    return list(pending.values())


def analyse_games(
    db_path: Path,
    games: Sequence[Game],
    stockfish_path: Path,
    workers: int,
    on_progress: Callable[[int, int], None],
) -> None:
    fens = pending_positions(db_path, games)
    on_progress(0, len(fens))
    batches = [fens[start : start + BATCH] for start in range(0, len(fens), BATCH)]
    conn = connect(db_path)
    buffered: list[PositionAnalysis] = []
    finished = 0
    # Spawned, because this also runs in a thread of the API server, where forking is unsafe.
    with get_context("spawn").Pool(workers, _init_worker, (str(stockfish_path),)) as pool:
        for results in pool.imap_unordered(_analyse_batch, batches):
            buffered.extend(results)
            finished += len(results)
            if len(buffered) >= SAVE_EVERY:
                insert_position_analyses(conn, buffered)
                buffered = []
            on_progress(finished, len(fens))
    insert_position_analyses(conn, buffered)
    conn.close()


def analyse_all(db_path: Path, username: str, stockfish_path: Path, workers: int) -> None:
    conn = connect(db_path)
    games = list_games(conn, username)
    conn.close()
    analyse_games(db_path, games, stockfish_path, workers, lambda done, total: print(f"{done}/{total}", flush=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("db_path", type=Path)
    parser.add_argument("username")
    parser.add_argument("stockfish_path", type=Path)
    parser.add_argument("--workers", type=int, required=True)
    args = parser.parse_args()
    analyse_all(args.db_path, args.username, args.stockfish_path, args.workers)


if __name__ == "__main__":
    main()
