// Diverging cool→warm palette for ROTI / probability heatmaps.
// Values 0..1 → CSS color string.
const STOPS: { stop: number; rgb: [number, number, number] }[] = [
  { stop: 0.0, rgb: [15, 27, 50] },
  { stop: 0.25, rgb: [15, 100, 130] },
  { stop: 0.5, rgb: [15, 163, 177] },
  { stop: 0.75, rgb: [247, 160, 114] },
  { stop: 1.0, rgb: [230, 57, 70] },
];

function interp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

export function rotiColor(value: number, vmin = 0, vmax = 1): string {
  const t = Math.max(0, Math.min(1, (value - vmin) / (vmax - vmin)));
  for (let i = 0; i < STOPS.length - 1; i += 1) {
    const a = STOPS[i];
    const b = STOPS[i + 1];
    if (t >= a.stop && t <= b.stop) {
      const local = (t - a.stop) / (b.stop - a.stop);
      const r = interp(a.rgb[0], b.rgb[0], local);
      const g = interp(a.rgb[1], b.rgb[1], local);
      const bl = interp(a.rgb[2], b.rgb[2], local);
      return `rgb(${r.toFixed(0)} ${g.toFixed(0)} ${bl.toFixed(0)})`;
    }
  }
  const last = STOPS[STOPS.length - 1].rgb;
  return `rgb(${last.join(" ")})`;
}

export function constellationColor(sat: string): string {
  const head = sat.charAt(0).toUpperCase();
  switch (head) {
    case "G":
      return "#0FA3B1";
    case "R":
      return "#9B5DE5";
    case "E":
      return "#FFC857";
    case "C":
      return "#E63946";
    default:
      return "#6C757D";
  }
}
