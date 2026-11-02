import { expect, type Page, test } from "@playwright/test";

function colours(page: Page) {
	return page.locator("body").evaluate((body) => {
		const style = getComputedStyle(body);
		return { background: style.backgroundColor, text: style.color };
	});
}

test("the page follows a light system setting", async ({ page }) => {
	await page.emulateMedia({ colorScheme: "light" });
	await page.goto("/");

	expect(await colours(page)).toEqual({ background: "rgb(255, 255, 255)", text: "rgb(0, 0, 0)" });
});

test("the page follows a dark system setting", async ({ page }) => {
	await page.emulateMedia({ colorScheme: "dark" });
	await page.goto("/");

	const { background, text } = await colours(page);
	expect(background).not.toBe("rgb(255, 255, 255)");
	expect(text).toBe("rgb(255, 255, 255)");
});

test("the page changes when the system setting changes", async ({ page }) => {
	await page.emulateMedia({ colorScheme: "light" });
	await page.goto("/");

	await page.emulateMedia({ colorScheme: "dark" });

	expect((await colours(page)).background).not.toBe("rgb(255, 255, 255)");
});
