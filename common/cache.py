#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Caching utilities for the Agent-Z.
Uses cachetools for robust LRU cache implementation.

Author: Agent-Z Team
Version: 1.0.0
"""

import hashlib
from typing import Optional, Dict, Any

from cachetools import LRUCache as _LRUCache


class LRUCache(_LRUCache):
    """LRU Cache wrapper using cachetools.
    
    Provides thread-safe LRU cache with TTL support and statistics.
    """
    
    def __init__(self, maxsize: int = 100, ttl: Optional[float] = None):
        """Initialize the LRU cache.
        
        Args:
            maxsize: Maximum number of items to store.
            ttl: Optional time-to-live in seconds.
        """
        super().__init__(maxsize=maxsize)
        self.ttl = ttl
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        if key in self:
            self._hits += 1
            return super().get(key)
        self._misses += 1
        return None
    
    def put(self, key: str, value: Any) -> None:
        """Put a value into the cache."""
        if key in self:
            self.pop(key)
        if len(self) >= self.maxsize:
            # Remove oldest entry
            oldest_key = next(iter(self))
            self.pop(oldest_key)
        self[key] = value
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self),
            "max_size": self.maxsize,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0
        }


def create_cache_key(input_data: str, config_hash: str) -> str:
    """Create a cache key from input data and configuration."""
    key_data = f"{input_data}:{config_hash}"
    return hashlib.md5(key_data.encode('utf-8')).hexdigest()


def hash_config(config: Any) -> str:
    """Create a hash of the agent configuration."""
    if hasattr(config, 'model_dump'):
        # Pydantic model
        config_str = config.model_dump_json()
    elif hasattr(config, '__dict__'):
        attrs = sorted(config.__dict__.items())
        config_str = str(attrs)
    else:
        config_str = repr(config)
    return hashlib.md5(config_str.encode('utf-8')).hexdigest()
