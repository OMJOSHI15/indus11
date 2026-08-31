"""
Measure /analyze response latency after the decision-path split.

Review 1 measured 14,046 ms end-to-end because the LLM call sat inside the
decision path. The split moved that call to a background task, so this
measures what a caller actually waits for: rule engine + graph analyzer.

    python -m scripts.benchmark_latency [n]

The /analyze route is rate limited to 30/minute, so runs above ~30 requests
report 429s for the remainder. That is the limiter working, not a failure —
set RATE_LIMIT_ENABLED=false in .env and restart the API for a longer run.
"""
import asyncio
import statistics
import sys
import time
from collections import Counter

import httpx

API = "http://localhost:8000/api/v1/transactions/analyze"
BUDGET_MS = 500  # the target agreed at Review 1


def _tx(i: int) -> dict:
    return {
        "tx_id": f"BENCH-{int(time.time())}-{i:04d}",
        "sender_account_id": f"ACC-{i % 20 + 1:03d}",
        "receiver_account_id": f"ACC-{(i + 7) % 20 + 1:03d}",
        "amount": 250.0 + (i % 40) * 300,
        "currency": "INR",
        "merchant_category": ["retail", "wire_transfer", "groceries", "crypto_exchange"][i % 4],
        "device_id": f"DEV-{i % 12:03d}",
        "ip_address": f"10.0.0.{i % 200 + 1}",
    }


async def main(n: int = 40) -> None:
    async with httpx.AsyncClient(timeout=60) as client:
        # One warm-up request: the first call pays for Mongo/Redis/Neo4j
        # connection setup, which no real caller pays on every request.
        await client.post(API, json=_tx(9999))

        latencies, decisions = [], []
        for i in range(n):
            start = time.perf_counter()
            r = await client.post(API, json=_tx(i))
            elapsed = (time.perf_counter() - start) * 1000
            if r.status_code != 200:
                print(f"  request {i} failed: {r.status_code} {r.text[:120]}")
                continue
            latencies.append(elapsed)
            decisions.append(r.json()["decision"])

    latencies.sort()
    mean = statistics.mean(latencies)
    print(f"\nRequests:      {len(latencies)}")
    print(f"Mean:          {mean:7.1f} ms")
    print(f"Median (p50):  {statistics.median(latencies):7.1f} ms")
    print(f"p95:           {latencies[int(len(latencies) * 0.95)]:7.1f} ms")
    print(f"Max:           {latencies[-1]:7.1f} ms")
    print(f"Within {BUDGET_MS} ms:  {sum(x <= BUDGET_MS for x in latencies)}/{len(latencies)}")
    print(f"Review 1 baseline: 14046 ms  ->  {14046 / mean:.0f}x faster")
    print(f"Decisions:     {dict(Counter(decisions))}")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 40))
