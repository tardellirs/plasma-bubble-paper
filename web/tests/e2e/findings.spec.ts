import { test, expect } from "@playwright/test";

test("/findings renders even when analysis JSON is absent", async ({ page }) => {
  // Stub the API: pretend analysis isn't on disk yet.
  await page.route("**/api/storms/v3/analysis", (route) =>
    route.fulfill({ json: { available: false } }),
  );
  await page.goto("/findings");
  await expect(
    page.getByRole("heading", { name: /Analysis not yet available/i }),
  ).toBeVisible();
});

test("/findings renders the three hero stats when analysis is present", async ({ page }) => {
  await page.route("**/api/storms/v3/analysis", (route) =>
    route.fulfill({
      json: {
        available: true,
        model_id_predicted_with: "xgb_v0.3.0",
        Q1_storm_vs_quiet: {
          storm_rate_mean: 0.123,
          quiet_rate_mean: 0.045,
          ratio_storm_to_quiet: {
            ratio: 2.73,
            ci_lo: 1.9,
            ci_hi: 3.5,
            n_storms: 31,
            n_quiet_groups: 287,
          },
          n_intense_storms: 31,
        },
        Q2_lt_amplification: {
          four_bin: {
            pre_sunset: { mean: 0.13, ci_lo: 0.08, ci_hi: 0.18, n: 7 },
            PRE: { mean: 0.21, ci_lo: 0.14, ci_hi: 0.28, n: 6 },
            post_midnight: { mean: 0.09, ci_lo: 0.05, ci_hi: 0.14, n: 10 },
            morning: { mean: 0.08, ci_lo: 0.04, ci_hi: 0.13, n: 8 },
          },
          two_bin: {
            PRE_adjacent: { mean: 0.17, ci_lo: 0.11, ci_hi: 0.23, n: 13 },
            non_PRE: { mean: 0.085, ci_lo: 0.05, ci_hi: 0.12, n: 18 },
          },
          two_bin_mannwhitney_test: { p_one_sided_greater: 0.012 },
          kruskal_wallis_4bin: { p: 0.04 },
        },
        Q3_intensity_curve: { spearman_rho: 0.62, spearman_p: 0.003, n_storms: 31 },
        Q6_solar_cycle: {
          by_quartile: [
            { quartile: 0, n: 8, phase_lo: 0.4, phase_hi: 0.55, rate_mean: 0.06 },
            { quartile: 3, n: 8, phase_lo: 0.85, phase_hi: 0.99, rate_mean: 0.18 },
          ],
          n_storms: 31,
        },
      },
    }),
  );
  await page.route("**/api/storms/v3/figure/**", (route) =>
    // 1x1 transparent PNG so the <img> doesn't 404.
    route.fulfill({
      contentType: "image/png",
      body: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        "base64",
      ),
    }),
  );

  await page.goto("/findings");
  await expect(
    page.getByRole("heading", { name: /What we found/i }),
  ).toBeVisible();
  // Three hero stats present.
  await expect(page.getByText("EPB rate during storm vs quiet")).toBeVisible();
  await expect(page.getByText("PRE-adjacent vs non-PRE storms")).toBeVisible();
  await expect(page.getByText(/Solar-cycle/i)).toBeVisible();
  // Citation block with bibtex marker.
  await expect(page.getByText("@article{")).toBeVisible();
});

test("nav exposes Findings link", async ({ page }) => {
  await page.goto("/");
  const link = page.locator('header nav a[href="/findings"]');
  await expect(link).toBeVisible();
});
