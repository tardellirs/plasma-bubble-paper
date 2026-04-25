"use client";

import {
  Area,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type TimelineRow = {
  time: string;
  kp: number | null;
  dst: number | null;
  f107: number | null;
  ap: number | null;
};

const STORM_THRESHOLDS = [
  { y: -30, label: "moderate", color: "#F7A072" },
  { y: -100, label: "intense", color: "#E63946" },
  { y: -250, label: "super", color: "#9B5DE5" },
];

export function StormTimeline({ rows }: { rows: TimelineRow[] }) {
  const data = rows.map((r) => ({
    ...r,
    t: new Date(r.time).toISOString().slice(0, 13),
  }));
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
            Geomagnetic activity
          </div>
          <div className="font-display text-base mt-1">
            Kp + Dst — last {Math.round(rows.length / 24)} days
          </div>
        </div>
        <div className="text-xs font-mono text-[var(--fg-muted)]">
          source: GFZ Potsdam · WDC Kyoto
        </div>
      </div>
      <div className="grid grid-cols-1 gap-2">
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ left: 0, right: 12, top: 4, bottom: 0 }}>
              <XAxis
                dataKey="t"
                stroke="#8c93a8"
                fontSize={10}
                interval={Math.max(1, Math.floor(data.length / 12))}
                tickFormatter={(v) => v.slice(5, 10)}
              />
              <YAxis stroke="#8c93a8" fontSize={10} domain={[0, 9]} />
              <Tooltip
                contentStyle={{
                  background: "#0e1320",
                  border: "1px solid #1c2236",
                  borderRadius: 8,
                  color: "#f5f6f8",
                  fontSize: 12,
                }}
              />
              <ReferenceLine y={5} stroke="#F7A072" strokeDasharray="3 3" />
              <Area
                type="step"
                dataKey="kp"
                stroke="#0FA3B1"
                strokeWidth={1.5}
                fill="#0FA3B1"
                fillOpacity={0.18}
                isAnimationActive={false}
                name="Kp"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ left: 0, right: 12, top: 4, bottom: 0 }}>
              <XAxis
                dataKey="t"
                stroke="#8c93a8"
                fontSize={10}
                interval={Math.max(1, Math.floor(data.length / 12))}
                tickFormatter={(v) => v.slice(5, 10)}
              />
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
              {STORM_THRESHOLDS.map((t) => (
                <ReferenceLine
                  key={t.label}
                  y={t.y}
                  stroke={t.color}
                  strokeDasharray="3 3"
                  label={{ value: t.label, fill: t.color, fontSize: 10, position: "right" }}
                />
              ))}
              <Line
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
    </div>
  );
}
