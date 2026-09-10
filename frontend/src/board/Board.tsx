import { Chess } from "chess.js";
import { useState } from "react";
import { Chessboard } from "react-chessboard";

export function Board() {
	const [game] = useState(() => new Chess());
	const [fen, setFen] = useState(game.fen());

	function onPieceDrop({ sourceSquare, targetSquare }: { sourceSquare: string; targetSquare: string | null }) {
		if (targetSquare === null) return false;
		try {
			game.move({ from: sourceSquare, to: targetSquare, promotion: "q" });
		} catch {
			return false;
		}
		setFen(game.fen());
		return true;
	}

	return (
		<div className="mx-auto w-full max-w-[600px]">
			{game.isCheckmate() && (
				<div className="mb-2 rounded bg-red-600 py-2 text-center font-bold text-white">Checkmate</div>
			)}
			<Chessboard options={{ id: "board", position: fen, onPieceDrop }} />
		</div>
	);
}
