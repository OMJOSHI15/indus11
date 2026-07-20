"""Account management routes. Owner: Member A"""
from fastapi import APIRouter, HTTPException

from app.core.redis_client import cache_delete
from app.models.account import Account
from app.schemas.risk import AccountProfile

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/", response_model=AccountProfile, summary="Create an account")
async def create_account(profile: AccountProfile):
    if await Account.find_one(Account.account_id == profile.account_id):
        raise HTTPException(status_code=409, detail="Account already exists")
    await Account(**profile.model_dump()).insert()
    return profile


@router.get("/{account_id}", response_model=AccountProfile, summary="Get account profile")
async def get_account(account_id: str):
    account = await Account.find_one(Account.account_id == account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return AccountProfile(
        account_id=account.account_id,
        owner_name=account.owner_name,
        avg_monthly_transaction=account.avg_monthly_transaction,
        is_blacklisted=account.is_blacklisted,
        country_code=account.country_code,
        risk_tier=account.risk_tier,
    )


@router.patch("/{account_id}/blacklist", summary="Toggle blacklist status")
async def toggle_blacklist(account_id: str, blacklisted: bool):
    account = await Account.find_one(Account.account_id == account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.is_blacklisted = blacklisted
    await account.save()
    await cache_delete(f"account:{account_id}")
    return {"account_id": account_id, "is_blacklisted": blacklisted}
