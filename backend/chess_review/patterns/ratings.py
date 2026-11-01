import re

from chess_review.db import Game


def own_rating(game: Game) -> int | None:
    colour = "White" if game.white.lower() == game.username else "Black"
    match = re.search(rf'^\[{colour}Elo "(\d+)"\]$', game.pgn, re.MULTILINE)
    return int(match.group(1)) if match else None


def rating_change(game: Game, previous: Game | None) -> int | None:
    # Chess.com stores the rating after each game, so the change is the gap between consecutive games.
    if previous is None:
        return None
    rating = own_rating(game)
    previous_rating = own_rating(previous)
    if rating is None or previous_rating is None:
        return None
    return rating - previous_rating
