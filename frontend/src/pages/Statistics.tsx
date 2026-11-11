import { useEffect, useState } from "react";
import {
	type BaselineStatistics,
	type ForkKind,
	type ForkSummary,
	getBaselines,
	getForkStatistics,
	getPawnPushStatistics,
	getReasonStatistics,
	type PawnPushSummary,
	type ReasonCount,
	type ReasonSummary,
	type ResultReasons,
} from "../api/client";
import { EngineRun } from "./EngineRun";

function percent(part: number, whole: number): string {
	return `${((part / whole) * 100).toFixed(1)}%`;
}

function bandLabel(band: number): string {
	return `${band}–${band + 99}`;
}

// The same counts for the baseline players, to compare shares against.
type Comparison = { counts: Map<string, number>; total: number } | null;

function comparison(rows: { name: string; count: number }[], total: number): Comparison {
	return { counts: new Map(rows.map((row) => [row.name, row.count])), total };
}

function BaselineNote({ part, whole }: { part: number; whole: number }) {
	return <span className="text-gray-600 dark:text-gray-400"> · baseline {percent(part, whole)}</span>;
}

// Green for what won the player games, red for what lost them.
type Tone = "won" | "lost" | "neutral";

const TONES: Record<Tone, string> = {
	won: "text-green-700 dark:text-green-400",
	lost: "text-red-700 dark:text-red-400",
	neutral: "",
};

// Stays in view while its table scrolls past, so long tables keep their context. The background hides the rows below.
function StickyHead({ title, tone, children }: { title: string; tone: Tone; children: React.ReactNode }) {
	return (
		<thead className="sticky top-0 bg-[Canvas] dark:bg-[#2b2d31]">
			<tr>
				<th colSpan={4} className={`pt-2 text-left text-sm font-semibold ${TONES[tone]}`}>
					{title}
				</th>
			</tr>
			<tr className="text-left text-sm text-gray-600 dark:text-gray-400">{children}</tr>
		</thead>
	);
}

function ShareTable({
	title,
	tone,
	heading,
	countHeading,
	rows,
	total,
	baseline,
}: {
	title: string;
	tone: Tone;
	heading: string;
	countHeading: string;
	rows: { name: string; count: number }[];
	total: number;
	baseline: Comparison;
}) {
	// Reasons only the baseline players had still show, at zero for the player.
	const names = new Set(rows.map((row) => row.name));
	const baselineOnly = [...(baseline?.counts.keys() ?? [])].filter((name) => !names.has(name));
	const allRows = [...rows, ...baselineOnly.map((name) => ({ name, count: 0 }))];
	return (
		<table className="mt-4 w-full">
			<StickyHead title={title} tone={tone}>
				<th className="py-1 font-normal">{heading}</th>
				<th className="py-1 pl-3 text-right font-normal">{countHeading}</th>
				<th className="py-1 pl-3 text-right font-normal">Share</th>
				{baseline && <th className="py-1 pl-3 text-right font-normal">Baseline</th>}
			</StickyHead>
			<tbody>
				{allRows.map((row) => (
					<tr key={row.name} className="border-t">
						<td className={`py-2 ${TONES[tone]}`}>{row.name}</td>
						<td className="py-2 pl-3 text-right tabular-nums">{row.count}</td>
						<td className="py-2 pl-3 text-right tabular-nums">{percent(row.count, total)}</td>
						{baseline && (
							<td className="py-2 pl-3 text-right tabular-nums text-gray-600 dark:text-gray-400">
								{percent(baseline.counts.get(row.name) ?? 0, baseline.total)}
							</td>
						)}
					</tr>
				))}
			</tbody>
		</table>
	);
}

function forkRows(kinds: ForkKind[]): { name: string; count: number }[] {
	return kinds.map((kind) => ({ name: kind.name, count: kind.losses }));
}

