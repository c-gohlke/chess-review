import { useState } from "react";
import { Board } from "./board/Board";
import { Games } from "./pages/Games";
import { Openings } from "./pages/Openings";
import { Review } from "./pages/Review";

type Tab = "play" | "games" | "openings";

function App() {
	const [tab, setTab] = useState<Tab>("play");
	const [gameId, setGameId] = useState<number | null>(null);

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
			{tab === "play" && <Board />}
			{tab === "games" &&
				(gameId === null ? <Games onSelect={setGameId} /> : <Review gameId={gameId} onBack={() => setGameId(null)} />)}
			{tab === "openings" && gameId !== null && <Review gameId={gameId} onBack={() => setGameId(null)} />}
			{/* Stays mounted behind a replay, so Back returns to the same expanded rows and filters. */}
			{tab === "openings" && (
				<div hidden={gameId !== null}>
					<Openings onSelect={setGameId} />
				</div>
			)}
		</main>
	);
}

export default App;
