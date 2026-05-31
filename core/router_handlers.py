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
    keywords=['时间', '现在几点', '几点了', '什么时间', '几点', 'date', '日期', '今天几号', '星期几'],
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
    keywords=['天气', '温度', '下雨', '晴天', '多云', 'weather', 'sunny', 'rain'],
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
    keywords=['hello', 'hi', '你好', 'bye', 'thanks', 'thank you', '上一句', '刚才', '之前', '历史', 'history'],
    priority=1
)
async def conversation_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    llm = get_llm_logger("ConversationHandler")
    llm_logger = get_llm_logger("LLMProvider")
    tool_logger = get_tool_logger("ConversationTools")
    
    execution_flow = []
    should_log = _should_log(context)
    
    input_lower = input_text.lower()
    
    time_keywords = ['时间', '现在几点', '几点了', '什么时间', '几点', '几点钟', 'date', '日期', '今天几号', '星期几']
    weather_keywords = ['天气', '温度', '下雨', '晴天', '多云', 'weather']
    
    # 问候语直接返回，不需要调用 LLM
    greeting_keywords = ['hello', 'hi', '你好', '嗨', 'good morning', 'good afternoon', '早上好', '下午好']
    if any(kw in input_lower for kw in greeting_keywords):
        if should_log:
            llm.info(f"🤖 [LLM层] ConversationHandler 检测到问候语")
        execution_flow.append("🧠 [决策层] 检测到问候语，直接返回")
        return "你好！我是你的智能助手。有什么我可以帮助你的吗？", execution_flow
    
    if any(kw in input_lower for kw in time_keywords):
        return await time_query_handler(input_text, context)
    
    if any(kw in input_lower for kw in weather_keywords):
        return await weather_query_handler(input_text, context)
    
    if should_log:
        llm.info(f"🤖 [LLM层] ConversationHandler 收到请求: {input_text[:30]}...")
    execution_flow.append("🧠 [决策层] ConversationHandler 收到请求")
    
    # 获取会话历史和 LLM provider
    session_history = context.get('session_history', []) if context else []
    llm_provider = context.get('llm_provider') if context else None
    
    # 检查是否是历史查询请求
    last_msg_keywords = ['上一句', '刚说的', '最后说了什么']
    history_keywords = ['聊了些什么', '聊什么', '历史', '刚才聊', '之前聊', '我们聊']
    
    is_last_msg_query = any(kw in input_lower for kw in last_msg_keywords)
    is_history_query = any(kw in input_lower for kw in history_keywords)
    
    if is_last_msg_query or is_history_query:
        if should_log:
            llm.info(f"🤖 [LLM层] ConversationHandler 检测到历史查询请求")
        execution_flow.append("🧠 [决策层] 检测到历史查询请求")
        
        if session_history:
            # 查找所有用户消息
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
            
            if is_history_query and llm_provider:
                # 调用 LLM 总结对话历史
                try:
                    provider_name = llm_provider.__class__.__name__
                    if should_log:
                        llm.info(f"🤖 [LLM层] {provider_name} 准备总结对话历史...")
                    execution_flow.append(f"🧠 [DR层] {provider_name} 准备总结对话")
                    
                    # 构建对话历史摘要
                    history_text = "以下是我们的对话历史：\n\n"
                    for i, (user_msg, assistant_msg) in enumerate(zip(user_messages, assistant_messages), 1):
                        history_text += f"用户：{user_msg}\n"
                        if assistant_msg:
                            history_text += f"我：{assistant_msg}\n"
                        history_text += "\n"
                    
                    prompt = f"{history_text}\n\n请简要总结我们刚才聊了什么内容，用中文回答。"
                    
                    response = await llm_provider.generate(prompt)
                    
                    if should_log:
                        llm.info(f"🤖 [LLM层] {provider_name} 总结完成")
                    execution_flow.append(f"🧠 [决策层] {provider_name} 总结完成")
                    
                    return f"📝 我们刚才的对话总结：\n\n{response}", execution_flow
                except Exception as e:
                    if should_log:
                        llm.error(f"🤖 [LLM层] 总结对话失败: {str(e)}")
            
            elif is_last_msg_query and user_messages:
                # 返回上一条消息
                last_user_msg = user_messages[-1] if user_messages else ""
                response = f"📝 你上一条消息是：\n\n{last_user_msg}"
                return response, execution_flow
            elif user_messages:
                # 没有 LLM 但有历史，返回简要摘要
                history_text = "📝 我们最近的对话：\n\n"
                for i, (user_msg, assistant_msg) in enumerate(zip(user_messages[-5:], assistant_messages[-5:]), 1):
                    history_text += f"• 你：{user_msg[:100]}{'...' if len(user_msg) > 100 else ''}\n"
                    if assistant_msg:
                        history_text += f"  我：{assistant_msg[:100]}{'...' if len(assistant_msg) > 100 else ''}\n"
                    history_text += "\n"
                return history_text, execution_flow
            else:
                return "抱歉，我还没有记录到你之前的消息。", execution_flow
        else:
            return "抱歉，我还没有记录到我们之前的对话内容。", execution_flow
    
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
    
    greetings = ['hello', 'hi', '你好', '嗨', 'how are you', 'good morning']
    farewells = ['bye', 'goodbye', '再见', 'see you']
    
    if any(g in input_lower for g in greetings):
        return "你好！很高兴见到你！有什么技术问题我可以帮助你解答吗？", execution_flow
    elif any(f in input_lower for f in farewells):
        return "再见！祝你有美好的一天！", execution_flow
    else:
        return "我明白你说的。我可以帮你处理各种任务，比如：\n- 回答问题\n- 执行终端命令\n- 文件操作\n- 代码相关任务\n\n请问有什么我可以帮助你的吗？", execution_flow


