import { defineConfig, devices } from "@playwright/test";

const localPort = process.env.PLAYWRIGHT_PORT || "3100";
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${localPort}`;
const shouldStartLocalServer = !process.env.PLAYWRIGHT_BASE_URL;
const serverMode = process.env.PLAYWRIGHT_SERVER_MODE || "dev";
const useProductionServer = serverMode === "prod" || serverMode === "production";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: {
    timeout: 8_000,
  },
  fullyParallel: true,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: shouldStartLocalServer
    ? {
        command: useProductionServer
          ? `npm run build && npm run start -- --hostname 127.0.0.1 --port ${localPort}`
          : `npm run dev -- --hostname 127.0.0.1 --port ${localPort}`,
        env: { ...process.env, NODE_ENV: useProductionServer ? "production" : "development" },
        url: baseURL,
        reuseExistingServer: !useProductionServer && !process.env.CI,
        timeout: useProductionServer ? 240_000 : 120_000,
      }
    : undefined,
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
