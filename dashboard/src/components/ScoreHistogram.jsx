import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART_NEUTRALS, DECISION_COLORS, MONO, tooltipStyle } from "../theme.js";

// Buckets coloured by the band each one falls in: 0-39 approve, 40-69 review,
// 70+ block. The 60-79 bucket straddles the block threshold at 70, so it is
// shown as review — the lower of the two, which understates rather than
// overstates risk.
const BUCKET_COLORS = [
  DECISION_COLORS.APPROVE,
  DECISION_COLORS.APPROVE,
  DECISION_COLORS.REVIEW,
  DECISION_COLORS.REVIEW,
  DECISION_COLORS.BLOCK,
];

export default function ScoreHistogram({ distribution }) {
  if (!distribution) {
    return <div className="skeleton" style={{ height: 180 }} />;
  }

  if (distribution.total === 0) {
    return (
      <div className="empty">
        No score data yet. The histogram fills in as transactions are analyzed.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={distribution.score_histogram} barCategoryGap="22%">
        <CartesianGrid stroke={CHART_NEUTRALS.grid} vertical={false} />
        <XAxis
          dataKey="bucket"
          tick={{ fill: CHART_NEUTRALS.label, fontSize: 11, fontFamily: MONO }}
          axisLine={{ stroke: CHART_NEUTRALS.axis }}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fill: CHART_NEUTRALS.label, fontSize: 11, fontFamily: MONO }}
          axisLine={false}
          tickLine={false}
          width={32}
        />
        <Tooltip cursor={{ fill: "rgba(237,237,236,0.04)" }} contentStyle={tooltipStyle} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {distribution.score_histogram.map((entry, i) => (
            <Cell key={entry.bucket} fill={BUCKET_COLORS[i] ?? CHART_NEUTRALS.label} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
