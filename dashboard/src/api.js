// Thin fetch wrappers around the FastAPI backend (proxied via /api in dev).
//
// Demo mode (VITE_DEMO=1) serves a committed snapshot of a real local run instead
// of calling the API. The full stack needs four databases and a local language
// model, none of which can run on a static host, so the deployed build reads
// captured data and disables the actions that would write.

export const DEMO = import.meta.env.VITE_DEMO === "1";

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
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

const DEMO_WRITE_MESSAGE =
  "This is a static demo — scoring a new transaction needs the live backend. " +
  "Run it locally with `docker compose up` to try this.";

export const getRiskDistribution = async () =>
  DEMO ? (await demoData()).risk_distribution : request("/stats/risk-distribution");

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

export const analyzeTransaction = async (tx) => {
  if (DEMO) throw new Error(DEMO_WRITE_MESSAGE);
  return request("/transactions/analyze", { method: "POST", body: JSON.stringify(tx) });
};

export const updateDecision = async (id, decision) => {
  if (DEMO) throw new Error(DEMO_WRITE_MESSAGE);
  return request(`/transactions/${id}/decision`, {
    method: "PATCH",
    body: JSON.stringify({ decision }),
  });
};
