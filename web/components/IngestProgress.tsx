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

export function IngestProgress({ status }: { status: IngestStatus | null }) {
  if (!status || status.total === 0) {
    return (
      <div className="card p-6">
        <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
          Ingest progress
        </div>
        <p className="mt-2 text-[var(--fg-muted)]">
          No station-days processed yet. Run{" "}
          <code className="kbd">epb ingest phase2a</code>.
        </p>
      </div>
    );
  }
  const okPct = (status.ok / Math.max(1, status.total)) * 100;
  const failPct = (status.failed / Math.max(1, status.total)) * 100;
  const stations = Object.entries(status.by_station).sort();

  return (
    <div className="card p-6">
      <div className="flex items-baseline justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
            Ingest progress
          </div>
          <div className="font-display text-2xl mt-1">
            {status.ok}/{status.total} station-days
          </div>
          {status.median_duration_s != null && (
            <div className="text-xs text-[var(--fg-muted)] font-mono mt-1">
              median {status.median_duration_s.toFixed(0)}s · cumulative{" "}
              {status.total_minutes.toFixed(0)} min
            </div>
          )}
        </div>
        {status.failed > 0 && (
          <div className="text-xs font-mono text-[var(--warn)]">
            {status.failed} failed
          </div>
        )}
      </div>

      <div className="mt-4 h-2 w-full rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full bg-[var(--accent)]"
          style={{ width: `${okPct}%` }}
        />
        <div
          className="h-full bg-[var(--warn)] -mt-2"
          style={{ width: `${failPct}%`, marginLeft: `${okPct}%` }}
        />
      </div>

      <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
        {stations.map(([sta, counts]) => {
          const ok = counts.ok ?? 0;
          const fail = counts.failed ?? 0;
          const total = ok + fail + (counts.skipped ?? 0);
          return (
            <div key={sta} className="flex items-center justify-between bg-white/5 rounded px-2 py-1">
              <span className="text-white">{sta}</span>
              <span className="text-[var(--fg-muted)]">
                {ok}/{total}
                {fail > 0 ? ` ·${fail}f` : ""}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
