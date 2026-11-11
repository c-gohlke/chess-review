from dataclasses import replace
from pathlib import Path

import chess
import pytest
from fastapi.testclient import TestClient

from chess_review.api.app import create_app
from chess_review.db import Game, PositionAnalysis, Result, connect, insert_games, insert_position_analyses
from chess_review.patterns.openings import (
    NO_VARIATION,
    UNKNOWN_OPENING,
    eval_after_move_10,
    parse_opening,
    position_after_move_10,
    summarize_openings,
)

BASE = "https://www.chess.com/openings/"
# Eleven moves with clock comments, as Chess.com exports them.
ITALIAN_MOVES = (
    "1. e4 {[%clk 0:03:00]} 1... e5 {[%clk 0:03:00]} 2. Nf3 2... Nc6 3. Bc4 3... Bc5 4. c3 4... Nf6 5. d3 5... d6 "
    "6. O-O 6... O-O 7. Re1 7... a6 8. a4 8... h6 9. h3 9... Re8 10. Nbd2 10... Be6 11. Bxe6 {[%clk 0:02:10]} 1-0"
)
ITALIAN_SAN = [
    "e4",
    "e5",
    "Nf3",
    "Nc6",
    "Bc4",
    "Bc5",
    "c3",
    "Nf6",
    "d3",
    "d6",
    "O-O",
    "O-O",
    "Re1",
    "a6",
    "a4",
    "h6",
    "h3",
    "Re8",
    "Nbd2",
    "Be6",
]


def pgn(slug: str, moves: str = "1. e4 e5") -> str:
    return f'[Event "Live Chess"]\n[ECOUrl "{BASE}{slug}"]\n\n{moves}'


def italian_move_10() -> str:
    board = chess.Board()
    for san in ITALIAN_SAN:
        board.push_san(san)
    return board.epd()


def analysis(cp: int | None = None, mate: int | None = None) -> PositionAnalysis:
    return PositionAnalysis(italian_move_10(), cp, mate, "")


def test_position_after_move_10_skips_comments_and_stops_after_blacks_tenth_move() -> None:
    assert position_after_move_10(pgn("Italian-Game", ITALIAN_MOVES)) == italian_move_10()


def test_position_after_move_10_is_none_for_a_shorter_game() -> None:
    assert position_after_move_10(pgn("Italian-Game", "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0")) is None


@pytest.mark.parametrize(
    ("stored", "as_white", "as_black"),
    [
        (analysis(cp=35), 0.35, -0.35),
        (analysis(cp=-2500), -10.0, 10.0),
        (analysis(mate=3), 10.0, -10.0),
        (analysis(mate=-1), -10.0, 10.0),
        (analysis(mate=0), -10.0, 10.0),
    ],
)
def test_eval_after_move_10_is_capped_and_from_the_players_side(
    game_1: Game, game_2: Game, stored: PositionAnalysis, as_white: float, as_black: float
) -> None:
    analyses = {stored.position: stored}
    italian = pgn("Italian-Game", ITALIAN_MOVES)

    assert eval_after_move_10(replace(game_1, pgn=italian), analyses) == as_white
    assert eval_after_move_10(replace(game_2, pgn=italian), analyses) == as_black


def test_eval_after_move_10_is_none_before_the_engine_has_seen_the_position(game_1: Game) -> None:
    assert eval_after_move_10(replace(game_1, pgn=pgn("Italian-Game", ITALIAN_MOVES)), {}) is None


def test_summary_averages_move_10_evals_and_skips_games_without_one(game_1: Game) -> None:
    other_line = ITALIAN_MOVES.replace("8... h6", "8... h5").replace("9. h3", "9. h4")
    board = chess.Board()
    for san in ITALIAN_SAN:
        board.push_san({"h6": "h5", "h3": "h4"}.get(san, san))
    variation = "Italian-Game-Giuoco-Pianissimo"
    analyses = {
        italian_move_10(): analysis(cp=100),
        board.epd(): PositionAnalysis(board.epd(), -50, None, ""),
    }
    games = [
        replace(game_1, pgn=pgn(variation, ITALIAN_MOVES)),
        replace(game_1, pgn=pgn(variation, ITALIAN_MOVES)),
        replace(game_1, pgn=pgn(variation, other_line)),
        replace(game_1, pgn=pgn(variation)),
    ]

    [family] = summarize_openings(games, analyses).white

    assert (family.games, family.eval_mean, family.eval_median) == (4, 0.5, 1.0)
    assert (family.variations[0].eval_mean, family.variations[0].eval_median) == (0.5, 1.0)


