import type { GameDetail } from "../api/client";

type Props = {
	analysis: GameDetail["analysis"] | undefined;
	moves: string[];
	ply: number;
	onSelectPly: (ply: number) => void;
};

export function GameStatistics({ analysis, moves, ply, onSelectPly }: Props) {
	return (
		<aside className="w-full min-w-0 lg:w-80 lg:shrink-0">
			<h2 className="mb-2 text-lg font-bold">Game statistics</h2>
			{!analysis && <p>This game has not been analysed yet.</p>}
			{analysis && (
				<>
					<p className="mb-3">
						Decided by: <strong>{analysis.decided_by}</strong>
					</p>
					{analysis.moments.length === 0 && <p>No costly errors found.</p>}
					<ol className="flex flex-col gap-2">
						{analysis.moments.map((moment) => (
							<li key={moment.ply}>
								<button
									type="button"
									aria-current={ply === moment.ply + 1 ? "step" : undefined}
									className={`w-full rounded border px-3 py-2 text-left ${ply === moment.ply + 1 ? "border-blue-600" : ""}`}
									onClick={() => onSelectPly(moment.ply + 1)}
								>
									<span className="font-bold text-blue-700 underline">
										Move {moment.move_number}
										{moment.ply % 2 === 1 ? "…" : "."} {moves[moment.ply]}
									</span>{" "}
									<span className="ml-1 text-sm text-gray-600">{moment.player}</span>{" "}
									{moment.is_decisive && <span className="ml-1 text-sm font-bold">Deciding move</span>}{" "}
									<span className="mt-1 block text-sm">{moment.labels.join(", ")}</span>
								</button>
							</li>
						))}
					</ol>
				</>
			)}
		</aside>
	);
}
