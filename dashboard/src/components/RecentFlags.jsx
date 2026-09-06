import { useMemo, useState } from "react";
import { AlertTriangleIcon, BanIcon, ShieldIcon } from "../icons.jsx";

const BADGE_ICONS = {
  REVIEW: AlertTriangleIcon,
  BLOCK: BanIcon,
};

const FILTERS = [
  { key: "ALL", label: "All" },
  { key: "REVIEW", label: "In review" },
  { key: "BLOCK", label: "Blocked" },
];

function DecisionBadge({ decision }) {
  const Bicon = BADGE_ICONS[decision] ?? AlertTriangleIcon;
  return (
    <span className={`badge ${decision}`}>
      <Bicon size={12} />
      {decision}
    </span>
  );
}

/** Score with a proportional bar, so relative risk reads at a glance. */
function ScoreCell({ score }) {
  const band = score >= 70 ? "block" : score >= 40 ? "review" : "approve";
  return (
    <div className="score-cell">
      <span className="score-value">{score}</span>
      <span className="score-track" aria-hidden="true">
        <span className={`score-fill ${band}`} style={{ width: `${score}%` }} />
      </span>
    </div>
  );
}

export default function RecentFlags({ flags, onSelect }) {
  const [filter, setFilter] = useState("ALL");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState({ key: "created_at", dir: "desc" });

  const rows = useMemo(() => {
    if (!flags) return [];
    const needle = query.trim().toLowerCase();
    const filtered = flags.filter((tx) => {
      if (filter !== "ALL" && tx.decision !== filter) return false;
      if (!needle) return true;
      return [tx.tx_id, tx.sender_account_id, tx.receiver_account_id]
        .some((v) => String(v).toLowerCase().includes(needle));
    });
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const av = sort.key === "created_at" ? new Date(a.created_at) : a[sort.key];
      const bv = sort.key === "created_at" ? new Date(b.created_at) : b[sort.key];
      return av > bv ? dir : av < bv ? -dir : 0;
    });
  }, [flags, filter, query, sort]);

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
        No flagged transactions. Everything analyzed so far was approved.
      </div>
    );
  }

  const toggleSort = (key) =>
    setSort((s) =>
      s.key === key
        ? { key, dir: s.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "desc" });

  const arrow = (key) =>
    sort.key === key ? (sort.dir === "asc" ? " ↑" : " ↓") : "";

  const counts = flags.reduce((acc, tx) => {
    acc[tx.decision] = (acc[tx.decision] || 0) + 1;
    return acc;
  }, {});

  return (
    <>
      <div className="table-controls">
        <div className="filter-chips" role="group" aria-label="Filter by decision">
          {FILTERS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              className={`chip${filter === key ? " active" : ""}`}
              aria-pressed={filter === key}
              onClick={() => setFilter(key)}
            >
              {label}
              <span className="chip-count">
                {key === "ALL" ? flags.length : counts[key] || 0}
              </span>
            </button>
          ))}
        </div>
        <input
          type="search"
          className="table-search"
          placeholder="Search transaction or account…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search flagged transactions"
        />
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Tx ID</th>
              <th scope="col">Sender</th>
              <th scope="col">Receiver</th>
              <th scope="col">Amount</th>
              <th scope="col">Category</th>
              <th scope="col">
                <button type="button" className="th-sort"
                        onClick={() => toggleSort("composite_score")}>
                  Score{arrow("composite_score")}
                </button>
              </th>
              <th scope="col">Decision</th>
              <th scope="col">
                <button type="button" className="th-sort"
                        onClick={() => toggleSort("created_at")}>
                  When{arrow("created_at")}
                </button>
              </th>
              <th scope="col">Explanation</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((tx, i) => (
              <tr
                key={tx.tx_id}
                className="row-enter"
                style={{ animationDelay: `${Math.min(i, 12) * 28}ms` }}
                onClick={() => onSelect?.(tx.tx_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect?.(tx.tx_id);
                  }
                }}
                tabIndex={onSelect ? 0 : -1}
                title="Open transaction details"
              >
                <td className="num">{tx.tx_id}</td>
                <td className="num">{tx.sender_account_id}</td>
                <td className="num">{tx.receiver_account_id}</td>
                <td className="num">
                  ₹{tx.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </td>
                <td>{tx.merchant_category || "—"}</td>
                <td><ScoreCell score={tx.composite_score} /></td>
                <td><DecisionBadge decision={tx.decision} /></td>
                <td>{new Date(tx.created_at).toLocaleString()}</td>
                <td className="explanation-cell" title={tx.explanation || ""}>
                  {tx.explanation || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && (
          <div className="empty" style={{ marginTop: 12 }}>
            Nothing matches that filter.
          </div>
        )}
      </div>
    </>
  );
}
