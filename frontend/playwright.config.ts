import { defineConfig, devices } from "@playwright/test";

// Runs against a live stack: backend on :8000 and `npm run dev` (or preview) on :5173.
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
