import type { components } from "./schema";

export type GameSummary = components["schemas"]["GameSummary"];
export type GameDetail = components["schemas"]["GameDetail"];
export type OpeningStats = components["schemas"]["OpeningStats"];
export type OpeningSummary = components["schemas"]["OpeningSummary"];
export type TimeClass = components["schemas"]["TimeClass"];

async function checkOk(response: Response): Promise<Response> {
	if (!response.ok) throw new Error(`request failed with status ${response.status}`);
	return response;
}

export async function listGames(): Promise<GameSummary[]> {
	const response = await checkOk(await fetch("/api/games"));
	return response.json();
}

export async function getGame(id: number): Promise<GameDetail> {
	const response = await checkOk(await fetch(`/api/games/${id}`));
	return response.json();
}

export async function getOpenings(since: Date | null, timeClass: TimeClass | null): Promise<OpeningSummary> {
	const params = new URLSearchParams();
	if (since) params.set("since", since.toISOString());
	if (timeClass) params.set("time_class", timeClass);
	const response = await checkOk(await fetch(`/api/openings?${params}`));
	return response.json();
}

export async function importChesscom(username: string): Promise<{ imported: number }> {
	const response = await checkOk(await fetch(`/api/import/chesscom/${username}`, { method: "POST" }));
	return response.json();
}
