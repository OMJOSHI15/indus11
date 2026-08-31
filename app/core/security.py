"""
API-key guard for mutating/administrative routes.

Not full authentication — no users, no sessions, just a shared secret that
gates the routes whose misuse actually corrupts a decision or the graph
(overriding a BLOCK, un-blacklisting an account, running label propagation).
Everything read-only (GET routes, /analyze) stays open, matching the
mentor's guidance to prioritise a working dashboard over auth infrastructure.
"""
import secrets

from fastapi import Header, HTTPException

from app.config import settings


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    # Constant-time compare — a naive `==` leaks the key length/prefix
    # through response-timing differences.
    if not secrets.compare_digest(x_api_key, settings.app_secret_key):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header")
