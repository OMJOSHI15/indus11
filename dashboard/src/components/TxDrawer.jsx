import { useEffect, useState } from "react";
import { DEMO, getTransaction, updateDecision } from "../api.js";
import { BanIcon, CheckCircleIcon } from "../icons.jsx";
import { LAYERS, humanize, parseExplanation } from "../signals.js";
import { fullTime, money } from "../format.js";
import { DECISION_LABELS } from "../theme.js";
import ComponentFailure from "./ComponentFailure.jsx";
import AccountGraph from "./AccountGraph.jsx";
import Sheet from "./Sheet.jsx";
import { DecisionBadge } from "./RecentFlags.jsx";

/**
 * Transaction details over the queue: the reviewer keeps the list in view, and
 * the one decision this exists for (approve or block) sits in a footer that
 * never scrolls away.
 */
export default function TxDrawer({ txId, onClose, onUpdated }) {
  const [tx, setTx] = useState(null);
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState("");
  const [err, setErr] = useState(null);

  useEffect(() => {
    setTx(null);
    setErr(null);
    getTransaction(txId).then(setTx).catch((e) => setErr(e.message));
  }, [txId]);

  async function decide(decision) {
    setBusy(true);
    setErr(null);
    try {
      setTx(await updateDecision(txId, decision, reason.trim()));
      onUpdated?.();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  const { signals, text } = parseExplanation(tx?.explanation);
  const failures = Object.entries(tx?.layer_failures ?? {});

  const footer = tx && (
    tx.decision !== "REVIEW" ? (
      <p className="sub">Decision final: {tx.decision.toLowerCase()}.</p>
    ) : DEMO ? (
      <p className="sub">Overriding writes to the database, so it is off in this static demo.</p>
    ) : (
      <>
        <label className="override-reason">
          <span>Reason</span>
          <input type="text" value={reason} maxLength={280} placeholder="recorded with the override"
                 onChange={(e) => setReason(e.target.value)} />
        </label>
        <div className="override-actions">
          <button type="button" className="button button--approve" disabled={busy} onClick={() => decide("APPROVE")}>
            <CheckCircleIcon size={15} /> Approve
          </button>
          <button type="button" className="button button--block" disabled={busy} onClick={() => decide("BLOCK")}>
            <BanIcon size={15} /> Block
          </button>
        </div>
      </>
    )
  );

  return (
    <Sheet title={txId} titleClass="mono" subtitle={tx && fullTime(tx.created_at)} onClose={onClose} footer={footer}>
      {!tx && !err && <div className="skeleton" style={{ height: 320 }} />}

      {tx && (
        <>
          <section className="verdict">
            <div>
              <span className="verdict__label">Composite risk score</span>
              <span className="verdict__n">{tx.composite_score}<small>/100</small></span>
            </div>
            <DecisionBadge decision={tx.decision} />
          </section>

          <dl className="facts">
            <div><dt>Sender</dt><dd className="mono">{tx.sender_account_id}</dd></div>
            <div><dt>Receiver</dt><dd className="mono">{tx.receiver_account_id}</dd></div>
            <div><dt>Amount</dt><dd className="num">{money(tx.amount)}</dd></div>
            <div><dt>Category</dt><dd>{tx.merchant_category ? humanize(tx.merchant_category) : "—"}</dd></div>
            <div><dt>Device</dt><dd className="mono">{tx.device_id || "—"}</dd></div>
            <div><dt>IP address</dt><dd className="mono">{tx.ip_address || "—"}</dd></div>
          </dl>

          {tx.note && <p className="note"><span>Submitted reason</span>{tx.note}</p>}

          {failures.length > 0 && (
            <section className="sheet__section">
              {failures.map(([name, error]) => <ComponentFailure key={name} name={name} error={error} />)}
            </section>
          )}

          <section className="sheet__section">
            <h3>Signals</h3>
            {!signals.length && <p className="sub">No signals fired on this transaction.</p>}
            {LAYERS.map(({ key, label }) => {
              const own = signals.filter((s) => s.layer === key);
              if (!own.length) return null;
              return (
                <div key={key} className="signal-group">
                  <span className={`signal-group__label layer-${key}`}>{label}</span>
                  <ul>
                    {own.map((s) => (
                      <li key={s.code}>
                        <span>{humanize(s.code)}</span>
                        {s.detail && <span className="sub">{s.detail}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </section>

          <section className="sheet__section">
            <h3>Explanation</h3>
            <p className="prose">
              {tx.rag_pending
                ? "The language model is still writing its assessment. The decision above already stands on the rule and graph layers."
                : text || "No explanation recorded."}
            </p>
          </section>

          {tx.overrides?.length > 0 && (
            <section className="sheet__section">
              <h3>Decision history</h3>
              <ol className="audit">
                {tx.overrides.map((o, i) => (
                  <li key={`${o.at}-${i}`}>
                    <span>
                      <strong>{DECISION_LABELS[o.from_decision] ?? o.from_decision ?? "—"}</strong>
                      {" → "}
                      <strong>{DECISION_LABELS[o.to_decision] ?? o.to_decision}</strong>
                      {" by "}{o.actor}
                    </span>
                    <span className="sub">{fullTime(o.at)}{o.reason ? ` · ${o.reason}` : " · no reason given"}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section className="sheet__section">
            <h3>Sender’s network</h3>
            <AccountGraph sender={tx.sender_account_id} receiver={tx.receiver_account_id} />
          </section>
        </>
      )}
      {err && <p className="error-text" role="alert">{err}</p>}
    </Sheet>
  );
}
