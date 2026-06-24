"""
统一的 Tool Schema 注册表
Tool Schema 对齐层的核心组件

提供统一的工具 Schema 生成和处理逻辑，支持：
1. 动态生成 OpenAI 风格的 function calling schemas
2. 跨 Provider 统一的工具调用处理
3. 工具响应格式的标准化
"""

import json
from typing import Dict, List, Optional, Any, Union, Callable
from pydantic import BaseModel, Field
from enum import Enum


class ToolSource(str, Enum):
    """工具来源"""
    HERMES = "hermes"
    OPENCLAW = "openclaw"
    CUSTOM = "custom"


class UnifiedToolSchema(BaseModel):
    """统一工具 Schema"""
    name: str
    description: str
    source: ToolSource
    source_name: str
    parameters: Dict = Field(default_factory=dict)
    returns: Optional[Dict] = None
    examples: List[Dict] = Field(default_factory=list)
    safety_level: str = "medium"
    category: str = "general"


class SchemaRegistry:
    """工具 Schema 注册表"""

    def __init__(self):
        self._schemas: Dict[str, UnifiedToolSchema] = {}
        self._adapters: Dict[str, "BaseToolAdapter"] = {}

    def register(self, schema: UnifiedToolSchema) -> None:
        """注册工具 Schema"""
        self._schemas[schema.name] = schema

    def register_adapter(self, name: str, adapter: "BaseToolAdapter") -> None:
        """注册工具适配器"""
        self._adapters[name] = adapter

    def get(self, name: str) -> Optional[UnifiedToolSchema]:
        """获取工具 Schema"""
        return self._schemas.get(name)

    def list_all(self) -> List[UnifiedToolSchema]:
        """列出所有工具"""
        return list(self._schemas.values())

    def list_by_category(self, category: str) -> List[UnifiedToolSchema]:
        """按类别列出工具"""
        return [s for s in self._schemas.values() if s.category == category]

    def list_by_source(self, source: ToolSource) -> List[UnifiedToolSchema]:
        """按来源列出工具"""
        return [s for s in self._schemas.values() if s.source == source]

    def convert_tool_call(
        self,
        tool_name: str,
        source: ToolSource,
        params: Dict
    ) -> Dict:
        """转换工具调用格式"""
        schema = self.get(tool_name)
        if not schema:
            raise ValueError(f"Tool not found: {tool_name}")

        adapter = self._adapters.get(source)
        if adapter:
            return adapter.convert(tool_name, params)

        return params

    def unregister(self, name: str) -> bool:
        """取消注册工具"""
        if name in self._schemas:
            del self._schemas[name]
            return True
        return False

    def clear(self) -> None:
        """清空所有注册"""
        self._schemas.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 统一的工具 Schema 生成器
# ═══════════════════════════════════════════════════════════════════════════════

def generate_openai_tools_schema(tools: Union[Dict[str, Any], List[Dict]]) -> List[Dict]:
    """
    生成 OpenAI 风格的 function calling tools 列表

    统一格式：
    [
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {...}
            }
        }
    ]

    Args:
        tools: 工具字典 {name: tool_obj} 或工具列表 [{name, description, parameters}]

    Returns:
        OpenAI 风格的 tools 列表
    """
    result = []

    # 统一处理两种输入格式
    if isinstance(tools, dict):
        tool_items = tools.items()
    elif isinstance(tools, list):
        tool_items = [(t.get("name") or t.get("tool_name"), t) for t in tools]
    else:
        return result

    for tool_name, tool in tool_items:
        if not tool_name:
            continue

        # 提取工具属性
        if hasattr(tool, 'description'):
            description = tool.description
        else:
            description = tool.get("description", f"Tool: {tool_name}")

        if hasattr(tool, 'parameters'):
            parameters = tool.parameters
        else:
            parameters = tool.get("parameters", {"type": "object", "properties": {}})

        # 确保 parameters 是有效格式
        if not isinstance(parameters, dict) or "type" not in parameters:
            parameters = {"type": "object", "properties": parameters or {}}

        result.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": description,
                "parameters": parameters
            }
        })

    return result


def extract_tool_from_response(response_data: Dict) -> Optional[Dict[str, Any]]:
    """
    从 LLM 响应中提取工具调用信息

    支持多种响应格式的标准化：
    - OpenAI: tool_calls[0].function
    - MiniMax: function_call or tool_calls[0]
    - Claude: content[0].input

    Args:
        response_data: LLM 响应数据

    Returns:
        标准化格式: {"name": "...", "arguments": {...}} 或 None
    """
    if not response_data:
        return None

    # 格式1: OpenAI tool_calls 格式
    if "tool_calls" in response_data:
        tool_calls = response_data["tool_calls"]
        if tool_calls and len(tool_calls) > 0:
            tc = tool_calls[0]
            func = tc.get("function", tc)
            return {
                "name": func.get("name", ""),
                "arguments": _parse_arguments(func.get("arguments", "{}"))
            }

    # 格式2: MiniMax function_call 格式
    if "function_call" in response_data:
        func = response_data["function_call"]
        if isinstance(func, dict):
            func = func.get("function", func)
            return {
                "name": func.get("name", ""),
                "arguments": _parse_arguments(func.get("arguments", "{}"))
            }

    # 格式3: Claude tool_use 格式
    if "content" in response_data:
        content = response_data["content"]
        if isinstance(content, list) and len(content) > 0:
            block = content[0]
            if block.get("type") == "tool_use":
                return {
                    "name": block.get("name", ""),
                    "arguments": block.get("input", {})
                }

    return None


