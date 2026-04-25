import { fetchOrNull, type SnapshotMeta } from "@/lib/api";
import { DatasetStats } from "@/components/DatasetStats";
import { FeatureHistogram } from "@/components/FeatureHistogram";

export const revalidate = 0;

async function loadSnapshot(): Promise<{
  ids: string[];
  current: SnapshotMeta | null;
}> {
  const ids = (await fetchOrNull<string[]>("/training-data/snapshots")) ?? [];
  if (ids.length === 0) return { ids: [], current: null };
  const meta = await fetchOrNull<SnapshotMeta>(
    `/training-data/snapshots/${ids[ids.length - 1]}`
  );
  return { ids, current: meta };
}

export default async function DatasetPage() {
  const { ids, current } = await loadSnapshot();
  if (!current) {
    return (
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h1 className="font-display text-3xl font-semibold">Training data</h1>
        <p className="mt-3 text-[var(--fg-muted)]">
          No snapshots yet. Run <code className="kbd">epb dataset snapshot</code>
          and refresh.
        </p>
      </section>
    );
  }
  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-10">
      <div>
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Dataset · snapshot {current.snapshot_id}
        </p>
        <h1 className="font-display text-3xl md:text-4xl font-semibold mt-3">
          Training data, every window accounted for.
        </h1>
        <p className="mt-3 max-w-2xl text-[var(--fg-muted)]">
          The dataset card below is generated automatically from the snapshot.
          Available snapshots:{" "}
          <span className="font-mono text-sm text-white">{ids.join(", ")}</span>
          . Each feature/label/split parquet is hash-pinned in the snapshot
          manifest so that the published model and figures can always be
          reproduced.
        </p>
      </div>

      <DatasetStats meta={current} />

      <FeatureHistogram snapshotId={current.snapshot_id} />

      <div className="card p-6">
        <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
          Download
        </div>
        <p className="mt-2 text-sm text-[var(--fg-muted)] max-w-2xl">
          Get the parquet directly. SHA-256:&nbsp;
          <code className="font-mono text-xs text-white">
            {current.sha256_features.slice(0, 16)}…
          </code>
        </p>
        <a
          className="btn btn-primary mt-4"
          href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/training-data/snapshots/${current.snapshot_id}/download.parquet`}
          data-testid="download-features"
        >
          Download features.parquet ({(current.n_windows / 1000).toFixed(1)}k rows)
        </a>
      </div>
    </section>
  );
}
