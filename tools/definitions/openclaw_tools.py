"""OpenClaw 高级工具定义"""
from tools.schema_registry import UnifiedToolSchema, ToolSource


OPENCLAW_TOOLS = [
    UnifiedToolSchema(
        name="str_replace_editor",
        description="字符串替换编辑器 - 精确替换文件中的指定文本",
        source=ToolSource.OPENCLAW,
        source_name="str_replace_editor",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件完整路径"
                },
                "old_string": {
                    "type": "string",
                    "description": "要替换的原始文本（必须精确匹配）"
                },
                "new_string": {
                    "type": "string",
                    "description": "替换后的新文本"
                }
            },
            "required": ["path", "old_string", "new_string"]
        },
        returns={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"}
            }
        },
        examples=[
            {
                "description": "替换函数名",
                "params": {
                    "path": "example.py",
                    "old_string": "def old_function():",
                    "new_string": "def new_function():"
                }
            }
        ],
        safety_level="high",
        category="file",
    ),
    UnifiedToolSchema(
        name="computer_use",
        description="计算机使用 - 通过截图和控制计算机进行 GUI 自动化操作",
        source=ToolSource.OPENCLAW,
        source_name="computer_use",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["screenshot", "click", "type", "key_combo", "scroll"],
                    "description": "操作类型"
                },
                "element_id": {
                    "type": "string",
                    "description": "UI 元素 ID（用于 click）"
                },
                "text": {
                    "type": "string",
                    "description": "输入文本（用于 type）"
                },
                "x": {
                    "type": "integer",
                    "description": "X 坐标（用于 click/scroll）"
                },
                "y": {
                    "type": "integer",
                    "description": "Y 坐标（用于 click/scroll）"
                },
                "keys": {
                    "type": "string",
                    "description": "快捷键组合（如 Ctrl+C）"
                }
            },
            "required": ["action"]
        },
        returns={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "screenshot": {"type": "string", "description": "Base64 编码的截图"},
                "message": {"type": "string"}
            }
        },
        safety_level="critical",
        category="gui",
    ),
    UnifiedToolSchema(
        name="multi_edit",
        description="多位置编辑 - 同时替换文件中多处相同的文本",
        source=ToolSource.OPENCLAW,
        source_name="multi_edit",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "old_string": {
                    "type": "string",
                    "description": "要替换的所有相同文本"
                },
                "new_string": {
                    "type": "string",
                    "description": "替换后的文本"
                },
                "count": {
                    "type": "integer",
                    "description": "替换次数限制（0=全部）",
                    "default": 0
                }
            },
            "required": ["path", "old_string", "new_string"]
        },
        safety_level="high",
        category="file",
    ),
    UnifiedToolSchema(
        name="create_file",
        description="创建新文件",
        source=ToolSource.OPENCLAW,
        source_name="create_file",
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
                }
            },
            "required": ["path", "content"]
        },
        returns={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "path": {"type": "string"}
            }
        },
        safety_level="medium",
        category="file",
    ),
    UnifiedToolSchema(
        name="search_files",
        description="搜索文件内容 - 在文件中搜索包含关键词的行",
        source=ToolSource.OPENCLAW,
        source_name="search_files",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "搜索目录路径"
                },
                "pattern": {
                    "type": "string",
                    "description": "搜索关键词或正则表达式"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "文件类型过滤（如 *.py）",
                    "default": "*"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "是否递归搜索子目录",
                    "default": True
                }
            },
            "required": ["path", "pattern"]
        },
        returns={
            "type": "object",
            "properties": {
                "matches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "line": {"type": "integer"},
                            "content": {"type": "string"}
                        }
                    }
                }
            }
        },
        safety_level="low",
        category="file",
    ),
    UnifiedToolSchema(
        name="insert_content_at_line",
        description="在指定行号后插入内容",
        source=ToolSource.OPENCLAW,
        source_name="insert_content_at_line",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "line": {
                    "type": "integer",
                    "description": "在第几行后插入"
                },
                "content": {
                    "type": "string",
                    "description": "要插入的内容"
                }
            },
            "required": ["path", "line", "content"]
        },
        safety_level="high",
        category="file",
    ),
    UnifiedToolSchema(
        name="view_lines",
        description="查看文件指定行范围的内容",
        source=ToolSource.OPENCLAW,
        source_name="view_lines",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "start": {
                    "type": "integer",
                    "description": "起始行号（从1开始）",
                    "default": 1
                },
                "end": {
                    "type": "integer",
                    "description": "结束行号",
                    "default": 100
                }
            },
            "required": ["path"]
        },
        returns={
            "type": "object",
            "properties": {
                "lines": {"type": "string"},
                "total_lines": {"type": "integer"}
            }
        },
        safety_level="low",
        category="file",
    ),
]


COMPUTER_USE_ACTIONS = [
    {
        "name": "screenshot",
        "description": "截取当前屏幕",
        "params": {}
    },
    {
        "name": "click",
        "description": "点击指定坐标或元素",
        "params": {"x": "int (可选)", "y": "int (可选)", "element_id": "str (可选)"}
    },
    {
        "name": "type",
        "description": "输入文本",
        "params": {"text": "str (必需)"}
    },
    {
        "name": "key_combo",
        "description": "发送快捷键",
        "params": {"keys": "str (必需，如 Ctrl+C)"}
    },
    {
        "name": "scroll",
        "description": "滚动页面",
        "params": {"x": "int", "y": "int", "direction": "up/down"}
    },
]