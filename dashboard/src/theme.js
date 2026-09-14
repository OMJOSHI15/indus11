// Chart palette — the one place chart colours are named.
//
// Values are CSS custom properties, not hex: SVG presentation attributes
// resolve var(), so the light/dark switch in index.css repaints every chart
// without re-rendering it. Each theme's hex steps sit in its block in
// index.css, run through the dataviz validator all-pairs on that theme's card
// (a donut wraps, so first and last slots touch). Green/red failed for
// deuteranopia in both themes, which is why approve is teal.

export const DECISION_COLORS = {
  APPROVE: "var(--approve)",
  REVIEW: "var(--review)",
  BLOCK: "var(--block)",
};

export const DECISION_LABELS = { APPROVE: "Approved", REVIEW: "In review", BLOCK: "Blocked" };
export const DECISIONS = ["APPROVE", "REVIEW", "BLOCK"];

export const LAYER_COLORS = { rule: "var(--layer-rule)", graph: "var(--layer-graph)", model: "var(--layer-model)" };

export const SERIES = "var(--series)"; // single-series charts

export const CHART = {
  grid: "var(--chart-grid)",
  axis: "var(--chart-axis)",
  label: "var(--muted)",
  ink: "var(--ink)",
  ink2: "var(--ink-2)",
  surface: "var(--card)",
  track: "var(--gauge-track)",
  hover: "var(--hover)",
};

export const FONT = "-apple-system, BlinkMacSystemFont, Inter, system-ui, sans-serif";

export const axisTick = { fill: CHART.label, fontSize: 11, fontFamily: FONT };

export const tooltipStyle = {
  background: "var(--card)",
  border: "1px solid var(--line)",
  borderRadius: 10,
  fontSize: 12,
  fontFamily: FONT,
  color: CHART.ink,
  boxShadow: "0 8px 24px -8px rgba(0, 0, 0, 0.25)",
  padding: "8px 10px",
};

export const tooltipItemStyle = { color: CHART.ink };

const THEME_KEY = "indus11-theme";

/** Current theme; the inline script in index.html sets it before first paint. */
export const currentTheme = () => document.documentElement.dataset.theme ?? "light";

export function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem(THEME_KEY, theme); } catch { /* private mode: session only */ }
}

export const compact = (n) =>
  Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 }).format(n);
