"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const PHASE_COLOR: Record<string, string> = {
  none: "#0FA3B1",
  recovery: "#F7A072",
  main: "#E63946",
};

const PHASE_ORDER = ["none", "main", "recovery"];

export type PhaseRow = {
  storm_phase: string;
  n: number;
  positives: number;
  rate: number;
};

export function PhaseBars({ rows }: { rows: PhaseRow[] }) {
  const data = rows
    .filter((r) => r.storm_phase)
    .sort(
      (a, b) =>
        PHASE_ORDER.indexOf(a.storm_phase) - PHASE_ORDER.indexOf(b.storm_phase)
    )
    .map((r) => ({ ...r, ratePct: r.rate * 100 }));
  return (
    <div className="card p-5">
      <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
        EPB-positive rate by storm phase
      </div>
      <div className="font-display text-base mt-1 mb-3">
        Quiet vs. main vs. recovery
      </div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: 0, right: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1c2236" />
            <XAxis dataKey="storm_phase" stroke="#8c93a8" fontSize={11} />
            <YAxis stroke="#8c93a8" fontSize={11} unit="%" />
            <Tooltip
              contentStyle={{
                background: "#0e1320",
                border: "1px solid #1c2236",
                borderRadius: 8,
                color: "#f5f6f8",
                fontSize: 12,
              }}
              formatter={(v: number, _: string, payload) => {
                const p = payload as unknown as { payload: PhaseRow };
                return [
                  `${(v as number).toFixed(2)} %`,
                  `n = ${p.payload.n.toLocaleString()}`,
                ];
              }}
            />
            <Bar dataKey="ratePct">
              {data.map((d) => (
                <Cell key={d.storm_phase} fill={PHASE_COLOR[d.storm_phase] ?? "#6C757D"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-3 text-xs text-[var(--fg-muted)] max-w-prose">
        Storm-recovery windows show a higher EPB rate than quiet times — a
        signature of the disturbance dynamo electric field that lingers
        after the Dst minimum.
      </p>
    </div>
  );
}
