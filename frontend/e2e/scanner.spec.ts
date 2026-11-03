import { expect, test } from "@playwright/test";
import path from "node:path";

const email = `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 6)}@example.com`;
const password = "E2eTestPassw0rd";
const sample = path.resolve(process.cwd(), "../tests/fixtures/sample_orchard.jpg"); // run from frontend/

test.describe.serial("scanner flow", () => {
  test("register, upload an image, see real detections and history", async ({ page }) => {
    await page.goto("/register");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/app$/);

    await page.goto("/app/scanner");
    await page.getByTestId("file-input").setInputFiles(sample);
    await expect(page.getByRole("heading", { name: "Results" })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/Scan #\d+/).first()).toBeVisible();

    await page.goto("/app/history");
    await expect(page.getByRole("link", { name: /#\d+/ }).first()).toBeVisible();
  });

  test("camera permission denied shows a clear error", async ({ page, context }) => {
    await context.clearPermissions();
    await page.addInitScript(() => {
      // simulate a user denying the permission prompt
      Object.defineProperty(navigator, "mediaDevices", {
        value: { getUserMedia: () => Promise.reject(Object.assign(new Error("denied"), { name: "NotAllowedError" })), enumerateDevices: async () => [] },
      });
    });
    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.goto("/app/scanner");
    await page.getByRole("tab", { name: "Camera" }).click();
    await page.getByRole("button", { name: "Start camera" }).click();
    await expect(page.getByRole("alert")).toContainText(/permission was denied/i);
  });

  test("dashboard is responsive on small screens", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("button", { name: "Open menu" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(overflow).toBe(false);
  });
});
