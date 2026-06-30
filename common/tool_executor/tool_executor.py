# -*- coding: utf-8 -*-
# 🔧 System - Tool Executor - 核心实现

"""
ToolExecutor - 统一工具执行器

功能：
1. 单个工具执行
2. 批量工具执行（顺序/并发）
3. Rail 拦截支持
4. 统一错误处理
5. 事件发射
"""

import asyncio
import time
import inspect
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, Union

from common.logging_manager import get_task_logger
from common.tool_executor.types import (
    ToolInvokeResult,
    ToolInvokeRequest,
    ToolInvokeError,
    ExecuteMode,
    ExecuteOptions,
)

if TYPE_CHECKING:
    from agent.rails import Rail, RailResult


def _default_error_classifier(error: Exception) -> ToolInvokeError:
    """
    默认错误分类器

    可根据需要替换为更复杂的实现。
    """
    error_type = type(error).__name__
    message = str(error)

    # 常见的可重试错误
    retryable_keywords = [
        "timeout", "timed out", "connection",
        "network", "econnreset", "etimedout",
    ]

    is_retryable = any(kw in message.lower() for kw in retryable_keywords)

    # 常见的不可重试错误
    non_retryable_keywords = [
        "not found", "does not exist", "permission denied",
        "access denied", "invalid", "malformed",
    ]

    if any(kw in message.lower() for kw in non_retryable_keywords):
        is_retryable = False

    return ToolInvokeError(
        error_type=error_type,
        message=message,
        is_retryable=is_retryable,
        details={"exception_type": error_type},
    )


