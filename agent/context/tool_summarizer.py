#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Summarizer Registry - 工具摘要注册表

提供可扩展的工具结果摘要机制，替代硬编码的 if-elif 链。
支持通过装饰器注册自定义摘要函数。

Usage:
    from agent.context.tool_summarizer import register, summarize_tool_result

    @register("read_file")
    def summarize_read_file(tool_name: str, args: Dict, content: str) -> str:
        path = args.get("path", "?")
        return f"[read_file] read {path}"

    # 使用注册表
    result = summarize_tool_result("read_file", args_json, content)
"""

from typing import Dict, Callable, Any, Optional, List
from functools import wraps
import re
import json


# ============================================================================
# Tool Summarizer Registry
# ============================================================================

class ToolSummarizerRegistry:
    """工具摘要注册表"""

    def __init__(self):
        self._summarizers: Dict[str, Callable] = {}
        self._fallback: Optional[Callable] = None

    def register(
        self,
        tool_names: List[str] = None,
        pattern: str = None
    ) -> Callable:
        """
        注册工具摘要函数。

        Args:
            tool_names: 要注册的工具名称列表
            pattern: 工具名称前缀模式（如 "browser_"）

        Returns:
            装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            if tool_names:
                for name in tool_names:
                    self._summarizers[name] = func
            elif pattern:
                # 前缀匹配会在 get_summarizer 中处理
                self._summarizers[f"__prefix:{pattern}"] = func
            else:
                self._fallback = func
            return func
        return decorator

    def get_summarizer(self, tool_name: str) -> Optional[Callable]:
        """获取工具的摘要函数"""
        # 精确匹配
        if tool_name in self._summarizers:
            return self._summarizers[tool_name]
        # 前缀匹配
        for key, func in self._summarizers.items():
            if key.startswith("__prefix:") and tool_name.startswith(key[9:]):
                return func
        return self._fallback


# 全局注册表实例
_registry = ToolSummarizerRegistry()


def register(tool_names: List[str] = None, pattern: str = None) -> Callable:
    """
    工具摘要函数装饰器。

    Usage:
        @register(["read_file", "write_file"])
        def summarize_file_tools(tool_name, args, content):
            ...
    """
    return _registry.register(tool_names, pattern)


def summarize_tool_result(tool_name: str, tool_args: str, tool_content: str) -> str:
    """
    根据工具名称生成摘要。

    Args:
        tool_name: 工具名称
        tool_args: 工具参数（JSON 字符串）
        tool_content: 工具返回内容

    Returns:
        摘要文本
    """
    # 解析参数
    try:
        args = json.loads(tool_args) if tool_args and tool_args.strip().startswith("{") else {}
    except (json.JSONDecodeError, TypeError):
        args = {}

    content = tool_content or ""
    content_len = len(content)
    line_count = content.count("\n") + 1 if content.strip() else 0

    # 获取摘要函数
    summarizer = _registry.get_summarizer(tool_name)
    if summarizer:
        return summarizer(tool_name, args, content, content_len, line_count)

    # 默认回退
    return _generic_summary(tool_name, args, content_len)


def _generic_summary(tool_name: str, args: Dict, content_len: int) -> str:
    """通用摘要生成"""
    first_arg = ""
    for k, v in list(args.items())[:2]:
        sv = str(v)[:30]
        first_arg += f" {k}={sv}"
    return f"[{tool_name}]{first_arg} ({content_len:,} chars)"


# ============================================================================
# Helper Functions (供摘要函数使用)
# ============================================================================

def _extract_exit_code(content: str) -> str:
    """从内容中提取 exit_code"""
    match = re.search(r'"exit_code"\s*:\s*(-?\d+)', content)
    return match.group(1) if match else "?"


def _extract_count(content: str, key: str = "total_count") -> str:
    """从 JSON 内容中提取计数"""
    match = re.search(rf'"{key}"\s*:\s*(\d+)', content)
    return match.group(1) if match else "?"


def _truncate(s: str, max_len: int) -> str:
    """截断字符串"""
    return s[:max_len] + "..." if len(s) > max_len else s


# ============================================================================
# Built-in Tool Summarizers (内置工具摘要)
# ============================================================================

