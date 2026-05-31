#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Router Handlers Module.

Contains all route handlers for the TaskRouter.
Inspired by Hermes Agent's route handlers.
"""

from typing import Dict, List, Tuple, Any

from datetime import datetime


def _should_log(context: Dict[str, Any]) -> bool:
    """Check if detailed logs should be printed based on context."""
    return context.get('enable_detailed_logs', True)


import json
import os
import subprocess
import asyncio

from .router import router, route_handler, RouteMatch
from .logging_manager import get_decision_logger, get_execution_logger, get_llm_logger, get_tool_logger
from .environment import env_detector


@route_handler(
    'time_query',
    'Time Query Handler',
    'Handles time and date queries',
    # DEPRECATED: keywords should be determined by LLM, not hardcoded
    keywords=[],
    priority=2
)
async def time_query_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    tool = get_tool_logger("TimeQuery")
    
    execution_flow = []
    should_log = _should_log(context)
    
    if should_log:
        tool.info(f"（TimeQuery） 收到时间查询请求: {input_text[:30]}...")
    execution_flow.append("🧠 [决策层] TimeQuery 收到请求")
    
    now = datetime.now()
    weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekday = weekday_names[now.weekday()]
    
    date_str = now.strftime('%Y年%m月%d日')
    time_str = now.strftime('%H:%M:%S')
    
    response = f"📅 当前时间：{date_str} {weekday}\n⏰ 现在是：{time_str}"
    
    if '天' in input_text or '号' in input_text or 'day' in input_text.lower():
        response += f"\n\n今天是{now.day}号"
    
    if should_log:
        tool.info(f"（TimeQuery） 返回时间: {date_str} {time_str}")
    execution_flow.append("🧠 [决策层] TimeQuery 返回结果")
    
    return response, execution_flow


@route_handler(
    'weather_query',
    'Weather Query Handler',
    'Handles weather and temperature queries',
    # DEPRECATED: keywords should be determined by LLM, not hardcoded
    keywords=[],
    priority=2
)
async def weather_query_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    tool = get_tool_logger("WeatherQuery")
    
    execution_flow = []
    should_log = _should_log(context)
    
    if should_log:
        tool.info(f"（WeatherQuery） 收到天气查询请求: {input_text[:30]}...")
    execution_flow.append("🧠 [决策层] WeatherQuery 收到请求")
    
    skill_manager = context.get('skill_manager') if context else None
    
    city = None
    cities = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '南京', '重庆']
    for c in cities:
        if c in input_text:
            city = c
            break
    
    if city and skill_manager:
        if should_log:
            tool.info(f"（WeatherQuery） 使用 WeatherSkill 查询 {city}")
        execution_flow.append(f"（WeatherQuery） 调用 WeatherSkill")
        
        try:
            result = await skill_manager.execute_skill('weather', city=city)
            if result and result.success:
                if should_log:
                    tool.info(f"（WeatherQuery） 收到结果: {result.output[:50]}...")
                execution_flow.append("（WeatherQuery） WeatherSkill 执行成功")
                return result.output, execution_flow
        except Exception as e:
            if should_log:
                tool.warning(f"（WeatherQuery） WeatherSkill 执行失败: {str(e)}")
    
    response = "🌤️ 天气查询功能\n\n抱歉，我目前无法获取实时天气信息。\n\n您可以通过以下方式查询天气：\n• 查看手机天气应用\n• 搜索「城市名+天气」\n• 使用语音助手说「今天天气怎么样」"
    
    if city:
        response = f"📍 {city}天气查询\n\n抱歉，暂不支持查询 {city} 的实时天气。\n\n建议您通过天气预报网站或手机应用查看。"
    
    if should_log:
        tool.info(f"（WeatherQuery） 返回: 无法获取实时天气")
    execution_flow.append("🧠 [决策层] WeatherQuery 返回结果")
    
    return response, execution_flow


@route_handler(
    'conversation',
    'Conversation Handler',
    'Handles general conversation and greetings',
    # DEPRECATED: keywords should be determined by LLM, not hardcoded
    keywords=[],
    priority=1
)
async def conversation_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    llm = get_llm_logger("ConversationHandler")
    llm_logger = get_llm_logger("LLMProvider")
    tool_logger = get_tool_logger("ConversationTools")
    
    execution_flow = []
    should_log = _should_log(context)
    
    input_lower = input_text.lower()
    
    # 完全使用 LLM 判断意图（遵循规则）
    llm_provider = context.get('llm_provider') if context else None
    session_history = context.get('session_history', []) if context else []
    
    if llm_provider:
        try:
            # LLM 判断用户意图类型
            intent_prompt = f"""用户输入："{input_text}"

判断用户意图类型：
1. greeting - 问候语（hello, hi, 你好, 早上好等）
2. time_query - 查询时间（现在几点、日期等）
3. weather_query - 查询天气
4. history_query - 查询对话历史（之前聊了什么、上一句是什么）
5. conversation - 普通对话

