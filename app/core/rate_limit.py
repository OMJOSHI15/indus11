"""Rate limiting via slowapi. Owner: Member A"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed by client IP. Global default applies to every route via
# SlowAPIMiddleware (see main.py); hot endpoints set tighter limits
# with @limiter.limit(...).
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
