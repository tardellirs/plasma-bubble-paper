import Link from "next/link";
import { fetchOrNull } from "@/lib/api";

export const revalidate = 0;

type Quartile = {
  quartile: number;
  n: number;
  phase_lo: number;
  phase_hi: number;
  rate_mean: number;
};

type ForecastResponse = {
  available?: boolean;
  reason?: string;
  generated_at?: string;
  lookahead_hours?: number;
  current?: {
    time: string;
    f107_obs: number;
    ap_daily: number | null;
    dst_latest_hour: number | null;
  };
  cycle?: {
    phase: number | null;
    matched_quartile: Quartile | null;
    all_quartiles: Quartile[];
  };
  predicted_rate_per_window?: number | null;
  risk_band?: "low" | "moderate" | "high" | "extreme";
  dst_24h?: { time: string; dst: number }[];
  method?: string;
};

const BAND_STYLE: Record<
  NonNullable<ForecastResponse["risk_band"]>,
  { label: string; cls: string; ringCls: string }
> = {
  low: {
    label: "LOW",
    cls: "text-emerald-300",
    ringCls: "ring-1 ring-emerald-400/40",
  },
  moderate: {
    label: "MODERATE",
    cls: "text-amber-200",
    ringCls: "ring-1 ring-amber-400/40",
  },
  high: {
    label: "HIGH",
    cls: "text-rose-200",
    ringCls: "ring-1 ring-rose-400/50",
  },
  extreme: {
    label: "EXTREME",
    cls: "text-violet-200",
    ringCls: "ring-1 ring-violet-400/60",
  },
};

