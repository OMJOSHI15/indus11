"""Risk and account schemas."""
from pydantic import BaseModel


class AccountProfile(BaseModel):
    account_id: str
    owner_name: str
    avg_monthly_transaction: float = 0.0
    is_blacklisted: bool = False
    country_code: str = "CA"
    risk_tier: str = "standard"  # standard | elevated | high


class RiskSummary(BaseModel):
    account_id: str
    total_transactions: int
    flagged_count: int
    last_block_reason: str | None = None
