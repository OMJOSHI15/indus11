import { useEffect, useState } from "react";
import { getNeighbors } from "../api.js";

const W = 460;
const H = 300;
const CX = W / 2;
const CY = H / 2;
const RX = 140;
const RY = 104;
const MAX_NODES = 14;

const idOf = (n) => n.properties.account_id ?? n.properties.device_id ?? n.properties.address;

// Known fraud first so it is never the part cut off, then the counterparty,
// then shared infrastructure, then ordinary transfer partners.
const rank = (n, receiver) =>
  n.properties.risk_label === "fraud" ? 0
    : idOf(n) === receiver ? 1
      : n.label !== "Account" ? 2
        : n.properties.risk_label === "fraud_adjacent" ? 3 : 4;

function Shape({ node, x, y }) {
  const cls = `node node--${node.label.toLowerCase()}${
    node.properties.risk_label ? ` node--${node.properties.risk_label}` : ""}${node.receiver ? " node--receiver" : ""}`;
  if (node.label === "Device") return <rect className={cls} x={x - 6} y={y - 6} width="12" height="12" rx="3" />;
  if (node.label === "IPAddress") return <path className={cls} d={`M${x} ${y - 8}L${x + 8} ${y}L${x} ${y + 8}L${x - 8} ${y}Z`} />;
  return <circle className={cls} cx={x} cy={y} r="7" />;
}

/**
 * One hop around the sender: the accounts it paid and the devices and IPs it
 * shares. This is the neighbourhood the graph layer scored, drawn so a reviewer
 * can see a shared device or a fraud-labelled counterparty instead of reading
 * about it.
 */
export default function AccountGraph({ sender, receiver }) {
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    getNeighbors(sender)
      .then((data) => !cancelled && setState(data ? { status: "ready", data } : { status: "demo" }))
      .catch((err) => !cancelled && setState({
        status: String(err.message).startsWith("404") ? "absent" : "error",
      }));
    return () => { cancelled = true; };
  }, [sender]);

  if (state.status === "demo") return null;
  if (state.status === "loading") return <div className="skeleton" style={{ height: 240 }} />;
  if (state.status === "absent") return <p className="dim small">{sender} has no history in the graph yet.</p>;
  if (state.status === "error") return <p className="dim small">The graph database is unreachable, so the network cannot be drawn.</p>;

  const unique = [...new Map(state.data.neighbors.map((n) => [`${n.label}:${idOf(n)}`, n])).values()]
    .map((n) => ({ ...n, receiver: idOf(n) === receiver }))
    .sort((a, b) => rank(a, receiver) - rank(b, receiver));
  const nodes = unique.slice(0, MAX_NODES);
  const fraud = unique.filter((n) => n.properties.risk_label === "fraud").length;
  const shared = unique.filter((n) => n.label !== "Account").length;

  if (!nodes.length) return <p className="dim small">{sender} has no connections in the graph.</p>;

  const placed = nodes.map((node, i) => {
    const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
    return { node, angle, x: CX + RX * Math.cos(angle), y: CY + RY * Math.sin(angle) };
  });

  return (
    <figure className="account-graph">
      <svg viewBox={`0 0 ${W} ${H}`} role="img"
           aria-label={`${sender} connects to ${unique.length} nodes, ${fraud} labelled fraud`}>
        {placed.map(({ node, x, y }) => (
          <line key={`e-${node.label}-${idOf(node)}`}
                className={`edge${node.properties.risk_label === "fraud" ? " edge--fraud" : ""}`}
                x1={CX} y1={CY} x2={x} y2={y} />
        ))}
        {placed.map(({ node, angle, x, y }) => {
          const cos = Math.cos(angle);
          const lx = x + cos * 14;
          const ly = y + Math.sin(angle) * 14 + 3.5;
          const anchor = Math.abs(cos) < 0.2 ? "middle" : cos > 0 ? "start" : "end";
          return (
            <g key={`n-${node.label}-${idOf(node)}`}>
              <title>{`${idOf(node)} · ${node.via.replace("_", " ").toLowerCase()}`}</title>
              <Shape node={node} x={x} y={y} />
              <text className={`node-label${node.receiver ? " node-label--strong" : ""}`}
                    x={lx} y={Math.abs(cos) < 0.2 ? ly + Math.sign(Math.sin(angle)) * 6 : ly}
                    textAnchor={anchor}>
                {idOf(node)}
              </text>
            </g>
          );
        })}
        <circle className="node node--center" cx={CX} cy={CY} r="11" />
        <text className="node-label node-label--strong" x={CX} y={CY + 28} textAnchor="middle">{sender}</text>
      </svg>
      <figcaption>
        <span className="key" aria-hidden="true">
          <svg viewBox="0 0 12 12"><circle className="node" cx="6" cy="6" r="4" /></svg>account
          <svg viewBox="0 0 12 12"><rect className="node node--device" x="2" y="2" width="8" height="8" rx="2" /></svg>device
          <svg viewBox="0 0 12 12"><path className="node node--ipaddress" d="M6 1L11 6L6 11L1 6Z" /></svg>IP
        </span>
        <span>{unique.length} connections</span>
        <span>{shared} shared device or IP</span>
        <span className={fraud ? "fraud-count" : undefined}>{fraud} labelled fraud</span>
        {unique.length > MAX_NODES && <span>showing {MAX_NODES}</span>}
      </figcaption>
    </figure>
  );
}