只返回 JSON：{{"type": "greeting|time_query|weather_query|history_query|conversation", "confidence": 0.0-1.0}}
"""
            
            if should_log:
                llm.info(f"🤖 [LLM层] ConversationHandler 使用 LLM 判断意图...")
            
            intent_response = await llm_provider.generate(intent_prompt)
            
            import re
            import json
            json_match = re.search(r'\{.*?"type".*?\}', intent_response, re.DOTALL)
            
            if json_match:
                intent_data = json.loads(json_match.group(0))
                intent_type = intent_data.get('type', 'conversation')
                
                if should_log:
                    llm.info(f"🤖 [LLM层] LLM 判断意图: {intent_type} (置信度: {intent_data.get('confidence', 0):.2f})")
                execution_flow.append(f"🧠 [决策层] LLM 判断: {intent_type}")
                
                # 根据 LLM 判断的意图类型处理
                if intent_type == 'greeting':
                    greeting_response = await llm_provider.generate(f"用户说：{input_text}。请友好地回复一个简短的问候，不要超过20个字。")
                    return greeting_response, execution_flow
                
                elif intent_type == 'time_query':
                    return await time_query_handler(input_text, context)
                
                elif intent_type == 'weather_query':
                    return await weather_query_handler(input_text, context)
                
                elif intent_type == 'history_query':
                    if session_history:
                        # 查找消息历史
                        user_messages = []
                        assistant_messages = []
                        for msg in session_history:
                            if isinstance(msg, dict):
                                role = msg.get('role', '')
                                content = msg.get('content', '')
                            else:
                                role = getattr(msg, 'role', '')
                                content = getattr(msg, 'content', '')
                            
                            if role == 'user':
                                user_messages.append(content)
                            elif role == 'assistant':
                                assistant_messages.append(content)
                        
                        # 使用 LLM 总结或返回
                        if '上一句' in input_text or '最后说了' in input_text:
                            if user_messages:
                                return f"你上一条消息是：{user_messages[-1]}", execution_flow
                        
                        # LLM 总结对话历史
                        history_text = "以下是对话历史：\n\n"
                        for i, (user_msg, assistant_msg) in enumerate(zip(user_messages, assistant_messages), 1):
                            history_text += f"用户：{user_msg}\n"
                            if assistant_msg:
                                history_text += f"助手：{assistant_msg}\n"
                            history_text += "\n"
                        
                        prompt = f"{history_text}\n\n请简要总结我们聊了什么，用中文回答。简洁一些。"
                        response = await llm_provider.generate(prompt)
                        return f"📝 对话总结：\n\n{response}", execution_flow
                    else:
                        return "我们还没有聊过天呢。你想聊些什么？", execution_flow
                
                # conversation 类型继续往下走，使用 LLM 对话
        except Exception as e:
            if should_log:
                llm.warning(f"🤖 [LLM层] ConversationHandler LLM 判断失败: {str(e)}")
            execution_flow.append("🧠 [决策层] LLM 失败，使用基础回复")
            return "抱歉，我遇到了一些问题。请告诉我你想做什么？", execution_flow
    
    if should_log:
        llm.info(f"🤖 [LLM层] ConversationHandler 收到请求: {input_text[:30]}...")
    execution_flow.append("🧠 [决策层] ConversationHandler 收到请求")
    
    # 使用 LLM 对话（前面的 LLM 已判断意图）
    if llm_provider:
        try:
            provider_name = llm_provider.__class__.__name__
            llm_logger.info(f"🤖 [LLM层] {provider_name} 准备调用...")
            
            # 构建完整的输入日志
            if session_history:
                input_summary = f"[对话历史 {len(session_history)} 条] {input_text[:30]}..."
                llm_logger.debug(f"🤖 [LLM层] ┌─ 输入 (共 {len(session_history) + 1} 条消息):")
                for i, msg in enumerate(session_history):
                    if isinstance(msg, dict):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')[:50]
                    else:
                        role = getattr(msg, 'role', 'unknown')
                        content = getattr(msg, 'content', '')[:50]
                    ellipsis = "..." if len(getattr(msg, 'content', str(msg))) > 50 else ""
                    llm_logger.debug(f"🤖 [LLM层] │  [{i}][{role}]: {content}{ellipsis}")
                llm_logger.debug(f"🤖 [LLM层] │  [user]: {input_text[:50]}...")
                llm_logger.debug(f"🤖 [LLM层] └─ 当前输入: {input_text[:50]}...")
            else:
                input_summary = input_text[:50]
                llm_logger.debug(f"🤖 [LLM层] ┌─ 输入: {input_text}")
            
            llm.info(f"🤖 [LLM层] ConversationHandler 准备调用 LLM")
            
            # Convert session history to messages format for LLM
            messages_for_llm = None
            if session_history:
                from brain.llm.base import Message as LLMMessage
                messages_for_llm = []
                for msg in session_history:
                    if isinstance(msg, dict):
                        role = msg.get('role', 'user')
                        content = msg.get('content', '')
                    else:
                        role = getattr(msg, 'role', 'user')
                        content = getattr(msg, 'content', '')
                    messages_for_llm.append(LLMMessage(role=role, content=content))
            
            if messages_for_llm:
                response = await llm_provider.generate(input_text, messages=messages_for_llm)
            else:
                response = await llm_provider.generate(input_text)
            
            # 详细输出日志
            llm_logger.debug(f"🤖 [LLM层] ├─ 响应长度: {len(response)} 字符")
            llm_logger.summary(f"🤖 [LLM层] {provider_name} 返回成功")
            llm_logger.debug(f"🤖 [LLM层] └─ 输出: {response[:200]}{'...' if len(response) > 200 else ''}")
            llm.info(f"🤖 [LLM层] ConversationHandler 收到 LLM 返回")
            
            return response, execution_flow
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            llm_logger.error(f"🤖 [LLM层] {provider_name} 调用失败: {error_type} - {error_msg}")
            llm.error(f"🤖 [LLM层] ConversationHandler LLM 调用失败: {error_type}")
            
            # 提供更详细的错误信息给用户
            if "API" in error_msg or "api" in error_msg.lower():
                detail = "可能是 API 配置问题，请检查 API Key 和网络连接。"
            elif "timeout" in error_msg.lower() or "超时" in error_msg:
                detail = "请求超时，请检查网络连接后重试。"
            elif "auth" in error_msg.lower() or "认证" in error_msg or "401" in error_msg:
                detail = "认证失败，请检查 API Key 是否正确。"
            elif "rate" in error_msg.lower() or "限流" in error_msg:
                detail = "请求过于频繁，请稍后再试。"
            else:
                detail = f"错误信息: {error_msg[:100]}"
            
            user_message = f"❌ 大模型调用失败\n\n{detail}\n\n如果问题持续存在，请检查：\n• API Key 是否有效\n• 网络连接是否正常\n• API 服务是否可用"
            
            return user_message, execution_flow
    
    if should_log:
        llm.info(f"🤖 [LLM层] ConversationHandler 使用模板响应")
    execution_flow.append("🧠 [决策层] TemplateEngine 使用模板")
    
    # 使用 LLM 判断意图并响应（遵循规则）
    llm_provider = context.get('llm_provider') if context else None
    
    if llm_provider:
        try:
            # LLM 判断意图类型
            intent_prompt = f"""用户输入："{input_text}"

判断用户意图：
1. greeting - 问候语
2. farewell - 告别语
3. other - 其他

