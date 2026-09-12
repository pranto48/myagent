# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 2.2.0
import time
from typing import Dict, List, Tuple
from config import settings

class RateLimiter:
    """
    Sliding Window Rate Limiter and Brute-Force Shield.
    Protects authentication endpoints and LLM inference from credential stuffing and DoS.
    """
    _requests: Dict[str, List[float]] = {}
    _lockouts: Dict[str, float] = {}

    @classmethod
    def check_rate_limit(cls, key: str, max_limit: int = 60, window_seconds: int = 60) -> Tuple[bool, int]:
        """
        Checks if the specified identifier (IP address or user) has exceeded the rate limit.
        Returns (is_allowed, retry_after_seconds).
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, 0

        now = time.time()

        # Check existing lockout
        if key in cls._lockouts:
            remaining_lockout = cls._lockouts[key] - now
            if remaining_lockout > 0:
                return False, int(remaining_lockout)
            else:
                del cls._lockouts[key]

        # Clean old timestamps
        history = cls._requests.get(key, [])
        valid_history = [t for t in history if now - t < window_seconds]
        cls._requests[key] = valid_history

        if len(valid_history) >= max_limit:
            # Exceeded limit, impose temporary cool-down
            cls._lockouts[key] = now + window_seconds
            return False, window_seconds

        cls._requests[key].append(now)
        return True, 0

    @classmethod
    def record_auth_failure(cls, key: str, max_failures: int = 5, lockout_seconds: int = 300) -> bool:
        """
        Tracks failed login attempts and triggers exponential lockout after threshold.
        """
        now = time.time()
        failure_key = f"auth_fail:{key}"
        history = cls._requests.get(failure_key, [])
        valid_history = [t for t in history if now - t < 300]
        valid_history.append(now)
        cls._requests[failure_key] = valid_history

        if len(valid_history) >= max_failures:
            cls._lockouts[key] = now + lockout_seconds
            return True # Lockout triggered
        return False

    @classmethod
    def reset(cls, key: str):
        """Clears lockouts and histories on successful authentication."""
        failure_key = f"auth_fail:{key}"
        cls._requests.pop(key, None)
        cls._requests.pop(failure_key, None)
        cls._lockouts.pop(key, None)
