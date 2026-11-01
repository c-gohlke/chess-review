from pathlib import Path

import chess
import chess.engine

from chess_review.db import Evaluation

DEPTH = 18


def evaluate(stockfish_path: Path, board: chess.Board) -> Evaluation:
    with chess.engine.SimpleEngine.popen_uci(str(stockfish_path)) as engine:
        info = engine.analyse(board, chess.engine.Limit(depth=DEPTH))
    score = info["score"].white()
    return Evaluation(cp=score.score(), mate=score.mate())
