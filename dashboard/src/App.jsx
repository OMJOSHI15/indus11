import { useCallback, useEffect, useState } from "react";
import AnalyzeForm from "./components/AnalyzeForm.jsx";
import TxDrawer from "./components/TxDrawer.jsx";
import Sheet from "./components/Sheet.jsx";
import { Accuracy, Network, Overview, Queue, Signals } from "./pages.jsx";
import { DEMO, getGraphStats, getOverview, getRecentFlags, getRiskDistribution } from "./api.js";
import { SAMPLE_DISTRIBUTION, SAMPLE_FLAGS } from "./sampleData.js";
import { currentTheme, setTheme } from "./theme.js";
import {
  GaugeIcon, LayoutIcon, ListIcon, MoonIcon, NetworkIcon, PlusIcon, RefreshIcon, ScanSearchIcon, SunIcon, WifiOffIcon,
} from "./icons.jsx";

const REFRESH_MS = 15000;

const ROUTES = [
  { path: "overview", label: "Overview", Icon: LayoutIcon, Page: Overview,
    title: "Fraud overview", lede: "Every transaction scored by the rule, graph and language-model layers." },
  { path: "queue", label: "Review queue", Icon: ListIcon, Page: Queue,
    title: "Review queue", lede: "Transactions the pipeline handed to a person. Select a row for the full decision." },
  { path: "signals", label: "Signals", Icon: ScanSearchIcon, Page: Signals,
    title: "Signals", lede: "Which flags fire, and how the composite score is spread." },
  { path: "accuracy", label: "Model accuracy", Icon: GaugeIcon, Page: Accuracy,
    title: "Model accuracy", lede: "Measured on the labelled synthetic benchmark, not on live traffic." },
  { path: "network", label: "Graph network", Icon: NetworkIcon, Page: Network,
    title: "Graph network", lede: "Accounts, devices and addresses behind the Neo4j layer." },
];

// Routes live in the hash: no server rewrite rules, and the back button, bookmarks
// and a reload all keep the page you were on. An unknown hash falls back to the first route.
const hashRoute = () => window.location.hash.replace(/^#\/?/, "").split("?")[0];
const routeFor = (path) => ROUTES.find((r) => r.path === path) ?? ROUTES[0];

function useRoute() {
  const [path, setPath] = useState(hashRoute);
  useEffect(() => {
    const onChange = () => {
      setPath(hashRoute());
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return routeFor(path);
}

export default function App() {
  const [distribution, setDistribution] = useState(null);
  const [flags, setFlags] = useState(null);
  const [overview, setOverview] = useState(undefined);
  const [graphStats, setGraphStats] = useState(undefined);
  const [offline, setOffline] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [theme, setThemeState] = useState(currentTheme);
  const route = useRoute();

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  };

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

  useEffect(() => {
    document.title = `${route.title} · Nirix`;
  }, [route]);

  const { Page } = route;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <img className="brand__mark" src={`${import.meta.env.BASE_URL}nirix-icon.png`} alt="" width="34" height="34" />
          <div>
            <strong>Nirix</strong>
            <span>Fraud intelligence</span>
          </div>
        </div>
        <nav aria-label="Pages">
          {ROUTES.map(({ path, label, Icon }) => {
            const active = path === route.path;
            return (
              <a key={path} href={`#/${path}`} className={active ? "is-active" : undefined}
                 aria-current={active ? "page" : undefined}>
                <Icon size={17} />{label}
              </a>
            );
          })}
        </nav>
        <div className={`status${offline ? " status--offline" : ""}`}>
          <span className="status__dot" aria-hidden="true" />
          <div>
            <strong>{DEMO ? "Sample data" : offline ? "API offline" : "Live"}</strong>
            <span>{updatedAt ? `Updated ${updatedAt.toLocaleTimeString("en-IN", { timeStyle: "short" })}` : "Connecting…"}</span>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="page-head">
          <div>
            <h1>{route.title}</h1>
            <p>{route.lede}</p>
          </div>
          <div className="page-head__actions">
            <button type="button" className="button button--quiet button--icon" onClick={toggleTheme}
                    aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                    title={theme === "dark" ? "Light mode" : "Dark mode"}>
              {theme === "dark" ? <SunIcon size={16} /> : <MoonIcon size={16} />}
            </button>
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

        <Page distribution={distribution} overview={overview} graphStats={graphStats}
              flags={flags} offline={offline} onSelect={setSelectedId} />
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