只返回 JSON：{{"type": "意图类型"}}
"""
            
            intent_response = await llm_provider.generate(intent_prompt)
            
            import re
            import json
            json_match = re.search(r'\{.*?"type".*?\}', intent_response, re.DOTALL)
            
            if json_match:
                intent_data = json.loads(json_match.group(0))
                intent_type = intent_data.get('type', 'other')
                
                if intent_type == 'greeting':
                    response = await llm_provider.generate(f"用户说：{input_text}。请友好地回复一个简短的问候。")
                    return response, execution_flow
                elif intent_type == 'farewell':
                    response = await llm_provider.generate(f"用户说：{input_text}。请友好地回复一个简短的告别。")
                    return response, execution_flow
        except Exception:
            pass
    
    # 降级：默认响应
    return "我明白你说的。我可以帮你处理各种任务，比如：\n- 回答问题\n- 执行终端命令\n- 文件操作\n- 代码相关任务\n\n请问有什么我可以帮助你的吗？", execution_flow


@route_handler(
    'coding_assistant',
    'Coding Assistant Handler',
    'Handles coding-related queries and code generation',
    # DEPRECATED: keywords should be determined by LLM, not hardcoded
    keywords=[],
    priority=3
)
async def coding_assistant_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    llm = get_llm_logger("CodingAssistant")
    llm_logger = get_llm_logger("LLMProvider")
    tool_logger = get_tool_logger("CodeTools")
    
    should_log = _should_log(context)
    execution_flow = []
    
    llm.info(f"🤖 [LLM层] CodingAssistant 收到编程请求: {input_text[:30]}...")
    tool_logger.debug(f"（CodeAnalyzer） 准备生成代码")
    execution_flow.append("🧠 [决策层] CodingAssistant 收到请求")
    
    llm_provider = context.get('llm_provider') if context else None
    
    if llm_provider:
        try:
            provider_name = llm_provider.__class__.__name__
            llm_logger.info(f"🤖 [LLM层] {provider_name} 准备生成代码...")
            
            prompt = f"请用代码解决以下问题，代码要完整可运行：\n{input_text}"
            llm_logger.debug(f"🤖 [LLM层] ┌─ 代码请求:")
            llm_logger.debug(f"🤖 [LLM层] │  Prompt: {prompt[:100]}...")
            llm_logger.debug(f"🤖 [LLM层] └─ 原始输入: {input_text[:50]}...")
            
            response = await llm_provider.generate(prompt)
            
            llm_logger.summary(f"🤖 [LLM层] {provider_name} 代码生成成功")
            llm_logger.debug(f"🤖 [LLM层] ├─ 代码长度: {len(response)} 字符")
            llm_logger.debug(f"🤖 [LLM层] └─ 生成代码:\n{response[:300]}{'...' if len(response) > 300 else ''}")
            tool_logger.debug(f"（CodeAnalyzer） 代码生成完成")
            
            return response, execution_flow
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            llm_logger.error(f"🤖 [LLM层] {provider_name} 代码生成失败: {error_type} - {error_msg}")
            llm.error(f"🤖 [LLM层] CodingAssistant 代码生成失败: {error_type}")
            
            user_message = f"❌ 代码生成失败\n\n错误类型: {error_type}\n错误信息: {error_msg[:100]}\n\n请检查：\n• 网络连接是否正常\n• API 服务是否可用"
            
            return user_message, execution_flow
    
    tool_logger.info(f"🛠️ [工具层] CodeAnalyzer 使用模板响应")
    execution_flow.append("🧠 [决策层] CodeAnalyzer 使用模板")
    return "请配置 LLM provider 以启用代码助手功能。", execution_flow


@route_handler(
    'file_operations',
    'File Operations Handler',
    'Handles file reading, writing, and management',
    # DEPRECATED: keywords should be determined by LLM, not hardcoded
    keywords=[],
    priority=4
)
async def file_operations_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    tool = get_tool_logger("FileOperations")
    execution = get_execution_logger("FileManager")
    tool_logger = get_tool_logger("FileTools")
    
    execution_flow = []
    should_log = _should_log(context)
    
    tool.info(f"（FileManager） 收到文件操作请求: {input_text[:30]}...")
    tool_logger.debug(f"（FileManager） 准备执行文件操作")
    execution_flow.append("🧠 [决策层] FileOperations 收到请求")
    
    input_lower = input_text.lower()
    llm_provider = context.get('llm_provider') if context else None
    
    # 使用 LLM 判断意图（遵循规则）
    if llm_provider:
        try:
            # LLM 判断文件操作类型
            intent_prompt = f"""用户输入："{input_text}"

判断用户想做什么文件操作：
1. read_file - 读取文件内容
2. write_file - 写入/创建文件
3. list_directory - 列出目录内容
4. open_folder - 打开文件夹
5. other - 其他操作

