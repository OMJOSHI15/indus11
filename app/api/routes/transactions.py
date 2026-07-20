"""
Transaction analysis routes — the main API surface.
Owner: Member A (route/persistence), B (graph), C (RAG/decision)
"""
import asyncio
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.rate_limit import limiter
from app.core.redis_client import cache_get, cache_set
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.risk import AccountProfile
from app.schemas.transaction import AnalysisResponse, TransactionRequest
from app.services.decision_engine import make_decision
from app.services.graph_analyzer import run_graph_analyzer
from app.services.rag_pipeline import run_rag_pipeline
from app.services.rule_engine import run_rule_engine

router = APIRouter(prefix="/transactions", tags=["transactions"])


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


@router.post("/analyze", response_model=AnalysisResponse, summary="Analyze a transaction for fraud risk")
@limiter.limit("30/minute")
async def analyze_transaction(request: Request, tx: TransactionRequest):
    """
    Submit a transaction for real-time fraud analysis.

    All three analyzers (Rule Engine, Neo4j Graph, RAG Pipeline) run in parallel.
    The Decision Engine aggregates scores and returns APPROVE / REVIEW / BLOCK.
    """
    start = time.perf_counter()

    # Load account profiles (cached)
    sender, receiver = await asyncio.gather(
        _load_account_profile(tx.sender_account_id),
        _load_account_profile(tx.receiver_account_id),
    )

    # Run all three analyzers concurrently
    rule_result, graph_result, rag_result = await asyncio.gather(
        run_rule_engine(tx, sender, receiver),
        run_graph_analyzer(tx),
        run_rag_pipeline(tx, sender),
    )

    # Unpack RAG tuple (score, explanation)
    if isinstance(rag_result, tuple):
        rag_score, rag_explanation = rag_result
    else:
        rag_score, rag_explanation = rag_result, "RAG pipeline unavailable."

    elapsed_ms = (time.perf_counter() - start) * 1000

    response = make_decision(tx, rule_result, graph_result, rag_score, rag_explanation, elapsed_ms)

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
        created_at=datetime.utcnow(),
    )
    await db_tx.insert()

    return response


class DecisionUpdate(BaseModel):
    decision: str


@router.patch("/{tx_id}/decision", summary="Override a transaction decision (approve/block a review)")
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
async def list_transactions(decision: str | None = None, limit: int = 50):
    query = Transaction.find()
    if decision:
        query = Transaction.find(Transaction.decision == decision.upper())
    return await query.sort(-Transaction.created_at).limit(limit).to_list()