@register(["read_file"])
def _summarize_read_file(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    path = args.get("path", "?")
    offset = args.get("offset", 1)
    limit = args.get("limit", "")
    location = f"line {offset}" + (f"-{offset + limit}" if limit else "")
    return f"[read_file] read {path} from {location} ({content_len:,} chars)"


@register(["write_file"])
def _summarize_write_file(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    path = args.get("path", "?")
    content_param = args.get("content", "")
    lines = content_param.count("\n") + 1 if content_param else "?"
    return f"[write_file] wrote {path} ({lines} lines)"


@register(["patch"])
def _summarize_patch(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    path = args.get("path", "?")
    mode = args.get("mode", "replace")
    new_str = args.get("new_string", "")
    return f"[patch] {mode} in {path} - {'updated' if new_str else 'modified'}"


@register(["list_directory"])
def _summarize_list_directory(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    path = args.get("path", ".")
    all_files = args.get("all", False)
    entry_count = content.count("\n") if content.strip() else "?"
    return f"[list_directory] listing {path} ({entry_count} entries{' incl. hidden' if all_files else ''})"


@register(["create_directory"])
def _summarize_create_directory(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    path = args.get("path", "?")
    return f"[create_directory] created {path}"


@register(["delete_file"])
def _summarize_delete_file(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    path = args.get("path", "?")
    return f"[delete_file] deleted {path}"


@register(["search_files"])
def _summarize_search_files(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    pattern = args.get("pattern", "?")
    path = args.get("path", ".")
    target = args.get("target", "content")
    count = _extract_count(content)
    return f"[search_files] {target} '{pattern}' in {path} -> {count} matches"


@register(["grep"])
def _summarize_grep(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    pattern = args.get("pattern", "?")
    path = args.get("path", ".")
    count = _extract_count(content)
    return f"[grep] '{pattern}' in {path} -> {count} matches"


@register(["terminal"])
def _summarize_terminal(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    cmd = args.get("command", "")
    cmd = _truncate(cmd, 60)
    exit_code = _extract_exit_code(content)
    return f"[terminal] `{cmd}` -> exit {exit_code}, {line_count} lines"


@register(["bash"])
def _summarize_bash(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    cmd = args.get("command", "")
    cmd = _truncate(cmd, 60)
    exit_code = _extract_exit_code(content)
    return f"[bash] `{cmd}` -> exit {exit_code}, {line_count} lines"


@register(["execute_code"])
def _summarize_execute_code(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    language = args.get("language", "?")
    code = args.get("code", "")
    code_preview = _truncate(code, 40).replace("\n", " ")
    return f"[execute_code] {language}: `{code_preview}` ({line_count} lines output)"


@register(["web_search"])
def _summarize_web_search(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    query = args.get("query", "?")
    limit = args.get("limit", 5)
    return f"[web_search] query='{query}' (limit={limit}, {content_len:,} chars)"


@register(["web_fetch"])
def _summarize_web_fetch(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    url = args.get("url", args.get("urls", ["?"]))
    if isinstance(url, list):
        url = url[0] if url else "?"
    return f"[web_fetch] {url} ({content_len:,} chars)"


@register(["web_extract"])
def _summarize_web_extract(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    urls = args.get("urls", [])
    url_count = len(urls) if isinstance(urls, list) else 1
    url_desc = urls[0] if isinstance(urls, list) and urls else str(urls)[:50]
    more = f" (+{url_count-1} more)" if url_count > 1 else ""
    return f"[web_extract] {url_desc}{more} ({content_len:,} chars)"


# Browser tools - 前缀匹配
@register(pattern="browser_")
def _summarize_browser(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    action = tool_name.replace("browser_", "")
    url = args.get("url", "")
    ref = args.get("ref", "")

    if tool_name == "browser_snapshot":
        return f"[browser_snapshot] {url}" + (f" ({content_len:,} chars)" if content_len > 0 else "")
    elif tool_name == "browser_vision":
        question = _truncate(args.get("question", ""), 50)
        return f"[browser_vision] '{question}'" + (f" ({content_len:,} chars)" if content_len > 0 else "")
    elif tool_name == "browser_console":
        return f"[browser_console] ({content_len:,} chars)"
    elif tool_name == "browser_get_images":
        return f"[browser_get_images] ({content_len:,} chars)"
    else:
        detail = f" {url}" if url else (f" ref={ref[:20]}" if ref else "")
        return f"[browser_{action}]{detail}"


@register(["analyze_image"])
def _summarize_analyze_image(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    question = _truncate(args.get("question", ""), 50)
    return f"[analyze_image] '{question}' ({content_len:,} chars)"


@register(["extract_text"])
def _summarize_extract_text(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    return f"[extract_text] ({content_len:,} chars extracted)"


@register(["compare_images"])
def _summarize_compare_images(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    return f"[compare_images] ({content_len:,} chars)"


@register(["image_generate"])
def _summarize_image_generate(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    prompt = _truncate(args.get("prompt", ""), 50)
    model = args.get("model", "?")
    return f"[image_generate] model={model}: '{prompt}'" + (f" ({content_len:,} chars)" if content_len > 0 else "")


@register(["memory"])
def _summarize_memory(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    action = args.get("action", "?")
    target = args.get("target", "?")
    count = _extract_count(content, "entry_count")
    return f"[memory] {action} on {target} ({count} entries)"


@register(["session_search"])
def _summarize_session_search(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    query = args.get("query", "?")
    limit = args.get("limit", 5)
    count = _extract_count(content, "result_count")
    return f"[session_search] '{query}' -> {count} results (limit={limit})"


@register(["todo"])
def _summarize_todo(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    action = args.get("action", "?")
    return f"[todo] {action}"


@register(["todo_create"])
def _summarize_todo_create(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    title = _truncate(args.get("title", ""), 40)
    return f"[todo_create] '{title}'"


@register(["todo_add"])
def _summarize_todo_add(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    task = _truncate(args.get("task", ""), 40)
    return f"[todo_add] '{task}'"


@register(["todo_complete"])
def _summarize_todo_complete(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    task_id = args.get("task_id", "?")
    return f"[todo_complete] task={task_id}"


@register(["skill_view", "skills_list", "skill_manage", "skill_create"])
def _summarize_skill(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    name = args.get("name", "?")
    action = args.get("action", tool_name.replace("skill_", ""))
    return f"[{tool_name}] name={name} ({action})"


@register(["text_to_speech"])
def _summarize_text_to_speech(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    text = _truncate(args.get("text", ""), 30)
    voice = args.get("voice", "?")
    return f"[text_to_speech] voice={voice}: '{text}'" + (f" ({content_len:,} chars)" if content_len > 0 else "")


@register(["clarify"])
def _summarize_clarify(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    return "[clarify] asked user a question"


@register(["cronjob"])
def _summarize_cronjob(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    action = args.get("action", "?")
    return f"[cronjob] {action}"


@register(["checkpoint"])
def _summarize_checkpoint(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    action = args.get("action", "?")
    name = args.get("name", "?")
    return f"[checkpoint] {action}: {name}"


@register(["process"])
def _summarize_process(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    action = args.get("action", "?")
    sid = args.get("session_id", "?")
    return f"[process] {action} session={sid}"


@register(["delegate_task"])
def _summarize_delegate_task(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    goal = _truncate(args.get("goal", ""), 50)
    return f"[delegate_task] '{goal}' ({content_len:,} chars result)"


@register(["checkpoint_restore"])
def _summarize_checkpoint_restore(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    checkpoint_id = args.get("checkpoint_id", "?")
    return f"[checkpoint_restore] id={checkpoint_id}"


@register(["checkpoint_list"])
def _summarize_checkpoint_list(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    return f"[checkpoint_list] ({content_len:,} chars)"


# Home automation - 前缀匹配
@register(pattern="ha_")
def _summarize_home_automation(tool_name: str, args: Dict, content: str, content_len: int, line_count: int) -> str:
    action = tool_name.replace("ha_", "")
    entity = args.get("entity_id", "?")
    return f"[{tool_name}] entity={entity}"


__all__ = [
    'register',
    'summarize_tool_result',
    'ToolSummarizerRegistry',
]