只返回 JSON：{{"type": "操作类型", "target": "目标路径或文件", "confidence": 0.0-1.0}}
"""
            
            if should_log:
                tool.info(f"（FileManager） 使用 LLM 判断文件操作类型...")
            
            intent_response = await llm_provider.generate(intent_prompt)
            
            import re
            import json
            json_match = re.search(r'\{.*?"type".*?\}', intent_response, re.DOTALL)
            
            if json_match:
                intent_data = json.loads(json_match.group(0))
                intent_type = intent_data.get('type', 'other')
                target = intent_data.get('target', '')
                
                if should_log:
                    tool.info(f"（FileManager） LLM 判断: {intent_type} -> {target}")
                execution_flow.append(f"🧠 [决策层] LLM 判断: {intent_type}")
                
                # 根据意图类型处理
                if intent_type == 'read_file' and target:
                    return await _read_file_with_llm(target, execution_flow, should_log, execution)
                
                elif intent_type == 'list_directory' or intent_type == 'open_folder':
                    if target:
                        return await _list_directory_with_llm(target, execution_flow, should_log, execution)
                    else:
                        # 尝试列出常见文件夹
                        return await _list_common_folders(input_text, execution_flow, should_log, execution, tool)
                
                elif intent_type == 'write_file':
                    return "[文件写入] 请使用更具体的文件操作技能来写入文件。", execution_flow
                
        except Exception as e:
            if should_log:
                tool.warning(f"（FileManager） LLM 判断失败: {str(e)}，使用基础处理")
            execution_flow.append("🧠 [决策层] LLM 失败")
    
    # 基础处理：使用正则提取文件路径（不是硬编码意图，而是提取参数）
    import re
    file_patterns = [
        r'[\'"](.+?)[\'"]',  # 引号内的路径
        r'(?:file|path|路径)[:\s]+([^\s]+)',  # file: /path
        r'([A-Za-z]:\\[^\s]+)',  # Windows 绝对路径
        r'(/[^\s]+\.[a-zA-Z]+)',  # Unix 路径
    ]
    
    file_path = None
    for pattern in file_patterns:
        match = re.search(pattern, input_text)
        if match:
            file_path = match.group(1)
            break
    
    if file_path:
        return await _read_file_with_llm(file_path, execution_flow, should_log, execution)
    
    # 默认情况
    if should_log:
        execution.info(f"FileManager 无法识别具体操作")
    return f"[文件操作] 无法识别操作类型。请使用：\n- 读取文件 /path/to/file\n- 列出目录 /path/to/dir\n- 查看桌面文件", execution_flow


async def _read_file_with_llm(file_path: str, execution_flow: list, should_log: bool, execution) -> Tuple[str, list]:
    """使用 LLM 辅助读取文件"""
    try:
        if should_log:
            execution.info(f"FileManager 读取文件: {file_path}")
        execution_flow.append(f"（FileManager） 读取 {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(3000)
            return f"📄 文件内容 ({file_path}):\n\n{content}", execution_flow
    except Exception as e:
        return f"无法读取文件 {file_path}: {str(e)}", execution_flow


async def _list_directory_with_llm(target_path: str, execution_flow: list, should_log: bool, execution) -> Tuple[str, list]:
    """使用 LLM 辅助列出目录"""
    try:
        if should_log:
            execution.info(f"FileManager 列出目录: {target_path}")
        execution_flow.append(f"（FileManager） 列出 {target_path}")
        
        files = os.listdir(target_path)
        if files:
            file_list = "\n".join([f"  • {f}" for f in files[:50]])
            return f"📁 目录内容 ({target_path}):\n\n{file_list}\n\n共 {len(files)} 个文件/文件夹", execution_flow
        else:
            return f"📁 目录为空", execution_flow
    except Exception as e:
        return f"无法访问目录 {target_path}: {str(e)}", execution_flow


async def _list_common_folders(input_text: str, execution_flow: list, should_log: bool, execution, tool) -> Tuple[str, list]:
    """列出常见文件夹"""
    folder_keywords = {
        'desktop': ['desktop', '桌面'],
        'documents': ['documents', '文档', 'doc'],
        'downloads': ['downloads', '下载'],
        'pictures': ['pictures', '图片', 'photos'],
        'music': ['music', '音乐'],
        'videos': ['videos', '视频', 'movies'],
    }
    
    input_lower = input_text.lower()
    
    for folder_key, keywords in folder_keywords.items():
        if any(kw in input_lower for kw in keywords):
            target_path = env_detector.get_folder_path(folder_key)
            if target_path:
                if should_log:
                    execution.info(f"FileManager 列出目录: {target_path}")
                execution_flow.append(f"（FileManager） 列出 {target_path}")
                
                try:
                    files = os.listdir(target_path)
                    if files:
                        file_list = "\n".join([f"  • {f}" for f in files[:50]])
                        return f"📁 {folder_key} 目录内容:\n\n{file_list}\n\n共 {len(files)} 个文件/文件夹", execution_flow
                    else:
                        return f"📁 {folder_key} 目录为空", execution_flow
                except Exception as e:
                    return f"无法访问 {folder_key} 目录: {str(e)}", execution_flow
    
    return "[文件操作] 请指定要查看的目录路径", execution_flow


@route_handler(
    'web_search',
    'Web Search Handler',
    'Handles web search and information lookup',
    # DEPRECATED: keywords should be determined by LLM, not hardcoded
    keywords=[],
    priority=3
)
async def web_search_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    tool = get_tool_logger("WebSearch")
    llm_logger = get_llm_logger("LLMProvider")
    tool_logger = get_tool_logger("WebTools")
    
    execution_flow = []
    should_log = _should_log(context)
    
    tool.info(f"（WebSearch） 收到搜索请求: {input_text[:30]}...")
    tool_logger.debug(f"（WebSearch） 准备执行搜索操作")
    execution_flow.append("🧠 [决策层] WebSearch 收到请求")
    
    skill_manager = context.get('skill_manager') if context else None
    llm_provider = context.get('llm_provider') if context else None
    
    if llm_provider:
        try:
            provider_name = llm_provider.__class__.__name__
            llm_logger.info(f"🤖 [LLM层] {provider_name} 准备进行意图理解和参数提取...")
            execution_flow.append(f"🧠 [决策层] {provider_name} 准备调用")
            
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

            if should_log:
                tool.info(f"（{provider_name}） 发送分析请求...")
            llm_response = await llm_provider.generate(prompt)
            
            if should_log:
                tool.info(f"🛠️ [工具层] {provider_name} 收到分析结果: {llm_response[:100]}...")
            execution_flow.append(f"🧠 [决策层] {provider_name} 意图分析完成")
            
            import json
            import re
            
            try:
                intent_data = json.loads(llm_response.strip())
                llm_logger.debug(f"🤖 [LLM层] LLM 分析结果解析成功: {intent_data}")
                
                intent = intent_data.get('intent', 'web_search')
                browser_name = intent_data.get('browser_name')
                search_engine = intent_data.get('search_engine', 'baidu')
                search_query = intent_data.get('search_query')
                open_url = intent_data.get('open_url')
                
                llm_logger.info(f"🤖 [LLM层] WebSearch LLM 分析: intent={intent}, browser={browser_name}, engine={search_engine}, query={search_query}")
                execution_flow.append(f"🧠 [决策层] {provider_name} 意图分析完成")
                
                if intent == 'browser_search' and skill_manager:
                    tool_logger.info(f"（WebTools） 执行浏览器搜索任务")
                    
                    if open_url:
                        url = open_url
                    elif search_query:
                        if search_engine == 'google':
                            url = f"https://www.google.com/search?q={search_query}"
                        else:
                            url = f"https://www.baidu.com/s?wd={search_query}"
                    else:
                        url = f"https://www.baidu.com"
                    
                    if should_log:
                        decision.info(f"WebTools 构建 URL: {url}")
                    result = await skill_manager.execute_skill('tool_open_browser', 
                                                              browser_name=browser_name, 
                                                              url=url)
                    
                    if result and result.success:
                        if should_log:
                            execution.info(f"WebTools open_browser 执行成功")
                        execution_flow.append("（WebTools） 打开浏览器成功")
                        return result.output, execution_flow
                    else:
                        if should_log:
                            tool.warning(f"（WebSearch） open_browser 执行失败: {result.error if result else 'Unknown'}")
                        execution_flow.append("（WebTools） open_browser 执行失败，尝试 fallback")
                elif search_query:
                    if search_engine == 'google':
                        url = f"https://www.google.com/search?q={search_query}"
                    else:
                        url = f"https://www.baidu.com/s?wd={search_query}"
                    
                    result = await skill_manager.execute_skill('tool_open_browser', 
                                                              browser_name=browser_name, 
                                                              url=url)
                    if result and result.success:
                        return result.output, execution_flow
                
            except (json.JSONDecodeError, KeyError) as e:
                llm_logger.warning(f"🤖 [LLM层] LLM 返回格式错误: {e}，尝试 fallback 到规则匹配")
                execution_flow.append(f"⚠️ [决策层] JSON 解析失败，fallback")
                
        except Exception as e:
            llm_logger.error(f"🤖 [LLM层] {provider_name} LLM 调用失败: {str(e)}")
            tool.error(f"（WebSearch） LLM 调用失败: {str(e)}")
    
    tool_logger.info(f"（SearchEngine） 使用规则匹配")
    execution_flow.append("🧠 [决策层] SearchEngine 使用规则匹配")
    
    import re
    query_match = re.search(r'search\s+([^\n]+)|搜索\s+([^\n]+)|查找\s+([^\n]+)|找一下\s+([^\n]+)', input_text)
    if query_match:
        query = query_match.group(1) or query_match.group(2) or query_match.group(3) or query_match.group(4)
    else:
        query = input_text.replace('search', '').replace('搜索', '').replace('查一下', '').strip()
    
    input_lower = input_text.lower()
    
    # 使用 LLM 判断是否需要打开浏览器（遵循规则）
    use_browser_tool = False
    if llm_provider:
        try:
            browser_intent_prompt = f"""用户输入："{input_text}"

