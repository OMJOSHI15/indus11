// Split a stored explanation into the flags that fired and the model's prose.
//
// The decision engine writes "Triggered signals: CODE (detail); CODE. <prose>".
// Details can themselves contain full stops (IP addresses, ₹ amounts), so the
// end of the list is the first ". " outside parentheses, not the first ". ".

const PREFIX = "Triggered signals: ";

// Keep in sync with the flag codes in app/services/rule_engine.py and
// graph_analyzer.py. Anything else in the list came from the language model.
const RULE_CODES = new Set([
  "VELOCITY_EXCEEDED", "AMOUNT_ANOMALY", "BLACKLISTED_ACCOUNT",
  "HIGH_RISK_MERCHANT", "HIGH_RISK_SENDER_TIER", "ELEVATED_RISK_SENDER_TIER",
  "STRUCTURING", "DORMANT_ACCOUNT_REACTIVATED", "NEW_BENEFICIARY_HIGH_VALUE",
  "PASS_THROUGH", "BENEFICIARY_FAN_OUT", "ODD_HOUR_HIGH_VALUE",
  "SMURFING", "FAN_IN_COLLECTION_ACCOUNT", "MICRO_TEST_THEN_LARGE", "IMPOSSIBLE_TRAVEL",
  "NEW_DEVICE_HIGH_VALUE", "NEW_IP_HIGH_VALUE", "DEVICE_HOPPING", "DAILY_OUTFLOW_SPIKE",
  "REPEATED_ROUND_AMOUNTS", "SPLIT_PAYMENTS", "BACK_AND_FORTH", "NEAR_UPI_LIMIT_REPEATED",
  "LARGE_FIRST_TRANSACTION", "FIRST_HIGH_RISK_MERCHANT", "CURRENCY_MISMATCH",
  "HIGH_RISK_JURISDICTION", "SOCIAL_ENGINEERING_NOTE", "MERCHANT_COLLUSION_BURST",
  "ACCOUNT_DRAINING",
]);
const GRAPH_CODES = new Set([
  "SHARED_DEVICE", "SHARED_IP", "CIRCULAR_FLOW",
  "MONEY_MULE_PATTERN", "FRAUD_CLUSTER_PROXIMITY",
]);

export const LAYERS = [
  { key: "rule", label: "Rule engine" },
  { key: "graph", label: "Graph analysis" },
  { key: "model", label: "Language model" },
];

export const layerOf = (code) =>
  code.endsWith("_ERROR") ? "error"
    : RULE_CODES.has(code) ? "rule"
      : GRAPH_CODES.has(code) ? "graph"
        : "model";

/** "SHARED_DEVICE" → "Shared device", "wire_fraud" → "Wire fraud". */
export const humanize = (code) => {
  const words = code.toLowerCase().replace(/_/g, " ").replace(/\bip\b/g, "IP").replace(/\bupi\b/g, "UPI");
  return words.charAt(0).toUpperCase() + words.slice(1);
};

export function parseExplanation(explanation) {
  const source = explanation ?? "";
  if (!source.startsWith(PREFIX)) return { signals: [], text: source };

  let depth = 0;
  let end = source.length;
  for (let i = PREFIX.length; i < source.length; i += 1) {
    const ch = source[i];
    if (ch === "(") depth += 1;
    else if (ch === ")") depth -= 1;
    else if (ch === "." && depth === 0 && (source[i + 1] ?? " ") === " ") {
      end = i;
      break;
    }
  }

  const signals = source
    .slice(PREFIX.length, end)
    .split("; ")
    .filter(Boolean)
    .map((raw) => {
      const open = raw.indexOf(" (");
      const code = open < 0 ? raw.trim() : raw.slice(0, open).trim();
      const detail = open < 0 ? null : raw.slice(open + 2, -1);
      return { code, detail, layer: layerOf(code) };
    })
    .filter((s) => s.layer !== "error"); // failures are shown from layer_failures

  return { signals, text: source.slice(end + 1).trim() };
}
