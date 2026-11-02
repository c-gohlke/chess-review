import { useEffect, useRef } from "react";
import type { GameDetail } from "../api/client";

type Analysis = NonNullable<GameDetail["analysis"]>;
type Moment = Analysis["moments"][number];

type Props = {
	analysis: GameDetail["analysis"] | undefined;
	moves: string[];
	ply: number;
	onSelectPly: (ply: number) => void;
};

type Block = { key: Moment } | { run: number[] };

const COSTLY = "bg-amber-100 dark:bg-amber-950 font-bold text-amber-900 dark:text-amber-200";
const DECIDING = "bg-red-100 dark:bg-red-950 font-bold text-red-900 dark:text-red-200";

// Key moves get a block of their own; the moves between them run on as one paragraph.
function toBlocks(moveCount: number, moments: Moment[]): Block[] {
	const byPly = new Map(moments.map((moment) => [moment.ply, moment]));
	const blocks: Block[] = [];
	let run: number[] = [];
	for (let index = 0; index < moveCount; index += 1) {
		const moment = byPly.get(index);
		if (moment) {
			if (run.length > 0) blocks.push({ run });
			blocks.push({ key: moment });
			run = [];
		} else {
			run.push(index);
		}
	}
	if (run.length > 0) blocks.push({ run });
	return blocks;
}

function moveNumber(index: number): string {
	return `${Math.floor(index / 2) + 1}${index % 2 === 1 ? "…" : "."}`;
}

function MoveButton({
	index,
	san,
	ply,
	moment,
	onSelectPly,
}: {
	index: number;
	san: string;
	ply: number;
	moment?: Moment;
	onSelectPly: Props["onSelectPly"];
}) {
	const isCurrent = ply === index + 1;
	const emphasis = moment ? (moment.is_decisive ? DECIDING : COSTLY) : "";
	const mark = moment ? (moment.is_decisive ? "??" : "?") : "";
	return (
		<button
			type="button"
			aria-current={isCurrent ? "step" : undefined}
			className={`rounded px-1 font-mono ${emphasis} ${isCurrent ? "outline-2 outline-blue-600 dark:outline-blue-400" : ""}`}
			onClick={() => onSelectPly(index + 1)}
		>
			{san}
			{mark}
		</button>
	);
}

function KeyMove({
	moment,
	moves,
	ply,
	onSelectPly,
}: Pick<Props, "moves" | "ply" | "onSelectPly"> & { moment: Moment }) {
	return (
		<div className="my-2">
			<span className="font-mono text-sm text-gray-600 dark:text-gray-400">{moveNumber(moment.ply)}</span>{" "}
			<MoveButton index={moment.ply} san={moves[moment.ply]} ply={ply} moment={moment} onSelectPly={onSelectPly} />
			<p
				className={`mt-1 border-l-2 pl-2 text-sm ${moment.is_decisive ? "border-red-700 dark:border-red-400" : "border-amber-700 dark:border-amber-400"}`}
			>
				<strong>
					{moment.is_decisive ? "Deciding move" : "Costly move"} by {moment.player}.
				</strong>{" "}
				{moment.labels.join(", ")}. Gave away {moment.win_lost} points of win chance.
			</p>
		</div>
	);
}

function MoveRun({ run, moves, ply, onSelectPly }: Pick<Props, "moves" | "ply" | "onSelectPly"> & { run: number[] }) {
	return (
		<p className="leading-7">
			{run.map((index) => (
				<span key={index}>
					{(index % 2 === 0 || index === run[0]) && (
						<span className="font-mono text-sm text-gray-600 dark:text-gray-400">{moveNumber(index)} </span>
					)}
					<MoveButton index={index} san={moves[index]} ply={ply} onSelectPly={onSelectPly} />{" "}
				</span>
			))}
		</p>
	);
}

export function GameStatistics({ analysis, moves, ply, onSelectPly }: Props) {
	const listRef = useRef<HTMLDivElement>(null);

	// Scrolls the list only, so stepping on a phone does not move the board off screen.
	// biome-ignore lint/correctness/useExhaustiveDependencies: runs when the current move changes.
	useEffect(() => {
		const list = listRef.current;
		const current = list?.querySelector("[aria-current]");
		if (!list || !(current instanceof HTMLElement)) return;
		const top = current.getBoundingClientRect().top - list.getBoundingClientRect().top;
		if (top < 0 || top > list.clientHeight - current.offsetHeight) {
			list.scrollTop += top - list.clientHeight / 2;
		}
	}, [ply]);

	const blocks = toBlocks(moves.length, analysis?.moments ?? []);
	return (
		<aside className="w-full min-w-0 lg:w-80 lg:shrink-0">
			<h2 className="mb-2 text-lg font-bold">Game statistics</h2>
			{analysis ? (
				<p className="mb-2">
					Decided by: <strong>{analysis.decided_by}</strong>
				</p>
			) : (
				<p className="mb-2">This game has not been analysed yet. You can start the engine from the Statistics tab.</p>
			)}
			{analysis && analysis.moments.length === 0 && <p className="mb-2">No costly errors found.</p>}
			{analysis && analysis.moments.length > 0 && (
				<ul className="mb-2 text-sm text-gray-600 dark:text-gray-400">
					<li>
						<span className={`rounded px-1 font-mono ${COSTLY}`}>?</span> Costly move, gave away a lot of win chance
					</li>
					<li className="mt-1">
						<span className={`rounded px-1 font-mono ${DECIDING}`}>??</span> Deciding move, lost the game
					</li>
				</ul>
			)}
			<div ref={listRef} data-testid="move-list" className="lg:max-h-[560px] lg:overflow-y-auto lg:pr-1">
				{blocks.map((block) =>
					"key" in block ? (
						<KeyMove key={block.key.ply} moment={block.key} moves={moves} ply={ply} onSelectPly={onSelectPly} />
					) : (
						<MoveRun key={block.run[0]} run={block.run} moves={moves} ply={ply} onSelectPly={onSelectPly} />
					),
				)}
			</div>
		</aside>
	);
}
