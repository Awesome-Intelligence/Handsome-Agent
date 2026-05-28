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

from .layer_logger import get_layer_logger


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
        self._control_logger = get_layer_logger("control", "TaskRouter")
        self._intent_logger = get_layer_logger("control", "IntentClassifier")
        self._enable_detailed_logs = True  # Default value, will be set by agent
    
    def set_detailed_logs(self, enabled: bool):
        """Set whether to print detailed logs."""
        self._enable_detailed_logs = enabled
        self.intent_classifier.enable_detailed_logs = enabled
    
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
            if self._enable_detailed_logs:
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
            if self._enable_detailed_logs:
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
    """
    
    INTENT_KEYWORDS = {
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
    
    INTENT_DESCRIPTIONS = """
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
    
    def __init__(self, llm_provider=None, mode: str = "llm", threshold: float = 0.3, language: str = "zh", enable_detailed_logs: bool = True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._ctrl_logger = get_layer_logger("control", "IntentClassifier")
        self.llm_provider = llm_provider
        self.mode = mode  # keyword, llm, hybrid (default: llm for smart intent classification)
        self.threshold = threshold  # Confidence threshold for hybrid mode
        self.language = language  # zh, en, ja, ko
        self.enable_detailed_logs = enable_detailed_logs  # Control detailed logging
    
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
        else:  # hybrid mode
            return self._classify_hybrid(input_text)
    
    def _classify_keyword_only(self, input_text: str) -> str:
        """Keyword-only intent classification."""
        keyword_intent, confidence = self._keyword_classify(input_text)
        if self.enable_detailed_logs:
            self._ctrl_logger.info(f"关键词分类: {keyword_intent} (置信度: {confidence:.2f})")
        return keyword_intent
    
    def _classify_llm_only(self, input_text: str) -> str:
        """LLM-only intent classification."""
        if self.llm_provider:
            llm_intent = self._llm_classify(input_text)
            if llm_intent:
                if self.enable_detailed_logs:
                    self._ctrl_logger.info(f"LLM 分类: {llm_intent}")
                return llm_intent
        if self.enable_detailed_logs:
            self._ctrl_logger.warning("LLM not available, falling back to keyword classification")
        return self._classify_keyword_only(input_text)
    
    def _classify_hybrid(self, input_text: str) -> str:
        """Hybrid intent classification (keyword + LLM fallback)."""
        keyword_intent, confidence = self._keyword_classify(input_text)
        
        if confidence >= self.threshold:
            if self.enable_detailed_logs:
                self._ctrl_logger.info(f"关键词分类: {keyword_intent} (置信度: {confidence:.2f})")
            return keyword_intent
        
        if self.llm_provider:
            llm_intent = self._llm_classify(input_text)
            if llm_intent:
                if self.enable_detailed_logs:
                    self._ctrl_logger.info(f"LLM 分类: {llm_intent}")
                return llm_intent
        
        if self.enable_detailed_logs:
            self._ctrl_logger.info(f"关键词分类 (低置信度): {keyword_intent}")
        return keyword_intent
    
    async def classify_async(self, input_text: str) -> str:
        """Async version of classify with LLM assistance."""
        if self.mode == "keyword":
            return self._classify_keyword_only(input_text)
        elif self.mode == "llm":
            return await self._classify_llm_only_async(input_text)
        else:  # hybrid mode
            return await self._classify_hybrid_async(input_text)
    
    async def _classify_llm_only_async(self, input_text: str) -> str:
        """Async LLM-only intent classification."""
        if self.llm_provider:
            llm_intent = await self._llm_classify_async(input_text)
            if llm_intent:
                if self.enable_detailed_logs:
                    self._ctrl_logger.info(f"LLM 分类: {llm_intent}")
                return llm_intent
        if self.enable_detailed_logs:
            self._ctrl_logger.warning("LLM not available, falling back to keyword classification")
        return self._classify_keyword_only(input_text)
    
    async def _classify_hybrid_async(self, input_text: str) -> str:
        """Async hybrid intent classification."""
        keyword_intent, confidence = self._keyword_classify(input_text)
        
        if confidence >= self.threshold:
            if self.enable_detailed_logs:
                self._ctrl_logger.info(f"关键词分类: {keyword_intent} (置信度: {confidence:.2f})")
            return keyword_intent
        
        if self.llm_provider:
            llm_intent = await self._llm_classify_async(input_text)
            if llm_intent:
                if self.enable_detailed_logs:
                    self._ctrl_logger.info(f"LLM 分类: {llm_intent}")
                return llm_intent
        
        if self.enable_detailed_logs:
            self._ctrl_logger.info(f"关键词分类 (低置信度): {keyword_intent}")
        return keyword_intent
    
    def _keyword_classify(self, input_text: str) -> Tuple[str, float]:
        """Keyword-based intent classification with confidence score."""
        input_lower = input_text.lower()
        scores = {}
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in input_lower)
            # Weighted by number of keywords
            score = matches / max(len(keywords), 1)
            scores[intent] = score
        
        if not scores or max(scores.values()) == 0:
            return 'conversation', 0.0
        
        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent]
        
        return best_intent, confidence
    
    async def _llm_classify_async(self, input_text: str) -> Optional[str]:
        """LLM-assisted intent classification."""
        if not self.llm_provider:
            return None
        
        prompt = f"""Classify the following user input into one of these intents:
{self.INTENT_DESCRIPTIONS}

User input: "{input_text}"

Respond with only the intent name (e.g., "conversation", "coding", "terminal").
If the input is a command to open or run something on the computer, classify as "terminal".
If unsure, respond with "conversation"."""
        
        try:
            response = await self.llm_provider.generate(prompt)
            response = response.strip().lower()
            
            # Validate response
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
