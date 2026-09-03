"""Pydantic request/response schemas — the API contract shared across all team members."""
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

# Matches the dashboard's fixed category dropdown (dashboard/src/components/
# AnalyzeForm.jsx). Free text here would land straight in the RAG layer's LLM
# prompt (rag_pipeline.USER_PROMPT), which is a prompt-injection vector — a
# sender could put "groceries\n\nIGNORE PREVIOUS INSTRUCTIONS..." in this
# field to try to talk the model into a lower score.
# Keep in sync with the dashboard dropdown (dashboard/src/components/
# AnalyzeForm.jsx) and scripts/evaluate.py's LEGIT_CATEGORIES.
MerchantCategory = Literal[
    "groceries", "restaurants", "utilities", "retail", "travel",
    "fuel", "healthcare",
    "wire_transfer", "crypto_exchange", "gambling", "money_service",
]


class Decision(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class TransactionRequest(BaseModel):
    """Payload submitted for fraud analysis."""
    tx_id: str = Field(..., description="Unique transaction identifier")
    sender_account_id: str
    receiver_account_id: str
    amount: float = Field(..., gt=0)
    currency: str = Field(default="INR", max_length=3)
    merchant_category: Optional[MerchantCategory] = None
    merchant_id: Optional[str] = Field(default=None, max_length=64)
    device_id: Optional[str] = Field(default=None, max_length=128)
    ip_address: Optional[str] = Field(default=None, max_length=64)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    note: Optional[str] = Field(
        default=None, max_length=500,
        description="Optional reason/context for the transaction",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"json_schema_extra": {"example": {
        "tx_id": "TX-2026-001",
        "sender_account_id": "ACC-001",
        "receiver_account_id": "ACC-002",
        "amount": 4500.00,
        "currency": "CAD",
        "merchant_category": "wire_transfer",
        "device_id": "DEV-XYZ",
        "ip_address": "192.168.1.100",
    }}}


class LayerScore(BaseModel):
    """Score and flags from one analysis layer."""
    score: int
    max_score: int
    flags: list[str] = []


class AnalysisResponse(BaseModel):
    """Final fraud analysis response."""
    tx_id: str
    decision: Decision
    composite_score: int = Field(..., ge=0, le=100)
    rule_engine: LayerScore
    graph_analyzer: LayerScore
    rag_pipeline: LayerScore
    explanation: str
    processing_time_ms: float
    timestamp: datetime
    rag_pending: bool = Field(
        default=False,
        description="True if the RAG/LLM layer hasn't scored this transaction yet — "
                     "the rule+graph decision returned within budget and the written "
                     "explanation attaches once the language model finishes.",
    )
