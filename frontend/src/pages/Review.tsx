import { useEffect, useState } from "react";
import { type GameDetail, getGame } from "../api/client";
import { GameViewer } from "../board/GameViewer";

export function Review({ gameId, onBack }: { gameId: number; onBack: () => void }) {
	const [game, setGame] = useState<GameDetail | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		getGame(gameId)
			.then(setGame)
			.catch((err: Error) => setError(err.message));
	}, [gameId]);

	return (
		<div className="mx-auto w-full max-w-[600px]">
			<button type="button" className="mb-4 rounded border px-4 py-2" onClick={onBack}>
				Back
			</button>
			{error && <p className="text-red-600">{error}</p>}
			{game && <GameViewer pgn={game.pgn} />}
		</div>
	);
}
