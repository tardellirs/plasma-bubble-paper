import { test, expect } from "@playwright/test";

test("/storms page renders hero and catalog", async ({ page }) => {
  await page.goto("/storms");
  await expect(
    page.getByRole("heading", { name: /Storms, dynamos, and bubbles/i })
  ).toBeVisible();
  await expect(page.getByText(/Storms in dataset/i)).toBeVisible();
  // Either the catalog table renders, or the empty-state copy does.
  const tableHeading = page.getByRole("heading", { name: /Storm catalog/i });
  await expect(tableHeading).toBeVisible();
  const emptyState = page.getByText(/No storms detected/i);
  const tableHeader = page.getByText(/EPB rate/i).first();
  await expect(emptyState.or(tableHeader)).toBeVisible();
});

test("nav exposes Storms link", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  const link = page.locator('header nav a[href="/storms"]');
  await expect(link).toBeVisible();
  await Promise.all([page.waitForURL(/\/storms$/), link.click()]);
});
