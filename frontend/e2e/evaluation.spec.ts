import { expect, type Page, test } from "@playwright/test";

const GAME = {
	id: 1,
	white: "alice",
	black: "bob",
	result: "loss",
	time_class: "blitz",
	played_at: "2024-01-01T00:00:00Z",
	pgn: "1. f3 e5 2. g4 Qh4#",
};

// Keyed by the moves played so far, which is the piece placement's only change in this game.
function evaluationFor(fen: string) {
	if (fen.includes("6Pq")) return { cp: null, mate: 0 };
	if (fen.includes("6P1")) return { cp: null, mate: -1 };
	if (fen.includes("4p3")) return { cp: -150, mate: null };
	if (fen.includes("5P2")) return { cp: -35, mate: null };
	return { cp: 20, mate: null };
}

async function openGame(page: Page) {
	await page.route("**/api/games", (route) => route.fulfill({ json: [GAME] }));
	await page.route("**/api/games/1", (route) => route.fulfill({ json: GAME }));
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
