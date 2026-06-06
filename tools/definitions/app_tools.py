"""
Application Launcher Tools - 应用程序启动工具

包含：
- launch_app: 启动应用程序
- open_folder: 打开文件夹
- open_file: 用默认程序打开文件
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class LaunchAppSchema(BaseModel):
    """launch_app 工具参数"""
    app_name: str = Field(description="应用程序名称或可执行文件名，支持：calculator, notepad, cmd, powershell, explorer, taskmgr, control, paint, wordpad, word, excel, chrome, edge, firefox 或直接输入：calc.exe, notepad.exe 等")
    args: Optional[List[str]] = Field(default=None, description="可选的启动参数")


class OpenFolderSchema(BaseModel):
    """open_folder 工具参数"""
    path: Optional[str] = Field(default=None, description="要打开的文件夹路径（默认为当前目录）")


class OpenFileSchema(BaseModel):
    """open_file 工具参数"""
    path: str = Field(description="要打开的文件路径（绝对路径或相对于当前目录的路径）")


# 工具定义
LAUNCH_APP_TOOL = {
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
    "category": "system",
    "safety_level": "medium",
    "source": "hermes",
}


OPEN_FOLDER_TOOL = {
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
    "category": "file",
    "safety_level": "low",
    "source": "hermes",
}


OPEN_FILE_TOOL = {
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
    "category": "file",
    "safety_level": "low",
    "source": "hermes",
}


# 工具列表
APP_TOOLS = [LAUNCH_APP_TOOL, OPEN_FOLDER_TOOL, OPEN_FILE_TOOL]