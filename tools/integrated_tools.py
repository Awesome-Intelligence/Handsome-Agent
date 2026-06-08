#!/usr/bin/env python3
"""
Integrated Tools - 整合后的工具系统

统一管理所有工具，整合 ToolRegistry 和 LLM 驱动的决策引擎
"""

import sys
import os
import json
import logging
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from agent.agent import AgentResponse

from tools.registry import registry, ToolEntry
from common.logging_manager import get_decision_logger


class Tool:
    """Tool definition"""
    def __init__(self, name: str, description: str = "", category: str = "general", emoji: str = "🔧"):
        self.name = name
        self.description = description
        self.category = category
        self.emoji = emoji

logger = get_decision_logger(__name__)


def register_integrated_tools(engine):
    """
    把 ToolRegistry 中的工具注册到 LLM 驱动的决策引擎中

    Args:
        engine: LLMDrivenDecisionEngine 实例
    """
    # 延迟导入，避免循环依赖
    from agent.tool_selector.llm_tool_selector import ToolDefinition
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
                examples=[],
                # 🏃 Execution - 🛠️ ToolExec - 传递 emoji 标识
                emoji=tool_entry.emoji if hasattr(tool_entry, 'emoji') else "🔧"
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
                handler=create_handler(tool_entry) if tool_entry.handler else None,
                emoji=tool_entry.emoji if hasattr(tool_entry, 'emoji') else "🔧"
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
_global_engine: Optional[Any] = None


def get_integrated_engine(llm_provider=None, force_reinit: bool = False, context_manager=None):
    """
    获取整合后的决策引擎（单例）

    Args:
        llm_provider: LLM 提供者
        force_reinit: 是否强制重新初始化
        context_manager: 统一的上下文管理器（可选）

    Returns:
        LLMDrivenDecisionEngine: 已注册所有工具的决策引擎
    """
    global _global_engine

    # 延迟导入，避免循环依赖
    from agent.tool_selector.llm_tool_selector import LLMDrivenDecisionEngine

    if _global_engine is None or force_reinit:
        initialize_tools()
        _global_engine = LLMDrivenDecisionEngine(
            llm_provider=llm_provider,
            context_manager=context_manager
        )
        register_integrated_tools(_global_engine)
    else:
        # 如果 engine 已存在但传入了新的 llm_provider，更新它
        if llm_provider is not None:
            _global_engine.llm_provider = llm_provider
        
        # 如果传入了新的 context_manager，更新 tool_selector
        if context_manager is not None:
            _global_engine._context_manager = context_manager
            _global_engine.tool_selector._context_manager = context_manager

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
