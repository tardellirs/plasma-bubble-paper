"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchOrNull } from "@/lib/api";
import type { EventRow } from "@/lib/api";

type TimeseriesRow = {
  time: string;
  prob: number;
  roti_max: number | null;
  dtec_max: number | null;
  sidx_max: number | null;
  label: number;
  kp: number | null;
  dst: number | null;
  storm_phase: string;
};

type Resp = { sta: string; sat: string; rows: TimeseriesRow[] };

const PAD_MIN = 30; // minutes of context on each side of the event window

export function EventDetail({
  event,
  onClose,
}: {
  event: EventRow;
  onClose: () => void;
}) {
  const [data, setData] = useState<TimeseriesRow[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setData(null);
    const tStart = new Date(event.start);
    const tEnd = new Date(event.end);
    const t0 = new Date(tStart.getTime() - PAD_MIN * 60 * 1000);
    const t1 = new Date(tEnd.getTime() + PAD_MIN * 60 * 1000);
    const qs = new URLSearchParams({
      sta: event.sta,
      sat: event.sat,
      t0: t0.toISOString(),
      t1: t1.toISOString(),
    });
    fetchOrNull<Resp>(`/events/timeseries?${qs.toString()}`).then((resp) => {
      if (cancelled) return;
      setData(resp?.rows ?? []);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [event.sta, event.sat, event.start, event.end]);

  // Close on Esc
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const eventStart = +new Date(event.start);
  const eventEnd = +new Date(event.end);

  const chartRows =
    data?.map((r) => ({
      ...r,
      tms: +new Date(r.time),
      prob_pct: r.prob != null ? r.prob * 100 : null,
    })) ?? [];

  return (
    <>
      {/* backdrop */}
      <div
        aria-hidden
        className="absolute inset-0 bg-black/55 backdrop-blur-sm z-30"
        onClick={onClose}
      />
      {/* drawer */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Event time series"
        className="absolute top-0 right-0 bottom-0 z-40 w-full sm:w-[560px] bg-[var(--bg)]/95 border-l border-[#1c2236] shadow-2xl overflow-y-auto"
      >
        <div className="p-6 space-y-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="font-mono text-xs text-[var(--accent)]">
                {event.sta} / {event.sat}
              </div>
              <h2 className="font-display text-xl mt-1">
                {new Date(event.start).toUTCString()}
              </h2>
              <div className="text-xs text-[var(--fg-muted)] mt-1">
                {event.duration_minutes.toFixed(1)} min · peak prob{" "}
                {event.peak_probability.toFixed(2)} · peak ROTI{" "}
                {event.peak_roti?.toFixed(2) ?? "—"} TECU/min
              </div>
            </div>
            <button
              type="button"
              aria-label="Close"
              onClick={onClose}
              className="text-[var(--fg-muted)] hover:text-white text-xl leading-none px-2"
            >
              ×
            </button>
          </div>

          <div className="grid grid-cols-3 gap-2 text-xs">
            <Stat
              label="windows"
              value={event.n_windows.toString()}
            />
            <Stat
              label="QD-lat"
              value={`${event.qd_lat_mean.toFixed(1)}°`}
            />
            <Stat
              label="IPP lon"
              value={`${event.ipp_lon_mean.toFixed(1)}°`}
            />
          </div>

          {loading && (
            <div className="text-sm text-[var(--fg-muted)]">
              Loading time series…
            </div>
          )}

          {!loading && chartRows.length === 0 && (
            <div className="text-sm text-[var(--fg-muted)]">
              No window-level series available for this event.
            </div>
          )}

          {!loading && chartRows.length > 0 && (
            <>
              <ChartCard title="Detection probability">
                <ResponsiveContainer width="100%" height={140}>
                  <LineChart
                    data={chartRows}
                    margin={{ top: 8, right: 8, bottom: 4, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1c2236" />
                    <XAxis
                      dataKey="tms"
                      type="number"
                      domain={["dataMin", "dataMax"]}
                      tickFormatter={(v) =>
                        new Date(v as number).toISOString().slice(11, 16)
                      }
                      stroke="#6b7280"
                      fontSize={10}
                    />
                    <YAxis
                      domain={[0, 100]}
                      stroke="#6b7280"
                      fontSize={10}
                      tickFormatter={(v) => `${v}%`}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(10,14,26,0.95)",
                        border: "1px solid #1c2236",
                        fontSize: 11,
                      }}
                      labelFormatter={(v) =>
                        new Date(v as number).toISOString().slice(11, 19) +
                        " UTC"
                      }
                      formatter={(value: number, name) => [
                        name === "prob_pct"
                          ? `${value.toFixed(0)}%`
                          : value,
                        name === "prob_pct" ? "Model prob" : name,
                      ]}
                    />
                    <ReferenceArea
                      x1={eventStart}
                      x2={eventEnd}
                      strokeOpacity={0}
                      fill="#e63946"
                      fillOpacity={0.08}
                    />
                    <Line
                      type="monotone"
                      dataKey="prob_pct"
                      stroke="#e63946"
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="ROTI peak (TECU / min)">
                <ResponsiveContainer width="100%" height={130}>
                  <LineChart
                    data={chartRows}
                    margin={{ top: 8, right: 8, bottom: 4, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1c2236" />
                    <XAxis
                      dataKey="tms"
                      type="number"
                      domain={["dataMin", "dataMax"]}
                      tickFormatter={(v) =>
                        new Date(v as number).toISOString().slice(11, 16)
                      }
                      stroke="#6b7280"
                      fontSize={10}
                    />
                    <YAxis stroke="#6b7280" fontSize={10} />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(10,14,26,0.95)",
                        border: "1px solid #1c2236",
                        fontSize: 11,
                      }}
                      labelFormatter={(v) =>
                        new Date(v as number).toISOString().slice(11, 19) +
                        " UTC"
                      }
                    />
                    <ReferenceArea
                      x1={eventStart}
                      x2={eventEnd}
                      strokeOpacity={0}
                      fill="#0FA3B1"
                      fillOpacity={0.08}
                    />
                    <Line
                      type="monotone"
                      dataKey="roti_max"
                      stroke="#0FA3B1"
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="ΔTEC max & SIDX max">
                <ResponsiveContainer width="100%" height={130}>
                  <LineChart
                    data={chartRows}
                    margin={{ top: 8, right: 8, bottom: 4, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1c2236" />
                    <XAxis
                      dataKey="tms"
                      type="number"
                      domain={["dataMin", "dataMax"]}
                      tickFormatter={(v) =>
                        new Date(v as number).toISOString().slice(11, 16)
                      }
                      stroke="#6b7280"
                      fontSize={10}
                    />
                    <YAxis stroke="#6b7280" fontSize={10} />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(10,14,26,0.95)",
                        border: "1px solid #1c2236",
                        fontSize: 11,
                      }}
                      labelFormatter={(v) =>
                        new Date(v as number).toISOString().slice(11, 19) +
                        " UTC"
                      }
                    />
                    <Line
                      type="monotone"
                      dataKey="dtec_max"
                      stroke="#F7A072"
                      strokeWidth={2}
                      dot={false}
                      name="ΔTEC"
                      isAnimationActive={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="sidx_max"
                      stroke="#9B5DE5"
                      strokeWidth={2}
                      dot={false}
                      name="SIDX"
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>

              <div className="text-xs text-[var(--fg-muted)] flex flex-wrap gap-4">
                <span>
                  Storm phase:{" "}
                  <span className="text-white/80 font-mono">
                    {chartRows[0]?.storm_phase ?? "—"}
                  </span>
                </span>
                {chartRows[0]?.kp != null && (
                  <span>
                    Kp:{" "}
                    <span className="text-white/80 font-mono">
                      {chartRows[0].kp.toFixed(1)}
                    </span>
                  </span>
                )}
                {chartRows[0]?.dst != null && (
                  <span>
                    Dst:{" "}
                    <span className="text-white/80 font-mono">
                      {chartRows[0].dst.toFixed(0)} nT
                    </span>
                  </span>
                )}
              </div>
            </>
          )}
        </div>
      </aside>
    </>
  );
}

function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-3">
      <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)] mb-2 px-1">
        {title}
      </div>
      {children}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[#1c2236] p-2">
      <div className="text-[10px] uppercase tracking-wider text-[var(--fg-muted)]">
        {label}
      </div>
      <div className="font-mono text-sm mt-0.5">{value}</div>
    </div>
  );
}
