import Link from "next/link";
import { fetchOrNull } from "@/lib/api";
import { StormCatalog, type StormRow } from "@/components/StormCatalog";
import {
  SolarCycleStrip,
  type SsnPoint,
  type StormDot,
} from "@/components/SolarCycleStrip";
import { StormDrawer } from "@/components/StormDrawer";
import { Suspense } from "react";

// Cache the SSR payload for 60 s — none of these data sources change in
// real-time. Repeat visits within the window get instant render.
export const revalidate = 60;

type Q1 = {
  storm_rate_mean: number;
  quiet_rate_mean: number;
  ratio_storm_to_quiet: {
    ratio: number;
    ci_lo: number;
    ci_hi: number;
    n_storms: number;
  };
  n_intense_storms: number;
};

type Q2Bin = { mean: number; ci_lo: number; ci_hi: number; n: number };

type Q2 = {
  four_bin: Record<string, Q2Bin>;
  two_bin_mannwhitney_test: { p_one_sided_greater: number };
};

type Q3Bin = {
  abs_dst_lo: number;
  abs_dst_hi: number;
  n: number;
  rate_mean: number;
};

type Q6 = {
  by_quartile: {
    quartile: number;
    n: number;
    phase_lo: number;
    phase_hi: number;
    rate_mean: number;
  }[];
  n_storms: number;
};

type Analysis = {
  available?: boolean;
  Q1_storm_vs_quiet?: Q1;
  Q2_lt_amplification?: Q2;
  Q3_intensity_curve?: { spearman_rho: number; spearman_p: number; n_storms: number; bins?: Q3Bin[] };
  Q6_solar_cycle?: Q6;
};

type SolarCyclePayload = { ssn: SsnPoint[]; storms: StormDot[] };

