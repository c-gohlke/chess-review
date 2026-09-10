import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
	testDir: "e2e",
	webServer: { command: "pnpm dev --port 5173 --strictPort", url: "http://localhost:5173", reuseExistingServer: true },
	use: { baseURL: "http://localhost:5173" },
	projects: [
		{ name: "desktop", use: { ...devices["Desktop Chrome"] } },
		{ name: "phone", use: { ...devices["Pixel 7"] } },
	],
});
