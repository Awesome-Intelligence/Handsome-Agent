#!/usr/bin/env python3
"""
# 🏃 Execution - 🛠️ ToolExec - Application Launcher
# 应用程序启动工具 - 基于 Hermes 设计优化
#
# 优化说明：
# - 移除冗余的独立工具（open_calculator, open_notepad, open_cmd）
# - 统一使用 launch_app 处理所有应用启动
# - 保留 open_folder/open_file 因其有特殊参数处理逻辑
"""

import json
import platform
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional

from tools.registry import registry
from common.logging_manager import get_execution_logger

logger = get_execution_logger("AppLauncher")


# 常见 Windows 应用程序（可被 launch_app 直接使用）
COMMON_APPS = {
    "calculator": ["calc.exe"],
    "notepad": ["notepad.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "explorer": ["explorer.exe"],
    "taskmgr": ["taskmgr.exe"],
    "control": ["control.exe"],
    "paint": ["mspaint.exe"],
    "wordpad": ["write.exe"],
    "word": ["winword.exe"],
    "excel": ["excel.exe"],
    "chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
}


def find_app_path(app_name: str) -> Optional[str]:
    """查找应用程序路径"""
    app_name_lower = app_name.lower()
    
    # 先检查是否在常见应用列表中
    if app_name_lower in COMMON_APPS:
        for exe_name in COMMON_APPS[app_name_lower]:
            try:
                # 尝试直接启动（Windows会在PATH中查找）
                return exe_name
            except Exception:
                    continue
    
    # 直接返回用户输入的名称
    return app_name


def launch_app(
    app_name: str,
    args: Optional[list] = None,
) -> str:
    """启动应用程序"""
    try:
        app_path = find_app_path(app_name)
        
        if not app_path:
            return json.dumps({
                "success": False,
                "error": f"找不到应用程序: {app_name}"
            }, ensure_ascii=False)
        
        cmd = [app_path]
        if args:
            cmd.extend(args)
        
        # 启动应用程序，不等待它完成
        subprocess.Popen(cmd, shell=False)
        
        return json.dumps({
            "success": True,
            "message": f"已启动应用程序: {app_name}",
            "app": app_name,
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"启动应用程序失败: {e}")
        return json.dumps({
            "success": False,
            "error": f"启动应用程序失败: {str(e)}"
        }, ensure_ascii=False)


def check_app_launcher_requirements() -> bool:
    """检查应用程序启动工具的需求"""
    return True


def open_folder(path: Optional[str] = None) -> str:
    """
    # 🏃 Execution - 🛠️ ToolExec - 打开文件夹
    #
    Args:
        path: 文件夹路径，默认为当前目录

    Returns:
        JSON 格式的结果字符串
    """
    try:
        if not path:
            path = os.getcwd()

        folder = Path(path)
        if not folder.exists():
            return json.dumps({
                "success": False,
                "error": f"文件夹不存在: {path}"
            }, ensure_ascii=False)

        if not folder.is_dir():
            return json.dumps({
                "success": False,
                "error": f"路径不是文件夹: {path}"
            }, ensure_ascii=False)

        subprocess.Popen(["explorer", str(folder)], shell=False)

        return json.dumps({
            "success": True,
            "message": f"已打开文件夹: {folder}",
            "path": str(folder),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"打开文件夹失败: {e}")
        return json.dumps({
            "success": False,
            "error": f"打开文件夹失败: {str(e)}"
        }, ensure_ascii=False)


def open_file(path: str) -> str:
    """
    # 🏃 Execution - 🛠️ ToolExec - 用默认程序打开文件
    #
    Args:
        path: 文件路径

    Returns:
        JSON 格式的结果字符串
    """
    try:
        file_path = Path(path).resolve()

        if not file_path.exists():
            return json.dumps({
                "success": False,
                "error": f"文件不存在: {path}"
            }, ensure_ascii=False)

        if file_path.is_dir():
            return json.dumps({
                "success": False,
                "error": f"路径是文件夹而非文件: {path}，请使用 open_folder 工具"
            }, ensure_ascii=False)

        system = platform.system()
        if system == "Windows":
            os.startfile(str(file_path))
        elif system == "Darwin":
            subprocess.Popen(["open", str(file_path)])
        else:
            subprocess.Popen(["xdg-open", str(file_path)])

        return json.dumps({
            "success": True,
            "message": f"已用默认程序打开文件: {file_path.name}",
            "path": str(file_path),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"打开文件失败: {e}")
        return json.dumps({
            "success": False,
            "error": f"打开文件失败: {str(e)}"
        }, ensure_ascii=False)


# =============================================================================
# 工具定义 (Tool Schema Definitions)
# =============================================================================

LAUNCH_APP_SCHEMA = {
    "name": "launch_app",
    "description": (
        "启动 Windows 应用程序。支持以下常见应用：\n"
        "- calculator, notepad, cmd, powershell, explorer, taskmgr, control\n"
        "- paint, wordpad\n"
        "- word, excel\n"
        "- chrome, edge, firefox\n"
        "- 或直接输入可执行文件名（如 calc.exe）"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": (
                    "应用程序名称或可执行文件名\n"
                    "支持：calculator, notepad, cmd, powershell, explorer, taskmgr, "
                    "control, paint, wordpad, word, excel, chrome, edge, firefox\n"
                    "或直接输入：calc.exe, notepad.exe 等"
                ),
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "可选的启动参数",
            },
        },
        "required": ["app_name"],
    },
}


OPEN_FOLDER_SCHEMA = {
    "name": "open_folder",
    "description": "打开指定的文件夹。如果未指定路径，则打开当前目录。",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要打开的文件夹路径（默认为当前目录）",
            },
        },
    },
}


OPEN_FILE_SCHEMA = {
    "name": "open_file",
    "description": (
        "用系统默认程序打开文件（如 .md 用记事本/Typora、.pdf 用浏览器、.py 用 IDE 等）。"
        "适合用户想'打开某个文件看看'的场景。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要打开的文件路径（绝对路径或相对于当前目录的路径）",
            },
        },
        "required": ["path"],
    },
}


# =============================================================================
# 工具注册 (Tool Registrations)
# =============================================================================

registry.register(
    name="launch_app",
    toolset="app_launcher",
    schema=LAUNCH_APP_SCHEMA,
    handler=lambda args, **kw: launch_app(
        app_name=args.get("app_name", ""),
        args=args.get("args"),
    ),
    check_fn=check_app_launcher_requirements,
    emoji="🚀",
)


registry.register(
    name="open_folder",
    toolset="app_launcher",
    schema=OPEN_FOLDER_SCHEMA,
    handler=lambda args, **kw: open_folder(
        path=args.get("path"),
    ),
    check_fn=check_app_launcher_requirements,
    emoji="📂",
)


registry.register(
    name="open_file",
    toolset="app_launcher",
    schema=OPEN_FILE_SCHEMA,
    handler=lambda args, **kw: open_file(
        path=args.get("path", ""),
    ),
    check_fn=check_app_launcher_requirements,
    emoji="📄",
)
