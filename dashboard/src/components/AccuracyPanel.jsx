import { useEffect, useState } from "react";
import { getAccuracy } from "../api.js";
import { CHART, SERIES } from "../theme.js";
import { ChartSkeleton } from "./Charts.jsx";

const pct = (value) => `${(value * 100).toFixed(1)}%`;

/** Half-ring meter. The unfilled track is a pale step of the same blue. */
function Gauge({ label, value, note }) {
  const r = 52;
  const length = Math.PI * r;
  return (
    <figure className="gauge">
      <svg viewBox="0 0 128 76" role="img" aria-label={`${label} ${pct(value)}`}>
        <path d="M12 68 A52 52 0 0 1 116 68" fill="none" stroke={CHART.track} strokeWidth="11" strokeLinecap="round" />
        <path d="M12 68 A52 52 0 0 1 116 68" fill="none" stroke={SERIES} strokeWidth="11" strokeLinecap="round"
              strokeDasharray={`${length * value} ${length}`} />
      </svg>
      <strong>{pct(value)}</strong>
      <figcaption>{label}</figcaption>
      {note && <span className="gauge__note">{note}</span>}
    </figure>
  );
}

export default function AccuracyPanel() {
  const [report, setReport] = useState(null);
  const [state, setState] = useState("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    getAccuracy()
      .then((data) => { if (!cancelled) { setReport(data); setState("ready"); } })
      // 404 means no evaluation has been run yet: a first-run state, not an error.
      .catch((err) => { if (!cancelled) setState(String(err.message).startsWith("404") ? "empty" : "error"); });
    return () => { cancelled = true; };
  }, [attempt]);

  if (state === "loading") return <ChartSkeleton height={300} />;
  if (state === "empty") {
    return <p className="empty">No evaluation yet. Run <code>python -m scripts.evaluate</code> with the API up.</p>;
  }
  if (state === "error") {
    return (
      <div className="empty">
        Could not load evaluation results.
        <button type="button" className="button button--quiet" onClick={() => setAttempt((n) => n + 1)}>Retry</button>
      </div>
    );
  }

  const { counts, metrics, graph } = report;
  const { flagged, confusion, realistic } = metrics;
  const cells = [
    ["Approved", confusion.APPROVE],
    ["Review", confusion.REVIEW],
    ["Blocked", confusion.BLOCK],
  ];
  const max = Math.max(...cells.flatMap(([, c]) => [c.fraud, c.legit]));
  const shade = (n) => ({ background: `color-mix(in srgb, ${SERIES} ${Math.round(8 + (n / max) * 62)}%, transparent)` });

  return (
    <div className="accuracy">
      <div className="gauges">
        <Gauge label="Precision" value={flagged.precision} note="flagged that were fraud" />
        <Gauge label="Recall" value={flagged.recall} note="fraud that was caught" />
        <Gauge label="F1 score" value={flagged.f1} note="balance of both" />
      </div>

      <table className="confusion">
        <caption>{counts.total} labelled transactions: {counts.fraud} fraud, {counts.legit} legitimate</caption>
        <thead>
          <tr><th scope="col">Decision</th><th scope="col">Fraud</th><th scope="col">Legitimate</th></tr>
        </thead>
        <tbody>
          {cells.map(([label, c]) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              <td style={shade(c.fraud)}>{c.fraud}</td>
              <td style={shade(c.legit)}>{c.legit}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="card__note">
        Graph layer flagged {graph.graph_flagged} of {graph.ring_transactions} mule-ring transactions.
        {realistic && ` At a real-world fraud rate of ${realistic.prevalence * 100}%, the same detector's precision would be ${pct(realistic.precision)}.`}
      </p>
    </div>
  );
}
