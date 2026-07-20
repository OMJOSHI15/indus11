// Thin fetch wrappers around the FastAPI backend (proxied via /api in dev).

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

export const getRiskDistribution = () => request("/stats/risk-distribution");
export const getRecentFlags = (limit = 20) => request(`/stats/recent-flags?limit=${limit}`);
export const analyzeTransaction = (tx) =>
  request("/transactions/analyze", { method: "POST", body: JSON.stringify(tx) });
export const getTransaction = (id) => request(`/transactions/${id}`);
export const updateDecision = (id, decision) =>
  request(`/transactions/${id}/decision`, { method: "PATCH", body: JSON.stringify({ decision }) });