判断用户是否想打开浏览器：
- true - 用户想打开浏览器
- false - 用户只是想搜索

只返回 JSON：{{"use_browser": true|false}}
"""
            
            browser_response = await llm_provider.generate(browser_intent_prompt)
            import re
            import json
            json_match = re.search(r'\{.*?"use_browser".*?\}', browser_response, re.DOTALL)
            
            if json_match:
                browser_data = json.loads(json_match.group(0))
                use_browser_tool = browser_data.get('use_browser', False)
        except Exception:
            pass
    
    if use_browser_tool and skill_manager:
        try:
            if should_log:
                execution.info(f"WebTools 检测到浏览器操作，尝试执行 tool_open_browser")
            execution_flow.append("（WebTools） 检测到浏览器请求")
            
            browser_name = None
            for browser in ['edge', 'chrome', 'firefox', 'brave', 'opera', 'vivaldi']:
                if browser in input_lower:
                    browser_name = browser
                    break
            
            patterns_to_remove = [
                r'帮我打开浏览器',
                r'用浏览器',
                r'用百度',
                r'帮我',
                r'打开',
                r'访问',
                r'去',
                r'到',
                r'搜索',
                r'查找',
                r'查一下',
                r'搜一下',
                r'browser',
                r'浏览器',
                r'打开(chrome|edge|firefox)',
                r'(chrome|edge|firefox)',
            ]
            
            search_text = input_text
            for pattern in patterns_to_remove:
                search_text = re.sub(pattern, '', search_text, flags=re.IGNORECASE)
            
            search_text = re.sub(r'[，。、？！，。；：""''（）【】《》,，、.。]+', ' ', search_text)
            search_text = re.sub(r'\s+', ' ', search_text).strip()
            
            if search_text:
                url = f"https://www.baidu.com/s?wd={search_text}"
            else:
                url = "https://www.baidu.com"
            
            result = await skill_manager.execute_skill('tool_open_browser', browser_name=browser_name, url=url)
            if result and result.success:
                execution.info(f"WebTools open_browser 执行成功")
                execution_flow.append("（） 打开浏览器成）功")
                return result.output, execution_flow
        except Exception as e:
            tool.warning(f"（WebSearch） open_browser 异常: {str(e)}")
    
    execution_flow.append("🧠 [决策层] SearchEngine 使用模板")
    import re
    query_match = re.search(r'search\s+([^\n]+)|搜索\s+([^\n]+)|查找\s+([^\n]+)|找一下\s+([^\n]+)', input_text)
    if query_match:
        query = query_match.group(1) or query_match.group(2) or query_match.group(3) or query_match.group(4)
    else:
        query = input_text.replace('search', '').replace('搜索', '').replace('查一下', '').strip()
    return f"[网络搜索] 搜索词：{query}\n\n请配置 LLM provider 或 web_search 技能来执行实际搜索。", execution_flow


@route_handler(
    'terminal_command',
    'Terminal Command Handler',
    'Handles terminal and command execution, app launching',
    # DEPRECATED: keywords should be determined by LLM, not hardcoded
    keywords=[],
    priority=4
)
async def terminal_command_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    tool = get_tool_logger("TerminalCommand")
    execution = get_execution_logger("TerminalTools")
    
    execution_flow = []
    should_log = _should_log(context)
    
    if should_log:
        tool.info(f"（TerminalCommand） 收到命令请求: {input_text[:30]}...")
        
    execution_flow.append("🧠 [决策层] TerminalCommand 收到请求")
    
    # 完全使用 LLM 来理解意图（遵循规则：意图理解必须用 LLM）
    llm_provider = context.get('llm_provider') if context else None
    command = None
    
    if llm_provider:
        try:
            if should_log:
                tool.info(f"（TerminalCommand） 使用 LLM 理解用户意图...")
            execution_flow.append("🧠 [决策层] 调用 LLM 理解意图")
            
            # LLM 判断用户是想执行命令还是查询历史
            import re
            import json
            
            intent_prompt = f"""你是一个智能助手。用户输入："{input_text}"

请判断用户的意图：
1. 如果用户想打开应用、执行命令、操作文件 -> type="execute"
2. 如果用户想查询之前做了什么、问历史 -> type="query"

只返回 JSON：
{{"type": "execute|query", "reasoning": "判断理由"}}
"""
            
            intent_response = await llm_provider.generate(intent_prompt)
            
            json_match = re.search(r'\{.*?"type".*?\}', intent_response, re.DOTALL)
            
            if json_match:
                intent_data = json.loads(json_match.group(0))
                intent_type = intent_data.get('type', 'execute')
                
                if should_log:
                    tool.info(f"（TerminalCommand） LLM 判断意图: {intent_type} - {intent_data.get('reasoning', '')}")
                execution_flow.append(f"🧠 [决策层] LLM 判断: {intent_type}")
                
                # 如果是查询意图，查询会话历史
                if intent_type == 'query':
                    session_history = context.get('session_history', [])
                    if session_history:
                        if should_log:
                            tool.info(f"（TerminalCommand） 查询会话历史...")
                        execution_flow.append("🧠 [决策层] 查询会话历史")
                        
                        recent_commands = []
                        for msg in reversed(session_history[-10:]):
                            if isinstance(msg, dict) and msg.get('role') == 'assistant':
                                content = msg.get('content', '')
                                if '执行成功' in content or '✅' in content or '成功打开' in content:
                                    recent_commands.append(content)
                        
                        if recent_commands:
                            query_prompt = f"""用户问：{input_text}
最近的执行记录：
{chr(10).join(recent_commands[:3])}

请根据执行记录回答用户的问题。如果执行成功，说明执行了什么。简洁回答。"""
                            
                            answer = await llm_provider.generate(query_prompt)
                            if should_log:
                                tool.info(f"（TerminalCommand） LLM 根据历史回答")
                            execution_flow.append("🧠 [决策层] 基于历史生成回答")
                            return answer, execution_flow
                        
                        return "我没有找到之前的命令执行记录。你可以让我打开某个应用或执行某个命令。", execution_flow
            
            # 如果 LLM 判断是执行意图，继续执行命令解析
            system_prompt = """你是一个命令解析器。根据用户输入，生成对应的 Windows 命令。
