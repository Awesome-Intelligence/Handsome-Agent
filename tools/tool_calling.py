#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool calling integration for the agent.
Enables the agent to use tools for executing tasks.
"""

import json
import re
from typing import Dict, List, Any, Optional
from . import tool_registry, ToolResult


class ToolCallingAgent:
    """Agent with tool calling capabilities."""
    
    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider
        self.tools = tool_registry.list_tools()
    
    def get_tools_description(self) -> str:
        """Get description of all available tools."""
        if not self.tools:
            return "无可用工具"
        
        desc = "可用工具:\n\n"
        for tool in self.tools:
            desc += f"**{tool['name']}**: {tool['description']}\n"
            if tool['parameters']:
                desc += "参数:\n"
                for param in tool['parameters']:
                    required = "必需" if param.get('required') else "可选"
                    desc += f"  - {param['name']} ({param['type']}, {required}): {param.get('description', '')}\n"
            desc += "\n"
        
        return desc
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Call a specific tool with arguments."""
        tool = tool_registry.get(tool_name)
        
        if not tool:
            return ToolResult(success=False, output="", error=f"未找到工具: {tool_name}")
        
        try:
            func = tool['func']
            
            sig_params = {}
            for param_name, param_value in arguments.items():
                sig_params[param_name] = param_value
            
            result = func(**sig_params)
            return result
            
        except TypeError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"参数错误: {str(e)}\n可用参数: {[p['name'] for p in tool['parameters']]}"
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    async def generate_with_tools(self, prompt: str, max_turns: int = 5) -> str:
        """Generate response with tool calling capabilities."""
        if not self.llm_provider:
            return "工具调用需要配置大模型"
        
        tools_json = json.dumps(self.tools, indent=2, ensure_ascii=False)
        
        system_prompt = f"""你是一个智能助手，可以使用工具来完成任务。

{self.get_tools_description()}

当用户请求需要执行操作时，你应该：
1. 分析用户请求，确定需要使用的工具
2. 使用JSON格式返回工具调用，如：
{{"tool": "tool_name", "args": {{"param1": "value1", "param2": "value2"}}}}
3. 等待工具执行结果后，继续处理
4. 如果需要多个工具，按顺序调用

如果没有需要执行的工具，直接回答用户问题。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        for turn in range(max_turns):
            try:
                response = await self.llm_provider.generate(messages)
                
                tool_calls = self._extract_tool_calls(response)
                
                if not tool_calls:
                    return response
                
                for call in tool_calls:
                    tool_name = call.get("tool")
                    args = call.get("args", {})
                    
                    result = self.call_tool(tool_name, args)
                    
                    messages.append({"role": "assistant", "content": json.dumps(call)})
                    messages.append({
                        "role": "system",
                        "content": f"工具 '{tool_name}' 执行结果:\n{result.output}\n{result.error if result.error else ''}"
                    })
                    
            except Exception as e:
                return f"执行出错: {str(e)}"
        
        return "达到最大调用次数限制"
    
    def _extract_tool_calls(self, text: str) -> List[Dict]:
        """Extract tool calls from LLM response."""
        tool_calls = []
        
        json_patterns = [
            r'\{[^{}]*"tool"\s*:\s*"([^"]+)"[^{}]*"args"\s*:\s*(\{[^}]+\})[^}]*\}',
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    if isinstance(match, tuple):
                        if len(match) == 2:
                            call = {"tool": match[0], "args": json.loads(match[1])}
                        else:
                            call = json.loads(match[0])
                    else:
                        call = json.loads(match)
                    
                    if "tool" in call and "args" in call:
                        tool_calls.append(call)
                except:
                    continue
        
        if not tool_calls:
            code_blocks = re.findall(r'```(?:json|python)?\s*(.*?)```', text, re.DOTALL)
            for block in code_blocks:
                if any(tool['name'] in block for tool in self.tools):
                    for tool in self.tools:
                        if tool['name'] in block:
                            try:
                                args_match = re.search(r'{[^}]+}', block)
                                if args_match:
                                    tool_calls.append({
                                        "tool": tool['name'],
                                        "args": json.loads(args_match.group())
                                    })
                            except:
                                pass
        
        return tool_calls


def create_tool_calling_agent(llm_provider=None) -> ToolCallingAgent:
    """Create a tool calling agent."""
    return ToolCallingAgent(llm_provider)
