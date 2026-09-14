// Chart palette — the one place SVG colours are defined.
//
// Recharts writes colours as SVG attributes, which cannot read CSS custom
// properties, so the values live here and index.css mirrors the ones it needs.
//
// Every set below was run through the dataviz validator on the #ffffff card
// surface, all-pairs (a donut wraps, so first and last slots touch):
//   decisions  #2a9d8f,#eda100,#d03b3b  worst CVD ΔE 11.3, normal ΔE 24.1
//   layers     #2a78d6,#4a3aa7,#e87ba4  worst CVD ΔE 13.0, normal ΔE 16.3
// Green/red failed (deutan ΔE 4.1), which is why approve is teal, not green.
// Amber and pink sit under 3:1 on white, so every chart using them carries a
// legend with counts and a tooltip.

export const DECISION_COLORS = {
  APPROVE: "#2a9d8f",
  REVIEW: "#eda100",
  BLOCK: "#d03b3b",
};

export const DECISION_LABELS = { APPROVE: "Approved", REVIEW: "In review", BLOCK: "Blocked" };
export const DECISIONS = ["APPROVE", "REVIEW", "BLOCK"];

export const LAYER_COLORS = { rule: "#2a78d6", graph: "#4a3aa7", model: "#e87ba4" };

export const SERIES = "#2a78d6"; // single-series charts

export const CHART = {
  grid: "#ebeae5",
  axis: "#c3c2b7",
  label: "#6f6e69",
  ink: "#0b0b0b",
  surface: "#ffffff",
  track: "#eef3fb",
};

export const FONT = "-apple-system, BlinkMacSystemFont, Inter, system-ui, sans-serif";

export const axisTick = { fill: CHART.label, fontSize: 11, fontFamily: FONT };

export const tooltipStyle = {
  background: "#ffffff",
  border: "1px solid rgba(11, 11, 11, 0.08)",
  borderRadius: 10,
  fontSize: 12,
  fontFamily: FONT,
  color: CHART.ink,
  boxShadow: "0 8px 24px -8px rgba(16, 24, 40, 0.18)",
  padding: "8px 10px",
};

export const compact = (n) =>
  Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 }).format(n);
