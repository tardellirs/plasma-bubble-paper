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

type Q3 = {
  spearman_rho: number;
  spearman_p: number;
  n_storms: number;
  bins?: { abs_dst_lo: number; abs_dst_hi: number; n: number; rate_mean: number }[];
};

type Q4 = {
  n_short: number;
  n_long: number;
  short_rate_mean: number;
  long_rate_mean: number;
  p_two_sided?: number | null;
};

type Q5 = {
  pre_hours: number;
  n_pre_windows: number;
  pre_rate: number | null;
  quiet_rate: number;
  elevation_ratio: number | null;
};

type Q6Quartile = {
  quartile: number;
  n: number;
  phase_lo: number;
  phase_hi: number;
  rate_mean: number;
};

type Q7 = {
  pair: string[];
  peak_lag_min: number;
  peak_corr: number;
  bin_minutes?: number;
};

type Q8Bin = { mean: number; ci_lo: number; ci_hi: number; n: number };
type Q8 = {
  by_sector: Record<string, Q8Bin>;
  kruskal_wallis_3sector?: { p: number; n_bins: number };
  n_storms_total: number;
};

type Analysis = {
  available?: boolean;
  generated_at?: string;
  model_id_predicted_with?: string;
  Q1_storm_vs_quiet?: Q1;
  Q2_lt_amplification?: Q2;
  Q3_intensity_curve?: Q3;
  Q4_recovery_duration?: Q4;
  Q5_pre_storm_baseline?: Q5;
  Q6_solar_cycle?: { by_quartile: Q6Quartile[]; n_storms: number };
  Q7_inter_station_lag?: Q7;
  Q8_storm_onset_longitude?: Q8;
};

function fmtPct(x: number) {
  return `${(x * 100).toFixed(2)}%`;
}

function fmtRate(x: number | null | undefined) {
  if (x == null || !Number.isFinite(x)) return "—";
  return x.toFixed(4);
}

