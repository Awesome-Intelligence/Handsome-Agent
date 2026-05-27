"""公共异常定义"""


class HandsomeAgentError(Exception):
    """基础异常"""
    
    def __init__(self, message: str, code: int = 1000):
        self.message = message
        self.code = code
        super().__init__(self.message)


class BrainServiceError(HandsomeAgentError):
    """Brain Service 异常"""
    
    def __init__(self, message: str, code: int = 2000):
        super().__init__(message, code)


class ExecutorError(HandsomeAgentError):
    """执行器异常"""
    
    def __init__(self, message: str, code: int = 3000):
        super().__init__(message, code)


class ToolError(HandsomeAgentError):
    """工具异常"""
    
    def __init__(self, message: str, tool_name: str = "", code: int = 4000):
        self.tool_name = tool_name
        super().__init__(message, code)


class ValidationError(HandsomeAgentError):
    """验证异常"""
    
    def __init__(self, message: str, field: str = "", code: int = 5000):
        self.field = field
        super().__init__(message, code)


class SecurityError(HandsomeAgentError):
    """安全异常"""
    
    def __init__(self, message: str, code: int = 6000):
        super().__init__(message, code)


class TimeoutError(HandsomeAgentError):
    """超时异常"""
    
    def __init__(self, message: str, timeout: float = 0, code: int = 7000):
        self.timeout = timeout
        super().__init__(message, code)