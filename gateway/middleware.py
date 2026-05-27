#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gateway middleware components."""

from .config import RateLimiter, GatewayConfig, authenticate
from typing import Dict, Optional
import time


class RateLimitMiddleware:
    """Rate limiting middleware."""
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.limiter = RateLimiter(config.rate_limit, config.rate_window)
        self.stats = {
            "total": 0,
            "allowed": 0,
            "denied": 0,
            "start_time": time.time()
        }
    
    def check(self, client_id: str) -> bool:
        """Check rate limit."""
        if not self.config.enable_rate_limit:
            return True
        
        self.stats["total"] += 1
        allowed = self.limiter.is_allowed(client_id)
        
        if allowed:
            self.stats["allowed"] += 1
        else:
            self.stats["denied"] += 1
        
        return allowed
    
    def get_stats(self) -> Dict:
        """Get middleware statistics."""
        return {
            **self.stats,
            "uptime": time.time() - self.stats["start_time"],
            "limit": self.config.rate_limit,
            "window": self.config.rate_window
        }


class AuthMiddleware:
    """Authentication middleware."""
    
    def __init__(self, config: GatewayConfig):
        self.config = config
    
    def check(self, api_key: Optional[str]) -> bool:
        """Check authentication."""
        if not self.config.enable_auth:
            return True
        
        return authenticate(api_key or "", self.config.api_keys)


__all__ = ["RateLimitMiddleware", "AuthMiddleware", "RateLimiter", "GatewayConfig", "authenticate"]
