import { useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  CHART, DECISIONS, DECISION_COLORS, DECISION_LABELS, LAYER_COLORS, SERIES,
  axisTick, compact, tooltipItemStyle, tooltipStyle,
} from "../theme.js";
import { LAYERS, humanize, layerOf } from "../signals.js";

const pct = (part, whole) => (whole ? `${((part / whole) * 100).toFixed(1)}%` : "—");
const BAR = 24; // thickest a bar may get; the rest of the band stays air
const INK_2 = CHART.ink2;

export function Card({ title, subtitle, action, className = "", children }) {
  return (
    <section className={`card ${className}`}>
      <header className="card__head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </header>
      {children}
    </section>
  );
}

export function Legend({ items }) {
  return (
    <ul className="legend">
      {items.map(({ color, label }) => (
        <li key={label}>
          <span className="legend__key" style={{ background: color }} aria-hidden="true" />
          <span className="legend__label">{label}</span>
        </li>
      ))}
    </ul>
  );
}

export const ChartSkeleton = ({ height = 240 }) => <div className="skeleton" style={{ height }} />;

const DECISION_LEGEND = DECISIONS.map((d) => ({ color: DECISION_COLORS[d], label: DECISION_LABELS[d] }));
const cursor = { fill: CHART.hover };
const shareOfRow = (v, name, item) => [`${v.toLocaleString("en-IN")} (${pct(v, item.payload.total)})`, name];

const stackBars = (radiusEnd) =>
  DECISIONS.map((d, i) => (
    <Bar key={d} dataKey={d} name={DECISION_LABELS[d]} stackId="decision" fill={DECISION_COLORS[d]}
         stroke={CHART.surface} strokeWidth={1.5} maxBarSize={BAR} isAnimationActive={false}
         radius={i === DECISIONS.length - 1 ? radiusEnd : 0} />
  ));

