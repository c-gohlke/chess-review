import type { GameListItem } from "../api/client";

const RESULT_STYLES: Record<GameListItem["result"], string> = {
	win: "border-green-300 dark:border-green-800 bg-green-100 dark:bg-green-950",
	loss: "border-red-300 dark:border-red-800 bg-red-100 dark:bg-red-950",
	draw: "",
};

function formatRatingChange(change: number): string {
	if (change > 0) return `+${change}`;
	return change < 0 ? `−${Math.abs(change)}` : "0";
}

export function GameRow({ game, onSelect }: { game: GameListItem; onSelect: (id: number) => void }) {
	return (
		<button
			type="button"
			className={`w-full rounded border px-4 py-2 text-left ${RESULT_STYLES[game.result]}`}
			onClick={() => onSelect(game.id)}
		>
			<span className="flex items-baseline justify-between gap-3">
				<span>
					{game.white} vs {game.black}
				</span>
				{game.rating_change !== null && (
					<span className="font-bold tabular-nums">{formatRatingChange(game.rating_change)}</span>
				)}
			</span>
			<span className="block text-sm text-gray-700 dark:text-gray-300">{game.opening}</span>
			<span className="block text-sm text-gray-700 dark:text-gray-300">
				{game.result} — {game.time_class} — {game.played_at.slice(0, 10)}
			</span>
		</button>
	);
}
