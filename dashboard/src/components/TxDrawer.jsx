import { useEffect, useRef, useState } from "react";
import { DEMO, getTransaction, updateDecision } from "../api.js";
import { BanIcon, CheckCircleIcon, XIcon } from "../icons.jsx";
import { LAYERS, humanize, parseExplanation } from "../signals.js";
import { fullTime, money } from "../format.js";
import ComponentFailure from "./ComponentFailure.jsx";
import AccountGraph from "./AccountGraph.jsx";
import { DecisionBadge } from "./RecentFlags.jsx";

const FOCUSABLE = "button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])";

/**
 * A sheet over the queue rather than a centred modal: the reviewer keeps the
 * list in view, and the one decision this screen exists for (approve or block)
 * sits in a footer that never scrolls away.
 */
export default function TxDrawer({ txId, onClose, onUpdated }) {
  const [tx, setTx] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const sheetRef = useRef(null);

  useEffect(() => {
    setTx(null);
    setErr(null);
    getTransaction(txId).then(setTx).catch((e) => setErr(e.message));
  }, [txId]);

  // Focus moves into the sheet, stays there, and returns to the row on close.
  useEffect(() => {
    const opener = document.activeElement;
    sheetRef.current?.querySelector("button")?.focus();
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
      opener?.focus?.();
    };
  }, []);

  function onKeyDown(e) {
    if (e.key === "Escape") {
      e.stopPropagation();
      onClose();
      return;
    }
    if (e.key !== "Tab") return;
    const items = [...sheetRef.current.querySelectorAll(FOCUSABLE)].filter((el) => !el.disabled);
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  async function decide(decision) {
    setBusy(true);
    setErr(null);
    try {
      setTx(await updateDecision(txId, decision));
      onUpdated?.();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  const { signals, text } = parseExplanation(tx?.explanation);
  const failures = Object.entries(tx?.layer_failures ?? {});

  return (
    <div className="drawer-root" onKeyDown={onKeyDown}>
      <div className="scrim" onClick={onClose} aria-hidden="true" />
      <aside ref={sheetRef} className="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title">
        <header className="sheet__head">
          <div>
            <h2 id="sheet-title" className="mono">{txId}</h2>
            {tx && <p className="sub">{fullTime(tx.created_at)}</p>}
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close details">
            <XIcon size={16} />
          </button>
        </header>

        <div className="sheet__body">
          {!tx && !err && <div className="skeleton" style={{ height: 320 }} />}

          {tx && (
            <>
              <section className="sheet__verdict">
                <div className="verdict__score">
                  <span className={`verdict__n ${tx.decision}`}>{tx.composite_score}</span>
                  <span className="dim">/100</span>
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

              {tx.note && (
                <p className="note"><span className="dim">Submitted reason</span>{tx.note}</p>
              )}

              {failures.length > 0 && (
                <section className="sheet__section">
                  {failures.map(([name, error]) => (
                    <ComponentFailure key={name} name={name} error={error} />
                  ))}
                </section>
              )}

              <section className="sheet__section">
                <h3>Signals</h3>
                {!signals.length && <p className="dim small">No signals fired on this transaction.</p>}
                {LAYERS.map(({ key, label }) => {
                  const own = signals.filter((s) => s.layer === key);
                  if (!own.length) return null;
                  return (
                    <div key={key} className="signal-group">
                      <span className="signal-group__label">{label}</span>
                      <ul>
                        {own.map((s) => (
                          <li key={s.code}>
                            <span>{humanize(s.code)}</span>
                            {s.detail && <span className="dim">{s.detail}</span>}
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

              <section className="sheet__section">
                <h3>Sender’s network</h3>
                <AccountGraph sender={tx.sender_account_id} receiver={tx.receiver_account_id} />
              </section>
            </>
          )}
          {err && <p className="error-text" role="alert">{err}</p>}
        </div>

        {tx && (
          <footer className="sheet__foot">
            {tx.decision !== "REVIEW" ? (
              <p className="dim small">Decision final: {tx.decision.toLowerCase()}.</p>
            ) : DEMO ? (
              <p className="dim small">Overriding writes to the database, so it is off in this static demo.</p>
            ) : (
              <>
                <button type="button" className="tinted approve" disabled={busy} onClick={() => decide("APPROVE")}>
                  <CheckCircleIcon size={15} /> Approve
                </button>
                <button type="button" className="tinted block" disabled={busy} onClick={() => decide("BLOCK")}>
                  <BanIcon size={15} /> Block
                </button>
              </>
            )}
          </footer>
        )}
      </aside>
    </div>
  );
}
