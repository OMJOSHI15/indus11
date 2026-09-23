// One component per route. Every page reads from the same poll in App.jsx, so
// switching pages costs no request: the shell owns the data, pages only lay it out.
import { useEffect, useState } from "react";
import AccountGraph from "./components/AccountGraph.jsx";
import AccuracyPanel from "./components/AccuracyPanel.jsx";
import RecentFlags from "./components/RecentFlags.jsx";
import {
  AmountBands, Card, CategoryRisk, ChartSkeleton, DecisionDonut, DecisionsByDay, ScoreHistogram, TopSignals,
} from "./components/Charts.jsx";
import { getGraphAccounts } from "./api.js";
import { moneyShort } from "./format.js";
import { DECISION_COLORS } from "./theme.js";

const share = (part, whole) => (whole ? `${((part / whole) * 100).toFixed(1)}%` : "—");

function Kpi({ label, value, sub, keyColor, tone }) {
  return (
    <div className={`kpi${tone ? ` kpi--${tone}` : ""}`}>
      <span className="kpi__label">
        {keyColor && <span className="kpi__key" style={{ background: keyColor }} aria-hidden="true" />}
        {label}
      </span>
      <span className="kpi__value">{value ?? <span className="skeleton" style={{ display: "block", width: 90, height: 30 }} />}</span>
      <span className="kpi__sub">{sub ?? " "}</span>
    </div>
  );
}

// undefined = still loading, null = this build or backend cannot provide it.
const Live = ({ data, height, children }) =>
  data === null
    ? <p className="empty" style={{ minHeight: height }}>Needs the live backend.</p>
    : children;

export function Overview({ distribution, overview }) {
  const t = overview?.totals;
  const blocked = distribution?.decisions?.BLOCK;
  const flagged = distribution && distribution.decisions.REVIEW + distribution.decisions.BLOCK;

  return (
    <>
      <section className="kpis" aria-label="Key figures">
        <Kpi label="Transactions scored" value={distribution?.total.toLocaleString("en-IN")}
             sub={overview && `${overview.by_day.length} active days`} />
        <Kpi label="Flagged for review" keyColor={DECISION_COLORS.REVIEW}
             value={flagged?.toLocaleString("en-IN")}
             sub={distribution && `${share(flagged, distribution.total)} of scored`} />
        <Kpi label="Blocked" keyColor={DECISION_COLORS.BLOCK} value={blocked?.toLocaleString("en-IN")}
             sub={distribution && `${share(blocked, distribution.total)} of scored`} />
        <Kpi label="Value flagged" value={t && moneyShort(t.flagged_amount)} sub={t && "in review or blocked"} />
        <Kpi label="Average risk score" value={t && t.avg_score} sub={t && "out of 100"} />
        <Kpi label="Layer failures" value={t?.layer_failures} tone={t?.layer_failures ? "alert" : undefined}
             sub={t && `${t.rag_pending.toLocaleString("en-IN")} explanations pending`} />
      </section>

      <div className="grid">
        <Card className="span-8" title="Decisions by day" subtitle="Approved, in review and blocked per active day">
          <Live data={overview} height={290}><DecisionsByDay overview={overview} /></Live>
        </Card>

        <Card className="span-4" title="Decision mix" subtitle="All scored transactions">
          <DecisionDonut distribution={distribution} />
        </Card>

        <Card className="span-6" title="Risk by merchant category" subtitle="Decisions within each category">
          <Live data={overview} height={340}><CategoryRisk overview={overview} /></Live>
        </Card>

        <Card className="span-6" title="Flag rate by amount" subtitle="Share of transactions sent to review or block">
          <Live data={overview} height={340}><AmountBands overview={overview} /></Live>
        </Card>
      </div>
    </>
  );
}

export function Queue({ distribution, overview, flags, offline, onSelect }) {
  const t = overview?.totals;
  const blocked = distribution?.decisions?.BLOCK;

  return (
    <>
      <section className="kpis kpis--4" aria-label="Queue figures">
        <Kpi label="In review" keyColor={DECISION_COLORS.REVIEW} value={distribution?.decisions.REVIEW.toLocaleString("en-IN")}
             sub={distribution && `${share(distribution.decisions.REVIEW, distribution.total)} of scored`} />
        <Kpi label="Blocked" keyColor={DECISION_COLORS.BLOCK} value={blocked?.toLocaleString("en-IN")}
             sub={distribution && `${share(blocked, distribution.total)} of scored`} />
        <Kpi label="Value flagged" value={t && moneyShort(t.flagged_amount)} sub={t && "in review or blocked"} />
        <Kpi label="Explanations pending" value={t?.rag_pending?.toLocaleString("en-IN")}
             sub={t && "language-model layer still running"} />
      </section>

      <div className="grid">
        <Card className="span-12" title="Recent decisions"
              subtitle="20 most recent review and block decisions. Select a row for the full explanation.">
          <RecentFlags flags={flags} onSelect={offline ? undefined : onSelect} />
        </Card>
      </div>
    </>
  );
}

