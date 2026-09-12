import httpx2
import pytest

from chess_review.importers.chesscom import HEADERS, archive_urls, get, parse_game

USERNAME = "erik"


@pytest.mark.integration
def test_fetches_and_parses_last_month_of_real_games() -> None:
    with httpx2.Client(headers=HEADERS, timeout=60) as client:
        urls = archive_urls(client, USERNAME)
        raw_games = get(client, urls[-1]).json()["games"]

    games = [game for raw in raw_games if (game := parse_game(raw, USERNAME)) is not None]

    assert len(games) > 0
    assert all(game.pgn for game in games)
