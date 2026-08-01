"""Rate limiting via slowapi. Owner: Member A"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Keyed by client IP. Global default applies to every route via
# SlowAPIMiddleware (see main.py); hot endpoints set tighter limits
# with @limiter.limit(...).
# `enabled` is off only when benchmarking locally — see settings.rate_limit_enabled.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
    enabled=settings.rate_limit_enabled,
)
