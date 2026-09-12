import { expect, test } from "@playwright/test";
import { drag } from "./drag";

test("board renders and accepts a legal move", async ({ page }) => {
	await page.goto("/");
	await expect(page.locator("[data-square]")).toHaveCount(64);

	await drag(page, "e2", "e4");
	await expect(page.locator('[data-square="e4"] [data-piece]')).toHaveCount(1);
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCount(0);
});

test("illegal move snaps back and clears the highlights", async ({ page }) => {
	await page.goto("/");
	await drag(page, "e2", "e5");
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCount(1);
	await expect(page.locator('[data-square="e5"] [data-piece]')).toHaveCount(0);
	await expect(page.locator('[data-square="e4"] div').first()).not.toHaveCSS("background-image", /radial-gradient/);
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCSS("transform", "none");
});

test("clicking an illegal square clears the selection", async ({ page }) => {
	await page.goto("/");
	await page.locator('[data-square="e2"]').click();
	await expect(page.locator('[data-square="e4"] div').first()).toHaveCSS("background-image", /radial-gradient/);

	await page.locator('[data-square="e5"]').click();
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCount(1);
	await expect(page.locator('[data-square="e4"] div').first()).not.toHaveCSS("background-image", /radial-gradient/);
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCSS("transform", "none");
});

test("right-clicking clears the selection", async ({ page }) => {
	await page.goto("/");
	await page.locator('[data-square="e2"]').click();
	await expect(page.locator('[data-square="e4"] div').first()).toHaveCSS("background-image", /radial-gradient/);

	await page.locator('[data-square="a5"]').click({ button: "right" });
	await page.mouse.move(0, 0);
	await expect(page.locator('[data-square="e4"] div').first()).not.toHaveCSS("background-image", /radial-gradient/);
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCSS("transform", "none");
});

test("right-clicking during a drag cancels it and clears the highlights", async ({ page }) => {
	await page.goto("/");
	const target = page.locator('[data-square="e4"]');
	await page.locator('[data-square="e2"]').hover();
	await page.mouse.down();
	const box = await target.boundingBox();
	if (!box) throw new Error("square e4 not visible");
	await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 10 });
	await expect(target.locator("div").first()).toHaveCSS("background-image", /radial-gradient/);

	await page.mouse.down({ button: "right" });
	await page.mouse.up({ button: "right" });
	await page.mouse.up();
	await page.mouse.move(0, 0);
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCount(1);
	await expect(page.locator('[data-square="e4"] [data-piece]')).toHaveCount(0);
	await expect(target.locator("div").first()).not.toHaveCSS("background-image", /radial-gradient/);
	await expect(page.locator('[data-square="e2"] [data-piece]')).toHaveCSS("transform", "none");
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

test("pressing a piece highlights its legal moves before the mouse is released", async ({ page }) => {
	await page.goto("/");

	await page.locator('[data-square="e2"]').hover();
	await page.mouse.down();
	await expect(page.locator('[data-square="e4"] div').first()).toHaveCSS("background-image", /radial-gradient/);
	await page.mouse.up();
});

test("dragging a piece highlights its legal moves until it is dropped", async ({ page }) => {
	await page.goto("/");

	const source = page.locator('[data-square="e2"]');
	const target = page.locator('[data-square="e4"]');
	await source.hover();
	await page.mouse.down();
	const box = await target.boundingBox();
	if (!box) throw new Error("square e4 not visible");
	await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 10 });
	await expect(page.locator('[data-square="e3"] div').first()).toHaveCSS("background-image", /radial-gradient/);
	await expect(page.locator('[data-square="e4"] div').first()).toHaveCSS("background-image", /radial-gradient/);

	await page.mouse.up();
	await expect(page.locator('[data-square="e4"] [data-piece]')).toHaveCount(1);
	await expect(page.locator('[data-square="e3"] div').first()).not.toHaveCSS("background-image", /radial-gradient/);
});

test("a hovered or selected piece is enlarged by 20%", async ({ page }) => {
	await page.goto("/");
	const pawn = page.locator('[data-square="e2"] [data-piece]');
	const knight = page.locator('[data-square="g1"] [data-piece]');

	await pawn.hover();
	await expect(pawn).toHaveCSS("transform", "matrix(1.2, 0, 0, 1.2, 0, 0)");
	await expect(knight).toHaveCSS("transform", "none");

	await pawn.click();
	await page.mouse.move(0, 0);
	await expect(pawn).toHaveCSS("transform", "matrix(1.2, 0, 0, 1.2, 0, 0)");
});
