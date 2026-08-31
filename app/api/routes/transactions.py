"""
Transaction analysis routes — the main API surface.
Owner: Member A (route/persistence), B (graph), C (RAG/decision)
"""
import asyncio
import logging
import time
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from app.core.rate_limit import limiter
from app.core.redis_client import cache_get, cache_set
from app.core.security import require_api_key
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.risk import AccountProfile
from app.schemas.transaction import AnalysisResponse, LayerScore, TransactionRequest
from app.services.decision_engine import make_decision
from app.services.graph_analyzer import run_graph_analyzer
from app.services.rag_pipeline import run_rag_pipeline
from app.services.rule_engine import run_rule_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])

# Shown while the RAG/LLM layer (13-14s measured, see the SRS NFR table) hasn't
# scored the transaction yet — Review 1 flagged that this call was gating the
# whole decision.
RAG_PENDING_EXPLANATION = (
    "Pending — the written explanation attaches once the language model finishes."
)

# Background RAG work is unbounded otherwise: replaying the 208-transaction
# evaluation set queued 208 concurrent language-model calls and killed the
# server. The deterministic path stays fast regardless — this only decides how
# quickly the explanations catch up.
_RAG_CONCURRENCY = asyncio.Semaphore(4)


async def _load_account_profile(account_id: str) -> AccountProfile:
    """Load account from Redis cache, fallback to MongoDB."""
    cached = await cache_get(f"account:{account_id}")
    if cached:
        return AccountProfile(**cached)

    account = await Account.find_one(Account.account_id == account_id)

    if not account:
        # Return a default profile for unknown accounts (flagged as elevated)
        profile = AccountProfile(
            account_id=account_id,
            owner_name="Unknown",
            risk_tier="elevated",
        )
    else:
        profile = AccountProfile(
            account_id=account.account_id,
            owner_name=account.owner_name,
            avg_monthly_transaction=account.avg_monthly_transaction,
            is_blacklisted=account.is_blacklisted,
            country_code=account.country_code,
            risk_tier=account.risk_tier,
        )

    await cache_set(f"account:{account_id}", profile.model_dump(), ttl=300)
    return profile


async def _finish_rag_layer(
    tx: TransactionRequest,
    sender: AccountProfile,
    rule_result: LayerScore,
    graph_result: LayerScore,
    deterministic_ms: float,
) -> None:
    """
    Runs after the response has already gone back to the client — the split
    Review 1 asked for: the LLM call (13-14s measured) never gates the
    decision, only the rule and graph layers do. Scores the RAG layer and
    folds the result into the persisted record, including a decision change
    if the RAG score moves the composite across a band.
    """
    start = time.perf_counter()
    async with _RAG_CONCURRENCY:
        try:
            rag_result = await run_rag_pipeline(tx, sender)
        except Exception as e:
            # Nothing awaits this task, so an escaping exception would only
            # surface in the log and leave the record pending forever. Clear
            # the flag and keep the deterministic decision already persisted.
            logger.warning(f"Background RAG failed for {tx.tx_id}: {e}")
            await Transaction.find_one(Transaction.tx_id == tx.tx_id).update(
                {"$set": {"rag_pending": False}}
            )
            return
    if isinstance(rag_result, tuple):
        rag_score, rag_explanation = rag_result
    else:
        rag_score, rag_explanation = rag_result, "RAG pipeline unavailable."
    total_ms = deterministic_ms + (time.perf_counter() - start) * 1000

    final = make_decision(tx, rule_result, graph_result, rag_score, rag_explanation, total_ms)
    await Transaction.find_one(Transaction.tx_id == tx.tx_id).update(
        {"$set": {
            "composite_score": final.composite_score,
            "decision": final.decision.value,
            "explanation": final.explanation[:2000],
            "rag_pending": False,
        }}
    )


@router.post("/analyze", response_model=AnalysisResponse, summary="Analyze a transaction for fraud risk")
@limiter.limit("30/minute")
async def analyze_transaction(request: Request, tx: TransactionRequest, background_tasks: BackgroundTasks):
    """
    Submit a transaction for real-time fraud analysis.

    The rule engine and graph analyzer run in parallel and must return within
    a ~500ms budget; the response and the initial persisted decision come
    from those two alone. The RAG/LLM layer runs afterward as a background
    task — its score, written explanation, and any resulting decision change
    land on the persisted record once ready (poll GET /transactions/{tx_id}
    and check `rag_pending`), never on this response.
    """
    start = time.perf_counter()

    # Load account profiles (cached)
    sender, receiver = await asyncio.gather(
        _load_account_profile(tx.sender_account_id),
        _load_account_profile(tx.receiver_account_id),
    )

    # Run the two deterministic analyzers concurrently — the RAG/LLM layer is
    # scored separately in the background, see _finish_rag_layer above.
    rule_result, graph_result = await asyncio.gather(
        run_rule_engine(tx, sender, receiver),
        run_graph_analyzer(tx),
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    pending_rag = LayerScore(score=0, max_score=30, flags=[])
    response = make_decision(
        tx, rule_result, graph_result, pending_rag, RAG_PENDING_EXPLANATION,
        elapsed_ms, rag_pending=True,
    )

    # Persist to MongoDB
    db_tx = Transaction(
        tx_id=tx.tx_id,
        sender_account_id=tx.sender_account_id,
        receiver_account_id=tx.receiver_account_id,
        amount=tx.amount,
        currency=tx.currency,
        merchant_category=tx.merchant_category,
        merchant_id=tx.merchant_id,
        device_id=tx.device_id,
        ip_address=tx.ip_address,
        composite_score=response.composite_score,
        decision=response.decision.value,
        explanation=response.explanation[:2000],
        note=tx.note,
        rag_pending=True,
        created_at=datetime.utcnow(),
    )
    # tx_id is uniquely indexed: a retry of an already-scored transaction is a
    # client conflict, not a server fault. Overwriting would destroy the audit trail.
    try:
        await db_tx.insert()
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail=f"Transaction {tx.tx_id} has already been analysed",
        )

    background_tasks.add_task(_finish_rag_layer, tx, sender, rule_result, graph_result, elapsed_ms)

    return response


class DecisionUpdate(BaseModel):
    decision: str


@router.patch(
    "/{tx_id}/decision",
    summary="Override a transaction decision (approve/block a review)",
    dependencies=[Depends(require_api_key)],
)
async def override_decision(tx_id: str, body: DecisionUpdate):
    dec = body.decision.upper()
    if dec not in ("APPROVE", "REVIEW", "BLOCK"):
        raise HTTPException(status_code=400, detail="decision must be APPROVE, REVIEW, or BLOCK")
    tx = await Transaction.find_one(Transaction.tx_id == tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    tx.decision = dec
    await tx.save()
    return tx


@router.get("/{tx_id}", summary="Retrieve a past transaction analysis")
async def get_transaction(tx_id: str):
    tx = await Transaction.find_one(Transaction.tx_id == tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    return tx


@router.get("/", summary="List recent transactions with optional decision filter")
async def list_transactions(decision: str | None = None, limit: int = Query(default=50, le=200)):
    query = Transaction.find()
    if decision:
        query = Transaction.find(Transaction.decision == decision.upper())
    return await query.sort(-Transaction.created_at).limit(limit).to_list()
