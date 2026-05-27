#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM-powered Intent Recognition Service.
Unified service for understanding user intent using LLM.
This module provides pure LLM-based intent recognition - NO hardcoded rules.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """Result of intent recognition."""
    success: bool
    intent_type: str
    action_type: str
    target: str
    parameters: Dict[str, Any]
    raw_response: str
    error: Optional[str] = None


class LLMIntentService:
    """
    Unified LLM-powered intent recognition service.
    
    This service uses LLM to understand user intent across all domains.
    NO hardcoded rules - completely relies on LLM for intent understanding.
    """
    
    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider
        self.intent_prompts = self._create_intent_prompts()
    
    def set_llm_provider(self, llm_provider):
        """Set the LLM provider."""
        self.llm_provider = llm_provider
    
    def _create_intent_prompts(self) -> Dict[str, str]:
        """Create intent recognition prompts for different domains."""
        return {
            'browser_search': """分析以下用户输入，理解用户的真实意图并提取执行所需的参数。

用户输入：{input_text}

请以 JSON 格式返回分析结果，包含以下字段：
{{
    "intent_type": "browser_search" - 始终返回这个值
    "action_type": "open_browser" / "search" / "visit_url" / "unknown"
    "target": 目标浏览器名称或 null，如 "chrome", "edge", "firefox", "默认浏览器"
    "parameters": {{
        "url": "完整网址或 null",
        "search_query": "搜索关键词或 null",
        "search_engine": "baidu / google / null，使用的搜索引擎"
    }}
}}

支持的操作：
- 打开浏览器访问网址
- 使用搜索引擎搜索内容
- 打开特定网站
- 打开浏览器（不访问任何网址）

分析要求：
1. 如果用户要打开浏览器，action_type 为 "open_browser"
2. 如果用户要搜索内容，action_type 为 "search"
3. 如果用户要访问特定网址，action_type 为 "visit_url"
4. 如果用户提到"百度"、"google"等，search_engine 使用对应值
5. 如果用户提供了网址或域名，提取到 url 字段
6. 如果用户说了搜索内容，提取到 search_query 字段

只返回 JSON，不要有其他内容。""",

            'terminal_command': """分析以下用户输入，理解用户的真实意图并提取执行命令所需的参数。

用户输入：{input_text}

请以 JSON 格式返回分析结果，包含以下字段：
{{
    "intent_type": "terminal_command" - 始终返回这个值
    "action_type": "open_app" / "open_folder" / "open_file" / "execute_command" / "unknown"
    "target": 要打开的应用名/文件夹名/文件路径/命令名
    "command": 要执行的完整终端命令（如 start chrome, explorer shell:desktop 等），如果不确定则为空字符串
    "parameters": {{
        "path": "文件/文件夹路径（如果适用）",
        "url": "应用相关的网址（如果适用）",
        "app_name": "应用名称（如果适用）"
    }}
}}

支持的操作：
- 打开应用程序（浏览器、记事本、计算器、文件管理器等）
- 打开系统文件夹（桌面、我的电脑、文档、下载、图片、音乐、视频等）
- 打开特定文件
- 执行终端命令

支持的系统和常用路径：
- 浏览器: chrome, edge, firefox, safari
- 系统工具: notepad(记事本), calc(计算器), explorer(资源管理器)
- 文件夹: 桌面(desktop), 我的电脑(mycomputer), 此电脑, 文档(documents), 下载(downloads), 图片(pictures), 音乐(music), 视频(videos)
- 命令: 任意终端命令

文件夹对应的命令：
- 桌面: explorer shell:desktop
- 我的电脑/此电脑: explorer shell:mycomputer
- 文档: explorer shell:personal
- 下载: explorer shell:downloads
- 图片: explorer shell:photos
- 音乐: explorer shell:music
- 视频: explorer shell:video

分析要求：
1. 如果用户要打开应用，action_type 为 "open_app"
2. 如果用户要打开文件夹，action_type 为 "open_folder"
3. 如果用户要打开文件，action_type 为 "open_file"
4. 如果用户要执行命令，action_type 为 "execute_command"
5. 如果无法确定，返回 "unknown"

只返回 JSON，不要有其他内容。""",

            'general_query': """分析以下用户输入，理解用户的真实意图。

用户输入：{input_text}

请以 JSON 格式返回分析结果：
{{
    "intent_type": "general_query" - 始终返回这个值
    "query_type": "question" / "conversation" / "creation" / "analysis" / "configuration" / "unknown"
    "topic": 用户询问的主题或领域
    "parameters": {{}}
}}

分析要求：
1. 如果用户提问（什么、怎么、为什么等），query_type 为 "question"
2. 如果用户只是聊天（你好、再见等），query_type 为 "conversation"
3. 如果用户要求创建内容（写代码、创建文件等），query_type 为 "creation"
4. 如果用户要求分析（检查、优化、审查等），query_type 为 "analysis"
5. 如果用户要求配置（设置、安装、配置等），query_type 为 "configuration"

只返回 JSON，不要有其他内容。"""
        }
    
    async def recognize_intent(self, input_text: str, domain: str = 'general') -> IntentResult:
        """
        Recognize user intent using LLM.
        
        Args:
            input_text: User's input text
            domain: Domain for intent recognition ('browser_search', 'terminal_command', 'general_query')
            
        Returns:
            IntentResult object containing the analysis
            
        Raises:
            如果 LLM 不可用，返回 IntentResult with success=False
        """
        if not self.llm_provider:
            logger.error("LLM provider not configured")
            return IntentResult(
                success=False,
                intent_type="unknown",
                action_type="unknown",
                target="",
                parameters={},
                raw_response="",
                error="LLM provider not configured. Please configure LLM to enable intent recognition."
            )
        
        try:
            prompt_template = self.intent_prompts.get(domain, self.intent_prompts['general_query'])
            prompt = prompt_template.format(input_text=input_text)
            
            logger.info(f"LLM Intent Service: Sending request for domain '{domain}'")
            logger.debug(f"Prompt: {prompt[:200]}...")
            
            llm_response = await self.llm_provider.generate(prompt)
            
            logger.info(f"LLM Intent Service: Received response")
            logger.debug(f"Response: {llm_response[:200]}...")
            
            intent_data = json.loads(llm_response.strip())
            
            return IntentResult(
                success=True,
                intent_type=intent_data.get('intent_type', domain),
                action_type=intent_data.get('action_type', 'unknown'),
                target=intent_data.get('target', ''),
                parameters=intent_data.get('parameters', {}),
                raw_response=llm_response,
                error=None
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM response is not valid JSON: {e}")
            logger.error(f"Raw response: {llm_response if 'llm_response' in locals() else 'N/A'}")
            return IntentResult(
                success=False,
                intent_type=domain,
                action_type="unknown",
                target="",
                parameters={},
                raw_response=llm_response if 'llm_response' in locals() else "",
                error=f"Failed to parse LLM response as JSON: {str(e)}. Please check LLM configuration."
            )
            
        except Exception as e:
            logger.error(f"LLM intent recognition failed: {e}")
            return IntentResult(
                success=False,
                intent_type=domain,
                action_type="unknown",
                target="",
                parameters={},
                raw_response="",
                error=f"LLM intent recognition failed: {str(e)}. No fallback to hardcoded rules."
            )
    
    def is_llm_available(self) -> bool:
        """Check if LLM provider is available."""
        return self.llm_provider is not None


# Global instance
llm_intent_service = LLMIntentService()


def get_llm_intent_service() -> LLMIntentService:
    """Get the global LLM intent service instance."""
    return llm_intent_service