function Forks({ player, forks, baseline }: { player: string; forks: ForkSummary; baseline: ForkSummary | null }) {
	const total = forks.analysed_losses;
	if (total === 0) return <p>{player}'s games have not been analysed yet.</p>;
	const base = baseline?.analysed_losses ?? 0;
	return (
		<>
			<p>
				A fork figured in {forks.losses_with_fork} of {total} analysed losses ({percent(forks.losses_with_fork, total)})
				{baseline && <BaselineNote part={baseline.losses_with_fork} whole={base} />}.
			</p>
			<p className="mt-1">
				It was the deciding error in {forks.decided_by_fork} ({percent(forks.decided_by_fork, total)})
				{baseline && <BaselineNote part={baseline.decided_by_fork} whole={base} />}.
			</p>
			<ShareTable
				title="Losses to forks"
				tone="lost"
				heading="Kind of fork"
				countHeading="Losses"
				rows={forkRows(forks.kinds)}
				total={total}
				baseline={baseline && comparison(forkRows(baseline.kinds), base)}
			/>
			<p className="mt-4">
				{player} missed a fork of their own in {forks.losses_with_missed_fork} (
				{percent(forks.losses_with_missed_fork, total)})
				{baseline && <BaselineNote part={baseline.losses_with_missed_fork} whole={base} />}.
			</p>
			<ShareTable
				title="Losses to forks"
				tone="lost"
				heading="Kind of fork missed"
				countHeading="Losses"
				rows={forkRows(forks.missed_kinds)}
				total={total}
				baseline={baseline && comparison(forkRows(baseline.missed_kinds), base)}
			/>
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

function pushCount(summary: PawnPushSummary, wing: string, timing: string): number {
	return summary.counts.find((row) => row.wing === wing && row.timing === timing)?.games ?? 0;
}

function PawnPushes({ pawnPushes, baseline }: { pawnPushes: PawnPushSummary; baseline: PawnPushSummary | null }) {
	const total = pawnPushes.analysed_games;
	if (total === 0) return null;
	const cell = (wing: string, timing: string) => {
		const count = pushCount(pawnPushes, wing, timing);
		return (
			<>
				{count} ({percent(count, total)})
				{baseline && (
					<div className="text-sm text-gray-600 dark:text-gray-400">
						baseline {percent(pushCount(baseline, wing, timing), baseline.analysed_games)}
					</div>
				)}
			</>
		);
	};
	return (
		<>
			<h2 className="mt-8 mb-2 text-lg font-bold">Pawn pushes</h2>
			<p>Games out of {total} analysed where a pawn push on a wing came too early or too late.</p>
			<table className="mt-4 w-full">
				<StickyHead title="Pawn pushes" tone="neutral">
					<th className="py-1 font-normal">Wing</th>
					<th className="py-1 text-right font-normal">Too early</th>
					<th className="py-1 text-right font-normal">Too late</th>
				</StickyHead>
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

function reasonRows(counts: ReasonCount[]): { name: string; count: number }[] {
	return counts.map((count) => ({ name: count.name, count: count.games }));
}

function ResultReasonsSection({
	title,
	tone,
	whose,
	reasons,
	baseline,
}: {
	title: string;
	tone: Tone;
	whose: string;
	reasons: ResultReasons;
	baseline: ResultReasons | null;
}) {
	if (reasons.games === 0) return null;
	return (
		<>
			<h2 className={`mt-8 mb-2 text-lg font-bold ${TONES[tone]}`}>{title}</h2>
			<p>
				The deciding error in each of {reasons.games} analysed games, and every error {whose} made in them.
			</p>
			<ShareTable
				title={title}
				tone={tone}
				heading="Deciding error"
				countHeading="Games"
				rows={reasonRows(reasons.deciding)}
				total={reasons.games}
				baseline={baseline && comparison(reasonRows(baseline.deciding), baseline.games)}
			/>
			<ShareTable
				title={title}
				tone={tone}
				heading="Errors in the game"
				countHeading="Games"
				rows={reasonRows(reasons.tags)}
				total={reasons.games}
				baseline={baseline && comparison(reasonRows(baseline.tags), baseline.games)}
			/>
			<p className="mt-3 text-sm text-gray-600 dark:text-gray-400">
				A game counts once under each kind of error in it, so these shares add up to more than 100%.
			</p>
		</>
	);
}

function BaselinePicker({
	baselines,
	band,
	onChange,
}: {
	baselines: BaselineStatistics[];
	band: number | null;
	onChange: (band: number | null) => void;
}) {
	if (baselines.length === 0) return null;
	return (
		<label className="mb-6 flex flex-col gap-1">
			<span className="text-sm text-gray-600 dark:text-gray-400">Compare with</span>
			<select
				className="min-h-11 rounded border bg-transparent px-2"
				value={band ?? ""}
				onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)}
			>
				<option value="">Nobody</option>
				{baselines.map((baseline) => (
					<option key={baseline.band} value={baseline.band}>
						Players rated {bandLabel(baseline.band)} ({baseline.games} rapid games)
					</option>
				))}
			</select>
		</label>
	);
}

export function Statistics({ player }: { player: string }) {
	const [forks, setForks] = useState<ForkSummary | null>(null);
	const [pawnPushes, setPawnPushes] = useState<PawnPushSummary | null>(null);
	const [reasons, setReasons] = useState<ReasonSummary | null>(null);
	const [baselines, setBaselines] = useState<BaselineStatistics[]>([]);
	const [band, setBand] = useState<number | null>(null);
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
		getReasonStatistics(player)
			.then(setReasons)
			.catch((err: Error) => setError(err.message));
	}, [player, runsFinished]);

	useEffect(() => {
		getBaselines()
			.then(setBaselines)
			.catch((err: Error) => setError(err.message));
	}, []);

	const baseline = baselines.find((candidate) => candidate.band === band) ?? null;

	return (
		<section className="mx-auto w-full max-w-[600px]">
			<EngineRun player={player} onFinished={() => setRunsFinished((count) => count + 1)} />
			<BaselinePicker baselines={baselines} band={band} onChange={setBand} />
			<h2 className={`mb-2 text-lg font-bold ${TONES.lost}`}>Losses to forks</h2>
			{error && <p className="text-red-600 dark:text-red-400">{error}</p>}
			{forks && <Forks player={player} forks={forks} baseline={baseline?.forks ?? null} />}
			{pawnPushes && <PawnPushes pawnPushes={pawnPushes} baseline={baseline?.pawn_pushes ?? null} />}
			{reasons && (
				<ResultReasonsSection
					title="Why games were lost"
					tone="lost"
					whose={player}
					reasons={reasons.losses}
					baseline={baseline?.reasons.losses ?? null}
				/>
			)}
			{reasons && (
				<ResultReasonsSection
					title="Why games were won"
					tone="won"
					whose="the opponent"
					reasons={reasons.wins}
					baseline={baseline?.reasons.wins ?? null}
				/>
			)}
		</section>
	);
}
