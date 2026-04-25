export default function MethodsPage() {
  return (
    <section className="max-w-3xl mx-auto px-6 py-16 prose prose-invert">
      <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
        Methods · v0.1
      </p>
      <h1 className="font-display text-4xl font-semibold mt-2 mb-6 text-white">
        How we detect equatorial plasma bubbles.
      </h1>
      <p className="text-[var(--fg-muted)]">
        We build on{" "}
        <a
          href="https://github.com/giorgiopicanco/OASIS"
          className="text-[var(--accent)]"
        >
          pyOASIS
        </a>
        , which interpolates MGEX SP3 orbits, screens RINEX phase data for
        cycle slips, and performs arc-wise geometry-free leveling. From the
        leveled phase combinations we compute three indices — ROTI, ΔTEC and
        SIDX — at native resolutions of 1–2.5 minutes.
      </p>
      <h2 className="text-white">Weak labels</h2>
      <p className="text-[var(--fg-muted)]">
        A 10-minute window is labelled positive when it satisfies all four
        criteria below:
      </p>
      <ul className="text-[var(--fg-muted)]">
        <li>
          IPP local solar time is within the night band (default 19h–06h).
        </li>
        <li>
          ROTI ≥ 0.5 TECU/min sustained for at least 5 minutes (Pi et al.,
          1997).
        </li>
        <li>
          At least two satellites trip the threshold within a ±10°
          IPP-longitude corridor (Cherniak, Krankowski &amp; Zakharenkova,
          2014).
        </li>
        <li>
          Quasi-dipole latitude at the IPP within ±20° (suppress auroral
          contamination).
        </li>
      </ul>
      <h2 className="text-white">Baseline classifier</h2>
      <p className="text-[var(--fg-muted)]">
        We train an XGBoost binary classifier on roughly 18 hand-crafted
        features per window: ROTI / ΔTEC / SIDX percentiles, slope and
        duration-above-threshold; window geometry (IPP longitude, latitude,
        QD-latitude, local time, elevation); and counts of cross-satellite
        co-occurrence. Folds are produced by{" "}
        <code className="kbd">GroupKFold</code> on the (station, day-of-year)
        key so that adjacent windows from the same station-day cannot leak
        across the train/validation split.
      </p>
      <h2 className="text-white">Reproducibility</h2>
      <p className="text-[var(--fg-muted)]">
        Every figure exported to <code className="kbd">paper/figures</code>{" "}
        records its source script, the SHA-256 of the dataset snapshot, the
        model id, and the random seed. The snapshot itself ships a Hugging
        Face-style dataset card.
      </p>
    </section>
  );
}