/* ── Decision mix ───────────────────────────────────────────────────────── */
export function DecisionDonut({ distribution }) {
  if (!distribution) return <ChartSkeleton height={220} />;
  const { decisions, total } = distribution;
  const data = DECISIONS.map((d) => ({ name: DECISION_LABELS[d], key: d, value: decisions[d] }));
  return (
    <div className="donut">
      <div className="donut__chart" role="img"
           aria-label={DECISIONS.map((d) => `${decisions[d]} ${DECISION_LABELS[d]}`).join(", ")}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="66%" outerRadius="94%"
                 paddingAngle={1.5} stroke={CHART.surface} strokeWidth={2} startAngle={90} endAngle={-270}
                 isAnimationActive={false}>
              {data.map((e) => <Cell key={e.key} fill={DECISION_COLORS[e.key]} />)}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} formatter={(v, name) => [`${v.toLocaleString("en-IN")} (${pct(v, total)})`, name]} />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut__center">
          <strong>{total.toLocaleString("en-IN")}</strong>
          <span>scored</span>
        </div>
      </div>
      <ul className="legend legend--stacked">
        {DECISIONS.map((d) => (
          <li key={d}>
            <span className="legend__key" style={{ background: DECISION_COLORS[d] }} aria-hidden="true" />
            <span className="legend__label">{DECISION_LABELS[d]}</span>
            <span className="legend__value">{decisions[d].toLocaleString("en-IN")}</span>
            <span className="legend__pct">{pct(decisions[d], total)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── Decisions by day ───────────────────────────────────────────────────── */
const dayLabel = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

export function DecisionsByDay({ overview }) {
  const [mode, setMode] = useState("count");
  if (!overview) return <ChartSkeleton height={290} />;
  const data = overview.by_day.map((r) => ({ ...r, label: dayLabel(r.day) }));
  const share = mode === "share";
  return (
    <>
      <div className="card__toolbar">
        <Legend items={DECISION_LEGEND} />
        <div className="segmented" role="group" aria-label="Scale">
          {[["count", "Count"], ["share", "Share"]].map(([key, label]) => (
            <button key={key} type="button" className="segmented__item" aria-pressed={mode === key}
                    onClick={() => setMode(key)}>{label}</button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} stackOffset={share ? "expand" : "none"} margin={{ top: 8, right: 4, left: -8, bottom: 0 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis dataKey="label" tick={axisTick} axisLine={{ stroke: CHART.axis }} tickLine={false} />
          <YAxis tick={axisTick} axisLine={false} tickLine={false} width={44}
                 tickFormatter={(v) => (share ? `${Math.round(v * 100)}%` : compact(v))} />
          <Tooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} cursor={cursor} formatter={shareOfRow} />
          {stackBars([4, 4, 0, 0])}
        </BarChart>
      </ResponsiveContainer>
      <p className="card__note">Days without scored transactions are left out. The 31 Aug spike is the evaluation runs.</p>
    </>
  );
}

/* ── Risk by merchant category ──────────────────────────────────────────── */
export function CategoryRisk({ overview }) {
  if (!overview) return <ChartSkeleton height={340} />;
  const data = overview.by_category.map((r) => ({ ...r, label: humanize(r.category) }));
  return (
    <>
      <Legend items={DECISION_LEGEND} />
      <ResponsiveContainer width="100%" height={data.length * 28 + 36}>
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={CHART.grid} horizontal={false} />
          <XAxis type="number" tick={axisTick} axisLine={false} tickLine={false} tickFormatter={compact} />
          <YAxis type="category" dataKey="label" tick={{ ...axisTick, fill: INK_2 }} axisLine={false} tickLine={false} width={112} />
          <Tooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} cursor={cursor} formatter={shareOfRow} />
          {stackBars([0, 4, 4, 0])}
        </BarChart>
      </ResponsiveContainer>
    </>
  );
}

/* ── Most frequent signals ──────────────────────────────────────────────── */
export function TopSignals({ overview }) {
  if (!overview) return <ChartSkeleton height={340} />;
  const flagged = overview.totals.flagged;
  const data = overview.signals.map((s) => ({ ...s, label: humanize(s.code), layer: layerOf(s.code) }));
  if (!data.length) return <p className="empty">No signals have fired yet.</p>;
  return (
    <>
      <Legend items={LAYERS.map(({ key, label }) => ({ color: LAYER_COLORS[key], label }))} />
      <ResponsiveContainer width="100%" height={data.length * 28 + 36}>
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 40, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={CHART.grid} horizontal={false} />
          <XAxis type="number" tick={axisTick} axisLine={false} tickLine={false} tickFormatter={compact} />
          <YAxis type="category" dataKey="label" tick={{ ...axisTick, fill: INK_2 }} axisLine={false} tickLine={false} width={160} />
          <Tooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} cursor={cursor}
                   formatter={(v, _n, item) => [`${v} of ${flagged} flagged (${pct(v, flagged)})`,
                     LAYERS.find((l) => l.key === item.payload.layer)?.label]} />
          <Bar dataKey="count" maxBarSize={16} radius={[0, 4, 4, 0]} isAnimationActive={false}>
            {data.map((d) => <Cell key={d.code} fill={LAYER_COLORS[d.layer]} />)}
            <LabelList dataKey="count" position="right" style={{ ...axisTick, fill: INK_2 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </>
  );
}

/* ── Flag rate by amount ────────────────────────────────────────────────── */
export function AmountBands({ overview }) {
  if (!overview) return <ChartSkeleton height={250} />;
  const data = overview.by_amount.map((b) => ({ ...b, rate: b.total ? b.flagged / b.total : 0 }));
  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} margin={{ top: 24, right: 4, left: -8, bottom: 0 }}>
        <CartesianGrid stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="band" tick={axisTick} axisLine={{ stroke: CHART.axis }} tickLine={false} interval={0} />
        <YAxis tick={axisTick} axisLine={false} tickLine={false} width={44} domain={[0, 1]}
               tickFormatter={(v) => `${Math.round(v * 100)}%`} />
        <Tooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} cursor={cursor}
                 formatter={(_v, _n, item) => [`${item.payload.flagged} of ${item.payload.total} flagged`, "Flag rate"]} />
        <Bar dataKey="rate" fill={SERIES} maxBarSize={36} radius={[4, 4, 0, 0]} isAnimationActive={false}>
          <LabelList dataKey="rate" position="top" formatter={(v) => `${Math.round(v * 100)}%`}
                     style={{ ...axisTick, fill: INK_2, fontWeight: 600 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ── Composite score distribution ───────────────────────────────────────── */
// Buckets take the band they mostly fall in: 0-39 approve, 40-69 review, 70+
// block. 60-79 straddles 70 and is shown as review, understating rather than
// overstating risk.
const BUCKET_DECISION = ["APPROVE", "APPROVE", "REVIEW", "REVIEW", "BLOCK"];

export function ScoreHistogram({ distribution }) {
  if (!distribution) return <ChartSkeleton height={250} />;
  return (
    <>
      <Legend items={DECISION_LEGEND} />
      <ResponsiveContainer width="100%" height={226}>
        <BarChart data={distribution.score_histogram} margin={{ top: 24, right: 4, left: -8, bottom: 0 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis dataKey="bucket" tick={axisTick} axisLine={{ stroke: CHART.axis }} tickLine={false} />
          <YAxis tick={axisTick} axisLine={false} tickLine={false} width={44} tickFormatter={compact} />
          <Tooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} cursor={cursor} formatter={(v) => [v.toLocaleString("en-IN"), "Transactions"]} />
          <Bar dataKey="count" maxBarSize={36} radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {distribution.score_histogram.map((b, i) => <Cell key={b.bucket} fill={DECISION_COLORS[BUCKET_DECISION[i]]} />)}
            <LabelList dataKey="count" position="top" formatter={compact} style={{ ...axisTick, fill: INK_2 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </>
  );
}
