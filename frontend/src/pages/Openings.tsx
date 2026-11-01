import { useEffect, useState } from "react";
import { getOpenings, type OpeningStats, type OpeningSummary } from "../api/client";

type Colour = "white" | "black";

const COLOUR_LABELS: Record<Colour, string> = { white: "White", black: "Black" };

function formatNet(net: number): string {
	if (net === 0) return "0.0";
	return `${net > 0 ? "+" : "−"}${Math.abs(net).toFixed(1)}`;
}

function sumNet(openings: OpeningStats[]): number {
	return openings.reduce((total, opening) => total + opening.net, 0);
}

function NetBar({ net, scale }: { net: number; scale: number }) {
	const width = `${(Math.abs(net) / scale) * 100}%`;
	return (
		<div className="grid h-2.5 grid-cols-2 bg-gray-100">
			<div className="flex justify-end border-r border-gray-500">
				{net < 0 && <div className="bg-orange-500" style={{ width }} />}
			</div>
			<div className="flex">{net > 0 && <div className="bg-blue-700" style={{ width }} />}</div>
		</div>
	);
}

function OpeningRow({ opening, scale }: { opening: OpeningStats; scale: number }) {
	const score = Math.round(((opening.wins + opening.draws / 2) / opening.games) * 100);
	return (
		<div className="flex flex-col gap-1.5">
			<div className="flex items-baseline justify-between gap-3">
				<span className="font-semibold">{opening.name}</span>
				<span className="font-bold tabular-nums">{formatNet(opening.net)}</span>
			</div>
			<NetBar net={opening.net} scale={scale} />
			<span className="text-sm text-gray-600 tabular-nums">
				{opening.games} {opening.games === 1 ? "game" : "games"} · {score}% · {opening.wins}W {opening.draws}D{" "}
				{opening.losses}L
			</span>
		</div>
	);
}

function FamilyRow({ family, scale }: { family: OpeningStats; scale: number }) {
	const [open, setOpen] = useState(false);
	return (
		<li className="border-t">
			<button
				type="button"
				className="min-h-11 w-full py-2.5 text-left"
				aria-expanded={open}
				onClick={() => setOpen(!open)}
			>
				<OpeningRow opening={family} scale={scale} />
			</button>
			{open && (
				<ul className="mb-3 flex flex-col gap-3 rounded bg-blue-50 p-3">
					{family.variations.map((variation) => (
						<li key={variation.name}>
							<OpeningRow opening={variation} scale={scale} />
						</li>
					))}
				</ul>
			)}
		</li>
	);
}

export function Openings() {
	const [summary, setSummary] = useState<OpeningSummary | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [colour, setColour] = useState<Colour>("white");

	useEffect(() => {
		getOpenings()
			.then(setSummary)
			.catch((err: Error) => setError(err.message));
	}, []);

	if (error) return <p className="mx-auto w-full max-w-[600px] text-red-600">{error}</p>;
	if (!summary) return null;

	if (summary.white.length + summary.black.length === 0) {
		return <p className="mx-auto w-full max-w-[600px]">No games yet</p>;
	}

	const everyOpening = [...summary.white, ...summary.black];
	// One scale for both colours and for variations, so bar lengths stay comparable.
	const scale = Math.max(...everyOpening.map((opening) => Math.abs(opening.net)), 0.5);
	const repeated = summary[colour].filter((opening) => opening.games > 1);
	const once = summary[colour].filter((opening) => opening.games === 1);

	return (
		<div className="mx-auto flex w-full max-w-[600px] flex-col gap-4">
			<div className="grid grid-cols-2 gap-2">
				{(["white", "black"] as const).map((option) => (
					<button
						key={option}
						type="button"
						className={`min-h-11 rounded px-4 py-2 text-left ${option === colour ? "bg-blue-600 text-white" : "border"}`}
						aria-pressed={option === colour}
						onClick={() => setColour(option)}
					>
						{COLOUR_LABELS[option]} <span className="font-bold tabular-nums">{formatNet(sumNet(summary[option]))}</span>
					</button>
				))}
			</div>
			<ul className="flex flex-col">
				{repeated.map((family) => (
					<FamilyRow key={family.name} family={family} scale={scale} />
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
