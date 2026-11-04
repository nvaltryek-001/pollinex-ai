import { expect, test } from "@playwright/test";
import { emailFor, login, PASSWORD, register, uploadSample } from "./helpers";

const NEW_PASSWORD = "Chang3dPassword!";

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
    // species reference panel follows the (corrected) species and is labelled as general knowledge
    await expect(page.getByText("About Hibiscus").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/reference knowledge · not from this image/).first()).toBeVisible();
    await expect(page.getByText("How this result was produced")).toBeVisible();

    await page.goto("/app/history");
    await page.getByRole("link", { name: /#\d+/ }).first().click();
    await expect(page.getByRole("button", { name: "PDF report" })).toBeVisible({ timeout: 15_000 });
    const [pdf] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "PDF report" }).click()]);
    expect(pdf.suggestedFilename()).toMatch(/^pollinex_scan_\d+\.pdf$/);
    const [csv] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: /CSV/ }).click()]);
    expect(csv.suggestedFilename()).toBe("pollinex_scans.csv");
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
      "/app/research", "/app/datasets", "/app/reports", "/app/help", "/app/settings"];
    for (const p of paths) {
      await page.goto(p);
      await expect(page.locator("h1").first(), `page heading on ${p}`).toBeVisible({ timeout: 15_000 });
      await page.waitForLoadState("networkidle");
      await expect(page.getByRole("alert"), `error banner on ${p}`).toHaveCount(0);
    }
  });

  test("species information panel works for all nine species", async ({ page }) => {
    await login(page, email);
    await page.goto("/app/species");
    const names = ["Apple", "Peach", "Pear", "Sunflower", "Hibiscus", "Tomato", "Strawberry", "Brinjal (eggplant)", "Chilli (hot pepper)"];
    for (const n of names) {
      const card = page.locator("section").filter({ has: page.getByRole("heading", { name: n, exact: true }) }).first();
      await card.getByRole("button", { name: "Biology & evidence" }).click();
      await expect(page.getByText(`About ${n}`).first(), `species panel for ${n}`).toBeVisible({ timeout: 15_000 });
      await card.getByRole("button", { name: "Less" }).click();
    }
    await expect(page.getByText(/not AI-supported/).first()).toBeVisible();
  });

  test("settings: rename, change password, old password stops working, logout protects pages", async ({ page }) => {
    await login(page, email);
    await page.goto("/app/settings");
    await page.getByLabel("Display name").fill("E2E Researcher");
    await page.getByRole("button", { name: "Save profile" }).click();
    await expect(page.getByText("Profile saved")).toBeVisible();
    await page.getByLabel("Current password").fill(PASSWORD);
    await page.getByLabel("New password", { exact: true }).fill(NEW_PASSWORD);
    await page.getByLabel("Confirm new password").fill(NEW_PASSWORD);
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByText(/Password changed/)).toBeVisible();
    // change it back so later tests (and the serial login helper) keep working
    await page.getByLabel("Current password").fill(NEW_PASSWORD);
    await page.getByLabel("New password", { exact: true }).fill(PASSWORD);
    await page.getByLabel("Confirm new password").fill(PASSWORD);
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByText(/Password changed/).first()).toBeVisible();
    // logout, then a protected page sends you to the sign-in page
    await page.getByRole("button", { name: "Log out" }).click();
    await page.goto("/app/history");
    await expect(page).toHaveURL(/\/login/);
  });

  test("no page scrolls sideways on a phone-sized screen", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await login(page, email);
    await expect(page.getByRole("button", { name: "Open menu" })).toBeVisible();
    for (const p of ["/app", "/app/scanner", "/app/history", "/app/species", "/app/fields", "/app/inventory", "/app/environment",
      "/app/analytics", "/app/evaluation", "/app/datasets", "/app/research", "/app/reports", "/app/help", "/app/settings", "/app/simulator"]) {
      await page.goto(p);
      await expect(page.locator("h1").first()).toBeVisible({ timeout: 15_000 });
      await page.waitForLoadState("networkidle");
      const w = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(w, `horizontal overflow on ${p} (${w}px)`).toBeLessThanOrEqual(1);
    }
    // a saved scan's result page (image, tables, species panel, provenance card)
    await page.goto("/app/history");
    await page.getByRole("link", { name: /#\d+/ }).first().click();
    await expect(page.getByText("How this result was produced")).toBeVisible({ timeout: 15_000 });
    const w = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(w, `horizontal overflow on the scan detail page (${w}px)`).toBeLessThanOrEqual(1);
  });
});
