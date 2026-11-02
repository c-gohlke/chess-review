"""Turn the engine pass into a reasons table per game and a habits table, both as CSV."""

import argparse
import csv
import json
import re
import sqlite3
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import chess

from chess_review.db import (
    NO_MOVES,
    Game,
    GameMoment,
    GameReason,
    Result,
    connect,
    list_games,
    list_unanalysed_games,
    load_position_analyses,
    replace_game_moments,
    replace_game_reasons,
    replace_opponent_reasons,
)
from chess_review.patterns.associations import Outcome, associate, expected_score
from chess_review.patterns.habits import base_seconds, is_white, opening_habits, session_context
from chess_review.patterns.openings import parse_opening
from chess_review.patterns.ratings import own_rating
from chess_review.themes.reasons import Diagnosis, Step, build_steps, diagnose, has_moves

SCORES = {Result.WIN: 1.0, Result.DRAW: 0.5, Result.LOSS: 0.0}


@dataclass(frozen=True)
class GameReasons:
    game: Game
    own: Diagnosis
    opponent: Diagnosis
    plies: int

    @property
    def deciding(self) -> Diagnosis:
        return self.opponent if self.game.result == Result.WIN else self.own


def _header(pgn: str, name: str) -> str:
    match = re.search(rf'^\[{name} "(.*)"\]$', pgn, re.MULTILINE)
    return match.group(1) if match else ""


def _opponent_rating(game: Game) -> int | None:
    value = _header(game.pgn, "BlackElo" if is_white(game) else "WhiteElo")
    return int(value) if value else None


def diagnose_game(game: Game, steps: list[Step]) -> GameReasons:
    base = base_seconds(game.pgn)
    termination = _header(game.pgn, "Termination")
    white = is_white(game)
    own_name, opponent_name = (game.white, game.black) if white else (game.black, game.white)
    own_color = chess.WHITE if white else chess.BLACK
    return GameReasons(
        game=game,
        own=diagnose(steps, own_color, own_name, termination, base),
        opponent=diagnose(steps, not own_color, opponent_name, termination, base),
        plies=len(steps),
    )


def pre_game_gap(game: Game, previous: Game | None) -> float | None:
    """Rating gap before the game. Both stored ratings are post-game, and a rated game moves them oppositely."""
    if previous is None:
        return None
    rating, before, opponent = own_rating(game), own_rating(previous), _opponent_rating(game)
    if rating is None or before is None or opponent is None:
        return None
    return before - (opponent + (rating - before))


def build_outcomes(games: list[Game]) -> list[Outcome]:
    """`games` is oldest first. Only games with a known rating gap count, so all share one baseline."""
    context = session_context(games)
    last_in_class: dict[str, Game] = {}
    outcomes = []
    for game in games:
        previous = last_in_class.get(game.time_class)
        last_in_class[game.time_class] = game
        assert game.id is not None
        gap = pre_game_gap(game, previous)
        if gap is None:
            continue
        habits = opening_habits(game.pgn, is_white(game)) or {}
        outcomes.append(
            Outcome(
                score=SCORES[game.result],
                expected=expected_score(gap, 0),
                stratum=f"{game.time_class}/{'white' if is_white(game) else 'black'}",
                features=habits | context[game.id],
            )
        )
    return outcomes


def _reason_row(reasons: GameReasons) -> dict[str, object]:
    game = reasons.game
    return {
        "id": game.id,
        "played_at": game.played_at.isoformat(),
        "url": _header(game.pgn, "Link"),
        "time_class": game.time_class,
        "colour": "white" if is_white(game) else "black",
        "opponent": game.black if is_white(game) else game.white,
        "result": game.result,
        "opening": parse_opening(game.pgn)[0],
        "moves": (reasons.plies + 1) // 2,
        "deciding_reason": reasons.deciding.primary,
        "decisive_move": reasons.deciding.decisive_move,
        "own_error": reasons.own.primary,
        "own_tags": " ".join(reasons.own.tags),
        "opponent_error": reasons.opponent.primary,
        "opponent_tags": " ".join(reasons.opponent.tags),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(reasons: list[GameReasons]) -> dict[str, object]:
    losses = [item for item in reasons if item.game.result == Result.LOSS]
    wins = [item for item in reasons if item.game.result == Result.WIN]
    draws = [item for item in reasons if item.game.result == Result.DRAW]
    return {
        "games": {"losses": len(losses), "wins": len(wins), "draws": len(draws)},
        "loss_primary": Counter(item.own.primary for item in losses).most_common(),
        "win_primary": Counter(item.opponent.primary for item in wins).most_common(),
        "loss_tags": Counter(tag for item in losses for tag in item.own.tags).most_common(),
        "win_tags": Counter(tag for item in wins for tag in item.opponent.tags).most_common(),
        "win_own_tags": Counter(tag for item in wins for tag in item.own.tags).most_common(),
        "draw_own_tags": Counter(tag for item in draws for tag in item.own.tags).most_common(),
    }


def _moments(game_id: int, diagnosis: Diagnosis) -> list[GameMoment]:
    return [
        GameMoment(game_id, ply, ply == diagnosis.decisive_ply, diagnosis.win_lost[ply], tags)
        for ply, tags in diagnosis.moments.items()
    ]


def store_reasons(conn: sqlite3.Connection, reasons: list[GameReasons]) -> None:
    rows = [(item.game.id, item) for item in reasons if item.game.id is not None]
    replace_game_reasons(conn, [GameReason(id_, item.own.primary, item.own.tags) for id_, item in rows])
    replace_opponent_reasons(conn, [GameReason(id_, item.opponent.primary, item.opponent.tags) for id_, item in rows])
    replace_game_moments(
        conn, [moment for id_, item in rows for moment in _moments(id_, item.own) + _moments(id_, item.opponent)]
    )


def classify_unanalysed(db_path: Path, username: str) -> None:
    """A game still missing engine results is left out, so a later run picks it up."""
    conn = connect(db_path)
    analyses = load_position_analyses(conn)
    games = list_unanalysed_games(conn, username)
    reasons = []
    for game in games:
        steps = build_steps(game.pgn, analyses)
        if steps:
            reasons.append(diagnose_game(game, steps))
    store_reasons(conn, reasons)
    empty = [GameReason(game.id, NO_MOVES, []) for game in games if game.id is not None and not has_moves(game.pgn)]
    replace_game_reasons(conn, empty)
    replace_opponent_reasons(conn, empty)
    conn.close()


def classify(db_path: Path, username: str, out_dir: Path) -> None:
    conn = connect(db_path)
    analyses = load_position_analyses(conn)
    games = sorted(list_games(conn, username), key=lambda game: game.played_at)
    reasons = []
    for game in games:
        steps = build_steps(game.pgn, analyses)
        if steps:
            reasons.append(diagnose_game(game, steps))
    store_reasons(conn, reasons)
    conn.close()

    write_csv(out_dir / "game-reasons.csv", [_reason_row(item) for item in reversed(reasons)])
    write_csv(out_dir / "habits.csv", [asdict(item) for item in associate(build_outcomes(games))])
    (out_dir / "summary.json").write_text(json.dumps(summarize(reasons), indent=2, default=str))
    print(f"{len(reasons)}/{len(games)} games classified")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("db_path", type=Path)
    parser.add_argument("username")
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    classify(args.db_path, args.username, args.out_dir)


if __name__ == "__main__":
    main()