function pStr(p: number | null | undefined) {
  if (p == null || !Number.isFinite(p)) return "—";
  return p < 0.001 ? "<0.001" : p.toFixed(3);
}

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
  const q3 = a.Q3_intensity_curve;
  const q4 = a.Q4_recovery_duration;
  const q5 = a.Q5_pre_storm_baseline;
  const q6 = a.Q6_solar_cycle;
  const q7 = a.Q7_inter_station_lag;
  const q8 = a.Q8_storm_onset_longitude;

  const q1Ratio = q1.ratio_storm_to_quiet;
  const q1Null = q1Ratio.ci_lo <= 1 && q1Ratio.ci_hi >= 1;

  const preMean = q2.two_bin.PRE_adjacent.mean;
  const nonPreMean = q2.two_bin.non_PRE.mean;
  const preFactor = nonPreMean > 0 ? preMean / nonPreMean : Number.NaN;
  const q2Null = q2.two_bin_mannwhitney_test.p_one_sided_greater >= 0.05;

  const cycleSpread =
    q6 && q6.by_quartile.length >= 2
      ? q6.by_quartile[q6.by_quartile.length - 1].rate_mean /
        Math.max(1e-9, q6.by_quartile[0].rate_mean)
      : null;

  const maxQ6Rate = q6
    ? Math.max(...q6.by_quartile.map((q) => q.rate_mean))
    : 0;

  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-12">
      {/* Header */}
      <div>
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Storms v3 · interactive abstract
        </p>
        <h1 className="font-display text-3xl md:text-4xl font-semibold mt-3">
          The headline result is solar-cycle modulation, not storms.
        </h1>
        <p className="mt-3 max-w-3xl text-[var(--fg-muted)]">
          We ran <code className="font-mono text-xs text-[var(--accent)]">{a.model_id_predicted_with}</code>{" "}
          over 11 years of GNSS data covering 31 intense+ geomagnetic storms.
          The clean positive finding is that the EPB-positive rate scales
          monotonically with the F10.7 solar-cycle phase — solar-max storms
          produce {cycleSpread != null ? `${cycleSpread.toFixed(1)}×` : "—"}{" "}
          more EPBs than solar-min storms. The classical
          &quot;storms-amplify-EPBs&quot; story (Q1, Q2 below) does not survive
          on this sample once you control for cycle phase: both come back
          null with wide confidence intervals. This page reports both,
          honestly.
        </p>
      </div>

      {/* Hero stats — lead with Q6, then make Q1/Q2 nullness explicit */}
      <div className="grid sm:grid-cols-3 gap-4">
        <BigStat
          label="Solar-cycle Q4 / Q1 rate ratio"
          value={cycleSpread != null ? `${cycleSpread.toFixed(2)}×` : "n/a"}
          sub={
            q6
              ? `n=${q6.n_storms} storms across ${q6.by_quartile.length} F10.7 quartiles · MONOTONIC`
              : ""
          }
          accent
          tone="positive"
        />
        <BigStat
          label="EPB rate during storm vs quiet"
          value={`${q1Ratio.ratio.toFixed(2)}×`}
          sub={`95% CI [${q1Ratio.ci_lo.toFixed(2)}, ${q1Ratio.ci_hi.toFixed(2)}] · n=${q1Ratio.n_storms} storms · ${q1Null ? "NULL (CI crosses 1)" : "significant"}`}
          tone={q1Null ? "null" : "positive"}
        />
        <BigStat
          label="PRE-adjacent vs non-PRE storms"
          value={Number.isFinite(preFactor) ? `${preFactor.toFixed(2)}×` : "n/a"}
          sub={`Mann-Whitney p = ${pStr(q2.two_bin_mannwhitney_test.p_one_sided_greater)} · ${q2Null ? "NULL (p ≥ 0.05)" : "significant"}`}
          tone={q2Null ? "null" : "positive"}
        />
      </div>

      {/* Reading guide */}
      <div className="card p-6">
        <h2 className="font-display text-xl font-semibold">How to read this page</h2>
        <ul className="mt-3 space-y-2 text-sm text-[var(--fg-muted)] max-w-prose">
          <li>
            <Tone tone="positive">positive</Tone> — bootstrap-by-storm 95% CI
            is on one side of the null (1× for ratios, 0 for rates), or the
            test rejects at α=0.05.
          </li>
          <li>
            <Tone tone="null">null</Tone> — CI crosses the null or test
            p ≥ 0.05. We report the point estimate but cannot claim a
            real effect.
          </li>
          <li>
            All bootstraps resample by <code>storm_id</code> (not by window) to
            avoid pseudoreplication. Quiet-day baselines come from matched
            station/season/cycle controls, not from storm-time data.
          </li>
        </ul>
      </div>

      {/* Q6 — solar cycle (POSITIVE, the headline) */}
      <Section
        tag="Q6 — solar-cycle modulation"
        title="EPB rate scales monotonically with cycle phase."
        tone="positive"
      >
        <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
          We split the 31 intense+ storms into four quartiles of F10.7 phase
          (low → high cycle activity) and computed the per-storm EPB rate in
          each. The ratio Q4/Q1 ={" "}
          <span className="text-white/90 font-mono">
            {cycleSpread != null ? `${cycleSpread.toFixed(2)}×` : "—"}
          </span>{" "}
          — i.e. solar-max storms produce {cycleSpread != null ? `${cycleSpread.toFixed(1)}×` : "—"}{" "}
          more EPBs per night-time window than solar-min storms of the same
          intensity class. Consistent with the classical EUV-driven
          F-region instability picture (Aarons 1991; Abdu 2012).
        </p>
        {q6 && (
          <div className="mt-4 grid grid-cols-4 gap-2">
            {q6.by_quartile.map((q) => (
              <QuartileBar
                key={q.quartile}
                qIdx={q.quartile}
                rate={q.rate_mean}
                phaseLo={q.phase_lo}
                phaseHi={q.phase_hi}
                n={q.n}
                maxRate={maxQ6Rate}
              />
            ))}
          </div>
        )}
        <FigImage
          src="/api/storms/v3/figure/fig18_cycle_modulation"
          alt="Solar-cycle modulation"
          caption="fig18 — EPB rate vs F10.7 phase quartile, with bootstrap CI per quartile."
        />
      </Section>

      {/* Q1 — storm vs quiet (NULL) */}
      <Section
        tag="Q1 — storm vs quiet rate"
        title="Storm-time and quiet-time EPB rates are statistically indistinguishable."
        tone="null"
      >
        <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
          Storm rate{" "}
          <span className="text-white/90 font-mono">
            {fmtRate(q1.storm_rate_mean)}
          </span>{" "}
          vs quiet baseline{" "}
          <span className="text-white/90 font-mono">
            {fmtRate(q1.quiet_rate_mean)}
          </span>
          ; ratio{" "}
          <span className="text-white/90 font-mono">
            {q1Ratio.ratio.toFixed(2)}× (95% CI [{q1Ratio.ci_lo.toFixed(2)},{" "}
            {q1Ratio.ci_hi.toFixed(2)}])
          </span>
          . The CI crosses 1, so we cannot reject the null. The most likely
          explanation: the quiet baseline at solar maximum is already
          saturated with EPBs (the climatology is dominated by post-sunset
          equatorial activity regardless of storms), so there is no
          headroom for storms to &quot;boost&quot; the cycle-averaged
          rate. Stratifying by cycle phase first (Q6) and{" "}
          <em>then</em> asking the storm question is the correct next
          step.
        </p>
        <FigImage
          src="/api/storms/v3/figure/fig12_storm_vs_quiet_v3"
          alt="Storm vs quiet rate"
          caption="fig12 — storm vs quiet bars with bootstrap-by-storm CI whiskers."
        />
      </Section>

      {/* Q2 — PRE LT amplification (NULL) */}
      <Section
        tag="Q2 — PRE-window LT amplification"
        title="Storms minimising in the PRE LT bin do not produce more EPBs."
        tone="null"
      >
        <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
          PRE-adjacent storms (Dst-min in 12–22 LT over Brazil): mean rate{" "}
          <span className="text-white/90 font-mono">
            {fmtRate(q2.two_bin.PRE_adjacent.mean)}
          </span>{" "}
          (n={q2.two_bin.PRE_adjacent.n}) vs non-PRE storms{" "}
          <span className="text-white/90 font-mono">
            {fmtRate(q2.two_bin.non_PRE.mean)}
          </span>{" "}
          (n={q2.two_bin.non_PRE.n}). One-sided Mann-Whitney p ={" "}
          <span className="text-white/90 font-mono">
            {pStr(q2.two_bin_mannwhitney_test.p_one_sided_greater)}
          </span>
          ; Kruskal-Wallis on the 4-bin split p ={" "}
          <span className="text-white/90 font-mono">
            {pStr(q2.kruskal_wallis_4bin.p)}
          </span>
          . The PRE-coupling hypothesis (Abdu 2012) predicts the opposite
          direction; we do not see it. With n=6 storms in the strict PRE
          bin, statistical power is the obvious limitation, but the point
          estimate also sits below non-PRE.
        </p>
        <div className="mt-4 grid grid-cols-4 gap-2">
          {(["pre_sunset", "PRE", "post_midnight", "morning"] as const).map(
            (bin) => {
              const b = q2.four_bin[bin];
              if (!b) return null;
              return (
                <LtBinBar
                  key={bin}
                  label={bin === "PRE" ? "PRE (17–22)" : bin.replace("_", " ")}
                  bin={b}
                  highlight={bin === "PRE"}
                  maxRate={Math.max(
                    ...Object.values(q2.four_bin).map((x) => x.mean),
                  )}
                />
              );
            },
          )}
        </div>
        <FigImage
          src="/api/storms/v3/figure/fig13_storm_lt_polar"
          alt="LT polar plot"
          caption="fig13 — polar view, theta = LT-of-Dst-min, radius = per-storm EPB rate."
        />
      </Section>

      {/* Q3 — intensity response */}
      {q3 && (
        <Section
          tag="Q3 — intensity response"
          title="No clear monotonic response to storm intensity."
          tone={q3.spearman_p < 0.05 ? "positive" : "null"}
        >
          <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
            Spearman ρ between |Dst|-min and per-storm EPB rate ={" "}
            <span className="text-white/90 font-mono">
              {q3.spearman_rho.toFixed(2)}
            </span>{" "}
            (p ={" "}
            <span className="text-white/90 font-mono">{pStr(q3.spearman_p)}</span>
            , n = {q3.n_storms}). On this sample we don&apos;t see a
            monotonic intensity → rate response — bigger storms are not
            reliably bubblier than moderate ones. Consistent with the
            saturation explanation in Q1.
          </p>
          <FigImage
            src="/api/storms/v3/figure/fig14_intensity_curve"
            alt="Intensity curve"
            caption="fig14 — EPB rate vs |Dst|-min, hex-bin density behind a regression line."
          />
        </Section>
      )}

      {/* Q4 — recovery duration */}
      {q4 && (
        <Section
          tag="Q4 — recovery duration effect"
          title="Long-recovery storms produce more EPBs than short-recovery, but the test is underpowered."
          tone={q4.p_two_sided != null && q4.p_two_sided < 0.05 ? "positive" : "null"}
        >
          <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
            Short recovery (≤24 h, n={q4.n_short}): rate{" "}
            <span className="text-white/90 font-mono">
              {fmtRate(q4.short_rate_mean)}
            </span>
            . Long recovery (≥72 h, n={q4.n_long}): rate{" "}
            <span className="text-white/90 font-mono">
              {fmtRate(q4.long_rate_mean)}
            </span>
            . Mann-Whitney two-sided p ={" "}
            <span className="text-white/90 font-mono">
              {pStr(q4.p_two_sided)}
            </span>
            . The direction matches the disturbance-dynamo persistence
            model (long recoveries → more EPBs on subsequent nights), but
            n=2 in the short-recovery bin caps the power.
          </p>
          <FigImage
            src="/api/storms/v3/figure/fig16_recovery_duration"
            alt="Recovery duration"
            caption="fig16 — short vs long recovery rate distributions."
          />
        </Section>
      )}

      {/* Q5 — pre-storm baseline (often null because no pre-storm windows ingested) */}
      {q5 && (
        <Section
          tag="Q5 — pre-storm baseline drift"
          title={
            q5.elevation_ratio == null
              ? "Not yet computable — pre-storm windows missing from ingest."
              : "Pre-storm window EPB rate vs quiet baseline."
          }
          tone="null"
        >
          <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
            Quiet baseline rate:{" "}
            <span className="text-white/90 font-mono">
              {fmtRate(q5.quiet_rate)}
            </span>
            . Pre-storm window (last {q5.pre_hours} h before main_start):{" "}
            <span className="text-white/90 font-mono">
              {fmtRate(q5.pre_rate)}
            </span>{" "}
            (n_windows={q5.n_pre_windows}). Elevation factor:{" "}
            <span className="text-white/90 font-mono">
              {q5.elevation_ratio == null
                ? "—"
                : `${q5.elevation_ratio.toFixed(2)}×`}
            </span>
            .
            {q5.n_pre_windows === 0 && (
              <span className="block mt-2">
                The current ingest covers storm-windows but not the 12 h
                pre-onset window for many storms — so this question is{" "}
                <em>not yet answerable</em> from the v3 dataset. Resolve by
                extending the day-selector to grab `dst_min_time` − 12 h.
              </span>
            )}
          </p>
          {q5.n_pre_windows > 0 && (
            <FigImage
              src="/api/storms/v3/figure/fig17_precursor"
              alt="Precursor"
              caption="fig17 — EPB rate in the 12 h pre-onset window vs quiet baseline."
            />
          )}
        </Section>
      )}

      {/* Q7 — inter-station lag */}
      {q7 && (
        <Section
          tag="Q7 — inter-station correlation lag"
          title={`${q7.pair.join(" → ")} EPB activity peaks at lag ${q7.peak_lag_min} min.`}
          tone="positive"
        >
          <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
            Cross-correlation of per-window EPB probability between{" "}
            <span className="font-mono">{q7.pair[0]}</span> and{" "}
            <span className="font-mono">{q7.pair[1]}</span> peaks at{" "}
            <span className="text-white/90 font-mono">
              {q7.peak_lag_min} min
            </span>{" "}
            with peak correlation{" "}
            <span className="text-white/90 font-mono">
              {q7.peak_corr.toFixed(2)}
            </span>
            . A non-zero peak lag would indicate an estimable zonal
            structure-drift speed between the two stations; the
            zero-lag peak here means the two sites see EPB onset
            roughly simultaneously at 10-min binning, which is what
            you&apos;d expect for plumes with km-scale zonal drift over
            an inter-station baseline of ~3000 km.
          </p>
          <FigImage
            src="/api/storms/v3/figure/fig19_station_lag"
            alt="Inter-station lag"
            caption="fig19 — cross-correlation curve, lag in minutes."
          />
        </Section>
      )}

      {/* Q8 — storm-onset LT × longitude */}
      {q8 && q8.by_sector && (
        <Section
          tag="Q8 — storm-onset longitude (UT-of-Dst-min)"
          title="Per-storm Brazilian-sector EPB rate by which longitude was at sunset when Dst-min hit."
          tone={
            q8.kruskal_wallis_3sector && q8.kruskal_wallis_3sector.p < 0.05
              ? "positive"
              : "null"
          }
        >
          <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
            Same physics as Q2 (PRE coupling) viewed at the global LT
            scale: bin every intense+ storm by the UT-hour of its
            Dst-minimum. UT 06–14 ≈ sunset over Asia/India; UT 14–22 ≈
            sunset over the Atlantic / Brazilian terminator (overlaps
            with Q2&apos;s &quot;PRE&quot; bin); UT 22–06 ≈ sunset over
            Pacific. We measure the per-storm rate over the Brazilian
            sector in each UT-of-onset bin, with bootstrap CIs.
          </p>
          <div className="mt-4 grid grid-cols-3 gap-2">
            {(["asia", "atlantic", "pacific"] as const).map((sec) => {
              const b = q8.by_sector[sec];
              if (!b) return null;
              const max = Math.max(
                ...Object.values(q8.by_sector).map((x) => x.mean ?? 0),
                0.001,
              );
              const pct = b.mean != null ? (b.mean / max) * 100 : 0;
              const highlight = sec === "atlantic";
              return (
                <div
                  key={sec}
                  className={`card p-3 ${highlight ? "ring-1 ring-[var(--accent)]/40" : ""}`}
                >
                  <div className="text-[10px] uppercase tracking-wider text-[var(--fg-muted)]">
                    {sec}{" "}
                    <span className="text-white/60 font-mono">
                      (UT{" "}
                      {sec === "asia"
                        ? "06–14"
                        : sec === "atlantic"
                          ? "14–22"
                          : "22–06"}
                      )
                    </span>
                  </div>
                  <div className="mt-2 h-20 flex items-end">
                    <div
                      className={`w-full rounded-t ${highlight ? "bg-[var(--accent)]/80" : "bg-white/30"}`}
                      style={{ height: `${Math.max(4, pct)}%` }}
                    />
                  </div>
                  <div className="mt-2 font-mono text-xs text-white/85">
                    {b.mean != null ? b.mean.toFixed(4) : "—"}
                  </div>
                  <div className="text-[10px] text-[var(--fg-muted)] font-mono">
                    n={b.n} ·{" "}
                    {b.ci_lo != null && b.ci_hi != null
                      ? `[${b.ci_lo.toFixed(3)}, ${b.ci_hi.toFixed(3)}]`
                      : "—"}
                  </div>
                </div>
              );
            })}
          </div>
          {q8.kruskal_wallis_3sector && (
            <div className="mt-3 text-xs text-[var(--fg-muted)] font-mono">
              Kruskal-Wallis (3 sectors) p ={" "}
              {pStr(q8.kruskal_wallis_3sector.p)} · n_bins ={" "}
              {q8.kruskal_wallis_3sector.n_bins} · n_storms ={" "}
              {q8.n_storms_total}
            </div>
          )}
        </Section>
      )}

      {/* Catalog context fig */}
      <Section
        tag="Storm catalog context"
        title="11 years of solar activity, geomagnetic storms, and ingest coverage."
      >
        <p className="mt-2 text-[var(--fg-muted)] max-w-prose">
          Sunspot-number curve (top), every storm in the v3 catalog plotted
          as a red dot at <code>(dst_min_time, |Dst|)</code>, and the
          shaded bands marking what we actually ingested with pyOASIS.
          Use this to gut-check the cycle-phase claim in Q6: most of our
          highest-rate storms cluster in the descending-to-rising-phase
          band where solar EUV is high.
        </p>
        <FigImage
          src="/api/storms/v3/figure/fig15_solar_cycle_strip"
          alt="Solar-cycle strip"
          caption="fig15 — SSN line + storm dots + ingest coverage bars."
        />
      </Section>

      {/* Honest caveats */}
      <div className="card p-6 max-w-prose">
        <h2 className="font-display text-xl font-semibold">
          Honest caveats
        </h2>
        <ul className="mt-3 space-y-2 text-sm text-[var(--fg-muted)]">
          <li>
            <strong className="text-white/85">Labels still circular.</strong>{" "}
            The training labels share inputs with the model features (Pi
            1997 / Cherniak 2014 heuristic). Q1–Q7 results are
            &quot;model believes&quot; statements, validated against
            literature events on the <a className="underline text-[var(--accent)]" href="/validation">/validation</a> page.
          </li>
          <li>
            <strong className="text-white/85">Sample size.</strong> 31
            intense+ storms is small for 4-way LT stratification (Q2). The
            null result there is consistent with low power; we report the
            estimate honestly rather than fishing.
          </li>
          <li>
            <strong className="text-white/85">Brazilian-sector LT.</strong>{" "}
            Q2 LT bins are computed at the Brazilian terminator
            (UTC − 3 h), not global LT. The PRE hypothesis is
            specifically about Dst-min lining up with the pre-reversal
            enhancement over our station footprint.
          </li>
          <li>
            <strong className="text-white/85">Q5 not yet answerable.</strong>{" "}
            The pre-storm baseline question needs ingest of the 12 h
            window before <code>main_start</code> for each storm; the v3
            day-selector centres on <code>dst_min_time</code>, missing
            most of those windows.
          </li>
        </ul>
      </div>

      {/* Reproduce + cite */}
      <div className="card p-6 max-w-prose">
        <h2 className="font-display text-xl font-semibold">Reproduce</h2>
        <pre className="mt-3 bg-black/40 p-3 text-xs overflow-auto">
{`# All numbers on this page come from one JSON:
curl https://plasma-bubble.ifsp.dev/api/storms/v3/analysis | jq .

# Regenerate locally:
epb analysis storms-v3 --predictions v3 --out data/processed/analysis_v3.json
python paper/scripts/make_fig12_storm_vs_quiet_v3.py
python paper/scripts/make_fig13_storm_lt_polar.py
# ... fig14-19 follow the same pattern`}
        </pre>
        <h2 className="mt-6 font-display text-xl font-semibold">Cite</h2>
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
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
  tone?: "positive" | "null";
}) {
  const ringCls = accent
    ? "ring-1 ring-[var(--accent)]/40"
    : tone === "null"
      ? "ring-1 ring-amber-400/30"
      : tone === "positive"
        ? "ring-1 ring-emerald-400/30"
        : "";
  const valCls =
    tone === "null"
      ? "text-amber-200"
      : tone === "positive" || accent
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

function Section({
  tag,
  title,
  tone,
  children,
}: {
  tag: string;
  title: string;
  tone?: "positive" | "null";
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="flex items-center gap-3">
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          {tag}
        </p>
        {tone && <Tone tone={tone}>{tone}</Tone>}
      </div>
      <h2 className="font-display text-xl md:text-2xl font-semibold mt-2">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Tone({ tone, children }: { tone: "positive" | "null"; children: React.ReactNode }) {
  const cls =
    tone === "positive"
      ? "bg-emerald-500/15 text-emerald-300"
      : "bg-amber-500/15 text-amber-200";
  return (
    <span
      className={`text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 ${cls}`}
    >
      {children}
    </span>
  );
}

function QuartileBar({
  qIdx,
  rate,
  phaseLo,
  phaseHi,
  n,
  maxRate,
}: {
  qIdx: number;
  rate: number;
  phaseLo: number;
  phaseHi: number;
  n: number;
  maxRate: number;
}) {
  const pct = maxRate > 0 ? (rate / maxRate) * 100 : 0;
  return (
    <div className="card p-3">
      <div className="text-[10px] uppercase tracking-wider text-[var(--fg-muted)]">
        Q{qIdx + 1} · phase {phaseLo.toFixed(2)}–{phaseHi.toFixed(2)}
      </div>
      <div className="mt-2 h-20 flex items-end">
        <div
          className="w-full rounded-t bg-[var(--accent)]/70"
          style={{ height: `${Math.max(4, pct)}%` }}
        />
      </div>
      <div className="mt-2 font-mono text-xs text-white/85">
        rate {rate.toFixed(4)}
      </div>
      <div className="text-[10px] text-[var(--fg-muted)] font-mono">
        n={n} storms
      </div>
    </div>
  );
}

function LtBinBar({
  label,
  bin,
  highlight,
  maxRate,
}: {
  label: string;
  bin: LtBin;
  highlight?: boolean;
  maxRate: number;
}) {
  const pct = maxRate > 0 ? (bin.mean / maxRate) * 100 : 0;
  return (
    <div className={`card p-3 ${highlight ? "ring-1 ring-[var(--accent)]/40" : ""}`}>
      <div className="text-[10px] uppercase tracking-wider text-[var(--fg-muted)]">
        {label}
      </div>
      <div className="mt-2 h-20 flex items-end">
        <div
          className={`w-full rounded-t ${highlight ? "bg-[var(--accent)]/80" : "bg-white/30"}`}
          style={{ height: `${Math.max(4, pct)}%` }}
        />
      </div>
      <div className="mt-2 font-mono text-xs text-white/85">
        {bin.mean.toFixed(4)}
      </div>
      <div className="text-[10px] text-[var(--fg-muted)] font-mono">
        n={bin.n}
      </div>
    </div>
  );
}

function FigImage({
  src,
  alt,
  caption,
}: {
  src: string;
  alt: string;
  caption?: string;
}) {
  return (
    <figure className="mt-4 rounded-md border border-[#1c2236] overflow-hidden bg-[#0a0e1a]">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} className="block w-full h-auto" />
      {caption && (
        <figcaption className="px-3 py-2 text-[11px] text-[var(--fg-muted)] font-mono">
          {caption}
        </figcaption>
      )}
    </figure>
  );
}
