"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { rotiColor, constellationColor } from "@/lib/colors";
import type { EventRow, Station } from "@/lib/api";

type Props = {
  events: EventRow[];
  stations: Station[];
};

// Self-contained dark style — raster tiles from OSM with a dark filter
// applied via a synthetic overlay. We avoid demotiles.maplibre.org because
// it aborts under React StrictMode double-mounts and renders blank.
const MAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: [
        "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
      ],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
      maxzoom: 19,
    },
  },
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": "#0a0e1a" },
    },
    {
      id: "osm",
      type: "raster",
      source: "osm",
      paint: {
        "raster-opacity": 0.55,
        "raster-saturation": -0.6,
        "raster-contrast": -0.05,
        "raster-brightness-min": 0.0,
        "raster-brightness-max": 0.7,
      },
    },
  ],
};

export default function MapDeck({ events, stations }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [hover, setHover] = useState<EventRow | null>(null);

  // Time slider over the event range.
  const { tMin, tMax } = useMemo(() => {
    if (events.length === 0)
      return { tMin: Date.now() - 1000, tMax: Date.now() };
    const xs = events.map((e) => +new Date(e.start));
    return { tMin: Math.min(...xs), tMax: Math.max(...xs) };
  }, [events]);
  const [tCursor, setTCursor] = useState<number>(tMax);

  useEffect(() => {
    setTCursor(tMax);
  }, [tMax]);

  useEffect(() => {
    if (!ref.current) return;
    const map = new maplibregl.Map({
      container: ref.current,
      style: MAP_STYLE,
      center: [-50, -10],
      zoom: 3.6,
      pitch: 0,
      attributionControl: { compact: true } as never,
    });
    map.dragRotate.disable();
    map.touchZoomRotate.disableRotation();
    mapRef.current = map;

    map.on("load", () => {
      // Some browsers report the container size as 0 on the first paint
      // before CSS settles; nudge MapLibre to re-measure.
      map.resize();
      // Stations source
      map.addSource("stations", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: stations.map((s) => ({
            type: "Feature",
            geometry: {
              type: "Point",
              coordinates: [s.geodetic_lon_deg, s.geodetic_lat_deg],
            },
            properties: { id: s.id, name: s.name, region: s.region },
          })),
        },
      });
      map.addLayer({
        id: "stations-halo",
        source: "stations",
        type: "circle",
        paint: {
          "circle-radius": 14,
          "circle-color": "#0FA3B1",
          "circle-opacity": 0.12,
        },
      });
      map.addLayer({
        id: "stations-core",
        source: "stations",
        type: "circle",
        paint: {
          "circle-radius": 4,
          "circle-color": "#0FA3B1",
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#FAFAFC",
        },
      });
      // Station labels render as HTML overlay markers (see below) — symbol
      // layers would need a `glyphs` endpoint, which we avoid to keep the
      // basemap dependency-free.
      stations.forEach((s) => {
        const el = document.createElement("div");
        el.className =
          "px-2 py-0.5 rounded-md text-[11px] font-mono text-white " +
          "bg-[#0a0e1a]/85 border border-[#1c2236] shadow-md pointer-events-none " +
          "whitespace-nowrap select-none";
        el.textContent = s.id;
        new maplibregl.Marker({ element: el, offset: [0, 14] })
          .setLngLat([s.geodetic_lon_deg, s.geodetic_lat_deg])
          .addTo(map);
      });

      // Events source
      map.addSource("events", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "events-glow",
        source: "events",
        type: "circle",
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["get", "peak"],
            0,
            6,
            1,
            18,
          ],
          "circle-color": ["get", "color"],
          "circle-opacity": 0.18,
          "circle-blur": 0.4,
        },
      });
      map.addLayer({
        id: "events-points",
        source: "events",
        type: "circle",
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["get", "peak"],
            0,
            3,
            1,
            7,
          ],
          "circle-color": ["get", "color"],
          "circle-stroke-width": 0.5,
          "circle-stroke-color": "rgba(255,255,255,0.7)",
        },
      });

      map.on("mousemove", "events-points", (e) => {
        const f = e.features?.[0];
        if (f && f.properties) {
          const p = f.properties as Record<string, string>;
          map.getCanvas().style.cursor = "pointer";
          setHover({
            sta: p.sta,
            sat: p.sat,
            start: p.start,
            end: p.end,
            n_windows: Number(p.n_windows ?? 0),
            peak_probability: Number(p.peak ?? 0),
            peak_roti: p.peak_roti ? Number(p.peak_roti) : null,
            ipp_lon_mean: 0,
            ipp_lat_mean: 0,
            qd_lat_mean: 0,
            duration_minutes: Number(p.duration ?? 0),
          });
        }
      });
      map.on("mouseleave", "events-points", () => {
        map.getCanvas().style.cursor = "";
        setHover(null);
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [stations]);

  // Update events layer when cursor or events change.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const src = map.getSource("events") as maplibregl.GeoJSONSource | undefined;
    if (!src) return;
    const features = events
      .filter((e) => +new Date(e.start) <= tCursor)
      .map((e) => ({
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [
            ((e.ipp_lon_mean + 180) % 360) - 180,
            e.ipp_lat_mean,
          ],
        },
        properties: {
          sta: e.sta,
          sat: e.sat,
          start: e.start,
          end: e.end,
          n_windows: e.n_windows,
          peak: e.peak_probability,
          peak_roti: e.peak_roti,
          duration: e.duration_minutes,
          color: rotiColor(
            e.peak_probability ?? 0,
            0,
            1
          ),
          sat_color: constellationColor(e.sat),
        },
      }));
    src.setData({ type: "FeatureCollection", features });
  }, [events, tCursor]);

  return (
    <div className="relative h-full w-full">
      {/*
        maplibre-gl.css forces `position: relative` on the container, which
        overrides Tailwind's `absolute inset-0` and collapses the div to
        zero height. Use explicit h-full/w-full instead.
      */}
      <div ref={ref} className="h-full w-full" />

      <div className="absolute top-4 left-4 right-4 flex items-center justify-between pointer-events-none">
        <div className="card pointer-events-auto p-4 max-w-md">
          <div className="text-xs uppercase tracking-wider text-[var(--fg-muted)]">
            Equatorial Plasma Bubble Map
          </div>
          <div className="font-display text-lg mt-1">
            {events.length.toLocaleString()} events · {stations.length} stations
          </div>
          <div className="text-xs text-[var(--fg-muted)] mt-1">
            Color: detection probability. Click an event to open its time
            series.
          </div>
        </div>

        {hover && (
          <div className="card pointer-events-auto p-4 max-w-xs text-sm fade-up">
            <div className="font-mono text-xs text-[var(--accent)]">
              {hover.sta} / {hover.sat}
            </div>
            <div className="mt-1 font-display text-base">
              {new Date(hover.start).toUTCString()}
            </div>
            <div className="mt-2 text-[var(--fg-muted)] text-xs">
              prob = {hover.peak_probability.toFixed(2)} · ROTI peak{" "}
              {hover.peak_roti?.toFixed(2) ?? "—"} · {hover.duration_minutes.toFixed(1)} min
            </div>
          </div>
        )}
      </div>

      <div className="absolute bottom-6 left-6 right-6">
        <div className="card p-4">
          <div className="flex items-center justify-between text-xs text-[var(--fg-muted)] mb-2">
            <span className="font-mono">
              cursor · {new Date(tCursor).toISOString().slice(0, 19)}Z
            </span>
            <span>
              <span className="kbd">←</span> back  ·  <span className="kbd">→</span> forward
            </span>
          </div>
          <input
            aria-label="Time cursor"
            type="range"
            min={tMin}
            max={tMax}
            value={tCursor}
            onChange={(e) => setTCursor(Number(e.target.value))}
            className="w-full accent-[var(--accent)]"
            data-testid="time-slider"
          />
        </div>
      </div>
    </div>
  );
}
