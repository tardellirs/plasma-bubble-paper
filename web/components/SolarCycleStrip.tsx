"use client";

import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useRouter, usePathname } from "next/navigation";

export type SsnPoint = { date: string; ssn: number };
export type StormDot = {
  storm_id: number;
  dst_min_time: string;
  abs_dst_min: number;
  storm_class: string;
  is_intense_or_stronger: boolean;
};

const CLASS_COLORS: Record<string, string> = {
  moderate: "#F7A072",
  intense: "#E63946",
  severe: "#C81D25",
  super: "#9B5DE5",
};

export function SolarCycleStrip({
  ssn,
  storms,
}: {
  ssn: SsnPoint[];
  storms: StormDot[];
}) {
  const router = useRouter();
  const pathname = usePathname();
  // Down-sample SSN to ~monthly cadence for performance.
  const ssnByMonth: Record<string, number[]> = {};
  for (const p of ssn) {
    const key = p.date.slice(0, 7);
    (ssnByMonth[key] ??= []).push(p.ssn);
  }
  const ssnSeries = Object.entries(ssnByMonth)
    .map(([month, vals]) => ({
      t: Date.parse(`${month}-15T00:00:00Z`),
      ssn: vals.reduce((a, b) => a + b, 0) / vals.length,
    }))
    .sort((a, b) => a.t - b.t);

  const stormSeries = storms
    .map((s) => ({
      t: Date.parse(s.dst_min_time),
      abs_dst: s.abs_dst_min,
      storm_class: s.storm_class,
      storm_id: s.storm_id,
    }))
    .sort((a, b) => a.t - b.t);

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
            Solar-cycle context · 2014 → today
          </div>
          <div className="font-display text-base mt-1">
            SSN curve · {storms.length} storms in v3 catalog
          </div>
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono text-[var(--fg-muted)]">
          {Object.entries(CLASS_COLORS).map(([cls, c]) => (
            <span key={cls} className="flex items-center gap-1">
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ background: c }}
              />
              {cls}
            </span>
          ))}
        </div>
      </div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart margin={{ left: 0, right: 12, top: 6, bottom: 0 }}>
            <CartesianGrid stroke="#1c2236" strokeDasharray="3 3" />
            <XAxis
              dataKey="t"
              type="number"
              domain={["dataMin", "dataMax"]}
              scale="time"
              stroke="#8c93a8"
              fontSize={10}
              tickFormatter={(v) =>
                new Date(v).toISOString().slice(0, 7)
              }
              tickCount={10}
            />
            <YAxis
              yAxisId="left"
              stroke="#8c93a8"
              fontSize={10}
              label={{
                value: "SSN",
                angle: -90,
                position: "insideLeft",
                fill: "#8c93a8",
                fontSize: 10,
              }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#E63946"
              fontSize={10}
              domain={[0, 500]}
              label={{
                value: "|Dst| (nT)",
                angle: 90,
                position: "insideRight",
                fill: "#E63946",
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
                new Date(v as number).toISOString().slice(0, 10)
              }
              formatter={(value, name, ctx) => {
                if (name === "SSN") return [(value as number).toFixed(0), "SSN"];
                if (name === "|Dst|")
                  return [
                    `${(value as number).toFixed(0)} nT (${(ctx.payload as { storm_class?: string })?.storm_class})`,
                    "|Dst|",
                  ];
                return [value, name];
              }}
            />
            <Line
              yAxisId="left"
              data={ssnSeries}
              type="monotone"
              dataKey="ssn"
              stroke="#0FA3B1"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
              name="SSN"
            />
            <Scatter
              yAxisId="right"
              data={stormSeries}
              dataKey="abs_dst"
              name="|Dst|"
              fill="#E63946"
              isAnimationActive={false}
              shape={(props: {
                cx?: number;
                cy?: number;
                payload?: { storm_class: string; storm_id: number };
              }) => {
                const { cx, cy, payload } = props;
                if (cx == null || cy == null || !payload) return <g />;
                return (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={3}
                    fill={CLASS_COLORS[payload.storm_class] ?? "#fff"}
                    fillOpacity={0.7}
                    stroke="none"
                    style={{ cursor: "pointer" }}
                    onClick={() =>
                      router.push(
                        `${pathname}?selected=${payload.storm_id}`,
                        { scroll: false },
                      )
                    }
                  />
                );
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 text-[11px] text-[var(--fg-muted)] font-mono">
        click any storm dot → opens detail drawer (or use the catalog below)
      </div>
    </div>
  );
}
