import type { components } from "./schema";

export type GameSummary = components["schemas"]["GameSummary"];
export type GameDetail = components["schemas"]["GameDetail"];

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

export async function importChesscom(username: string): Promise<{ imported: number }> {
	const response = await checkOk(await fetch(`/api/import/chesscom/${username}`, { method: "POST" }));
	return response.json();
}
