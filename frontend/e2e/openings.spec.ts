import { expect, test } from "@playwright/test";

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

test("openings split by colour with drill-down into variations", async ({ page }) => {
	await page.route("**/api/openings", (route) => route.fulfill({ json: OPENINGS }));

	await page.goto("/");
	await page.getByRole("button", { name: "Openings" }).click();

	await expect(page.getByRole("button", { name: "White +1.5" })).toBeVisible();
	await expect(page.getByRole("button", { name: "Black −0.5" })).toBeVisible();

	await expect(page.getByText("Accelerated")).toHaveCount(0);
	await page.getByRole("button", { name: /London System/ }).click();
	await expect(page.getByText("Accelerated")).toBeVisible();

	await page.getByRole("button", { name: /Black/ }).click();
	await expect(page.getByText("Scandinavian Defense")).toBeVisible();
	await expect(page.getByText("−1.0")).toBeVisible();
	await expect(page.getByText("1 played once: +0.5")).toBeVisible();
	await expect(page.getByText("London System")).toHaveCount(0);
});
