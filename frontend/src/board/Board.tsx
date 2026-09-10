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
			<Chessboard options={{ id: "board", position: fen, onPieceDrop }} />
		</div>
	);
}
