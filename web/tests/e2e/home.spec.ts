import { test, expect } from "@playwright/test";

test("home renders hero and stat tiles", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Equatorial plasma bubbles/i })
  ).toBeVisible();
  await expect(page.getByRole("link", { name: /Explore the live map/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Inspect the dataset/ })).toBeVisible();
  // Stats tiles
  await expect(page.getByText(/Stations/, { exact: false })).toBeVisible();
  await expect(page.getByText(/Detected events/i)).toBeVisible();
});

test("nav links route to map and dataset", async ({ page }) => {
  await page.goto("/");
  // Use the nav <header> to disambiguate from the hero CTA.
  const nav = page.locator("header nav");
  await nav.getByRole("link", { name: "Map" }).click();
  await expect(page).toHaveURL(/\/map$/);
  await page.goto("/");
  await nav.getByRole("link", { name: "Dataset" }).click();
  await expect(page).toHaveURL(/\/dataset$/);
});
