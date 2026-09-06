import { useEffect, useState } from "react";
import { DEMO, analyzeTransaction, getTransaction } from "../api.js";
import {
  AlertTriangleIcon,
  BanIcon,
  CheckCircleIcon,
  ScanSearchIcon,
} from "../icons.jsx";

// Keep in sync with MerchantCategory in app/schemas/transaction.py — the
// backend rejects anything outside this set.
const CATEGORIES = [
  "groceries", "restaurants", "utilities", "retail", "travel",
  "fuel", "healthcare",
  "wire_transfer", "crypto_exchange", "gambling", "money_service",
];

const DECISION_META = {
  APPROVE: { icon: CheckCircleIcon, color: "var(--success)" },
  REVIEW: { icon: AlertTriangleIcon, color: "var(--warning)" },
  BLOCK: { icon: BanIcon, color: "var(--danger)" },
};

function LayerBar({ name, layer, pending }) {
  return (
    <div className="layer-bar">
      <div className="meta">
        <span>
          {name}
          {pending && <span className="pending-tag">scoring…</span>}
        </span>
        <span>
          {pending ? "—" : `${layer.score}/${layer.max_score}`}
        </span>
      </div>
      <div
        className="track"
        role="progressbar"
        aria-label={`${name} score`}
        aria-valuenow={layer.score}
        aria-valuemin={0}
        aria-valuemax={layer.max_score}
      >
        <div
          className="fill"
          style={{ width: `${(layer.score / layer.max_score) * 100}%` }}
        />
      </div>
    </div>
  );
}

export default function AnalyzeForm({ onAnalyzed }) {
  const [form, setForm] = useState({
    sender_account_id: "ACC-001",
    receiver_account_id: "ACC-002",
    amount: "250.00",
    merchant_category: "retail",
    device_id: "DEV-001",
    ip_address: "10.0.0.1",
    note: "",
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await analyzeTransaction({
        tx_id: `TX-${Date.now()}`,
        ...form,
        amount: parseFloat(form.amount),
        currency: "INR",
      });
      setResult(response);
      onAnalyzed?.();
    } catch (err) {
      setError(
        `Could not analyze the transaction (${err.message}). ` +
          "Check that the API and databases are running, then try again."
      );
    } finally {
      setBusy(false);
    }
  }

  // The analyze endpoint answers as soon as the rule and graph layers are
  // done; the language model attaches its score and explanation to the stored
  // record a few seconds later. Poll until it lands so the analyst sees the
  // final decision without refreshing.
  useEffect(() => {
    if (!result?.rag_pending || DEMO) return undefined;
    let cancelled = false;
    let timer;
    const deadline = Date.now() + 120000;

    const tick = async () => {
      if (cancelled || Date.now() > deadline) return;
      try {
        const record = await getTransaction(result.tx_id);
        if (cancelled) return;
        if (record.rag_pending === false) {
          setResult((prev) =>
            prev && prev.tx_id === record.tx_id
              ? {
                  ...prev,
                  rag_pending: false,
                  decision: record.decision,
                  composite_score: record.composite_score,
                  explanation: record.explanation,
                  rag_pipeline: {
                    ...prev.rag_pipeline,
                    score: Math.max(
                      record.composite_score -
                        prev.rule_engine.score -
                        prev.graph_analyzer.score,
                      0
                    ),
                  },
                }
              : prev
          );
          onAnalyzed?.();
          return;
        }
      } catch {
        // A failed poll is not worth surfacing — the decision already shown
        // is valid on its own, only the written explanation is outstanding.
      }
      timer = setTimeout(tick, 3000);
    };

    timer = setTimeout(tick, 3000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [result?.tx_id, result?.rag_pending, onAnalyzed]);

  const meta = result ? DECISION_META[result.decision] : null;
  const DecisionIcon = meta?.icon;

  return (
    <>
      <form className="analyze" onSubmit={submit}>
        <label>
          Sender account
          <input
            value={form.sender_account_id}
            onChange={set("sender_account_id")}
            required
            autoComplete="off"
          />
        </label>
        <label>
          Receiver account
          <input
            value={form.receiver_account_id}
            onChange={set("receiver_account_id")}
            required
            autoComplete="off"
          />
        </label>
        <label>
          Amount (₹)
          <input
            type="number"
            inputMode="decimal"
            min="0.01"
            step="0.01"
            value={form.amount}
            onChange={set("amount")}
            required
          />
        </label>
        <label>
          Merchant category
          <select value={form.merchant_category} onChange={set("merchant_category")}>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          Device ID
          <input value={form.device_id} onChange={set("device_id")} autoComplete="off" />
        </label>
        <label>
          IP address
          <input value={form.ip_address} onChange={set("ip_address")} autoComplete="off" />
        </label>
        <label style={{ gridColumn: "1 / -1" }}>
          Reason / note (optional)
          <textarea
            value={form.note}
            onChange={set("note")}
            rows={2}
            placeholder="e.g. customer travelling abroad, helps a reviewer decide"
            autoComplete="off"
          />
        </label>
        <button
          type="submit"
          disabled={busy || DEMO}
          title={DEMO ? "Scoring runs against the live backend. Clone the repo and run the stack to try it." : undefined}
        >
          {busy ? <span className="spinner" aria-hidden="true" /> : <ScanSearchIcon size={15} />}
          {busy ? "Analyzing…" : DEMO ? "Analyze (live backend only)" : "Analyze"}
        </button>
      </form>

      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}

      {result && (
        <div className="result" role="status">
          <div className="headline">
            <span className={`badge ${result.decision}`}>
              <DecisionIcon size={12} />
              {result.decision}
            </span>
            <span className="score" style={{ color: meta.color }}>
              {result.composite_score}
              <span style={{ fontSize: 12, color: "var(--text-dim)" }}>/100</span>
            </span>
            <span className="latency">{result.processing_time_ms.toFixed(0)} ms</span>
          </div>
          <LayerBar name="Rule engine" layer={result.rule_engine} />
          <LayerBar name="Graph analysis" layer={result.graph_analyzer} />
          <LayerBar
            name="RAG assessment"
            layer={result.rag_pipeline}
            pending={result.rag_pending}
          />
          <p className="explanation">{result.explanation}</p>
        </div>
      )}
    </>
  );
}
