"""tools - 工具定义和 Schema 对齐

Hermes 风格工具系统，包含：
- 文件工具 (File Tools)
- Shell 工具 (Shell Tools)
- Web 工具 (Web Tools)
- 代码工具 (Code Tools)
- 浏览器工具 (Browser Tools)
- 多媒体工具 (Multimedia Tools)
- 任务工具 (Task Tools)
- 工具注册表 (Tool Registry)

内置工具实现：
- 记忆工具 (Memory Tool)
- 技能管理工具 (Skill Manager Tool)
- 审批工具 (Approval Tool)
- 代理工具 (Delegate Tool)
- 视觉工具 (Vision Tool)
- MCP 工具 (MCP Tool)
- 看板工具 (Kanban Tool)
- 定时任务工具 (Cronjob Tool)

新增工具（参考 Hermes）：
- 浏览器工具 (Browser Tool) - 浏览器自动化
- TTS 工具 (TTS Tool) - 文本转语音
- 代码执行工具 (Code Execution Tool) - 安全代码执行
- 图像生成工具 (Image Generation Tool) - AI 图像生成
- Home Assistant 工具 (Home Assistant Tool) - 智能家居控制
- 会话搜索工具 (Session Search Tool) - 历史会话搜索
"""

from .schema_registry import SchemaRegistry, UnifiedToolSchema, ToolSource
from .registry import ToolRegistry, ToolEntry, registry, discover_builtin_tools
from .definitions.file_tools import FILE_TOOLS
from .definitions.shell_tools import SHELL_TOOLS
from .definitions.web_tools import WEB_TOOLS
from .definitions.code_tools import CODE_TOOLS
from .definitions.browser_tools import BROWSER_TOOLS
from .definitions.multimedia_tools import MULTIMEDIA_TOOLS
from .definitions.task_tools import TASK_TOOLS


def get_all_tools():
    """获取所有工具定义"""
    all_tools = {}

    for tool in FILE_TOOLS:
        all_tools[tool.name] = tool.model_dump()

    for tool in SHELL_TOOLS:
        all_tools[tool.name] = tool.model_dump()

    for tool in WEB_TOOLS:
        all_tools[tool.name] = tool.model_dump()

    for tool in CODE_TOOLS:
        all_tools[tool.name] = tool.model_dump()

    for tool in BROWSER_TOOLS:
        all_tools[tool.name] = tool.model_dump()

    for tool in MULTIMEDIA_TOOLS:
        all_tools[tool.name] = tool.model_dump()

    for tool in TASK_TOOLS:
        all_tools[tool.name] = tool.model_dump()

    return all_tools


def get_tool_by_name(name: str):
    """根据名称获取工具定义"""
    all_tools = get_all_tools()
    return all_tools.get(name)


def get_tools_by_category(category: str):
    """根据分类获取工具"""
    all_tools = get_all_tools()
    return {
        name: tool
        for name, tool in all_tools.items()
        if tool.get('category') == category
    }


__all__ = [
    # 注册表
    "SchemaRegistry",
    "UnifiedToolSchema",
    "ToolSource",
    "ToolRegistry",
    "ToolEntry",
    "registry",
    "discover_builtin_tools",
    # 工具定义
    "FILE_TOOLS",
    "SHELL_TOOLS",
    "WEB_TOOLS",
    "CODE_TOOLS",
    "BROWSER_TOOLS",
    "MULTIMEDIA_TOOLS",
    "TASK_TOOLS",
    # 工具获取函数
    "get_all_tools",
    "get_tool_by_name",
    "get_tools_by_category",
]
