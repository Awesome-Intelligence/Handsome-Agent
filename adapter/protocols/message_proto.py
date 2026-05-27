"""通信协议版本定义"""
from enum import Enum


class ProtocolVersion(str, Enum):
    """协议版本"""
    V1 = "v1"
    V2 = "v2"


class MessageProtocol:
    """消息协议定义"""
    
    VERSION = ProtocolVersion.V2
    CONTENT_TYPE = "application/json"
    CHARSET = "utf-8"
    
    # API 端点
    ENDPOINTS = {
        "process": "/api/v1/process",
        "execute": "/api/v1/execute",
        "execution_result": "/api/v1/execution_result",
        "health": "/api/v1/health",
    }
    
    @classmethod
    def get_headers(cls, api_key: str | None = None) -> dict:
        """获取标准 HTTP 请求头"""
        headers = {
            "Content-Type": f"{cls.CONTENT_TYPE}; charset={cls.CHARSET}",
            "X-Protocol-Version": cls.VERSION.value,
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers