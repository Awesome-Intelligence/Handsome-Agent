#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM-powered terminal command handler.
Uses LLM for intent understanding and command parameter extraction.
"""

import json
import re
from typing import Dict, Any, Tuple, List, Optional


async def llm_terminal_command_handler(input_text: str, context: Dict[str, Any]) -> Tuple[Optional[str], List[str], bool]:
    """
    Use LLM to understand terminal command intent and extract parameters.
    
    Args:
        input_text: User's input text
        context: Context containing llm_provider and skill_manager
        
    Returns:
        Tuple of (response, execution_flow, success)
        - If success=True, response contains the result
        - If success=False, caller should fallback to rule-based handler
    """
    llm_provider = context.get('llm_provider')
    skill_manager = context.get('skill_manager')
    
    if not llm_provider:
        return None, [], False
    
    prompt = f"""分析以下用户输入，理解用户的真实意图并提取执行命令所需的参数。

用户输入：{input_text}

请以 JSON 格式返回分析结果，包含以下字段：
{{
    "action_type": "open_app" / "open_folder" / "open_file" / "execute_command" / "unknown",
    "target": 要打开的应用名/文件夹名/文件路径，如 "chrome", "edge", "桌面", "我的电脑", "notepad", "计算器" 等
    "command": 要执行的完整命令，如果 action_type 为 execute_command 则必须提供
    "parameters": {}  // 额外参数对象，根据不同 action_type 可能包含：
        // open_app 时: {"url": "可选的网址"}
        // open_folder 时: {}
        // open_file 时: {"path": "文件路径"}
        // execute_command 时: {}
}}

支持的应用和命令：
- 浏览器: chrome, edge, firefox, safari, 浏览器
- 系统工具: notepad(记事本), calc(计算器), explorer(资源管理器), 记事本, 计算器
- 文件夹: 桌面, 我的电脑, 此电脑, 文档, 下载, 图片, 音乐, 视频, downloads, pictures, music, videos, desktop, documents
- 命令: 任意终端命令

分析要求：
1. 如果用户要打开应用（如浏览器、记事本、计算器），action_type 为 "open_app"
2. 如果用户要打开文件夹（如桌面、我的电脑、文档），action_type 为 "open_folder"
3. 如果用户要打开特定文件，action_type 为 "open_file"
4. 如果用户要执行特定命令，action_type 为 "execute_command"
5. 识别用户提到的浏览器、文件夹、应用等作为 target
6. 如果用户提到网址或搜索关键词，包含在 parameters 中
7. 如果无法确定具体操作，返回 "unknown"

只返回 JSON，不要有其他内容。"""

    try:
        llm_response = await llm_provider.generate(prompt)
        
        try:
            intent_data = json.loads(llm_response.strip())
            
            action_type = intent_data.get('action_type', 'unknown')
            target = intent_data.get('target', '')
            command = intent_data.get('command', '')
            parameters = intent_data.get('parameters', {})
            
            execution_flow = []
            execution_flow.append(f"🤖 [LLM层] 意图识别: {action_type} - {target}")
            
            if action_type == 'open_app' and target and skill_manager:
                browser_name = None
                if target.lower() in ['chrome', 'edge', 'firefox', 'safari', 'browser', '浏览器']:
                    browser_name = target.lower()
                    if browser_name in ['browser', '浏览器']:
                        browser_name = None  # 使用默认浏览器
                
                url = parameters.get('url')
                
                execution_flow.append("🔧 [工具层] 执行打开应用")
                
                result = await skill_manager.execute_skill('tool_open_browser', 
                                                          browser_name=browser_name, 
                                                          url=url)
                
                if result and result.success:
                    execution_flow.append("🔧 [工具层] 打开应用成功")
                    return result.output, execution_flow, True
                
            elif action_type == 'open_folder' and target and skill_manager:
                folder_commands = {
                    '桌面': 'start explorer shell:desktop',
                    'desktop': 'start explorer shell:desktop',
                    '我的电脑': 'start explorer shell:mycomputer',
                    '此电脑': 'start explorer shell:mycomputer',
                    '文档': 'start explorer shell:personal',
                    'documents': 'start explorer shell:personal',
                    '下载': 'start explorer shell:downloads',
                    'downloads': 'start explorer shell:downloads',
                    '图片': 'start explorer shell:photos',
                    'pictures': 'start explorer shell:photos',
                    '音乐': 'start explorer shell:music',
                    'music': 'start explorer shell:music',
                    '视频': 'start explorer shell:video',
                    'videos': 'start explorer shell:video',
                }
                
                folder_cmd = None
                target_lower = target.lower()
                
                for folder_key, folder_cmd_template in folder_commands.items():
                    if folder_key.lower() in target_lower or target_lower in folder_key.lower():
                        folder_cmd = folder_cmd_template
                        break
                
                if folder_cmd:
                    execution_flow.append("🔧 [工具层] 执行打开文件夹")
                    
                    result = await skill_manager.execute_skill('tool_terminal', command=folder_cmd)
                    
                    if result and result.success:
                        execution_flow.append("🔧 [工具层] 打开文件夹成功")
                        return result.output, execution_flow, True
                
            elif action_type == 'execute_command' and command and skill_manager:
                execution_flow.append("🔧 [工具层] 执行终端命令")
                
                result = await skill_manager.execute_skill('tool_terminal', command=command)
                
                if result and result.success:
                    execution_flow.append("🔧 [工具层] 命令执行成功")
                    return result.output, execution_flow, True
            
            return None, execution_flow, False
            
        except (json.JSONDecodeError, KeyError) as e:
            return None, [f"⚠️ [LLM层] JSON 解析失败: {str(e)}"], False
            
    except Exception as e:
        return None, [f"❌ [LLM层] LLM 调用失败: {str(e)}"], False