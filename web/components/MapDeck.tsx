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

// Free demo style hosted by MapLibre. Avoids any token requirement; in
// production we'll switch to Protomaps PMTiles for offline-style basemap.
const STYLE_URL = "https://demotiles.maplibre.org/style.json";

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
      style: STYLE_URL,
      center: [-50, -10],
      zoom: 3.6,
      pitch: 0,
      attributionControl: { compact: true },
    });
    map.dragRotate.disable();
    map.touchZoomRotate.disableRotation();
    mapRef.current = map;

    map.on("load", () => {
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
      map.addLayer({
        id: "stations-labels",
        source: "stations",
        type: "symbol",
        layout: {
          "text-field": ["get", "id"],
          "text-size": 11,
          "text-offset": [0, 1.1],
          "text-anchor": "top",
          "text-allow-overlap": true,
        },
        paint: {
          "text-color": "#FAFAFC",
          "text-halo-color": "#0a0e1a",
          "text-halo-width": 1.2,
        },
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
    <div className="relative h-full">
      <div ref={ref} className="absolute inset-0" />

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
