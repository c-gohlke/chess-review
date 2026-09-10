import { expect, test } from "@playwright/test";
import { drag } from "./drag";

test("checkmate shows the banner", async ({ page }) => {
	await page.goto("/");
	await expect(page.locator("[data-square]")).toHaveCount(64);

	// Fool's mate: 1. f3 e5 2. g4 Qh4#
	await drag(page, "f2", "f3");
	await drag(page, "e7", "e5");
	await drag(page, "g2", "g4");
	await drag(page, "d8", "h4");

	await expect(page.getByText("Checkmate")).toBeVisible();
	await expect(page.locator("main")).toHaveScreenshot("checkmate.png");
});
