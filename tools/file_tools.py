#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File operation tools for the agent.
"""

import os
import json
from typing import Optional, List
from . import ToolResult, register_tool, tool_registry


@register_tool(
    name="read_file",
    description="读取文件内容",
    parameters=[
        {"name": "path", "type": "string", "required": True, "description": "文件路径"},
        {"name": "limit", "type": "integer", "required": False, "description": "限制行数"}
    ]
)
def read_file(path: str, limit: Optional[int] = None) -> ToolResult:
    """读取文件内容"""
    try:
        if not os.path.exists(path):
            return ToolResult(success=False, output="", error=f"文件不存在: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if limit and limit > 0:
            lines = content.split('\n')
            content = '\n'.join(lines[:limit])
            if len(lines) > limit:
                content += f"\n... (共 {len(lines)} 行，显示前 {limit} 行)"
        
        return ToolResult(success=True, output=content)
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


@register_tool(
    name="write_file",
    description="写入文件内容",
    parameters=[
        {"name": "path", "type": "string", "required": True, "description": "文件路径"},
        {"name": "content", "type": "string", "required": True, "description": "文件内容"},
        {"name": "append", "type": "boolean", "required": False, "description": "是否追加模式"}
    ]
)
def write_file(path: str, content: str, append: bool = False) -> ToolResult:
    """写入文件内容"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
        
        mode = 'a' if append else 'w'
        with open(path, mode, encoding='utf-8') as f:
            f.write(content)
        
        action = "追加" if append else "写入"
        return ToolResult(success=True, output=f"成功{action}文件: {path}")
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


@register_tool(
    name="search_files",
    description="搜索文件内容",
    parameters=[
        {"name": "pattern", "type": "string", "required": True, "description": "搜索关键词"},
        {"name": "path", "type": "string", "required": False, "description": "搜索目录"},
        {"name": "file_glob", "type": "string", "required": False, "description": "文件过滤，如 *.py"},
        {"name": "limit", "type": "integer", "required": False, "description": "结果数量限制"}
    ]
)
def search_files(pattern: str, path: str = ".", file_glob: Optional[str] = None, limit: int = 20) -> ToolResult:
    """搜索文件内容"""
    try:
        import glob
        matches = []
        search_path = os.path.join(path, '**')
        pattern_lower = pattern.lower()
        
        if file_glob:
            pattern_path = os.path.join(search_path, file_glob)
        else:
            pattern_path = os.path.join(search_path, '*')
        
        for file_path in glob.glob(pattern_path, recursive=True):
            if not os.path.isfile(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if pattern_lower in content.lower():
                    lines = content.split('\n')
                    match_lines = [i+1 for i, line in enumerate(lines) if pattern_lower in line.lower()]
                    matches.append({
                        "path": file_path,
                        "line_count": len(lines),
                        "match_lines": match_lines[:5]
                    })
                    
                    if len(matches) >= limit:
                        break
            except Exception:
                continue
        
        if not matches:
            return ToolResult(success=True, output="未找到匹配结果", data={"matches": []})
        
        result_text = f"找到 {len(matches)} 个匹配:\n\n"
        for m in matches:
            result_text += f"📄 {m['path']} (行数: {m['line_count']})\n"
            if m['match_lines']:
                result_text += f"   匹配行: {', '.join(map(str, m['match_lines']))}\n"
            result_text += "\n"
        
        return ToolResult(success=True, output=result_text, data={"matches": matches})
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


@register_tool(
    name="list_directory",
    description="列出目录内容",
    parameters=[
        {"name": "path", "type": "string", "required": False, "description": "目录路径"},
        {"name": "all", "type": "boolean", "required": False, "description": "显示隐藏文件"}
    ]
)
def list_directory(path: str = ".", all: bool = False) -> ToolResult:
    """列出目录内容"""
    try:
        items = []
        for item in os.listdir(path):
            if not all and item.startswith('.'):
                continue
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                items.append(f"📁 {item}/")
            else:
                size = os.path.getsize(full_path)
                items.append(f"📄 {item} ({size} bytes)")
        
        if not items:
            return ToolResult(success=True, output="目录为空")
        
        return ToolResult(success=True, output="\n".join(items))
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


@register_tool(
    name="patch_file",
    description="修补文件内容（替换指定文本）",
    parameters=[
        {"name": "path", "type": "string", "required": True, "description": "文件路径"},
        {"name": "old_string", "type": "string", "required": True, "description": "要替换的文本"},
        {"name": "new_string", "type": "string", "required": True, "description": "替换后的文本"},
        {"name": "replace_all", "type": "boolean", "required": False, "description": "替换所有匹配"}
    ]
)
def patch_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> ToolResult:
    """修补文件内容"""
    try:
        if not os.path.exists(path):
            return ToolResult(success=False, output="", error=f"文件不存在: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_string not in content:
            return ToolResult(success=False, output="", error="未找到要替换的文本")
        
        if replace_all:
            new_content = content.replace(old_string, new_string)
            count = content.count(old_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
            count = 1
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return ToolResult(success=True, output=f"成功替换 {count} 处: {path}")
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))
