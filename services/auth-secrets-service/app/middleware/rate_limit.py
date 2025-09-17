from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..errors import error_response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._requests = defaultdict(deque)
        self._enabled = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() in {
            "1",
            "true",
            "yes",
        }
        self._window = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "10"))
        self._max_req = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "50"))

    async def dispatch(self, request: Request, call_next):
        if not self._enabled or request.url.path in {"/health", "/metrics"}:
            return await call_next(request)
        now = time.time()
        dq = self._requests[request.client.host if request.client else "unknown"]
        cutoff = now - self._window
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= self._max_req:
            return error_response(429, "rate_limited", "Too Many Requests")
        dq.append(now)
        return await call_next(request)
