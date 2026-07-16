#!/usr/bin/env python3
"""File Tools Bridge - Registered to Agent-Z Decision Engine"""

import glob as glob_module
import json
import os
from pathlib import Path
from typing import Optional

from tools.registry import registry
from common.logging_manager import get_execution_logger

logger = get_execution_logger("FileToolsBridge")

DEFAULT_WORKSPACE_DIR = Path.home() / ".agent_z"


def _resolve_workspace_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return str(DEFAULT_WORKSPACE_DIR / path)


def _read_file(path: str, limit: Optional[int] = None) -> dict:
    try:
        resolved_path = _resolve_workspace_path(path)
        if not os.path.exists(resolved_path):
            return {"success": False, "output": "", "error": f"文件不存在: {resolved_path}"}

        with open(resolved_path, "r", encoding="utf-8") as f:
            content = f.read()

        if limit and limit > 0:
            lines = content.split("\n")
            content = "\n".join(lines[:limit])
            if len(lines) > limit:
                content += f"\n... (共 {len(lines)} 行，显示前 {limit} 行)"

        return {"success": True, "output": content, "error": None}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


def _write_file(path: str, content: str, append: bool = False) -> dict:
    try:
        resolved_path = _resolve_workspace_path(path)
        dirname = os.path.dirname(resolved_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        mode = "a" if append else "w"
        with open(resolved_path, mode, encoding="utf-8") as f:
            f.write(content)

        action = "追加" if append else "写入"
        return {"success": True, "output": f"成功{action}文件: {resolved_path}", "error": None}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


def _list_directory(path: str = ".", show_all: bool = False) -> dict:
    try:
        resolved_path = _resolve_workspace_path(path)
        items = []
        for item in os.listdir(resolved_path):
            if not show_all and item.startswith("."):
                continue
            full_path = os.path.join(resolved_path, item)
            if os.path.isdir(full_path):
                items.append(f"[DIR]  {item}/")
            else:
                size = os.path.getsize(full_path)
                items.append(f"[FILE] {item} ({size} bytes)")

        if not items:
            return {"success": True, "output": "目录为空", "error": None}

        return {"success": True, "output": "\n".join(items), "error": None}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


def _search_files(
    pattern: str, path: str = ".", file_glob: Optional[str] = None, limit: int = 20
) -> dict:
    try:
        resolved_path = _resolve_workspace_path(path)
        matches = []
        pattern_lower = pattern.lower()
        search_path = os.path.join(resolved_path, "**")
        glob_pattern = os.path.join(search_path, file_glob if file_glob else "*")

        for file_path in glob_module.glob(glob_pattern, recursive=True):
            if not os.path.isfile(file_path):
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if pattern_lower in content.lower():
                    lines = content.split("\n")
                    match_lines = [
                        i + 1 for i, line in enumerate(lines)
                        if pattern_lower in line.lower()
                    ]
                    matches.append({
                        "path": file_path,
                        "line_count": len(lines),
                        "match_lines": match_lines[:5],
                    })
                    if len(matches) >= limit:
                        break
            except Exception:
                continue

        if not matches:
            return {"success": True, "output": "未找到匹配结果", "error": None}

        result_text = f"找到 {len(matches)} 个匹配:\n\n"
        for m in matches:
            result_text += f"  {m['path']} (行数: {m['line_count']})\n"
            if m["match_lines"]:
                result_text += f"    匹配行: {', '.join(map(str, m['match_lines']))}\n"
            result_text += "\n"

        return {"success": True, "output": result_text, "error": None}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


READ_FILE_SCHEMA = {
    "name": "read_file",
    "description": "读取文件内容。适合查看文本文件、代码文件、配置文件、Markdown文档等。",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "文件路径（绝对路径或相对于当前目录的路径）",
            },
            "limit": {
                "type": "integer",
                "description": "限制读取行数（可选）",
            },
        },
        "required": ["path"],
    },
}

WRITE_FILE_SCHEMA = {
    "name": "write_file",
    "description": "写入文件内容",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "要写入的内容"},
            "append": {"type": "boolean", "description": "是否追加模式（可选）"},
        },
        "required": ["path", "content"],
    },
}

LIST_DIRECTORY_SCHEMA = {
    "name": "list_directory",
    "description": "列出目录内容",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "目录路径（默认为当前目录）"},
            "all": {"type": "boolean", "description": "是否显示隐藏文件"},
        },
    },
}

SEARCH_FILES_SCHEMA = {
    "name": "search_files",
    "description": "在文件中搜索指定内容",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "搜索关键词或正则表达式"},
            "path": {"type": "string", "description": "搜索起始目录（默认为当前目录）"},
            "file_glob": {
                "type": "string",
                "description": "文件名过滤模式，如 *.py、*.md",
            },
            "limit": {"type": "integer", "description": "结果数量限制（默认 20）"},
        },
        "required": ["pattern"],
    },
}


def _read_file_handler(args, **kw):
    return json.dumps(
        _read_file(path=args.get("path", "."), limit=args.get("limit")),
        ensure_ascii=False,
    )


def _write_file_handler(args, **kw):
    return json.dumps(
        _write_file(
            path=args.get("path", ""),
            content=args.get("content", ""),
            append=args.get("append", False),
        ),
        ensure_ascii=False,
    )


def _list_directory_handler(args, **kw):
    return json.dumps(
        _list_directory(
            path=args.get("path", "."),
            show_all=args.get("all", False),
        ),
        ensure_ascii=False,
    )


def _search_files_handler(args, **kw):
    return json.dumps(
        _search_files(
            pattern=args.get("pattern", ""),
            path=args.get("path", "."),
            file_glob=args.get("file_glob"),
            limit=args.get("limit", 20),
        ),
        ensure_ascii=False,
    )


registry.register(
    name="read_file",
    toolset="file_operations",
    schema=READ_FILE_SCHEMA,
    handler=_read_file_handler,
    emoji="📖",
)

registry.register(
    name="write_file",
    toolset="file_operations",
    schema=WRITE_FILE_SCHEMA,
    handler=_write_file_handler,
    emoji="✏️",
)

registry.register(
    name="list_directory",
    toolset="file_operations",
    schema=LIST_DIRECTORY_SCHEMA,
    handler=_list_directory_handler,
    emoji="📂",
)

registry.register(
    name="search_files",
    toolset="file_operations",
    schema=SEARCH_FILES_SCHEMA,
    handler=_search_files_handler,
    emoji="🔍",
)
