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

技能管理工具（Agent 集成）：
- 技能管理工具 (Skill Manager Tool) - skill_manage
- 技能查看工具 (Skill View Tool) - skill_view
- 技能列表工具 (Skill List Tool) - skill_list
- 技能搜索工具 (Skill Search Tool) - skill_search
- 技能 Curator 工具 (Skill Curator Tool) - skill_curator
- 技能调度器工具 (Skill Scheduler Tool) - skill_scheduler
- 技能分析工具 (Skill Analysis Tool) - skill_analysis
- 技能打包工具 (Skill Bundle Tool) - skill_bundle
- 技能历史工具 (Skill History Tool) - skill_history

新增工具（参考 Hermes）：
- 浏览器工具 (Browser Tool) - 浏览器自动化
- TTS 工具 (TTS Tool) - 文本转语音
- 代码执行工具 (Code Execution Tool) - 安全代码执行
- 图像生成工具 (Image Generation Tool) - AI 图像生成
- Home Assistant 工具 (Home Assistant Tool) - 智能家居控制
- 会话搜索工具 (Session Search Tool) - 历史会话搜索
- 凭证管理工具 (Credential Manager Tool) - 密钥安全管理

凭证管理模块：
- CredentialManager - 凭证管理器类
- SecretMetadata - 密钥元数据结构
- SecretCaptureResult - 密钥捕获结果
- get_credential_manager() - 获取凭证管理器单例
- reset_credential_manager() - 重置凭证管理器单例
"""

from dataclasses import dataclass
from typing import Any, Optional

from .schema_registry import SchemaRegistry, UnifiedToolSchema, ToolSource
from .registry import ToolRegistry, ToolEntry, registry, discover_builtin_tools
from .model_tools import register_tool, tool_registry
from .definitions.file_tools import FILE_TOOLS
from .credential_manager import (
    CredentialManager,
    SecretMetadata,
    SecretCaptureResult,
    get_credential_manager,
    reset_credential_manager,
)


# ─────────────────────────────────────────────────────────────────────────────
# ToolResult - 工具返回值类型（兼容旧版工具）
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ToolResult:
    """工具返回值类型（兼容旧版工具）

    Attributes:
        success: 是否成功
        output: 输出内容
        error: 错误信息（失败时）
        metadata: 元数据
        data: 额外数据
    """
    success: bool
    output: Any = ""
    error: Optional[str] = None
    metadata: Optional[dict] = None
    data: Optional[dict] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
            "data": self.data,
        }


from .definitions.shell_tools import SHELL_TOOLS
from .definitions.web_tools import WEB_TOOLS
from .definitions.code_tools import CODE_TOOLS
from .definitions.browser_tools import BROWSER_TOOLS
from .definitions.multimedia_tools import MULTIMEDIA_TOOLS
from .definitions.task_tools import TASK_TOOLS
from .definitions.app_tools import APP_TOOLS


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

    for tool in APP_TOOLS:
        all_tools[tool['name']] = tool

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
    # 工具装饰器和类型
    "register_tool",
    "tool_registry",
    "ToolResult",
    # 工具定义
    "FILE_TOOLS",
    "SHELL_TOOLS",
    "WEB_TOOLS",
    "CODE_TOOLS",
    "BROWSER_TOOLS",
    "MULTIMEDIA_TOOLS",
    "TASK_TOOLS",
    "APP_TOOLS",
    # 工具获取函数
    "get_all_tools",
    "get_tool_by_name",
    "get_tools_by_category",
    # 凭证管理
    "CredentialManager",
    "SecretMetadata",
    "SecretCaptureResult",
    "get_credential_manager",
    "reset_credential_manager",
]
