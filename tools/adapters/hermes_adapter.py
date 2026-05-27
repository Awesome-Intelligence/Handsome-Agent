"""Hermes 工具适配器"""
from .schema_registry import BaseToolAdapter, ToolSource


class HermesToolAdapter(BaseToolAdapter):
    """Hermes 工具适配器 - 将 Hermes 工具转换为统一格式"""
    
    def __init__(self):
        super().__init__(ToolSource.HERMES)
    
    def convert(self, tool_name: str, params: dict) -> dict:
        """
        转换 Hermes 工具参数
        
        Hermes 的参数通常是简单的字典
        这里可以进行参数映射和验证
        """
        # 参数映射表（示例）
        param_mappings = {
            "input_text": "text",
            "input_data": "data",
            "target_file": "path",
        }
        
        converted = {}
        for key, value in params.items():
            new_key = param_mappings.get(key, key)
            converted[new_key] = value
        
        return converted
    
    def convert_result(self, result: dict) -> dict:
        """转换 Hermes 返回结果"""
        # Hermes 返回格式可能需要转换
        return result