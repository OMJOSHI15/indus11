"""
API-key guard for mutating/administrative routes.

Not full authentication — no users, no sessions, no tenants, just a shared
secret that gates every route which writes.

That now includes /analyze. It is not read-only: each call writes a
transaction, extends the sender's Redis history and adds nodes and edges to
the graph, so an open endpoint lets any caller poison the state that every
later decision is scored against. GET routes stay open; they only read.

A shared secret identifies no one, so it stops strangers, not insiders. The
dashboard is a browser app and has to carry the key in its bundle, so anyone
who can open the dashboard can read it: this keeps the write routes closed to
the open internet, not to a determined user. Per-user authentication is out of
scope for this project and is recorded as such rather than implied.
"""
import secrets

from fastapi import Header, HTTPException

from app.config import settings


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    # Constant-time compare — a naive `==` leaks the key length/prefix
    # through response-timing differences.
    if not secrets.compare_digest(x_api_key, settings.app_secret_key):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header")
