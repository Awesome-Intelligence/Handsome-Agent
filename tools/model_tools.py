#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model Tools Module - Inspired by Hermes Agent

This module provides utilities for working with tools in the agent system.
Note: The ToolRegistry has been moved to tools/registry.py.
This module now delegates to the unified registry.

Key features:
- Async bridging (_run_async, _get_tool_loop, _get_worker_loop) to prevent
  "Event loop is closed" errors with cached httpx/AsyncOpenAI clients
- ToolDispatcher for executing tools
- register_tool decorator for registering tools
"""

import asyncio
import inspect
import logging
import threading
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json

from .registry import registry, ToolEntry

logger = logging.getLogger(__name__)


# =============================================================================
# Async Bridging  (single source of truth -- used by registry.execute too)
# =============================================================================

_tool_loop = None
_tool_loop_lock = threading.Lock()
_worker_thread_local = threading.local()


def _get_tool_loop():
    """Return a long-lived event loop for running async tool handlers.

    Using a persistent loop (instead of asyncio.run() which creates and
    *closes* a fresh loop every time) prevents "Event loop is closed"
    errors that occur when cached httpx/AsyncOpenAI clients attempt to
    close their transport on a dead loop during garbage collection.
    """
    global _tool_loop
    with _tool_loop_lock:
        if _tool_loop is None or _tool_loop.is_closed():
            _tool_loop = asyncio.new_event_loop()
        return _tool_loop


def _get_worker_loop():
    """Return a persistent event loop for the current worker thread.

    Each worker thread (e.g., delegate_task's ThreadPoolExecutor threads)
    gets its own long-lived loop stored in thread-local storage.  This
    prevents the "Event loop is closed" errors that occurred when
    asyncio.run() was used per-call: asyncio.run() creates a loop, runs
    the coroutine, then *closes* the loop — but cached httpx/AsyncOpenAI
    clients remain bound to that now-dead loop and raise RuntimeError
    during garbage collection or subsequent use.

    By keeping the loop alive for the thread's lifetime, cached clients
    stay valid and their cleanup runs on a live loop.
    """
    loop = getattr(_worker_thread_local, 'loop', None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _worker_thread_local.loop = loop
    return loop


def _run_async(coro):
    """Run an async coroutine from a sync context.

    If the current thread already has a running event loop (e.g., inside
    the gateway's async stack), we spin up a disposable thread so
    asyncio.run() can create its own loop without conflicting.

    For the common CLI path (no running loop), we use a persistent event
    loop so that cached async clients (httpx / AsyncOpenAI) remain bound
    to a live loop and don't trigger "Event loop is closed" on GC.

    When called from a worker thread (parallel tool execution), we use a
    per-thread persistent loop to avoid both contention with the main
    thread's shared loop AND the "Event loop is closed" errors caused by
    asyncio.run()'s create-and-destroy lifecycle.

    This is the single source of truth for sync->async bridging in tool
    handlers. Each handler is self-protecting via this function.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        worker_loop: Optional[asyncio.AbstractEventLoop] = None
        loop_ready = threading.Event()

        def _run_in_worker():
            nonlocal worker_loop
            worker_loop = asyncio.new_event_loop()
            loop_ready.set()
            try:
                asyncio.set_event_loop(worker_loop)
                return worker_loop.run_until_complete(coro)
            finally:
                try:
                    pending = asyncio.all_tasks(worker_loop)
                    for t in pending:
                        t.cancel()
                    if pending:
                        worker_loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass
                worker_loop.close()

        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(_run_in_worker)
        try:
            return future.result(timeout=300)
        except concurrent.futures.TimeoutError:
            if loop_ready.wait(timeout=1.0) and worker_loop is not None:
                try:
                    for t in asyncio.all_tasks(worker_loop):
                        worker_loop.call_soon_threadsafe(t.cancel)
                except RuntimeError:
                    pass
            raise
        finally:
            pool.shutdown(wait=False)

    if threading.current_thread() is not threading.main_thread():
        worker_loop = _get_worker_loop()
        return worker_loop.run_until_complete(coro)

    tool_loop = _get_tool_loop()
    return tool_loop.run_until_complete(coro)


class ToolDispatcher:
    """
    Dispatches tool execution requests.
    
    Handles:
    - Parameter validation
    - Permission checks
    - Error handling
    - Result formatting
    """
    
    def __init__(self, tool_registry=None):
        self.registry = tool_registry if tool_registry is not None else registry
    
    async def dispatch(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Dispatch a tool call.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters
        
        Returns:
            Dictionary with 'success', 'output', and optionally 'error'
        """
        tool_info = self.registry.get(tool_name)
        
        if not tool_info:
            return {
                "success": False,
                "error": f"Tool not found: {tool_name}"
            }
        
        if not tool_info.is_available():
            return {
                "success": False,
                "error": f"Tool not available: {tool_name}"
            }
        
        validation = self._validate_parameters(tool_info, kwargs)
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["error"]
            }
        
        try:
            if tool_info.is_async:
                result = await tool_info.handler(**kwargs)
            else:
                result = tool_info.handler(**kwargs)
            
            return {
                "success": True,
                "output": result
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_parameters(self, tool_info: ToolEntry, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate tool parameters.
        
        Returns:
            Dict with 'valid' (bool) and 'error' (str if invalid)
        """
        schema = tool_info.get_schema()
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        for param_name, prop in properties.items():
            if param_name in required and param_name not in kwargs:
                return {
                    "valid": False,
                    "error": f"Missing required parameter: {param_name}"
                }
            
            if param_name in kwargs:
                expected_type = prop.get("type", "string")
                value = kwargs[param_name]
                
                if expected_type == "integer" and not isinstance(value, int):
                    return {
                        "valid": False,
                        "error": f"Parameter {param_name} must be an integer"
                    }
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return {
                        "valid": False,
                        "error": f"Parameter {param_name} must be a boolean"
                    }
        
        return {"valid": True, "error": None}


# ─────────────────────────────────────────────────────────────────────────────
# 统一工具注册表
# ─────────────────────────────────────────────────────────────────────────────

# 统一使用 registry.py 中的 registry
# 已在文件顶部导入


def register_tool(name: str, description: str, parameters: List[Dict[str, Any]],
                  requires_permission: bool = False, category: str = "general"):
    """
    装饰器：注册工具到统一的 ToolRegistry
    
    Example:
        @register_tool(
            name="file_write",
            description="Write content to a file",
            parameters=[
                {"name": "path", "type": "string", "description": "File path", "required": True},
                {"name": "content", "type": "string", "description": "Content to write", "required": True}
            ],
            category="files"
        )
        def file_write(path: str, content: str) -> str:
            # implementation
    """
    def decorator(func):
        props = {}
        required = []
        for param in parameters:
            param_name = param.get("name")
            if param_name:
                props[param_name] = {
                    "type": param.get("type", "string"),
                    "description": param.get("description", ""),
                }
                if param.get("required", False):
                    required.append(param_name)
        
        schema = {
            "type": "object",
            "properties": props,
            "required": required,
            "description": description,
        }
        
        registry.register(
            name=name,
            toolset=category,
            schema=schema,
            handler=func,
            description=description,
        )
        return func
    return decorator


# 为了向后兼容，提供 module-level 的 tool_registry
class _ToolRegistryProxy:
    """tool_registry 的兼容层"""
    def __getattr__(self, name):
        return getattr(registry, name)

    def __len__(self):
        return len(registry.get_all_tools())

    def __iter__(self):
        return iter(registry.get_all_tools())


tool_registry = _ToolRegistryProxy()
