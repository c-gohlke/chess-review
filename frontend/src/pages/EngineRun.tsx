import { useEffect, useRef, useState } from "react";
import { type AnalysisState, getAnalysis, startAnalysis } from "../api/client";

const POLL_MS = 2000;
// Measured on the first full run: about 19 positions a second at 62 new positions a game.
const SECONDS_PER_GAME = 3.3;

const RUNNING_PHASES = ["preparing", "analysing", "classifying"];

function isRunning(state: AnalysisState | null): boolean {
	return state !== null && RUNNING_PHASES.includes(state.phase);
}

function duration(games: number): string {
	const minutes = Math.ceil((games * SECONDS_PER_GAME) / 60);
	if (minutes < 60) return `about ${minutes} min`;
	return `about ${Math.round(minutes / 6) / 10} hours`;
}

function Progress({ state }: { state: AnalysisState }) {
	if (state.phase === "analysing") {
		return (
			<>
				<p>
					Running the engine: {state.done} of {state.total} positions
				</p>
				<progress className="mt-1 w-full" value={state.done} max={Math.max(state.total, 1)} />
			</>
		);
	}
	return <p>{state.phase === "preparing" ? "Preparing the run…" : "Working out the reasons…"}</p>;
}

export function EngineRun({ player, onFinished }: { player: string; onFinished: () => void }) {
	const [state, setState] = useState<AnalysisState | null>(null);
	const [error, setError] = useState<string | null>(null);
	const wasRunning = useRef(false);
	const running = isRunning(state);

	useEffect(() => {
		if (wasRunning.current && !running) onFinished();
		wasRunning.current = running;
	}, [running, onFinished]);

	useEffect(() => {
		function refresh() {
			getAnalysis(player)
				.then((next) => {
					setState(next);
					setError(null);
				})
				.catch((err: Error) => setError(err.message));
		}
		refresh();
		if (!running) return;
		const timer = setInterval(refresh, POLL_MS);
		return () => clearInterval(timer);
	}, [player, running]);

	function handleStart() {
		startAnalysis(player)
			.then((next) => {
				setState(next);
				setError(null);
			})
			.catch((err: Error) => setError(err.message));
	}

	const otherPlayer = state?.running_player && state.running_player !== player ? state.running_player : null;
	return (
		<div className="mb-6 rounded border p-3">
			<h2 className="mb-1 text-lg font-bold">Engine analysis</h2>
			{error && <p className="text-red-600 dark:text-red-400">{error}</p>}
			{state && (
				<p>
					{state.games - state.unanalysed} of {state.games} games analysed.
				</p>
			)}
			{state?.phase === "failed" && (
				<p className="text-red-600 dark:text-red-400">The last run failed: {state.error}</p>
			)}
			{running && state && <Progress state={state} />}
			{otherPlayer && <p className="text-sm">The engine is busy with {otherPlayer}.</p>}
			{state && !running && !otherPlayer && state.unanalysed > 0 && (
				<button type="button" className="mt-2 rounded bg-blue-600 px-4 py-2 text-white" onClick={handleStart}>
					Analyse {state.unanalysed} {state.unanalysed === 1 ? "game" : "games"} ({duration(state.unanalysed)})
				</button>
			)}
		</div>
	);
}