def _parse_arguments(arguments: Any) -> Dict[str, Any]:
    """
    解析工具参数

    Args:
        arguments: 参数字符串或字典

    Returns:
        解析后的参数字典
    """
    if isinstance(arguments, dict):
        return arguments

    if isinstance(arguments, str):
        try:
            return json.loads(arguments)
        except json.JSONDecodeError:
            return {"input": arguments}

    return {}


def format_tool_result(result: Any, tool_name: str = None) -> str:
    """
    格式化工具执行结果为字符串

    Args:
        result: 工具执行结果
        tool_name: 工具名称（用于日志）

    Returns:
        格式化的结果字符串
    """
    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        # 检查是否是错误结果
        if not result.get("success", True) or result.get("error"):
            return json.dumps(result, ensure_ascii=False, indent=2)

        # 成功结果，简化输出
        return json.dumps(result, ensure_ascii=False, indent=2)

    return str(result)


# ═══════════════════════════════════════════════════════════════════════════════
# 工具调用结果标准化
# ═══════════════════════════════════════════════════════════════════════════════

class ToolCallResult:
    """标准化的工具调用结果"""

    def __init__(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        success: bool = True,
        error: str = None
    ):
        self.tool_name = tool_name
        self.arguments = arguments
        self.result = result
        self.success = success
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "success": self.success,
            "error": self.error
        }

    def to_message_dict(self, tool_call_id: str) -> Dict[str, str]:
        """转换为 tool 角色消息"""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": format_tool_result(self.result, self.tool_name),
            "name": self.tool_name
        }


class BaseToolAdapter:
    """工具适配器基类"""

    def __init__(self, source: ToolSource):
        self.source = source

    def convert(self, tool_name: str, params: Dict) -> Dict:
        """转换工具参数"""
        raise NotImplementedError


class HermesToolAdapter(BaseToolAdapter):
    """Hermes 工具适配器"""

    def __init__(self):
        super().__init__(ToolSource.HERMES)

    def convert(self, tool_name: str, params: Dict) -> Dict:
        """转换 Hermes 工具参数为统一格式"""
        return params


class OpenClawToolAdapter(BaseToolAdapter):
    """OpenClaw 工具适配器"""

    def __init__(self):
        super().__init__(ToolSource.OPENCLAW)

    def convert(self, tool_name: str, params: Dict) -> Dict:
        """转换 OpenClaw 工具参数为统一格式"""
        return params


# 别名以兼容旧代码
BaseToolRegistry = SchemaRegistry
BaseTool = UnifiedToolSchema


class ToolCategory(Enum):
    """工具类别"""
    FILE_TOOLS = "file"
    SHELL_TOOLS = "shell"
    WEB_TOOLS = "web"
    APP_LAUNCHER = "app"


def validate_parameters(schema: Dict, params: Dict) -> Dict:
    """
    验证参数是否符合 Schema

    Args:
        schema: 工具参数 Schema
        params: 实际参数

    Returns:
        验证后的参数（可能添加默认值）

    Raises:
        ValueError: 缺少必需参数或参数类型错误
    """
    if not schema:
        return params

    # 获取参数定义
    properties = schema.get("properties", {})
    required_params = schema.get("required", [])

    # 检查必需参数
    for param_name in required_params:
        if param_name not in params:
            raise ValueError(f"缺少必需参数: {param_name}")

    # 验证每个参数的类型
    for param_name, param_value in params.items():
        if param_name not in properties:
            # 未定义的参数，只发出警告
            continue

        param_schema = properties[param_name]
        expected_type = param_schema.get("type", "string")

        # 类型验证
        if not _validate_type(param_value, expected_type, param_schema):
            raise ValueError(
                f"参数类型错误: {param_name}，期望 {expected_type}，实际 {type(param_value).__name__}"
            )

    return params


def _validate_type(value: Any, expected_type: str, param_schema: Dict) -> bool:
    """验证值是否符合预期类型"""
    if value is None:
        return True  # None 值通过（除非有 required 约束）

    if expected_type == "string":
        return isinstance(value, str)
    elif expected_type == "number" or expected_type == "integer":
        return isinstance(value, (int, float))
    elif expected_type == "boolean":
        return isinstance(value, bool)
    elif expected_type == "array":
        return isinstance(value, list)
    elif expected_type == "object":
        return isinstance(value, dict)

    return True  # 未知类型默认通过