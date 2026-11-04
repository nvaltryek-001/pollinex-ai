import { expect, test } from "@playwright/test";
import { emailFor, login, register, uploadSample } from "./helpers";

test.describe.serial("scanner, camera and core flows", () => {
  let email = "";

  test("register, upload an image, see real detections, correct a species, history", async ({ page }, info) => {
    email = emailFor(info, "flow");
    await register(page, email);
    await uploadSample(page);
    await expect(page.getByText(/Scan #\d+/).first()).toBeVisible();
    // every flower result carries a provenance badge
    await expect(page.getByText(/trained model|close-up fallback/i).first()).toBeVisible();
    // manual species correction re-runs readiness
    await page.getByLabel("Wrong species?").selectOption("hibiscus");
    await expect(page.getByText(/user corrected/i).first()).toBeVisible({ timeout: 30_000 });

    await page.goto("/app/history");
    await expect(page.getByRole("link", { name: /#\d+/ }).first()).toBeVisible();
  });

  test("camera starts with a (fake) device, live scan analyses sampled frames, capture saves a scan", async ({ page }) => {
    await login(page, email);
    await page.goto("/app/scanner");
    await page.getByRole("tab", { name: "Camera" }).click();
    await page.getByRole("button", { name: "Start camera" }).click();
    await expect(page.getByRole("button", { name: "Stop camera" })).toBeVisible({ timeout: 20_000 });
    await page.getByRole("button", { name: "Start live scan" }).click();
    await expect.poll(async () => Number(await page.getByTestId("frames-analysed").textContent()), { timeout: 60_000 }).toBeGreaterThan(0);
    await page.getByRole("button", { name: "Stop live scan" }).click();
    await page.getByRole("button", { name: /Capture & analyse/ }).click();
    await expect(page.getByRole("heading", { name: "Results" })).toBeVisible({ timeout: 90_000 });
  });

  test("camera permission denied shows a clear error", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "mediaDevices", {
        value: { getUserMedia: () => Promise.reject(Object.assign(new Error("denied"), { name: "NotAllowedError" })), enumerateDevices: async () => [] },
      });
    });
    await login(page, email);
    await page.goto("/app/scanner");
    await page.getByRole("tab", { name: "Camera" }).click();
    await page.getByRole("button", { name: "Start camera" }).click();
    await expect(page.getByRole("alert")).toContainText(/permission was denied/i);
  });

  test("simulator runs, replays and shows the computational disclaimer", async ({ page }) => {
    await login(page, email);
    await page.goto("/app/simulator");
    await page.getByLabel("Species profile").selectOption("tomato");
    await page.getByRole("button", { name: "Run simulation" }).click();
    await expect(page.getByText("Simulated transfer efficiency").first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/not measured/i).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Replay from start" })).toBeVisible();
  });

  test("every page in the sidebar loads without an error banner", async ({ page }) => {
    await login(page, email);
    const paths = ["/app", "/app/scanner", "/app/history", "/app/fields", "/app/inventory", "/app/environment", "/app/species",
      "/app/structure", "/app/maturity", "/app/readiness", "/app/health", "/app/simulator", "/app/analytics", "/app/evaluation",
      "/app/research", "/app/datasets", "/app/reports"];
    for (const p of paths) {
      await page.goto(p);
      await expect(page.locator("h1").first()).toBeVisible({ timeout: 15_000 });
      await page.waitForLoadState("networkidle");
      await expect(page.getByRole("alert"), `error banner on ${p}`).toHaveCount(0);
    }
  });

  test("dashboard is responsive on small screens", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await login(page, email);
    await expect(page.getByRole("button", { name: "Open menu" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(overflow).toBe(false);
  });
});
