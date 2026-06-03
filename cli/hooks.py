#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hooks - Lifecycle hook system.

🚪 Access - 💬 CLI - 生命周期钩子

提供在特定事件发生时执行回调的机制。
"""

import logging
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Hook registry
_HOOKS: Dict[str, List[Callable]] = {
    "before_chat": [],
    "after_chat": [],
    "before_tool": [],
    "after_tool": [],
    "on_error": [],
    "on_startup": [],
    "on_shutdown": [],
}


def register_hook(event: str, handler: Callable):
    """Register a hook handler.

    Args:
        event: Event name (e.g., 'before_chat', 'after_chat')
        handler: Handler function
    """
    global _HOOKS

    if event not in _HOOKS:
        _HOOKS[event] = []

    if handler not in _HOOKS[event]:
        _HOOKS[event].append(handler)
        logger.debug(f"Registered hook: {event}")


def unregister_hook(event: str, handler: Callable):
    """Unregister a hook handler.

    Args:
        event: Event name
        handler: Handler function
    """
    global _HOOKS

    if event in _HOOKS and handler in _HOOKS[event]:
        _HOOKS[event].remove(handler)
        logger.debug(f"Unregistered hook: {event}")


def trigger_hook(event: str, *args, **kwargs):
    """Trigger a hook event.

    Args:
        event: Event name
        *args: Positional arguments to pass to handlers
        **kwargs: Keyword arguments to pass to handlers

    Returns:
        List of handler return values
    """
    global _HOOKS

    results = []
    handlers = _HOOKS.get(event, [])

    for handler in handlers:
        try:
            result = handler(*args, **kwargs)
            results.append(result)
        except Exception as e:
            logger.error(f"Hook handler failed: {event} -> {handler}: {e}")

    return results


def get_hooks(event: str) -> List[Callable]:
    """Get all handlers for an event.

    Args:
        event: Event name

    Returns:
        List of handler functions
    """
    return list(_HOOKS.get(event, []))


def clear_hooks(event: Optional[str] = None):
    """Clear hooks.

    Args:
        event: Optional event name (clears all if None)
    """
    global _HOOKS

    if event is None:
        _HOOKS = {key: [] for key in _HOOKS}
    elif event in _HOOKS:
        _HOOKS[event] = []


# Decorator for hooks
def hook(event: str):
    """Decorator to register a function as a hook handler.

    Args:
        event: Event name

    Usage:
        @hook("before_chat")
        def my_handler(message):
            print(f"Before chat: {message}")
    """
    def decorator(func: Callable) -> Callable:
        register_hook(event, func)
        return func
    return decorator


if __name__ == "__main__":
    # Test
    @hook("before_chat")
    def test_before_chat(message):
        print(f"Hook triggered: before_chat with message: {message}")

    trigger_hook("before_chat", "Hello, world!")