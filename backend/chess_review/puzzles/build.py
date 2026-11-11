"""Turn the costly moves found in a player's games into puzzles, written as one CSV per theme.

Puzzles follow the Lichess puzzle format: `FEN` is the position before the opponent's move, and
`Moves` starts with that move, so a puzzle player can show it before the solver's turn.

Each costly move gives up to two puzzles:
- the tactic it allowed, solved by the other side from the position after it;
- the tactic its player missed, solved from the position the player had.
The same position can come out of both, when the next player missed what was allowed. It then
becomes one puzzle with both themes.
"""

import argparse
import csv
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

import chess

from chess_review.db import (
    Game,
    GameMoment,
    PositionAnalysis,
    connect,
    list_game_moments,
    list_games,
    load_position_analyses,
)
from chess_review.patterns.habits import is_white
from chess_review.themes.motifs import line_gain
from chess_review.themes.reasons import Step, build_steps

COLUMNS = ["PuzzleId", "FEN", "Moves", "Themes", "SolvedBy", "WinLost", "GameUrl"]
NAMED_TACTICS = {"hanging_piece", "pin", "skewer", "discovered_attack", "promotion", "other_tactic"}
MATE_IN = re.compile(r"(?:allowed_)?mate_in_(\d+)")


@dataclass(frozen=True)
class Puzzle:
    """`moves` are UCI: the opponent's move first, then the solution, ending on the solver's move."""

    id: str
    fen: str
    moves: list[str]
    themes: list[str]
    solved_by: str
    win_lost: int
    game_url: str


def themes_for(tag: str) -> list[str]:
    """The puzzle themes for a moment's tag, or none when the tag is not a tactic a puzzle can teach."""
    if match := MATE_IN.fullmatch(tag):
        return ["mate", f"mate_in_{match.group(1)}"]
    if tag.startswith("fork_"):
        return ["fork", tag]
    return [tag] if tag in NAMED_TACTICS else []


def _line(analysis: PositionAnalysis) -> list[chess.Move]:
    return [chess.Move.from_uci(uci) for uci in analysis.pv.split()]


def _is_legal(board: chess.Board, line: list[chess.Move]) -> bool:
    current = board.copy(stack=False)
    for move in line:
        if not current.is_legal(move):
            return False
        current.push(move)
    return True


def solution(board: chess.Board, line: list[chess.Move], themes: list[str]) -> list[chess.Move]:
    """The engine line cut where the tactic pays off; empty when it does not reach its goal.

    `board` has the solver to move. A mate runs to the mate, a promotion to the promotion, and any
    other tactic to the solver's first move after which the material is won.
    """
    if not line or not _is_legal(board, line):
        return []
    if "mate" in themes:
        end = board.copy(stack=False)
        for move in line:
            end.push(move)
        return line if end.is_checkmate() else []
    solver = board.turn
    if "promotion" in themes:
        for index in range(0, len(line), 2):
            if line[index].promotion is not None:
                return line[: index + 1]
        return []
    won = line_gain(board, line, solver)
    for index in range(0, len(line), 2):
        if line_gain(board, line[: index + 2], solver) >= won:
            return line[: index + 1]
    return line


def _puzzle(game: Game, setup: Step, analysis: PositionAnalysis, themes: list[str], win_lost: int) -> Puzzle | None:
    """`setup` is the opponent's move shown first; `analysis` is of the position after it."""
    moves = solution(setup.after, _line(analysis), themes)
    if not moves:
        return None
    solver_is_white = setup.after.turn == chess.WHITE
    return Puzzle(
        id=f"{game.id}-{setup.index}",
        fen=setup.board.fen(),
        moves=[setup.move.uci()] + [move.uci() for move in moves],
        themes=themes,
        solved_by="you" if solver_is_white == is_white(game) else "opponent",
        win_lost=win_lost,
        game_url=game.source_id,
    )


def _allowed(tags: list[str]) -> list[str]:
    """`_error_tags` puts the tactic a move allowed first; a moment may only record a missed mate."""
    themes = themes_for(tags[0]) if tags and not tags[0].startswith("missed_") else []
    if themes and "back_rank_mate" in tags:
        themes.append("back_rank_mate")
    return themes


def _missed(tags: list[str]) -> list[str]:
    return [theme for tag in tags if tag.startswith("missed_") for theme in themes_for(tag.removeprefix("missed_"))]


def game_puzzles(game: Game, steps: list[Step], moments: list[GameMoment]) -> list[Puzzle]:
    puzzles: list[Puzzle | None] = []
    for moment in moments:
        step = steps[moment.ply]
        if themes := _allowed(moment.tags):
            puzzles.append(_puzzle(game, step, step.following, themes, moment.win_lost))
        if (themes := _missed(moment.tags)) and moment.ply > 0:
            puzzles.append(_puzzle(game, steps[moment.ply - 1], step.before, themes, moment.win_lost))
    return [puzzle for puzzle in puzzles if puzzle is not None]


def merge_duplicates(puzzles: list[Puzzle]) -> list[Puzzle]:
    """One puzzle per position and first solution move; it keeps every theme and the largest cost."""
    merged: dict[tuple[str, str, str], Puzzle] = {}
    for puzzle in puzzles:
        key = (puzzle.fen, puzzle.moves[0], puzzle.moves[1])
        if (kept := merged.get(key)) is None:
            merged[key] = puzzle
            continue
        themes = kept.themes + [theme for theme in puzzle.themes if theme not in kept.themes]
        merged[key] = replace(kept, themes=themes, win_lost=max(kept.win_lost, puzzle.win_lost))
    return list(merged.values())


def build_puzzles(conn: sqlite3.Connection, username: str) -> list[Puzzle]:
    analyses = load_position_analyses(conn)
    puzzles = []
    for game in list_games(conn, username):
        assert game.id is not None
        moments = list_game_moments(conn, game.id)
        if moments:
            puzzles.extend(game_puzzles(game, build_steps(game.pgn, analyses), moments))
    return merge_duplicates(puzzles)


def _row(puzzle: Puzzle) -> dict[str, object]:
    return {
        "PuzzleId": puzzle.id,
        "FEN": puzzle.fen,
        "Moves": " ".join(puzzle.moves),
        "Themes": " ".join(puzzle.themes),
        "SolvedBy": puzzle.solved_by,
        "WinLost": puzzle.win_lost,
        "GameUrl": puzzle.game_url,
    }


def write_dataset(out_dir: Path, puzzles: list[Puzzle]) -> Counter[str]:
    """Writes `<theme>.csv` for every theme, costliest mistakes first, and returns the counts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ordered = sorted(puzzles, key=lambda puzzle: -puzzle.win_lost)
    counts = Counter(theme for puzzle in ordered for theme in puzzle.themes)
    for theme in counts:
        with (out_dir / f"{theme}.csv").open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(_row(puzzle) for puzzle in ordered if theme in puzzle.themes)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("db_path", type=Path)
    parser.add_argument("username")
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    conn = connect(args.db_path)
    puzzles = build_puzzles(conn, args.username)
    conn.close()
    counts = write_dataset(args.out_dir, puzzles)
    print(f"{len(puzzles)} puzzles")
    for theme, count in counts.most_common():
        print(f"{theme}: {count}")


if __name__ == "__main__":
    main()
