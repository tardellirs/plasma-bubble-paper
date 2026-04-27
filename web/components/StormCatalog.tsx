import Link from "next/link";

export type StormRow = {
  storm_id: number;
  main_start: string;
  recovery_end: string;
  dst_min_time: string;
  dst_min: number | null;
  n_windows: number;
  n_positive: number;
  positive_rate: number;
  stations: string;
  class_label: string;
};

const CLASS_COLOR: Record<string, string> = {
  super: "text-[#9B5DE5]",
  severe: "text-[#E63946]",
  intense: "text-[#F7A072]",
  moderate: "text-[#0FA3B1]",
};

export function StormCatalog({ rows }: { rows: StormRow[] }) {
  if (rows.length === 0) {
    return (
      <div className="card p-6 text-[var(--fg-muted)]">
        No storms detected in the active dataset window. Re-run{" "}
        <code className="kbd">epb labels v2</code> after broader ingest.
      </div>
    );
  }
  return (
    <div className="card overflow-hidden">
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase text-[var(--fg-muted)]">
          <tr>
            <th className="px-4 py-3">Storm</th>
            <th className="px-4 py-3">Class</th>
            <th className="px-4 py-3">Dst min</th>
            <th className="px-4 py-3">Stations</th>
            <th className="px-4 py-3">Windows</th>
            <th className="px-4 py-3">EPB rate</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const t0 = new Date(
              new Date(r.main_start).getTime() - 6 * 3600 * 1000
            ).toISOString();
            const t1 = new Date(
              new Date(r.recovery_end).getTime() + 6 * 3600 * 1000
            ).toISOString();
            return (
              <tr
                key={r.storm_id}
                className="border-t border-[#1c2236] hover:bg-white/5 transition"
              >
                <td className="px-4 py-3 font-mono">
                  {new Date(r.dst_min_time).toISOString().slice(0, 16)}Z
                </td>
                <td className={`px-4 py-3 font-medium ${CLASS_COLOR[r.class_label] ?? ""}`}>
                  {r.class_label}
                </td>
                <td className="px-4 py-3 font-mono">
                  {r.dst_min !== null ? `${r.dst_min.toFixed(0)} nT` : "—"}
                </td>
                <td className="px-4 py-3 font-mono text-xs">{r.stations}</td>
                <td className="px-4 py-3 font-mono">{r.n_windows.toLocaleString()}</td>
                <td className="px-4 py-3 font-mono">
                  {(r.positive_rate * 100).toFixed(2)}%
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-3">
                    <Link
                      href={`/storms?selected=${r.storm_id}`}
                      scroll={false}
                      className="text-[var(--accent)] hover:underline"
                    >
                      details
                    </Link>
                    <Link
                      href={`/map?t0=${t0}&t1=${t1}`}
                      className="text-[var(--fg-muted)] hover:underline"
                    >
                      map →
                    </Link>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
