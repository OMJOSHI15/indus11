import { useCallback, useEffect, useState } from "react";
import DecisionDonut from "./components/DecisionDonut.jsx";
import ScoreHistogram from "./components/ScoreHistogram.jsx";
import RecentFlags from "./components/RecentFlags.jsx";
import AnalyzeForm from "./components/AnalyzeForm.jsx";
import TxModal from "./components/TxModal.jsx";
import AccuracyPanel from "./components/AccuracyPanel.jsx";
import { DEMO, getRecentFlags, getRiskDistribution } from "./api.js";
import useCountUp from "./useCountUp.js";
import { SAMPLE_DISTRIBUTION, SAMPLE_FLAGS } from "./sampleData.js";
import { WifiOffIcon } from "./icons.jsx";

const REFRESH_MS = 10000;

/** KPI figure that counts up when the value changes. */
function KpiValue({ value }) {
  const shown = useCountUp(value);
  return <div className="value">{shown.toLocaleString()}</div>;
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
      const [dist, recent] = await Promise.all([
        getRiskDistribution(),
        getRecentFlags(20),
      ]);
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

  const decisionCount = (key) => distribution?.decisions?.[key] ?? 0;

  return (
    <div className="layout">
      <header className="topbar">
        <div className="logo-mark" aria-hidden="true">I11</div>
        <div>
          <h1>Indus11</h1>
          <div className="subtitle">Transaction risk &amp; fraud decisioning</div>
        </div>
        <div className="spacer" />
        <span className={`status-pill${offline ? " offline" : ""}`}>
          <span className="dot" aria-hidden="true" />
          {DEMO ? "Sample data" : offline ? "API offline" : "Live"}
        </span>
      </header>

      {DEMO ? null : (
        offline && (
          <div className="banner" role="status">
            <WifiOffIcon size={15} />
            Backend unreachable. Showing sample data; start the API and databases to
            see live results.
          </div>
        )
      )}

      <section className="stat-lead">
        <div className="stat-lead__figure">
          <span className="stat-lead__label">Transactions analysed</span>
          {loading
            ? <div className="skeleton" style={{ width: 150, height: 56 }} />
            : <KpiValue value={total} />}
        </div>

        <div className="stat-lead__split">
          <div
            className="split-bar"
            role="img"
            aria-label={
              loading
                ? "Decision mix loading"
                : DECISIONS.map((d) => `${decisionCount(d.key)} ${d.label}`).join(", ")
            }
          >
            {DECISIONS.map(({ key, cls }) => (
              <span
                key={key}
                className={`split-bar__seg ${cls}`}
                // flex-grow, not width: the segments always fill the bar even
                // before any transaction has been scored.
                style={{ flexGrow: Math.max(decisionCount(key), total ? 0 : 1) }}
              />
            ))}
          </div>

          <ul className="split-legend">
            {DECISIONS.map(({ key, label, cls }) => (
              <li key={key} className={`split-legend__item ${cls}`}>
                <span className="split-legend__label">{label}</span>
                {loading ? (
                  <div className="skeleton" style={{ width: 48, height: 24 }} />
                ) : (
                  <>
                    <span className="split-legend__value">
                      {decisionCount(key).toLocaleString()}
                    </span>
                    <span className="split-legend__pct">
                      {total > 0 ? `${((decisionCount(key) / total) * 100).toFixed(1)}%` : "—"}
                    </span>
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <div className="grid">
        <section className="panel" aria-busy={loading}>
          <h2>Decision mix</h2>
          <DecisionDonut distribution={distribution} />
        </section>

        <section className="panel" aria-busy={loading}>
          <h2>Composite score distribution</h2>
          <ScoreHistogram distribution={distribution} />
        </section>

        <section className="panel">
          <h2>Analyze a transaction</h2>
          <AnalyzeForm onAnalyzed={refresh} />
        </section>

        <section className="panel wide">
          <h2>Detection accuracy on the synthetic benchmark</h2>
          <AccuracyPanel offline={offline} />
        </section>

        <section className="panel wide" aria-busy={flags === null}>
          <h2>Recent flags for review and block</h2>
          <RecentFlags flags={flags} onSelect={offline ? undefined : setSelectedId} />
        </section>
      </div>

      {selectedId && (
        <TxModal
          txId={selectedId}
          onClose={() => setSelectedId(null)}
          onUpdated={refresh}
        />
      )}
    </div>
  );
}
