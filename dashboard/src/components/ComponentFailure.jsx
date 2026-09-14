import { useState } from "react";
import { DEMO, restartComponent } from "../api.js";

export const LAYER_LABELS = {
  rule_engine: "Rule engine",
  graph_analyzer: "Graph analyzer",
  rag_pipeline: "Language model",
};

/**
 * A scoring layer that could not run: what broke, and a button to restart that
 * one component. Restarting does not re-score this transaction — it stays in
 * review — so the confirmation says so rather than implying the result changed.
 */
export default function ComponentFailure({ name, error }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const label = LAYER_LABELS[name] ?? name;

  async function restart() {
    setBusy(true);
    setResult(null);
    try {
      setResult(await restartComponent(name));
    } catch (err) {
      setResult({ ok: false, detail: err.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="layer-failure" role="alert">
      <div className="layer-failure__head">
        <span className="failed-tag">{label} failed</span>
        <button
          type="button"
          className="link-button"
          onClick={restart}
          disabled={busy || DEMO}
        >
          {busy ? "Restarting…" : `Restart ${label.toLowerCase()}`}
        </button>
      </div>
      {error && <code className="layer-failure__error">{error}</code>}
      {result && (
        <p className={`layer-failure__result ${result.ok ? "ok" : "bad"}`} role="status">
          {result.ok
            ? `Back online: ${result.detail}. This transaction stays in review; new transactions use the restarted component.`
            : `Still down: ${result.detail}`}
        </p>
      )}
    </div>
  );
}
