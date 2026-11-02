import { useEffect, useState } from "react";
import { listUsers } from "./api/client";
import { Board } from "./board/Board";
import { Games } from "./pages/Games";
import { Openings } from "./pages/Openings";
import { Review } from "./pages/Review";

type Tab = "play" | "games" | "openings";

const PLAYER_KEY = "chess-review-player";

function App() {
	const [tab, setTab] = useState<Tab>("play");
	const [gameId, setGameId] = useState<number | null>(null);
	const [users, setUsers] = useState<string[] | null>(null);
	const [usersError, setUsersError] = useState<string | null>(null);
	const [chosenPlayer, setChosenPlayer] = useState(() => localStorage.getItem(PLAYER_KEY));

	const player = users?.find((user) => user === chosenPlayer) ?? users?.[0] ?? null;

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
			<div className="mx-auto mb-4 flex w-full max-w-[600px] gap-2">
				<button
					type="button"
					className={`rounded px-4 py-2 ${tab === "play" ? "bg-blue-600 text-white" : "border"}`}
					onClick={() => setTab("play")}
				>
					Play
				</button>
				<button
					type="button"
					className={`rounded px-4 py-2 ${tab === "games" ? "bg-blue-600 text-white" : "border"}`}
					onClick={() => {
						setTab("games");
						setGameId(null);
					}}
				>
					Games
				</button>
				<button
					type="button"
					className={`rounded px-4 py-2 ${tab === "openings" ? "bg-blue-600 text-white" : "border"}`}
					onClick={() => {
						setTab("openings");
						setGameId(null);
					}}
				>
					Openings
				</button>
			</div>
			{tab !== "play" && users && users.length > 1 && (
				<div className="mx-auto mb-4 w-full max-w-[600px]">
					<select
						aria-label="Player"
						className="min-h-11 w-full rounded border px-3"
						value={player ?? ""}
						onChange={(event) => choosePlayer(event.target.value)}
					>
						{users.map((user) => (
							<option key={user} value={user}>
								{user}
							</option>
						))}
					</select>
				</div>
			)}
			{tab !== "play" && usersError && <p className="mx-auto w-full max-w-[600px] text-red-600">{usersError}</p>}
			{tab === "play" && <Board />}
			{tab === "games" &&
				users &&
				(gameId === null ? (
					<Games key={player} player={player} onSelect={setGameId} onImported={handleImported} />
				) : (
					<Review gameId={gameId} onBack={() => setGameId(null)} />
				))}
			{tab === "openings" && gameId !== null && <Review gameId={gameId} onBack={() => setGameId(null)} />}
			{/* Stays mounted behind a replay, so Back returns to the same expanded rows and filters. */}
			{tab === "openings" && users && player === null && <p className="mx-auto w-full max-w-[600px]">No games yet</p>}
			{tab === "openings" && player && (
				<div hidden={gameId !== null}>
					<Openings key={player} player={player} onSelect={setGameId} />
				</div>
			)}
		</main>
	);
}

export default App;
