import { useState } from "react";
import { Board } from "./board/Board";
import { Games } from "./pages/Games";
import { Review } from "./pages/Review";

type Tab = "play" | "games";

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
			</div>
			{tab === "play" && <Board />}
			{tab === "games" &&
				(gameId === null ? <Games onSelect={setGameId} /> : <Review gameId={gameId} onBack={() => setGameId(null)} />)}
		</main>
	);
}

export default App;