export function Signals({ distribution, overview }) {
  return (
    <div className="grid">
      <Card className="span-8" title="Most frequent signals" subtitle="How often each flag fired on flagged transactions">
        <Live data={overview} height={340}><TopSignals overview={overview} /></Live>
      </Card>

      <Card className="span-4" title="Score distribution" subtitle="Composite risk score, 0 to 100">
        <ScoreHistogram distribution={distribution} />
      </Card>

      <Card className="span-12" title="How a score is built" subtitle="Three layers score in parallel, then the bands decide">
        <dl className="stat-list stat-list--wide">
          <div><dt>Rule engine</dt><dd>0–40 points</dd></div>
          <div><dt>Graph analysis</dt><dd>0–30 points</dd></div>
          <div><dt>Language model</dt><dd>0–30 points</dd></div>
          <div><dt><span className="kpi__key" style={{ background: DECISION_COLORS.APPROVE }} aria-hidden="true" />Approve</dt><dd>below 40</dd></div>
          <div><dt><span className="kpi__key" style={{ background: DECISION_COLORS.REVIEW }} aria-hidden="true" />Review</dt><dd>40 to 69</dd></div>
          <div><dt><span className="kpi__key" style={{ background: DECISION_COLORS.BLOCK }} aria-hidden="true" />Block</dt><dd>70 and above</dd></div>
        </dl>
      </Card>
    </div>
  );
}

export function Accuracy() {
  return (
    <div className="grid">
      <Card className="span-8" title="Detection accuracy" subtitle="Labelled synthetic benchmark">
        <AccuracyPanel />
      </Card>

      <Card className="span-4" title="How to read this" subtitle="What the figures do and do not cover">
        <p className="card__note">
          Precision is the share of flagged transactions that were really fraud; recall is the share of
          fraud the pipeline caught; F1 balances the two. Accuracy is every decision that matched its
          label, approvals included, so on a set that is mostly legitimate it sits high whatever the
          detector does — read it beside precision and recall, not instead of them.
        </p>
        <p className="card__note">
          All four come from <code>scripts/evaluate.py</code> over a labelled synthetic set, not from
          live traffic, so they say how the layers behave on that data only.
        </p>
        <p className="card__note">
          Re-run the script after changing thresholds or adding rules; the stored report is a snapshot of
          the last run, not a live measurement.
        </p>
      </Card>
    </div>
  );
}

/** Picks an account and draws the hop around it. Fraud seeds come first from the
 *  backend, so the graph opens on a node that actually has a neighbourhood. */
function AccountExplorer() {
  const [accounts, setAccounts] = useState(undefined);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getGraphAccounts(25)
      .then((rows) => {
        if (cancelled) return;
        setAccounts(rows);
        if (rows?.length) setSelected(rows[0].account_id);
      })
      .catch(() => !cancelled && setAccounts(null));
    return () => { cancelled = true; };
  }, []);

  if (accounts === undefined) return <ChartSkeleton height={320} />;
  if (accounts === null) return <p className="empty" style={{ minHeight: 320 }}>Needs the live backend.</p>;
  if (!accounts.length) return <p className="empty" style={{ minHeight: 320 }}>No connected accounts in the graph yet.</p>;

  return (
    <>
      <div className="card__toolbar">
        <label className="picker">
          <span>Account</span>
          <select value={selected ?? ""} onChange={(e) => setSelected(e.target.value)}>
            {accounts.map(({ account_id, risk_label, connections }) => (
              <option key={account_id} value={account_id}>
                {account_id}{risk_label === "fraud" ? " · known fraud" : risk_label === "fraud_adjacent" ? " · fraud-adjacent" : ""} · {connections} connections
              </option>
            ))}
          </select>
        </label>
      </div>
      {selected && <AccountGraph key={selected} sender={selected} />}
    </>
  );
}

export function Network({ graphStats }) {
  return (
    <div className="grid">
      <Card className="span-8" title="Account neighbourhood"
            subtitle="One hop around the account: who it paid, and the devices and addresses it shares">
        <AccountExplorer />
      </Card>

      <Card className="span-4" title="Transaction graph" subtitle="Neo4j entities behind the graph layer">
        <Live data={graphStats} height={220}>
          {graphStats === undefined ? <ChartSkeleton height={220} /> : (
            <dl className="stat-list">
              <div><dt>Accounts</dt><dd>{graphStats.accounts.toLocaleString("en-IN")}</dd></div>
              <div><dt>Devices</dt><dd>{graphStats.devices.toLocaleString("en-IN")}</dd></div>
              <div><dt>IP addresses</dt><dd>{graphStats.ips.toLocaleString("en-IN")}</dd></div>
              <div><dt>Transfers</dt><dd>{graphStats.sent.toLocaleString("en-IN")}</dd></div>
              <div>
                <dt><span className="kpi__key" style={{ background: DECISION_COLORS.BLOCK }} aria-hidden="true" />Known fraud accounts</dt>
                <dd>{graphStats.fraud_seeds}</dd>
              </div>
              <div><dt>Fraud-adjacent accounts</dt><dd>{graphStats.fraud_adjacent}</dd></div>
            </dl>
          )}
        </Live>
      </Card>

      <Card className="span-12" title="What the graph layer looks for" subtitle="Cypher patterns scored at up to 30 points">
        <dl className="stat-list stat-list--wide">
          <div><dt>Shared device</dt><dd>two accounts signing in from one device</dd></div>
          <div><dt>Shared IP address</dt><dd>unrelated accounts on one address</dd></div>
          <div><dt>Circular flow</dt><dd>money returning to its sender through hops</dd></div>
          <div><dt>Money mule pattern</dt><dd>funds in and straight back out, minus a cut</dd></div>
          <div><dt>Fraud cluster proximity</dt><dd>within two hops of a known fraud account</dd></div>
        </dl>
      </Card>
    </div>
  );
}
