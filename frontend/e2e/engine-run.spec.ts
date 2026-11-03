import { expect, type Page, test } from "@playwright/test";

const IDLE = { games: 10, unanalysed: 3, phase: "idle", done: 0, total: 0, error: null, running_player: null };

type State = { [key: string]: unknown };

// The first state is served until the run is requested, then each poll takes the next one.
async function openStatistics(page: Page, [before, ...after]: State[]) {
	let polls = 0;
	let requested = false;
	await page.route("**/api/users", (route) => route.fulfill({ json: ["alice"] }));
	await page.route("**/api/statistics/forks?*", (route) =>
		route.fulfill({ json: { analysed_losses: 7, losses_with_fork: 0, decided_by_fork: 0, kinds: [] } }),
	);
	await page.route("**/api/analysis?*", (route) => {
		requested ||= route.request().method() === "POST";
		if (!requested) return route.fulfill({ json: before });
		const state = after[Math.min(polls, after.length - 1)];
		polls += 1;
		return route.fulfill({ json: state });
	});
	await page.goto("/");
	await page.getByRole("button", { name: "Statistics" }).click();
}

test("offers to analyse the games the engine has not seen", async ({ page }) => {
	await openStatistics(page, [IDLE]);

	await expect(page.getByText("7 of 10 games analysed.")).toBeVisible();
	await expect(page.getByRole("button", { name: "Analyse 3 games (about 1 min)" })).toBeVisible();
});

test("shows no button when every game is analysed", async ({ page }) => {
	await openStatistics(page, [{ ...IDLE, unanalysed: 0 }]);

	await expect(page.getByText("10 of 10 games analysed.")).toBeVisible();
	await expect(page.getByRole("button", { name: /^Analyse/ })).toHaveCount(0);
});

test("a requested run shows its progress until it finishes", async ({ page }) => {
	const running = { ...IDLE, phase: "analysing", done: 40, total: 120, running_player: "alice" };
	await openStatistics(page, [IDLE, running, running, { ...IDLE, unanalysed: 0 }]);

	await page.getByRole("button", { name: /^Analyse/ }).click();

	await expect(page.getByText("Running the engine: 40 of 120 positions")).toBeVisible();
	await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "40");
	await expect(page.getByRole("button", { name: /^Analyse/ })).toHaveCount(0);
	await expect(page.getByText("10 of 10 games analysed.")).toBeVisible({ timeout: 10000 });
});

test("a failed run is shown and can be tried again", async ({ page }) => {
	await openStatistics(page, [{ ...IDLE, phase: "failed", error: "stockfish not found" }]);

	await expect(page.getByText("The last run failed: stockfish not found")).toBeVisible();
	await expect(page.getByRole("button", { name: /^Analyse/ })).toBeVisible();
});

test("says so when the engine is busy with another player", async ({ page }) => {
	await openStatistics(page, [{ ...IDLE, running_player: "bob" }]);

	await expect(page.getByText("The engine is busy with bob.")).toBeVisible();
	await expect(page.getByRole("button", { name: /^Analyse/ })).toHaveCount(0);
});
