#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Router Module - Inspired by Hermes Agent's routing system.

This module provides task routing and intent classification.
Features:
- Keyword-based intent classification
- LLM-assisted intent classification
- Multi-route matching with confidence scores
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum


class IntentType(Enum):
    """Supported intent types."""
    CONVERSATION = "conversation"
    QUESTION = "question"
    WEATHER = "weather"
    TIME_QUERY = "time_query"
    CODING = "coding"
    FILE_OPERATION = "file_operation"
    WEB_SEARCH = "web_search"
    TERMINAL = "terminal"
    CREATION = "creation"
    ANALYSIS = "analysis"
    CONFIGURATION = "configuration"


@dataclass
class RouteConfig:
    """Configuration for a route."""
    id: str
    name: str
    description: str
    handler: Callable
    keywords: List[str] = field(default_factory=list)
    intent_types: List[str] = field(default_factory=list)
    priority: int = 1


@dataclass
class RouteMatch:
    """Result of route matching."""
    route_id: str
    handler: Callable
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)


def route_handler(route_id: str, name: str, description: str, keywords: List[str] = None,
                  intent_types: List[str] = None, priority: int = 1):
    """Decorator to register a route handler."""
    def decorator(func: Callable) -> Callable:
        config = RouteConfig(
            id=route_id,
            name=name,
            description=description,
            handler=func,
            keywords=keywords or [],
            intent_types=intent_types or [],
            priority=priority
        )
        router.register_route(config)
        return func
    return decorator


class TaskRouter:
    """
    Intelligent task router that matches user input to appropriate handlers.
    
    Features:
    - Intent classification with confidence scores
    - Keyword and semantic matching
    - Priority-based route selection
    - LLM-assisted classification (optional)
    """
    
    def __init__(self):
        self.routes: List[RouteConfig] = []
        self.intent_classifier = IntentClassifier()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.propagate = False
    
    def register_route(self, config: RouteConfig):
        """Register a route configuration."""
        self.routes.append(config)
        self.routes.sort(key=lambda x: -x.priority)
        self.logger.info(f"Registered route: {config.id} (priority: {config.priority})")
    
    def route(self, input_text: str, intent: str = None) -> Optional[RouteMatch]:
        """Route input to appropriate handler (sync wrapper)."""
        if not intent:
            intent = self.intent_classifier.classify(input_text)
        
        matches = self._find_matches(input_text, intent)
        
        if matches:
            best_match = matches[0]
            self.logger.info(f"Routing to {best_match.route_id} with confidence {best_match.confidence:.2f}")
            return best_match
        return None
    
    async def route_async(self, input_text: str, intent: str = None) -> Optional[RouteMatch]:
        """Route input to appropriate handler (async version)."""
        if not intent:
            intent = await self.intent_classifier.classify_async(input_text)
        
        matches = self._find_matches(input_text, intent)
        
        if matches:
            best_match = matches[0]
            self.logger.info(f"Routing to {best_match.route_id} with confidence {best_match.confidence:.2f}")
            return best_match
        return None
    
    def _find_matches(self, input_text: str, intent: str) -> List[RouteMatch]:
        """Find all matching routes."""
        matches = []
        input_lower = input_text.lower()
        
        for route in self.routes:
            confidence = 0.0
            
            if intent in route.intent_types:
                confidence += 0.4
            
            keyword_matches = sum(1 for kw in route.keywords if kw.lower() in input_lower)
            if route.keywords:
                confidence += keyword_matches / len(route.keywords) * 0.4
            
            if confidence > 0.1:
                matches.append(RouteMatch(
                    route_id=route.id,
                    handler=route.handler,
                    confidence=confidence,
                    context={"intent": intent, "route": route.name}
                ))
        
        matches.sort(key=lambda x: -x.confidence)
        return matches
    
    def list_routes(self) -> List[RouteConfig]:
        return self.routes


