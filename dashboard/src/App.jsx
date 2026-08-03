import { useCallback, useEffect, useState } from "react";
import DecisionDonut from "./components/DecisionDonut.jsx";
import ScoreHistogram from "./components/ScoreHistogram.jsx";
import RecentFlags from "./components/RecentFlags.jsx";
import AnalyzeForm from "./components/AnalyzeForm.jsx";
import TxModal from "./components/TxModal.jsx";
import AccuracyPanel from "./components/AccuracyPanel.jsx";
import { DEMO, getRecentFlags, getRiskDistribution } from "./api.js";
import { SAMPLE_DISTRIBUTION, SAMPLE_FLAGS } from "./sampleData.js";
import {
  ActivityIcon,
  AlertTriangleIcon,
  BanIcon,
  CheckCircleIcon,
  ShieldIcon,
  WifiOffIcon,
} from "./icons.jsx";

const REFRESH_MS = 10000;

const KPIS = [
  { key: "total", label: "Analyzed", icon: ActivityIcon },
  { key: "APPROVE", label: "Approved", icon: CheckCircleIcon },
  { key: "REVIEW", label: "In review", icon: AlertTriangleIcon },
  { key: "BLOCK", label: "Blocked", icon: BanIcon },
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

  const kpiValue = (key) =>
    key === "total" ? total : distribution?.decisions?.[key] ?? 0;

  return (
    <div className="layout">
      <header className="topbar">
        <div className="logo-mark">
          <ShieldIcon size={20} label="Indus11 logo" />
        </div>
        <div>
          <h1>Indus11</h1>
          <div className="subtitle">AI Financial Risk &amp; Fraud Decision Engine</div>
        </div>
        <div className="spacer" />
        <span className={`status-pill${offline || DEMO ? " offline" : ""}`}>
          <span className="dot" aria-hidden="true" />
          {DEMO ? "Demo data" : offline ? "API offline" : "Live"}
        </span>
      </header>

      {DEMO ? (
        <div className="banner" role="status">
          <WifiOffIcon size={15} />
          <span>
            Static demo — real results captured from a local run of the full stack.
            The backend needs four databases and a local language model, so scoring
            a new transaction is disabled here. Run it yourself with{" "}
            <code>docker compose up</code>.
          </span>
        </div>
      ) : (
        offline && (
          <div className="banner" role="status">
            <WifiOffIcon size={15} />
            Backend unreachable — showing sample data. Start the API and databases to
            see live results.
          </div>
        )
      )}

      <div className="kpi-row">
        {KPIS.map(({ key, label, icon: Kicon }) => (
          <div key={key} className={`kpi ${key === "total" ? "total" : key.toLowerCase()}`}>
            <div className="icon-chip">
              <Kicon size={18} />
            </div>
            <div>
              <div className="label">{label}</div>
              {loading ? (
                <div className="skeleton" style={{ width: 56, height: 28 }} />
              ) : (
                <>
                  <div className="value">{kpiValue(key).toLocaleString()}</div>
                  {key !== "total" && total > 0 && (
                    <div className="pct">
                      {((kpiValue(key) / total) * 100).toFixed(1)}%
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
      </div>

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
          <h2>Detection accuracy — synthetic benchmark</h2>
          <AccuracyPanel />
        </section>

        <section className="panel wide" aria-busy={flags === null}>
          <h2>Recent flags — review &amp; block</h2>
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
