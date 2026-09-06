// Chart palette — the one place SVG colours are defined.
//
// Recharts sets colours as SVG attributes, which cannot read the CSS custom
// properties in index.css, so the values live here too. They are deliberately
// the same hexes as --approve / --review / --block: when a decision colour
// changes it has to change in both files, and having them together in one
// module makes that obvious rather than leaving literals scattered per chart.
//
// The system rule these follow: colour is signal. Nothing in a chart is
// coloured unless it encodes a decision. Axes, grids and labels stay neutral.

export const DECISION_COLORS = {
  APPROVE: "#6f9e78",
  REVIEW: "#c39a4e",
  BLOCK: "#c2645a",
};

export const CHART_NEUTRALS = {
  grid: "#232427",
  axis: "#303135",
  label: "#8d8d88",
  surface: "#191a1c",
  border: "#303135",
  text: "#ededec",
};

export const MONO = "JetBrains Mono, ui-monospace, monospace";

export const tooltipStyle = {
  background: CHART_NEUTRALS.surface,
  border: `1px solid ${CHART_NEUTRALS.border}`,
  borderRadius: 8,
  fontSize: 12,
  fontFamily: MONO,
  color: CHART_NEUTRALS.text,
  boxShadow: "0 12px 32px -12px rgba(0, 0, 0, 0.75)",
};
