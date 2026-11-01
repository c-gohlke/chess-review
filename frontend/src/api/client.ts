import type { components } from "./schema";

export type GameListItem = components["schemas"]["GameListItem"];
export type GameDetail = components["schemas"]["GameDetail"];
export type Evaluation = components["schemas"]["Evaluation"];
export type OpeningStats = components["schemas"]["OpeningStats"];
export type OpeningSummary = components["schemas"]["OpeningSummary"];
export type TimeClass = components["schemas"]["TimeClass"];
export type Colour = "white" | "black";

async function checkOk(response: Response): Promise<Response> {
	if (!response.ok) throw new Error(`request failed with status ${response.status}`);
	return response;
}

export async function listGames(limit: number, offset: number): Promise<GameListItem[]> {
	const response = await checkOk(await fetch(`/api/games?limit=${limit}&offset=${offset}`));
	return response.json();
}

export async function getGame(id: number): Promise<GameDetail> {
	const response = await checkOk(await fetch(`/api/games/${id}`));
	return response.json();
}

export async function getEvaluation(fen: string): Promise<Evaluation> {
	const response = await checkOk(await fetch(`/api/evaluation?${new URLSearchParams({ fen })}`));
	return response.json();
}

function filterParams(since: Date | null, timeClass: TimeClass | null): URLSearchParams {
	const params = new URLSearchParams();
	if (since) params.set("since", since.toISOString());
	if (timeClass) params.set("time_class", timeClass);
	return params;
}

export async function getOpenings(since: Date | null, timeClass: TimeClass | null): Promise<OpeningSummary> {
	const response = await checkOk(await fetch(`/api/openings?${filterParams(since, timeClass)}`));
	return response.json();
}

export async function getOpeningGames(
	family: string,
	variation: string,
	colour: Colour,
	since: Date | null,
	timeClass: TimeClass | null,
): Promise<GameListItem[]> {
	const params = filterParams(since, timeClass);
	params.set("family", family);
	params.set("variation", variation);
	params.set("colour", colour);
	const response = await checkOk(await fetch(`/api/openings/games?${params}`));
	return response.json();
}

export async function importChesscom(username: string): Promise<{ imported: number }> {
	const response = await checkOk(await fetch(`/api/import/chesscom/${username}`, { method: "POST" }));
	return response.json();
}
