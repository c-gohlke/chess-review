import { expect, type Page, test } from "@playwright/test";

// One screenshot per view, so an unintended layout or styling change fails a test.
// Every request is answered here, so the pictures never depend on a real server.

test.use({ timezoneId: "UTC" });

const GAMES = [
	{
		id: 1,
		white: "alice",
		black: "bob",
		result: "loss",
		time_class: "blitz",
		played_at: "2026-06-03T18:00:00Z",
		opening: "Barnes Opening",
		rating_change: -8,
	},
	{
		id: 2,
		white: "carol",
		black: "alice",
		result: "win",
		time_class: "rapid",
		played_at: "2026-06-02T18:00:00Z",
		opening: "Scandinavian Defense",
		rating_change: 9,
	},
	{
		id: 3,
		white: "alice",
		black: "dave",
		result: "draw",
		time_class: "bullet",
		played_at: "2026-06-01T18:00:00Z",
		opening: "London System",
		rating_change: null,
	},
];

const GAME_DETAIL = {
	...GAMES[0],
	pgn: "1. f3 e5 2. g4 Qh4#",
	colour: "white",
	analysis: {
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
	},
};

const stats = { draws: 0, eval_mean: null, eval_median: null, variations: [] };

const OPENINGS = {
	white: [
		{
			...stats,
			name: "London System",
			games: 12,
			wins: 8,
			losses: 3,
			draws: 1,
			net: 2.5,
			eval_mean: 0.42,
			eval_median: -0.2,
			variations: [{ ...stats, name: "Accelerated", games: 12, wins: 8, losses: 3, draws: 1, net: 2.5 }],
		},
		{ ...stats, name: "Barnes Opening", games: 5, wins: 1, losses: 4, net: -1.5 },
	],
	black: [
		{ ...stats, name: "Scandinavian Defense", games: 9, wins: 3, losses: 6, net: -1 },
		{ ...stats, name: "French Defense", games: 4, wins: 3, losses: 1, net: 1 },
	],
};

const FORKS = {
	analysed_losses: 200,
	losses_with_fork: 30,
	decided_by_fork: 12,
	kinds: [
		{ name: "Knight fork", losses: 20 },
		{ name: "Pawn fork, royal (king and queen)", losses: 5 },
		{ name: "Queen fork", losses: 5 },
	],
};

const PAWN_PUSHES = {
	analysed_games: 116,
	counts: [
		{ wing: "queenside", timing: "early", games: 9 },
		{ wing: "queenside", timing: "late", games: 21 },
		{ wing: "kingside", timing: "early", games: 34 },
		{ wing: "kingside", timing: "late", games: 3 },
	],
};

const REASONS = {
	losses: {
		games: 58,
		deciding: [
			{ name: "Endgame error", games: 14 },
			{ name: "Hung a piece", games: 12 },
			{ name: "Lost on time in an OK position", games: 9 },
		],
		tags: [
			{ name: "No immediate tactic", games: 35 },
			{ name: "Hung a piece", games: 22 },
			{ name: "Missed a fork", games: 4 },
		],
	},
	wins: {
		games: 55,
		deciding: [
			{ name: "Hung a piece", games: 15 },
			{ name: "Fork", games: 6 },
		],
		tags: [
			{ name: "Hung a piece", games: 24 },
			{ name: "Allowed a fork", games: 9 },
		],
	},
};

const ANALYSIS = { games: 120, unanalysed: 4, phase: "idle", done: 0, total: 0, error: null, running_player: null };

test.beforeEach(async ({ page }) => {
	await page.clock.setFixedTime(new Date("2026-06-15T12:00:00Z"));
	await page.route("**/api/users", (route) => route.fulfill({ json: ["alice", "carol"] }));
	await page.route("**/api/import/chesscom/*", (route) => route.fulfill({ json: { imported: 0 } }));
	await page.route("**/api/games?*", (route) => route.fulfill({ json: GAMES }));
	await page.route("**/api/games/1", (route) => route.fulfill({ json: GAME_DETAIL }));
	await page.route("**/api/games/*/analysis", (route) => route.fulfill({ json: GAME_DETAIL }));
	await page.route("**/api/evaluation?*", (route) => route.fulfill({ json: { cp: -150, mate: null } }));
	await page.route("**/api/openings?*", (route) => route.fulfill({ json: OPENINGS }));
	await page.route("**/api/statistics/forks?*", (route) => route.fulfill({ json: FORKS }));
	await page.route("**/api/statistics/pawn-pushes?*", (route) => route.fulfill({ json: PAWN_PUSHES }));
	await page.route("**/api/statistics/reasons?*", (route) => route.fulfill({ json: REASONS }));
	await page.route("**/api/analysis?*", (route) => route.fulfill({ json: ANALYSIS }));
	await page.goto("/");
});

async function snapshot(page: Page, name: string) {
	// A hovered piece is enlarged, so the pointer must not rest on the board.
	await page.mouse.move(0, 0);
	await expect(page.locator("main")).toHaveScreenshot(name);
}

test("analyze view", async ({ page }) => {
	await expect(page.locator("[data-square]")).toHaveCount(64);

	await snapshot(page, "analyze.png");
});

test("games view", async ({ page }) => {
	await page.getByRole("button", { name: "Games" }).click();
	await expect(page.getByText("alice vs dave")).toBeVisible();

	await snapshot(page, "games.png");
});

test("game view", async ({ page }) => {
	await page.getByRole("button", { name: "Games" }).click();
	await page.getByText("alice vs bob").click();
	await page.getByRole("button", { name: "g4??" }).click();
	await expect(page.getByText("3 / 4")).toBeVisible();
	// Waits for the bar to settle on the mocked evaluation of -150, a 36% share for white.
	await expect(page.getByTestId("eval-white")).toHaveAttribute("style", /height: 3\d/);

	await snapshot(page, "game.png");
});

test("openings view", async ({ page }) => {
	await page.getByRole("button", { name: "Openings" }).click();
	await expect(page.getByText("London System")).toBeVisible();

	await snapshot(page, "openings.png");
});

test("statistics view", async ({ page }) => {
	await page.getByRole("button", { name: "Statistics" }).click();
	await expect(page.getByRole("button", { name: /^Analyse 4 games/ })).toBeVisible();
	await expect(page.getByRole("row", { name: /Queen fork/ })).toBeVisible();
	await expect(page.getByRole("row", { name: /King side/ })).toBeVisible();
	await expect(page.getByRole("row", { name: /Allowed a fork/ })).toBeVisible();

	await snapshot(page, "statistics.png");
});

test("settings view", async ({ page }) => {
	await page.getByRole("button", { name: "Settings" }).click();
	await expect(page.getByLabel("Player")).toHaveValue("alice");

	await snapshot(page, "settings.png");
});

test.describe("on a large screen", () => {
	test.use({ viewport: { width: 2560, height: 1440 } });

	test("the analyze board fills the window's height", async ({ page }, testInfo) => {
		test.skip(testInfo.project.name !== "desktop", "phones have no large screen");
		await expect(page.locator("[data-square]")).toHaveCount(64);

		await snapshot(page, "analyze-large.png");
	});

	test("the game board fills the window's height", async ({ page }, testInfo) => {
		test.skip(testInfo.project.name !== "desktop", "phones have no large screen");
		await page.getByRole("button", { name: "Games" }).click();
		await page.getByText("alice vs bob").click();
		await expect(page.getByText("Decided by:")).toBeVisible();

		await snapshot(page, "game-large.png");
	});
});
