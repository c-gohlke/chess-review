from datetime import UTC, datetime

import httpx2

from chess_review.importers.chesscom import archive_urls, archives_since

ARCHIVES = ["https://api.chess.com/pub/player/mjalmok/games/2024/01"]


def chesscom(request: httpx2.Request) -> httpx2.Response:
    # Chess.com only serves lowercase usernames; anything else is a 301 to the lowercase URL.
    if request.url.path != "/pub/player/mjalmok/games/archives":
        return httpx2.Response(301, headers={"location": "https://api.chess.com/pub/player/mjalmok/games/archives"})
    return httpx2.Response(200, json={"archives": ARCHIVES})


def test_archive_urls_lowercases_username() -> None:
    with httpx2.Client(transport=httpx2.MockTransport(chesscom)) as client:
        assert archive_urls(client, "Mjalmok") == ARCHIVES


MONTHS = [f"https://api.chess.com/pub/player/mjalmok/games/{month}" for month in ("2024/12", "2025/01", "2025/02")]


def test_a_refresh_skips_months_before_the_latest_stored_game() -> None:
    assert archives_since(MONTHS, datetime(2025, 1, 31, tzinfo=UTC)) == MONTHS[1:]


def test_a_first_import_fetches_every_month() -> None:
    assert archives_since(MONTHS, None) == MONTHS
