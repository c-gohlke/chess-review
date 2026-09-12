import { expect, test } from "@playwright/test";

const GAMES = [
	{ id: 1, white: "alice", black: "bob", result: "win", time_class: "blitz", played_at: "2024-01-01T00:00:00Z" },
	{ id: 2, white: "carol", black: "dave", result: "loss", time_class: "rapid", played_at: "2024-01-02T00:00:00Z" },
];

const GAME_DETAIL = { ...GAMES[0], pgn: "1. e4 e5 2. Nf3 Nc6" };

test("games list, selecting a game, and navigating moves", async ({ page }) => {
	await page.route("**/api/games", (route) => route.fulfill({ json: GAMES }));
	await page.route("**/api/games/1", (route) => route.fulfill({ json: GAME_DETAIL }));

	await page.goto("/");
	await page.getByRole("button", { name: "Games" }).click();

	await expect(page.getByText("alice vs bob")).toBeVisible();
	await expect(page.getByText(/win/)).toBeVisible();
	await expect(page.getByText("carol vs dave")).toBeVisible();
	await expect(page.getByText(/loss/)).toBeVisible();

	await page.getByText("alice vs bob").click();
	await expect(page.locator("[data-square]")).toHaveCount(64);

	await page.getByRole("button", { name: "Next" }).click();
	await expect(page.locator('[data-square="e4"] [data-piece]')).toHaveCount(1);
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCount(0);

	await page.getByRole("button", { name: "Next" }).click();
	await page.getByRole("button", { name: "Next" }).click();
	await page.getByRole("button", { name: "Next" }).click();
	await expect(page.locator('[data-square="c6"] [data-piece]')).toHaveCount(1);

	await page.getByRole("button", { name: "Prev" }).click();
	await expect(page.locator('[data-square="c6"] [data-piece]')).toHaveCount(0);

	await page.getByRole("button", { name: "Next" }).click();
	await expect(page.getByRole("button", { name: "Next" })).toBeDisabled();
});

test("importing games from chess.com", async ({ page }) => {
	await page.route("**/api/games", (route) => route.fulfill({ json: [] }));
	await page.route("**/api/import/chesscom/alice", (route) => route.fulfill({ json: { imported: 3 } }));

	await page.goto("/");
	await page.getByRole("button", { name: "Games" }).click();
	await page.getByPlaceholder("Chess.com username").fill("alice");
	await page.getByRole("button", { name: "Import" }).click();

	await expect(page.getByText("Imported 3 games")).toBeVisible();
});
