import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangleIcon, BanIcon, SearchIcon, ShieldIcon } from "../icons.jsx";
import { humanize, parseExplanation } from "../signals.js";
import { ago, fullTime, money, toDate } from "../format.js";

const BADGE_ICONS = { REVIEW: AlertTriangleIcon, BLOCK: BanIcon };
const BADGE_TEXT = { REVIEW: "Review", BLOCK: "Block" };

const FILTERS = [
  { key: "ALL", label: "All" },
  { key: "REVIEW", label: "Review" },
  { key: "BLOCK", label: "Blocked" },
];

const MAX_CHIPS = 3;

export function DecisionBadge({ decision }) {
  const Bicon = BADGE_ICONS[decision];
  return (
    <span className={`badge ${decision}`}>
      {Bicon && <Bicon size={12} />}
      {BADGE_TEXT[decision] ?? "Approve"}
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

function SignalChips({ tx }) {
  const { signals } = parseExplanation(tx.explanation);
  const failed = Object.keys(tx.layer_failures ?? {}).length;
  const shown = signals.slice(0, MAX_CHIPS);
  const hidden = signals.length - shown.length;
  return (
    <div className="chips">
      {failed > 0 && (
        <span className="chip chip--failed" title={Object.values(tx.layer_failures).join("\n")}>
          {failed === 1 ? "Layer failed" : `${failed} layers failed`}
        </span>
      )}
      {shown.map((s) => (
        <span key={s.code} className="chip" title={s.detail ?? undefined}>
          {humanize(s.code)}
        </span>
      ))}
      {hidden > 0 && (
        <span className="chip chip--more" title={signals.slice(MAX_CHIPS).map((s) => humanize(s.code)).join(", ")}>
          +{hidden}
        </span>
      )}
      {!signals.length && !failed && <span className="dim">—</span>}
    </div>
  );
}

export default function RecentFlags({ flags, onSelect }) {
  const [filter, setFilter] = useState("ALL");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState({ key: "created_at", dir: "desc" });
  const searchRef = useRef(null);
  const bodyRef = useRef(null);

  // "/" jumps to search from anywhere that is not already a text field.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== "/" || e.metaKey || e.ctrlKey) return;
      if (e.target.closest?.("input, textarea, select, [role=dialog]")) return;
      e.preventDefault();
      searchRef.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const rows = useMemo(() => {
    if (!flags) return [];
    const needle = query.trim().toLowerCase();
    const filtered = flags.filter((tx) => {
      if (filter !== "ALL" && tx.decision !== filter) return false;
      if (!needle) return true;
      return [tx.tx_id, tx.sender_account_id, tx.receiver_account_id, tx.explanation]
        .some((v) => String(v ?? "").toLowerCase().includes(needle));
    });
    const dir = sort.dir === "asc" ? 1 : -1;
    const value = (tx) => (sort.key === "created_at" ? toDate(tx.created_at) : tx[sort.key]);
    return [...filtered].sort((a, b) => (value(a) > value(b) ? dir : value(a) < value(b) ? -dir : 0));
  }, [flags, filter, query, sort]);

  if (flags === null) {
    return (
      <div className="skeleton-stack">
        {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 44 }} />)}
      </div>
    );
  }

  if (!flags.length) {
    return (
      <div className="empty">
        <span className="icon"><ShieldIcon size={28} /></span>
        Nothing waiting for review. Every transaction so far was approved.
      </div>
    );
  }

  const toggleSort = (key) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "desc" }));
  const ariaSort = (key) => (sort.key === key ? (sort.dir === "asc" ? "ascending" : "descending") : "none");
  const arrow = (key) => (sort.key === key ? (sort.dir === "asc" ? "↑" : "↓") : "");

  const counts = flags.reduce((acc, tx) => ({ ...acc, [tx.decision]: (acc[tx.decision] || 0) + 1 }), {});

  const moveFocus = (e, index) => {
    const next = e.key === "ArrowDown" ? index + 1 : e.key === "ArrowUp" ? index - 1 : null;
    if (next === null) return;
    e.preventDefault();
    bodyRef.current?.querySelectorAll("tr")[next]?.focus();
  };

  return (
    <>
      <div className="table-controls">
        <div className="segmented" role="group" aria-label="Filter by decision">
          {FILTERS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              className="segmented__item"
              aria-pressed={filter === key}
              onClick={() => setFilter(key)}
            >
              {label}
              <span className="segmented__count">{key === "ALL" ? flags.length : counts[key] || 0}</span>
            </button>
          ))}
        </div>
        <label className="search">
          <SearchIcon size={14} />
          <input
            ref={searchRef}
            type="search"
            placeholder="Search ID, account or signal"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search flagged transactions"
          />
          <kbd aria-hidden="true">/</kbd>
        </label>
      </div>

      <div className="table-scroll">
        <table className="queue-table">
          <thead>
            <tr>
              <th scope="col" aria-sort={ariaSort("created_at")}>
                <button type="button" className="th-sort" onClick={() => toggleSort("created_at")}>
                  Transaction <span aria-hidden="true">{arrow("created_at")}</span>
                </button>
              </th>
              <th scope="col">Route</th>
              <th scope="col" className="right">Amount</th>
              <th scope="col" aria-sort={ariaSort("composite_score")}>
                <button type="button" className="th-sort" onClick={() => toggleSort("composite_score")}>
                  Score <span aria-hidden="true">{arrow("composite_score")}</span>
                </button>
              </th>
              <th scope="col">Decision</th>
              <th scope="col">Signals</th>
            </tr>
          </thead>
          <tbody ref={bodyRef}>
            {rows.map((tx, i) => (
              <tr
                key={tx.tx_id}
                className={`row-enter${onSelect ? " clickable" : ""}`}
                style={{ animationDelay: `${Math.min(i, 12) * 24}ms` }}
                onClick={() => onSelect?.(tx.tx_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect?.(tx.tx_id);
                  } else {
                    moveFocus(e, i);
                  }
                }}
                tabIndex={onSelect ? 0 : -1}
                aria-label={onSelect ? `Open ${tx.tx_id}` : undefined}
              >
                <td>
                  <div className="mono">{tx.tx_id}</div>
                  <div className="sub" title={fullTime(tx.created_at)}>{ago(tx.created_at)}</div>
                </td>
                <td className="mono route">
                  {tx.sender_account_id}
                  <span className="route__arrow" aria-label="to">→</span>
                  {tx.receiver_account_id}
                </td>
                <td className="right">
                  <div className="num">{money(tx.amount)}</div>
                  <div className="sub">{tx.merchant_category ? humanize(tx.merchant_category) : "—"}</div>
                </td>
                <td><ScoreCell score={tx.composite_score} /></td>
                <td><DecisionBadge decision={tx.decision} /></td>
                <td><SignalChips tx={tx} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && <div className="empty">Nothing matches that filter.</div>}
      </div>
    </>
  );
}
