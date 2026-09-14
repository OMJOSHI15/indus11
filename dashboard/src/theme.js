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
  APPROVE: "#30d158",
  REVIEW: "#ff9f0a",
  BLOCK: "#ff453a",
};

export const CHART_NEUTRALS = {
  grid: "rgba(84, 84, 88, 0.36)",
  axis: "rgba(84, 84, 88, 0.6)",
  label: "rgba(235, 235, 245, 0.52)",
  border: "rgba(255, 255, 255, 0.08)",
  text: "#f5f5f7",
};

export const MONO = "SF Mono, ui-monospace, JetBrains Mono, monospace";

export const tooltipStyle = {
  background: "rgba(30, 30, 33, 0.78)",
  backdropFilter: "saturate(180%) blur(20px)",
  WebkitBackdropFilter: "saturate(180%) blur(20px)",
  border: `0.5px solid ${CHART_NEUTRALS.border}`,
  borderRadius: 10,
  fontSize: 12,
  fontFamily: "-apple-system, BlinkMacSystemFont, Inter, system-ui, sans-serif",
  color: CHART_NEUTRALS.text,
  boxShadow: "0 12px 32px -12px rgba(0, 0, 0, 0.75)",
};
