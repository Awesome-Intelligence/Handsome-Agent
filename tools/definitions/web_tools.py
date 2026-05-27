"""Web 工具定义"""
from tools.schema_registry import UnifiedToolSchema, ToolSource


WEB_TOOLS = [
    UnifiedToolSchema(
        name="web_search",
        description="搜索网页",
        source=ToolSource.HERMES,
        source_name="search_web",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "max_results": {
                    "type": "integer",
                    "default": 5
                }
            },
            "required": ["query"]
        },
        safety_level="low",
        category="web",
    ),
    UnifiedToolSchema(
        name="web_fetch",
        description="获取网页内容",
        source=ToolSource.HERMES,
        source_name="fetch_page",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "网页 URL"
                },
                "max_length": {
                    "type": "integer",
                    "description": "最大获取长度",
                    "default": 5000
                }
            },
            "required": ["url"]
        },
        safety_level="medium",
        category="web",
    ),
    UnifiedToolSchema(
        name="http_request",
        description="发送 HTTP 请求",
        source=ToolSource.HERMES,
        source_name="http_call",
        parameters={
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                    "default": "GET"
                },
                "url": {
                    "type": "string"
                },
                "headers": {
                    "type": "object"
                },
                "body": {
                    "type": "object"
                }
            },
            "required": ["url"]
        },
        safety_level="medium",
        category="web",
    ),
]