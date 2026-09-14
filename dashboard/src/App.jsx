import { useCallback, useEffect, useState } from "react";
import ScoreHistogram from "./components/ScoreHistogram.jsx";
import RecentFlags from "./components/RecentFlags.jsx";
import AnalyzeForm from "./components/AnalyzeForm.jsx";
import TxDrawer from "./components/TxDrawer.jsx";
import AccuracyPanel from "./components/AccuracyPanel.jsx";
import { DEMO, getRecentFlags, getRiskDistribution } from "./api.js";
import useCountUp from "./useCountUp.js";
import { SAMPLE_DISTRIBUTION, SAMPLE_FLAGS } from "./sampleData.js";
import { WifiOffIcon } from "./icons.jsx";

const REFRESH_MS = 10000;

function CountUp({ value }) {
  return useCountUp(value).toLocaleString("en-IN");
}

// Ordered by severity, not alphabetically — the bar reads left to right as
// risk increases, so the block segment always sits at the sharp end.
const DECISIONS = [
  { key: "APPROVE", label: "Approved", cls: "approve" },
  { key: "REVIEW", label: "In review", cls: "review" },
  { key: "BLOCK", label: "Blocked", cls: "block" },
];

export default function App() {
  const [distribution, setDistribution] = useState(null);
  const [flags, setFlags] = useState(null);
  const [offline, setOffline] = useState(false);
  const [selectedId, setSelectedId] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [dist, recent] = await Promise.all([getRiskDistribution(), getRecentFlags(20)]);
      setDistribution(dist);
      setFlags(recent);
      setOffline(false);
    } catch {
      // Backend down: fall back to labeled sample data so the UI stays useful
      setDistribution(SAMPLE_DISTRIBUTION);
      setFlags(SAMPLE_FLAGS);
      setOffline(true);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  const loading = distribution === null;
  const total = distribution?.total ?? 0;
  const count = (key) => distribution?.decisions?.[key] ?? 0;
  const waiting = count("REVIEW");

  return (
    <>
      <header className="toolbar">
        <div className="toolbar__inner">
          <div className="brand">
            <span className="brand__mark" aria-hidden="true">I11</span>
            <span className="brand__name">Indus11</span>
          </div>
          <span className="toolbar__title">Fraud review</span>
          <span className={`status-pill${offline ? " offline" : ""}`}>
            <span className="dot" aria-hidden="true" />
            {DEMO ? "Sample data" : offline ? "API offline" : "Live"}
          </span>
        </div>
      </header>

      <main className="layout">
        {!DEMO && offline && (
          <div className="banner" role="status">
            <WifiOffIcon size={15} />
            Backend unreachable. Showing sample data; start the API and databases to see live results.
          </div>
        )}

        <section className="overview" aria-busy={loading}>
          <div className="overview__lead">
            <h1>
              {loading ? <span className="skeleton" style={{ display: "inline-block", width: 90, height: 40 }} /> : <CountUp value={waiting} />}
              <span> waiting for review</span>
            </h1>
            <p className="dim">
              {loading ? "Loading…" : `${total.toLocaleString("en-IN")} transactions analysed so far`}
            </p>
          </div>

          <div className="overview__split">
            <div
              className="split-bar"
              role="img"
              aria-label={loading ? "Decision mix loading" : DECISIONS.map((d) => `${count(d.key)} ${d.label}`).join(", ")}
            >
              {DECISIONS.map(({ key, cls }) => (
                <span
                  key={key}
                  className={`split-bar__seg ${cls}`}
                  // flex-grow, not width: the segments always fill the bar even
                  // before any transaction has been scored.
                  style={{ flexGrow: Math.max(count(key), total ? 0 : 1) }}
                />
              ))}
            </div>
            <ul className="split-legend">
              {DECISIONS.map(({ key, label, cls }) => (
                <li key={key} className="split-legend__item">
                  <span className="split-legend__label"><span className={`dot ${cls}`} aria-hidden="true" />{label}</span>
                  <span className="split-legend__value">{count(key).toLocaleString("en-IN")}</span>
                  <span className="split-legend__pct">
                    {total > 0 ? `${((count(key) / total) * 100).toFixed(1)}%` : "—"}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <div className="workspace">
          <section className="panel panel--queue" aria-busy={flags === null}>
            <div className="panel__head">
              <h2>Review queue</h2>
              <span className="dim small">20 most recent review and block decisions</span>
            </div>
            <RecentFlags flags={flags} onSelect={offline ? undefined : setSelectedId} />
          </section>

          <aside className="panel panel--analyze">
            <div className="panel__head"><h2>Analyze a transaction</h2></div>
            <AnalyzeForm onAnalyzed={refresh} />
          </aside>
        </div>

        <div className="insights">
          <section className="panel" aria-busy={loading}>
            <div className="panel__head"><h2>Score distribution</h2></div>
            <ScoreHistogram distribution={distribution} />
          </section>
          <section className="panel">
            <div className="panel__head">
              <h2>Detection accuracy</h2>
              <span className="dim small">Synthetic benchmark</span>
            </div>
            <AccuracyPanel offline={offline} />
          </section>
        </div>
      </main>

      {selectedId && (
        <TxDrawer txId={selectedId} onClose={() => setSelectedId(null)} onUpdated={refresh} />
      )}
    </>
  );
}
