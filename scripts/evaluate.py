"""
Accuracy evaluation harness. Owner: Member A (metrics), Member B (graph metrics)

Replays a labelled synthetic dataset through the live pipeline and reports how well
the composite score separates fraud from legitimate traffic:

  - precision / recall / F1, treating REVIEW+BLOCK as "flagged" (and a strict
    BLOCK-only variant)
  - a full decision x truth confusion matrix
  - ring-detection recall for the graph layer
  - a threshold sweep that re-derives the decision bands from the recorded scores,
    so REVIEW_THRESHOLD / BLOCK_THRESHOLD can be tuned from data instead of guesses

Ground truth mirrors the planted patterns in scripts/seed_neo4j.py: mule-ring cycles
and shared-device / shared-IP identity clusters are fraud, ordinary traffic is not.

Run with the API up (python -m scripts.evaluate). Results are written to
docs/eval-results.json, which GET /api/v1/stats/accuracy serves to the dashboard.
"""
import argparse
import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import httpx

API_URL = "http://localhost:8000/api/v1/transactions/analyze"
RESULTS_PATH = Path(__file__).resolve().parent.parent / "docs" / "eval-results.json"

# Same seed as the dataset generator so the evaluation set is reproducible.
SEED = 42

# ── Ground truth, mirroring scripts/seed_neo4j.py ─────────────────────────────
RINGS = [
    ["ACC-451", "ACC-452", "ACC-453", "ACC-454"],
    ["ACC-461", "ACC-462", "ACC-463", "ACC-464", "ACC-465"],
    ["ACC-471", "ACC-472", "ACC-473"],
]
DEVICE_CLUSTERS = {
    "DEV-FRAUD-A": ["ACC-451", "ACC-452", "ACC-453", "ACC-481", "ACC-483", "ACC-484"],
    "DEV-FRAUD-B": ["ACC-461", "ACC-462", "ACC-482", "ACC-485"],
}
SHARED_IP = "203.0.113.66"
IP_CLUSTER = ["ACC-451", "ACC-461", "ACC-471", "ACC-481", "ACC-482", "ACC-486"]

LEGIT_CATEGORIES = ["groceries", "restaurants", "utilities", "retail", "fuel", "healthcare"]
BASE_TIME = datetime(2026, 7, 28)

# Decision bands currently configured (app/config.py). The sweep searches around these.
DEFAULT_REVIEW_THRESHOLD = 40
DEFAULT_BLOCK_THRESHOLD = 70


# ── Dataset ───────────────────────────────────────────────────────────────────
def build_eval_set(run_id: str = "TEST") -> list[dict]:
    """
    Return labelled transactions: `label` is "fraud" or "legit", everything else is
    the analyze-endpoint payload. Deterministic for a fixed SEED.

    `run_id` namespaces the tx_ids so a repeated evaluation does not collide with
    the previous run's records (the analyze endpoint 409s on a duplicate tx_id).
    """
    rng = random.Random(SEED)
    rows: list[dict] = []
    n = 0

    def add(sender, receiver, amount, category, label, device=None, ip=None, tag=""):
        nonlocal n
        n += 1
        rows.append({
            "tx_id": f"EVAL-{run_id}-{n:04d}",
            "sender_account_id": sender,
            "receiver_account_id": receiver,
            "amount": round(amount, 2),
            "currency": "INR",
            "merchant_category": category,
            "device_id": device,
            "ip_address": ip,
            "timestamp": (BASE_TIME + timedelta(minutes=n * 3)).isoformat(),
            "label": label,
            "pattern": tag,
        })

    # ── Fraud: mule-ring cycles, amounts skimmed 5-12% per hop ────────────────
    for ring in RINGS:
        for cycle in range(3):
            amount = rng.uniform(300_000, 700_000)
            for i, sender in enumerate(ring):
                receiver = ring[(i + 1) % len(ring)]
                add(sender, receiver, amount, "wire_transfer", "fraud",
                    device=None, ip=SHARED_IP if sender in IP_CLUSTER else None,
                    tag="mule_ring")
                amount *= rng.uniform(0.88, 0.95)

    # ── Fraud: synthetic identities sharing one device ────────────────────────
    for device, members in DEVICE_CLUSTERS.items():
        for sender in members:
            add(sender, f"ACC-{rng.randint(1, 400):03d}", rng.uniform(80_000, 400_000),
                "crypto_exchange", "fraud", device=device, tag="shared_device")

    # ── Fraud: cluster of accounts behind one IP ──────────────────────────────
    for sender in IP_CLUSTER:
        add(sender, f"ACC-{rng.randint(1, 400):03d}", rng.uniform(50_000, 250_000),
            "money_service", "fraud", ip=SHARED_IP, tag="shared_ip")

    # ── Legit: ordinary retail traffic between unrelated accounts ─────────────
    # Roughly 3x the fraud volume, which is still far denser than reality — the
    # metrics below are therefore optimistic about precision on a live feed.
    for _ in range(len(rows) * 3):
        sender = f"ACC-{rng.randint(1, 400):03d}"
        receiver = f"ACC-{rng.randint(1, 400):03d}"
        if sender == receiver:
            continue
        add(sender, receiver, rng.uniform(500, 40_000),
            rng.choice(LEGIT_CATEGORIES), "legit",
            device=f"DEV-{rng.randint(1000, 9999)}",
            ip=f"10.0.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
            tag="normal")

    rng.shuffle(rows)
    return rows


