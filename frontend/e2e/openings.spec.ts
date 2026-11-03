import { expect, type Page, test } from "@playwright/test";

// "3 months ago" is computed in local time, so a daylight saving change would shift the expected instant.
test.use({ timezoneId: "UTC" });

test.beforeEach(({ page }) => page.route("**/api/users", (route) => route.fulfill({ json: ["alice"] })));

const stats = { draws: 0, variations: [] };

const OPENINGS = {
	white: [
		{
			...stats,
			name: "London System",
			games: 3,
			wins: 3,
			losses: 0,
			net: 1.5,
			variations: [{ ...stats, name: "Accelerated", games: 3, wins: 3, losses: 0, net: 1.5 }],
		},
	],
	black: [
		{ ...stats, name: "Scandinavian Defense", games: 4, wins: 1, losses: 3, net: -1 },
		{ ...stats, name: "French Defense", games: 1, wins: 1, losses: 0, net: 0.5 },
	],
};

test("filters default to the last 3 months and refetch when changed", async ({ page }) => {
	await page.clock.setFixedTime(new Date("2026-06-15T12:00:00Z"));
	const requests: URLSearchParams[] = [];
	await page.route("**/api/openings?*", (route) => {
		const params = new URL(route.request().url()).searchParams;
		requests.push(params);
		const json = params.has("time_class") ? { white: [], black: [] } : OPENINGS;
		return route.fulfill({ json });
	});

	await page.goto("/");
	await page.getByRole("button", { name: "Openings" }).click();

	await expect(page.getByRole("button", { name: /London System/ })).toBeVisible();
	expect(requests.at(-1)?.get("since")).toBe("2026-03-15T12:00:00.000Z");
	expect(requests.at(-1)?.has("time_class")).toBe(false);

	await page.getByLabel("Period").selectOption({ label: "All time" });
	await expect.poll(() => requests.at(-1)?.has("since")).toBe(false);

	await page.getByLabel("Time control").selectOption({ label: "Blitz" });
	await expect(page.getByText("No games for these filters")).toBeVisible();
	expect(requests.at(-1)?.get("time_class")).toBe("blitz");
	await expect(page.getByLabel("Period")).toBeVisible();
});

test("openings split by colour with drill-down into variations", async ({ page }) => {
	await page.route("**/api/openings?*", (route) => route.fulfill({ json: OPENINGS }));

	await page.goto("/");
	await page.getByRole("button", { name: "Openings" }).click();

	await expect(page.getByRole("button", { name: "White +1.5" })).toBeVisible();
	await expect(page.getByRole("button", { name: "Black −0.5" })).toBeVisible();

	await expect(page.getByText("Accelerated")).toHaveCount(0);
	await page.getByRole("button", { name: /London System/ }).click();
	await expect(page.getByText("Accelerated")).toBeVisible();

	await page.getByRole("button", { name: /Black/ }).click();
	await expect(page.getByText("Scandinavian Defense")).toBeVisible();
	await expect(page.getByText("25%")).toBeVisible();
	await expect(page.getByText("4 games · −1.0 · 1W 0D 3L")).toBeVisible();
	await expect(page.getByText("1 played once: +0.5")).toBeVisible();
	await expect(page.getByText("London System")).toHaveCount(0);
});

const GAME = {
	id: 7,
	white: "alice",
	black: "bob",
	result: "win",
	time_class: "blitz",
	played_at: "2024-01-01T00:00:00Z",
	opening: "London System",
	rating_change: 8,
};

async function openVariation(page: Page) {
	await page.route("**/api/openings?*", (route) => route.fulfill({ json: OPENINGS }));
	await page.goto("/");
	await page.getByRole("button", { name: "Openings" }).click();
	await page.getByRole("button", { name: /London System/ }).click();
	await page.getByRole("button", { name: /Accelerated/ }).click();
}

test("a variation opens its games, and they follow the filters", async ({ page }) => {
	const requests: URLSearchParams[] = [];
	await page.route("**/api/openings/games?*", (route) => {
		const params = new URL(route.request().url()).searchParams;
		requests.push(params);
		return route.fulfill({ json: params.get("time_class") === "blitz" ? [] : [GAME] });
	});

	await openVariation(page);

	await expect(page.getByRole("button", { name: "alice vs bob" })).toBeVisible();
	const first = requests.at(-1);
	expect(first?.get("family")).toBe("London System");
	expect(first?.get("variation")).toBe("Accelerated");
	expect(first?.get("colour")).toBe("white");
	expect(first?.has("since")).toBe(true);

	await page.getByLabel("Time control").selectOption({ label: "Blitz" });
	await expect(page.getByRole("button", { name: "alice vs bob" })).toHaveCount(0);
});

test("a game opens its replay, and Back returns to the expanded opening", async ({ page }) => {
	await page.route("**/api/openings/games?*", (route) => route.fulfill({ json: [GAME] }));
	await page.route("**/api/games/7", (route) => route.fulfill({ json: { ...GAME, pgn: "1. e4 e5", colour: "white" } }));
	await page.route("**/api/evaluation?*", (route) => route.fulfill({ json: { cp: 20, mate: null } }));

	await openVariation(page);
	await page.getByRole("button", { name: "alice vs bob" }).click();

	await expect(page.locator("[data-square]")).toHaveCount(64);
	await expect(page.getByLabel("Period")).toBeHidden();

	await page.getByRole("button", { name: "Back" }).click();

	await expect(page.getByRole("button", { name: "alice vs bob" })).toBeVisible();
	await expect(page.locator("[data-square]")).toHaveCount(0);
});

test("a failed games request shows an error under the variation", async ({ page }) => {
	await page.route("**/api/openings/games?*", (route) => route.fulfill({ status: 500 }));

	await openVariation(page);

	await expect(page.getByText("request failed with status 500")).toBeVisible();
});

test("a failed openings request is shown", async ({ page }) => {
	await page.route("**/api/openings?*", (route) => route.fulfill({ status: 500 }));
	await page.goto("/");

	await page.getByRole("button", { name: "Openings" }).click();

	await expect(page.getByText("request failed with status 500")).toBeVisible();
});
