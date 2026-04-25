/**
 * Thin client for the EPB detector FastAPI service.
 *
 * Two paths depending on where fetch runs:
 *
 * - **Browser (CSR)**: relative `/api/*` — Next.js rewrites in
 *   `next.config.mjs` proxy to the private FastAPI container.
 * - **Server (SSR / RSC)**: absolute URL is required by Node's `fetch`.
 *   We use `API_INTERNAL_URL` (default `http://epb-api:8000`, suitable
 *   for the docker-compose stack) so the page never goes back through
 *   the public Traefik path on render.
 *
 * `NEXT_PUBLIC_API_URL` overrides the browser default — set it in
 * `.env.local` to point straight at a local API for dev.
 */

const IS_SERVER = typeof window === "undefined";

export const API_BASE = IS_SERVER
  ? process.env.API_INTERNAL_URL ?? "http://localhost:8000"
  : process.env.NEXT_PUBLIC_API_URL ?? "/api";

export type Station = {
  id: string;
  name: string;
  region: "magnetic-equator" | "eia-crest-south" | "mid-latitude";
  geodetic_lat_deg: number;
  geodetic_lon_deg: number;
  height_m: number;
  ecef_x_m: number;
  ecef_y_m: number;
  ecef_z_m: number;
  operator: string;
  status: string;
  mvp: boolean;
};

export type EventRow = {
  sta: string;
  sat: string;
  start: string;
  end: string;
  n_windows: number;
  peak_probability: number;
  peak_roti: number | null;
  ipp_lon_mean: number;
  ipp_lat_mean: number;
  qd_lat_mean: number;
  duration_minutes: number;
};

export type EventsSummary = {
  total: number;
  by_station: Record<string, number>;
};

export type SnapshotMeta = {
  snapshot_id: string;
  created_at: string;
  git_sha: string;
  rule_version: string;
  n_windows: number;
  n_positives: number;
  n_station_days: number;
  stations: string[];
  years: number[];
  feature_columns: string[];
  sha256_features: string;
  sha256_labels: string;
  sha256_splits: string;
};

export async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API ${path} -> ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

// Safe wrappers — return null instead of throwing in SSR pages so we can
// render a graceful "API offline" state when the backend isn't reachable.
export async function fetchOrNull<T>(path: string): Promise<T | null> {
  try {
    return await fetchJSON<T>(path);
  } catch {
    return null;
  }
}
