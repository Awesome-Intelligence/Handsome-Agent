#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Core module caching functionality.

These tests cover LRU cache implementation and cache key generation.
"""

import unittest
from core.cache import LRUCache, create_cache_key, hash_config
from core import AgentConfig


class TestLRUCache(unittest.TestCase):
    """Test LRU cache implementation."""
    
    def test_lru_cache_basic(self):
        """Test basic LRU cache functionality."""
        cache = LRUCache(maxsize=3)
        
        # Test put and get
        cache.put("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")
        
        # Test multiple items
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        self.assertEqual(cache.get("key1"), "value1")
        self.assertEqual(cache.get("key2"), "value2")
        self.assertEqual(cache.get("key3"), "value3")
        
        # Test eviction (maxsize=3, add 4th item)
        cache.put("key4", "value4")
        self.assertIsNone(cache.get("key1"))  # Should be evicted
        self.assertEqual(cache.get("key2"), "value2")
        self.assertEqual(cache.get("key3"), "value3")
        self.assertEqual(cache.get("key4"), "value4")
    
    def test_lru_cache_update(self):
        """Test LRU cache update behavior."""
        cache = LRUCache(maxsize=2)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key1", "value1_updated")  # Update existing key
        
        # Check values without using get() to avoid changing LRU order
        self.assertEqual(cache.cache["key1"], "value1_updated")
        self.assertEqual(cache.cache["key2"], "value2")
        
        # Add new item - should evict key2 (least recently used)
        cache.put("key3", "value3")
        self.assertEqual(cache.cache["key1"], "value1_updated")
        self.assertNotIn("key2", cache.cache)
        self.assertEqual(cache.cache["key3"], "value3")


class TestCacheKeyGeneration(unittest.TestCase):
    """Test cache key generation functions."""
    
    def test_create_cache_key(self):
        """Test cache key creation."""
        key1 = create_cache_key("query1", "config1")
        key2 = create_cache_key("query1", "config1")
        key3 = create_cache_key("query2", "config1")
        
        self.assertEqual(key1, key2)  # Same input should produce same key
        self.assertNotEqual(key1, key3)  # Different input should produce different key
    
    def test_hash_config(self):
        """Test configuration hashing."""
        config1 = AgentConfig()
        config2 = AgentConfig()
        config3 = AgentConfig(explanation_depth="brief")
        
        hash1 = hash_config(config1)
        hash2 = hash_config(config2)
        hash3 = hash_config(config3)
        
        self.assertEqual(hash1, hash2)  # Same config should produce same hash
        self.assertNotEqual(hash1, hash3)  # Different config should produce different hash


if __name__ == "__main__":
    unittest.main(verbosity=2)