export default async function ForecastPage() {
  const f = await fetchOrNull<ForecastResponse>("/forecast/epb-risk?lookahead_hours=6");

  if (!f || !f.available) {
    return (
      <section className="max-w-4xl mx-auto px-6 py-16">
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Forecast · climatological context
        </p>
        <h1 className="font-display text-3xl font-semibold mt-3">
          Forecast not available.
        </h1>
        <p className="mt-4 text-[var(--fg-muted)]">
          {f?.reason ??
            "The forecast endpoint needs analysis_v3.json + a recent space-weather parquet to compute the climatological risk band."}
        </p>
      </section>
    );
  }

  const band = f.risk_band ?? "low";
  const style = BAND_STYLE[band];
  const cur = f.current;
  const cyc = f.cycle;
  const dstSpark = (f.dst_24h ?? []).map((p) => p.dst);
  const dstMin = dstSpark.length ? Math.min(...dstSpark) : null;

  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-10">
      <div>
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Forecast · climatological context
        </p>
        <h1 className="font-display text-3xl md:text-4xl font-semibold mt-3">
          Brazilian-sector EPB risk · next {f.lookahead_hours ?? 6} h.
        </h1>
        <p className="mt-3 max-w-3xl text-[var(--fg-muted)]">
          This is{" "}
          <strong className="text-white/85">
            not a real-time per-station prediction
          </strong>{" "}
          — we don&apos;t have live ROTI / ΔTEC / SIDX ingest. Instead, we
          combine the current geomagnetic state (Dst / Kp / F10.7) with
          the per-quartile EPB rates from the storms-v3 solar-cycle
          analysis (Q6) to produce a coarse climatological risk band.
          Use it as situational awareness, not as a per-station nowcast.
        </p>
      </div>

      {/* Hero gauge */}
      <div className={`card p-8 ${style.ringCls}`}>
        <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
          Current EPB risk band
        </div>
        <div className={`mt-2 font-display text-6xl ${style.cls}`}>
          {style.label}
        </div>
        {f.predicted_rate_per_window != null && (
          <div className="mt-4 text-sm text-[var(--fg-muted)]">
            Climatological per-window rate at current cycle phase:{" "}
            <span className="text-white/85 font-mono">
              {(f.predicted_rate_per_window * 100).toFixed(2)}%
            </span>{" "}
            (one 10-min night-time window in this band has this probability
            of containing an EPB based on Q6 historical rates).
          </div>
        )}
        <div className="mt-3 text-xs text-[var(--fg-muted)] font-mono">
          {f.method}
        </div>
      </div>

      {/* Current state */}
      <div className="grid sm:grid-cols-3 gap-4">
        <Stat
          label="Current Dst (last hour)"
          value={
            cur?.dst_latest_hour != null
              ? `${cur.dst_latest_hour.toFixed(0)} nT`
              : "—"
          }
          sub={dstMin != null ? `24h min: ${dstMin.toFixed(0)} nT` : undefined}
        />
        <Stat
          label="F10.7 obs"
          value={cur?.f107_obs != null ? cur.f107_obs.toFixed(1) : "—"}
          sub={
            cyc?.phase != null
              ? `cycle phase ${cyc.phase.toFixed(2)}`
              : undefined
          }
        />
        <Stat
          label="Ap daily"
          value={cur?.ap_daily != null ? cur.ap_daily.toFixed(0) : "—"}
        />
      </div>

      {/* Cycle quartile context */}
      {cyc?.all_quartiles && cyc.all_quartiles.length > 0 && (
        <div className="card p-6">
          <h2 className="font-display text-xl font-semibold">
            Where we are in the solar cycle
          </h2>
          <p className="mt-2 text-sm text-[var(--fg-muted)] max-w-prose">
            Q6 split the 11-yr storm sample into quartiles of F10.7 phase.
            The current phase (
            <span className="font-mono text-white/85">
              {cyc.phase != null ? cyc.phase.toFixed(2) : "—"}
            </span>
            ) lands in the highlighted quartile below.
          </p>
          <div className="mt-4 grid grid-cols-4 gap-2">
            {cyc.all_quartiles.map((q) => {
              const isMatch =
                cyc.matched_quartile?.quartile === q.quartile;
              const max = Math.max(
                ...cyc.all_quartiles.map((x) => x.rate_mean),
                0.001,
              );
              const pct = (q.rate_mean / max) * 100;
              return (
                <div
                  key={q.quartile}
                  className={`card p-3 ${isMatch ? "ring-1 ring-[var(--accent)]/60" : ""}`}
                >
                  <div className="text-[10px] uppercase tracking-wider text-[var(--fg-muted)]">
                    Q{q.quartile + 1} · {q.phase_lo.toFixed(2)}–
                    {q.phase_hi.toFixed(2)}
                  </div>
                  <div className="mt-2 h-16 flex items-end">
                    <div
                      className={`w-full rounded-t ${isMatch ? "bg-[var(--accent)]/80" : "bg-white/30"}`}
                      style={{ height: `${Math.max(4, pct)}%` }}
                    />
                  </div>
                  <div className="mt-2 font-mono text-xs text-white/85">
                    rate {q.rate_mean.toFixed(4)}
                  </div>
                  <div className="text-[10px] text-[var(--fg-muted)] font-mono">
                    n={q.n}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Caveats */}
      <div className="card p-6 max-w-prose">
        <h2 className="font-display text-xl font-semibold">Caveats</h2>
        <ul className="mt-3 space-y-2 text-sm text-[var(--fg-muted)]">
          <li>
            <strong className="text-white/85">No real-time GNSS.</strong>{" "}
            We don&apos;t ingest IBGE RINEX live; this gauge does NOT
            run the model on current data. It uses the climatological
            per-quartile rate from Q6 instead.
          </li>
          <li>
            <strong className="text-white/85">Dst lags ~1 hour.</strong>{" "}
            WDC Kyoto realtime Dst is the most recent hourly value
            available; we don&apos;t forward-project a trajectory yet.
          </li>
          <li>
            <strong className="text-white/85">Bands are coarse.</strong>{" "}
            Mapping continuous Dst + climatological rate to four bands
            is intentionally simple. For a real per-station nowcast we
            would need the live ingest (Phase 4 of the original plan).
          </li>
        </ul>
        <Link
          className="mt-4 inline-block text-sm text-[var(--accent)] underline"
          href="/findings"
        >
          See /findings for the underlying Q6 cycle modulation result →
        </Link>
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
        {label}
      </div>
      <div className="mt-1 font-display text-2xl">{value}</div>
      {sub && <div className="mt-1 text-xs text-[var(--fg-muted)] font-mono">{sub}</div>}
    </div>
  );
}
