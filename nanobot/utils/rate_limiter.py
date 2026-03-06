from __future__ import annotations
import time
import threading
from collections import defaultdict
from typing import Dict

class TokenBucket:
    def __init__(self, rate_per_sec: float, capacity: int):
        self.rate = float(rate_per_sec)
        self.capacity = int(capacity)
        self.tokens = float(capacity)
        self.timestamp = time.monotonic()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> float:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.timestamp
            self.timestamp = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0
            needed = tokens - self.tokens
            wait = needed / self.rate if self.rate > 0 else 1.0
            self.tokens = 0.0
            return wait

class PerDomainLimiter:
    def __init__(self, default_rps: float = 1.0, default_burst: int = 5):
        self.default_rps = float(default_rps)
        self.default_burst = int(default_burst)
        self._buckets: Dict[str, TokenBucket] = defaultdict(lambda: TokenBucket(self.default_rps, self.default_burst))

    def throttle(self, host: str):
        b = self._buckets[host]
        wait = b.consume(1)
        if wait > 0:
            time.sleep(wait)
