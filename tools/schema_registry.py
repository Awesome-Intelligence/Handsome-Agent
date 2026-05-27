"""
统一的 Tool Schema 注册表
Tool Schema 对齐层的核心组件
"""

from typing import Dict, List, Optional
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
    source_name: str  # 原始工具名称
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
        """
        转换工具调用格式
        
        将不同来源的工具调用转换为统一格式
        """
        schema = self.get(tool_name)
        if not schema:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # 使用适配器转换
        adapter = self._adapters.get(source)
        if adapter:
            return adapter.convert(tool_name, params)
        
        # 直接返回参数
        return params


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
        # Hermes 参数映射（简化实现）
        return params


class OpenClawToolAdapter(BaseToolAdapter):
    """OpenClaw 工具适配器"""
    
    def __init__(self):
        super().__init__(ToolSource.OPENCLAW)
    
    def convert(self, tool_name: str, params: Dict) -> Dict:
        """转换 OpenClaw 工具参数为统一格式"""
        # OpenClaw 的参数格式可能不同，需要转换
        # 这是一个简化实现
        return params