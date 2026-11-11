import { expect, type Page, test } from "@playwright/test";

const FORKS = {
	analysed_losses: 200,
	losses_with_fork: 30,
	decided_by_fork: 12,
	kinds: [
		{ name: "Knight fork", losses: 20 },
		{ name: "Pawn fork, royal (king and queen)", losses: 5 },
	],
	losses_with_missed_fork: 16,
	missed_kinds: [{ name: "Bishop fork", losses: 16 }],
};

const PAWN_PUSHES = {
	analysed_games: 400,
	counts: [
		{ wing: "queenside", timing: "early", games: 10 },
		{ wing: "queenside", timing: "late", games: 40 },
		{ wing: "kingside", timing: "early", games: 60 },
		{ wing: "kingside", timing: "late", games: 2 },
	],
};

const REASONS = {
	losses: {
		games: 200,
		deciding: [
			{ name: "Endgame error", games: 70 },
			{ name: "Hung a piece", games: 50 },
		],
		tags: [{ name: "Low on time", games: 90 }],
	},
	wins: { games: 160, deciding: [{ name: "Fork", games: 40 }], tags: [{ name: "Missed a fork", games: 8 }] },
};

const ANALYSIS = { games: 10, unanalysed: 0, phase: "idle", done: 0, total: 0, error: null, running_player: null };

const BASELINE = {
	band: 1600,
	games: 1000,
	forks: {
		analysed_losses: 400,
		losses_with_fork: 80,
		decided_by_fork: 20,
		kinds: [{ name: "Knight fork", losses: 60 }],
		losses_with_missed_fork: 40,
		missed_kinds: [{ name: "Bishop fork", losses: 40 }],
	},
	pawn_pushes: {
		analysed_games: 1000,
		counts: [
			{ wing: "queenside", timing: "early", games: 50 },
			{ wing: "queenside", timing: "late", games: 100 },
			{ wing: "kingside", timing: "early", games: 200 },
			{ wing: "kingside", timing: "late", games: 10 },
		],
	},
	reasons: {
		losses: { games: 400, deciding: [{ name: "Allowed a mate", games: 100 }], tags: [] },
		wins: { games: 500, deciding: [{ name: "Fork", games: 50 }], tags: [] },
	},
};

test.beforeEach(async ({ page }) => {
	await page.route("**/api/statistics/pawn-pushes?*", (route) => route.fulfill({ json: PAWN_PUSHES }));
	await page.route("**/api/statistics/reasons?*", (route) => route.fulfill({ json: REASONS }));
	await page.route("**/api/statistics/baselines", (route) => route.fulfill({ json: [BASELINE] }));
});

async function openStatistics(page: Page, forks: typeof FORKS) {
	await page.route("**/api/users", (route) => route.fulfill({ json: ["alice"] }));
	await page.route("**/api/statistics/forks?*", (route) => route.fulfill({ json: forks }));
	await page.route("**/api/analysis?*", (route) => route.fulfill({ json: ANALYSIS }));
	await page.goto("/");
	await page.getByRole("button", { name: "Statistics" }).click();
}

test("shows how often the player lost to each kind of fork", async ({ page }) => {
	await openStatistics(page, FORKS);

	await expect(page.getByText("A fork figured in 30 of 200 analysed losses (15.0%)")).toBeVisible();
	await expect(page.getByText("It was the deciding error in 12 (6.0%).")).toBeVisible();
	await expect(page.getByRole("row", { name: "Knight fork 20 10.0%" })).toBeVisible();
	await expect(page.getByRole("row", { name: "Pawn fork, royal (king and queen) 5 2.5%" })).toBeVisible();
	await expect(page.getByText("alice missed a fork of their own in 16 (8.0%).")).toBeVisible();
	await expect(page.getByRole("row", { name: "Bishop fork 16 8.0%" })).toBeVisible();
});

