"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { API_BASE } from "@/lib/api";

type DistributionResponse = {
  feature: string;
  bins: number[];
  negative: number[];
  positive: number[];
};

const FEATURE_OPTIONS = [
  "roti_max",
  "roti_p95",
  "roti_duration_above",
  "dtec_max",
  "sidx_max",
  "elevation_mean",
  "qd_lat_mean",
  "local_time_mean",
];

export function FeatureHistogram({
  snapshotId,
}: {
  snapshotId: string;
}) {
  const [feature, setFeature] = useState("roti_max");
  const [data, setData] = useState<DistributionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setData(null);
    fetch(
      `${API_BASE}/training-data/snapshots/${snapshotId}/distribution?feature=${feature}`,
      { cache: "no-store" }
    )
      .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then((d: DistributionResponse) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [feature, snapshotId]);

  const chartData = data
    ? data.bins.slice(0, -1).map((edge, i) => ({
        bin: ((edge + (data.bins[i + 1] ?? edge)) / 2).toFixed(2),
        positive: data.positive[i] ?? 0,
        negative: data.negative[i] ?? 0,
      }))
    : [];

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
            Feature distribution
          </div>
          <div className="mt-1 font-display text-lg">{feature}</div>
        </div>
        <select
          aria-label="Feature"
          className="bg-transparent border border-[#1c2236] rounded px-2 py-1 text-sm font-mono"
          value={feature}
          onChange={(e) => setFeature(e.target.value)}
          data-testid="feature-select"
        >
          {FEATURE_OPTIONS.map((f) => (
            <option key={f} value={f} className="bg-[var(--bg-soft)]">
              {f}
            </option>
          ))}
        </select>
      </div>
      <div className="h-72">
        {error && (
          <div className="text-sm text-[var(--warn)] font-mono">{error}</div>
        )}
        {!error && (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1c2236" />
              <XAxis dataKey="bin" stroke="#8c93a8" fontSize={10} />
              <YAxis stroke="#8c93a8" fontSize={10} />
              <Tooltip
                contentStyle={{
                  background: "#0e1320",
                  border: "1px solid #1c2236",
                  borderRadius: 8,
                  color: "#f5f6f8",
                  fontSize: 12,
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, color: "#8c93a8" }}
              />
              <Bar dataKey="negative" fill="#6C757D" name="non-EPB" />
              <Bar dataKey="positive" fill="#0FA3B1" name="EPB" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
