import { test, expect } from "@playwright/test";

const FAKE_CATALOG = [
  {
    storm_id: 23,
    main_start: "2024-05-10T16:00:00+00:00",
    dst_min_time: "2024-05-11T02:00:00+00:00",
    dst_min_value: -406,
    recovery_end: "2024-05-14T18:00:00+00:00",
    storm_class: "super",
    lt_bin: "post_midnight",
    season: "MAM",
    recovery_duration_hours: 88,
    f107_at_min: 187,
    solar_cycle_phase: 0.93,
    is_intense_or_stronger: true,
  },
];

// FIXME: page is server-rendered (RSC), so the SSR fetch goes straight to
// API_INTERNAL_URL — Playwright's page.route only intercepts browser
// requests and never fires here. Re-enable once the data fetch moves to
// a client component or we wire up MSW for SSR mocks.
test.fixme("/storms/[id] populates the storm card", async ({ page }) => {
  await page.route("**/api/storms/v3/catalog**", (route) =>
    route.fulfill({ json: FAKE_CATALOG }),
  );
  await page.route("**/api/events**", (route) =>
    route.fulfill({
      json: [
        {
          sta: "SALU",
          sat: "G05",
          start: "2024-05-11T00:01:00Z",
          end: "2024-05-11T00:21:00Z",
          n_windows: 2,
          peak_probability: 0.9,
          peak_roti: 1.2,
          ipp_lon_mean: 314,
          ipp_lat_mean: -3,
        },
        {
          sta: "BRAZ",
          sat: "G07",
          start: "2024-05-11T01:00:00Z",
          end: "2024-05-11T01:20:00Z",
          n_windows: 2,
          peak_probability: 0.85,
          peak_roti: 0.95,
          ipp_lon_mean: 312,
          ipp_lat_mean: -16,
        },
      ],
    }),
  );

  await page.goto("/storms/23");
  await expect(
    page.getByRole("heading", { name: /Storm #23.*SUPER/i }),
  ).toBeVisible();
  // Header summary text.
  await expect(page.getByText(/-406 nT/)).toBeVisible();
  await expect(page.getByText(/post_midnight/)).toBeVisible();
  // Per-station list.
  await expect(page.getByText("SALU")).toBeVisible();
  await expect(page.getByText("BRAZ")).toBeVisible();
});

test("/storms/[id] handles unknown id gracefully", async ({ page }) => {
  await page.route("**/api/storms/v3/catalog**", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto("/storms/99999");
  await expect(
    page.getByRole("heading", { name: /Storm #99999 not found/i }),
  ).toBeVisible();
});
