"""Beanie document model for accounts (MongoDB `accounts` collection)."""
from typing import Annotated

from beanie import Document, Indexed


class Account(Document):
    account_id: Annotated[str, Indexed(unique=True)]
    owner_name: str
    country_code: str = "CA"
    avg_monthly_transaction: float = 0.0
    is_blacklisted: bool = False
    risk_tier: str = "standard"  # standard | elevated | high

    class Settings:
        name = "accounts"
