// Clearly-labeled sample data shown ONLY when the backend is unreachable,
// so the dashboard is still reviewable (demo mode banner is displayed).

export const SAMPLE_DISTRIBUTION = {
  decisions: { APPROVE: 132, REVIEW: 38, BLOCK: 17 },
  score_histogram: [
    { bucket: "0-19", count: 104 },
    { bucket: "20-39", count: 28 },
    { bucket: "40-59", count: 26 },
    { bucket: "60-79", count: 19 },
    { bucket: "80-100", count: 10 },
  ],
  total: 187,
};

export const SAMPLE_FLAGS = [
  {
    tx_id: "TX-20260704-0917",
    sender_account_id: "ACC-013",
    receiver_account_id: "ACC-461",
    amount: 9450.0,
    currency: "INR",
    merchant_category: "wire_transfer",
    composite_score: 82,
    decision: "BLOCK",
    explanation:
      "Triggered signals: AMOUNT_ANOMALY ($9450 vs avg $650); HIGH_RISK_MERCHANT (wire_transfer); MONEY_MULE_PATTERN (2 fee-skimming cycles). Wire just below the $10k reporting threshold from a high-risk sender into a known mule ring.",
    created_at: "2026-07-04T18:42:10Z",
  },
  {
    tx_id: "TX-20260704-0894",
    sender_account_id: "ACC-009",
    receiver_account_id: "ACC-486",
    amount: 2100.0,
    currency: "INR",
    merchant_category: "crypto_exchange",
    composite_score: 55,
    decision: "REVIEW",
    explanation:
      "Triggered signals: HIGH_RISK_MERCHANT (crypto_exchange); SHARED_IP (8 accounts on IP 203.0.113.66). First crypto purchase for this account at 3x monthly average.",
    created_at: "2026-07-04T17:20:44Z",
  },
  {
    tx_id: "TX-20260704-0851",
    sender_account_id: "ACC-014",
    receiver_account_id: "ACC-002",
    amount: 480.0,
    currency: "INR",
    merchant_category: "retail",
    composite_score: 74,
    decision: "BLOCK",
    explanation:
      "Triggered signals: BLACKLISTED_ACCOUNT. Sender is on the institutional blacklist.",
    created_at: "2026-07-04T15:03:29Z",
  },
  {
    tx_id: "TX-20260704-0812",
    sender_account_id: "ACC-005",
    receiver_account_id: "ACC-451",
    amount: 3200.0,
    currency: "INR",
    merchant_category: "money_service",
    composite_score: 48,
    decision: "REVIEW",
    explanation:
      "Triggered signals: HIGH_RISK_MERCHANT (money_service); FRAUD_CLUSTER_PROXIMITY (1 fraud neighbor). Receiver is one hop from a labeled fraud cluster.",
    created_at: "2026-07-04T13:55:02Z",
  },
  {
    tx_id: "TX-20260704-0788",
    sender_account_id: "ACC-011",
    receiver_account_id: "ACC-483",
    amount: 950.0,
    currency: "INR",
    merchant_category: "gambling",
    composite_score: 44,
    decision: "REVIEW",
    explanation:
      "Triggered signals: VELOCITY_EXCEEDED (7 tx in 10 min); HIGH_RISK_MERCHANT (gambling). Burst of transactions inconsistent with account history.",
    created_at: "2026-07-04T12:11:37Z",
  },
];
