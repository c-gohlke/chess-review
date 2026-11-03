import { Chess } from "chess.js";
import { useEffect, useLayoutEffect, useState } from "react";
import { Chessboard } from "react-chessboard";
import { type Evaluation, type GameDetail, getEvaluation } from "../api/client";
import { EvalBar, formatEvaluation } from "./EvalBar";
import { GameStatistics } from "./GameStatistics";

function fenAtPly(moves: string[], ply: number): string {
	const game = new Chess();
	for (const move of moves.slice(0, ply)) game.move(move);
	return game.fen();
}

type Props = {
	pgn: string;
	white: string;
	black: string;
	colour: "white" | "black";
	analysis: GameDetail["analysis"] | undefined;
	analysing: boolean;
};

export function GameViewer({ pgn, white, black, colour, analysis, analysing }: Props) {
	const [moves] = useState(() => {
		const game = new Chess();
		game.loadPgn(pgn);
		return game.history();
	});
	const [ply, setPly] = useState(0);
	const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
	const [evaluationError, setEvaluationError] = useState<string | null>(null);

	// A layout effect, so the keys work as soon as the board is on screen.
	useLayoutEffect(() => {
		function onKeyDown(event: KeyboardEvent) {
			if (event.key === "ArrowLeft") setPly((current) => Math.max(current - 1, 0));
			if (event.key === "ArrowRight") setPly((current) => Math.min(current + 1, moves.length));
		}
		window.addEventListener("keydown", onKeyDown);
		return () => window.removeEventListener("keydown", onKeyDown);
	}, [moves]);

	const fen = fenAtPly(moves, ply);

	useEffect(() => {
		// Stepping quickly must not let an older position's result replace the current one.
		let stale = false;
		getEvaluation(fen)
			.then((result) => {
				if (stale) return;
				setEvaluation(result);
				setEvaluationError(null);
			})
			.catch((error: Error) => {
				if (!stale) setEvaluationError(error.message);
			});
		return () => {
			stale = true;
		};
	}, [fen]);

	return (
		<div className="flex flex-col gap-6 lg:flex-row">
			<div className="w-full min-w-0 max-w-[600px]">
				<p data-testid="top-player" className="mb-1 font-bold">
					{colour === "white" ? black : white}
				</p>
				<div className="flex gap-2">
					<EvalBar evaluation={evaluation} whiteToMove={fen.split(" ")[1] === "w"} whiteAtBottom={colour === "white"} />
					<div className="min-w-0 flex-1">
						<Chessboard
							options={{ id: "game-viewer", position: fen, allowDragging: false, boardOrientation: colour }}
						/>
					</div>
				</div>
				<p data-testid="bottom-player" className="mt-1 font-bold">
					{colour === "white" ? white : black}
				</p>
				<p className="mt-2 min-h-6 text-center font-bold tabular-nums">
					{evaluationError ?? (evaluation && formatEvaluation(evaluation))}
				</p>
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
			<GameStatistics analysis={analysis} analysing={analysing} moves={moves} ply={ply} onSelectPly={setPly} />
		</div>
	);
}