# ── Pure metric functions (unit-tested in tests/test_eval.py) ─────────────────
def classify(score: int, review_threshold: int, block_threshold: int) -> str:
    """Re-derive a decision from a composite score. Mirrors decision_engine."""
    if score >= block_threshold:
        return "BLOCK"
    if score >= review_threshold:
        return "REVIEW"
    return "APPROVE"


def confusion(scored: list[dict], review_threshold: int, block_threshold: int) -> dict:
    """decision -> {fraud, legit} counts."""
    matrix = {d: {"fraud": 0, "legit": 0} for d in ("APPROVE", "REVIEW", "BLOCK")}
    for row in scored:
        decision = classify(row["composite_score"], review_threshold, block_threshold)
        matrix[decision][row["label"]] += 1
    return matrix


def precision_recall_f1(tp: int, fp: int, fn: int) -> dict:
    """Standard binary metrics; 0.0 rather than a division error on empty inputs."""
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def metrics_at(scored: list[dict], review_threshold: int, block_threshold: int) -> dict:
    """
    Two views of the same run:
      flagged - REVIEW or BLOCK counts as catching the fraud (what an analyst sees)
      blocked - only BLOCK counts (what actually stops a payment automatically)
    """
    matrix = confusion(scored, review_threshold, block_threshold)

    flagged_tp = matrix["REVIEW"]["fraud"] + matrix["BLOCK"]["fraud"]
    flagged_fp = matrix["REVIEW"]["legit"] + matrix["BLOCK"]["legit"]
    flagged_fn = matrix["APPROVE"]["fraud"]

    blocked_tp = matrix["BLOCK"]["fraud"]
    blocked_fp = matrix["BLOCK"]["legit"]
    blocked_fn = matrix["APPROVE"]["fraud"] + matrix["REVIEW"]["fraud"]

    return {
        "confusion": matrix,
        "flagged": precision_recall_f1(flagged_tp, flagged_fp, flagged_fn),
        "blocked": precision_recall_f1(blocked_tp, blocked_fp, blocked_fn),
    }


def sweep_thresholds(scored: list[dict]) -> dict:
    """
    Re-derive decisions from the recorded scores across candidate bands and return the
    best pair. No re-run needed: the composite score is fixed, only the mapping to a
    decision changes.

    Flagged-F1 alone cannot choose a block threshold — moving the block band shuffles
    transactions between REVIEW and BLOCK, and both count as "flagged", so every block
    value ties. Ties are therefore broken on blocked-F1, and when no transaction reaches
    any candidate block band the suggestion is reported as None rather than an arbitrary
    number: recommending one would silently turn every review into an auto-block.
    """
    best = None
    for review_threshold in range(20, 65, 5):
        for block_threshold in range(review_threshold + 5, 95, 5):
            metrics = metrics_at(scored, review_threshold, block_threshold)
            candidate = {
                "review_threshold": review_threshold,
                "block_threshold": block_threshold,
                "f1": metrics["flagged"]["f1"],
                "blocked_f1": metrics["blocked"]["f1"],
            }
            better = best is None or (
                (candidate["f1"], candidate["blocked_f1"]) > (best["f1"], best["blocked_f1"])
            )
            if better:
                best = candidate

    highest_score = max((row["composite_score"] for row in scored), default=0)
    if best is not None and highest_score < best["block_threshold"]:
        best["block_threshold"] = None
        best["block_note"] = (
            f"no transaction scored above {highest_score} — the block band never fires "
            "on this dataset"
        )
    return best


def ring_recall(scored: list[dict]) -> dict:
    """Graph layer: share of planted mule-ring transactions that got a graph flag."""
    ring_rows = [r for r in scored if r["pattern"] == "mule_ring"]
    detected = [r for r in ring_rows if r.get("graph_score", 0) > 0]
    total = len(ring_rows)
    return {
        "ring_transactions": total,
        "graph_flagged": len(detected),
        "recall": round(len(detected) / total, 4) if total else 0.0,
    }


