import { fetchOrNull } from "@/lib/api";
import { StormTimeline, type TimelineRow } from "@/components/StormTimeline";
import { PhaseBars, type PhaseRow } from "@/components/PhaseBars";
import { StormCatalog, type StormRow } from "@/components/StormCatalog";
import { SuperposedEpoch, type SuperposedRow } from "@/components/SuperposedEpoch";

export const revalidate = 0;

async function loadAll() {
  const [timeline, phase, catalog, sea] = await Promise.all([
    fetchOrNull<{ rows: TimelineRow[] }>("/storms/timeline"),
    fetchOrNull<{ rows: PhaseRow[] }>("/storms/by-phase"),
    fetchOrNull<StormRow[]>("/storms/catalog"),
    fetchOrNull<{ rows: SuperposedRow[] }>("/storms/superposed-epoch"),
  ]);
  return {
    timeline: timeline?.rows ?? [],
    phase: phase?.rows ?? [],
    catalog: catalog ?? [],
    sea: sea?.rows ?? [],
  };
}

export default async function StormsPage() {
  const { timeline, phase, catalog, sea } = await loadAll();
  const intense = catalog.filter((c) =>
    ["intense", "severe", "super"].includes(c.class_label),
  ).length;
  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-10">
      <div>
        <p className="font-mono text-xs text-[var(--accent)] tracking-[0.2em] uppercase">
          Phase 2 · geomagnetic context
        </p>
        <h1 className="font-display text-3xl md:text-4xl font-semibold mt-3">
          Storms, dynamos, and bubbles.
        </h1>
        <p className="mt-3 max-w-2xl text-[var(--fg-muted)]">
          We pull Kp/ap/F10.7 from <span className="font-mono">GFZ Potsdam</span>{" "}
          and Dst from <span className="font-mono">WDC Kyoto</span>, classify
          storm episodes by Dst minimum, and tag every detection window with
          its storm phase. The plot below shows what happens to EPB rates
          before, during, and after each event.
        </p>
        <div className="mt-6 flex flex-wrap gap-3 text-sm">
          <Stat label="Storms in dataset" value={catalog.length.toString()} />
          <Stat label="Intense or stronger" value={intense.toString()} />
          <Stat
            label="Strongest Dst min"
            value={
              catalog.length
                ? `${catalog[0].dst_min?.toFixed(0) ?? "—"} nT`
                : "—"
            }
            sub={catalog[0]?.dst_min_time?.slice(0, 10)}
          />
        </div>
      </div>

      <StormTimeline rows={timeline} />

      <div className="grid lg:grid-cols-2 gap-4">
        <PhaseBars rows={phase} />
        <SuperposedEpoch rows={sea} />
      </div>

      <div>
        <h2 className="font-display text-2xl font-semibold mb-3">
          Storm catalog
        </h2>
        <StormCatalog rows={catalog} />
      </div>

      <div className="card p-6 max-w-prose">
        <h2 className="font-display text-xl font-semibold">Why this matters</h2>
        <p className="mt-3 text-[var(--fg-muted)]">
          Equatorial plasma bubbles are not a simple monotonic response to
          geomagnetic activity. During the main phase, prompt penetration
          electric fields can either reinforce or suppress the post-sunset
          enhancement of the eastward zonal field that triggers Rayleigh-Taylor
          instability. During the recovery phase, the disturbance dynamo
          rearranges thermospheric winds and often inhibits bubbles on the
          following night. The site shows this directly via the phase-binned
          rate and the superposed-epoch view above.
        </p>
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
    <div className="card px-5 py-3">
      <div className="text-[10px] uppercase tracking-wider text-[var(--fg-muted)]">
        {label}
      </div>
      <div className="font-display text-xl">{value}</div>
      {sub && (
        <div className="text-xs text-[var(--fg-muted)] font-mono">{sub}</div>
      )}
    </div>
  );
}
