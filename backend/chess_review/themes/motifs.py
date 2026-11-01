"""Name the tactic in an engine line. Pure logic: boards and moves in, a label out."""

import chess

PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}
# A line that nets less than this is not a tactic: it may be a trade or an engine preference.
MIN_GAIN = 2
SLIDERS = (chess.BISHOP, chess.ROOK, chess.QUEEN)


def material(board: chess.Board, color: chess.Color) -> int:
    return sum(value * len(board.pieces(piece, color)) for piece, value in PIECE_VALUES.items() if piece != chess.KING)


def line_gain(board: chess.Board, line: list[chess.Move], attacker: chess.Color) -> int:
    """Material won by `attacker`, read after the defender's last reply so a final capture is not overcounted."""
    balance = material(board, attacker) - material(board, not attacker)
    current = board.copy(stack=False)
    results = []
    for move in line:
        current.push(move)
        if current.turn == attacker:
            results.append(material(current, attacker) - material(current, not attacker) - balance)
    return results[-1] if results else 0


def _value(board: chess.Board, square: chess.Square) -> int:
    piece = board.piece_at(square)
    return PIECE_VALUES[piece.piece_type] if piece else 0


def _is_loose(board: chess.Board, square: chess.Square) -> bool:
    piece = board.piece_at(square)
    return piece is not None and not board.attackers(piece.color, square)


def _fork_targets(board: chess.Board, forker: chess.Square) -> list[int]:
    """Piece types on squares the forker attacks that it would profit from taking."""
    piece = board.piece_at(forker)
    assert piece is not None
    targets = []
    for square in board.attacks(forker):
        target = board.piece_at(square)
        if target is None or target.color == piece.color or target.piece_type == chess.PAWN:
            continue
        if target.piece_type == chess.KING or _value(board, square) > _value(board, forker) or _is_loose(board, square):
            targets.append(target.piece_type)
    return targets


def fork_name(board: chess.Board, move: chess.Move) -> str | None:
    """`board` is the position after `move`. Returns e.g. `fork_knight` or `fork_knight_royal`."""
    forker = board.piece_at(move.to_square)
    assert forker is not None
    targets = _fork_targets(board, move.to_square)
    if len(targets) < 2:
        return None
    name = f"fork_{chess.piece_name(forker.piece_type)}"
    if chess.KING not in targets or chess.QUEEN not in targets:
        return name
    if targets.count(chess.ROOK) >= 2:
        return f"{name}_grand"
    return f"{name}_family" if len(targets) >= 3 else f"{name}_royal"


def _find_fork(board: chess.Board, line: list[chess.Move], attacker: chess.Color) -> str | None:
    current = board.copy(stack=False)
    for move in line[:4]:
        is_attacker_move = current.turn == attacker
        current.push(move)
        if is_attacker_move:
            name = fork_name(current, move)
            if name is not None:
                return name
    return None


def _is_hanging_capture(board: chess.Board, line: list[chess.Move]) -> bool:
    first = line[0]
    if not board.is_capture(first) or board.is_en_passant(first):
        return False
    return _is_loose(board, first.to_square) or _value(board, first.to_square) > _value(board, first.from_square)


def _creates_pin(board: chess.Board, line: list[chess.Move], attacker: chess.Color) -> bool:
    """Only pins against the king: `is_pinned` does not see a piece pinned to a queen or rook."""
    after = board.copy(stack=False)
    after.push(line[0])
    defender = not attacker
    for square in chess.SquareSet(after.occupied_co[defender]):
        if _value(after, square) >= 3 and after.is_pinned(defender, square) and not board.is_pinned(defender, square):
            return bool(after.attacks(line[0].to_square) & after.pin(defender, square))
    return False


def _is_skewer(board: chess.Board, line: list[chess.Move]) -> bool:
    if len(line) < 3:
        return False
    first, reply, follow_up = line[:3]
    slider = board.piece_type_at(first.from_square)
    if slider not in SLIDERS or follow_up.from_square != first.to_square:
        return False
    after_reply = board.copy(stack=False)
    after_reply.push(first)
    front_value = _value(after_reply, reply.from_square)
    after_reply.push(reply)
    behind = follow_up.to_square
    is_on_line = reply.from_square in chess.SquareSet.between(first.to_square, behind)
    return is_on_line and front_value > _value(after_reply, behind) > 0


def _is_discovered(board: chess.Board, line: list[chess.Move], attacker: chess.Color) -> bool:
    first = line[0]
    after = board.copy(stack=False)
    after.push(first)
    sliders = [square for piece in SLIDERS for square in after.pieces(piece, attacker)]
    for slider_square in sliders:
        if slider_square == first.to_square:
            continue
        newly_attacked = after.attacks(slider_square) & ~board.attacks(slider_square)
        for square in newly_attacked & chess.SquareSet(after.occupied_co[not attacker]):
            if _value(after, square) >= 3 and first.from_square in chess.SquareSet.between(slider_square, square):
                return True
    return False


def promotes(board: chess.Board, line: list[chess.Move], attacker: chess.Color) -> bool:
    current = board.copy(stack=False)
    for move in line:
        if current.turn == attacker and move.promotion is not None:
            return True
        current.push(move)
    return False


def tactic_name(board: chess.Board, line: list[chess.Move], attacker: chess.Color) -> str:
    """`board` has `attacker` to move and `line` is the engine's best line from there."""
    if not line:
        return "positional"
    gain = line_gain(board, line, attacker)
    if gain < MIN_GAIN:
        if promotes(board, line, attacker):
            return "promotion"
        return "pawn_loss" if gain == 1 else "positional"
    if fork := _find_fork(board, line, attacker):
        return fork
    if _is_hanging_capture(board, line):
        return "hanging_piece"
    if _is_skewer(board, line):
        return "skewer"
    if _creates_pin(board, line, attacker):
        return "pin"
    if _is_discovered(board, line, attacker):
        return "discovered_attack"
    return "promotion" if promotes(board, line, attacker) else "other_tactic"


def is_back_rank_mate(board: chess.Board, line: list[chess.Move]) -> bool:
    """Whether the mating line ends with a rook or queen mating on the king's first rank."""
    current = board.copy(stack=False)
    for move in line:
        current.push(move)
    if not line or not current.is_checkmate():
        return False
    king = current.king(current.turn)
    assert king is not None
    home_rank = 0 if current.turn == chess.WHITE else 7
    mover = current.piece_type_at(line[-1].to_square)
    return (
        chess.square_rank(king) == home_rank
        and mover in (chess.ROOK, chess.QUEEN)
        and chess.square_rank(line[-1].to_square) == home_rank
    )
