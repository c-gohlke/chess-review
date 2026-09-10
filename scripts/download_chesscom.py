# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""Download all games of a Chess.com user as monthly JSON archives.

Usage: uv run scripts/download_chesscom.py <username> [--out DIR]

Each month is written to DIR/<username>/<YYYY-MM>.json exactly as returned by the
public API (https://api.chess.com/pub/player/<username>/games/<YYYY>/<MM>), so the
PGN, clocks and ratings of every game are preserved. Months already on disk are
skipped, except the most recent one, which may still be receiving games.
"""

import argparse
import sys
from pathlib import Path

import httpx

API = "https://api.chess.com/pub/player"
# Chess.com rejects requests without a descriptive User-Agent.
HEADERS = {"User-Agent": "chess-review (https://github.com/c-gohlke/chess-review)"}


def get(client: httpx.Client, url: str) -> httpx.Response:
    # The API occasionally stalls on a single request; one retry is enough in practice.
    for attempt in range(2):
        try:
            response = client.get(url)
        except httpx.TimeoutException:
            if attempt == 1:
                raise
            continue
        response.raise_for_status()
        return response
    raise AssertionError("unreachable")


def archive_urls(client: httpx.Client, username: str) -> list[str]:
    urls: list[str] = get(client, f"{API}/{username}/games/archives").json()["archives"]
    return urls


def download(username: str, out_dir: Path) -> int:
    target = out_dir / username
    target.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers=HEADERS, timeout=60) as client:
        urls = archive_urls(client, username)
        for url in urls:
            year, month = url.rsplit("/", 2)[-2:]
            path = target / f"{year}-{month}.json"
            if path.exists() and url != urls[-1]:
                continue
            response = get(client, url)
            path.write_bytes(response.content)
            print(f"{path} ({len(response.json()['games'])} games)")
    return len(urls)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download all games of a Chess.com user.")
    parser.add_argument("username")
    parser.add_argument("--out", type=Path, default=Path("data"), help="output directory (default: data)")
    args = parser.parse_args()
    try:
        months = download(args.username.lower(), args.out)
    except httpx.HTTPStatusError as error:
        sys.exit(f"{error.response.status_code} from {error.request.url}")
    print(f"{months} months archived for {args.username}")


if __name__ == "__main__":
    main()
