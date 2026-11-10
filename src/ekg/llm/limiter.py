import time
from collections import deque


class RateLimiter:
    def __init__(self, rpm: int, tpm: int) -> None:
        self.rpm = rpm
        self.tpm = tpm
        self.calls: deque[float] = deque()
        self.tokens: deque[tuple[float, int]] = deque()

    def acquire(self, estimated_tokens: int) -> None:
        now = time.monotonic()
        self._trim(now)
        if len(self.calls) >= self.rpm or sum(item[1] for item in self.tokens) + estimated_tokens > self.tpm:
            wait = 60 - (now - self.calls[0]) if self.calls else 0.1
            time.sleep(max(wait, 0.01))
            self.acquire(estimated_tokens)
            return
        self.calls.append(now)
        self.tokens.append((now, estimated_tokens))

    def _trim(self, now: float) -> None:
        while self.calls and now - self.calls[0] >= 60:
            self.calls.popleft()
        while self.tokens and now - self.tokens[0][0] >= 60:
            self.tokens.popleft()
