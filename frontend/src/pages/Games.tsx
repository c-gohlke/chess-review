import { useEffect, useState } from "react";
import { type GameSummary, importChesscom, listGames } from "../api/client";

export function Games({ onSelect }: { onSelect: (id: number) => void }) {
	const [games, setGames] = useState<GameSummary[]>([]);
	const [loadError, setLoadError] = useState<string | null>(null);
	const [username, setUsername] = useState("");
	const [importMessage, setImportMessage] = useState<string | null>(null);

	function reload() {
		listGames()
			.then(setGames)
			.catch((error: Error) => setLoadError(error.message));
	}

	useEffect(reload, []);

	async function handleImport() {
		try {
			const result = await importChesscom(username);
			setImportMessage(`Imported ${result.imported} games`);
			reload();
		} catch (error) {
			setImportMessage(error instanceof Error ? error.message : String(error));
		}
	}

	return (
		<div className="mx-auto w-full max-w-[600px]">
			<div className="mb-4 flex gap-2">
				<input
					className="flex-1 rounded border px-3 py-2"
					placeholder="Chess.com username"
					value={username}
					onChange={(event) => setUsername(event.target.value)}
				/>
				<button type="button" className="rounded bg-blue-600 px-4 py-2 text-white" onClick={handleImport}>
					Import
				</button>
			</div>
			{importMessage && <p className="mb-4">{importMessage}</p>}
			{loadError && <p className="text-red-600">{loadError}</p>}
			{!loadError && games.length === 0 && <p>No games yet</p>}
			<ul className="flex flex-col gap-2">
				{games.map((game) => (
					<li key={game.id}>
						<button
							type="button"
							className="w-full rounded border px-4 py-2 text-left"
							onClick={() => onSelect(game.id)}
						>
							{game.white} vs {game.black} — {game.result} — {game.time_class} — {game.played_at?.slice(0, 10)}
						</button>
					</li>
				))}
			</ul>
		</div>
	);
}