只返回 JSON，不要其他内容。
格式：{"action": "launch_app|open_folder|execute_command", "command": "实际命令", "app_name": "应用名（可选）"}

可用的操作：
- launch_app: 启动应用程序
- open_folder: 打开文件夹
- execute_command: 执行命令

常见应用的 Windows 命令：
- Chrome: start chrome
- Edge: start microsoft-edge:
- Firefox: start firefox
- IE: start iexplore
- Notepad: start notepad
- Calculator: start calc
- Explorer: start explorer
- 其他：直接用 start 命令

常见文件夹：
- 桌面: start explorer shell:desktop
- 文档: start explorer shell:personal
- 下载: start explorer shell:downloads
- 此电脑: start explorer shell:mycomputer

示例：
输入："帮我打开名字叫做ie的浏览器" -> {"action": "launch_app", "command": "start iexplore", "app_name": "IE浏览器"}
输入："打开计算器" -> {"action": "launch_app", "command": "start calc", "app_name": "计算器"}
输入："打开桌面" -> {"action": "open_folder", "command": "start explorer shell:desktop", "app_name": "桌面"}
输入："打开cmd" -> {"action": "execute_command", "command": "start cmd", "app_name": "命令提示符"}
"""
            
            response = await llm_provider.generate(f"{system_prompt}\n\n用户输入：{input_text}")
            
            # 提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                command = result.get('command')
                app_name = result.get('app_name', '')
                
                if should_log and command:
                    tool.info(f"（TerminalCommand） LLM 解析成功: 应用={app_name}, 命令={command}")
                execution_flow.append(f"🧠 [决策层] LLM 理解: {app_name}")
                
        except Exception as e:
            if should_log:
                tool.warning(f"（TerminalCommand） LLM 解析失败: {str(e)}")
            execution_flow.append("🧠 [决策层] LLM 失败")
    
    # 降级方案：如果 LLM 失败，返回错误而不是硬编码
    if not command:
        if llm_provider:
            # 再次尝试 LLM，简化 prompt
            try:
                if should_log:
                    tool.info(f"（TerminalCommand） 重试 LLM 解析...")
                
                retry_prompt = f"""用户输入："{input_text}"
提取要执行的命令或应用名称，生成 Windows 命令。
格式：{{"command": "命令", "app": "应用名"}}

