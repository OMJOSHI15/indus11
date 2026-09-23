"""Beanie document model for transactions (MongoDB `transactions` collection)."""
from datetime import datetime
from typing import Annotated, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field


class DecisionChange(BaseModel):
    """
    One human override of a pipeline decision. Kept because the decision field
    alone cannot answer "who released this payment, and when" — the question a
    reviewer or an auditor asks first.
    """
    at: datetime = Field(default_factory=datetime.utcnow)
    from_decision: Optional[str] = None
    to_decision: str
    actor: str = "unknown"     # the caller holds a shared API key, so this is self-declared
    reason: Optional[str] = None


class Transaction(Document):
    tx_id: Annotated[str, Indexed(unique=True)]
    sender_account_id: Annotated[str, Indexed()]
    receiver_account_id: Annotated[str, Indexed()]
    amount: float
    currency: str = "INR"
    merchant_category: Optional[str] = None
    merchant_id: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    composite_score: Optional[int] = None
    # Per-layer scores, kept beside the composite: the response has always
    # carried them, but only the total was stored, so a past decision could not
    # be attributed to a layer afterwards. None on a layer that has not run.
    rule_score: Optional[int] = None
    graph_score: Optional[int] = None
    rag_score: Optional[int] = None
    decision: Annotated[Optional[str], Indexed()] = None  # APPROVE | REVIEW | BLOCK
    explanation: Optional[str] = None
    note: Optional[str] = None  # optional reason submitted with the transaction
    rag_pending: bool = False  # True until the background RAG/LLM layer updates this record
    # Set only by scripts/drain_pending.py. An explanation written long after
    # the decision it explains must not read as contemporaneous, so the record
    # carries when it was finished and the drawer says so.
    rag_drained_at: Optional[datetime] = None
    layer_failures: dict[str, str] = Field(default_factory=dict)  # layer name -> error; empty when every layer ran
    overrides: list[DecisionChange] = Field(default_factory=list)  # append-only; the pipeline never writes here
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "transactions"
