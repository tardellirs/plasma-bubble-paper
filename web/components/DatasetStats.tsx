import type { SnapshotMeta } from "@/lib/api";

export function DatasetStats({ meta }: { meta: SnapshotMeta }) {
  const positiveRate = (meta.n_positives / Math.max(1, meta.n_windows)) * 100;
  const tiles: { label: string; value: string; sub?: string }[] = [
    {
      label: "Snapshot",
      value: meta.snapshot_id,
      sub: `git ${meta.git_sha}`,
    },
    {
      label: "Rule",
      value: meta.rule_version,
    },
    {
      label: "Windows",
      value: meta.n_windows.toLocaleString(),
      sub: `${meta.n_station_days.toLocaleString()} station-days`,
    },
    {
      label: "Positives",
      value: meta.n_positives.toLocaleString(),
      sub: `${positiveRate.toFixed(2)}% of windows`,
    },
    {
      label: "Stations",
      value: meta.stations.length.toString(),
      sub: meta.stations.slice(0, 6).join(" · "),
    },
    {
      label: "Years",
      value: meta.years.join(", "),
    },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {tiles.map((t) => (
        <div key={t.label} className="card p-5">
          <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
            {t.label}
          </div>
          <div className="mt-2 font-display text-xl">{t.value}</div>
          {t.sub && (
            <div className="mt-1 text-xs text-[var(--fg-muted)] font-mono">
              {t.sub}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