常见格式：
- "打开X" -> start X
- "运行X" -> start X  
- 直接是程序名 -> start 程序名
"""
                
                retry_response = await llm_provider.generate(retry_prompt)
                json_match = re.search(r'\{.*\}', retry_response, re.DOTALL)
                
                if json_match:
                    result = json.loads(json_match.group(0))
                    command = result.get('command', input_text)
                    if should_log:
                        tool.info(f"（TerminalCommand） 重试成功: {command}")
            except Exception as e2:
                if should_log:
                    tool.warning(f"（TerminalCommand） 重试也失败: {str(e2)}")
        
        # 如果仍然没有命令，直接用输入作为命令（最后降级）
        if not command:
            command = input_text
    
    # 注意：不再使用硬编码的字典匹配，完全依赖 LLM 理解意图（遵循规则）
    
    # 直接使用 subprocess 执行命令（参考 Hermes Agent）
    try:
        if should_log:
            execution.info(f"（TerminalCommand） 直接执行命令: {command}")
        
        # 使用 cmd /c 执行 Windows 命令
        process = await asyncio.create_subprocess_shell(
            f'cmd /c {command}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=30
        )
        
        output = stdout.decode('utf-8', errors='replace').strip()
        error = stderr.decode('utf-8', errors='replace').strip()
        
        if process.returncode == 0:
            if should_log:
                execution.summary(f"（TerminalCommand） 执行成功")
            result_msg = f"✅ 命令执行成功"
            if output:
                result_msg += f"\n{output}"
            return result_msg, execution_flow
        else:
            if should_log:
                execution.error(f"（TerminalCommand） 执行失败: {error or '未知错误'}")
            return f"❌ 命令执行失败: {error or '未知错误'}", execution_flow
            
    except asyncio.TimeoutError:
        if should_log:
            execution.error(f"（TerminalCommand） 执行超时")
        return "❌ 命令执行超时（超过30秒）", execution_flow
    except Exception as e:
        if should_log:
            execution.error(f"🛠️ [工具层] TerminalCommand 执行异常: {str(e)}")
        return f"❌ 命令执行异常: {str(e)}", execution_flow


@route_handler(
    'general_question',
    'General Question Handler',
    'Handles general knowledge questions',
    # DEPRECATED: keywords should be determined by LLM, not hardcoded
    keywords=[],
    priority=2
)
async def general_question_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    llm = get_llm_logger("GeneralQuestion")
    
    execution_flow = []
    should_log = _should_log(context)
    
    if should_log:
        llm.info(f"🤖 [LLM层] GeneralQuestion 收到问题: {input_text[:30]}...")
        
    execution_flow.append("🧠 [决策层] GeneralQuestion 收到请求")
    
    llm_provider = context.get('llm_provider') if context else None
    
    if llm_provider:
        try:
            provider_name = llm_provider.__class__.__name__
            if should_log:
                llm.info(f"🤖 [LLM层] {provider_name} 准备回答问题...")
            execution_flow.append(f"🧠 [决策层] {provider_name} 准备调用")
            
            llm_logger = get_llm_logger("LLMProvider")
            llm_logger.debug(f"🤖 [LLM层] ┌─ 问题:")
            llm_logger.debug(f"🤖 [LLM层] │  {input_text}")
            llm_logger.debug(f"🤖 [LLM层] └─ 正在等待 LLM 响应...")
            
            response = await llm_provider.generate(input_text)
            
            if should_log:
                llm.summary(f"🤖 [LLM层] {provider_name} 回答成功")
            llm_logger.debug(f"🤖 [LLM层] ├─ 回答长度: {len(response)} 字符")
            llm_logger.debug(f"🤖 [LLM层] └─ 回答内容:\n{response[:300]}{'...' if len(response) > 300 else ''}")
            execution_flow.append(f"🧠 [决策层] {provider_name} 回答成功")
            
            return response, execution_flow
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            if should_log:
                llm.error(f"🤖 [LLM层] {provider_name} 回答失败: {error_type} - {error_msg}")
            execution_flow.append(f"❌ [决策层] {provider_name} 回答失败: {error_type}")
            
            user_message = f"❌ 回答失败\n\n错误类型: {error_type}\n错误信息: {error_msg[:100]}\n\n请检查：\n• 网络连接是否正常\n• API 服务是否可用"
            
            return user_message, execution_flow
    
    if should_log:
        llm.info(f"🤖 [LLM层] GeneralQuestion 使用内置知识库")
    execution_flow.append("🧠 [决策层] KnowledgeBase 使用内置知识")
    
    input_lower = input_text.lower()
    
    knowledge_base = {
        'python': 'Python 是一种高级编程语言，由 Guido van Rossum 创建。它以简洁的语法和强大的功能著称，广泛用于 Web 开发、数据科学、人工智能等领域。',
        'git': 'Git 是一个分布式版本控制系统，由 Linus Torvalds 创建。它用于跟踪代码变更、协作开发和版本管理。常用命令包括：git init, git add, git commit, git push, git pull。',
        'javascript': 'JavaScript 是一种脚本语言，最初用于网页交互。现在可用于前端（React、Vue）、后端（Node.js）、移动端（React Native）等全栈开发。',
        '什么是ai': '人工智能（AI）是研究使计算机能够模拟人类智能的学科，包括机器学习、深度学习，自然语言处理等分支。',
        '什么是machine learning': '机器学习是人工智能的一个分支，通过让计算机从数据中学习模式和规律，而不是依赖明确的编程指令。',
    }
    
    for key, answer in knowledge_base.items():
        if key in input_lower:
            if should_log:
                llm.info(f"🤖 [LLM层] GeneralQuestion 找到匹配知识: {key}")
            return f"[知识库回答]\n\n{answer}", execution_flow
    
    return "[知识库] 抱歉，知识库中没有找到相关答案。请配置 LLM provider 获取更全面的回答。", execution_flow


@route_handler(
    'task_management',
    'Task Management Handler',
    'Handles task/todo list operations like create, add, complete, list tasks',
    # DEPRECATED: keywords should be determined by LLM, not hardcoded
    keywords=[],
    priority=2
)
async def task_management_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    任务管理处理器
    处理创建、添加、完成、取消、删除、列出任务等操作
    """
    tool = get_tool_logger("TaskManagement")
    execution = get_execution_logger("TodoToolkit")
    
    execution_flow = []
    should_log = _should_log(context)
    
    tool.info(f"（TaskManager） 收到任务管理请求: {input_text[:30]}...")
    execution_flow.append("🧠 [决策层] TaskManagement 收到请求")
    
    from .todo_adapter import get_todo_adapter
    
    session_id = context.get('session_id', 'default') if context else 'default'
    llm_provider = context.get('llm_provider') if context else None
    
    try:
        adapter = get_todo_adapter(session_id)
        
        if should_log:
            execution.info(f"TodoToolkit 开始分析请求: {input_text[:30]}...")
        execution_flow.append("（TodoToolkit） 解析请求")
        
        # 使用 LLM 判断任务操作类型（遵循规则）
        if llm_provider:
            try:
                intent_prompt = f"""用户输入："{input_text}"

判断用户想做什么任务操作：
1. create - 创建新任务列表
2. add - 添加任务
3. complete - 完成任务
4. cancel - 取消任务
5. delete - 删除任务
6. list - 列出任务
7. reset - 重置任务
8. clear - 清空任务
9. unknown - 其他操作

只返回 JSON：{{"type": "操作类型", "confidence": 0.0-1.0}}
"""
                
                if should_log:
                    tool.info(f"（TaskManager） 使用 LLM 判断任务操作...")
                
                intent_response = await llm_provider.generate(intent_prompt)
                
                import re
                import json
                json_match = re.search(r'\{.*?"type".*?\}', intent_response, re.DOTALL)
                
                if json_match:
                    intent_data = json.loads(json_match.group(0))
                    intent_type = intent_data.get('type', 'list')
                    
                    if should_log:
                        tool.info(f"（TaskManager） LLM 判断: {intent_type}")
                    execution_flow.append(f"🧠 [决策层] LLM 判断: {intent_type}")
                    
                    # 根据 LLM 判断执行对应操作
                    if intent_type == 'create':
                        result = _handle_create_tasks(input_text, adapter, should_log)
                    elif intent_type == 'add':
                        result = _handle_add_task(input_text, adapter, should_log)
                    elif intent_type == 'complete':
                        result = _handle_complete_task(input_text, adapter, should_log)
                    elif intent_type == 'cancel':
                        result = _handle_cancel_task(input_text, adapter, should_log)
                    elif intent_type == 'delete':
                        result = _handle_remove_task(input_text, adapter, should_log)
                    elif intent_type == 'list':
                        result = _handle_list_tasks(adapter, should_log)
                    elif intent_type == 'reset':
                        result = _handle_reset_tasks(adapter, should_log)
                    elif intent_type == 'clear':
                        result = _handle_clear_tasks(adapter, should_log)
                    else:
                        result = _handle_list_tasks(adapter, should_log)
                    
                    if should_log:
                        execution.summary(f"（TaskManager） 执行完成")
                    
                    return result, execution_flow
                    
            except Exception as e:
                if should_log:
                    tool.warning(f"（TaskManager） LLM 判断失败: {str(e)}")
                execution_flow.append("🧠 [决策层] LLM 失败，使用列表作为默认")
        
        # 如果没有 LLM，默认列出任务
        result = _handle_list_tasks(adapter, should_log)
        
        if should_log:
            execution.summary(f"（TaskManager） 执行完成")
        
        return result, execution_flow
        
        if should_log:
            execution.summary(f"（TaskManager） 执行完成")
        
        return result, execution_flow
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        if should_log:
            execution.error(f"（TaskManager） 执行失败: {error_type} - {error_msg}")
        
        return f"❌ 任务管理失败\n\n错误类型: {error_type}\n错误信息: {error_msg[:100]}", execution_flow