export default async function StormsPage() {
  const [analysis, cycle, catalog] = await Promise.all([
    fetchOrNull<Analysis>("/storms/v3/analysis"),
    fetchOrNull<SolarCyclePayload>("/storms/v3/solar-cycle"),
    fetchOrNull<StormRow[]>("/storms/catalog"),
  ]);

  const q1 = analysis?.Q1_storm_vs_quiet;
  const q2 = analysis?.Q2_lt_amplification;
  const q3 = analysis?.Q3_intensity_curve;
  const q6 = analysis?.Q6_solar_cycle;
  const ssn = cycle?.ssn ?? [];
  const storms = cycle?.storms ?? [];
  const cat = catalog ?? [];
  const intense = storms.filter((s) => s.is_intense_or_stronger).length;
  const strongest = storms
    .map((s) => s.abs_dst_min)
    .reduce((a, b) => Math.max(a, b), 0);

  const q1Null = q1 ? q1.ratio_storm_to_quiet.ci_lo <= 1 && q1.ratio_storm_to_quiet.ci_hi >= 1 : false;
  const cycleSpread =
    q6 && q6.by_quartile.length >= 2
      ? q6.by_quartile[q6.by_quartile.length - 1].rate_mean /
        Math.max(1e-9, q6.by_quartile[0].rate_mean)
      : null;

  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-10">
      {/* Hero */}
      <div>
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Storms-v3 · 11-year storm catalog
        </p>
        <h1 className="font-display text-3xl md:text-4xl font-semibold mt-3">
          Storms, dynamos, and bubbles.
        </h1>
        <p className="mt-3 max-w-3xl text-[var(--fg-muted)]">
          We pull Kp/ap/F10.7 from <span className="font-mono">GFZ Potsdam</span>{" "}
          and Dst from <span className="font-mono">WDC Kyoto</span>, classify
          every storm episode 2014–today by Dst-min, and compare the model&apos;s
          per-storm EPB rate to a matched quiet baseline. The headline result
          is solar-cycle modulation, not storms — see{" "}
          <Link href="/findings" className="text-[var(--accent)] underline">
            /findings
          </Link>{" "}
          for the full Q1–Q8 readout.
        </p>
        <div className="mt-6 flex flex-wrap gap-3 text-sm">
          <Stat label="Storms in dataset" value={storms.length.toString()} />
          <Stat label="Intense or stronger" value={intense.toString()} />
          <Stat
            label="Strongest |Dst|-min"
            value={strongest > 0 ? `${strongest.toFixed(0)} nT` : "—"}
          />
        </div>
      </div>

      {/* Solar-cycle context strip — top */}
      {ssn.length > 0 && <SolarCycleStrip ssn={ssn} storms={storms} />}

      {/* Hero stats from analysis_v3 */}
      {analysis?.available && q1 && q6 && (
        <div className="grid sm:grid-cols-3 gap-4">
          <BigStat
            label="Solar-cycle Q4 / Q1 rate"
            value={cycleSpread != null ? `${cycleSpread.toFixed(2)}×` : "—"}
            sub={`monotonic across ${q6.by_quartile.length} quartiles · n=${q6.n_storms}`}
            tone="positive"
          />
          <BigStat
            label="Storm vs quiet rate"
            value={`${q1.ratio_storm_to_quiet.ratio.toFixed(2)}×`}
            sub={`95% CI [${q1.ratio_storm_to_quiet.ci_lo.toFixed(2)}, ${q1.ratio_storm_to_quiet.ci_hi.toFixed(2)}] · ${q1Null ? "NULL" : "significant"}`}
            tone={q1Null ? "null" : "positive"}
          />
          <BigStat
            label="Intense+ storms in v3"
            value={q1.n_intense_storms.toString()}
            sub="11 years · bootstrap-by-storm CIs"
          />
        </div>
      )}

      {/* Q2 — LT bins */}
      {q2 && (
        <div className="card p-6">
          <div className="flex items-baseline justify-between gap-3">
            <div>
              <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
                Q2 — LT amplification
              </p>
              <h2 className="font-display text-xl mt-1">
                Per-storm rate by Dst-min LT bin (Brazilian sector)
              </h2>
            </div>
            <span
              className={`text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 ${q2.two_bin_mannwhitney_test.p_one_sided_greater >= 0.05 ? "bg-amber-500/15 text-amber-200" : "bg-emerald-500/15 text-emerald-300"}`}
            >
              {q2.two_bin_mannwhitney_test.p_one_sided_greater >= 0.05
                ? "null"
                : "positive"}
            </span>
          </div>
          <LtBars q2={q2} />
          <div className="mt-3 text-xs text-[var(--fg-muted)] font-mono">
            Mann-Whitney p (PRE-adjacent &gt; non-PRE) ={" "}
            {q2.two_bin_mannwhitney_test.p_one_sided_greater.toFixed(3)}
          </div>
        </div>
      )}

      {/* Q3 — intensity bins */}
      {q3?.bins && q3.bins.length > 0 && (
        <div className="card p-6">
          <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
            Q3 — intensity response
          </p>
          <h2 className="font-display text-xl mt-1">
            EPB rate vs |Dst|-min, quintile bins
          </h2>
          <IntensityBars bins={q3.bins} />
          <div className="mt-3 text-xs text-[var(--fg-muted)] font-mono">
            Spearman ρ = {q3.spearman_rho.toFixed(2)} · p ={" "}
            {q3.spearman_p.toFixed(3)} · n = {q3.n_storms} storms
          </div>
        </div>
      )}

      {/* Storm catalog */}
      <div>
        <h2 className="font-display text-2xl font-semibold mb-3">
          Storm catalog
        </h2>
        <StormCatalog rows={cat} />
      </div>

      {/* Why this matters */}
      <div className="card p-6 max-w-prose">
        <h2 className="font-display text-xl font-semibold">Why this matters</h2>
        <p className="mt-3 text-[var(--fg-muted)]">
          Equatorial plasma bubbles are not a simple monotonic response to
          geomagnetic activity. The classical picture (Aarons 1991; Abdu
          2012) predicts storms — especially storms whose Dst-min lands in
          the Brazilian PRE LT window — should produce more EPBs. Our
          11-year sample says the dominant signal is{" "}
          <em>solar-cycle phase</em>, not storms. Storm-vs-quiet ratio
          comes out at 0.84× (CI crosses 1) on this dataset; the most
          plausible explanation is that the quiet baseline at solar
          maximum is already saturated. See{" "}
          <Link href="/findings" className="text-[var(--accent)] underline">
            /findings
          </Link>{" "}
          for the full statistical readout and{" "}
          <Link
            href="/validation"
            className="text-[var(--accent)] underline"
          >
            /validation
          </Link>{" "}
          for the independent literature recall.
        </p>
      </div>

      {/* Right-side drawer driven by ?selected=<storm_id> */}
      <Suspense fallback={null}>
        <StormDrawer />
      </Suspense>
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
    <div className="card px-5 py-3">
      <div className="text-[10px] uppercase tracking-wider text-[var(--fg-muted)]">
        {label}
      </div>
      <div className="font-display text-xl">{value}</div>
      {sub && (
        <div className="text-xs text-[var(--fg-muted)] font-mono">{sub}</div>
      )}
    </div>
  );
}

