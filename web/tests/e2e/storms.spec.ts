import { test, expect } from "@playwright/test";

test("/storms page renders hero and catalog", async ({ page }) => {
  await page.goto("/storms");
  await expect(
    page.getByRole("heading", { name: /Storms, dynamos, and bubbles/i })
  ).toBeVisible();
  await expect(page.getByText(/Storms in dataset/i)).toBeVisible();
  // The "Storm catalog" heading renders regardless of API state — it's the
  // most stable assertion across CI (API offline) and local dev (API up).
  await expect(
    page.getByRole("heading", { name: /Storm catalog/i })
  ).toBeVisible();
});

test("nav exposes Storms link", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  const link = page.locator('header nav a[href="/storms"]');
  await expect(link).toBeVisible();
  await Promise.all([page.waitForURL(/\/storms$/), link.click()]);
});