def _handle_create_tasks(input_text: str, adapter, should_log: bool) -> str:
    """处理创建任务列表"""
    import re
    
    tasks = []
    
    numbered_pattern = r'(?:^|\n)\s*(\d+)[.、、]\s*(.+?)(?:\n|$)'
    matches = re.findall(numbered_pattern, input_text, re.MULTILINE)
    if matches:
        tasks = [task.strip() for _, task in matches]
    
    if not tasks:
        chinese_numbered_pattern = r'(?:^|[，。；、\n])\s*(\d+)\s*[.、.、　]+\s*(.+?)(?=[，。；、\n]|$)'
        matches = re.findall(chinese_numbered_pattern, input_text, re.MULTILINE)
        if matches:
            tasks = [task.strip() for _, task in matches]
    
    if not tasks:
        comma_separated_pattern = r'[:：]\s*(.+)'
        match = re.search(comma_separated_pattern, input_text)
        if match:
            after_colon = match.group(1)
            potential_tasks = re.split(r'[,，、\n]', after_colon)
            tasks = [t.strip() for t in potential_tasks if t.strip() and len(t.strip()) > 1]
    
    if not tasks:
        bullet_pattern = r'[-*]\s*(.+?)(?:\n|$)'
        matches = re.findall(bullet_pattern, input_text, re.MULTILINE)
        if matches:
            tasks = [task.strip() for task in matches]
    
    if not tasks:
        quote_pattern = r'[""\'](.+?)[""\']'
        matches = re.findall(quote_pattern, input_text)
        if matches:
            tasks = [task.strip() for task in matches]
    
    if not tasks:
        common_words = ['创建任务', '新建任务', '创建待办', 'create task', 'new task', 
                       'todo create', '创建', '新建', '设置', '如下', '这些']
        cleaned = input_text
        for word in common_words:
            cleaned = cleaned.replace(word, '')
        cleaned = re.sub(r'[，。、？！；：""''（）【】《》,，、.。]+', ' ', cleaned)
        cleaned = cleaned.strip()
        if cleaned:
            tasks = [t.strip() for t in re.split(r'[,，\n]', cleaned) if t.strip()]
    
    if not tasks:
        return "❌ 无法解析任务内容\n\n请按以下格式创建任务：\n- todo_create([\"任务1\", \"任务2\", \"任务3\"])\n- 1. 任务1\n  2. 任务2"
    
    from .todo_adapter import ToolCallResult
    result = adapter.call_tool('todo_create', {'tasks': tasks})
    
    if isinstance(result, ToolCallResult):
        return result.output if result.success else f"❌ {result.error}"
    return str(result)


def _handle_add_task(input_text: str, adapter, should_log: bool) -> str:
    """处理添加任务"""
    import re
    
    task_pattern = r'添加(?:任务|待办)[:：]?\s*[""\'"]?(.+?)[""\']?$'
    match = re.search(task_pattern, input_text)
    if match:
        task = match.group(1).strip()
    else:
        words_to_remove = ['添加任务', '新增任务', 'add task', '添加待办', '添加', '新增']
        cleaned = input_text
        for word in words_to_remove:
            cleaned = cleaned.replace(word, '')
        cleaned = re.sub(r'[，。、？！；：""''（）【】《》,，、.。]+', ' ', cleaned)
        task = cleaned.strip()
    
    if not task:
        return "❌ 未指定任务内容\n\n请说：添加任务 [任务描述]"
    
    from .todo_adapter import ToolCallResult
    result = adapter.call_tool('todo_add', {'task': task})
    
    if isinstance(result, ToolCallResult):
        return result.output if result.success else f"❌ {result.error}"
    return str(result)


def _handle_complete_task(input_text: str, adapter, should_log: bool) -> str:
    """处理完成任务"""
    import re
    
    task_id = None
    
    id_patterns = [
        r'#?(\d+)',
        r'第\s*(\d+)\s*个',
        r'任务\s*(\d+)',
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, input_text)
        if match:
            task_id = int(match.group(1))
            break
    
    if task_id is None:
        if '所有' in input_text or '全部' in input_text or 'all' in input_text.lower():
            list_result = adapter.call_tool('todo_list', {})
            from .todo_adapter import ToolCallResult
            if isinstance(list_result, ToolCallResult) and list_result.success:
                id_pattern = r'#(\d+)\.'
                ids = re.findall(id_pattern, list_result.output)
                if ids:
                    for tid in reversed(ids):
                        adapter.call_tool('todo_complete', {'task_id': int(tid), 'result': '批量完成'})
                    return "✅ 所有任务已完成！"
            return "❌ 没有可完成的任务"
        
        return "❌ 未指定任务ID\n\n请说：完成 #1 或 完成任务 1"
    
    from .todo_adapter import ToolCallResult
    result = adapter.call_tool('todo_complete', {'task_id': task_id})
    
    if isinstance(result, ToolCallResult):
        return result.output if result.success else f"❌ {result.error}"
    return str(result)


def _handle_cancel_task(input_text: str, adapter, should_log: bool) -> str:
    """处理取消任务"""
    import re
    
    task_id = None
    
    id_patterns = [
        r'#?(\d+)',
        r'第\s*(\d+)\s*个',
        r'任务\s*(\d+)',
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, input_text)
        if match:
            task_id = int(match.group(1))
            break
    
    if task_id is None:
        return "❌ 未指定任务ID\n\n请说：取消 #1 或 取消任务 1"
    
    from .todo_adapter import ToolCallResult
    result = adapter.call_tool('todo_cancel', {'task_id': task_id})
    
    if isinstance(result, ToolCallResult):
        return result.output if result.success else f"❌ {result.error}"
    return str(result)


def _handle_remove_task(input_text: str, adapter, should_log: bool) -> str:
    """处理删除任务"""
    import re
    
    task_id = None
    
    id_patterns = [
        r'#?(\d+)',
        r'第\s*(\d+)\s*个',
        r'任务\s*(\d+)',
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, input_text)
        if match:
            task_id = int(match.group(1))
            break
    
    if task_id is None:
        return "❌ 未指定任务ID\n\n请说：删除 #1 或 删除任务 1"
    
    from .todo_adapter import ToolCallResult
    result = adapter.call_tool('todo_remove', {'task_id': task_id})
    
    if isinstance(result, ToolCallResult):
        return result.output if result.success else f"❌ {result.error}"
    return str(result)


def _handle_list_tasks(adapter, should_log: bool) -> str:
    """处理列出任务"""
    from .todo_adapter import ToolCallResult
    result = adapter.call_tool('todo_list', {})
    
    if isinstance(result, ToolCallResult):
        if result.success:
            output = result.output
            if "暂无任务" in output:
                return "📋 **待办列表**\n\n目前没有任务列表。\n\n你可以：\n• 说「创建任务：任务1、任务2」来创建新列表\n• 说「添加任务 [描述]」来添加任务"
            return f"📋 **待办列表**\n\n{output}"
        else:
            return f"❌ {result.error}"
    return str(result)


def _handle_reset_tasks(adapter, should_log: bool) -> str:
    """处理重置任务"""
    from .todo_adapter import ToolCallResult
    result = adapter.call_tool('todo_reset', {})
    
    if isinstance(result, ToolCallResult):
        return result.output if result.success else f"❌ {result.error}"
    return str(result)


def _handle_clear_tasks(adapter, should_log: bool) -> str:
    """处理清空任务"""
    from .todo_adapter import ToolCallResult
    result = adapter.call_tool('todo_clear', {})
    
    if isinstance(result, ToolCallResult):
        return result.output if result.success else f"❌ {result.error}"
    return str(result)