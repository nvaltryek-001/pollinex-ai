import { expect, test } from "@playwright/test";
import { emailFor, register, uploadSample } from "./helpers";

// Captures genuine screenshots of the running application (CI uploads them as an artifact).
// Enabled only with SCREENSHOTS=1 so normal test runs stay fast.
test.skip(!process.env.SCREENSHOTS, "set SCREENSHOTS=1 to capture screenshots");

test("capture application screenshots", async ({ page }, info) => {
  const dir = "e2e-screenshots";
  const shot = async (name: string) => {
    // dismiss notifications and reset scroll so sticky header/sidebar render in place
    for (const b of await page.getByRole("button", { name: "Dismiss notification" }).all()) await b.click().catch(() => {});
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${dir}/${info.project.name}-${name}.png`, fullPage: info.project.name === "desktop" && !name.includes("simulator") });
  };
  await page.goto("/");
  await shot("01-landing");
  await register(page, emailFor(info, "shots"));
  await uploadSample(page);
  await page.waitForTimeout(1500);
  await shot("02-scanner-results");
  await page.goto("/app/simulator");
  await page.getByLabel("Species profile").selectOption("strawberry");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(page.getByText("Simulated transfer efficiency").first()).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(2500);
  await shot("03-simulator");
  for (const [p, n] of [["/app", "04-dashboard"], ["/app/evaluation", "05-model-evaluation"], ["/app/species", "06-species"],
    ["/app/readiness", "07-readiness"], ["/app/analytics", "08-analytics"], ["/app/datasets", "09-datasets"], ["/app/research", "10-research"]] as const) {
    await page.goto(p);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(800);
    await shot(n);
  }
});
