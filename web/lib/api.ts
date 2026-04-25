/**
 * Thin client for the EPB detector FastAPI service.
 *
 * In production, the Next.js app proxies `/api/*` to the private FastAPI
 * container (see `next.config.mjs` rewrites). For local dev, set
 * `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env.local` to bypass
 * the proxy and hit the API directly.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

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
