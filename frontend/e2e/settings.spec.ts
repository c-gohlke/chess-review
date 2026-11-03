import { expect, test } from "@playwright/test";

test("settings show the current player, even when there is only one", async ({ page }) => {
	await page.route("**/api/users", (route) => route.fulfill({ json: ["alice"] }));
	await page.goto("/");

	await page.getByRole("button", { name: "Settings" }).click();

	await expect(page.getByLabel("Player")).toHaveValue("alice");
	await expect(page.getByLabel("Player").getByRole("option")).toHaveText(["alice"]);
});

test("a failed players request is shown in Settings", async ({ page }) => {
	await page.route("**/api/users", (route) => route.fulfill({ status: 500 }));
	await page.goto("/");

	await page.getByRole("button", { name: "Settings" }).click();

	await expect(page.getByText("request failed with status 500")).toBeVisible();
	await expect(page.getByLabel("Player")).toHaveCount(0);
});
