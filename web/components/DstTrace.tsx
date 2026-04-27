"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type TimelinePoint = {
  time: string;
  kp: number | null;
  dst: number | null;
};

const STORM_THRESHOLDS = [
  { y: -30, label: "moderate", color: "#F7A072" },
  { y: -100, label: "intense", color: "#E63946" },
  { y: -250, label: "super", color: "#9B5DE5" },
];

export function DstTrace({
  rows,
  events,
}: {
  rows: TimelinePoint[];
  events?: { time: string; n: number }[];
}) {
  const data = rows.map((r) => ({
    t: Date.parse(r.time),
    dst: r.dst,
    kp: r.kp,
  }));

  // Aggregate events into the same time bins as the timeline (per hour).
  const eventBins = new Map<number, number>();
  if (events) {
    for (const e of events) {
      const t = Math.floor(Date.parse(e.time) / 3_600_000) * 3_600_000;
      eventBins.set(t, (eventBins.get(t) ?? 0) + e.n);
    }
  }
  const merged = data.map((d) => ({
    ...d,
    n_events: eventBins.get(d.t) ?? 0,
  }));

  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
        Dst trace · model EPB events overlay
      </div>
      <div className="h-72 mt-3">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={merged} margin={{ left: 0, right: 12, top: 6, bottom: 0 }}>
            <CartesianGrid stroke="#1c2236" strokeDasharray="3 3" />
            <XAxis
              dataKey="t"
              type="number"
              domain={["dataMin", "dataMax"]}
              scale="time"
              stroke="#8c93a8"
              fontSize={10}
              tickFormatter={(v) =>
                new Date(v).toISOString().slice(5, 13).replace("T", " ")
              }
              tickCount={8}
            />
            <YAxis
              yAxisId="dst"
              stroke="#E63946"
              fontSize={10}
              label={{
                value: "Dst (nT)",
                angle: -90,
                position: "insideLeft",
                fill: "#E63946",
                fontSize: 10,
              }}
            />
            <YAxis
              yAxisId="events"
              orientation="right"
              stroke="#0FA3B1"
              fontSize={10}
              label={{
                value: "EPB events / hr",
                angle: 90,
                position: "insideRight",
                fill: "#0FA3B1",
                fontSize: 10,
              }}
            />
            <Tooltip
              contentStyle={{
                background: "#0e1320",
                border: "1px solid #1c2236",
                borderRadius: 8,
                color: "#f5f6f8",
                fontSize: 12,
              }}
              labelFormatter={(v) =>
                new Date(v as number).toISOString().slice(0, 16).replace("T", " ") + " UTC"
              }
            />
            {STORM_THRESHOLDS.map((t) => (
              <ReferenceLine
                key={t.label}
                yAxisId="dst"
                y={t.y}
                stroke={t.color}
                strokeDasharray="3 3"
                label={{
                  value: t.label,
                  fill: t.color,
                  fontSize: 10,
                  position: "right",
                }}
              />
            ))}
            <Area
              yAxisId="events"
              type="step"
              dataKey="n_events"
              stroke="#0FA3B1"
              strokeWidth={1}
              fill="#0FA3B1"
              fillOpacity={0.18}
              isAnimationActive={false}
              name="EPB events / hr"
            />
            <Line
              yAxisId="dst"
              type="monotone"
              dataKey="dst"
              stroke="#E63946"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
              name="Dst"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
