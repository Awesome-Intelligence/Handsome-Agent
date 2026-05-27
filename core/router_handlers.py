#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Router Handlers Module.

Contains all route handlers for the TaskRouter.
Inspired by Hermes Agent's route handlers.
"""

from typing import Dict, List, Tuple, Any
import json

from .router import router, route_handler, RouteMatch
from .layer_logger import get_layer_logger


@route_handler(
    'conversation',
    'Conversation Handler',
    'Handles general conversation and greetings',
    keywords=['hello', 'hi', '你好', 'bye', 'thanks', 'thank you'],
    intent_types=['conversation'],
    priority=1
)
async def conversation_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    decision = get_layer_logger("decision", "ConversationHandler")
    
    execution_flow = []
    
    decision.info(f"conversation_handler 收到请求: {input_text[:30]}...")
    decision.info(f"   → 下一步将调用: LLMProvider.generate()")
    execution_flow.append("🧠 [决策层] ConversationHandler 收到请求")
    
    llm_provider = context.get('llm_provider') if context else None
    
    if llm_provider:
        try:
            provider_name = llm_provider.__class__.__name__
            decision.info(f"{provider_name} 准备调用大模型...")
            decision.info(f"   → 下一步将调用: {provider_name}.generate()")
            execution_flow.append(f"🧠 [决策层] {provider_name} 准备调用")
            
            response = await llm_provider.generate(input_text)
            
            decision.info(f"{provider_name} 大模型返回成功 (响应长度: {len(response)} 字符)")
            decision.info(f"ConversationHandler 收到 LLM 返回")
            execution_flow.append(f"🧠 [决策层] {provider_name} 大模型返回成功")
            
            return response, execution_flow
        except Exception as e:
            decision.error(f"{provider_name} 大模型调用失败: {str(e)}")
            execution_flow.append(f"❌ [决策层] 大模型调用失败: {str(e)}")
            return f"抱歉，服务暂时不可用。", execution_flow
    
    decision.info(f"TemplateEngine 使用模板响应")
    execution_flow.append("🧠 [决策层] TemplateEngine 使用模板")
    
    greetings = ['hello', 'hi', '你好', '嗨', 'how are you', 'good morning']
    farewells = ['bye', 'goodbye', '再见', 'see you']
    
    input_lower = input_text.lower()
    
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
    intent_types=['coding'],
    priority=3
)
async def coding_assistant_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    decision = get_layer_logger("decision", "CodingAssistant")
    
    execution_flow = []
    
    decision.info(f"CodingAssistant 收到编程请求: {input_text[:30]}...")
    decision.info(f"   → 下一步将调用: LLMProvider.generate()")
    execution_flow.append("🧠 [决策层] CodingAssistant 收到请求")
    
    llm_provider = context.get('llm_provider') if context else None
    
    if llm_provider:
        try:
            provider_name = llm_provider.__class__.__name__
            decision.info(f"{provider_name} 准备生成代码...")
            decision.info(f"   → 下一步将调用: {provider_name}.generate()")
            execution_flow.append(f"🧠 [决策层] {provider_name} 准备调用")
            
            prompt = f"请用代码解决以下问题，代码要完整可运行：\n{input_text}"
            response = await llm_provider.generate(prompt)
            
            decision.info(f"{provider_name} 代码生成成功 (响应长度: {len(response)} 字符)")
            execution_flow.append(f"🧠 [决策层] {provider_name} 代码生成成功")
            
            return response, execution_flow
        except Exception as e:
            decision.error(f"{provider_name} 代码生成失败: {str(e)}")
            execution_flow.append(f"❌ [决策层] 代码生成失败: {str(e)}")
            return f"抱歉，代码生成遇到问题：{str(e)}", execution_flow
    
    decision.info(f"CodeAnalyzer 使用模板响应")
    execution_flow.append("🧠 [决策层] CodeAnalyzer 使用模板")
    return "请配置 LLM provider 以启用代码助手功能。", execution_flow


@route_handler(
    'file_operations',
    'File Operations Handler',
    'Handles file reading, writing, and management',
    keywords=['file', 'read', 'write', 'save', 'delete', 'create file', 'open file', 'list', '目录', '文件'],
    intent_types=['file_operation'],
    priority=4
)
async def file_operations_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    decision = get_layer_logger("decision", "FileOperations")
    execution = get_layer_logger("execution", "FileManager")
    
    execution_flow = []
    
    decision.info(f"FileOperations 收到文件操作请求: {input_text[:30]}...")
    decision.info(f"   → 下一步将调用: SkillManager")
    execution_flow.append("🧠 [决策层] FileOperations 收到请求")
    
    skill_manager = context.get('skill_manager') if context else None
    
    if skill_manager:
        execution.info(f"FileManager 准备执行文件操作...")
        execution_flow.append("⚡ [执行层] FileManager 准备执行")
        
        input_lower = input_text.lower()
        
        if any(kw in input_lower for kw in ['read', '查看', '打开', '看']):
            execution.info(f"FileManager 识别为读取文件操作")
            import re
            match = re.search(r'[\'"](.+?)[\'"]|read\s+(\S+)', input_text)
            if match:
                file_path = match.group(1) or match.group(2)
                execution.info(f"FileManager 读取文件: {file_path}")
                execution_flow.append(f"⚡ [执行层] FileManager 读取 {file_path}")
                return f"[文件读取] 读取文件: {file_path}\n\n请配置 LLM provider 来执行实际的文件操作。", execution_flow
            return "请指定要读取的文件路径，例如：读取文件 /path/to/file.py", execution_flow
        
        elif any(kw in input_lower for kw in ['write', '创建', '新建', '写入']):
            execution.info(f"FileManager 识别为写入文件操作")
            return "[文件写入] 请使用更具体的文件操作技能来写入文件。", execution_flow
        
        elif any(kw in input_lower for kw in ['list', '列出', 'ls', 'dir']):
            execution.info(f"FileManager 识别为列出文件操作")
            return "[文件列表] 请使用 ls 或 list 命令查看目录内容。", execution_flow
        
        else:
            execution.info(f"FileManager 无法识别具体操作")
            return f"[文件操作] 无法识别操作类型。请使用：\n- 读取文件 /path/to/file\n- 写入文件 /path/to/file\n- 列出文件 /path/to/dir", execution_flow
    
    decision.info(f"FileAnalyzer 无 SkillManager")
    execution_flow.append("🧠 [决策层] FileAnalyzer 无法处理")
    return "文件操作功能未配置，请先配置 SkillManager。", execution_flow


@route_handler(
    'web_search',
    'Web Search Handler',
    'Handles web search and information lookup',
    keywords=['search', 'google', 'web', 'find', '查一下', '搜索', '帮我找', '搜一下', '帮我搜索'],
    intent_types=['web_search'],
    priority=3
)
async def web_search_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    decision = get_layer_logger("decision", "WebSearch")
    execution = get_layer_logger("execution", "WebTools")
    
    execution_flow = []
    
    decision.info(f"WebSearch 收到搜索请求: {input_text[:30]}...")
    decision.info(f"   → 下一步将调用: WebTools 或 LLM")
    execution_flow.append("🧠 [决策层] WebSearch 收到请求")
    
    skill_manager = context.get('skill_manager') if context else None
    llm_provider = context.get('llm_provider') if context else None
    
    if llm_provider:
        try:
            provider_name = llm_provider.__class__.__name__
            decision.info(f"{provider_name} 准备进行意图理解和参数提取...")
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

            decision.info(f"{provider_name} 发送分析请求...")
            llm_response = await llm_provider.generate(prompt)
            
            decision.info(f"{provider_name} 收到分析结果: {llm_response[:100]}...")
            execution_flow.append(f"🧠 [决策层] {provider_name} 意图分析完成")
            
            import json
            import re
            
            try:
                intent_data = json.loads(llm_response.strip())
                decision.info(f"LLM 分析结果解析成功: {intent_data}")
                
                intent = intent_data.get('intent', 'web_search')
                browser_name = intent_data.get('browser_name')
                search_engine = intent_data.get('search_engine', 'baidu')
                search_query = intent_data.get('search_query')
                open_url = intent_data.get('open_url')
                
                decision.info(f"WebSearch LLM 分析: intent={intent}, browser={browser_name}, engine={search_engine}, query={search_query}")
                
                if intent == 'browser_search' and skill_manager:
                    execution.info(f"WebTools 执行浏览器搜索任务")
                    execution_flow.append("⚡ [执行层] WebTools 准备执行")
                    
                    if open_url:
                        url = open_url
                    elif search_query:
                        if search_engine == 'google':
                            url = f"https://www.google.com/search?q={search_query}"
                        else:
                            url = f"https://www.baidu.com/s?wd={search_query}"
                    else:
                        url = f"https://www.baidu.com"
                    
                    decision.info(f"WebTools 构建 URL: {url}")
                    result = await skill_manager.execute_skill('tool_open_browser', 
                                                              browser_name=browser_name, 
                                                              url=url)
                    
                    if result and result.success:
                        execution.info(f"WebTools open_browser 执行成功")
                        execution_flow.append("⚡ [执行层] WebTools 打开浏览器成功")
                        return result.output, execution_flow
                    else:
                        decision.warning(f"WebTools open_browser 执行失败: {result.error if result else 'Unknown'}")
                        execution_flow.append("⚡ [执行层] open_browser 执行失败，尝试 fallback")
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
                decision.warning(f"LLM 返回格式错误: {e}，尝试 fallback 到规则匹配")
                execution_flow.append(f"⚠️ [决策层] JSON 解析失败，fallback")
                
        except Exception as e:
            decision.error(f"{provider_name} LLM 调用失败: {str(e)}")
            execution_flow.append(f"❌ [决策层] LLM 调用失败: {str(e)}")
    
    decision.info(f"SearchEngine 使用规则匹配")
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
            execution.info(f"WebTools 检测到浏览器操作，尝试执行 tool_open_browser")
            execution_flow.append("⚡ [执行层] WebTools 检测到浏览器请求")
            
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
                execution_flow.append("⚡ [执行层] WebTools 打开浏览器成功")
                return result.output, execution_flow
        except Exception as e:
            decision.warning(f"WebTools open_browser 异常: {str(e)}")
    
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
    intent_types=['terminal'],
    priority=4
)
async def terminal_command_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    decision = get_layer_logger("decision", "TerminalCommand")
    execution = get_layer_logger("execution", "TerminalTools")
    
    execution_flow = []
    
    decision.info(f"TerminalCommand 收到命令请求: {input_text[:30]}...")
    decision.info(f"   → 下一步将调用: SkillManager")
    execution_flow.append("🧠 [决策层] TerminalCommand 收到请求")
    
    command_mapping = {
        'chrome': 'start chrome',
        'browser': 'start chrome',
        '打开浏览器': 'start chrome',
        '打开chrome': 'start chrome',
        'edge': 'start msedge',
        '打开edge': 'start msedge',
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
            decision.info(f"CommandAnalyzer 识别到命令: {cmd}")
            break
    
    if command == input_text:
        for key, cmd in folder_mapping.items():
            if key in input_lower:
                command = cmd
                decision.info(f"CommandAnalyzer 识别到文件夹: {cmd}")
                break
    
    skill_manager = context.get('skill_manager') if context else None
    
    if skill_manager and use_browser_tool:
        try:
            execution.info(f"TerminalTools 尝试执行 tool_open_browser 技能")
            execution_flow.append("⚡ [执行层] TerminalTools 准备执行")
            
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
                execution.info(f"识别到 URL: {url}")
                decision.info(f"TerminalCommand 识别到网址: {url}")
            
            result = await skill_manager.execute_skill('tool_open_browser', browser_name=browser_name, url=url)
            if result and result.success:
                execution.info(f"TerminalTools open_browser 执行成功")
                execution_flow.append("⚡ [执行层] TerminalTools 执行成功")
                return result.output, execution_flow
            else:
                decision.warning(f"TerminalTools open_browser 执行失败，尝试 fallback")
                execution_flow.append("⚡ [执行层] open_browser 执行失败，fallback")
        except Exception as e:
            decision.warning(f"TerminalTools open_browser 异常: {str(e)}，尝试 fallback")
    
    if skill_manager:
        try:
            execution.info(f"TerminalTools 尝试执行 tool_terminal 技能")
            execution_flow.append("⚡ [执行层] TerminalTools 准备执行")
            result = await skill_manager.execute_skill('tool_terminal', command=command)
            if result and result.success:
                execution.info(f"TerminalTools 执行成功")
                execution_flow.append("⚡ [执行层] TerminalTools 执行成功")
                return result.output, execution_flow
        except Exception as e:
            decision.error(f"TerminalTools 执行失败: {str(e)}")
            return f"命令执行失败：{str(e)}", execution_flow
    
    decision.info(f"CommandAnalyzer 使用模板响应")
    execution_flow.append("🧠 [决策层] CommandAnalyzer 使用模板")
    return f"[终端命令] 将执行: {command}", execution_flow


@route_handler(
    'general_question',
    'General Question Handler',
    'Handles general knowledge questions',
    keywords=['what', 'who', 'how', 'why', 'explain', 'tell me', '什么是', '如何', '为什么'],
    intent_types=['question'],
    priority=2
)
async def general_question_handler(input_text: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    decision = get_layer_logger("decision", "GeneralQuestion")
    
    execution_flow = []
    
    decision.info(f"GeneralQuestion 收到问题: {input_text[:30]}...")
    decision.info(f"   → 下一步将调用: LLMProvider")
    execution_flow.append("🧠 [决策层] GeneralQuestion 收到请求")
    
    llm_provider = context.get('llm_provider') if context else None
    
    if llm_provider:
        try:
            provider_name = llm_provider.__class__.__name__
            decision.info(f"{provider_name} 准备回答问题...")
            decision.info(f"   → 下一步将调用: {provider_name}.generate()")
            execution_flow.append(f"🧠 [决策层] {provider_name} 准备调用")
            
            response = await llm_provider.generate(input_text)
            
            decision.info(f"{provider_name} 回答成功 (响应长度: {len(response)} 字符)")
            execution_flow.append(f"🧠 [决策层] {provider_name} 回答成功")
            
            return response, execution_flow
        except Exception as e:
            decision.error(f"{provider_name} 回答失败: {str(e)}")
            execution_flow.append(f"❌ [决策层] 回答失败: {str(e)}")
            return f"抱歉，回答遇到问题：{str(e)}", execution_flow
    
    decision.info(f"KnowledgeBase 使用内置知识库")
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
            decision.info(f"KnowledgeBase 找到匹配知识: {key}")
            return f"[知识库回答]\n\n{answer}", execution_flow
    
    return "[知识库] 抱歉，知识库中没有找到相关答案。请配置 LLM provider 获取更全面的回答。", execution_flow