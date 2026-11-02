import { expect, type Locator, type Page, test } from "@playwright/test";

test.beforeEach(({ page }) => page.route("**/api/users", (route) => route.fulfill({ json: ["alice"] })));

const GAME = {
	id: 1,
	white: "alice",
	black: "bob",
	result: "loss",
	time_class: "blitz",
	played_at: "2024-01-01T00:00:00Z",
	opening: "Barnes Opening",
	rating_change: -8,
	pgn: "1. f3 e5 2. g4 Qh4#",
	colour: "white",
};

// Keyed by the moves played so far, which is the piece placement's only change in this game.
function evaluationFor(fen: string) {
	if (fen.includes("6Pq")) return { cp: null, mate: 0 };
	if (fen.includes("6P1")) return { cp: null, mate: -1 };
	if (fen.includes("4p3")) return { cp: -150, mate: null };
	if (fen.includes("5P2")) return { cp: -35, mate: null };
	return { cp: 20, mate: null };
}

async function openGame(page: Page, game = GAME) {
	await page.route("**/api/games?*", (route) => route.fulfill({ json: [game] }));
	await page.route("**/api/games/1", (route) => route.fulfill({ json: game }));
	await page.route("**/api/evaluation?*", (route) => {
		const fen = new URL(route.request().url()).searchParams.get("fen") ?? "";
		return route.fulfill({ json: evaluationFor(fen) });
	});
	await page.goto("/");
	await page.getByRole("button", { name: "Games" }).click();
	await page.getByText("alice vs bob").click();
}

async function whiteShare(page: Page): Promise<number> {
	const bar = page.getByTestId("eval-white");
	return bar.evaluate((element) => Number.parseFloat(element.style.height));
}

async function top(locator: Locator): Promise<number> {
	await expect(locator).toBeVisible();
	const box = await locator.boundingBox();
	if (!box) throw new Error("element has no box");
	return box.y;
}

test("a game played as white has white at the bottom", async ({ page }) => {
	await openGame(page);

	const rankOne = await top(page.locator('[data-square="e1"]'));
	expect(rankOne).toBeGreaterThan(await top(page.locator('[data-square="e8"]')));
	const whiteShareTop = await top(page.getByTestId("eval-white"));
	expect(whiteShareTop).toBeGreaterThan(await top(page.getByRole("img", { name: /evaluation/ })));
});

test("a game played as black has black at the bottom", async ({ page }) => {
	await openGame(page, { ...GAME, colour: "black" });

	const rankOne = await top(page.locator('[data-square="e1"]'));
	expect(rankOne).toBeLessThan(await top(page.locator('[data-square="e8"]')));
	const whiteShareTop = await top(page.getByTestId("eval-white"));
	expect(whiteShareTop).toBe(await top(page.getByRole("img", { name: /evaluation/ })));
});

const ANALYSIS = {
	decided_by: "Allowed a mate",
	moments: [
		{
			ply: 2,
			move_number: 2,
			player: "alice",
			is_decisive: true,
			win_lost: 59,
			labels: ["Allowed mate in 1", "Low on time"],
		},
		{ ply: 3, move_number: 2, player: "bob", is_decisive: false, win_lost: 20, labels: ["Hung a piece"] },
	],
};

test("the game's statistics link to their moves", async ({ page }) => {
	await openGame(page, { ...GAME, analysis: ANALYSIS } as typeof GAME);

	await expect(page.getByText("Decided by:")).toContainText("Allowed a mate");
	await expect(
		page.getByText("Deciding move by alice. Allowed mate in 1, Low on time. Gave away 59 points of win chance."),
	).toBeVisible();
	await expect(page.getByRole("button", { name: "f3", exact: true })).toBeVisible();
	await page.getByRole("button", { name: "g4??" }).click();
	await expect(page.getByText("3 / 4")).toBeVisible();

	await page.getByRole("button", { name: "Qh4#?" }).click();
	await expect(page.getByText("4 / 4")).toBeVisible();
});

test("the statistics sit beside the board on a wide screen", async ({ page }, testInfo) => {
	test.skip(testInfo.project.name !== "desktop", "phones stack them below the board");
	await openGame(page, { ...GAME, analysis: ANALYSIS } as typeof GAME);

	const board = await page.locator('[data-square="h1"]').boundingBox();
	const panel = await page.getByRole("heading", { name: "Game statistics" }).boundingBox();
	expect(panel?.x).toBeGreaterThan((board?.x ?? 0) + (board?.width ?? 0));
});

test("an unanalysed game says so", async ({ page }) => {
	await openGame(page);

	await expect(page.getByText("This game has not been analysed yet.")).toBeVisible();
	await page.getByRole("button", { name: "g4" }).click();
	await expect(page.getByText("3 / 4")).toBeVisible();
});

test("the evaluation follows the replayed position", async ({ page }) => {
	await openGame(page);
	const next = page.getByRole("button", { name: "Next" });

	await expect(page.getByText("+0.20")).toBeVisible();
	expect(await whiteShare(page)).toBeGreaterThan(50);

	await next.click();
	await expect(page.getByText("−0.35")).toBeVisible();
	expect(await whiteShare(page)).toBeLessThan(50);

	await next.click();
	await next.click();
	await expect(page.getByText("−M1")).toBeVisible();
	expect(await whiteShare(page)).toBe(0);
	await expect(next).toBeEnabled();
});

test("checkmate fills the bar for the side that delivered it", async ({ page }) => {
	await openGame(page);
	const next = page.getByRole("button", { name: "Next" });
	for (let move = 0; move < 4; move += 1) await next.click();

	await expect(page.getByText("Checkmate")).toBeVisible();
	expect(await whiteShare(page)).toBe(0);
});

test("a failed evaluation is shown and the replay keeps working", async ({ page }) => {
	await openGame(page);
	await expect(page.getByText("+0.20")).toBeVisible();
	await page.route("**/api/evaluation?*", (route) => route.fulfill({ status: 500 }));

	await page.getByRole("button", { name: "Next" }).click();

	await expect(page.getByText("request failed with status 500")).toBeVisible();
	await expect(page.getByText("1 / 4")).toBeVisible();
});
