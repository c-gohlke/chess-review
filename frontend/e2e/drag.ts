import type { Page } from "@playwright/test";

export async function drag(page: Page, from: string, to: string) {
	const source = page.locator(`[data-square="${from}"]`);
	const target = page.locator(`[data-square="${to}"]`);
	await source.hover();
	await page.mouse.down();
	const box = await target.boundingBox();
	if (!box) throw new Error(`square ${to} not visible`);
	await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 10 });
	await page.mouse.up();
}
