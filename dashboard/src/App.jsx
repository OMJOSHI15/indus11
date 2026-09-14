import { useCallback, useEffect, useState } from "react";
import RecentFlags from "./components/RecentFlags.jsx";
import AnalyzeForm from "./components/AnalyzeForm.jsx";
import TxDrawer from "./components/TxDrawer.jsx";
import AccuracyPanel from "./components/AccuracyPanel.jsx";
import Sheet from "./components/Sheet.jsx";
import {
  AmountBands, Card, CategoryRisk, ChartSkeleton, DecisionDonut, DecisionsByDay, ScoreHistogram, TopSignals,
} from "./components/Charts.jsx";
import { DEMO, getGraphStats, getOverview, getRecentFlags, getRiskDistribution } from "./api.js";
import { SAMPLE_DISTRIBUTION, SAMPLE_FLAGS } from "./sampleData.js";
import { moneyShort } from "./format.js";
import { DECISION_COLORS } from "./theme.js";
import {
  GaugeIcon, LayoutIcon, ListIcon, NetworkIcon, PlusIcon, RefreshIcon, WifiOffIcon,
} from "./icons.jsx";

const REFRESH_MS = 15000;

const NAV = [
  { href: "#overview", label: "Overview", Icon: LayoutIcon },
  { href: "#queue", label: "Review queue", Icon: ListIcon },
  { href: "#model", label: "Model accuracy", Icon: GaugeIcon },
  { href: "#network", label: "Graph network", Icon: NetworkIcon },
];

const share = (part, whole) => (whole ? `${((part / whole) * 100).toFixed(1)}%` : "—");

function Kpi({ label, value, sub, keyColor, tone }) {
  return (
    <div className={`kpi${tone ? ` kpi--${tone}` : ""}`}>
      <span className="kpi__label">
        {keyColor && <span className="kpi__key" style={{ background: keyColor }} aria-hidden="true" />}
        {label}
      </span>
      <span className="kpi__value">{value ?? <span className="skeleton" style={{ display: "block", width: 90, height: 30 }} />}</span>
      <span className="kpi__sub">{sub ?? " "}</span>
    </div>
  );
}

// undefined = still loading, null = this build or backend cannot provide it.
const Live = ({ data, height, children }) =>
  data === null
    ? <p className="empty" style={{ minHeight: height }}>Needs the live backend.</p>
    : children;

