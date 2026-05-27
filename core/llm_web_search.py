#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM-powered web search handler.
Uses LLM for intent understanding and parameter extraction.
"""

import json
import re
from typing import Dict, Any, Tuple, List, Optional


async def llm_web_search_handler(input_text: str, context: Dict[str, Any]) -> Tuple[Optional[str], List[str], bool]:
    """
    Use LLM to understand intent and extract parameters for web search.
    
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
    
    prompt = f"""分析以下用户输入，理解用户的真实意图并提取参数。

用户输入：{input_text}

请以 JSON 格式返回分析结果，包含以下字段：
{{
    "intent": "browser_search" 或 "web_search"，如果涉及打开浏览器进行搜索则为 "browser_search"
    "browser_name": "chrome" / "edge" / "firefox" / null，如果不需要打开浏览器则为 null
    "search_engine": "baidu" / "google" / null，使用的搜索引擎
    "search_query": 用户想要搜索的内容，如果不需要搜索则为 null
    "open_url": 要直接访问的完整 URL，如果用户指定了具体网址则为该网址
}}

分析要求：
1. 如果用户说要"打开浏览器"、"用浏览器"、"访问网站"等涉及打开浏览器的操作，intent 为 "browser_search"
2. 如果用户提到"百度"、"google"等搜索引擎，search_engine 使用对应值
3. 如果用户说"帮我查一下"、"搜索"等，提取搜索关键词到 search_query
4. 如果用户提供了完整 URL（如 https://...），使用 open_url
5. 如果同时涉及搜索，search_query 和 search_engine 都要填

只返回 JSON，不要有其他内容。"""

    try:
        llm_response = await llm_provider.generate(prompt)
        
        try:
            intent_data = json.loads(llm_response.strip())
            
            intent = intent_data.get('intent', 'web_search')
            browser_name = intent_data.get('browser_name')
            search_engine = intent_data.get('search_engine', 'baidu')
            search_query = intent_data.get('search_query')
            open_url = intent_data.get('open_url')
            
            execution_flow = []
            execution_flow.append("🤖 [LLM层] 意图分析完成")
            
            if intent == 'browser_search' and skill_manager:
                execution_flow.append("🔧 [工具层] 执行浏览器搜索任务")
                
                if open_url:
                    url = open_url
                elif search_query:
                    if search_engine == 'google':
                        url = f"https://www.google.com/search?q={search_query}"
                    else:
                        url = f"https://www.baidu.com/s?wd={search_query}"
                else:
                    url = f"https://www.baidu.com"
                
                result = await skill_manager.execute_skill('tool_open_browser', 
                                                          browser_name=browser_name, 
                                                          url=url)
                
                if result and result.success:
                    execution_flow.append("🔧 [工具层] 打开浏览器成功")
                    return result.output, execution_flow, True
                
            elif search_query:
                if search_engine == 'google':
                    url = f"https://www.google.com/search?q={search_query}"
                else:
                    url = f"https://www.baidu.com/s?wd={search_query}"
                
                result = await skill_manager.execute_skill('tool_open_browser', 
                                                          browser_name=browser_name, 
                                                          url=url)
                if result and result.success:
                    return result.output, execution_flow, True
            
            return None, execution_flow, False
            
        except (json.JSONDecodeError, KeyError) as e:
            return None, [f"⚠️ [LLM层] JSON 解析失败: {str(e)}"], False
            
    except Exception as e:
        return None, [f"❌ [LLM层] LLM 调用失败: {str(e)}"], False