class ToolExecutor:
    """
    统一工具执行器

    设计说明：
    - Rail 拦截统一由调用方（如 AgentLoop）负责处理
    - rails 参数保留用于未来直接模式，当前通过调用方使用 RailRegistry
    - 核心方法 execute() 只负责工具执行逻辑

    使用示例：
    ```python
    executor = ToolExecutor(
        tool_registry={"read_file": read_file_handler},
        stream_emitter=emitter,
    )

    # 单个执行（Rail 拦截由调用方负责）
    result = await executor.execute("read_file", {"path": "test.py"})

    # 批量执行（顺序）
    results = await executor.execute_batch([
        ("read_file", {"path": "a.py"}),
        ("write_file", {"path": "b.py", "content": "..."}),
    ])

    # 批量执行（并发，最多 5 个）
    executor_concurrent = ToolExecutor(
        tool_registry=handlers,
        max_concurrent=5,
    )
    results = await executor_concurrent.execute_batch(tool_calls)
    ```
    """

    def __init__(
        self,
        tool_registry: Dict[str, Callable],
        rails: Optional[List["Rail"]] = None,
        stream_emitter: Optional[Any] = None,
        error_classifier: Optional[Callable[[Exception], ToolInvokeError]] = None,
        max_concurrent: int = 1,
        session_id: Optional[str] = None,
    ):
        """
        初始化工具执行器

        注意：rails 参数当前保留，但 Rail 拦截实际由调用方使用
        RailRegistry.trigger_*_tool_call() 方法处理。

        Args:
            tool_registry: 工具名称到处理函数的映射
            rails: Rail 拦截器列表（当前由调用方通过 RailRegistry 处理）
            stream_emitter: 流式事件发射器
            error_classifier: 自定义错误分类器
            max_concurrent: 最大并发数（1=顺序执行）
            session_id: 会话 ID（用于日志）
        """
        self.tool_registry = tool_registry
        self.rails = rails or []
        self.stream_emitter = stream_emitter
        self.error_classifier = error_classifier or _default_error_classifier
        self.max_concurrent = max_concurrent
        self.session_id = session_id or "default"

        # 初始化日志器
        self.logger = get_task_logger("ToolExecutor", sublayer="execution")

        # 线程池（用于并发执行）
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        if self.max_concurrent > 1:
            self._thread_pool = ThreadPoolExecutor(max_workers=self.max_concurrent)

    def __del__(self):
        """清理资源"""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=False)

    # === 公共接口 ===

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Any] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> ToolInvokeResult:
        """
        执行单个工具

        注意：
        - Rail 拦截统一由调用方（如 AgentLoop）负责处理
        - 此方法只负责工具执行逻辑，不处理 Rail
        - 如需 Rail 拦截，请在调用此方法前/后由调用方处理

        执行流程：
        1. 检查工具是否存在
        2. 执行工具（支持异步/同步）
        3. 发射事件
        4. 返回结果

        Args:
            tool_name: 工具名称
            parameters: 工具参数
            context: 传递给 Rail 的上下文（当前未使用，为未来扩展保留）
            extra_context: 额外的上下文参数，会作为关键字参数传递给工具处理器
                          例如：{"parent_agent": agent_instance}

        Returns:
            ToolInvokeResult
        """
        start_time = time.time()

        # 1. 检查工具是否存在
        if tool_name not in self.tool_registry:
            self.logger.warning(f"工具不存在: {tool_name}")
            self._emit_tool_start(tool_name, parameters)
            result = ToolInvokeResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' not found",
                error_type="ToolNotFoundError",
                execution_time=time.time() - start_time,
            )
            self._emit_tool_end(tool_name, result)
            return result

        # 2. 执行工具
        result = await self._do_execute(tool_name, parameters, extra_context)
        result.execution_time = time.time() - start_time

        # 3. 发射事件
        self._emit_tool_start(tool_name, parameters)
        self._emit_tool_end(tool_name, result)

        return result

    async def execute_batch(
        self,
        tool_calls: List[Union[ToolInvokeRequest, tuple, Dict]],
        context: Optional[Any] = None,
    ) -> List[ToolInvokeResult]:
        """
        批量执行工具

        根据 max_concurrent 决定顺序或并发执行：
        - max_concurrent=1: 顺序执行
        - max_concurrent>1: 使用 ThreadPoolExecutor 并发执行

        Args:
            tool_calls: 工具调用列表，支持多种格式：
                - ToolInvokeRequest 对象
                - tuple: (tool_name, arguments)
                - dict: {"tool_name": ..., "arguments": ...}
            context: 传递给 Rail 的上下文

        Returns:
            执行结果列表（顺序与输入一致）
        """
        # 标准化输入
        requests = self._normalize_tool_calls(tool_calls)

        if self.max_concurrent <= 1:
            # 顺序执行
            return await self._execute_sequential(requests, context)
        else:
            # 并发执行
            return await self._execute_concurrent(requests, context)

    async def execute_single(
        self,
        request: ToolInvokeRequest,
        context: Optional[Any] = None,
    ) -> ToolInvokeResult:
        """
        执行单个请求（ToolInvokeRequest 格式）

        Args:
            request: 工具调用请求
            context: 传递给 Rail 的上下文

        Returns:
            ToolInvokeResult
        """
        return await self.execute(request.tool_name, request.arguments, context)

    # === 批量执行实现 ===

    async def _execute_sequential(
        self,
        requests: List[ToolInvokeRequest],
        context: Optional[Any],
    ) -> List[ToolInvokeResult]:
        """顺序执行"""
        results = []
        for request in requests:
            result = await self.execute(request.tool_name, request.arguments, context)
            results.append(result)
        return results

    async def _execute_concurrent(
        self,
        requests: List[ToolInvokeRequest],
        context: Optional[Any],
    ) -> List[ToolInvokeResult]:
        """并发执行"""
        if not self._thread_pool:
            return await self._execute_sequential(requests, context)

        # 使用信号量限制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _execute_with_semaphore(request: ToolInvokeRequest) -> ToolInvokeResult:
            async with semaphore:
                return await self.execute(request.tool_name, request.arguments, context)

        tasks = [_execute_with_semaphore(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=False)

    def _normalize_tool_calls(
        self,
        tool_calls: List[Union[ToolInvokeRequest, tuple, Dict]],
    ) -> List[ToolInvokeRequest]:
        """标准化工具调用列表"""
        requests = []
        for call in tool_calls:
            if isinstance(call, ToolInvokeRequest):
                requests.append(call)
            elif isinstance(call, tuple) and len(call) >= 2:
                requests.append(ToolInvokeRequest(
                    tool_name=call[0],
                    arguments=call[1] if len(call) > 1 else {},
                ))
            elif isinstance(call, dict):
                requests.append(ToolInvokeRequest(
                    tool_name=call.get("tool_name", call.get("name", "")),
                    arguments=call.get("arguments", call.get("args", {})),
                ))
        return requests

    # === Rail 拦截（预留接口，由调用方负责） ===

    async def _trigger_before_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
    ) -> Optional["RailResult"]:
        """触发 before_tool_call Rails

        注意：此方法是预留接口，实际 Rail 拦截由调用方（如 AgentLoop）负责。
        调用方应使用 RailRegistry.trigger_before_tool_call() 进行拦截。
        此方法存在是为了保持接口兼容性，未来可能用于直接模式。
        """
        for rail in self.rails:
            if hasattr(rail, "before_tool_call"):
                try:
                    result = await rail.before_tool_call(tool_name, args)
                    if result and hasattr(result, "allowed") and not result.allowed:
                        return result
                except Exception as e:
                    self.logger.error(f"Rail before_tool_call 错误: {e}")
        return None

    async def _trigger_after_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: ToolInvokeResult,
    ) -> None:
        """触发 after_tool_call Rails

        注意：此方法是预留接口，实际 Rail 拦截由调用方（如 AgentLoop）负责。
        调用方应使用 RailRegistry.trigger_after_tool_call() 进行拦截。
        此方法存在是为了保持接口兼容性，未来可能用于直接模式。
        """
        for rail in self.rails:
            if hasattr(rail, "after_tool_call"):
                try:
                    await rail.after_tool_call(tool_name, args, result.output)
                except Exception as e:
                    self.logger.error(f"Rail after_tool_call 错误: {e}")

    # === 核心执行逻辑 ===

    async def _do_execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> ToolInvokeResult:
        """实际执行工具（不带 Rail 拦截）"""
        handler = self.tool_registry[tool_name]
        start_time = time.time()

        try:
            # 参考 Hermes：拦截 todo 工具，直接传递 agent 的 _todo_store
            if tool_name == "todo":
                from tools.todo_tool import todo_tool as _todo_tool
                parent_agent = extra_context.get("parent_agent") if extra_context else None
                store = parent_agent._todo_store if parent_agent else None
                result = _todo_tool(
                    todos=parameters.get("todos"),
                    merge=parameters.get("merge", False),
                    store=store,
                    persist=parameters.get("persist", False),
                )
            else:
                # 调用工具，支持传递额外上下文参数
                if extra_context:
                    result = handler(parameters, **extra_context)
                else:
                    result = handler(parameters)

            # 处理异步结果
            if inspect.iscoroutine(result):
                result = await result

            # 处理字符串结果
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    result = {"result": result}

            # 成功结果
            return ToolInvokeResult(
                tool_name=tool_name,
                success=True,
                output=result,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            # 错误处理
            error_info = self._classify_error(e)
            self.logger.error(
                f"工具执行错误 - tool={tool_name} "
                f"type={error_info.error_type} "
                f"msg={error_info.message[:100]}"
            )

            return ToolInvokeResult(
                tool_name=tool_name,
                success=False,
                error=error_info.message,
                error_type=error_info.error_type,
                is_retryable=error_info.is_retryable,
                execution_time=time.time() - start_time,
            )

    def _classify_error(self, error: Exception) -> ToolInvokeError:
        """对错误进行分类"""
        return self.error_classifier(error)

    # === 事件发射 ===

    def _emit_tool_start(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> None:
        """发射工具开始事件"""
        if self.stream_emitter and hasattr(self.stream_emitter, "emit_tool_start"):
            self.stream_emitter.emit_tool_start(tool_name, parameters)

    def _emit_tool_end(
        self,
        tool_name: str,
        result: ToolInvokeResult,
    ) -> None:
        """发射工具结束事件"""
        if self.stream_emitter and hasattr(self.stream_emitter, "emit_tool_end"):
            # 格式化结果
            if result.is_blocked:
                output = {"error": result.block_reason}
            elif not result.success:
                output = {"error": result.error}
            else:
                output = result.output if isinstance(result.output, dict) else {"result": result.output}

            self.stream_emitter.emit_tool_end(tool_name, output)
