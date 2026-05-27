"""文件操作工具定义"""
from tools.schema_registry import UnifiedToolSchema, ToolSource


FILE_TOOLS = [
    UnifiedToolSchema(
        name="file_read",
        description="读取文件内容",
        source=ToolSource.HERMES,
        source_name="read_file",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码",
                    "default": "utf-8"
                }
            },
            "required": ["path"]
        },
        returns={
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "lines": {"type": "integer"}
            }
        },
        examples=[
            {
                "description": "读取 Python 文件",
                "params": {"path": "example.py"},
                "expected": "def hello(): ..."
            }
        ],
        safety_level="low",
        category="file",
    ),
    UnifiedToolSchema(
        name="file_write",
        description="写入文件内容",
        source=ToolSource.HERMES,
        source_name="write_file",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "文件内容"
                },
                "append": {
                    "type": "boolean",
                    "description": "是否追加模式",
                    "default": False
                }
            },
            "required": ["path", "content"]
        },
        safety_level="medium",
        category="file",
    ),
    UnifiedToolSchema(
        name="file_edit",
        description="编辑文件（行号范围替换）",
        source=ToolSource.OPENCLAW,
        source_name="str_replace_editor",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"}
            },
            "required": ["path", "old_string", "new_string"]
        },
        safety_level="high",
        category="file",
    ),
    UnifiedToolSchema(
        name="directory_list",
        description="列出目录内容",
        source=ToolSource.HERMES,
        source_name="list_directory",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "目录路径"
                },
                "recursive": {
                    "type": "boolean",
                    "default": False
                }
            },
            "required": ["path"]
        },
        safety_level="low",
        category="file",
    ),
]