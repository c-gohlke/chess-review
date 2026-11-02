import chess
import pytest

from chess_review.themes.motifs import fork_name, is_back_rank_mate, line_gain, tactic_name


def line(*uci: str) -> list[chess.Move]:
    return [chess.Move.from_uci(move) for move in uci]


@pytest.mark.parametrize(
    ("fen", "uci", "expected"),
    [
        ("q3k3/8/8/3N4/8/8/8/4K3 w - - 0 1", "d5c7", "fork_knight_royal"),
        ("q3k3/8/4r3/3N4/8/8/8/4K3 w - - 0 1", "d5c7", "fork_knight_family"),
        ("q3k3/8/r3r3/3N4/8/8/8/4K3 w - - 0 1", "d5c7", "fork_knight_grand"),
        ("4k3/8/8/1n1b4/8/2P5/8/4K3 w - - 0 1", "c3c4", "fork_pawn"),
        ("4k3/8/8/3N4/8/8/8/4K3 w - - 0 1", "d5c7", None),
    ],
)
def test_fork_name(fen: str, uci: str, expected: str | None) -> None:
    board = chess.Board(fen)
    move = chess.Move.from_uci(uci)
    board.push(move)
    assert fork_name(board, move) == expected


def test_line_gain_reads_after_the_defenders_reply() -> None:
    board = chess.Board("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    assert line_gain(board, line("e4d5", "e8d7"), chess.WHITE) == 1


@pytest.mark.parametrize(
    ("fen", "moves", "expected"),
    [
        ("4k3/8/8/3n4/8/8/8/3RK3 w - - 0 1", ("d1d5", "e8e7"), "hanging_piece"),
        ("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", ("e2e4", "e8e7"), "positional"),
        ("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1", ("e4d5", "e8d7"), "pawn_loss"),
        ("8/3k3r/8/8/8/8/8/R3K3 w - - 0 1", ("a1a7", "d7d6", "a7h7", "d6e6"), "skewer"),
        ("4k3/8/2n5/8/8/8/8/4KB2 w - - 0 1", ("f1b5", "e8d8", "b5c6", "d8c7"), "pin"),
        ("4q2k/8/8/8/4N3/8/8/4R1K1 w - - 0 1", ("e4g5", "h8g8", "e1e8", "g8g7"), "discovered_attack"),
        ("8/P7/8/8/8/8/8/k1K5 w - - 0 1", ("a7a8q", "a1a2"), "promotion"),
    ],
)
def test_tactic_name(fen: str, moves: tuple[str, ...], expected: str) -> None:
    assert tactic_name(chess.Board(fen), line(*moves), chess.WHITE) == expected


def test_back_rank_mate_is_recognised() -> None:
    assert is_back_rank_mate(chess.Board("6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1"), line("a1a8"))


def test_mate_off_the_back_rank_is_not_a_back_rank_mate() -> None:
    assert not is_back_rank_mate(chess.Board("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1"), line("f7g7"))
