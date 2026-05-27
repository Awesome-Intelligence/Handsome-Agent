"""OpenClaw 工具适配器"""
from typing import Dict, Any, List
from .schema_registry import BaseToolAdapter, ToolSource


class OpenClawToolAdapter(BaseToolAdapter):
    """OpenClaw 工具适配器 - 将 OpenClaw 工具转换为统一格式"""
    
    def __init__(self):
        super().__init__(ToolSource.OPENCLAW)
        self._param_mappings = self._build_param_mappings()
    
    def _build_param_mappings(self) -> Dict[str, Dict[str, str]]:
        """构建参数映射表"""
        return {
            "str_replace_editor": {
                "file_path": "path",
                "old_string": "old_string",
                "new_string": "new_string",
            },
            "computer_use": {
                "action_type": "action",
                "element_id": "element_id",
                "input_text": "text",
                "x_coord": "x",
                "y_coord": "y",
                "hotkey": "keys",
            },
            "multi_edit": {
                "target_file": "path",
                "find_text": "old_string",
                "replace_text": "new_string",
                "max_count": "count",
            },
            "create_file": {
                "file_path": "path",
                "file_content": "content",
            },
            "search_files": {
                "search_directory": "path",
                "keyword": "pattern",
                "file_type": "file_pattern",
                "recursive_search": "recursive",
            },
            "insert_content_at_line": {
                "target_file": "path",
                "line_number": "line",
                "insert_text": "content",
            },
            "view_lines": {
                "target_file": "path",
                "start_line": "start",
                "end_line": "end",
            },
        }
    
    def convert(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换 OpenClaw 工具参数为统一格式
        
        策略：
        - Hermes 负责"想"（生成 Tool Call 意图）
        - OpenClaw 负责"做"（调用具体的 Edit 工具实现）
        - Hermes 不需要关心工具是怎么实现的，只需要能调用
        """
        mapping = self._param_mappings.get(tool_name, {})
        converted = {}
        
        for key, value in params.items():
            new_key = mapping.get(key, key)
            converted[new_key] = value
        
        return converted
    
    def convert_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换 OpenClaw 返回结果为统一格式
        
        OpenClaw 返回通常包含状态和详细结果
        转换为 Hermes 期望的统一格式
        """
        return {
            "success": result.get("success", True),
            "output": result.get("result", result.get("output", "")),
            "metadata": {
                "tool_source": "openclaw",
                **result.get("metadata", {})
            }
        }
    
    def prepare_tool_call(self, tool_name: str, reasoning: str) -> Dict[str, Any]:
        """
        准备工具调用请求
        
        用于将 Hermes 生成的意图转换为 OpenClaw 可执行的格式
        """
        schema_mapping = {
            "str_replace_editor": "edit_file",
            "multi_edit": "batch_edit",
            "computer_use": "gui_automation",
            "search_files": "grep",
            "view_lines": "read_file_lines",
        }
        
        return {
            "target_tool": schema_mapping.get(tool_name, tool_name),
            "reasoning": reasoning,
            "source": "hermes"
        }
    
    def get_supported_tools(self) -> List[str]:
        """获取支持的工具列表"""
        return list(self._param_mappings.keys())