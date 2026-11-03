import { defineConfig, devices } from "@playwright/test";

// Runs against a live stack: backend on :8000 and `vite preview --port 5173` (or `npm run dev`).
// Chromium's built-in fake camera lets the camera tests run headless (no real hardware needed).
const fakeCamera = {
  launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] },
  permissions: ["camera"],
};

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], ...fakeCamera } },
    { name: "mobile", use: { ...devices["Pixel 7"], ...fakeCamera } },
  ],
});
