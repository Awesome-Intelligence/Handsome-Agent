"""代码执行工具定义"""
from tools.schema_registry import UnifiedToolSchema, ToolSource


CODE_TOOLS = [
    UnifiedToolSchema(
        name="python_execute",
        description="执行 Python 代码，支持包管理和结果返回",
        source=ToolSource.HERMES,
        source_name="execute_code",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码"
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒）",
                    "default": 30
                },
                "packages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "需要安装的包",
                    "default": []
                },
                "working_dir": {
                    "type": "string",
                    "description": "工作目录"
                }
            },
            "required": ["code"]
        },
        returns={
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "exit_code": {"type": "integer"}
            }
        },
        examples=[
            {
                "description": "执行简单计算",
                "params": {"code": "print(1 + 2)"}
            }
        ],
        safety_level="medium",
        category="code",
    ),
    UnifiedToolSchema(
        name="delegate_task",
        description="委托子任务给其他 agent 处理",
        source=ToolSource.HERMES,
        source_name="delegate_task",
        parameters={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "要委托的任务描述"
                },
                "context": {
                    "type": "string",
                    "description": "相关上下文信息"
                },
                "max_turns": {
                    "type": "integer",
                    "description": "最大对话轮数",
                    "default": 20
                },
                "model": {
                    "type": "string",
                    "description": "指定使用的模型"
                }
            },
            "required": ["task"]
        },
        returns={
            "type": "object",
            "properties": {
                "result": {"type": "string"},
                "success": {"type": "boolean"}
            }
        },
        safety_level="low",
        category="code",
    ),
]
