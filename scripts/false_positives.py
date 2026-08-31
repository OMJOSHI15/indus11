"""
Which graph pattern produces the most false positives?

Asked directly at Review 1 and left unanswered. This measures it instead of
reasoning about it: replay the labelled evaluation set through the graph
layer and count, per pattern, how often it fires on a transaction labelled
legitimate.

Calls run_graph_analyzer directly rather than going through /analyze — the
question is about the graph layer alone, and the endpoint's 30/minute rate
limit would otherwise stretch a 200-transaction replay over seven minutes.

    python -m scripts.false_positives
"""
import asyncio
from collections import defaultdict

from app.schemas.transaction import TransactionRequest
from app.services.graph_analyzer import run_graph_analyzer
from scripts.evaluate import build_eval_set


def _pattern(flag: str) -> str:
    """The flag code, without its parenthetical detail."""
    return flag.split(" (")[0]


async def main() -> None:
    rows = build_eval_set(run_id="FP")
    fired_on_legit: dict[str, int] = defaultdict(int)
    fired_on_fraud: dict[str, int] = defaultdict(int)
    legit_total = sum(r["label"] == "legit" for r in rows)
    fraud_total = len(rows) - legit_total

    for row in rows:
        payload = {k: v for k, v in row.items() if k not in ("label", "pattern")}
        result = await run_graph_analyzer(TransactionRequest(**payload))
        target = fired_on_legit if row["label"] == "legit" else fired_on_fraud
        for flag in result.flags:
            target[_pattern(flag)] += 1

    print(f"\n  Replayed {len(rows)} transactions "
          f"({fraud_total} fraud / {legit_total} legit)\n")
    print(f"  {'pattern':<28}{'on fraud':>10}{'on legit':>10}{'FP rate':>10}")
    print("  " + "-" * 58)

    # Rank by false-positive rate: of every firing, what share was wrong.
    rates = {
        name: fired_on_legit[name] / max(fired_on_legit[name] + fired_on_fraud[name], 1)
        for name in set(fired_on_legit) | set(fired_on_fraud)
    }
    for name, rate in sorted(rates.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<28}{fired_on_fraud[name]:>10}{fired_on_legit[name]:>10}{rate:>9.1%}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
