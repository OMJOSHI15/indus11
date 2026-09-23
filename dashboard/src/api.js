// Thin fetch wrappers around the FastAPI backend (proxied via /api in dev).
//
// Demo mode (VITE_DEMO=1) serves a committed snapshot of a real local run instead
// of calling the API. The full stack needs four databases and a local language
// model, none of which can run on a static host, so the deployed build reads
// captured data and disables the actions that would write.

export const DEMO = import.meta.env.VITE_DEMO === "1";

// Matches the backend's APP_SECRET_KEY (see .env.example) — required for the
// decision-override, blacklist-toggle, and label-propagation routes. Sent on
// every request rather than conditionally; the read-only routes ignore it.
const API_KEY = import.meta.env.VITE_API_KEY || "dev-secret";

let demoCache = null;

async function demoData() {
  if (!demoCache) {
    const res = await fetch(`${import.meta.env.BASE_URL}demo-data.json`);
    if (!res.ok) throw new Error(`Could not load demo data: ${res.status}`);
    demoCache = await res.json();
  }
  return demoCache;
}

async function request(path, options = {}) {
  const res = await fetch(`/api/v1${path}`, {
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

const DEMO_WRITE_MESSAGE =
  "This is a static demo. Scoring a new transaction needs the live backend. " +
  "Run it locally with `./scripts/run_local.sh` to try this.";

export const getRiskDistribution = async () =>
  DEMO ? (await demoData()).risk_distribution : request("/stats/risk-distribution");

// Demo snapshots predate these aggregates; null lets the panels say so.
export const getOverview = async () =>
  DEMO ? (await demoData()).overview ?? null : request("/stats/overview");

export const getGraphStats = async () =>
  DEMO ? (await demoData()).graph_stats ?? null : request("/graph/stats");

export const getAccuracy = async () =>
  DEMO ? (await demoData()).accuracy : request("/stats/accuracy");

export const getRecentFlags = async (limit = 20) =>
  DEMO
    ? (await demoData()).recent_flags.slice(0, limit)
    : request(`/stats/recent-flags?limit=${limit}`);

export const getTransaction = async (id) => {
  if (!DEMO) return request(`/transactions/${id}`);
  const found = (await demoData()).recent_flags.find((tx) => tx.tx_id === id);
  if (!found) throw new Error(`Transaction ${id} is not part of the demo snapshot.`);
  return found;
};

// The static demo has no graph database behind it, so these return null and the
// callers leave the network out rather than showing an error.
export const getGraphAccounts = async (limit = 25) =>
  DEMO ? null : request(`/graph/accounts?limit=${limit}`);

// The drawer leaves the network section out when this is null.
export const getNeighbors = async (accountId) =>
  DEMO ? null : request(`/graph/account/${encodeURIComponent(accountId)}/neighbors`);

export const analyzeTransaction = async (tx) => {
  if (DEMO) throw new Error(DEMO_WRITE_MESSAGE);
  return request("/transactions/analyze", { method: "POST", body: JSON.stringify(tx) });
};

export const restartComponent = async (name) => {
  if (DEMO) throw new Error(DEMO_WRITE_MESSAGE);
  return request(`/components/${name}/restart`, { method: "POST" });
};

// actor and reason are recorded in the transaction's override log. The shared
// key identifies nobody, so "dashboard" is a claim, not an identity — but an
// override with no trace at all is worse.
export const updateDecision = async (id, decision, reason = null) => {
  if (DEMO) throw new Error(DEMO_WRITE_MESSAGE);
  return request(`/transactions/${id}/decision`, {
    method: "PATCH",
    body: JSON.stringify({ decision, actor: "dashboard", reason: reason || null }),
  });
};
