import { useEffect, useState } from "react";
import { analyseGame, type GameDetail, getGame } from "../api/client";
import { GameViewer } from "../board/GameViewer";

export function Review({ gameId, onBack }: { gameId: number; onBack: () => void }) {
	const [game, setGame] = useState<GameDetail | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [analysing, setAnalysing] = useState(false);

	useEffect(() => {
		let current = true;
		getGame(gameId)
			.then((loaded) => {
				if (!current) return;
				setGame(loaded);
				if (loaded.analysis) return;
				// Opening a game is the request to analyse it; the engine takes a few seconds.
				setAnalysing(true);
				return analyseGame(gameId).then((analysed) => current && setGame(analysed));
			})
			.catch((err: Error) => current && setError(err.message))
			.finally(() => current && setAnalysing(false));
		return () => {
			current = false;
		};
	}, [gameId]);

	return (
		<div className="mx-auto w-full max-w-[600px] lg:max-w-[944px]">
			<button type="button" className="mb-4 rounded border px-4 py-2" onClick={onBack}>
				Back
			</button>
			{error && <p className="text-red-600 dark:text-red-400">{error}</p>}
			{game && (
				<GameViewer
					pgn={game.pgn}
					white={game.white}
					black={game.black}
					colour={game.colour}
					analysis={game.analysis}
					analysing={analysing}
				/>
			)}
		</div>
	);
}
