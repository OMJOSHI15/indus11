"""
Replay the PaySim dataset through the rule engine and measure every rule
against PaySim's fraud labels.

PaySim (Lopez-Rojas, Elmir and Axelsson, 2016; Kaggle "ealaxi/paysim1") is a
simulation calibrated on one month of real mobile-money logs from an African
financial service. It is used here because it is the public dataset whose shape
matches this system: account-to-account payments with a sender, a receiver, an
amount, a type, an hourly time step and an isFraud label. Card datasets
(IEEE-CIS, the ULB credit-card set) have no receiver, so none of the
relationship rules could fire on them.

Only the rule engine is replayed. The graph layer needs every account loaded
into Neo4j and the language model takes seconds per transaction, so neither is
feasible over millions of rows; the numbers this script prints are rule-engine
numbers, and should be reported as such.

What does not carry over from PaySim, and is reported rather than hidden:
  - No merchant categories. TRANSFER is mapped to wire_transfer and CASH_OUT to
    money_service, which makes HIGH_RISK_MERCHANT fire on every row of the only
    two types PaySim puts fraud in. Its per-rule precision says how little that
    rule adds; judge the others on their own rows.
  - No account profiles. Average spend is each sender's running mean inside the
    replay, and PaySim senders rarely repeat, so AMOUNT_ANOMALY seldom has one.
  - Amounts are PaySim's currency units, compared with the ₹ thresholds as-is.
  - Time is an hourly step. Rows inside a step are spread one second apart so
    the velocity window has an order to follow.

Redis: the replay uses database 15 and flushes it at the start, so it never
touches the live system's history in database 0.

    python -m scripts.replay_paysim data/PS_20174392719_1491204439457_log.csv --rows 200000
"""
import argparse
import asyncio
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("REDIS_DB", "15")   # before app.config is imported

from app.core.redis_client import get_redis                 # noqa: E402
from app.schemas.risk import AccountProfile                 # noqa: E402
from app.schemas.transaction import TransactionRequest     # noqa: E402
from app.services.rule_engine import run_rule_engine       # noqa: E402

TYPE_TO_CATEGORY = {
    "TRANSFER": "wire_transfer",
    "CASH_OUT": "money_service",
    "PAYMENT": "retail",
    "DEBIT": "retail",
    "CASH_IN": None,
}
START = datetime(2026, 1, 1)
THRESHOLDS = [8, 10, 12, 15, 20, 25, 30]
OUT = Path(__file__).resolve().parents[1] / "docs" / "paysim-rule-results.json"


def to_transaction(row: dict, index: int) -> TransactionRequest:
    step = int(row["step"])
    return TransactionRequest(
        tx_id=f"PS-{index}",
        sender_account_id=row["nameOrig"],
        receiver_account_id=row["nameDest"],
        amount=max(float(row["amount"]), 0.01),     # a handful of PaySim rows have amount 0
        merchant_category=TYPE_TO_CATEGORY.get(row["type"]),
        timestamp=START + timedelta(hours=step - 1, seconds=index % 3600),
    )


def code(flag: str) -> str:
    return flag.split(" (", 1)[0]


def summarise(results: list[tuple[int, list[str], bool]]) -> dict:
    """results: (rule score, flag codes, is_fraud) per replayed row."""
    fraud = sum(1 for *_, f in results if f)
    legit = len(results) - fraud

    per_rule = defaultdict(lambda: {"fraud": 0, "legit": 0})
    for _, codes, is_fraud in results:
        for c in set(codes):
            per_rule[c]["fraud" if is_fraud else "legit"] += 1
    rules = {
        c: {**n,
            "precision": round(n["fraud"] / (n["fraud"] + n["legit"]), 4),
            "recall": round(n["fraud"] / fraud, 4) if fraud else 0.0}
        for c, n in sorted(per_rule.items(), key=lambda kv: -kv[1]["fraud"])
    }

    sweep = []
    for t in THRESHOLDS:
        tp = sum(1 for s, _, f in results if f and s >= t)
        fp = sum(1 for s, _, f in results if not f and s >= t)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / fraud if fraud else 0.0
        sweep.append({"min_rule_score": t, "flagged": tp + fp, "true_positives": tp,
                      "precision": round(p, 4), "recall": round(r, 4),
                      "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0})
    return {"rows": len(results), "fraud": fraud, "legit": legit, "rules": rules, "threshold_sweep": sweep}


async def replay(path: Path, rows: int) -> dict:
    redis = get_redis()
    await redis.flushdb()                               # database 15 only; see module docstring

    running = defaultdict(lambda: [0.0, 0])             # sender -> [amount total, count]
    results, started = [], time.time()
    with path.open(newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh)):
            if i >= rows:
                break
            tx = to_transaction(row, i)
            total, n = running[tx.sender_account_id]
            sender = AccountProfile(account_id=tx.sender_account_id, owner_name="",
                                    avg_monthly_transaction=total / n if n else 0.0)
            receiver = AccountProfile(account_id=tx.receiver_account_id, owner_name="")
            layer = await run_rule_engine(tx, sender, receiver)
            if layer.failed:
                raise SystemExit(f"Rule engine failed on row {i}: {layer.error}")
            running[tx.sender_account_id] = [total + tx.amount, n + 1]
            results.append((layer.score, [code(f) for f in layer.flags], row["isFraud"] == "1"))
            if i and i % 20_000 == 0:
                print(f"  {i:,} rows, {time.time() - started:.0f} s", file=sys.stderr)

    await redis.flushdb()
    await redis.aclose()
    return summarise(results)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path, help="PaySim log CSV from Kaggle (ealaxi/paysim1)")
    ap.add_argument("--rows", type=int, default=200_000, help="replay the first N rows, in time order")
    args = ap.parse_args()
    if not args.csv.exists():
        raise SystemExit(f"{args.csv} not found. Download PaySim from Kaggle (ealaxi/paysim1) first.")

    report = asyncio.run(replay(args.csv, args.rows))
    report.update(dataset="PaySim (Kaggle ealaxi/paysim1)", source_file=args.csv.name,
                  generated_at=datetime.utcnow().isoformat() + "Z",
                  scope="rule engine only; graph and language-model layers not replayed")
    OUT.write_text(json.dumps(report, indent=2))

    print(f"\n{report['rows']:,} rows · {report['fraud']:,} fraud · {report['legit']:,} legitimate\n")
    print(f"{'rule':32} {'fraud':>7} {'legit':>9} {'precision':>10} {'recall':>7}")
    for c, n in report["rules"].items():
        print(f"{c:32} {n['fraud']:>7,} {n['legit']:>9,} {n['precision']:>10.3f} {n['recall']:>7.3f}")
    print(f"\n{'rule score ≥':>12} {'flagged':>9} {'precision':>10} {'recall':>7} {'F1':>6}")
    for s in report["threshold_sweep"]:
        print(f"{s['min_rule_score']:>12} {s['flagged']:>9,} {s['precision']:>10.3f} {s['recall']:>7.3f} {s['f1']:>6.3f}")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
