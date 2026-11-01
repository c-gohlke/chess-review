import { useEffect, useState } from "react";
import {
	type Colour,
	type GameListItem,
	getOpeningGames,
	getOpenings,
	type OpeningStats,
	type OpeningSummary,
	type TimeClass,
} from "../api/client";
import { GameRow } from "../components/GameRow";

type Filters = { colour: Colour; months: string; timeClass: TimeClass | "" };

const COLOUR_LABELS: Record<Colour, string> = { white: "White", black: "Black" };

const PERIODS = [
	["1", "Last month"],
	["3", "Last 3 months"],
	["12", "Last year"],
	["", "All time"],
];

const TIME_CONTROLS: [TimeClass | "", string][] = [
	["", "All time controls"],
	["bullet", "Bullet"],
	["blitz", "Blitz"],
	["rapid", "Rapid"],
	["daily", "Daily"],
];

function monthsAgo(months: string): Date | null {
	if (!months) return null;
	const date = new Date();
	date.setMonth(date.getMonth() - Number(months));
	return date;
}

function formatNet(net: number): string {
	if (net === 0) return "0.0";
	return `${net > 0 ? "+" : "−"}${Math.abs(net).toFixed(1)}`;
}

function sumNet(openings: OpeningStats[]): number {
	return openings.reduce((total, opening) => total + opening.net, 0);
}

// Centred on 50%: the bar reaches the left edge at 0% and the right edge at 100%.
function ScoreBar({ score }: { score: number }) {
	const width = `${Math.abs(score - 50) * 2}%`;
	return (
		<div className="grid h-2.5 grid-cols-2 bg-gray-100">
			<div className="flex justify-end border-r border-gray-500">
				{score < 50 && <div className="bg-orange-500" style={{ width }} />}
			</div>
			<div className="flex">{score > 50 && <div className="bg-blue-700" style={{ width }} />}</div>
		</div>
	);
}

function OpeningRow({ opening }: { opening: OpeningStats }) {
	const score = ((opening.wins + opening.draws / 2) / opening.games) * 100;
	return (
		<div className="flex flex-col gap-1.5">
			<div className="flex items-baseline justify-between gap-3">
				<span className="font-semibold">{opening.name}</span>
				<span className="font-bold tabular-nums">{Math.round(score)}%</span>
			</div>
			<ScoreBar score={score} />
			<span className="text-sm text-gray-600 tabular-nums">
				{opening.games} {opening.games === 1 ? "game" : "games"} · {formatNet(opening.net)} · {opening.wins}W{" "}
				{opening.draws}D {opening.losses}L
			</span>
		</div>
	);
}

function VariationRow({
	family,
	variation,
	filters: { colour, months, timeClass },
	onSelect,
}: {
	family: string;
	variation: OpeningStats;
	filters: Filters;
	onSelect: (id: number) => void;
}) {
	const [open, setOpen] = useState(false);
	const [games, setGames] = useState<GameListItem[]>([]);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!open) return;
		// A slower, older request must not overwrite the result of the latest filters.
		let stale = false;
		getOpeningGames(family, variation.name, colour, monthsAgo(months), timeClass || null)
			.then((result) => {
				if (!stale) setGames(result);
			})
			.catch((err: Error) => setError(err.message));
		return () => {
			stale = true;
		};
	}, [open, family, variation.name, colour, months, timeClass]);

	return (
		<li>
			<button type="button" className="min-h-11 w-full text-left" aria-expanded={open} onClick={() => setOpen(!open)}>
				<OpeningRow opening={variation} />
			</button>
			{open && (
				<ul className="mt-3 flex flex-col gap-2 pl-3">
					{error && <li className="text-red-600">{error}</li>}
					{games.map((game) => (
						<li key={game.id}>
							<GameRow game={game} onSelect={onSelect} />
						</li>
					))}
				</ul>
			)}
		</li>
	);
}

function FamilyRow({
	family,
	filters,
	onSelect,
}: {
	family: OpeningStats;
	filters: Filters;
	onSelect: (id: number) => void;
}) {
	const [open, setOpen] = useState(false);
	return (
		<li className="border-t">
			<button
				type="button"
				className="min-h-11 w-full py-2.5 text-left"
				aria-expanded={open}
				onClick={() => setOpen(!open)}
			>
				<OpeningRow opening={family} />
			</button>
			{open && (
				<ul className="mb-3 flex flex-col gap-3 rounded bg-blue-50 p-3">
					{family.variations.map((variation) => (
						<VariationRow
							key={variation.name}
							family={family.name}
							variation={variation}
							filters={filters}
							onSelect={onSelect}
						/>
					))}
				</ul>
			)}
		</li>
	);
}

export function Openings({ onSelect }: { onSelect: (id: number) => void }) {
	const [summary, setSummary] = useState<OpeningSummary | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [colour, setColour] = useState<Colour>("white");
	const [months, setMonths] = useState("3");
	const [timeClass, setTimeClass] = useState<TimeClass | "">("");

	useEffect(() => {
		// A slower, older request must not overwrite the result of the latest filters.
		let stale = false;
		getOpenings(monthsAgo(months), timeClass || null)
			.then((result) => {
				if (!stale) setSummary(result);
			})
			.catch((err: Error) => setError(err.message));
		return () => {
			stale = true;
		};
	}, [months, timeClass]);

	const openings = summary?.[colour] ?? [];
	const repeated = openings.filter((opening) => opening.games > 1);
	const once = openings.filter((opening) => opening.games === 1);

	return (
		<div className="mx-auto flex w-full max-w-[600px] flex-col gap-4">
			<div className="grid grid-cols-2 gap-2">
				<select
					aria-label="Period"
					className="min-h-11 rounded border px-3"
					value={months}
					onChange={(event) => setMonths(event.target.value)}
				>
					{PERIODS.map(([value, label]) => (
						<option key={value} value={value}>
							{label}
						</option>
					))}
				</select>
				<select
					aria-label="Time control"
					className="min-h-11 rounded border px-3"
					value={timeClass}
					onChange={(event) => setTimeClass(event.target.value as TimeClass | "")}
				>
					{TIME_CONTROLS.map(([value, label]) => (
						<option key={value} value={value}>
							{label}
						</option>
					))}
				</select>
			</div>
			{error && <p className="text-red-600">{error}</p>}
			{summary && (
				<div className="grid grid-cols-2 gap-2">
					{(["white", "black"] as const).map((option) => (
						<button
							key={option}
							type="button"
							className={`min-h-11 rounded px-4 py-2 text-left ${option === colour ? "bg-blue-600 text-white" : "border"}`}
							aria-pressed={option === colour}
							onClick={() => setColour(option)}
						>
							{COLOUR_LABELS[option]}{" "}
							<span className="font-bold tabular-nums">{formatNet(sumNet(summary[option]))}</span>
						</button>
					))}
				</div>
			)}
			{summary && openings.length === 0 && <p>No games for these filters</p>}
			<ul className="flex flex-col">
				{repeated.map((family) => (
					<FamilyRow
						key={`${colour}-${family.name}`}
						family={family}
						filters={{ colour, months, timeClass }}
						onSelect={onSelect}
					/>
				))}
				{once.length > 0 && (
					<li className="border-t py-3 text-sm text-gray-600">
						{once.length} played once: {formatNet(sumNet(once))}
					</li>
				)}
			</ul>
		</div>
	);
}
