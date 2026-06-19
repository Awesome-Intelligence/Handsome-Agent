#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Callbacks - Callback system for async operations.

🚪 Access - 💬 CLI - 回调系统

提供异步操作的回调管理。
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Callback registry
_CALLBACKS: Dict[str, List[Callable]] = {
    "on_response": [],
    "on_tool_call": [],
    "on_error": [],
    "on_complete": [],
}


def register_callback(event: str, callback: Callable):
    """Register a callback.

    Args:
        event: Event name
        callback: Callback function
    """
    global _CALLBACKS

    if event not in _CALLBACKS:
        _CALLBACKS[event] = []

    if callback not in _CALLBACKS[event]:
        _CALLBACKS[event].append(callback)


def unregister_callback(event: str, callback: Callable):
    """Unregister a callback.

    Args:
        event: Event name
        callback: Callback function
    """
    global _CALLBACKS

    if event in _CALLBACKS and callback in _CALLBACKS[event]:
        _CALLBACKS[event].remove(callback)


async def trigger_callback(event: str, *args, **kwargs) -> List[Any]:
    """Trigger callbacks asynchronously.

    Args:
        event: Event name
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        List of callback results
    """
    global _CALLBACKS

    results = []
    callbacks = _CALLBACKS.get(event, [])

    for callback in callbacks:
        try:
            if asyncio.iscoroutinefunction(callback):
                result = await callback(*args, **kwargs)
            else:
                result = callback(*args, **kwargs)
            results.append(result)
        except Exception as e:
            logger.error(f"Callback failed: {event} -> {callback}: {e}")

    return results


def trigger_callback_sync(event: str, *args, **kwargs) -> List[Any]:
    """Trigger callbacks synchronously.

    Args:
        event: Event name
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        List of callback results
    """
    global _CALLBACKS

    results = []
    callbacks = _CALLBACKS.get(event, [])

    for callback in callbacks:
        try:
            result = callback(*args, **kwargs)
            results.append(result)
        except Exception as e:
            logger.error(f"Callback failed: {event} -> {callback}: {e}")

    return results


class CallbackManager:
    """Callback manager for managing multiple callbacks."""

    def __init__(self):
        self._callbacks: Dict[str, List[Callable]] = {}

    def register(self, event: str, callback: Callable):
        """Register a callback."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        if callback not in self._callbacks[event]:
            self._callbacks[event].append(callback)

    def unregister(self, event: str, callback: Callable):
        """Unregister a callback."""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)

    async def trigger(self, event: str, *args, **kwargs) -> List[Any]:
        """Trigger callbacks for an event."""
        results = []
        callbacks = self._callbacks.get(event, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    result = await callback(*args, **kwargs)
                else:
                    result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Callback failed: {callback}: {e}")

        return results

    def clear(self, event: Optional[str] = None):
        """Clear callbacks."""
        if event is None:
            self._callbacks.clear()
        elif event in self._callbacks:
            self._callbacks[event] = []


if __name__ == "__main__":
    # Test
    def test_callback(data):
        print(f"Callback triggered: {data}")

    register_callback("on_response", test_callback)
    trigger_callback_sync("on_response", "Hello, world!")
