"""
统一的 Tool Schema 注册表
Tool Schema 对齐层的核心组件
"""

from typing import Dict, List, Optional, Any
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