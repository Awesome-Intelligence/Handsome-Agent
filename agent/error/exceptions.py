"""自定义异常定义

提供 Agent 错误处理体系所需的异常类型层次。
"""

from __future__ import annotations


class AgentError(Exception):
    """Agent 基础异常类"""

    def __init__(self, message: str = "", **kwargs):
        super().__init__(message)
        self.extra = kwargs


class LLMError(AgentError):
    """LLM 相关错误基类"""

    provider: str = ""
    model: str = ""

    def __init__(self, message: str = "", provider: str = "", model: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.provider = provider
        self.model = model


class LLMAuthError(LLMError):
    """认证错误（401/403）"""
    pass


class LLMBillingError(LLMError):
    """计费/配额错误（402）"""
    pass


class LLMRateLimitError(LLMError):
    """速率限制错误（429）"""
    pass


class LLMContextOverflowError(LLMError):
    """上下文溢出错误"""
    pass


class LLMServerError(LLMError):
    """服务端错误（500/502/503）"""
    pass


class ToolExecutionError(AgentError):
    """工具执行错误"""

    def __init__(self, tool_name: str = "", message: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.tool_name = tool_name


class RailBlockedError(AgentError):
    """Rails 拦截错误"""

    def __init__(self, rail_name: str = "", message: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.rail_name = rail_name
