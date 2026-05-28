"""Web 工具定义 - 搜索和内容提取"""
from tools.schema_registry import UnifiedToolSchema, ToolSource


WEB_TOOLS = [
    UnifiedToolSchema(
        name="web_search",
        description="搜索网页获取信息，支持 Google、Bing 等搜索引擎",
        source=ToolSource.HERMES,
        source_name="web_search",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询关键词"
                },
                "num_results": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 10
                },
                "engine": {
                    "type": "string",
                    "description": "搜索引擎: google, bing, duckduckgo",
                    "default": "google"
                }
            },
            "required": ["query"]
        },
        returns={
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "snippet": {"type": "string"}
                        }
                    }
                }
            }
        },
        examples=[
            {
                "description": "搜索 Python 教程",
                "params": {"query": "Python 教程", "num_results": 5}
            }
        ],
        safety_level="low",
        category="web",
    ),
    UnifiedToolSchema(
        name="web_extract",
        description="提取网页内容，支持多 URL 批量提取",
        source=ToolSource.HERMES,
        source_name="web_extract",
        parameters={
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要提取的 URL 列表"
                },
                "prompt": {
                    "type": "string",
                    "description": "从页面中提取什么信息"
                },
                "max_length": {
                    "type": "integer",
                    "description": "每个页面最大提取字符数",
                    "default": 10000
                }
            },
            "required": ["urls"]
        },
        returns={
            "type": "object",
            "properties": {
                "extracted": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "content": {"type": "string"},
                            "success": {"type": "boolean"}
                        }
                    }
                }
            }
        },
        examples=[
            {
                "description": "提取网页主要内容",
                "params": {"urls": ["https://example.com"]}
            }
        ],
        safety_level="low",
        category="web",
    ),
    UnifiedToolSchema(
        name="http_request",
        description="发送 HTTP 请求（GET/POST/PUT/DELETE）",
        source=ToolSource.HERMES,
        source_name="http_request",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "请求 URL"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "description": "HTTP 方法",
                    "default": "GET"
                },
                "headers": {
                    "type": "object",
                    "description": "请求头"
                },
                "data": {
                    "type": "object",
                    "description": "请求体数据"
                },
                "json": {
                    "type": "object",
                    "description": "JSON 请求体"
                }
            },
            "required": ["url"]
        },
        safety_level="medium",
        category="web",
    ),
]
