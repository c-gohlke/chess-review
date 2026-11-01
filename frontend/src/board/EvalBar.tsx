import type { Evaluation } from "../api/client";

export function formatEvaluation({ cp, mate }: Evaluation): string {
	if (mate === 0) return "Checkmate";
	if (mate !== null) return `${mate > 0 ? "" : "−"}M${Math.abs(mate)}`;
	const pawns = (cp ?? 0) / 100;
	if (pawns === 0) return "0.00";
	return `${pawns > 0 ? "+" : "−"}${Math.abs(pawns).toFixed(2)}`;
}

function whiteShare({ cp, mate }: Evaluation, whiteToMove: boolean): number {
	if (mate === 0) return whiteToMove ? 0 : 100;
	if (mate !== null) return mate > 0 ? 100 : 0;
	// Flattens large advantages: being 9 pawns up is not much better than being 6 up.
	return 50 + (Math.atan((cp ?? 0) / 300) / Math.PI) * 100;
}

export function EvalBar({ evaluation, whiteToMove }: { evaluation: Evaluation | null; whiteToMove: boolean }) {
	const height = `${evaluation ? whiteShare(evaluation, whiteToMove) : 50}%`;
	return (
		<div
			role="img"
			aria-label="White's share of the evaluation"
			className="flex w-4 shrink-0 flex-col justify-end overflow-hidden rounded bg-gray-800"
		>
			<div data-testid="eval-white" className="bg-gray-100 transition-[height]" style={{ height }} />
		</div>
	);
}
