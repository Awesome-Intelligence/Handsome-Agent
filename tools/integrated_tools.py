#!/usr/bin/env python3
"""
Integrated Tools - 整合后的工具系统

统一管理所有工具，整合 ToolRegistry 和 LLM 驱动的决策引擎
"""

import sys
import os
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.registry import registry, ToolEntry
from core.llm_tool_selector import (
    LLMDrivenDecisionEngine,
    ToolDefinition
)
from core.simplified_agent import Tool

logger = logging.getLogger(__name__)


def register_integrated_tools(engine: LLMDrivenDecisionEngine):
    """
    把 ToolRegistry 中的工具注册到 LLM 驱动的决策引擎中
    
    Args:
        engine: LLMDrivenDecisionEngine 实例
    """
    # 导入我们新创建的工具
    import tools.app_launcher
    import tools.file_tools_bridge
    import tools.memory_tool
    import tools.skill_manager_tool
    import tools.approval_tool
    import tools.delegate_tool
    import tools.vision_tool
    import tools.mcp_tool
    import tools.kanban_tool
    import tools.cronjob_tool
    
    # 从 registry 获取工具并注册到决策引擎
    for tool_name, tool_entry in registry._tools.items():
        if tool_entry.is_available():
            # 正确获取参数 schema
            schema = tool_entry.get_schema()
            
            # 使用工厂函数来创建适配器，避免闭包问题
            def create_tool_adapter(entry):
                async def tool_adapter(parameters: Dict, context: Optional[Dict] = None):
                    try:
                        # 传入参数
                        result = entry.handler(parameters, **(context or {}))
                        # 如果返回字符串，尝试解析为 JSON
                        if isinstance(result, str):
                            try:
                                return json.loads(result)
                            except:
                                return {"result": result}
                        return result
                    except Exception as e:
                        logger.error(f"Tool {entry.name} execution failed: {e}")
                        return {"success": False, "error": str(e)}
                return tool_adapter
            
            # 使用 schema 中的参数
            param_schema = schema.get("parameters", {"type": "object", "properties": {}})
            
            engine.register_tool(
                name=tool_name,
                description=tool_entry.description or schema.get("description", ""),
                parameters=param_schema,
                handler=create_tool_adapter(tool_entry),
                category=tool_entry.toolset,
                examples=[]
            )
    
    logger.info(f"Registered {len(engine.tool_selector.tools)} integrated tools")
    return engine


def get_all_tools_as_simplified() -> List[Tool]:
    """
    获取所有工具为 SimplifiedAgent 可用的格式
    
    Returns:
        List[Tool]
    """
    # 导入工具
    import tools.app_launcher
    import tools.file_tools_bridge
    import tools.memory_tool
    import tools.skill_manager_tool
    import tools.approval_tool
    import tools.delegate_tool
    import tools.vision_tool
    import tools.mcp_tool
    import tools.kanban_tool
    import tools.cronjob_tool
    
    tools_list = []
    
    for tool_name, tool_entry in registry._tools.items():
        if tool_entry.is_available():
            schema = tool_entry.get_schema()
            param_schema = schema.get("parameters", {"type": "object", "properties": {}})
            
            # 使用工厂函数来创建 handler，避免闭包问题
            def create_handler(entry):
                async def handler(params):
                    try:
                        result = entry.handler(params)
                        if isinstance(result, str):
                            try:
                                return json.loads(result)
                            except:
                                return {"result": result}
                        return result
                    except Exception as e:
                        return {"error": str(e)}
                return handler
            
            tool = Tool(
                name=tool_name,
                description=tool_entry.description or schema.get("description", ""),
                parameters=param_schema,
                handler=create_handler(tool_entry) if tool_entry.handler else None
            )
            tools_list.append(tool)
    
    return tools_list


def initialize_tools():
    """
    初始化工具系统（自动导入所有工具模块以触发注册
    """
    logger.info("Initializing integrated tools...")
    
    # 导入所有工具模块
    try:
        import tools.app_launcher
        import tools.file_tools_bridge
        import tools.memory_tool
        import tools.skill_manager_tool
        import tools.approval_tool
        import tools.delegate_tool
        import tools.vision_tool
        import tools.mcp_tool
        import tools.kanban_tool
        import tools.cronjob_tool
        logger.info("All tool modules imported successfully")
    except Exception as e:
        logger.error(f"Failed to import tool modules: {e}")
    
    logger.info(f"Tool registry has {len(registry._tools)} tools")
    
    # 检查是否有错误
    for tool_name, tool_entry in registry._tools.items():
        if not tool_entry.is_available():
            logger.warning(f"Tool {tool_name} is not available")
    
    return registry


# 单例：已初始化的决策引擎
_global_engine: Optional[LLMDrivenDecisionEngine] = None


def get_integrated_engine(llm_provider=None, force_reinit: bool = False) -> LLMDrivenDecisionEngine:
    """
    获取整合后的决策引擎（单例）
    
    Args:
        llm_provider: LLM 提供者
        force_reinit: 是否强制重新初始化
    
    Returns:
        LLMDrivenDecisionEngine: 已注册所有工具的决策引擎
    """
    global _global_engine
    
    if _global_engine is None or force_reinit:
        initialize_tools()
        _global_engine = LLMDrivenDecisionEngine(llm_provider=llm_provider)
        register_integrated_tools(_global_engine)
    
    return _global_engine


if __name__ == "__main__":
    # 测试初始化
    logging.basicConfig(level=logging.INFO)
    
    print("Testing integrated tools initialization...")
    reg = initialize_tools()
    
    print(f"\nRegistered {len(reg._tools)} tools:")
    for name, entry in reg._tools.items():
        is_available = "AVAILABLE" if entry.is_available() else "UNAVAILABLE"
        print(f"  - {name} ({entry.toolset}) [{is_available}]")
    
    print("\n✅ Integrated tools system ready!")
