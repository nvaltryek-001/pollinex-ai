import { expect, type Page, type TestInfo } from "@playwright/test";
import path from "node:path";

export const PASSWORD = "E2eTestPassw0rd";
export const SAMPLE = path.resolve(process.cwd(), "../tests/fixtures/sample_orchard.jpg"); // run from frontend/

/** Unique per run + project so desktop and mobile never collide. */
export function emailFor(info: TestInfo, tag: string): string {
  return `e2e_${tag}_${info.project.name}_${process.env.GITHUB_RUN_ID ?? Date.now()}@example.com`;
}

export async function register(page: Page, email: string) {
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/app$/);
}

export async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/app$/);
}

export async function uploadSample(page: Page) {
  await page.goto("/app/scanner");
  await page.getByTestId("file-input").setInputFiles(SAMPLE);
  await expect(page.getByRole("heading", { name: "Results" })).toBeVisible({ timeout: 90_000 });
}
