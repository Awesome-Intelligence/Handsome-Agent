#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gateway configuration and rate limiting."""

from dataclasses import dataclass, field
from typing import List
import time


@dataclass
class GatewayConfig:
    """Gateway configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    api_keys: List[str] = field(default_factory=list)
    rate_limit: int = 100
    rate_window: int = 60
    enable_auth: bool = True
    enable_rate_limit: bool = True
    enable_cors: bool = True
    max_request_size: int = 1024 * 1024


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, limit: int = 100, window: int = 60):
        self.limit = limit
        self.window = window
        self.requests = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        
        if client_id not in self.requests:
            self.requests[client_id] = {"count": 0, "window_start": now}
        
        entry = self.requests[client_id]
        
        if now - entry["window_start"] > self.window:
            entry["count"] = 0
            entry["window_start"] = now
        
        if entry["count"] >= self.limit:
            return False
        
        entry["count"] += 1
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests."""
        if client_id not in self.requests:
            return self.limit
        
        entry = self.requests[client_id]
        return max(0, self.limit - entry["count"])


def authenticate(api_key: str, valid_keys: List[str]) -> bool:
    """Simple API key authentication."""
    if not valid_keys:
        return len(api_key) >= 16
    return api_key in valid_keys
