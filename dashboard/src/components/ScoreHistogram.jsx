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

// Buckets colored by decision band: 0-39 approve, 40-69 review, 70+ block
const BUCKET_COLORS = ["#34d399", "#34d399", "#fbbf24", "#f87171", "#f87171"];

const tooltipStyle = {
  background: "#182136",
  border: "1px solid #26304a",
  borderRadius: 8,
  fontSize: 12,
  color: "#e8edf7",
};

export default function ScoreHistogram({ distribution }) {
  if (!distribution) {
    return <div className="skeleton" style={{ height: 180 }} />;
  }

  if (distribution.total === 0) {
    return (
      <div className="empty">
        No score data yet — the histogram fills in as transactions are analyzed.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={distribution.score_histogram} barCategoryGap="22%">
        <CartesianGrid stroke="#1d2740" vertical={false} />
        <XAxis
          dataKey="bucket"
          tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "Fira Code" }}
          axisLine={{ stroke: "#26304a" }}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "Fira Code" }}
          axisLine={false}
          tickLine={false}
          width={32}
        />
        <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} contentStyle={tooltipStyle} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {distribution.score_histogram.map((entry, i) => (
            <Cell key={entry.bucket} fill={BUCKET_COLORS[i] ?? "#3b82f6"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
