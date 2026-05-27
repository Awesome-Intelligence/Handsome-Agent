#!/usr/bin/env python3
"""
Tool System - 参考Claude Tool Use模式
支持函数调用和工具执行
"""

import asyncio
from typing import Dict, Any, Callable


class Tool:
    """工具定义"""
    def __init__(self, name: str, description: str, handler: Callable):
        self.name = name
        self.description = description
        self.handler = handler
    
    def execute(self, query: str) -> str:
        try:
            return str(self.handler(query))
        except Exception as e:
            return f"Error: {e}"


class ToolSystem:
    """工具系统 - 参考LangChain Tool Calling"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        # 计算器工具
        self.register(Tool(
            "calculate",
            "Perform calculations",
            lambda q: self._calculate(q)
        ))
        
        # 搜索工具
        self.register(Tool(
            "search",
            "Search information",
            lambda q: f"Searching: {q}"
        ))
    
    def _calculate(self, expression: str) -> str:
        """安全计算器"""
        try:
            # 仅允许数字和基本运算符
            allowed = set("0123456789+-*/.() ")
            if all(c in allowed for c in expression):
                result = eval(expression)
                return str(result)
            return "Invalid characters"
        except Exception as e:
            return f"Calculation error: {e}"
    
    def register(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool
    
    def execute(self, tool_name: str, query: str) -> str:
        """执行工具"""
        if tool_name not in self.tools:
            return f"Tool {tool_name} not found"
        return self.tools[tool_name].execute(query)
    
    def detect_tools(self, query: str) -> list:
        """检测查询中的工具需求"""
        detected = []
        query_lower = query.lower()
        
        if any(c in query for c in "+-*/"):
            detected.append("calculate")
        if "search" in query_lower or "find" in query_lower:
            detected.append("search")
        
        return detected


class ToolAgent:
    """带工具的Agent - 参考AutoGPT Tool Use"""
    
    def __init__(self):
        self.tools = ToolSystem()
        self.knowledge = {
            "python": "Python is a high-level programming language.",
            "ai": "AI simulates human intelligence.",
            "ml": "Machine Learning learns from data."
        }
    
    async def respond(self, query: str) -> Dict[str, Any]:
        """处理查询并使用工具"""
        start_time = time.time()
        
        # 检测工具
        tools_detected = self.tools.detect_tools(query)
        tool_results = []
        
        # 执行工具
        for tool_name in tools_detected:
            result = self.tools.execute(tool_name, query)
            tool_results.append({
                "tool": tool_name,
                "result": result
            })
        
        # 生成响应
        content = self._generate_response(query)
        
        return {
            "content": content,
            "tools_used": tool_results,
            "execution_time": time.time() - start_time
        }
    
    def _generate_response(self, query: str) -> str:
        """生成知识库响应"""
        query_lower = query.lower()
        for topic, content in self.knowledge.items():
            if topic in query_lower:
                return content
        return "Processing your query with available tools"


import time

# 测试
async def test():
    agent = ToolAgent()
    result = await agent.respond("Calculate 2+2")
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(test())