def test_summary_has_no_eval_when_no_game_reaches_an_analysed_move_10(game_1: Game) -> None:
    [family] = summarize_openings([replace(game_1, pgn=pgn("French-Defense"))], {}).white

    assert (family.eval_mean, family.eval_median) == (None, None)


@pytest.mark.parametrize(
    ("slug", "family", "variation"),
    [
        ("French-Defense", "French Defense", NO_VARIATION),
        ("French-Defense-Exchange-Variation", "French Defense", "Exchange Variation"),
        ("Scandinavian-Defense-Mieses-Kotrc-Main-Line-3.Nc3", "Scandinavian Defense", "Mieses Kotrc Main Line"),
        ("Queens-Pawn-Opening-Chigorin-Variation-3.Bf4-Nf6", "Queen's Pawn Opening", "Chigorin Variation"),
        ("Alekhines-Defense", "Alekhine's Defense", NO_VARIATION),
        ("Modern-Defense-with-1-d4", "Modern Defense", NO_VARIATION),
        ("Indian-Game-3.e3-d5", "Indian Game", NO_VARIATION),
        ("Queens-Pawn-Opening-Accelerated-London-System", "London System", "Accelerated"),
        ("Indian-Game-East-Indian-London-System", "London System", "East Indian"),
        ("London-System", "London System", NO_VARIATION),
        (
            "Queens-Pawn-Opening-Accelerated-London-Schlechter-Variation",
            "London System",
            "Accelerated Schlechter Variation",
        ),
        ("London-System-...4.e3-e6", "London System", NO_VARIATION),
        ("French-Defense-Advance-Variation...4.c3-Nc6", "French Defense", "Advance Variation"),
    ],
)
def test_parse_opening_splits_family_and_variation(slug: str, family: str, variation: str) -> None:
    assert parse_opening(pgn(slug)) == (family, variation)


@pytest.mark.parametrize("game_pgn", ["1. e4 e5", pgn("Undefined")])
def test_parse_opening_without_a_named_opening_is_unknown(game_pgn: str) -> None:
    assert parse_opening(game_pgn) == (UNKNOWN_OPENING, NO_VARIATION)


def test_summary_splits_by_colour_and_sorts_most_played_then_worst_first(game_1: Game, game_2: Game) -> None:
    italian_win = replace(game_1, pgn=pgn("Italian-Game"))
    ruy_lopez_win = replace(game_1, pgn=pgn("Ruy-Lopez-Opening"))
    scotch_loss = replace(game_1, pgn=pgn("Scotch-Game"), result=Result.LOSS)
    black_loss = replace(game_2, pgn=pgn("French-Defense"))

    summary = summarize_openings([italian_win, italian_win, ruy_lopez_win, scotch_loss, black_loss], {})

    assert [(f.name, f.games, f.net) for f in summary.white] == [
        ("Italian Game", 2, 1.0),
        ("Scotch Game", 1, -0.5),
        ("Ruy Lopez Opening", 1, 0.5),
    ]
    assert [(f.name, f.net) for f in summary.black] == [("French Defense", -0.5)]


def test_summary_counts_results_per_family_and_variation(game_1: Game) -> None:
    summary = summarize_openings(
        [
            replace(game_1, pgn=pgn("French-Defense-Exchange-Variation"), result=Result.WIN),
            replace(game_1, pgn=pgn("French-Defense-Exchange-Variation"), result=Result.DRAW),
            replace(game_1, pgn=pgn("French-Defense-Advance-Variation"), result=Result.LOSS),
        ],
        {},
    )

    family = summary.white[0]
    assert (family.games, family.wins, family.draws, family.losses, family.net) == (3, 1, 1, 1, 0.0)
    assert [(v.name, v.games, v.net) for v in family.variations] == [
        ("Exchange Variation", 2, 0.5),
        ("Advance Variation", 1, -0.5),
    ]


@pytest.fixture
def client(tmp_path: Path, game_1: Game, game_2: Game) -> TestClient:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(conn, [replace(game_1, pgn=pgn("Italian-Game")), replace(game_2, pgn=pgn("French-Defense"))])
    conn.close()
    return TestClient(create_app(tmp_path, db_path, Path("stockfish")))


