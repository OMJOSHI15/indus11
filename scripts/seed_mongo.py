"""
Seed MongoDB with test accounts. Owner: Member A

Creates a predictable set of accounts covering every risk scenario the demo
needs: normal users, high spenders, elevated/high risk tiers, and blacklisted
accounts. Safe to re-run — existing account_ids are skipped.

Run from the project root (MongoDB must be up):
    python -m scripts.seed_mongo
"""
import asyncio

from app.core.database import close_db, init_db
from app.models.account import Account

SEED_ACCOUNTS = [
    # account_id, owner_name, country, avg_monthly_tx, blacklisted, risk_tier
    ("ACC-001", "Alice Martin", "CA", 1200.0, False, "standard"),
    ("ACC-002", "Bob Tremblay", "CA", 850.0, False, "standard"),
    ("ACC-003", "Chen Wei", "CA", 2400.0, False, "standard"),
    ("ACC-004", "Dana Roy", "CA", 560.0, False, "standard"),
    ("ACC-005", "Ethan Singh", "CA", 3100.0, False, "standard"),
    ("ACC-006", "Fatima Khan", "CA", 940.0, False, "standard"),
    ("ACC-007", "Gabriel Cote", "CA", 15000.0, False, "standard"),   # high spender — big tx is normal
    ("ACC-008", "Hana Kimura", "JP", 2200.0, False, "standard"),
    ("ACC-009", "Igor Petrov", "CA", 720.0, False, "elevated"),
    ("ACC-010", "Julia Santos", "BR", 1800.0, False, "elevated"),
    ("ACC-011", "Karim Haddad", "CA", 400.0, False, "elevated"),
    ("ACC-012", "Lena Fischer", "DE", 2900.0, False, "high"),
    ("ACC-013", "Marco Rossi", "CA", 650.0, False, "high"),
    ("ACC-014", "Nadia Osei", "CA", 1100.0, True, "high"),           # blacklisted
    ("ACC-015", "Omar Farouk", "CA", 300.0, True, "high"),           # blacklisted
    ("ACC-016", "Priya Sharma", "IN", 1600.0, False, "standard"),
    ("ACC-017", "Quinn OBrien", "CA", 880.0, False, "standard"),
    ("ACC-018", "Rosa Alvarez", "MX", 1950.0, False, "standard"),
    ("ACC-019", "Sam Whitefeather", "CA", 500.0, False, "standard"),
    ("ACC-020", "Tara Nguyen", "CA", 2750.0, False, "standard"),
]


async def seed() -> None:
    await init_db()
    created, skipped = 0, 0

    for account_id, owner, country, avg_tx, blacklisted, tier in SEED_ACCOUNTS:
        avg_inr = avg_tx * 80  # amounts in INR (₹)
        existing = await Account.find_one(Account.account_id == account_id)
        if existing:
            existing.avg_monthly_transaction = avg_inr
            existing.is_blacklisted = blacklisted
            existing.risk_tier = tier
            await existing.save()
            skipped += 1
            continue
        await Account(
            account_id=account_id,
            owner_name=owner,
            country_code=country,
            avg_monthly_transaction=avg_inr,
            is_blacklisted=blacklisted,
            risk_tier=tier,
        ).insert()
        created += 1

    await close_db()
    print(f"Seeded MongoDB accounts: {created} created, {skipped} already existed.")


if __name__ == "__main__":
    asyncio.run(seed())
