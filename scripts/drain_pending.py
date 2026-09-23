"""
Finish the RAG/LLM layer for transactions whose background task never completed.

The analyze route answers from the rule and graph layers and hands the LLM call
to a FastAPI BackgroundTask. That task lives in the API process: if the process
is restarted, or Ollama is down, or the call exceeds its timeout while nothing
is awaiting it, the record keeps `rag_pending: true` for good. Nothing retried
it until this script existed.

What it does, per pending record:
  - rebuilds the request from the stored fields;
  - re-reads the flags the deterministic layers raised, out of the stored
    explanation (the per-layer flag lists are not persisted, only the sentence
    they were written into);
  - runs the RAG layer again and re-bands the decision through the same
    make_decision the API uses, so a drained record is scored exactly as a
    live one would have been.

Attribution caveat, for records written before per-layer scores were stored:
their `rule_score`/`graph_score` are null, and the only thing left is the
composite, which for a pending record is precisely rule + graph (the pending
RAG layer contributes zero). The script therefore carries that sum in as the
rule score with the graph score at zero. The composite, the decision and the
explanation all come out right; only the split between the two deterministic
layers is lost, and it was already lost before this ran.

    python -m scripts.drain_pending --dry-run
    python -m scripts.drain_pending --limit 50
    python -m scripts.drain_pending --prefix EVAL
"""
import argparse
import asyncio
import time
from datetime import datetime

from app.services.explanation import signal_parts
from app.core.database import close_db, init_db
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.risk import AccountProfile
from app.schemas.transaction import AnalysisResponse, LayerScore, TransactionRequest
from app.services.decision_engine import make_decision
from app.services.rag_pipeline import run_rag_pipeline

RAG_TIMEOUT_S = 180
# Matches the API's own limit on concurrent language-model calls, so a drain
# does not queue behind itself or overload a laptop running the model locally.
CONCURRENCY = 4


async def profile_for(account_id: str) -> AccountProfile:
    account = await Account.find_one(Account.account_id == account_id)
    if not account:
        return AccountProfile(account_id=account_id, owner_name="Unknown", risk_tier="elevated")
    return AccountProfile(
        account_id=account.account_id, owner_name=account.owner_name,
        avg_monthly_transaction=account.avg_monthly_transaction,
        is_blacklisted=account.is_blacklisted, country_code=account.country_code,
        risk_tier=account.risk_tier,
    )


async def drain_one(record: Transaction) -> tuple[str, str]:
    """Returns (outcome, detail). Never raises: one bad record must not stop the run."""
    tx = TransactionRequest(
        tx_id=record.tx_id,
        sender_account_id=record.sender_account_id,
        receiver_account_id=record.receiver_account_id,
        amount=record.amount,
        currency=record.currency,
        merchant_category=record.merchant_category,
        merchant_id=record.merchant_id,
        device_id=record.device_id,
        ip_address=record.ip_address,
        note=record.note,
        timestamp=record.created_at,
    )
    flags = signal_parts(record.explanation)
    sender = await profile_for(record.sender_account_id)

    try:
        rag = await asyncio.wait_for(run_rag_pipeline(tx, sender, flags), timeout=RAG_TIMEOUT_S)
        rag_score, rag_explanation = rag
    except Exception as e:
        return "failed", f"{type(e).__name__}: {e}"

    # See the module docstring: the composite of a pending record is rule + graph.
    deterministic = record.composite_score or 0
    rule = LayerScore(score=record.rule_score if record.rule_score is not None else deterministic,
                      max_score=40, flags=flags)
    graph = LayerScore(score=record.graph_score or 0, max_score=30, flags=[])

    final: AnalysisResponse = make_decision(tx, rule, graph, rag_score, rag_explanation, 0.0)
    was = record.decision
    await Transaction.find_one(Transaction.tx_id == record.tx_id).update(
        {"$set": {
            "composite_score": final.composite_score,
            "rag_score": rag_score.score,
            "decision": final.decision.value,
            "explanation": final.explanation[:2000],
            "layer_failures": final.layer_failures,
            "rag_pending": False,
            "rag_drained_at": datetime.utcnow(),
        }}
    )
    changed = "" if was == final.decision.value else f" {was} -> {final.decision.value}"
    return "drained", f"score {deterministic} -> {final.composite_score}{changed}"


async def main(limit: int, prefix: str | None, dry_run: bool) -> None:
    await init_db()
    query = Transaction.find(Transaction.rag_pending == True)   # noqa: E712 — Beanie builds a query, not a bool
    pending = await query.sort(Transaction.created_at).limit(limit).to_list()
    if prefix:
        pending = [p for p in pending if p.tx_id.startswith(prefix)]

    total = await Transaction.find(Transaction.rag_pending == True).count()   # noqa: E712
    print(f"{total} transactions pending; this run takes {len(pending)}")
    if dry_run:
        for record in pending[:20]:
            print(f"  would drain {record.tx_id}  score {record.composite_score}  {record.decision}")
        if len(pending) > 20:
            print(f"  … and {len(pending) - 20} more")
        await close_db()
        return

    counts = {"drained": 0, "failed": 0}
    started = time.time()
    done = 0
    limiter = asyncio.Semaphore(CONCURRENCY)

    async def run(record):
        nonlocal done
        async with limiter:
            outcome, detail = await drain_one(record)
        counts[outcome] += 1
        done += 1
        print(f"  [{done}/{len(pending)}] {record.tx_id}  {outcome}: {detail}", flush=True)

    await asyncio.gather(*(run(record) for record in pending))

    left = await Transaction.find(Transaction.rag_pending == True).count()   # noqa: E712
    print(f"\n{counts['drained']} drained, {counts['failed']} failed "
          f"in {time.time() - started:.0f}s; {left} still pending")
    await close_db()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=100, help="how many records to take this run")
    ap.add_argument("--prefix", help="only tx_ids starting with this, e.g. EVAL")
    ap.add_argument("--dry-run", action="store_true", help="list what would be drained and stop")
    args = ap.parse_args()
    asyncio.run(main(args.limit, args.prefix, args.dry_run))
