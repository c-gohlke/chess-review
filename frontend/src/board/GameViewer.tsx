import { Chess } from "chess.js";
import { useEffect, useState } from "react";
import { Chessboard } from "react-chessboard";

function fenAtPly(moves: string[], ply: number): string {
	const game = new Chess();
	for (const move of moves.slice(0, ply)) game.move(move);
	return game.fen();
}

export function GameViewer({ pgn }: { pgn: string }) {
	const [moves] = useState(() => {
		const game = new Chess();
		game.loadPgn(pgn);
		return game.history();
	});
	const [ply, setPly] = useState(0);

	useEffect(() => {
		function onKeyDown(event: KeyboardEvent) {
			if (event.key === "ArrowLeft") setPly((current) => Math.max(current - 1, 0));
			if (event.key === "ArrowRight") setPly((current) => Math.min(current + 1, moves.length));
		}
		window.addEventListener("keydown", onKeyDown);
		return () => window.removeEventListener("keydown", onKeyDown);
	}, [moves]);

	const fen = fenAtPly(moves, ply);

	return (
		<div className="mx-auto w-full max-w-[600px]">
			<Chessboard options={{ id: "game-viewer", position: fen, allowDragging: false }} />
			<div className="mt-2 flex items-center justify-center gap-4">
				<button
					type="button"
					className="rounded border px-4 py-2 disabled:opacity-50"
					disabled={ply === 0}
					onClick={() => setPly(ply - 1)}
				>
					Prev
				</button>
				<span>
					{ply} / {moves.length}
				</span>
				<button
					type="button"
					className="rounded border px-4 py-2 disabled:opacity-50"
					disabled={ply === moves.length}
					onClick={() => setPly(ply + 1)}
				>
					Next
				</button>
			</div>
		</div>
	);
}
