import { fetchOrNull } from "@/lib/api";

export const revalidate = 0;

type StationStatus = "ingested_ok" | "not_in_queue" | string;

type StationDetail = {
  sta: string;
  ingest_state: StationStatus;
  model_events: number;
  detected: boolean;
};

type EventDetail = {
  date: string;
  in_window: boolean;
  expected_stations: string[];
  reference: string;
  doi?: string;
  notes?: string;
  stations: StationDetail[];
  testable_stations?: number;
  matched_stations?: number;
  verdict:
    | "hit"
    | "partial"
    | "miss"
    | "no_data_to_test"
    | "out_of_window";
};

type ValidationReport = {
  model_id: string;
  snapshot_id: string;
  window_start: string;
  window_end: string;
  n_case_studies_total: number;
  n_in_window: number;
  n_evaluable: number;
  event_recall: number;
  station_recall: number;
  stations_testable: number;
  stations_detected: number;
  per_event: EventDetail[];
};

export default async function ValidationPage() {
  const report = await fetchOrNull<ValidationReport>(
    "/validation/case-studies",
  );

  if (!report) {
    return (
      <section className="max-w-4xl mx-auto px-6 py-16">
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Phase 2 · independent validation
        </p>
        <h1 className="font-display text-3xl font-semibold mt-3">
          Validation report unavailable.
        </h1>
        <p className="mt-4 text-[var(--fg-muted)]">
          The API did not return a case-study validation file. This page
          will populate once <code>case_study_validation_v*.json</code> is
          present in <code>/data</code>.
        </p>
      </section>
    );
  }

  const evaluable = report.per_event.filter(
    (e) => e.in_window && e.verdict !== "no_data_to_test",
  );
  const inWindow = report.per_event.filter((e) => e.in_window);
  const outOfWindow = report.per_event.filter((e) => !e.in_window);
  const notTestable = report.per_event.filter(
    (e) => e.in_window && e.verdict === "no_data_to_test",
  );

  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-12">
      {/* Hero */}
      <div>
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Phase 2 · independent validation
        </p>
        <h1 className="font-display text-3xl md:text-4xl font-semibold mt-3">
          Did the model find what papers already documented?
        </h1>
        <p className="mt-3 max-w-2xl text-[var(--fg-muted)]">
          Independent label source: a curated YAML of EPB events confirmed
          in the peer-reviewed literature (
          <span className="font-mono text-xs">
            src/epb_detector/external/case_studies.yaml
          </span>
          ). For every case study that falls inside the Phase 2-A run window
          and has at least one station successfully ingested by pyOASIS, we
          ask: did the trained model flag at least one event on that date
          for that station?
        </p>
      </div>

      {/* Stats */}
      <div className="grid sm:grid-cols-3 gap-4">
        <BigStat
          label="Event-level recall"
          value={`${(report.event_recall * 100).toFixed(0)}%`}
          sub={`${evaluable.filter((e) => e.verdict === "hit" || e.verdict === "partial").length} / ${report.n_evaluable} testable case studies hit`}
        />
        <BigStat
          label="Station-level recall"
          value={`${report.stations_detected} / ${report.stations_testable}`}
          sub={`${(report.station_recall * 100).toFixed(0)}% of stations with valid data flagged the documented event`}
          accent
        />
        <BigStat
          label="Model"
          value={report.model_id}
          sub={`Snapshot ${report.snapshot_id} · ${report.window_start.slice(0, 10)} → ${report.window_end.slice(0, 10)}`}
        />
      </div>

      {/* Funnel */}
      <div className="card p-6">
        <h2 className="font-display text-xl font-semibold">
          How we computed it
        </h2>
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-4 gap-3 text-sm">
          <FunnelStep
            n={report.n_case_studies_total}
            label="case studies in YAML"
            tone="muted"
          />
          <FunnelStep
            n={report.n_in_window}
            label="inside Phase 2-A window"
            tone="muted"
          />
          <FunnelStep
            n={report.n_evaluable}
            label="testable (≥1 ingested station)"
            tone="muted"
          />
          <FunnelStep
            n={evaluable.filter((e) => e.verdict === "hit" || e.verdict === "partial").length}
            label="hits"
            tone="accent"
          />
        </div>
        <p className="mt-5 text-sm text-[var(--fg-muted)] max-w-prose">
          <strong className="text-white/80">Why "data-aware":</strong>{" "}
          stations that are missing from the IBGE archive (e.g. MAPA, PALM)
          or excluded from the day-selector queue cannot be evaluated. Counting
          them as misses would penalize the model for pre-conditions on the
          data. We report recall only over the subset where pyOASIS actually
          produced ROTI / ΔTEC / SIDX series.
        </p>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <span className="text-[var(--fg-muted)] uppercase tracking-wider">
          Station legend
        </span>
        <Chip tone="ok">SALU · detected</Chip>
        <Chip tone="warn">MAPA · ingest failed</Chip>
        <Chip tone="muted">BOAV · not in queue</Chip>
      </div>

      {/* In-window cards */}
      <div className="space-y-4">
        <h2 className="font-display text-xl font-semibold">
          Evaluable case studies ({inWindow.length})
        </h2>
        <div className="grid lg:grid-cols-2 gap-4">
          {inWindow.map((ev) => (
            <CaseCard key={ev.date} ev={ev} />
          ))}
        </div>
      </div>

      {/* Out-of-window */}
      {outOfWindow.length > 0 && (
        <div className="space-y-3">
          <h2 className="font-display text-xl font-semibold">
            Outside this run window
          </h2>
          <p className="text-sm text-[var(--fg-muted)] max-w-prose">
            These case studies are documented in literature but pre-date the
            Phase 2-A ingest window (Sep 2023 – May 2024). They will become
            evaluable when we extend the ingest backwards (Phase 2-B plan).
          </p>
          <div className="grid md:grid-cols-3 gap-3">
            {outOfWindow.map((ev) => (
              <div key={ev.date} className="card p-4 text-sm">
                <div className="font-mono text-xs text-[var(--fg-muted)]">
                  {ev.date}
                </div>
                <div className="mt-2 text-white/85">{ev.reference}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Methodology footer */}
      <div className="card p-6 max-w-prose">
        <h2 className="font-display text-xl font-semibold">
          Why this matters more than the test-set PR-AUC
        </h2>
        <p className="mt-3 text-[var(--fg-muted)]">
          The model and the training labels share their core inputs (ROTI
          peak / duration, local time, QD-latitude). A 0.999 PR-AUC on the
          held-out test fold mostly demonstrates that the model has learned
          to reproduce the Pi 1997 / Cherniak 2014 heuristic with high
          fidelity — useful, but circular. The case-study comparison uses
          a label source built from a different methodology (papers that
          confirmed events with airglow imagers, ionosondes, or in-situ
          probes) and so breaks the circularity.
        </p>
        <p className="mt-3 text-[var(--fg-muted)]">
          The case-study list is intentionally sparse and high-quality. Any
          trained eye that confirms a new event in our window should add it
          via{" "}
          <code className="font-mono text-xs text-[var(--accent)]">
            epb labels external add ...
          </code>
          .
        </p>
        <a
          className="mt-4 inline-block text-sm text-[var(--accent)] underline"
          href="https://github.com/tardellirs/plasma-bubble-paper/blob/main/docs/case_study_validation_v2.json"
          target="_blank"
          rel="noreferrer"
        >
          Raw validation JSON ↗
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
    <div
      className={`card p-6 ${
        accent ? "ring-1 ring-[var(--accent)]/40" : ""
      }`}
    >
      <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
        {label}
      </div>
      <div
        className={`mt-2 font-display text-3xl ${
          accent ? "text-[var(--accent)]" : ""
        }`}
      >
        {value}
      </div>
      {sub && (
        <div className="mt-2 text-xs text-[var(--fg-muted)]">{sub}</div>
      )}
    </div>
  );
}

function FunnelStep({
  n,
  label,
  tone,
}: {
  n: number;
  label: string;
  tone: "muted" | "accent";
}) {
  return (
    <div className="rounded-md border border-[#1c2236] p-3">
      <div
        className={`font-display text-2xl ${
          tone === "accent" ? "text-[var(--accent)]" : ""
        }`}
      >
        {n}
      </div>
      <div className="mt-1 text-xs text-[var(--fg-muted)]">{label}</div>
    </div>
  );
}

function CaseCard({ ev }: { ev: EventDetail }) {
  const verdict = ev.verdict;
  const verdictBadge: Record<EventDetail["verdict"], { txt: string; cls: string }> =
    {
      hit: {
        txt: "All testable stations matched",
        cls: "bg-emerald-500/15 text-emerald-300",
      },
      partial: {
        txt: "Partial match",
        cls: "bg-amber-500/15 text-amber-200",
      },
      miss: {
        txt: "No detection",
        cls: "bg-rose-500/15 text-rose-200",
      },
      no_data_to_test: {
        txt: "Not testable (no station ingested)",
        cls: "bg-white/5 text-[var(--fg-muted)]",
      },
      out_of_window: {
        txt: "Out of run window",
        cls: "bg-white/5 text-[var(--fg-muted)]",
      },
    };
  const totalEvents = ev.stations.reduce((acc, s) => acc + s.model_events, 0);
  const doiUrl =
    ev.doi && ev.doi.startsWith("10.")
      ? `https://doi.org/${ev.doi}`
      : ev.doi;
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-mono text-xs text-[var(--accent)] tracking-wider">
            {ev.date}
          </div>
          <h3 className="mt-1 font-display text-lg font-semibold">
            {ev.reference}
          </h3>
          {ev.notes && (
            <p className="mt-1 text-sm text-[var(--fg-muted)]">{ev.notes}</p>
          )}
        </div>
        <span
          className={`text-[10px] uppercase tracking-wider rounded-full px-2 py-1 whitespace-nowrap ${verdictBadge[verdict].cls}`}
        >
          {verdictBadge[verdict].txt}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {ev.stations.map((s) => {
          const tone: "ok" | "warn" | "muted" = s.detected
            ? "ok"
            : s.ingest_state === "ingested_ok"
              ? "warn"
              : s.ingest_state === "not_in_queue"
                ? "muted"
                : "warn";
          const subLabel = s.detected
            ? `${s.model_events} events`
            : s.ingest_state === "not_in_queue"
              ? "not queued"
              : s.ingest_state.startsWith("ingest_failed")
                ? "ingest failed"
                : "no detection";
          return (
            <Chip key={s.sta} tone={tone}>
              <span className="font-mono">{s.sta}</span>{" "}
              <span className="text-[10px] opacity-75 ml-1">{subLabel}</span>
            </Chip>
          );
        })}
      </div>

      {(verdict === "hit" || verdict === "partial") && (
        <div className="mt-4 text-xs text-[var(--fg-muted)]">
          <span className="text-white/80 font-mono">{totalEvents}</span>{" "}
          model-detected events on this date across testable stations
        </div>
      )}

      {doiUrl && (
        <a
          className="mt-3 inline-block text-xs text-[var(--accent)] underline"
          href={doiUrl}
          target="_blank"
          rel="noreferrer"
        >
          DOI ↗
        </a>
      )}
    </div>
  );
}

function Chip({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "ok" | "warn" | "muted";
}) {
  const cls = {
    ok: "bg-emerald-500/10 text-emerald-200 ring-1 ring-emerald-400/30",
    warn: "bg-amber-500/10 text-amber-100 ring-1 ring-amber-400/30",
    muted: "bg-white/5 text-[var(--fg-muted)] ring-1 ring-white/10",
  }[tone];
  return (
    <span
      className={`inline-flex items-center text-xs px-2 py-1 rounded-md ${cls}`}
    >
      {children}
    </span>
  );
}
