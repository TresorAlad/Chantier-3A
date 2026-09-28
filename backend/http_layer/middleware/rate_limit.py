"""Rate limiting for scan admission endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from http_layer.errors import json_error


class ScanRateLimitMiddleware(BaseHTTPMiddleware):
    """Limite simple par IP sur les routes /api/scan*."""

    def __init__(self, app, *, max_requests: int = 120, window_seconds: float = 60.0) -> None:
        """Initialize ``ScanRateLimitMiddleware``."""
        super().__init__(app)
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Dispatch on ``ScanRateLimitMiddleware``."""
        path = request.url.path
        if not path.startswith("/api/scan"):
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        q = self._hits[ip]
        while q and now - q[0] > self._window:
            q.popleft()
        if len(q) >= self._max:
            return json_error(429, "rate_limited", "too many scan requests")
        q.append(now)
        return await call_next(request)
