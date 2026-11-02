import { useEffect, useState } from "react";
import { type ForkSummary, getForkStatistics } from "../api/client";

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
					<tr className="text-left text-sm text-gray-600">
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
			<p className="mt-3 text-sm text-gray-600">A loss with two kinds of fork counts once under each kind.</p>
		</>
	);
}

export function Statistics({ player }: { player: string }) {
	const [forks, setForks] = useState<ForkSummary | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		getForkStatistics(player)
			.then(setForks)
			.catch((err: Error) => setError(err.message));
	}, [player]);

	return (
		<section className="mx-auto w-full max-w-[600px]">
			<h2 className="mb-2 text-lg font-bold">Losses to forks</h2>
			{error && <p className="text-red-600">{error}</p>}
			{forks && <Forks player={player} forks={forks} />}
		</section>
	);
}
