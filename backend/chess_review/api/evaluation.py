import chess
from fastapi import APIRouter, HTTPException, Request

from chess_review.analysis.engine import evaluate
from chess_review.api.games import Db
from chess_review.db import Evaluation, get_evaluation, insert_evaluation

router = APIRouter()


def parse_board(fen: str) -> chess.Board:
    try:
        board = chess.Board(fen)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="invalid FEN") from error
    if not board.is_valid():
        raise HTTPException(status_code=422, detail="illegal position")
    return board


@router.get("/api/evaluation")
def get_position_evaluation(fen: str, request: Request, conn: Db) -> Evaluation:
    board = parse_board(fen)
    # EPD leaves out the move counters, so a position reached by transposition is reused.
    position = board.epd()
    stored = get_evaluation(conn, position)
    if stored is not None:
        return stored
    evaluation = evaluate(request.app.state.stockfish_path, board)
    insert_evaluation(conn, position, evaluation)
    return evaluation