test("comparing with a baseline adds the baseline players' shares", async ({ page }) => {
	await openStatistics(page, FORKS);
	await expect(page.getByRole("columnheader", { name: "Baseline" })).toHaveCount(0);

	await page.getByLabel("Compare with").selectOption({ label: "Players rated 1600–1699 (1000 rapid games)" });

	await expect(page.getByText("A fork figured in 30 of 200 analysed losses (15.0%) · baseline 20.0%.")).toBeVisible();
	await expect(page.getByRole("row", { name: "Knight fork 20 10.0% 15.0%" })).toBeVisible();
	await expect(page.getByRole("row", { name: "Pawn fork, royal (king and queen) 5 2.5% 0.0%" })).toBeVisible();
	await expect(page.getByRole("row", { name: "Bishop fork 16 8.0% 10.0%" })).toBeVisible();
	await expect(
		page.getByRole("row", { name: "Queen side 10 (2.5%) baseline 5.0% 40 (10.0%) baseline 10.0%" }),
	).toBeVisible();
	// A reason only the baseline players had still gets a row.
	await expect(page.getByRole("row", { name: "Allowed a mate 0 0.0% 25.0%" })).toBeVisible();
	await expect(page.getByRole("row", { name: "Fork 40 25.0% 10.0%" })).toBeVisible();
});

test("shows why games were lost and won", async ({ page }) => {
	await openStatistics(page, FORKS);

	await expect(
		page.getByText("The deciding error in each of 200 analysed games, and every error alice made"),
	).toBeVisible();
	await expect(page.getByRole("row", { name: "Endgame error 70 35.0%" })).toBeVisible();
	await expect(page.getByRole("row", { name: "Hung a piece 50 25.0%" })).toBeVisible();
	await expect(page.getByRole("row", { name: "Low on time 90 45.0%" })).toBeVisible();
	await expect(
		page.getByText("The deciding error in each of 160 analysed games, and every error the opponent made"),
	).toBeVisible();
	await expect(page.getByRole("row", { name: "Fork 40 25.0%" })).toBeVisible();
	await expect(page.getByRole("row", { name: "Missed a fork 8 5.0%" })).toBeVisible();
});

test("shows how often wing pawn pushes came too early or too late", async ({ page }) => {
	await openStatistics(page, FORKS);

	await expect(page.getByText("Games out of 400 analysed")).toBeVisible();
	await expect(page.getByRole("row", { name: "Queen side 10 (2.5%) 40 (10.0%)" })).toBeVisible();
	await expect(page.getByRole("row", { name: "King side 60 (15.0%) 2 (0.5%)" })).toBeVisible();
});

test("explains when the player's games have not been analysed", async ({ page }) => {
	await openStatistics(page, {
		analysed_losses: 0,
		losses_with_fork: 0,
		decided_by_fork: 0,
		kinds: [],
		losses_with_missed_fork: 0,
		missed_kinds: [],
	});

	await expect(page.getByText("alice's games have not been analysed yet.")).toBeVisible();
});

test("a failed request is shown", async ({ page }) => {
	await page.route("**/api/users", (route) => route.fulfill({ json: ["alice"] }));
	await page.route("**/api/statistics/forks?*", (route) => route.fulfill({ status: 500 }));
	await page.route("**/api/analysis?*", (route) => route.fulfill({ json: ANALYSIS }));
	await page.goto("/");
	await page.getByRole("button", { name: "Statistics" }).click();

	await expect(page.getByText("request failed with status 500")).toBeVisible();
});

test("choosing another player in Settings shows their statistics", async ({ page }) => {
	await page.route("**/api/users", (route) => route.fulfill({ json: ["alice", "carol"] }));
	await page.route("**/api/analysis?*", (route) => route.fulfill({ json: ANALYSIS }));
	await page.route("**/api/statistics/forks?*", (route) => {
		const player = new URL(route.request().url()).searchParams.get("username");
		return route.fulfill({ json: player === "carol" ? { ...FORKS, losses_with_fork: 50 } : FORKS });
	});
	await page.goto("/");
	await page.getByRole("button", { name: "Statistics" }).click();
	await expect(page.getByText("A fork figured in 30 of 200 analysed losses (15.0%)")).toBeVisible();

	await page.getByRole("button", { name: "Settings" }).click();
	await page.getByLabel("Player").selectOption("carol");
	await page.getByRole("button", { name: "Statistics" }).click();

	await expect(page.getByText("A fork figured in 50 of 200 analysed losses (25.0%)")).toBeVisible();
});
