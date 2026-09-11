import { expect, test } from "@playwright/test";
import { drag } from "./drag";

test("board renders and accepts a legal move", async ({ page }) => {
	await page.goto("/");
	await expect(page.locator("[data-square]")).toHaveCount(64);

	await drag(page, "e2", "e4");
	await expect(page.locator('[data-square="e4"] [data-piece]')).toHaveCount(1);
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCount(0);
});

test("illegal move snaps back", async ({ page }) => {
	await page.goto("/");
	await drag(page, "e2", "e5");
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCount(1);
	await expect(page.locator('[data-square="e5"] [data-piece]')).toHaveCount(0);
});

test("clicking a piece highlights its legal moves, and clicking a highlighted square moves it", async ({ page }) => {
	await page.goto("/");

	await page.locator('[data-square="e2"]').click();
	await expect(page.locator('[data-square="e3"] div').first()).toHaveCSS("background-image", /radial-gradient/);
	await expect(page.locator('[data-square="e4"] div').first()).toHaveCSS("background-image", /radial-gradient/);
	await expect(page.locator('[data-square="d3"] div').first()).not.toHaveCSS("background-image", /radial-gradient/);

	await page.locator('[data-square="e4"]').click();
	await expect(page.locator('[data-square="e4"] [data-piece]')).toHaveCount(1);
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCount(0);
	await expect(page.locator('[data-square="e3"] div').first()).not.toHaveCSS("background-image", /radial-gradient/);
});
