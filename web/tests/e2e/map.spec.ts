import { test, expect } from "@playwright/test";

test("map page loads with header card and time slider", async ({ page }) => {
  await page.goto("/map");
  await expect(page.getByText(/Equatorial Plasma Bubble Map/i)).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByTestId("time-slider")).toBeVisible();
});

test("time slider is interactive", async ({ page }) => {
  await page.goto("/map");
  const slider = page.getByTestId("time-slider");
  await expect(slider).toBeVisible({ timeout: 15_000 });
  // Move the slider via keyboard so we don't need to know its bounding box.
  await slider.focus();
  await page.keyboard.press("Home");
  await page.keyboard.press("End");
});