# ── Live run ──────────────────────────────────────────────────────────────────
async def score_via_api(rows: list[dict], concurrency: int = 4) -> list[dict]:
    """POST each transaction to the analyze endpoint and record the response."""
    scored: list[dict] = []
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=120.0) as client:
        async def one(row):
            payload = {k: v for k, v in row.items() if k not in ("label", "pattern")}
            async with semaphore:
                response = await client.post(API_URL, json=payload)
            response.raise_for_status()
            body = response.json()
            scored.append({
                "tx_id": row["tx_id"],
                "label": row["label"],
                "pattern": row["pattern"],
                "composite_score": body["composite_score"],
                "decision": body["decision"],
                "rule_score": body["rule_engine"]["score"],
                "graph_score": body["graph_analyzer"]["score"],
                "rag_score": body["rag_pipeline"]["score"],
            })

        await asyncio.gather(*(one(row) for row in rows))

    return scored


def render(report: dict) -> str:
    """Plain-text summary for the terminal and for pasting into the report."""
    m, c = report["metrics"], report["metrics"]["confusion"]
    best = report["suggested_thresholds"]
    lines = [
        "",
        "=" * 62,
        "  INDUS11 — ACCURACY EVALUATION",
        "=" * 62,
        f"  dataset      : {report['counts']['total']} transactions "
        f"({report['counts']['fraud']} fraud / {report['counts']['legit']} legit)",
        f"  thresholds   : REVIEW >= {report['thresholds']['review']}, "
        f"BLOCK >= {report['thresholds']['block']}",
        "",
        "  Confusion matrix",
        f"    {'decision':<10}{'fraud':>8}{'legit':>8}",
    ]
    for decision in ("APPROVE", "REVIEW", "BLOCK"):
        lines.append(f"    {decision:<10}{c[decision]['fraud']:>8}{c[decision]['legit']:>8}")
    lines += [
        "",
        f"  Flagged (REVIEW or BLOCK)  precision {m['flagged']['precision']:.3f}   "
        f"recall {m['flagged']['recall']:.3f}   F1 {m['flagged']['f1']:.3f}",
        f"  Blocked (BLOCK only)       precision {m['blocked']['precision']:.3f}   "
        f"recall {m['blocked']['recall']:.3f}   F1 {m['blocked']['f1']:.3f}",
        "",
        f"  Graph ring recall          {report['graph']['recall']:.3f} "
        f"({report['graph']['graph_flagged']}/{report['graph']['ring_transactions']} "
        "ring transactions flagged)",
        "",
        f"  Best bands by F1           REVIEW >= {best['review_threshold']}, "
        + (
            f"BLOCK >= {best['block_threshold']}"
            if best["block_threshold"] is not None
            else "BLOCK n/a — " + best["block_note"]
        )
        + f"  (F1 {best['f1']:.3f})",
        "=" * 62,
        "",
    ]
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Indus11 accuracy")
    parser.add_argument("--review-threshold", type=int, default=DEFAULT_REVIEW_THRESHOLD)
    parser.add_argument("--block-threshold", type=int, default=DEFAULT_BLOCK_THRESHOLD)
    parser.add_argument("--limit", type=int, default=0, help="evaluate only the first N rows")
    args = parser.parse_args()

    run_id = datetime.utcnow().strftime("%m%d%H%M%S")
    rows = build_eval_set(run_id)
    if args.limit:
        rows = rows[: args.limit]

    print(f"Scoring {len(rows)} transactions against {API_URL} ...")
    try:
        scored = await score_via_api(rows)
    except (httpx.ConnectError, httpx.ReadTimeout):
        raise SystemExit(
            "Could not reach the API. Start the stack first:\n"
            "  ./scripts/run_local.sh      (or: docker compose up)"
        )

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "dataset": "synthetic (seeded mule rings, device/IP clusters, normal traffic)",
        "thresholds": {"review": args.review_threshold, "block": args.block_threshold},
        "counts": {
            "total": len(scored),
            "fraud": sum(1 for r in scored if r["label"] == "fraud"),
            "legit": sum(1 for r in scored if r["label"] == "legit"),
        },
        "metrics": metrics_at(scored, args.review_threshold, args.block_threshold),
        "graph": ring_recall(scored),
        "suggested_thresholds": sweep_thresholds(scored),
        # Per-row scores, so thresholds can be re-swept offline instead of
        # re-running the pipeline (an LLM-bound run takes over an hour).
        "scored": scored,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(render(report))
    print(f"Written to {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
