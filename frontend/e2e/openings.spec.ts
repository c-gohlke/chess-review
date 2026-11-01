import { expect, test } from "@playwright/test";

// "3 months ago" is computed in local time, so a daylight saving change would shift the expected instant.
test.use({ timezoneId: "UTC" });

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
