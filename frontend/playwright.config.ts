import { type AddressInfo, createServer } from "node:net";
import { defineConfig, devices } from "@playwright/test";

function freePort(): Promise<number> {
	return new Promise((resolve, reject) => {
		const server = createServer();
		server.once("error", reject);
		server.listen(0, "127.0.0.1", () => {
			const { port } = server.address() as AddressInfo;
			server.close(() => resolve(port));
		});
	});
}

// Each run gets its own port so the tests never attach to a dev server left running in another
// worktree. The runner picks the port and stores it in the environment because Playwright workers
// re-import this file and must agree on the same baseURL.
process.env.E2E_PORT ??= String(await freePort());
const baseURL = `http://localhost:${process.env.E2E_PORT}`;

export default defineConfig({
	testDir: "e2e",
	webServer: { command: `npm run dev -- --port ${process.env.E2E_PORT} --strictPort`, url: baseURL },
	use: { baseURL },
	projects: [
		{ name: "desktop", use: { ...devices["Desktop Chrome"] } },
		{ name: "phone", use: { ...devices["Pixel 7"] } },
	],
});
