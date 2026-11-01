from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chess_review.api.app import create_app
from chess_review.db import Game, Result, connect, insert_games
from chess_review.patterns.openings import NO_VARIATION, UNKNOWN_OPENING, parse_opening, summarize_openings

BASE = "https://www.chess.com/openings/"


def pgn(slug: str) -> str:
    return f'[Event "Live Chess"]\n[ECOUrl "{BASE}{slug}"]\n\n1. e4 e5'


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


def test_summary_splits_by_colour_and_sorts_worst_first(game_1: Game, game_2: Game) -> None:
    white_win = replace(game_1, pgn=pgn("Italian-Game"))
    white_loss = replace(game_1, pgn=pgn("Scotch-Game"), result=Result.LOSS)
    black_loss = replace(game_2, pgn=pgn("French-Defense"))

    summary = summarize_openings([white_win, white_loss, black_loss])

    assert [(f.name, f.net) for f in summary.white] == [("Scotch Game", -0.5), ("Italian Game", 0.5)]
    assert [(f.name, f.net) for f in summary.black] == [("French Defense", -0.5)]


def test_summary_counts_results_per_family_and_variation(game_1: Game) -> None:
    summary = summarize_openings(
        [
            replace(game_1, pgn=pgn("French-Defense-Exchange-Variation"), result=Result.WIN),
            replace(game_1, pgn=pgn("French-Defense-Exchange-Variation"), result=Result.DRAW),
            replace(game_1, pgn=pgn("French-Defense-Advance-Variation"), result=Result.LOSS),
        ]
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
    summary = client.get("/api/openings", params=params).json()

    assert [family["name"] for family in summary["white"]] == white
    assert [family["name"] for family in summary["black"]] == black


def opening_game_ids(client: TestClient, **params: str) -> list[int]:
    response = client.get("/api/openings/games", params=params)
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


def test_opening_games_rows_match_the_games_list(client: TestClient) -> None:
    params = {"family": "Italian Game", "variation": NO_VARIATION, "colour": "white"}

    [game] = client.get("/api/openings/games", params=params).json()

    assert game["opening"] == "Italian Game"
    assert game["white"] == "alice"
    assert game["rating_change"] is None


def test_openings_endpoint_rejects_since_without_timezone(client: TestClient) -> None:
    assert client.get("/api/openings", params={"since": "2023-11-15T00:00:00"}).status_code == 422


def test_openings_endpoint_returns_summary(tmp_path: Path, game_1: Game) -> None:
    db_path = tmp_path / "db.sqlite3"
    conn = connect(db_path)
    insert_games(conn, [replace(game_1, pgn=pgn("French-Defense"))])
    conn.close()

    response = TestClient(create_app(tmp_path, db_path, Path("stockfish"))).get("/api/openings")

    assert response.status_code == 200
    variation = {
        "name": NO_VARIATION,
        "games": 1,
        "wins": 1,
        "draws": 0,
        "losses": 0,
        "net": 0.5,
        "variations": [],
    }
    assert response.json() == {
        "white": [{**variation, "name": "French Defense", "variations": [variation]}],
        "black": [],
    }
