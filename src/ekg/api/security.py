import secrets
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class IpRateLimiter:
    def __init__(self, limit: int = 10, window: float = 60.0) -> None:
        self.limit, self.window = limit, window
        self.events: defaultdict[str, deque[float]] = defaultdict(deque)

    def allow(self, address: str) -> bool:
        now = time.monotonic()
        events = self.events[address]
        while events and now - events[0] > self.window:
            events.popleft()
        if len(events) >= self.limit:
            return False
        events.append(now)
        return True


def require_api_key(request: Request, expected: str) -> None:
    actual = request.headers.get("X-API-Key", "")
    if not expected or not secrets.compare_digest(actual, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


def require_write_rate(request: Request, limiter: IpRateLimiter) -> None:
    address = request.client.host if request.client else "unknown"
    if not limiter.allow(address):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limit exceeded")
