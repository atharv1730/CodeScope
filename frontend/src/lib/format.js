// Small formatting + color helpers shared across views.

export function fmtNumber(n) {
  if (n == null) return "—";
  return new Intl.NumberFormat().format(n);
}

export function fmtCompact(n) {
  if (n == null) return "—";
  return new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

export function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function shortPath(path, max = 48) {
  if (!path) return "";
  if (path.length <= max) return path;
  return "…" + path.slice(path.length - max + 1);
}

export function basename(path) {
  if (!path) return "";
  const parts = path.split("/");
  return parts[parts.length - 1];
}

// Categorical palette for languages / series (colorblind-friendly-ish).
export const SERIES_COLORS = [
  "#4f46e5", "#0ea5e9", "#16a34a", "#d97706", "#db2777",
  "#7c3aed", "#0891b2", "#ca8a04", "#dc2626", "#2563eb",
];

export function colorForIndex(i) {
  return SERIES_COLORS[i % SERIES_COLORS.length];
}

// Green -> amber -> red scale for a 0..max complexity value.
export function complexityColor(value, max) {
  if (value == null || !max) return "#e2e8f0";
  const t = Math.min(1, value / max);
  // interpolate green(22,163,74) -> amber(217,119,6) -> red(220,38,38)
  const stops = [
    [22, 163, 74],
    [217, 119, 6],
    [220, 38, 38],
  ];
  const seg = t < 0.5 ? 0 : 1;
  const localT = t < 0.5 ? t / 0.5 : (t - 0.5) / 0.5;
  const a = stops[seg];
  const b = stops[seg + 1];
  const mix = a.map((c, i) => Math.round(c + (b[i] - c) * localT));
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`;
}

export function riskPill(hasVuln, severelyOutdated, outdated) {
  if (hasVuln) return { label: "Vulnerable", cls: "bg-red-50 text-danger" };
  if (severelyOutdated) return { label: "Severely outdated", cls: "bg-amber-50 text-warn" };
  if (outdated) return { label: "Outdated", cls: "bg-amber-50 text-warn" };
  return { label: "Current", cls: "bg-green-50 text-good" };
}
