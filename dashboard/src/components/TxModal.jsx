import { useEffect, useState } from "react";
import { DEMO, getTransaction, updateDecision } from "../api.js";

const S = {
  overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex",
    alignItems: "center", justifyContent: "center", zIndex: 100, padding: 20 },
  card: { background: "#161D2E", border: "1px solid #2A3450", borderRadius: 12, padding: "22px 24px",
    width: "min(560px, 94vw)", maxHeight: "88vh", overflow: "auto", color: "#E8EDF7", position: "relative" },
  close: { position: "absolute", top: 12, right: 14, background: "none", border: "none",
    color: "#94A3B8", fontSize: 22, cursor: "pointer", lineHeight: 1 },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 18px", margin: "14px 0" },
  dt: { fontSize: 11, textTransform: "uppercase", letterSpacing: "0.4px", color: "#94A3B8", margin: 0 },
  dd: { margin: "2px 0 0", fontSize: 14 },
  note: { background: "#1C2539", border: "1px solid #2A3450", borderRadius: 8, padding: "8px 12px", fontSize: 13 },
  expl: { fontSize: 13, color: "#CBD5E1", lineHeight: 1.5, marginTop: 10 },
  actions: { display: "flex", gap: 10, marginTop: 16 },
  approve: { flex: 1, padding: "10px", borderRadius: 8, border: "none", cursor: "pointer",
    background: "#34D399", color: "#04231a", fontWeight: 700 },
  block: { flex: 1, padding: "10px", borderRadius: 8, border: "none", cursor: "pointer",
    background: "#F87171", color: "#2a0606", fontWeight: 700 },
  final: { marginTop: 14, fontSize: 13, color: "#94A3B8" },
};

const money = (a) => "₹" + Number(a).toLocaleString("en-IN", { minimumFractionDigits: 2 });

export default function TxModal({ txId, onClose, onUpdated }) {
  const [tx, setTx] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    getTransaction(txId).then(setTx).catch((e) => setErr(e.message));
  }, [txId]);

  async function decide(decision) {
    setBusy(true);
    setErr(null);
    try {
      const updated = await updateDecision(txId, decision);
      setTx(updated);
      onUpdated?.();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={S.overlay} onClick={onClose}>
      <div style={S.card} onClick={(e) => e.stopPropagation()}>
        <button style={S.close} onClick={onClose} aria-label="Close">×</button>
        {!tx ? (
          <div className="skeleton" style={{ height: 220 }} />
        ) : (
          <>
            <h3 style={{ margin: "0 30px 8px 0" }}>Transaction {tx.tx_id}</h3>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span className={`badge ${tx.decision}`}>{tx.decision}</span>
              <b style={{ fontSize: 16 }}>{tx.composite_score}/100</b>
            </div>
            <dl style={S.grid}>
              <div><dt style={S.dt}>Sender</dt><dd style={S.dd}>{tx.sender_account_id}</dd></div>
              <div><dt style={S.dt}>Receiver</dt><dd style={S.dd}>{tx.receiver_account_id}</dd></div>
              <div><dt style={S.dt}>Amount</dt><dd style={S.dd}>{money(tx.amount)}</dd></div>
              <div><dt style={S.dt}>Category</dt><dd style={S.dd}>{tx.merchant_category || "—"}</dd></div>
              <div><dt style={S.dt}>Device</dt><dd style={S.dd}>{tx.device_id || "—"}</dd></div>
              <div><dt style={S.dt}>IP address</dt><dd style={S.dd}>{tx.ip_address || "—"}</dd></div>
              <div><dt style={S.dt}>When</dt><dd style={S.dd}>{tx.created_at ? new Date(tx.created_at).toLocaleString() : "—"}</dd></div>
            </dl>
            {tx.note && <p style={S.note}><b>Submitted reason:</b> {tx.note}</p>}
            <p style={S.expl}>{tx.explanation || "No explanation recorded."}</p>
            {tx.decision === "REVIEW" && DEMO ? (
              <p style={S.final}>
                Awaiting analyst review. Overriding a decision writes to the
                database, so it is disabled in this static demo.
              </p>
            ) : tx.decision === "REVIEW" ? (
              <div style={S.actions}>
                <button style={S.approve} disabled={busy} onClick={() => decide("APPROVE")}>Approve</button>
                <button style={S.block} disabled={busy} onClick={() => decide("BLOCK")}>Block</button>
              </div>
            ) : (
              <p style={S.final}>Decision finalised: <b>{tx.decision}</b>.</p>
            )}
            {err && <p className="error-text" style={{ marginTop: 10 }}>{err}</p>}
          </>
        )}
      </div>
    </div>
  );
}