@pytest.mark.parametrize(
    ("params", "white", "black"),
    [
        ({}, ["Italian Game"], ["French Defense"]),
        ({"since": "2023-11-15T00:00:00Z"}, [], ["French Defense"]),
        ({"time_class": "blitz"}, ["Italian Game"], []),
        ({"since": "2023-11-15T00:00:00Z", "time_class": "blitz"}, [], []),
    ],
)
def test_openings_endpoint_filters_games(
    client: TestClient, params: dict[str, str], white: list[str], black: list[str]
) -> None:
    summary = client.get("/api/openings", params={"username": "alice", **params}).json()

    assert [family["name"] for family in summary["white"]] == white
    assert [family["name"] for family in summary["black"]] == black


def opening_game_ids(client: TestClient, **params: str) -> list[int]:
    response = client.get("/api/openings/games", params={"username": "alice", **params})
    assert response.status_code == 200
    return [game["id"] for game in response.json()]


def test_opening_games_match_family_variation_and_colour(tmp_path: Path, game_1: Game, game_2: Game) -> None:
    exchange = pgn("French-Defense-Exchange-Variation")
    advance = pgn("French-Defense-Advance-Variation")
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(
        conn,
        [
            replace(game_2, source_id="older-exchange", pgn=exchange),
            replace(game_2, source_id="newer-exchange", pgn=exchange),
            replace(game_2, source_id="advance", pgn=advance),
            replace(game_1, source_id="exchange-as-white", pgn=exchange),
        ],
    )
    conn.close()
    client = TestClient(create_app(tmp_path, db_path, Path("stockfish")))

    ids = opening_game_ids(client, family="French Defense", variation="Exchange Variation", colour="black")

    assert ids == [2, 1]


def test_opening_games_use_the_same_filters_as_the_summary(client: TestClient) -> None:
    french = {"family": "French Defense", "variation": NO_VARIATION, "colour": "black"}

    assert opening_game_ids(client, **french) == [2]
    assert opening_game_ids(client, **french, time_class="rapid") == [2]
    assert opening_game_ids(client, **french, time_class="blitz") == []
    assert opening_game_ids(client, **french, since="2023-11-16T00:00:00Z") == []


def test_openings_only_count_the_requested_player(tmp_path: Path, game_1: Game) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    french = pgn("French-Defense")
    other_player = replace(game_1, source_id="bob-game", username="bob", white="bob", pgn=french)
    insert_games(conn, [replace(game_1, pgn=french), other_player])
    conn.close()
    client = TestClient(create_app(tmp_path, db_path, Path("stockfish")))

    summary = client.get("/api/openings", params={"username": "alice"}).json()
    params = {"family": "French Defense", "variation": NO_VARIATION, "colour": "white"}

    assert summary["white"][0]["games"] == 1
    assert opening_game_ids(client, **params) == [1]


def test_opening_games_rows_match_the_games_list(client: TestClient) -> None:
    params = {"family": "Italian Game", "variation": NO_VARIATION, "colour": "white"}

    [game] = client.get("/api/openings/games", params={"username": "alice", **params}).json()

    assert game["opening"] == "Italian Game"
    assert game["white"] == "alice"
    assert game["rating_change"] is None


def test_openings_endpoint_rejects_since_without_timezone(client: TestClient) -> None:
    params = {"username": "alice", "since": "2023-11-15T00:00:00"}
    assert client.get("/api/openings", params=params).status_code == 422


def test_openings_endpoint_returns_summary(tmp_path: Path, game_1: Game) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(conn, [replace(game_1, pgn=pgn("French-Defense"))])
    conn.close()

    client = TestClient(create_app(tmp_path, db_path, Path("stockfish")))
    response = client.get("/api/openings", params={"username": "alice"})

    assert response.status_code == 200
    variation = {
        "name": NO_VARIATION,
        "games": 1,
        "wins": 1,
        "draws": 0,
        "losses": 0,
        "net": 0.5,
        "eval_mean": None,
        "eval_median": None,
        "variations": [],
    }
    assert response.json() == {
        "white": [{**variation, "name": "French Defense", "variations": [variation]}],
        "black": [],
    }


def test_openings_endpoint_reports_the_stored_move_10_eval(tmp_path: Path, game_2: Game) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(conn, [replace(game_2, pgn=pgn("Italian-Game", ITALIAN_MOVES))])
    insert_position_analyses(conn, [analysis(cp=80)])
    conn.close()
    client = TestClient(create_app(tmp_path, db_path, Path("stockfish")))

    [family] = client.get("/api/openings", params={"username": "alice"}).json()["black"]

    assert (family["eval_mean"], family["eval_median"]) == (-0.8, -0.8)
