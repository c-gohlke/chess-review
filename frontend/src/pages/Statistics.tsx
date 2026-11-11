import { useEffect, useState } from "react";
import { type ForkSummary, getForkStatistics, getPawnPushStatistics, type PawnPushSummary } from "../api/client";
import { EngineRun } from "./EngineRun";

function percent(part: number, whole: number): string {
	return `${((part / whole) * 100).toFixed(1)}%`;
}

function Forks({ player, forks }: { player: string; forks: ForkSummary }) {
	const total = forks.analysed_losses;
	if (total === 0) return <p>{player}'s games have not been analysed yet.</p>;
	return (
		<>
			<p>
				A fork figured in {forks.losses_with_fork} of {total} analysed losses ({percent(forks.losses_with_fork, total)}
				).
			</p>
			<p className="mt-1">
				It was the deciding error in {forks.decided_by_fork} ({percent(forks.decided_by_fork, total)}).
			</p>
			<table className="mt-4 w-full">
				<thead>
					<tr className="text-left text-sm text-gray-600 dark:text-gray-400">
						<th className="py-1 font-normal">Kind of fork</th>
						<th className="py-1 text-right font-normal">Losses</th>
						<th className="py-1 text-right font-normal">Share</th>
					</tr>
				</thead>
				<tbody>
					{forks.kinds.map((kind) => (
						<tr key={kind.name} className="border-t">
							<td className="py-2">{kind.name}</td>
							<td className="py-2 text-right tabular-nums">{kind.losses}</td>
							<td className="py-2 text-right tabular-nums">{percent(kind.losses, total)}</td>
						</tr>
					))}
				</tbody>
			</table>
			<p className="mt-3 text-sm text-gray-600 dark:text-gray-400">
				A loss with two kinds of fork counts once under each kind.
			</p>
		</>
	);
}

const WINGS: [PawnPushSummary["counts"][number]["wing"], string][] = [
	["queenside", "Queen side"],
	["kingside", "King side"],
];

function PawnPushes({ pawnPushes }: { pawnPushes: PawnPushSummary }) {
	const total = pawnPushes.analysed_games;
	if (total === 0) return null;
	const cell = (wing: string, timing: string) => {
		const count = pawnPushes.counts.find((row) => row.wing === wing && row.timing === timing)?.games ?? 0;
		return `${count} (${percent(count, total)})`;
	};
	return (
		<>
			<h2 className="mt-8 mb-2 text-lg font-bold">Pawn pushes</h2>
			<p>Games out of {total} analysed where a pawn push on a wing came too early or too late.</p>
			<table className="mt-4 w-full">
				<thead>
					<tr className="text-left text-sm text-gray-600 dark:text-gray-400">
						<th className="py-1 font-normal">Wing</th>
						<th className="py-1 text-right font-normal">Too early</th>
						<th className="py-1 text-right font-normal">Too late</th>
					</tr>
				</thead>
				<tbody>
					{WINGS.map(([wing, label]) => (
						<tr key={wing} className="border-t">
							<td className="py-2">{label}</td>
							<td className="py-2 text-right tabular-nums">{cell(wing, "early")}</td>
							<td className="py-2 text-right tabular-nums">{cell(wing, "late")}</td>
						</tr>
					))}
				</tbody>
			</table>
			<p className="mt-3 text-sm text-gray-600 dark:text-gray-400">
				Queen side is the a–c pawns, king side the f–h pawns. Too early: a push the engine didn't want cost 10 or more
				win-percentage points. Too late: the engine wanted a push there and the move played instead cost that much.
			</p>
		</>
	);
}

export function Statistics({ player }: { player: string }) {
	const [forks, setForks] = useState<ForkSummary | null>(null);
	const [pawnPushes, setPawnPushes] = useState<PawnPushSummary | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [runsFinished, setRunsFinished] = useState(0);

	// biome-ignore lint/correctness/useExhaustiveDependencies: a finished run changes the numbers.
	useEffect(() => {
		getForkStatistics(player)
			.then(setForks)
			.catch((err: Error) => setError(err.message));
		getPawnPushStatistics(player)
			.then(setPawnPushes)
			.catch((err: Error) => setError(err.message));
	}, [player, runsFinished]);

	return (
		<section className="mx-auto w-full max-w-[600px]">
			<EngineRun player={player} onFinished={() => setRunsFinished((count) => count + 1)} />
			<h2 className="mb-2 text-lg font-bold">Losses to forks</h2>
			{error && <p className="text-red-600 dark:text-red-400">{error}</p>}
			{forks && <Forks player={player} forks={forks} />}
			{pawnPushes && <PawnPushes pawnPushes={pawnPushes} />}
		</section>
	);
}
