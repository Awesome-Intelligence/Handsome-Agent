#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for async bridging functionality.

Tests cover:
- _get_tool_loop: persistent event loop for main thread
- _get_worker_loop: per-thread persistent event loops
- _run_async: sync->async bridging in various contexts
- execute_sync: registry synchronous execution with async handlers
"""

import asyncio
import threading
import time
import pytest

from tools.model_tools import _run_async, _get_tool_loop, _get_worker_loop
from tools.registry import registry, ToolEntry


class TestAsyncBridging:
    """Test async bridging functions."""

    def test_get_tool_loop_persistence(self):
        """Test that _get_tool_loop returns the same persistent loop."""
        loop1 = _get_tool_loop()
        loop2 = _get_tool_loop()
        
        assert loop1 is loop2
        assert not loop1.is_closed()

    def test_get_tool_loop_recreation_after_close(self):
        """Test that _get_tool_loop recreates after close."""
        loop1 = _get_tool_loop()
        loop1.close()
        
        loop2 = _get_tool_loop()
        
        assert loop1 is not loop2
        assert not loop2.is_closed()

    def test_get_worker_loop_per_thread(self):
        """Test that _get_worker_loop returns per-thread loops."""
        loops = []

        def get_loop_in_thread():
            loop = _get_worker_loop()
            loops.append(loop)
            return loop

        thread1 = threading.Thread(target=get_loop_in_thread)
        thread2 = threading.Thread(target=get_loop_in_thread)
        
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        assert len(loops) == 2
        assert loops[0] is not loops[1]

    def test_run_async_from_sync_context(self):
        """Test _run_async from a sync context."""
        async def async_func():
            await asyncio.sleep(0.01)
            return "async_result"

        result = _run_async(async_func())
        assert result == "async_result"

    def test_run_async_with_long_running_task(self):
        """Test _run_async handles longer-running async tasks."""
        async def slow_func():
            await asyncio.sleep(0.05)
            return "slow_result"

        start = time.monotonic()
        result = _run_async(slow_func())
        elapsed = time.monotonic() - start

        assert result == "slow_result"
        assert elapsed >= 0.05

    def test_run_async_from_worker_thread(self):
        """Test _run_async from a worker thread."""
        results = []

        def worker():
            async def async_func():
                await asyncio.sleep(0.01)
                return "worker_result"

            result = _run_async(async_func())
            results.append(result)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        assert len(results) == 1
        assert results[0] == "worker_result"

    def test_run_async_with_concurrent_threads(self):
        """Test _run_async works correctly with concurrent threads."""
        results = []
        barrier = threading.Barrier(5)

        def worker(thread_id):
            barrier.wait()

            async def async_func():
                await asyncio.sleep(0.02)
                return f"thread_{thread_id}"

            result = _run_async(async_func())
            results.append(result)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5
        for i in range(5):
            assert f"thread_{i}" in results


class TestExecuteSync:
    """Test registry.execute_sync method."""

    def test_execute_sync_with_sync_handler(self):
        """Test execute_sync with a sync handler."""
        def sync_handler(msg):
            return f"sync: {msg}"

        registry.register(
            name="test_sync_tool",
            toolset="test",
            schema={"type": "object", "properties": {"msg": {"type": "string"}}, "required": ["msg"]},
            handler=sync_handler,
            description="Sync test tool",
        )

        result = registry.execute_sync("test_sync_tool", {"msg": "hello"})
        assert result == "sync: hello"

        registry.unregister("test_sync_tool")

    def test_execute_sync_with_async_handler(self):
        """Test execute_sync with an async handler."""
        async def async_handler(msg):
            await asyncio.sleep(0.01)
            return f"async: {msg}"

        registry.register(
            name="test_async_tool",
            toolset="test",
            schema={"type": "object", "properties": {"msg": {"type": "string"}}, "required": ["msg"]},
            handler=async_handler,
            description="Async test tool",
            is_async=True,
        )

        result = registry.execute_sync("test_async_tool", {"msg": "hello"})
        assert result == "async: hello"

        registry.unregister("test_async_tool")

    def test_execute_sync_concurrent_calls(self):
        """Test execute_sync handles concurrent calls with async handlers."""
        results = []
        barrier = threading.Barrier(3)

        async def async_handler(msg):
            barrier.wait()
            await asyncio.sleep(0.02)
            return f"async: {msg}"

        registry.register(
            name="test_concurrent_tool",
            toolset="test",
            schema={"type": "object", "properties": {"msg": {"type": "string"}}, "required": ["msg"]},
            handler=async_handler,
            description="Concurrent test tool",
            is_async=True,
        )

        def worker(worker_id):
            result = registry.execute_sync("test_concurrent_tool", {"msg": f"worker_{worker_id}"})
            results.append(result)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 3
        for i in range(3):
            assert f"async: worker_{i}" in results

        registry.unregister("test_concurrent_tool")