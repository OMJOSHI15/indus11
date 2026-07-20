"""Beanie document model for transactions (MongoDB `transactions` collection)."""
from datetime import datetime
from typing import Annotated, Optional

from beanie import Document, Indexed
from pydantic import Field


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
    decision: Annotated[Optional[str], Indexed()] = None  # APPROVE | REVIEW | BLOCK
    explanation: Optional[str] = None
    note: Optional[str] = None  # optional reason submitted with the transaction
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "transactions"