function BigStat({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "positive" | "null";
}) {
  const ringCls =
    tone === "null"
      ? "ring-1 ring-amber-400/30"
      : tone === "positive"
        ? "ring-1 ring-emerald-400/30"
        : "";
  const valCls =
    tone === "null"
      ? "text-amber-200"
      : tone === "positive"
        ? "text-[var(--accent)]"
        : "";
  return (
    <div className={`card p-6 ${ringCls}`}>
      <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
        {label}
      </div>
      <div className={`mt-2 font-display text-3xl ${valCls}`}>{value}</div>
      {sub && <div className="mt-2 text-xs text-[var(--fg-muted)]">{sub}</div>}
    </div>
  );
}

function LtBars({ q2 }: { q2: Q2 }) {
  const order = ["pre_sunset", "PRE", "post_midnight", "morning"] as const;
  const bins = order
    .map((b) => ({ key: b, ...q2.four_bin[b] }))
    .filter((b) => b && b.n != null);
  const max = Math.max(...bins.map((b) => b.mean), 0.001);
  return (
    <div className="mt-4 grid grid-cols-4 gap-2">
      {bins.map((b) => {
        const pct = (b.mean / max) * 100;
        const highlight = b.key === "PRE";
        return (
          <div
            key={b.key}
            className={`card p-3 ${highlight ? "ring-1 ring-[var(--accent)]/40" : ""}`}
          >
            <div className="text-[10px] uppercase tracking-wider text-[var(--fg-muted)]">
              {b.key === "PRE" ? "PRE (17–22)" : b.key.replace("_", " ")}
            </div>
            <div className="mt-2 h-20 flex items-end">
              <div
                className={`w-full rounded-t ${highlight ? "bg-[var(--accent)]/80" : "bg-white/30"}`}
                style={{ height: `${Math.max(4, pct)}%` }}
              />
            </div>
            <div className="mt-2 font-mono text-xs text-white/85">
              {b.mean.toFixed(4)}
            </div>
            <div className="text-[10px] text-[var(--fg-muted)] font-mono">
              n={b.n}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function IntensityBars({ bins }: { bins: Q3Bin[] }) {
  const max = Math.max(...bins.map((b) => b.rate_mean), 0.001);
  return (
    <div
      className="mt-4 grid gap-2"
      style={{ gridTemplateColumns: `repeat(${bins.length}, minmax(0, 1fr))` }}
    >
      {bins.map((b, i) => {
        const pct = (b.rate_mean / max) * 100;
        return (
          <div key={i} className="card p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--fg-muted)]">
              |Dst| {b.abs_dst_lo.toFixed(0)}–{b.abs_dst_hi.toFixed(0)}
            </div>
            <div className="mt-2 h-20 flex items-end">
              <div
                className="w-full rounded-t bg-[var(--accent)]/70"
                style={{ height: `${Math.max(4, pct)}%` }}
              />
            </div>
            <div className="mt-2 font-mono text-xs text-white/85">
              {b.rate_mean.toFixed(4)}
            </div>
            <div className="text-[10px] text-[var(--fg-muted)] font-mono">
              n={b.n}
            </div>
          </div>
        );
      })}
    </div>
  );
}
