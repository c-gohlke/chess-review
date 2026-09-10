import { expect, test } from "@playwright/test";

async function drag(page: import("@playwright/test").Page, from: string, to: string) {
	const source = page.locator(`[data-square="${from}"]`);
	const target = page.locator(`[data-square="${to}"]`);
	await source.hover();
	await page.mouse.down();
	const box = await target.boundingBox();
	if (!box) throw new Error(`square ${to} not visible`);
	await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 10 });
	await page.mouse.up();
}

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
