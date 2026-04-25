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

export type SuperposedRow = {
  bin: number;
  n: number;
  positives: number;
  rate: number;
};

export function SuperposedEpoch({ rows }: { rows: SuperposedRow[] }) {
  const data = rows
    .map((r) => ({ ...r, ratePct: (r.rate ?? 0) * 100 }))
    .sort((a, b) => a.bin - b.bin);
  return (
    <div className="card p-5">
      <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
        Superposed-epoch analysis
      </div>
      <div className="font-display text-base mt-1 mb-3">
        EPB rate vs hours from Dst minimum
      </div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data}>
            <XAxis
              dataKey="bin"
              stroke="#8c93a8"
              fontSize={10}
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(v) => `${v}h`}
            />
            <YAxis stroke="#8c93a8" fontSize={10} unit="%" />
            <Tooltip
              contentStyle={{
                background: "#0e1320",
                border: "1px solid #1c2236",
                borderRadius: 8,
                color: "#f5f6f8",
                fontSize: 12,
              }}
              labelFormatter={(v) => `t = ${v}h`}
              formatter={(v: number, _: string, p) => {
                const r = (p as unknown as { payload: SuperposedRow }).payload;
                return [`${(v as number).toFixed(2)} %`, `n = ${r.n.toLocaleString()}`];
              }}
            />
            <ReferenceLine x={0} stroke="#E63946" strokeDasharray="3 3" />
            <Area
              type="monotone"
              dataKey="ratePct"
              stroke="#0FA3B1"
              strokeWidth={2}
              fill="#0FA3B1"
              fillOpacity={0.18}
              isAnimationActive={false}
              name="Rate"
            />
            <Line
              type="monotone"
              dataKey="ratePct"
              stroke="#0FA3B1"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
