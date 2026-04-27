import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchOrNull } from "@/lib/api";
import { DstTrace, type TimelinePoint } from "@/components/DstTrace";

export const revalidate = 0;

type CatalogRow = {
  storm_id: number;
  main_start: string;
  dst_min_time: string;
  dst_min_value: number;
  recovery_end: string;
  storm_class: string;
  lt_bin: string;
  season: string;
  recovery_duration_hours: number | null;
  f107_at_min: number | null;
  solar_cycle_phase: number | null;
  is_intense_or_stronger: boolean;
};

type EventRow = {
  sta: string;
  sat: string;
  start: string;
  end: string;
  n_windows: number;
  peak_probability: number;
  peak_roti: number | null;
  ipp_lon_mean: number;
  ipp_lat_mean: number;
};

type Timeline = { rows: TimelinePoint[] };

export default async function StormDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const stormId = Number(params.id);
  if (!Number.isFinite(stormId)) notFound();

  const catalog = await fetchOrNull<CatalogRow[]>(
    "/storms/v3/catalog?intense_only=false",
  );
  const storm = catalog?.find((s) => s.storm_id === stormId);
  if (!storm) {
    return (
      <section className="max-w-4xl mx-auto px-6 py-16">
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Storm detail
        </p>
        <h1 className="font-display text-3xl font-semibold mt-3">
          Storm #{stormId} not found.
        </h1>
        <p className="mt-4 text-[var(--fg-muted)]">
          The catalog parquet doesn&apos;t list a storm with that id, or the
          v3 catalog hasn&apos;t been built yet.
        </p>
      </section>
    );
  }

  const [events, timeline] = await Promise.all([
    fetchOrNull<EventRow[]>(
      `/events?t0=${encodeURIComponent(storm.main_start)}&t1=${encodeURIComponent(storm.recovery_end)}&limit=10000`,
    ),
    fetchOrNull<Timeline>(
      `/storms/timeline?t0=${encodeURIComponent(storm.main_start)}&t1=${encodeURIComponent(storm.recovery_end)}&step_hours=1`,
    ),
  ]);

  const evs = events ?? [];
  const tlRows = timeline?.rows ?? [];

  // Per-station counts.
  const byStation: Record<string, number> = {};
  for (const e of evs) byStation[e.sta] = (byStation[e.sta] ?? 0) + 1;
  const sortedStations = Object.entries(byStation).sort((a, b) => b[1] - a[1]);

  // Per-event hourly counts for the Dst trace overlay.
  const eventsByHour = evs.map((e) => ({
    time: e.start,
    n: 1,
  }));

  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-8">
      <div>
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Storms · detail
        </p>
        <h1 className="font-display text-3xl md:text-4xl font-semibold mt-3">
          Storm #{storm.storm_id} · {storm.storm_class.toUpperCase()}
        </h1>
        <p className="mt-3 max-w-2xl text-[var(--fg-muted)]">
          Dst minimum reached{" "}
          <span className="text-white/85 font-mono">
            {storm.dst_min_value.toFixed(0)} nT
          </span>{" "}
          on{" "}
          <span className="text-white/85 font-mono">
            {storm.dst_min_time.slice(0, 16)} UTC
          </span>
          . Local time at Brazilian sector when the minimum hit:{" "}
          <span className="text-white/85 font-mono">{storm.lt_bin}</span>.
        </p>
        <Link
          href="/storms"
          className="inline-block mt-3 text-xs text-[var(--accent)] underline"
        >
          ← back to /storms
        </Link>
      </div>

      <div className="grid sm:grid-cols-3 gap-4">
        <Stat label="EPB events detected" value={evs.length.toLocaleString()} />
        <Stat
          label="Recovery duration"
          value={
            storm.recovery_duration_hours != null
              ? `${storm.recovery_duration_hours.toFixed(0)} h`
              : "—"
          }
        />
        <Stat
          label="F10.7 at minimum"
          value={storm.f107_at_min != null ? storm.f107_at_min.toFixed(0) : "—"}
          sub={
            storm.solar_cycle_phase != null
              ? `cycle phase ${storm.solar_cycle_phase.toFixed(2)}`
              : undefined
          }
        />
      </div>

      {/* Dst trace + events */}
      {tlRows.length > 0 && <DstTrace rows={tlRows} events={eventsByHour} />}

      {/* Per-station EPB counts */}
      <div className="card p-6">
        <h2 className="font-display text-xl font-semibold">
          Detected EPBs · by station
        </h2>
        {sortedStations.length === 0 ? (
          <p className="mt-3 text-sm text-[var(--fg-muted)]">
            No events on disk for this storm window — either Phase 2-A
            never ingested it, or the model didn&apos;t fire any positives.
          </p>
        ) : (
          <ul className="mt-4 space-y-1 text-sm">
            {sortedStations.map(([sta, n]) => (
              <li
                key={sta}
                className="flex items-center justify-between font-mono"
              >
                <span>{sta}</span>
                <span className="text-[var(--accent)]">
                  {n.toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Storm window */}
      <div className="card p-6">
        <h2 className="font-display text-xl font-semibold">Storm window</h2>
        <ul className="mt-3 text-sm space-y-1 font-mono">
          <li>
            <span className="text-[var(--fg-muted)]">main start:</span>{" "}
            {storm.main_start.slice(0, 19)}Z
          </li>
          <li>
            <span className="text-[var(--fg-muted)]">dst-min:</span>{" "}
            {storm.dst_min_time.slice(0, 19)}Z
          </li>
          <li>
            <span className="text-[var(--fg-muted)]">recovery end:</span>{" "}
            {storm.recovery_end.slice(0, 19)}Z
          </li>
          <li>
            <span className="text-[var(--fg-muted)]">season:</span>{" "}
            {storm.season}
          </li>
        </ul>
        <Link
          href={`/map?t0=${encodeURIComponent(storm.main_start)}&t1=${encodeURIComponent(storm.recovery_end)}`}
          className="mt-4 inline-block text-sm text-[var(--accent)] underline"
        >
          View this storm window on the map →
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
      {sub && <div className="mt-1 text-xs text-[var(--fg-muted)]">{sub}</div>}
    </div>
  );
}
