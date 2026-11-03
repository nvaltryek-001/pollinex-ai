"""Small in-process sliding-window rate limiter (per key).

Suitable for a single API process (local use, small deployments). Behind several workers or hosts, use a
shared limiter at the reverse proxy instead. Disable with RATE_LIMIT_ENABLED=false (e.g. load tests).
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def enabled() -> bool:
    return os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"


def limit(key: str, max_calls: int, window_s: float) -> None:
    if not enabled():
        return
    now = time.monotonic()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window_s:
            q.popleft()
        if len(q) >= max_calls:
            retry = int(window_s - (now - q[0])) + 1
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many requests; retry in {retry} s",
                                headers={"Retry-After": str(retry)})
        q.append(now)


def reset() -> None:
    with _lock:
        _hits.clear()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
