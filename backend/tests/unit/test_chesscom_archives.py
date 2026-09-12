import httpx2

from chess_review.importers.chesscom import archive_urls

ARCHIVES = ["https://api.chess.com/pub/player/mjalmok/games/2024/01"]


def chesscom(request: httpx2.Request) -> httpx2.Response:
    # Chess.com only serves lowercase usernames; anything else is a 301 to the lowercase URL.
    if request.url.path != "/pub/player/mjalmok/games/archives":
        return httpx2.Response(301, headers={"location": "https://api.chess.com/pub/player/mjalmok/games/archives"})
    return httpx2.Response(200, json={"archives": ARCHIVES})


def test_archive_urls_lowercases_username() -> None:
    with httpx2.Client(transport=httpx2.MockTransport(chesscom)) as client:
        assert archive_urls(client, "Mjalmok") == ARCHIVES
