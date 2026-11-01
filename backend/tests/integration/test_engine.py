import shutil
from pathlib import Path

import chess
import pytest

from chess_review.analysis.engine import evaluate
from chess_review.db import Evaluation


@pytest.fixture
def stockfish() -> Path:
    path = shutil.which("stockfish")
    assert path is not None
    return Path(path)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("fen", "white_is_better"),
    [
        ("4k3/8/8/8/8/8/8/Q3K3 w - - 0 1", True),
        ("4k3/8/8/8/8/8/8/Q3K3 b - - 0 1", True),
        ("q3k3/8/8/8/8/8/8/4K3 w - - 0 1", False),
        ("q3k3/8/8/8/8/8/8/4K3 b - - 0 1", False),
    ],
)
def test_evaluation_is_from_whites_point_of_view(stockfish: Path, fen: str, white_is_better: bool) -> None:
    result = evaluate(stockfish, chess.Board(fen))

    value = result.cp if result.mate is None else result.mate
    assert value is not None
    assert (value > 0) == white_is_better


@pytest.mark.integration
def test_mate_in_one_is_reported_as_mate(stockfish: Path) -> None:
    assert evaluate(stockfish, chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")) == Evaluation(cp=None, mate=1)


@pytest.mark.integration
def test_checkmated_position_is_mate_zero(stockfish: Path) -> None:
    fools_mate = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"

    assert evaluate(stockfish, chess.Board(fools_mate)) == Evaluation(cp=None, mate=0)


@pytest.mark.integration
def test_stalemate_is_level(stockfish: Path) -> None:
    assert evaluate(stockfish, chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")) == Evaluation(cp=0, mate=None)
