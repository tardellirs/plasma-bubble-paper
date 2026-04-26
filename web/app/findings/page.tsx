import Image from "next/image";
import { fetchOrNull } from "@/lib/api";

export const revalidate = 0;

type RatioBlock = {
  ratio: number;
  ci_lo: number;
  ci_hi: number;
  n_storms?: number;
  n_quiet_groups?: number;
};

type Q1 = {
  storm_rate_mean: number;
  quiet_rate_mean: number;
  ratio_storm_to_quiet: RatioBlock;
  n_intense_storms: number;
};

type LtBin = { mean: number; ci_lo: number; ci_hi: number; n: number };

type Q2 = {
  four_bin: Record<string, LtBin>;
  two_bin: { PRE_adjacent: LtBin; non_PRE: LtBin };
  two_bin_mannwhitney_test: { p_one_sided_greater: number };
  kruskal_wallis_4bin: { p: number };
};

type Q6Quartile = {
  quartile: number;
  n: number;
  phase_lo: number;
  phase_hi: number;
  rate_mean: number;
};

type Analysis = {
  available?: boolean;
  generated_at?: string;
  model_id_predicted_with?: string;
  Q1_storm_vs_quiet?: Q1;
  Q2_lt_amplification?: Q2;
  Q3_intensity_curve?: { spearman_rho: number; spearman_p: number; n_storms: number };
  Q4_recovery_duration?: { short_rate_mean: number; long_rate_mean: number; p_two_sided?: number };
  Q5_pre_storm_baseline?: { pre_rate: number; quiet_rate: number; elevation_ratio: number };
  Q6_solar_cycle?: { by_quartile: Q6Quartile[]; n_storms: number };
  Q7_inter_station_lag?: { peak_lag_min: number; peak_corr: number; pair: string[] };
};

