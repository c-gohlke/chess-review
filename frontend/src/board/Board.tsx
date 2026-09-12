import { Chess, type Square } from "chess.js";
import { type CSSProperties, useState } from "react";
import { Chessboard } from "react-chessboard";

const LEGAL_MOVE_STYLE = { background: "radial-gradient(circle, rgba(0,0,0,0.2) 25%, transparent 26%)" };
// Read by the piece's transform in index.css; the square is the closest element we can style.
const SELECTED_PIECE_STYLE = { "--piece-scale": "1.2" } as CSSProperties;

export function Board() {
	const [game] = useState(() => new Chess());
	const [fen, setFen] = useState(game.fen());
	const [selectedSquare, setSelectedSquare] = useState<Square | null>(null);

	function legalMoveSquares(square: Square): Square[] {
		return game.moves({ square, verbose: true }).map((move) => move.to);
	}

	function selectIfMovable(square: string) {
		if (legalMoveSquares(square as Square).length > 0) setSelectedSquare(square as Square);
	}

	function onPieceDrop({ sourceSquare, targetSquare }: { sourceSquare: string; targetSquare: string | null }) {
		if (targetSquare === null) return false;
		try {
			game.move({ from: sourceSquare, to: targetSquare, promotion: "q" });
		} catch {
			return false;
		}
		setFen(game.fen());
		setSelectedSquare(null);
		return true;
	}

	function onSquareClick({ square }: { square: string }) {
		if (selectedSquare) {
			try {
				game.move({ from: selectedSquare, to: square, promotion: "q" });
				setFen(game.fen());
			} catch {
				// not a legal move for the selected piece; fall through to reselect below
			}
			setSelectedSquare(null);
			selectIfMovable(square);
			return;
		}

		selectIfMovable(square);
	}

	const squareStyles = selectedSquare
		? {
				...Object.fromEntries(legalMoveSquares(selectedSquare).map((square) => [square, LEGAL_MOVE_STYLE])),
				[selectedSquare]: SELECTED_PIECE_STYLE,
			}
		: {};

	return (
		<div className="mx-auto w-full max-w-[600px]">
			{game.isCheckmate() ? (
				<div className="mb-2 rounded bg-red-600 py-2 text-center font-bold text-white">Checkmate</div>
			) : (
				<h2 className="mb-2 text-center font-semibold">{game.turn() === "w" ? "White" : "Black"} to move</h2>
			)}
			<Chessboard
				options={{
					id: "board",
					position: fen,
					onPieceDrop,
					onSquareClick,
					onSquareMouseDown: ({ square }) => selectIfMovable(square),
					onPieceDrag: ({ square }) => {
						if (square !== null) selectIfMovable(square);
					},
					squareStyles,
				}}
			/>
		</div>
	);
}
