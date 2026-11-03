import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
	await page.route("**/api/users", (route) => route.fulfill({ json: ["alice"] }));
	await page.route("**/api/import/chesscom/*", (route) => route.fulfill({ json: { imported: 0 } }));
});

const GAMES = [
	{
		id: 1,
		white: "alice",
		black: "bob",
		result: "win",
		time_class: "blitz",
		played_at: "2024-01-01T00:00:00Z",
		opening: "French Defense",
		rating_change: 8,
	},
	{
		id: 2,
		white: "carol",
		black: "dave",
		result: "loss",
		time_class: "rapid",
		played_at: "2024-01-02T00:00:00Z",
		opening: "Scandinavian Defense",
		rating_change: -12,
	},
	{
		id: 3,
		white: "erin",
		black: "frank",
		result: "draw",
		time_class: "rapid",
		played_at: "2024-01-03T00:00:00Z",
		opening: "London System",
		rating_change: null,
	},
];

const GAME_DETAIL = { ...GAMES[0], pgn: "1. e4 e5 2. Nf3 Nc6", colour: "white" };

test("games list, selecting a game, and navigating moves", async ({ page }) => {
	await page.route("**/api/games?*", (route) => route.fulfill({ json: GAMES }));
	await page.route("**/api/games/1", (route) => route.fulfill({ json: GAME_DETAIL }));
	await page.route("**/api/evaluation?*", (route) => route.fulfill({ json: { cp: 20, mate: null } }));

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

test("navigating moves with the left and right arrow keys stops at both ends", async ({ page }) => {
	await page.route("**/api/games?*", (route) => route.fulfill({ json: GAMES }));
	await page.route("**/api/games/1", (route) => route.fulfill({ json: GAME_DETAIL }));
	await page.route("**/api/evaluation?*", (route) => route.fulfill({ json: { cp: 20, mate: null } }));

	await page.goto("/");
	await page.getByRole("button", { name: "Games" }).click();
	await page.getByText("alice vs bob").click();
	await expect(page.getByText("0 / 4")).toBeVisible();

	await page.keyboard.press("ArrowLeft");
	await expect(page.getByText("0 / 4")).toBeVisible();

	await page.keyboard.press("ArrowRight");
	await expect(page.getByText("1 / 4")).toBeVisible();
	await expect(page.locator('[data-square="e4"] [data-piece]')).toHaveCount(1);

	await page.keyboard.press("ArrowLeft");
	await expect(page.getByText("0 / 4")).toBeVisible();
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCount(1);

	for (let press = 0; press < 5; press++) await page.keyboard.press("ArrowRight");
	await expect(page.getByText("4 / 4")).toBeVisible();
});

for (const [colour, top, bottom] of [
	["white", "bob", "alice"],
	["black", "alice", "bob"],
]) {
	test(`playing ${colour}, the opponent's name is above the board and the player's below`, async ({ page }) => {
		await page.route("**/api/games?*", (route) => route.fulfill({ json: GAMES }));
		await page.route("**/api/games/1", (route) => route.fulfill({ json: { ...GAME_DETAIL, colour } }));
		await page.route("**/api/evaluation?*", (route) => route.fulfill({ json: { cp: 20, mate: null } }));

		await page.goto("/");
		await page.getByRole("button", { name: "Games" }).click();
		await page.getByText("alice vs bob").click();

		await expect(page.getByTestId("top-player")).toHaveText(top);
		await expect(page.getByTestId("bottom-player")).toHaveText(bottom);
	});
}

test("rows are coloured by result and show the opening and rating change", async ({ page }) => {
	await page.route("**/api/games?*", (route) => route.fulfill({ json: GAMES }));

	await page.goto("/");
	await page.getByRole("button", { name: "Games" }).click();

	const row = (name: string) => page.getByRole("button", { name });
	await expect(row("alice vs bob")).toHaveClass(/bg-green-100/);
	await expect(row("alice vs bob")).toContainText("French Defense");
	await expect(row("alice vs bob")).toContainText("+8");
	await expect(row("carol vs dave")).toHaveClass(/bg-red-100/);
	await expect(row("carol vs dave")).toContainText("Scandinavian Defense");
	await expect(row("carol vs dave")).toContainText("−12");
	await expect(row("erin vs frank")).not.toHaveClass(/bg-(green|red)-100/);
});

test("the empty message waits until games have loaded", async ({ page }) => {
	let respond = () => {};
	const released = new Promise<void>((resolve) => {
		respond = resolve;
	});
	await page.route("**/api/games?*", async (route) => {
		await released;
		await route.fulfill({ json: [] });
	});

	await page.goto("/");
	await page.getByRole("button", { name: "Games" }).click();

	await expect(page.getByPlaceholder("Chess.com username")).toBeVisible();
	await expect(page.getByText("No games yet")).toHaveCount(0);

	respond();
	await expect(page.getByText("No games yet")).toBeVisible();
});

test("games load one page at a time", async ({ page }) => {
	const total = 75;
	const allGames = Array.from({ length: total }, (_, index) => ({
		...GAMES[0],
		id: index + 1,
		white: `player${index + 1}`,
	}));
	await page.route("**/api/games?*", (route) => {
		const params = new URL(route.request().url()).searchParams;
		const offset = Number(params.get("offset"));
		return route.fulfill({ json: allGames.slice(offset, offset + Number(params.get("limit"))) });
	});

	await page.goto("/");
	await page.getByRole("button", { name: "Games" }).click();

	await expect(page.getByText(/ vs bob/)).toHaveCount(50);
	await expect(page.getByText("player51 vs bob")).toHaveCount(0);

	await page.getByRole("button", { name: "Show more" }).click();

	await expect(page.getByText(/ vs bob/)).toHaveCount(total);
	await expect(page.getByRole("button", { name: "Show more" })).toHaveCount(0);
});

test("games and openings show one player at a time, and the choice is remembered", async ({ page }) => {
	await page.route("**/api/users", (route) => route.fulfill({ json: ["alice", "carol"] }));
	const players: (string | null)[] = [];
	await page.route("**/api/games?*", (route) => {
		const player = new URL(route.request().url()).searchParams.get("username");
		players.push(player);
		return route.fulfill({ json: GAMES.filter((game) => game.white === player) });
	});
	await page.route("**/api/openings?*", (route) => {
		const player = new URL(route.request().url()).searchParams.get("username");
		players.push(player);
		return route.fulfill({ json: { white: [], black: [] } });
	});

	await page.goto("/");
	await page.getByRole("button", { name: "Games" }).click();
	await expect(page.getByText("alice vs bob")).toBeVisible();
	await expect(page.getByText("carol vs dave")).toHaveCount(0);

	await expect(page.getByLabel("Player")).toHaveCount(0);
	await page.getByRole("button", { name: "Settings" }).click();
	await page.getByLabel("Player").selectOption("carol");
	await page.getByRole("button", { name: "Games" }).click();
	await expect(page.getByText("carol vs dave")).toBeVisible();
	await expect(page.getByText("alice vs bob")).toHaveCount(0);

	await page.getByRole("button", { name: "Openings" }).click();
	await expect(page.getByText("No games for these filters")).toBeVisible();
	expect(players.at(-1)).toBe("carol");

	await page.reload();
	await page.getByRole("button", { name: "Games" }).click();
	await expect(page.getByText("carol vs dave")).toBeVisible();
});

test("settings point to the Games tab when there are no players", async ({ page }) => {
	await page.route("**/api/users", (route) => route.fulfill({ json: [] }));

	await page.goto("/");
	await page.getByRole("button", { name: "Settings" }).click();

	await expect(page.getByText("No players yet. Import games from the Games tab.")).toBeVisible();
});

test("importing a new player switches to them", async ({ page }) => {
	let users = ["alice"];
	await page.route("**/api/users", (route) => route.fulfill({ json: users }));
	await page.route("**/api/import/chesscom/Carol", (route) => {
		users = ["alice", "carol"];
		return route.fulfill({ json: { imported: 1 } });
	});
	await page.route("**/api/games?*", (route) => {
		const player = new URL(route.request().url()).searchParams.get("username");
		return route.fulfill({ json: GAMES.filter((game) => game.white === player) });
	});

	await page.goto("/");
	await page.getByRole("button", { name: "Games" }).click();
	await page.getByPlaceholder("Chess.com username").fill("Carol");
	await page.getByRole("button", { name: "Import" }).click();

	await expect(page.getByText("carol vs dave")).toBeVisible();
	await page.getByRole("button", { name: "Settings" }).click();
	await expect(page.getByLabel("Player")).toHaveValue("carol");
});

test("importing games from chess.com", async ({ page }) => {
	await page.route("**/api/games?*", (route) => route.fulfill({ json: [] }));
	await page.route("**/api/import/chesscom/alice", (route) => route.fulfill({ json: { imported: 3 } }));

	await page.goto("/");
	await page.getByRole("button", { name: "Games" }).click();
	await page.getByPlaceholder("Chess.com username").fill("alice");
	await page.getByRole("button", { name: "Import" }).click();

	await expect(page.getByText("Imported 3 games")).toBeVisible();
});

test("opening the Games tab fetches new games from chess.com", async ({ page }) => {
	let imported = false;
	await page.route("**/api/import/chesscom/alice", (route) => {
		imported = true;
		return route.fulfill({ json: { imported: 1 } });
	});
	await page.route("**/api/games?*", (route) => route.fulfill({ json: imported ? GAMES : GAMES.slice(1) }));
	await page.goto("/");

	await page.getByRole("button", { name: "Games", exact: true }).click();

	await expect(page.getByText("1 new game")).toBeVisible();
	await expect(page.getByRole("listitem")).toHaveCount(3);
});

test("a failed check leaves the stored games on show", async ({ page }) => {
	await page.route("**/api/import/chesscom/alice", (route) => route.fulfill({ status: 502 }));
	await page.route("**/api/games?*", (route) => route.fulfill({ json: GAMES }));
	await page.goto("/");

	await page.getByRole("button", { name: "Games", exact: true }).click();

	await expect(page.getByText(/^Could not check chess.com/)).toBeVisible();
	await expect(page.getByRole("listitem")).toHaveCount(3);
});

test("a failed games request is shown", async ({ page }) => {
	await page.route("**/api/games?*", (route) => route.fulfill({ status: 500 }));
	await page.goto("/");

	await page.getByRole("button", { name: "Games" }).click();

	await expect(page.getByText("request failed with status 500")).toBeVisible();
	await expect(page.getByText("No games yet")).toHaveCount(0);
});

test("a game that fails to load says so, and Back returns to the list", async ({ page }) => {
	await page.route("**/api/games?*", (route) => route.fulfill({ json: GAMES }));
	await page.route("**/api/games/1", (route) => route.fulfill({ status: 404 }));
	await page.goto("/");
	await page.getByRole("button", { name: "Games" }).click();

	await page.getByText("alice vs bob").click();
	await expect(page.getByText("request failed with status 404")).toBeVisible();
	await expect(page.locator("[data-square]")).toHaveCount(0);

	await page.getByRole("button", { name: "Back" }).click();
	await expect(page.getByText("alice vs bob")).toBeVisible();
});
