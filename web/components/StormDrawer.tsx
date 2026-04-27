"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { DstTrace, type TimelinePoint } from "./DstTrace";

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
};

type EventRow = {
  sta: string;
  start: string;
};

type DrawerData = {
  storm: CatalogRow | null;
  timeline: TimelinePoint[];
  events: EventRow[];
  loading: boolean;
  error?: string;
};

const API = "/api";

export function StormDrawer() {
  const router = useRouter();
  const params = useSearchParams();
  const selected = params.get("selected");
  const stormId = selected ? Number(selected) : null;

  const [data, setData] = useState<DrawerData>({
    storm: null,
    timeline: [],
    events: [],
    loading: false,
  });

  const close = useCallback(() => {
    // Drop the ?selected= param without re-scrolling.
    router.push("/storms", { scroll: false });
  }, [router]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    if (stormId != null) {
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }
  }, [stormId, close]);

  useEffect(() => {
    if (stormId == null || !Number.isFinite(stormId)) return;
    setData({ storm: null, timeline: [], events: [], loading: true });

    let cancelled = false;
    (async () => {
      try {
        const catRes = await fetch(`${API}/storms/v3/catalog?intense_only=false`, {
          cache: "no-store",
        });
        const catalog: CatalogRow[] = await catRes.json();
        const storm = catalog.find((s) => s.storm_id === stormId) ?? null;
        if (!storm) {
          if (!cancelled)
            setData({
              storm: null,
              timeline: [],
              events: [],
              loading: false,
              error: `Storm #${stormId} not in catalog.`,
            });
          return;
        }

        const [tlRes, evRes] = await Promise.all([
          fetch(
            `${API}/storms/timeline?t0=${encodeURIComponent(storm.main_start)}&t1=${encodeURIComponent(storm.recovery_end)}&step_hours=1`,
            { cache: "no-store" },
          ),
          fetch(
            `${API}/events?t0=${encodeURIComponent(storm.main_start)}&t1=${encodeURIComponent(storm.recovery_end)}&limit=10000`,
            { cache: "no-store" },
          ),
        ]);
        const tl = await tlRes.json();
        const ev = await evRes.json();
        if (!cancelled)
          setData({
            storm,
            timeline: tl?.rows ?? [],
            events: ev ?? [],
            loading: false,
          });
      } catch (e) {
        if (!cancelled)
          setData({
            storm: null,
            timeline: [],
            events: [],
            loading: false,
            error: String(e),
          });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [stormId]);

  if (stormId == null) return null;

  const byStation: Record<string, number> = {};
  for (const e of data.events) byStation[e.sta] = (byStation[e.sta] ?? 0) + 1;
  const sortedStations = Object.entries(byStation).sort((a, b) => b[1] - a[1]);
  const eventsByHour = data.events.map((e) => ({ time: e.start, n: 1 }));

  const storm = data.storm;

  return (
    <>
      {/* Backdrop */}
      <button
        type="button"
        aria-label="Close storm details"
        onClick={close}
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity"
      />

      {/* Drawer panel */}
      <aside
        className="fixed right-0 top-0 bottom-0 z-50 w-full sm:w-[640px] lg:w-[760px] overflow-y-auto bg-[var(--bg)] border-l border-[#1c2236] shadow-2xl"
        role="dialog"
        aria-modal="true"
      >
        <div className="sticky top-0 z-10 bg-[var(--bg)]/95 backdrop-blur border-b border-[#1c2236] px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--accent)]">
              Storm detail
            </span>
            {storm && (
              <span className="font-display text-lg truncate">
                #{storm.storm_id} · {storm.storm_class.toUpperCase()}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {storm && (
              <Link
                href={`/storms/${storm.storm_id}`}
                className="text-xs text-[var(--accent)] underline whitespace-nowrap"
              >
                full page ↗
              </Link>
            )}
            <button
              type="button"
              onClick={close}
              className="rounded-full w-8 h-8 flex items-center justify-center text-[var(--fg-muted)] hover:text-white hover:bg-white/10 transition"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="px-5 py-5 space-y-5">
          {data.loading && (
            <div className="text-sm text-[var(--fg-muted)] font-mono">
              loading storm #{stormId} …
            </div>
          )}

          {data.error && (
            <div className="card p-4 text-sm text-amber-200">{data.error}</div>
          )}

          {storm && (
            <>
              <p className="text-sm text-[var(--fg-muted)]">
                Dst minimum reached{" "}
                <span className="text-white/85 font-mono">
                  {storm.dst_min_value.toFixed(0)} nT
                </span>{" "}
                on{" "}
                <span className="text-white/85 font-mono">
                  {storm.dst_min_time.slice(0, 16)} UTC
                </span>
                . LT-at-Brazil bin:{" "}
                <span className="text-white/85 font-mono">{storm.lt_bin}</span>.
              </p>

              <div className="grid grid-cols-3 gap-2">
                <Stat
                  label="EPBs detected"
                  value={data.events.length.toLocaleString()}
                />
                <Stat
                  label="Recovery"
                  value={
                    storm.recovery_duration_hours != null
                      ? `${storm.recovery_duration_hours.toFixed(0)} h`
                      : "—"
                  }
                />
                <Stat
                  label="F10.7 at min"
                  value={
                    storm.f107_at_min != null
                      ? storm.f107_at_min.toFixed(0)
                      : "—"
                  }
                />
              </div>

              {data.timeline.length > 0 && (
                <DstTrace rows={data.timeline} events={eventsByHour} />
              )}

              <div className="card p-4">
                <h3 className="font-display text-sm font-semibold">
                  Detected EPBs · by station
                </h3>
                {sortedStations.length === 0 ? (
                  <p className="mt-2 text-xs text-[var(--fg-muted)]">
                    No events on disk for this storm window.
                  </p>
                ) : (
                  <ul className="mt-3 space-y-1 text-xs font-mono">
                    {sortedStations.map(([sta, n]) => (
                      <li
                        key={sta}
                        className="flex items-center justify-between"
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

              <div className="flex flex-wrap gap-2 pt-2">
                <Link
                  href={`/map?t0=${encodeURIComponent(storm.main_start)}&t1=${encodeURIComponent(storm.recovery_end)}`}
                  className="text-xs text-[var(--accent)] underline"
                >
                  view this window on /map →
                </Link>
                <Link
                  href={`/storms/${storm.storm_id}`}
                  className="text-xs text-[var(--accent)] underline"
                >
                  open dedicated page →
                </Link>
              </div>
            </>
          )}
        </div>
      </aside>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="card px-3 py-2">
      <div className="text-[9px] uppercase tracking-wider text-[var(--fg-muted)]">
        {label}
      </div>
      <div className="mt-0.5 font-display text-lg">{value}</div>
    </div>
  );
}