class IntentClassifier:
    """
    Intent classifier with both keyword and LLM-assisted classification.
    
    Classification flow:
    1. Try keyword matching first (fast)
    2. If uncertain, try LLM classification (if available)
    3. Fall back to default intent
    
    Supports loading keywords from YAML config file.
    """
    
    DEFAULT_INTENT_KEYWORDS = {
        'conversation': [
            'hello', 'hi', '你好', '嗨', 'how are you', 'good morning',
            'thanks', 'thank you', 'bye', 'goodbye', 'see you', 'morning', 'evening'
        ],
        'question': [
            'what', 'who', 'when', 'where', 'why', 'how', 'explain',
            'difference', 'compare', 'define', 'meaning', 'is there', 'tell me'
        ],
        'weather': [
            '天气', 'weather', '温度', 'temperature', '下雨', 'rain', '晴天', 'sunny',
            '多云', 'cloudy', '风', 'wind', '气候', 'climate', ' forecast', '预报'
        ],
        'time_query': [
            '时间', '现在几点', '几点了', '什么时间', '几点', 'date', '日期', '今天几号',
            '星期几', 'month', 'year', '年', '月', '日', '几点钟'
        ],
        'coding': [
            'code', 'python', 'function', 'program', 'debug', 'error', 'bug',
            'implement', 'write', 'fix', 'compile', 'syntax', 'class', 'method',
            'import', 'variable', 'loop', 'if else', 'def ', 'return', 'print'
        ],
        'file_operation': [
            'file', 'read', 'write', 'save', 'delete', 'create file', 'open file',
            'list files', 'directory', 'folder', 'path', 'list',
            '桌面', 'documents', 'downloads', '图片', '音乐', '视频', '文档', '下载',
            '查看', '看看', '浏览', '显示', '有哪些', '哪些', '内容', '目录',
            '打开文件夹', 'open folder'
        ],
        'web_search': [
            'search', 'google', 'bing', 'web', 'internet', 'online', 'find',
            'lookup', '查一下', '搜索', '搜一下', '帮我找', '帮我搜索'
        ],
        'terminal': [
            'run', 'execute', 'terminal', 'command', 'shell', 'bash', 'cmd',
            '运行', '执行', '命令', '终端', '命令行', 'npm', 'pip', 'git',
            '打开', 'open', '启动', 'start', 'launch',
            'browser', 'chrome', 'edge', 'firefox', 'safari', '浏览器',
            'notepad', '记事本', 'calc', '计算器', 'explorer', '资源管理器'
        ],
        'creation': [
            'create', 'build', 'make', 'generate', 'design', 'develop', '新建'
        ],
        'analysis': [
            'analyze', 'analyze this', 'explain this', 'review', 'optimize', '检查'
        ],
        'configuration': [
            'setup', 'config', 'configure', 'settings', 'preferences', '设置', '配置'
        ]
    }
    
    INTENTS_LIST = """
    Available intents:
    - conversation: Greetings, farewells, casual chat
    - question: Asking questions, seeking explanations
    - weather: Weather queries, temperature, forecasts
    - time_query: Time, date, current moment inquiries
    - coding: Programming, debugging, code-related tasks
    - file_operation: Reading, writing, managing files
    - web_search: Searching the internet, looking up information
    - terminal: Running commands, opening apps, system operations
    - creation: Creating new content, building things
    - analysis: Analyzing, reviewing, optimizing
    - configuration: Setting up, configuring, preferences
    """
    
    def __init__(self, llm_provider=None, mode: str = None, threshold: float = 0.3, language: str = "zh", enable_detailed_logs: bool = None, config_path: str = "config/intents.yaml"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.propagate = False
        self.logger.setLevel(logging.root.level)
        
        self._constructor_mode = mode
        self._constructor_detailed_logs = enable_detailed_logs
        
        self.mode = mode if mode is not None else "llm"
        self.threshold = threshold
        self.language = language
        self.enable_detailed_logs = enable_detailed_logs if enable_detailed_logs is not None else True
        self.llm_provider = llm_provider
        
        self.INTENT_KEYWORDS = self.DEFAULT_INTENT_KEYWORDS
        self.INTENT_DESCRIPTIONS = self.INTENTS_LIST
        self.llm_prompt_template = None
        
        self._load_config(config_path)
    
    def set_llm_provider(self, provider):
        """Set the LLM provider for assisted classification."""
        self.llm_provider = provider
    
    def set_mode(self, mode: str):
        """Set intent classification mode."""
        if mode in ["keyword", "llm", "hybrid"]:
            self.mode = mode
        else:
            self.logger.warning(f"Invalid intent mode: {mode}, defaulting to hybrid")
            self.mode = "hybrid"
    
    def set_language(self, language: str):
        """Set the language for intent classification."""
        if language in ["zh", "en", "ja", "ko"]:
            self.language = language
        else:
            self.logger.warning(f"Unsupported language: {language}, defaulting to zh")
            self.language = "zh"
    
    def _load_config(self, config_path: str):
        """从 YAML 配置文件加载意图关键词和配置"""
        try:
            import yaml
            import os
            
            if not os.path.exists(config_path):
                self.logger.warning(f"配置文件不存在: {config_path}，使用默认关键词")
                self.INTENT_KEYWORDS = self.DEFAULT_INTENT_KEYWORDS
                self.INTENT_DESCRIPTIONS = self.INTENTS_LIST
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if 'intents' in config:
                self.INTENT_KEYWORDS = {}
                self._intent_priorities = {}
                for intent_name, intent_config in config['intents'].items():
                    if isinstance(intent_config, dict) and 'keywords' in intent_config:
                        self.INTENT_KEYWORDS[intent_name] = intent_config['keywords']
                        self._intent_priorities[intent_name] = intent_config.get('priority', float('inf'))
                    elif isinstance(intent_config, list):
                        self.INTENT_KEYWORDS[intent_name] = intent_config
                        self._intent_priorities[intent_name] = float('inf')
                
                self.logger.info(f"从配置文件加载了 {len(self.INTENT_KEYWORDS)} 个意图的关键词")
            else:
                self.INTENT_KEYWORDS = self.DEFAULT_INTENT_KEYWORDS
                self._intent_priorities = {intent: i+1 for i, intent in enumerate(self.DEFAULT_INTENT_KEYWORDS.keys())}
            
            if 'intent_classification' in config:
                ic_config = config['intent_classification']
                
                if 'mode' in ic_config and self._constructor_mode is None:
                    self.mode = ic_config['mode']
                    self.logger.info(f"意图识别模式: {self.mode}")
                
                if 'confidence_threshold' in ic_config:
                    self.threshold = ic_config['confidence_threshold']
                    self.logger.info(f"置信度阈值: {self.threshold}")
                
                if 'enable_detailed_logs' in ic_config and self._constructor_detailed_logs is None:
                    self.enable_detailed_logs = ic_config['enable_detailed_logs']
                
                if 'default_language' in ic_config:
                    self.language = ic_config['default_language']
                
                if 'llm_prompt_template' in ic_config:
                    self.llm_prompt_template = ic_config['llm_prompt_template']
            
            self.logger.info(f"成功加载意图识别配置: {config_path}")
            
        except ImportError:
            self.logger.warning("PyYAML 未安装，使用默认关键词")
            self.INTENT_KEYWORDS = self.DEFAULT_INTENT_KEYWORDS
            self.INTENT_DESCRIPTIONS = self.INTENTS_LIST
        except Exception as e:
            self.logger.error(f"加载意图配置失败: {e}，使用默认配置")
            self.INTENT_KEYWORDS = self.DEFAULT_INTENT_KEYWORDS
            self.INTENT_DESCRIPTIONS = self.INTENTS_LIST
    
    def classify(self, input_text: str) -> str:
        """
        Classify user intent based on the configured mode.
        
        Args:
            input_text: User input text
            
        Returns:
            Intent type string
        """
        if self.mode == "keyword":
            return self._classify_keyword_only(input_text)
        elif self.mode == "llm":
            return self._classify_llm_only(input_text)
        else:
            return self._classify_hybrid(input_text)
    
    def _classify_keyword_only(self, input_text: str) -> str:
        """Keyword-only intent classification."""
        keyword_intent, confidence = self._keyword_classify(input_text)
        self.logger.debug(f"关键词分类: {keyword_intent} (置信度: {confidence:.2f})")
        return keyword_intent
    
    def _classify_llm_only(self, input_text: str) -> str:
        """LLM-only intent classification (with keyword fallback)."""
        if self.llm_provider:
            try:
                llm_intent = self._llm_classify(input_text)
                if llm_intent:
                    self.logger.info(f"🤖 LLM 分类成功: {llm_intent}")
                    return llm_intent
                else:
                    self.logger.warning("⚠️ LLM 返回无效结果，fallback 到关键词分类")
            except Exception as e:
                self.logger.warning(f"⚠️ LLM 调用失败: {e}，fallback 到关键词分类")
        
        self.logger.info("📝 使用关键词分类（LLM 不可用）")
        return self._classify_keyword_only(input_text)
    
    def _classify_hybrid(self, input_text: str) -> str:
        """Hybrid intent classification (keyword first, then LLM)."""
        keyword_intent, confidence = self._keyword_classify(input_text)
        
        if confidence >= self.threshold:
            self.logger.info(f"📝 关键词分类: {keyword_intent} (置信度: {confidence:.2f})")
            return keyword_intent
        
        if self.llm_provider:
            try:
                llm_intent = self._llm_classify(input_text)
                if llm_intent:
                    self.logger.info(f"🤖 LLM 分类: {llm_intent}")
                    return llm_intent
            except Exception as e:
                self.logger.warning(f"⚠️ LLM 调用失败: {e}")
        
        self.logger.info(f"📝 关键词分类 (低置信度): {keyword_intent} (置信度: {confidence:.2f})")
        return keyword_intent
    
    async def classify_async(self, input_text: str) -> str:
        """Async version of classify with LLM assistance."""
        if self.mode == "keyword":
            return self._classify_keyword_only(input_text)
        elif self.mode == "llm":
            return await self._classify_llm_only_async(input_text)
        else:
            return await self._classify_hybrid_async(input_text)
    
    async def _classify_llm_only_async(self, input_text: str) -> str:
        """Async LLM-only intent classification (with keyword fallback)."""
        if self.llm_provider:
            try:
                llm_intent = await self._llm_classify_async(input_text)
                if llm_intent:
                    self.logger.info(f"🤖 LLM 分类成功: {llm_intent}")
                    return llm_intent
                else:
                    self.logger.warning("⚠️ LLM 返回无效结果，fallback 到关键词分类")
            except Exception as e:
                self.logger.warning(f"⚠️ LLM 调用失败: {e}，fallback 到关键词分类")
        
        self.logger.info("📝 使用关键词分类（LLM 不可用）")
        return self._classify_keyword_only(input_text)
    
    async def _classify_hybrid_async(self, input_text: str) -> str:
        """Async hybrid intent classification (keyword first, then LLM)."""
        keyword_intent, confidence = self._keyword_classify(input_text)
        
        if confidence >= self.threshold:
            self.logger.info(f"📝 关键词分类: {keyword_intent} (置信度: {confidence:.2f})")
            return keyword_intent
        
        if self.llm_provider:
            try:
                llm_intent = await self._llm_classify_async(input_text)
                if llm_intent:
                    self.logger.info(f"🤖 LLM 分类: {llm_intent}")
                    return llm_intent
            except Exception as e:
                self.logger.warning(f"⚠️ LLM 调用失败: {e}")
        
        self.logger.info(f"📝 关键词分类 (低置信度): {keyword_intent} (置信度: {confidence:.2f})")
        return keyword_intent
    
    def _keyword_classify(self, input_text: str) -> Tuple[str, float]:
        """Keyword-based intent classification with confidence score."""
        input_lower = input_text.lower()
        scores = {}
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            total_weight = 0.0
            matched_count = 0
            for kw in keywords:
                if kw in input_lower:
                    weight = 1.0 + len(kw) / 10.0
                    total_weight += weight
                    matched_count += 1
            
            if matched_count > 0:
                input_length = len(input_lower)
                score = total_weight / max(input_length, len(max(keywords, key=len)))
                score = min(max(score, 0.0), 1.0)
                score = min(score * (1 + matched_count * 0.05), 1.0)
            else:
                score = 0.0
            
            scores[intent] = score
        
        if not scores or max(scores.values()) == 0:
            return 'conversation', 0.0
        
        max_score = max(scores.values())
        
        best_intent = None
        best_priority = float('inf')
        for intent, score in scores.items():
            if score == max_score:
                priority = self._intent_priorities.get(intent, float('inf'))
                if priority < best_priority:
                    best_priority = priority
                    best_intent = intent
        
        confidence = scores[best_intent]
        
        return best_intent, confidence
    
    async def _llm_classify_async(self, input_text: str) -> Optional[str]:
        """LLM-assisted intent classification."""
        if not self.llm_provider:
            return None
        
        if self.llm_prompt_template:
            prompt = self.llm_prompt_template.format(
                intents_list=self.INTENT_DESCRIPTIONS,
                user_input=input_text
            )
        else:
            prompt = f"""Classify the following user input into one of these intents:
{self.INTENT_DESCRIPTIONS}

User input: "{input_text}"

Respond with only the intent name (e.g., "conversation", "coding", "terminal").
If the input is a command to open or run something on the computer, classify as "terminal".
If unsure, respond with "conversation"."""
        
        try:
            response = await self.llm_provider.generate(prompt)
            response = response.strip().lower()
            
            valid_intents = list(self.INTENT_KEYWORDS.keys())
            for intent in valid_intents:
                if intent in response:
                    return intent
            
            return None
        except Exception as e:
            self.logger.warning(f"LLM classification failed: {e}")
            return None
    
    def _llm_classify(self, input_text: str) -> Optional[str]:
        """Synchronous wrapper for LLM classification."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._llm_classify_async(input_text))
        except Exception:
            return None


router = TaskRouter()


def _import_handlers():
    """Import all route handlers after router is initialized."""
    from . import router_handlers
    return router_handlers


_handlers = None

def get_handlers():
    """Get route handlers module."""
    global _handlers
    if _handlers is None:
        _handlers = _import_handlers()
    return _handlers


try:
    _handlers = _import_handlers()
except ImportError as e:
    pass