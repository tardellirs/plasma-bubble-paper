"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
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

type DayRotiPoint = {
  time: string;
  sat: string;
  system: "G" | "R";
  system_label: string;
  roti: number;
};

type DayRotiResp = {
  sta: string;
  date: string;
  year: number;
  doy: number;
  n_points: number;
  points: DayRotiPoint[];
};

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
  const [dayRoti, setDayRoti] = useState<DayRotiPoint[] | null>(null);
  const [dayRotiLoading, setDayRotiLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setDayRotiLoading(true);
    setData(null);
    setDayRoti(null);

    const tStart = new Date(event.start);
    const tEnd = new Date(event.end);
    const t0 = new Date(tStart.getTime() - PAD_MIN * 60 * 1000);
    const t1 = new Date(tEnd.getTime() + PAD_MIN * 60 * 1000);

    const qsTs = new URLSearchParams({
      sta: event.sta,
      sat: event.sat,
      t0: t0.toISOString(),
      t1: t1.toISOString(),
    });
    fetchOrNull<Resp>(`/events/timeseries?${qsTs.toString()}`).then((resp) => {
      if (cancelled) return;
      setData(resp?.rows ?? []);
      setLoading(false);
    });

    const dayUtc = tStart.toISOString().slice(0, 10);
    const qsDay = new URLSearchParams({ sta: event.sta, date: dayUtc });
    fetchOrNull<DayRotiResp>(`/events/day-roti?${qsDay.toString()}`).then(
      (resp) => {
        if (cancelled) return;
        setDayRoti(resp?.points ?? []);
        setDayRotiLoading(false);
      },
    );

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

          <ChartCard title={`24-hour ROTI · ${event.sta}`}>
            {dayRotiLoading ? (
              <div className="text-xs text-[var(--fg-muted)] py-12 text-center">
                Loading station-day scatter…
              </div>
            ) : dayRoti && dayRoti.length > 0 ? (
              <>
                <DayRotiScatter
                  points={dayRoti}
                  eventStart={eventStart}
                  eventEnd={eventEnd}
                />
                <div className="mt-2 flex items-center gap-4 text-[10px] text-[var(--fg-muted)] px-1">
                  <span className="inline-flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full bg-blue-500" />
                    GPS
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
                    GLONASS
                  </span>
                  <span className="ml-auto">
                    {dayRoti.length.toLocaleString()} samples · event window
                    shaded red
                  </span>
                </div>
              </>
            ) : (
              <div className="text-xs text-[var(--fg-muted)] py-6">
                No raw ROTI file on disk for this station-day.
              </div>
            )}
          </ChartCard>

          {loading && (
            <div className="text-sm text-[var(--fg-muted)]">
              Loading event window…
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

function DayRotiScatter({
  points,
  eventStart,
  eventEnd,
}: {
  points: DayRotiPoint[];
  eventStart: number;
  eventEnd: number;
}) {
  // Pre-bucket by constellation so Recharts gets two flat datasets it
  // can render as two coloured Scatter series.
  const gps = points
    .filter((p) => p.system === "G")
    .map((p) => ({ tms: +new Date(p.time), roti: p.roti, sat: p.sat }));
  const glonass = points
    .filter((p) => p.system === "R")
    .map((p) => ({ tms: +new Date(p.time), roti: p.roti, sat: p.sat }));

  const dayMs = 24 * 60 * 60 * 1000;
  const dayStart = Math.floor(eventStart / dayMs) * dayMs;
  const dayEnd = dayStart + dayMs;

  const ymax = Math.max(
    1,
    ...points.map((p) => p.roti).filter((v) => Number.isFinite(v)),
  );

  return (
    <ResponsiveContainer width="100%" height={200}>
      <ScatterChart margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1c2236" />
        <XAxis
          dataKey="tms"
          type="number"
          domain={[dayStart, dayEnd]}
          scale="time"
          ticks={Array.from({ length: 9 }, (_, i) => dayStart + i * 3 * 3600_000)}
          tickFormatter={(v) =>
            new Date(v as number).toISOString().slice(11, 13)
          }
          stroke="#6b7280"
          fontSize={10}
          label={{
            value: "Time (UT)",
            position: "insideBottom",
            offset: -2,
            fill: "#6b7280",
            fontSize: 10,
          }}
        />
        <YAxis
          dataKey="roti"
          type="number"
          domain={[0, Math.ceil(ymax)]}
          stroke="#6b7280"
          fontSize={10}
          label={{
            value: "ROTI (TECU/min)",
            angle: -90,
            position: "insideLeft",
            offset: 10,
            fill: "#6b7280",
            fontSize: 10,
          }}
        />
        <Tooltip
          cursor={{ strokeDasharray: "3 3", stroke: "#444" }}
          contentStyle={{
            background: "rgba(10,14,26,0.95)",
            border: "1px solid #1c2236",
            fontSize: 11,
          }}
          labelFormatter={() => ""}
          formatter={(value: number, _name, item) => {
            const p = item?.payload as { tms: number; sat: string };
            return [
              `${p.sat}: ${value.toFixed(2)} TECU/min @ ${new Date(p.tms).toISOString().slice(11, 16)}Z`,
              "",
            ];
          }}
        />
        <ReferenceArea
          x1={eventStart}
          x2={eventEnd}
          y1={0}
          y2={ymax}
          strokeOpacity={0}
          fill="#e63946"
          fillOpacity={0.1}
        />
        <Scatter
          name="GPS"
          data={gps}
          fill="#3b82f6"
          fillOpacity={0.65}
          r={2}
          isAnimationActive={false}
        />
        <Scatter
          name="GLONASS"
          data={glonass}
          fill="#ef4444"
          fillOpacity={0.65}
          r={2}
          isAnimationActive={false}
        />
      </ScatterChart>
    </ResponsiveContainer>
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
