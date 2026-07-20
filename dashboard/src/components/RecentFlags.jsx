import { AlertTriangleIcon, BanIcon, ShieldIcon } from "../icons.jsx";

const BADGE_ICONS = {
  REVIEW: AlertTriangleIcon,
  BLOCK: BanIcon,
};

function DecisionBadge({ decision }) {
  const Bicon = BADGE_ICONS[decision] ?? AlertTriangleIcon;
  return (
    <span className={`badge ${decision}`}>
      <Bicon size={12} />
      {decision}
    </span>
  );
}

export default function RecentFlags({ flags, onSelect }) {
  if (flags === null) {
    return (
      <div style={{ display: "grid", gap: 8 }}>
        {[0, 1, 2].map((i) => (
          <div key={i} className="skeleton" style={{ height: 34 }} />
        ))}
      </div>
    );
  }

  if (!flags.length) {
    return (
      <div className="empty">
        <span className="icon"><ShieldIcon size={28} /></span>
        No flagged transactions — everything analyzed so far was approved.
      </div>
    );
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th scope="col">Tx ID</th>
            <th scope="col">Sender</th>
            <th scope="col">Receiver</th>
            <th scope="col">Amount</th>
            <th scope="col">Category</th>
            <th scope="col">Score</th>
            <th scope="col">Decision</th>
            <th scope="col">When</th>
            <th scope="col">Explanation</th>
          </tr>
        </thead>
        <tbody>
          {flags.map((tx) => (
            <tr
              key={tx.tx_id}
              onClick={() => onSelect?.(tx.tx_id)}
              style={{ cursor: "pointer" }}
              title="Click to open transaction details"
            >
              <td className="num">{tx.tx_id}</td>
              <td className="num">{tx.sender_account_id}</td>
              <td className="num">{tx.receiver_account_id}</td>
              <td className="num">
                ₹{tx.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </td>
              <td>{tx.merchant_category || "—"}</td>
              <td className="num">{tx.composite_score}</td>
              <td><DecisionBadge decision={tx.decision} /></td>
              <td>{new Date(tx.created_at).toLocaleString()}</td>
              <td className="explanation-cell" title={tx.explanation || ""}>
                {tx.explanation || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
