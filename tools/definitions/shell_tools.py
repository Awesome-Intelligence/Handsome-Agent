"""Shell 命令工具定义"""
from tools.schema_registry import UnifiedToolSchema, ToolSource


SHELL_TOOLS = [
    UnifiedToolSchema(
        name="shell_execute",
        description="执行 Shell 命令",
        source=ToolSource.HERMES,
        source_name="execute_command",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的命令"
                },
                "timeout": {
                    "type": "number",
                    "description": "超时时间（秒）",
                    "default": 30
                },
                "cwd": {
                    "type": "string",
                    "description": "工作目录"
                }
            },
            "required": ["command"]
        },
        safety_level="critical",
        category="shell",
    ),
    UnifiedToolSchema(
        name="python_execute",
        description="执行 Python 代码",
        source=ToolSource.HERMES,
        source_name="run_python",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python 代码"
                },
                "timeout": {
                    "type": "number",
                    "default": 60
                }
            },
            "required": ["code"]
        },
        safety_level="high",
        category="shell",
    ),
    UnifiedToolSchema(
        name="git_command",
        description="执行 Git 命令",
        source=ToolSource.HERMES,
        source_name="git",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Git 命令（如 'status', 'commit -m \"message\"'）"
                },
                "repo_path": {
                    "type": "string",
                    "description": "仓库路径"
                }
            },
            "required": ["command"]
        },
        safety_level="medium",
        category="shell",
    ),
]