@route_handler(
    'coding_assistant',
    'Coding Assistant Handler',
    'Handles coding-related queries and code generation',
    keywords=['python', 'code', 'function', 'program', 'debug', 'syntax', 'class', 'def ', 'import', '写代码', '帮我写', '编程'],
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
    keywords=['file', 'read', 'write', 'save', 'delete', 'create file', 'open file', 'list', '目录', '文件'],
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
    tool_logger.debug(f"（FileManager） 准备执行文件操作...")
    execution_flow.append("（FileManager） 准备执行")
    
    # 先检查是否是特殊文件夹操作（桌面、文档、下载等）
    folder_name_mapping = {
        '桌面': 'desktop',
        'desktop': 'desktop',
        'documents': 'documents',
        '文档': 'documents',
        'downloads': 'downloads',
        '下载': 'downloads',
        'pictures': 'pictures',
        '图片': 'pictures',
        'photos': 'pictures',
        'photo': 'pictures',
        'music': 'music',
        '音乐': 'music',
        'videos': 'videos',
        '视频': 'videos',
        'movies': 'videos',
        'home': 'home',
    }
    
    for name, folder_key in folder_name_mapping.items():
        if name in input_lower:
            target_path = env_detector.get_folder_path(folder_key)
            if target_path:
                if should_log:
                    execution.info(f"FileManager 列出目录: {target_path}")
                execution_flow.append(f"（FileManager） 列出 {target_path}")
                
                try:
                    files = os.listdir(target_path)
                    if files:
                        file_list = "\n".join([f"  • {f}" for f in files[:50]])
                        return f"📁 {name} 目录内容:\n\n{file_list}\n\n共 {len(files)} 个文件/文件夹", execution_flow
                    else:
                        return f"📁 {name} 目录为空", execution_flow
                except Exception as e:
                    return f"无法访问 {name} 目录: {str(e)}", execution_flow
    
    # 检查是否是读取文件操作
    if any(kw in input_lower for kw in ['read', '读取', '打开文件', 'cat ', 'type ']):
        if should_log:
            execution.info(f"FileManager 识别为读取文件操作")
        import re
        match = re.search(r'[\'"](.+?)[\'"]|read\s+(\S+)|读取\s+(\S+)|打开\s+(\S+)', input_text)
        if match:
            file_path = match.group(1) or match.group(2) or match.group(3) or match.group(4)
            if file_path:
                if should_log:
                    execution.info(f"FileManager 读取文件: {file_path}")
                execution_flow.append(f"（FileManager） 读取 {file_path}")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(3000)
                        return f"📄 文件内容 ({file_path}):\n\n{content}", execution_flow
                except Exception as e:
                    return f"无法读取文件 {file_path}: {str(e)}", execution_flow
        return "请指定要读取的文件路径，例如：读取文件 /path/to/file.py", execution_flow
    
    # 检查是否是写入文件操作
    elif any(kw in input_lower for kw in ['write', '创建', '新建', '写入', '创建文件']):
        if should_log:
            execution.info(f"FileManager 识别为写入文件操作")
        return "[文件写入] 请使用更具体的文件操作技能来写入文件。", execution_flow
    
    # 检查是否是列出文件操作
    elif any(kw in input_lower for kw in ['list', '列出', 'ls', 'dir', '有哪些', '什么', '查看', '浏览', '显示']):
            if should_log:
                execution.info(f"FileManager 识别为列出文件操作")
            
            import re
            path_match = re.search(r'目录\s+(\S+)|folder\s+(\S+)|路径\s+(\S+)', input_text)
            if path_match:
                target_path = path_match.group(1) or path_match.group(2) or path_match.group(3)
                if target_path:
                    try:
                        files = os.listdir(target_path)
                        if files:
                            file_list = "\n".join([f"  • {f}" for f in files[:50]])
                            return f"📁 目录内容 ({target_path}):\n\n{file_list}\n\n共 {len(files)} 个文件/文件夹", execution_flow
                        else:
                            return f"📁 目录为空", execution_flow
                    except Exception as e:
                        return f"无法访问目录 {target_path}: {str(e)}", execution_flow
    
    # 默认情况：无法识别操作类型
    if should_log:
        execution.info(f"FileManager 无法识别具体操作")
    return f"[文件操作] 无法识别操作类型。请使用：\n- 读取文件 /path/to/file\n- 写入文件 /path/to/file\n- 列出文件 /path/to/dir\n- 查看桌面文件", execution_flow


@route_handler(
    'web_search',
    'Web Search Handler',
    'Handles web search and information lookup',
    keywords=['search', 'google', 'web', 'find', '查一下', '搜索', '帮我找', '搜一下', '帮我搜索'],
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
    
    use_browser_tool = any(keyword in input_lower for keyword in ['browser', '浏览器', 'chrome', 'edge', 'firefox', '打开浏览器', '打开chrome', '打开edge'])
    
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
    keywords=['run', 'execute', 'terminal', 'command', 'bash', 'npm', 'pip', 'git', '运行', '执行', '打开', 'open', '启动', 'launch', 'browser', 'chrome', '浏览器'],
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
    
    command_mapping = {
        'chrome': 'start "" "https://www.google.com"',
        'browser': 'start "" "https://www.google.com"',
        '打开浏览器': 'start "" "https://www.google.com"',
        '打开chrome': 'start "" "https://www.google.com"',
        'edge': 'start microsoft-edge:',
        '打开edge': 'start microsoft-edge:',
        'firefox': 'start firefox',
        'safari': 'start safari',
        'notepad': 'start notepad',
        '记事本': 'start notepad',
        'calc': 'start calc',
        '计算器': 'start calc',
        'explorer': 'start explorer',
        '资源管理器': 'start explorer',
    }
    
    folder_mapping = {
        '桌面': 'start explorer shell:desktop',
        'desktop': 'start explorer shell:desktop',
        '我的电脑': 'start explorer shell:mycomputer',
        '此电脑': 'start explorer shell:mycomputer',
        '文档': 'start explorer shell:personal',
        'documents': 'start explorer shell:personal',
        '下载': 'start explorer shell:downloads',
        'downloads': 'start explorer shell:downloads',
        '图片': 'start explorer shell:photos',
        'Pictures': 'start explorer shell:photos',
        '音乐': 'start explorer shell:music',
        'music': 'start explorer shell:music',
        '视频': 'start explorer shell:video',
        'videos': 'start explorer shell:video',
    }
    
    command = input_text
    input_lower = input_text.lower()
    
    use_browser_tool = any(keyword in input_lower for keyword in ['browser', '浏览器', '打开浏览器', 'chrome', 'edge', 'firefox'])
    
    for key, cmd in command_mapping.items():
        if key in input_lower:
            command = cmd
            if should_log:
                tool.info(f"（TerminalCommand） 识别到命令: {cmd}")
            break
    
    if command == input_text:
        for key, cmd in folder_mapping.items():
            if key in input_lower:
                command = cmd
                if should_log:
                    tool.info(f"（TerminalCommand） 识别到文件夹: {cmd}")
                break
    
    skill_manager = context.get('skill_manager') if context else None
    
    if skill_manager and use_browser_tool:
        try:
            if should_log:
                execution.info(f"TerminalTools 尝试执行 tool_open_browser 技能")
            execution_flow.append("（TerminalTools） 准备执行")
            
            browser_name = None
            for browser in ['edge', 'chrome', 'firefox', 'brave', 'opera', 'vivaldi']:
                if browser in input_lower:
                    browser_name = browser
                    break
            
            import re
            url = None
            url_patterns = [
                r'https?://[^\s]+',
                r'www\.[^\s]+',
                r'[a-zA-Z0-9]+\.(com|cn|org|net|io|co)[^\s]*',
            ]
            for pattern in url_patterns:
                match = re.search(pattern, input_text)
                if match:
                    url = match.group(0)
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    break
            
            if url:
                if should_log:
                    execution.info(f"识别到 URL: {url}")
                    tool.info(f"（TerminalCommand） 识别到网址: {url}")
            
            result = await skill_manager.execute_skill('tool_open_browser', browser_name=browser_name, url=url)
            if result and result.success:
                if should_log:
                    execution.info(f"TerminalTools open_browser 执行成功")
                execution_flow.append("（TerminalTools） 执行成功")
                return result.output, execution_flow
            else:
                if should_log:
                    tool.warning(f"（TerminalCommand） open_browser 执行失败，尝试 fallback")
                execution_flow.append("（WebTools） open_browser 执行失败，fallback")
        except Exception as e:
            if should_log:
                tool.warning(f"（TerminalCommand） open_browser 异常: {str(e)}，尝试 fallback")
    
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
    keywords=['what', 'who', 'how', 'why', 'explain', 'tell me', '什么是', '如何', '为什么'],
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
    keywords=['任务', 'todo', 'task', '待办', '清单', '列表', '添加任务', '完成', '完成任务', 
              '新建任务', '创建任务', '任务列表', '待办事项', '添加待办', 'complete', 
              'finish', 'done', 'cancel', '删除任务', '列出任务', '有哪些任务', 
              '还有几个', '待办列表', '任务管理'],
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
    
    try:
        adapter = get_todo_adapter(session_id)
        
        input_lower = input_text.lower()
        
        if should_log:
            execution.info(f"TodoToolkit 开始分析请求: {input_text[:30]}...")
        execution_flow.append("（TodoToolkit） 解析请求")
        
        if any(kw in input_lower for kw in ['创建任务', '新建任务', '创建待办', 'create task', 'new task', 'todo create']):
            result = _handle_create_tasks(input_text, adapter, should_log)
        elif any(kw in input_lower for kw in ['添加任务', '新增任务', 'add task', '添加待办', '添加一个新任务']):
            result = _handle_add_task(input_text, adapter, should_log)
        elif any(kw in input_lower for kw in ['完成任务', '完成', 'complete', 'finish', 'done', '完成 #']):
            result = _handle_complete_task(input_text, adapter, should_log)
        elif any(kw in input_lower for kw in ['取消', 'cancel', '取消任务', '取消待办']):
            result = _handle_cancel_task(input_text, adapter, should_log)
        elif any(kw in input_lower for kw in ['删除任务', 'remove', 'delete', '删除']):
            result = _handle_remove_task(input_text, adapter, should_log)
        elif any(kw in input_lower for kw in ['列出任务', '查看任务', '列表', '有哪些任务', '待办列表', 'todo list', 'list task', '显示任务', '列出']):
            result = _handle_list_tasks(adapter, should_log)
        elif any(kw in input_lower for kw in ['重置任务', 'reset']):
            result = _handle_reset_tasks(adapter, should_log)
        elif any(kw in input_lower for kw in ['清空任务', 'clear']):
            result = _handle_clear_tasks(adapter, should_log)
        elif any(kw in input_lower for kw in ['任务', 'todo', 'task', '待办', '清单']):
            result = _handle_list_tasks(adapter, should_log)
        else:
            result = _handle_list_tasks(adapter, should_log)
        
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