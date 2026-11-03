import { useEffect, useState } from "react";
import { importChesscom, listUsers } from "./api/client";
import { Board } from "./board/Board";
import { Games } from "./pages/Games";
import { Openings } from "./pages/Openings";
import { Review } from "./pages/Review";
import { Settings } from "./pages/Settings";
import { Statistics } from "./pages/Statistics";

type Tab = "analyze" | "games" | "openings" | "statistics" | "settings";

const PLAYER_KEY = "chess-review-player";

function App() {
	const [tab, setTab] = useState<Tab>("analyze");
	const [gameId, setGameId] = useState<number | null>(null);
	const [users, setUsers] = useState<string[] | null>(null);
	const [usersError, setUsersError] = useState<string | null>(null);
	const [chosenPlayer, setChosenPlayer] = useState(() => localStorage.getItem(PLAYER_KEY));

	const [gamesVersion, setGamesVersion] = useState(0);
	const [syncMessage, setSyncMessage] = useState<string | null>(null);

	const player = users?.find((user) => user === chosenPlayer) ?? users?.[0] ?? null;

	function openGames() {
		setTab("games");
		setGameId(null);
		if (player === null) return;
		setSyncMessage("Checking chess.com for new games…");
		importChesscom(player)
			.then(({ imported }) => {
				setSyncMessage(imported > 0 ? `${imported} new ${imported === 1 ? "game" : "games"}` : null);
				if (imported > 0) setGamesVersion((version) => version + 1);
			})
			.catch((error: Error) => setSyncMessage(`Could not check chess.com: ${error.message}`));
	}

	function choosePlayer(username: string) {
		localStorage.setItem(PLAYER_KEY, username);
		setChosenPlayer(username);
		setGameId(null);
	}

	useEffect(() => {
		listUsers()
			.then(setUsers)
			.catch((error: Error) => setUsersError(error.message));
	}, []);

	function handleImported(username: string) {
		choosePlayer(username);
		listUsers()
			.then(setUsers)
			.catch((error: Error) => setUsersError(error.message));
	}

	return (
		<main className="p-4">
			{/* Five equal columns on a phone, so every tab fits on one row. */}
			<div className="mx-auto mb-4 grid w-full max-w-[600px] grid-cols-5 gap-1 sm:flex sm:gap-2">
				<button
					type="button"
					className={`rounded px-1 py-2 text-sm sm:px-4 sm:text-base ${tab === "games" ? "bg-blue-600 text-white" : "border"}`}
					onClick={openGames}
				>
					Games
				</button>
				<button
					type="button"
					className={`rounded px-1 py-2 text-sm sm:px-4 sm:text-base ${tab === "openings" ? "bg-blue-600 text-white" : "border"}`}
					onClick={() => {
						setTab("openings");
						setGameId(null);
					}}
				>
					Openings
				</button>
				<button
					type="button"
					className={`rounded px-1 py-2 text-sm sm:px-4 sm:text-base ${tab === "statistics" ? "bg-blue-600 text-white" : "border"}`}
					onClick={() => {
						setTab("statistics");
						setGameId(null);
					}}
				>
					Statistics
				</button>
				<button
					type="button"
					className={`rounded px-1 py-2 text-sm sm:px-4 sm:text-base ${tab === "settings" ? "bg-blue-600 text-white" : "border"}`}
					onClick={() => setTab("settings")}
				>
					Settings
				</button>
				<button
					type="button"
					className={`rounded px-1 py-2 text-sm sm:px-4 sm:text-base ${tab === "analyze" ? "bg-blue-600 text-white" : "border"}`}
					onClick={() => setTab("analyze")}
				>
					Analyze
				</button>
			</div>
			{tab !== "analyze" && usersError && (
				<p className="mx-auto w-full max-w-[600px] text-red-600 dark:text-red-400">{usersError}</p>
			)}
			{tab === "games" && gameId === null && syncMessage && (
				<p className="mx-auto mb-4 w-full max-w-[600px] text-sm">{syncMessage}</p>
			)}
			{tab === "analyze" && <Board />}
			{tab === "settings" && users && <Settings users={users} player={player} onChoose={choosePlayer} />}
			{tab === "games" &&
				users &&
				(gameId === null ? (
					<Games key={player} player={player} version={gamesVersion} onSelect={setGameId} onImported={handleImported} />
				) : (
					<Review gameId={gameId} onBack={() => setGameId(null)} />
				))}
			{tab === "openings" && gameId !== null && <Review gameId={gameId} onBack={() => setGameId(null)} />}
			{/* Stays mounted behind a replay, so Back returns to the same expanded rows and filters. */}
			{(tab === "openings" || tab === "statistics") && users && player === null && (
				<p className="mx-auto w-full max-w-[600px]">No games yet</p>
			)}
			{tab === "statistics" && player && <Statistics key={player} player={player} />}
			{tab === "openings" && player && (
				<div hidden={gameId !== null}>
					<Openings key={player} player={player} onSelect={setGameId} />
				</div>
			)}
		</main>
	);
}

export default App;
