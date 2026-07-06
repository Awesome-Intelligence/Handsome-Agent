#!/usr/bin/env python3
# 🏃 Execution - 🛠️ ToolExec - 工具注册表

"""
Tool Registry Module

Central tool registry for managing metadata of all available tools.
Based on Hermes Agent registry.py implementation.

Features:
- Automatic tool discovery and registration
- Tool metadata management
- Tool availability checking (with caching)
- Dynamic schema override support

Import chain (circular-import safe):
    tools/registry.py  (no imports from model_tools or tool files)
           ^
    tools/*.py  (import from tools.registry at module level)
           ^
    model_tools.py  (imports tools.registry + all tool modules)
           ^
    run_agent.py, cli.py, batch_runner.py, etc.

Usage:
    from tools.registry import registry, ToolEntry, discover_builtin_tools
    
    # Get all registered tools
    tools = registry.get_all_tools()
    
    # Get tool definitions (for LLM)
    definitions = registry.get_definitions()
    
    # Execute tool
    result = await registry.execute("tool_name", parameters)
"""
import ast
import importlib
import json
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Any

from common.logging_manager import get_execution_logger

logger = get_execution_logger("ToolRegistry")


def _is_registry_register_call(node: ast.AST) -> bool:
    """检查节点是否是 registry.register(...) 调用"""
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    func = node.value.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "register"
        and isinstance(func.value, ast.Name)
        and func.value.id == "registry"
    )


def _module_registers_tools(module_path: Path) -> bool:
    """检查模块是否包含顶层 registry.register(...) 调用"""
    try:
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(module_path))
    except (OSError, SyntaxError):
        return False

    return any(_is_registry_register_call(stmt) for stmt in tree.body)


def discover_builtin_tools(tools_dir: Optional[Path] = None) -> List[str]:
    """导入内置自注册工具模块并返回其模块名列表"""
    tools_path = Path(tools_dir) if tools_dir is not None else Path(__file__).resolve().parent
    module_names = [
        f"tools.{path.stem}"
        for path in sorted(tools_path.glob("*.py"))
        if path.name not in {"__init__.py", "registry.py", "mcp_tool.py"}
        and _module_registers_tools(path)
    ]

    imported: List[str] = []
    for mod_name in module_names:
        try:
            importlib.import_module(mod_name)
            imported.append(mod_name)
        except Exception as e:
            logger.warning("无法导入工具模块 %s: %s", mod_name, e)
    return imported


class ToolEntry:
    """单个注册工具的元数据"""

    __slots__ = (
        "name", "toolset", "schema", "handler", "check_fn",
        "requires_env", "is_async", "description", "emoji",
        "max_result_size_chars", "dynamic_schema_overrides",
    )

    def __init__(
        self,
        name: str,
        toolset: str,
        schema: Dict[str, Any],
        handler: Callable,
        check_fn: Optional[Callable] = None,
        requires_env: Optional[List[str]] = None,
        is_async: bool = False,
        description: str = "",
        emoji: str = "🔧",
        max_result_size_chars: Optional[int] = None,
        dynamic_schema_overrides: Optional[Callable] = None,
    ):
        self.name = name
        self.toolset = toolset
        self.schema = schema
        self.handler = handler
        self.check_fn = check_fn
        self.requires_env = requires_env or []
        self.is_async = is_async
        self.description = description
        self.emoji = emoji
        self.max_result_size_chars = max_result_size_chars
        self.dynamic_schema_overrides = dynamic_schema_overrides

    def is_available(self) -> bool:
        """检查工具是否可用（考虑环境要求）"""
        if not self.check_fn:
            return True
        return _check_fn_cached(self.check_fn)

    def get_schema(self) -> Dict[str, Any]:
        """获取工具模式（包含动态覆盖）"""
        schema = self.schema.copy()
        if self.dynamic_schema_overrides:
            overrides = self.dynamic_schema_overrides()
            schema.update(overrides)
        return schema


# check_fn TTL 缓存
# 对于长期运行的 CLI 或网关进程，每次 get_definitions() 都调用 check_fn 是浪费
_CHECK_FN_TTL_SECONDS = 30.0
_check_fn_cache: Dict[Callable, tuple[float, bool]] = {}
_check_fn_cache_lock = threading.Lock()


def _check_fn_cached(fn: Callable) -> bool:
    """返回 bool(fn())，带 TTL 缓存"""
    now = time.monotonic()
    with _check_fn_cache_lock:
        cached = _check_fn_cache.get(fn)
        if cached is not None:
            ts, value = cached
            if now - ts < _CHECK_FN_TTL_SECONDS:
                return value
    try:
        value = bool(fn())
    except Exception:
        value = False
    with _check_fn_cache_lock:
        _check_fn_cache[fn] = (now, value)
    return value