export default async function FindingsPage() {
  const a = await fetchOrNull<Analysis>("/storms/v3/analysis");

  if (!a || !a.available) {
    return (
      <section className="max-w-4xl mx-auto px-6 py-16">
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Storms v3 · findings
        </p>
        <h1 className="font-display text-3xl font-semibold mt-3">
          Analysis not yet available.
        </h1>
        <p className="mt-4 text-[var(--fg-muted)]">
          The 11-yr storm-stratified ingest is still running. Once it
          finishes and{" "}
          <code className="font-mono text-xs text-[var(--accent)]">
            epb analysis storms-v3
          </code>{" "}
          writes <code>analysis_v3.json</code>, this page populates
          automatically.
        </p>
      </section>
    );
  }

  const q1 = a.Q1_storm_vs_quiet!;
  const q2 = a.Q2_lt_amplification!;
  const q6 = a.Q6_solar_cycle;

  const ratio = q1.ratio_storm_to_quiet;
  const preMean = q2.two_bin.PRE_adjacent.mean;
  const nonPreMean = q2.two_bin.non_PRE.mean;
  const preFactor = nonPreMean > 0 ? preMean / nonPreMean : Number.NaN;
  const cycleSpread =
    q6 && q6.by_quartile.length >= 2
      ? q6.by_quartile[q6.by_quartile.length - 1].rate_mean / Math.max(1e-9, q6.by_quartile[0].rate_mean)
      : null;

  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-12">
      <div>
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Storms v3 · interactive abstract
        </p>
        <h1 className="font-display text-3xl md:text-4xl font-semibold mt-3">
          What we found across 11 years of GNSS data.
        </h1>
        <p className="mt-3 max-w-2xl text-[var(--fg-muted)]">
          Single-page, journalist-friendly digest of the storm-stratified
          analysis. Every number is bootstrap-by-storm corrected; every
          figure is reproducible from the parquet and JSON files in this
          repo. Model:{" "}
          <code className="font-mono text-xs text-[var(--accent)]">
            {a.model_id_predicted_with}
          </code>
          .
        </p>
      </div>

      {/* Hero stats */}
      <div className="grid sm:grid-cols-3 gap-4">
        <BigStat
          label="EPB rate during storm vs quiet"
          value={`${ratio.ratio.toFixed(2)}×`}
          sub={`95% CI [${ratio.ci_lo.toFixed(2)}, ${ratio.ci_hi.toFixed(2)}] · n=${ratio.n_storms} storms`}
          accent
        />
        <BigStat
          label="PRE-adjacent vs non-PRE storms"
          value={Number.isFinite(preFactor) ? `${preFactor.toFixed(2)}×` : "n/a"}
          sub={`Mann-Whitney p = ${q2.two_bin_mannwhitney_test.p_one_sided_greater.toFixed(3)}`}
        />
        <BigStat
          label="Solar-cycle Q4 / Q1 rate ratio"
          value={cycleSpread != null ? `${cycleSpread.toFixed(2)}×` : "n/a"}
          sub={q6 ? `n=${q6.n_storms} storms across ${q6.by_quartile.length} F10.7 quartiles` : ""}
        />
      </div>

      {/* Q1 storm vs quiet */}
      <section>
        <h2 className="font-display text-xl font-semibold">
          Q1 — Storm vs quiet rate
        </h2>
        <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
          Storm-time EPB rate is{" "}
          <span className="text-white/90 font-mono">
            {q1.storm_rate_mean.toFixed(3)}
          </span>{" "}
          (per 10-min night-time window), versus quiet baseline{" "}
          <span className="text-white/90 font-mono">
            {q1.quiet_rate_mean.toFixed(3)}
          </span>
          . Bootstrap-by-storm 95% CI on the ratio:{" "}
          <span className="text-white/90 font-mono">
            [{ratio.ci_lo.toFixed(2)}, {ratio.ci_hi.toFixed(2)}]
          </span>
          .
        </p>
        <FigImage src="/api/storms/v3/figure/fig12_storm_vs_quiet_v3" alt="Storm vs quiet rate" />
      </section>

      {/* Q2 LT polar */}
      <section>
        <h2 className="font-display text-xl font-semibold">
          Q2 — Sunset (PRE) timing amplification
        </h2>
        <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
          Storms whose Dst minimum lands in the 17–22 LT window over the
          Brazilian sector show a {Number.isFinite(preFactor) ? `${preFactor.toFixed(2)}×` : "—"}{" "}
          higher EPB rate than storms minimising at other LTs. One-sided
          Mann-Whitney p ={" "}
          <span className="text-white/90 font-mono">
            {q2.two_bin_mannwhitney_test.p_one_sided_greater.toFixed(3)}
          </span>
          .
        </p>
        <FigImage src="/api/storms/v3/figure/fig13_storm_lt_polar" alt="LT polar plot" />
      </section>

      {/* Q3 intensity */}
      {a.Q3_intensity_curve && (
        <section>
          <h2 className="font-display text-xl font-semibold">
            Q3 — Intensity response
          </h2>
          <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
            Spearman ρ between |Dst|-min and per-storm EPB rate ={" "}
            <span className="text-white/90 font-mono">
              {a.Q3_intensity_curve.spearman_rho.toFixed(2)}
            </span>{" "}
            (p ={" "}
            <span className="text-white/90 font-mono">
              {a.Q3_intensity_curve.spearman_p.toFixed(3)}
            </span>
            ).
          </p>
          <FigImage src="/api/storms/v3/figure/fig14_intensity_curve" alt="Intensity curve" />
        </section>
      )}

      {/* Citation block */}
      <div className="card p-6 max-w-prose">
        <h2 className="font-display text-xl font-semibold">Cite</h2>
        <pre className="mt-3 bg-black/40 p-3 text-xs overflow-auto">
{`@article{plasmabubble2026,
  title  = {Storm-stratified Equatorial Plasma Bubble detection over Brazil},
  author = {Tardelli, R. and Picanço, G. and others},
  year   = {2026},
  note   = {in prep.}
}`}
        </pre>
        <a
          className="mt-4 inline-block text-sm text-[var(--accent)] underline"
          href="https://github.com/tardellirs/plasma-bubble-paper/blob/main/docs/results-storms-v3.md"
          target="_blank"
          rel="noreferrer"
        >
          Full report on GitHub ↗
        </a>
      </div>
    </section>
  );
}

function BigStat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className={`card p-6 ${accent ? "ring-1 ring-[var(--accent)]/40" : ""}`}>
      <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
        {label}
      </div>
      <div className={`mt-2 font-display text-3xl ${accent ? "text-[var(--accent)]" : ""}`}>
        {value}
      </div>
      {sub && <div className="mt-2 text-xs text-[var(--fg-muted)]">{sub}</div>}
    </div>
  );
}

function FigImage({ src, alt }: { src: string; alt: string }) {
  return (
    <div className="mt-4 rounded-md border border-[#1c2236] overflow-hidden bg-[#0a0e1a]">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} className="block w-full h-auto" />
    </div>
  );
}
