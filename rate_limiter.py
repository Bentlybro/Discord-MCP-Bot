import time
from collections import defaultdict, deque
from typing import Dict, Deque
import asyncio

class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, identifier: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds

        user_requests = self.requests[identifier]

        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()

        if len(user_requests) >= self.max_requests:
            return False

        user_requests.append(now)
        return True

    def get_remaining_requests(self, identifier: str) -> int:
        now = time.time()
        window_start = now - self.window_seconds

        user_requests = self.requests[identifier]

        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()

        return max(0, self.max_requests - len(user_requests))

    def get_reset_time(self, identifier: str) -> float:
        user_requests = self.requests[identifier]
        if not user_requests:
            return 0

        return user_requests[0] + self.window_seconds