def invalidate_check_fn_cache() -> None:
    """清除所有缓存的 check_fn 结果"""
    with _check_fn_cache_lock:
        _check_fn_cache.clear()


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}
        self._toolsets: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def register(
        self,
        name: str,
        toolset: str,
        schema: Dict[str, Any],
        handler: Callable,
        check_fn: Optional[Callable] = None,
        requires_env: Optional[List[str]] = None,
        is_async: bool = False,
        description: str = "",
        emoji: str = "🔧",
        max_result_size_chars: Optional[int] = None,
        dynamic_schema_overrides: Optional[Callable] = None,
    ) -> None:
        """注册一个工具"""
        entry = ToolEntry(
            name=name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            requires_env=requires_env,
            is_async=is_async,
            description=description,
            emoji=emoji,
            max_result_size_chars=max_result_size_chars,
            dynamic_schema_overrides=dynamic_schema_overrides,
        )

        with self._lock:
            self._tools[name] = entry
            if toolset not in self._toolsets:
                self._toolsets[toolset] = set()
            self._toolsets[toolset].add(name)

        logger.debug(f"工具已注册: {name} (toolset: {toolset})")

    def unregister(self, name: str) -> bool:
        """取消注册一个工具"""
        with self._lock:
            if name not in self._tools:
                return False
            entry = self._tools.pop(name)
            toolset = entry.toolset
            if toolset in self._toolsets:
                self._toolsets[toolset].discard(name)
            if not self._toolsets[toolset]:
                del self._toolsets[toolset]
            return True

    def get(self, name: str) -> Optional[ToolEntry]:
        """获取工具条目"""
        return self._tools.get(name)

    def get_all_tools(self) -> List[ToolEntry]:
        """获取所有已注册的工具"""
        return list(self._tools.values())

    def get_available_tools(self) -> List[ToolEntry]:
        """获取所有可用的工具"""
        return [t for t in self._tools.values() if t.is_available()]

    def get_by_toolset(self, toolset: str) -> List[ToolEntry]:
        """获取指定 toolset 的所有工具"""
        with self._lock:
            names = self._toolsets.get(toolset, set())
            return [self._tools[name] for name in names if name in self._tools]

    def get_definitions(
        self,
        toolsets: Optional[List[str]] = None,
        include_unavailable: bool = False,
    ) -> List[Dict[str, Any]]:
        """获取工具定义列表（用于 LLM）"""
        tools = self._tools.values()
        if toolsets:
            tool_names = set()
            for ts in toolsets:
                tool_names.update(self._toolsets.get(ts, set()))
            tools = [t for t in tools if t.name in tool_names]

        if not include_unavailable:
            tools = [t for t in tools if t.is_available()]

        definitions = []
        for tool in tools:
            schema = tool.get_schema()
            definitions.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or schema.get("description", ""),
                    "parameters": schema.get("parameters", {"type": "object", "properties": {}}),
                },
                "metadata": {
                    "toolset": tool.toolset,
                    "emoji": tool.emoji,
                    "is_async": tool.is_async,
                }
            })

        return definitions

    async def execute(self, name: str, parameters: Dict[str, Any]) -> Any:
        """执行工具（异步版本）"""
        entry = self.get(name)
        if not entry:
            raise ValueError(f"工具未找到: {name}")

        if not entry.is_available():
            raise RuntimeError(f"工具不可用: {name}")

        if entry.is_async:
            return await entry.handler(**parameters)
        else:
            return entry.handler(**parameters)

    def execute_sync(self, name: str, parameters: Dict[str, Any]) -> Any:
        """执行工具（同步版本）

        使用异步桥接来执行异步工具，防止"Event loop is closed"错误。
        同步工具直接执行，异步工具通过 _run_async 桥接执行。
        """
        entry = self.get(name)
        if not entry:
            raise ValueError(f"工具未找到: {name}")

        if not entry.is_available():
            raise RuntimeError(f"工具不可用: {name}")

        if entry.is_async:
            from .model_tools import _run_async
            return _run_async(entry.handler(**parameters))
        else:
            return entry.handler(**parameters)

    def list_toolsets(self) -> List[str]:
        """列出所有 toolset"""
        return list(self._toolsets.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        total = len(self._tools)
        available = len([t for t in self._tools.values() if t.is_available()])
        return {
            "total_tools": total,
            "available_tools": available,
            "toolsets": len(self._toolsets),
            "by_toolset": {
                ts: len(names) for ts, names in self._toolsets.items()
            },
        }


# 全局注册表实例
registry = ToolRegistry()


def check_file_requirements() -> bool:
    """文件工具需求检查"""
    try:
        from .terminal_tools import check_terminal_requirements
        return check_terminal_requirements()
    except Exception:
        return True
