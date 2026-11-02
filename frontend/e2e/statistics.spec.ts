import { expect, type Page, test } from "@playwright/test";

const FORKS = {
	analysed_losses: 200,
	losses_with_fork: 30,
	decided_by_fork: 12,
	kinds: [
		{ name: "Knight fork", losses: 20 },
		{ name: "Pawn fork, royal (king and queen)", losses: 5 },
	],
};

async function openStatistics(page: Page, forks: typeof FORKS) {
	await page.route("**/api/users", (route) => route.fulfill({ json: ["alice"] }));
	await page.route("**/api/statistics/forks?*", (route) => route.fulfill({ json: forks }));
	await page.goto("/");
	await page.getByRole("button", { name: "Statistics" }).click();
}

test("shows how often the player lost to each kind of fork", async ({ page }) => {
	await openStatistics(page, FORKS);

	await expect(page.getByText("A fork figured in 30 of 200 analysed losses (15.0%)")).toBeVisible();
	await expect(page.getByText("It was the deciding error in 12 (6.0%).")).toBeVisible();
	await expect(page.getByRole("row", { name: "Knight fork 20 10.0%" })).toBeVisible();
	await expect(page.getByRole("row", { name: "Pawn fork, royal (king and queen) 5 2.5%" })).toBeVisible();
});

test("explains when the player's games have not been analysed", async ({ page }) => {
	await openStatistics(page, { analysed_losses: 0, losses_with_fork: 0, decided_by_fork: 0, kinds: [] });

	await expect(page.getByText("alice's games have not been analysed yet.")).toBeVisible();
});

test("a failed request is shown", async ({ page }) => {
	await page.route("**/api/users", (route) => route.fulfill({ json: ["alice"] }));
	await page.route("**/api/statistics/forks?*", (route) => route.fulfill({ status: 500 }));
	await page.goto("/");
	await page.getByRole("button", { name: "Statistics" }).click();

	await expect(page.getByText("request failed with status 500")).toBeVisible();
});
