import Link from "next/link";
import { fetchOrNull, EventsSummary, Station, SnapshotMeta } from "@/lib/api";
import { IngestProgress } from "@/components/IngestProgress";

export const dynamic = "force-dynamic";

type IngestStatus = {
  total: number;
  ok: number;
  failed: number;
  skipped: number;
  by_station: Record<string, Record<string, number>>;
  median_duration_s: number | null;
  total_minutes: number;
  last_completed_at?: string | null;
};

type StormCatalogRow = {
  storm_id: number;
  dst_min: number | null;
  class_label: string;
};

async function loadHero() {
  const [summary, stations, snapshots, storms, ingest] = await Promise.all([
    fetchOrNull<EventsSummary>("/events/summary"),
    fetchOrNull<Station[]>("/stations"),
    fetchOrNull<string[]>("/training-data/snapshots"),
    fetchOrNull<StormCatalogRow[]>("/storms/catalog"),
    fetchOrNull<IngestStatus>("/ingest/status"),
  ]);
  let snapshotMeta: SnapshotMeta | null = null;
  if (snapshots && snapshots.length > 0) {
    snapshotMeta = await fetchOrNull<SnapshotMeta>(
      `/training-data/snapshots/${snapshots[snapshots.length - 1]}`
    );
  }
  return { summary, stations, snapshotMeta, storms: storms ?? [], ingest };
}

const STAT = (label: string, value: string | number, sub?: string) => (
  <div className="card p-5">
    <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
      {label}
    </div>
    <div className="font-display text-3xl font-semibold mt-2">{value}</div>
    {sub && (
      <div className="mt-1 text-sm text-[var(--fg-muted)]">{sub}</div>
    )}
  </div>
);

export default async function Home() {
  const { summary, stations, snapshotMeta, storms, ingest } = await loadHero();
  const totalEvents = summary?.total ?? 0;
  const stationCount = stations?.length ?? 0;
  const snapshotCount = snapshotMeta
    ? snapshotMeta.n_windows.toLocaleString()
    : "—";
  const positiveRate = snapshotMeta
    ? `${((snapshotMeta.n_positives / Math.max(1, snapshotMeta.n_windows)) * 100).toFixed(2)}%`
    : "—";
  const stormCount = storms.length;
  const intenseCount = storms.filter((s) =>
    ["intense", "severe", "super"].includes(s.class_label),
  ).length;

  return (
    <div className="gradient-radial">
      <section className="max-w-6xl mx-auto px-6 pt-16 pb-24">
        <div className="fade-up grid gap-10 md:grid-cols-[1fr_320px] items-center">
          <div>
            <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
              Open scientific platform · v0.1
            </p>
            <h1 className="font-display text-5xl md:text-6xl font-semibold leading-[1.05] mt-4">
              Equatorial plasma bubbles,{" "}
              <span className="text-[var(--accent)]">automatically detected</span>{" "}
              from GNSS.
            </h1>
            <p className="mt-6 max-w-2xl text-lg text-[var(--fg-muted)]">
              Bulk ingest, leveling, ROTI / ΔTEC / SIDX index synthesis, weak-label
              heuristics calibrated against the Pi (1997) and Cherniak et&nbsp;al.
              (2014) literature, an XGBoost baseline, and a full audit trail —
              ready for paper figures and conference plots.
            </p>
            <div className="mt-8 flex gap-3">
              <Link href="/map" className="btn btn-primary">
                Explore the live map →
              </Link>
              <Link href="/dataset" className="btn btn-ghost">
                Inspect the dataset
              </Link>
            </div>
          </div>
          <div className="hidden md:flex justify-center">
            <picture>
              <source srcSet="/mark-256.webp" type="image/webp" />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/mark-128.png"
                alt="EPB Detector globe mark with neon ring and bubble markers"
                width={280}
                height={280}
                className="w-[280px] h-[280px] drop-shadow-[0_0_40px_rgba(15,163,177,0.25)]"
              />
            </picture>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mt-16">
          {STAT(
            "Stations",
            stationCount,
            stations?.filter((s) => s.mvp).length
              ? `${stations.filter((s) => s.mvp).length} on the MVP track`
              : undefined
          )}
          {STAT("Detected events", totalEvents.toLocaleString())}
          {STAT(
            "Labelled windows",
            snapshotCount,
            snapshotMeta ? `rule ${snapshotMeta.rule_version}` : undefined
          )}
          {STAT(
            "Positive class rate",
            positiveRate,
            snapshotMeta
              ? `${snapshotMeta.n_positives.toLocaleString()} positives`
              : undefined
          )}
          {STAT(
            "Geomagnetic storms",
            stormCount.toString(),
            intenseCount > 0
              ? `${intenseCount} intense or stronger`
              : undefined
          )}
        </div>

        <div className="mt-12">
          <IngestProgress status={ingest} />
        </div>

        <div className="mt-12 card p-8">
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h2 className="font-display text-2xl font-semibold">
                A reproducible pipeline.
              </h2>
              <p className="mt-3 text-[var(--fg-muted)]">
                Every figure in the paper is traced to a versioned snapshot via
                <code className="kbd ml-1">paper/figures/manifest.json</code>:
                features, labels, and splits hash-pinned and re-runnable.
              </p>
            </div>
            <div>
              <h2 className="font-display text-2xl font-semibold">
                Made for low-latitude science.
              </h2>
              <p className="mt-3 text-[var(--fg-muted)]">
                Equatorial Brazilian RBMC stations (BOAV, MAPA, BELE, SALU,
                BRAZ…) plus a mid-latitude control (POAL) anchor the
                training data with the right ionospheric regimes.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
