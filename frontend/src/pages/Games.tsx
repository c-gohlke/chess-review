import { useEffect, useState } from "react";
import { type GameListItem, importChesscom, listGames } from "../api/client";
import { GameRow } from "../components/GameRow";

const PAGE_SIZE = 50;

export function Games({ onSelect }: { onSelect: (id: number) => void }) {
	// Null until the first page arrives, so loading is not mistaken for having no games.
	const [games, setGames] = useState<GameListItem[] | null>(null);
	const [hasMore, setHasMore] = useState(false);
	const [loadingMore, setLoadingMore] = useState(false);
	const [loadError, setLoadError] = useState<string | null>(null);
	const [username, setUsername] = useState("");
	const [importMessage, setImportMessage] = useState<string | null>(null);

	function reload() {
		listGames(PAGE_SIZE, 0)
			.then((page) => {
				setGames(page);
				setHasMore(page.length === PAGE_SIZE);
			})
			.catch((error: Error) => setLoadError(error.message));
	}

	useEffect(reload, []);

	function loadMore(loaded: GameListItem[]) {
		setLoadingMore(true);
		listGames(PAGE_SIZE, loaded.length)
			.then((page) => {
				setGames([...loaded, ...page]);
				setHasMore(page.length === PAGE_SIZE);
			})
			.catch((error: Error) => setLoadError(error.message))
			.finally(() => setLoadingMore(false));
	}

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
			{!loadError && games?.length === 0 && <p>No games yet</p>}
			<ul className="flex flex-col gap-2">
				{games?.map((game) => (
					<li key={game.id}>
						<GameRow game={game} onSelect={onSelect} />
					</li>
				))}
			</ul>
			{games && hasMore && (
				<button
					type="button"
					className="mt-4 min-h-11 w-full rounded border px-4 py-2 disabled:opacity-50"
					disabled={loadingMore}
					onClick={() => loadMore(games)}
				>
					Show more
				</button>
			)}
		</div>
	);
}
