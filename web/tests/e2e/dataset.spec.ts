import { test, expect } from "@playwright/test";

test("dataset page lists snapshot stats", async ({ page }) => {
  await page.goto("/dataset");
  await expect(
    page.getByRole("heading", { name: /Training data/ })
  ).toBeVisible();
  // Either we get cards (API up) or the no-snapshot fallback (which is the
  // graceful state when a fresh checkout has no snapshots yet).
  const stats = page.getByText(/Snapshot/, { exact: false });
  const empty = page.getByText(/No snapshots yet/);
  await expect(stats.or(empty)).toBeVisible();
});

test("methods page renders citations", async ({ page }) => {
  await page.goto("/methods");
  await expect(
    page.getByRole("heading", { name: /How we detect/ })
  ).toBeVisible();
  await expect(page.getByText(/Pi et al\., 1997/)).toBeVisible();
  await expect(page.getByText(/Cherniak/)).toBeVisible();
});
