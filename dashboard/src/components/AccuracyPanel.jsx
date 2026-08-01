import { useEffect, useState } from "react";
import { getAccuracy } from "../api.js";

// Percent with one decimal; metrics arrive as 0..1 floats.
const pct = (value) => `${(value * 100).toFixed(1)}%`;

const DECISIONS = ["APPROVE", "REVIEW", "BLOCK"];

export default function AccuracyPanel() {
  const [report, setReport] = useState(null);
  const [state, setState] = useState("loading"); // loading | ready | empty | error

  useEffect(() => {
    let cancelled = false;
    getAccuracy()
      .then((data) => {
        if (cancelled) return;
        setReport(data);
        setState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        // 404 means "no evaluation has been run yet" — a normal first-run state,
        // not a failure worth showing as an error.
        setState(String(err.message).startsWith("404") ? "empty" : "error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state === "loading") {
    return (
      <div className="accuracy">
        <div className="skeleton" style={{ height: 64, marginBottom: 12 }} />
        <div className="skeleton" style={{ height: 120 }} />
      </div>
    );
  }

  if (state === "empty") {
    return (
      <p className="empty">
        No evaluation has been run yet. Run{" "}
        <code>python -m scripts.evaluate</code> with the API up to measure precision
        and recall on the synthetic dataset.
      </p>
    );
  }

  if (state === "error") {
    return <p className="empty">Could not load evaluation results.</p>;
  }

  const { counts, metrics, graph, suggested_thresholds: suggested } = report;
  const { flagged, blocked, confusion } = metrics;

  return (
    <div className="accuracy">
      <div className="metric-row">
        <div className="metric">
          <div className="metric-label">Precision</div>
          <div className="metric-value">{pct(flagged.precision)}</div>
          <div className="metric-note">of flagged were fraud</div>
        </div>
        <div className="metric">
          <div className="metric-label">Recall</div>
          <div className="metric-value">{pct(flagged.recall)}</div>
          <div className="metric-note">of fraud was caught</div>
        </div>
        <div className="metric">
          <div className="metric-label">F1</div>
          <div className="metric-value">{pct(flagged.f1)}</div>
          <div className="metric-note">review + block</div>
        </div>
        <div className="metric">
          <div className="metric-label">Ring recall</div>
          <div className="metric-value">{pct(graph.recall)}</div>
          <div className="metric-note">
            {graph.graph_flagged}/{graph.ring_transactions} mule-ring hops
          </div>
        </div>
      </div>

      <table className="confusion">
        <caption>
          Confusion matrix — {counts.total.toLocaleString("en-IN")} transactions
          ({counts.fraud} fraud / {counts.legit} legitimate)
        </caption>
        <thead>
          <tr>
            <th scope="col">Decision</th>
            <th scope="col">Actually fraud</th>
            <th scope="col">Actually legitimate</th>
          </tr>
        </thead>
        <tbody>
          {DECISIONS.map((decision) => (
            <tr key={decision}>
              <th scope="row">
                <span className={`badge ${decision}`}>{decision}</span>
              </th>
              <td>{confusion[decision].fraud}</td>
              <td>{confusion[decision].legit}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="accuracy-footnote">
        Block-only view: precision {pct(blocked.precision)}, recall{" "}
        {pct(blocked.recall)}. Best bands by F1 — review ≥ {suggested.review_threshold},
        block ≥ {suggested.block_threshold}. Measured on synthetic data, where fraud is
        far denser than a real payment feed, so precision here is optimistic.
      </p>
    </div>
  );
}
