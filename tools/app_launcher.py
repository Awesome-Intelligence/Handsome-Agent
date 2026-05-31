#!/usr/bin/env python3
"""
应用程序启动工具 - 提供打开计算器、浏览器等应用程序的功能。

参考 Hermes Agent 的实现。
"""

import json
import platform
import subprocess
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)


# 常见应用程序的Windows路径
COMMON_APPS = {
    'calculator': [
        'calc.exe',
    ],
    'notepad': [
        'notepad.exe',
    ],
    'cmd': [
        'cmd.exe',
    ],
    'powershell': [
        'powershell.exe',
    ],
    'explorer': [
        'explorer.exe',
    ],
    'taskmgr': [
        'taskmgr.exe',
    ],
    'control': [
        'control.exe',
    ],
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


def open_calculator() -> str:
    """打开计算器"""
    return launch_app('calculator')


def open_notepad() -> str:
    """打开记事本"""
    return launch_app('notepad')


def open_cmd() -> str:
    """打开命令提示符"""
    return launch_app('cmd')


def open_explorer(path: Optional[str] = None) -> str:
    """打开文件资源管理器"""
    args = []
    if path:
        args = [path]
    return launch_app('explorer', args=args)


def open_folder(path: Optional[str] = None) -> str:
    """
    打开文件夹。
    
    Args:
        path: 文件夹路径，默认为当前目录
    
    Returns:
        JSON 格式的结果字符串
    """
    try:
        if not path:
            # 如果没有指定路径，打开当前目录
            path = os.getcwd()
        
        # 验证路径是否存在
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
        
        # 打开文件夹（使用 explorer）
        subprocess.Popen(['explorer', str(folder)], shell=False)
        
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
    用系统默认程序打开文件。

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


def check_app_launcher_requirements() -> bool:
    """检查应用程序启动工具的需求"""
    return True


# 工具定义
LAUNCH_APP_SCHEMA = {
    "name": "launch_app",
    "description": "启动Windows应用程序",
    "parameters": {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "应用程序名称（如 calculator, notepad, cmd 等，或者直接是可执行文件路径",
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


OPEN_CALCULATOR_SCHEMA = {
    "name": "open_calculator",
    "description": "打开Windows计算器",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


OPEN_NOTEPAD_SCHEMA = {
    "name": "open_notepad",
    "description": "打开Windows记事本",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


OPEN_CMD_SCHEMA = {
    "name": "open_cmd",
    "description": "打开Windows命令提示符",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


OPEN_EXPLORER_SCHEMA = {
    "name": "open_explorer",
    "description": "打开Windows文件资源管理器",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "可选的目录路径",
            },
        },
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


# 注册工具
OPEN_FILE_SCHEMA = {
    "name": "open_file",
    "description": "用系统默认程序打开文件（如 .md 用记事本/Typora、.pdf 用浏览器、.py 用 IDE 等）。适合用户想'打开某个文件看看'的场景。",
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
    name="open_calculator",
    toolset="app_launcher",
    schema=OPEN_CALCULATOR_SCHEMA,
    handler=lambda args, **kw: open_calculator(),
    check_fn=check_app_launcher_requirements,
    emoji="🔢",
)


registry.register(
    name="open_notepad",
    toolset="app_launcher",
    schema=OPEN_NOTEPAD_SCHEMA,
    handler=lambda args, **kw: open_notepad(),
    check_fn=check_app_launcher_requirements,
    emoji="📝",
)


registry.register(
    name="open_cmd",
    toolset="app_launcher",
    schema=OPEN_CMD_SCHEMA,
    handler=lambda args, **kw: open_cmd(),
    check_fn=check_app_launcher_requirements,
    emoji="💻",
)


registry.register(
    name="open_explorer",
    toolset="app_launcher",
    schema=OPEN_EXPLORER_SCHEMA,
    handler=lambda args, **kw: open_explorer(
        path=args.get("path"),
    ),
    check_fn=check_app_launcher_requirements,
    emoji="📁",
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
