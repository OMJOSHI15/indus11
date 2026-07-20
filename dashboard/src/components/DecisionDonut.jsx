import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { ScanSearchIcon } from "../icons.jsx";

const COLORS = { APPROVE: "#34d399", REVIEW: "#fbbf24", BLOCK: "#f87171" };

const tooltipStyle = {
  background: "#182136",
  border: "1px solid #26304a",
  borderRadius: 8,
  fontSize: 12,
  color: "#e8edf7",
};

export default function DecisionDonut({ distribution }) {
  if (!distribution) {
    return <div className="skeleton" style={{ height: 180 }} />;
  }

  const { decisions, total } = distribution;
  const data = Object.entries(decisions).map(([name, value]) => ({ name, value }));

  if (total === 0) {
    return (
      <div className="empty">
        <span className="icon"><ScanSearchIcon size={28} /></span>
        No transactions analyzed yet.
        <span>Submit one in the “Analyze a transaction” panel.</span>
      </div>
    );
  }

  return (
    <div className="donut-wrap">
      <div style={{ position: "relative", width: "55%", height: 180 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={52}
              outerRadius={76}
              paddingAngle={3}
              strokeWidth={0}
              isAnimationActive={false}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={COLORS[entry.name]} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <div>
            <div className="n">{total.toLocaleString()}</div>
            <div className="l">total</div>
          </div>
        </div>
      </div>

      <div className="legend" role="list" aria-label="Decision counts">
        {data.map(({ name, value }) => (
          <div key={name} className="row" role="listitem">
            <span className="swatch" style={{ background: COLORS[name] }} aria-hidden="true" />
            {name}
            <span className="count">
              {value.toLocaleString()}
              {total > 0 && ` · ${((value / total) * 100).toFixed(0)}%`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