export default function App() {
  const [distribution, setDistribution] = useState(null);
  const [flags, setFlags] = useState(null);
  const [overview, setOverview] = useState(undefined);
  const [graphStats, setGraphStats] = useState(undefined);
  const [offline, setOffline] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [dist, recent] = await Promise.all([getRiskDistribution(), getRecentFlags(20)]);
      setDistribution(dist);
      setFlags(recent);
      setOffline(false);
      setUpdatedAt(new Date());
    } catch {
      // Backend down: labelled sample data keeps the page reviewable.
      setDistribution(SAMPLE_DISTRIBUTION);
      setFlags(SAMPLE_FLAGS);
      setOffline(true);
    }
    // Independent: the graph database can be down while MongoDB is fine.
    getOverview().then(setOverview).catch(() => setOverview(null));
    getGraphStats().then(setGraphStats).catch(() => setGraphStats(null));
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  const t = overview?.totals;
  const blocked = distribution?.decisions?.BLOCK;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">I11</span>
          <div>
            <strong>Indus11</strong>
            <span>Fraud intelligence</span>
          </div>
        </div>
        <nav aria-label="Sections">
          {NAV.map(({ href, label, Icon }) => (
            <a key={href} href={href}><Icon size={17} />{label}</a>
          ))}
        </nav>
        <div className={`status${offline ? " status--offline" : ""}`}>
          <span className="status__dot" aria-hidden="true" />
          <div>
            <strong>{DEMO ? "Sample data" : offline ? "API offline" : "Live"}</strong>
            <span>{updatedAt ? `Updated ${updatedAt.toLocaleTimeString("en-IN", { timeStyle: "short" })}` : "Connecting…"}</span>
          </div>
        </div>
      </aside>

      <main className="main" id="overview">
        <header className="page-head">
          <div>
            <h1>Fraud overview</h1>
            <p>Every transaction scored by the rule, graph and language-model layers.</p>
          </div>
          <div className="page-head__actions">
            <button type="button" className="button button--quiet" onClick={refresh}>
              <RefreshIcon size={15} /> Refresh
            </button>
            <button type="button" className="button button--primary" onClick={() => setAnalyzing(true)}>
              <PlusIcon size={15} /> Analyze transaction
            </button>
          </div>
        </header>

        {!DEMO && offline && (
          <div className="banner" role="status">
            <WifiOffIcon size={15} />
            Backend unreachable. Showing sample data; start the API and databases to see live results.
          </div>
        )}

        <section className="kpis" aria-label="Key figures">
          <Kpi label="Transactions scored" value={distribution?.total.toLocaleString("en-IN")}
               sub={overview && `${overview.by_day.length} active days`} />
          <Kpi label="Flagged for review" keyColor={DECISION_COLORS.REVIEW}
               value={distribution && (distribution.decisions.REVIEW + distribution.decisions.BLOCK).toLocaleString("en-IN")}
               sub={distribution && `${share(distribution.decisions.REVIEW + distribution.decisions.BLOCK, distribution.total)} of scored`} />
          <Kpi label="Blocked" keyColor={DECISION_COLORS.BLOCK} value={blocked?.toLocaleString("en-IN")}
               sub={distribution && `${share(blocked, distribution.total)} of scored`} />
          <Kpi label="Value flagged" value={t && moneyShort(t.flagged_amount)} sub={t && "in review or blocked"} />
          <Kpi label="Average risk score" value={t && t.avg_score} sub={t && "out of 100"} />
          <Kpi label="Layer failures" value={t?.layer_failures} tone={t?.layer_failures ? "alert" : undefined}
               sub={t && `${t.rag_pending.toLocaleString("en-IN")} explanations pending`} />
        </section>

        <div className="grid">
          <Card className="span-6" title="Decisions by day" subtitle="Approved, in review and blocked per active day">
            <Live data={overview} height={290}><DecisionsByDay overview={overview} /></Live>
          </Card>

          <Card className="span-3" title="Decision mix" subtitle="All scored transactions">
            <DecisionDonut distribution={distribution} />
          </Card>

          <Card className="span-3" title="Transaction graph" subtitle="Neo4j entities behind the graph layer">
            <span id="network" className="anchor" />
            <Live data={graphStats} height={220}>
              {graphStats === undefined ? <ChartSkeleton height={220} /> : (
                <dl className="stat-list">
                  <div><dt>Accounts</dt><dd>{graphStats.accounts.toLocaleString("en-IN")}</dd></div>
                  <div><dt>Devices</dt><dd>{graphStats.devices.toLocaleString("en-IN")}</dd></div>
                  <div><dt>IP addresses</dt><dd>{graphStats.ips.toLocaleString("en-IN")}</dd></div>
                  <div><dt>Transfers</dt><dd>{graphStats.sent.toLocaleString("en-IN")}</dd></div>
                  <div>
                    <dt><span className="kpi__key" style={{ background: DECISION_COLORS.BLOCK }} aria-hidden="true" />Known fraud accounts</dt>
                    <dd>{graphStats.fraud_seeds}</dd>
                  </div>
                  <div><dt>Fraud-adjacent accounts</dt><dd>{graphStats.fraud_adjacent}</dd></div>
                </dl>
              )}
            </Live>
          </Card>

          <Card className="span-6" title="Risk by merchant category" subtitle="Decisions within each category">
            <Live data={overview} height={340}><CategoryRisk overview={overview} /></Live>
          </Card>

          <Card className="span-6" title="Most frequent signals" subtitle="How often each flag fired on flagged transactions">
            <Live data={overview} height={340}><TopSignals overview={overview} /></Live>
          </Card>

          <Card className="span-4" title="Score distribution" subtitle="Composite risk score, 0 to 100">
            <ScoreHistogram distribution={distribution} />
          </Card>

          <Card className="span-4" title="Flag rate by amount" subtitle="Share of transactions sent to review or block">
            <Live data={overview} height={250}><AmountBands overview={overview} /></Live>
          </Card>

          <Card className="span-4 span-md-12" title="Detection accuracy" subtitle="Labelled synthetic benchmark">
            <span id="model" className="anchor" />
            <AccuracyPanel />
          </Card>

          <Card className="span-12" title="Review queue" subtitle="20 most recent review and block decisions. Select a row for details.">
            <span id="queue" className="anchor" />
            <RecentFlags flags={flags} onSelect={offline ? undefined : setSelectedId} />
          </Card>
        </div>
      </main>

      {selectedId && <TxDrawer txId={selectedId} onClose={() => setSelectedId(null)} onUpdated={refresh} />}

      {analyzing && (
        <Sheet title="Analyze a transaction" subtitle="Scores it through all three layers and adds it to the dashboard"
               onClose={() => setAnalyzing(false)}>
          <AnalyzeForm onAnalyzed={refresh} />
        </Sheet>
      )}
    </div>
  );
}
