// Self-check for the explanation parser: node src/signals.check.mjs
import assert from "node:assert";
import { parseExplanation, humanize } from "./signals.js";
const r = parseExplanation("Triggered signals: AMOUNT_ANOMALY (₹704000 vs avg ₹52000); SHARED_IP (12 accounts on IP 203.0.113.66); HIGH_RISK_SENDER_TIER; wire_fraud. A massive wire. More.");
assert.deepEqual(r.signals.map(s => [s.code, s.layer]), [["AMOUNT_ANOMALY","rule"],["SHARED_IP","graph"],["HIGH_RISK_SENDER_TIER","rule"],["wire_fraud","model"]]);
assert.equal(r.signals[1].detail, "12 accounts on IP 203.0.113.66");
assert.equal(r.text, "A massive wire. More.");
assert.deepEqual(parseExplanation("No fraud signals triggered. ok"), { signals: [], text: "No fraud signals triggered. ok" });
assert.equal(parseExplanation("Triggered signals: RULE_ENGINE_ERROR (x). Rule engine failed.").signals.length, 0);
assert.equal(parseExplanation(null).text, "");
assert.equal(humanize("SHARED_DEVICE"), "Shared device");
assert.equal(humanize("SHARED_IP"), "Shared IP");
console.log("ok");
