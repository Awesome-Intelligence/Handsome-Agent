#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Handsome Agent Core Implementation
Inspired by Hermes Agent Architecture

Three-layer architecture: Access / Decision / Execution

DEPRECATED: This module uses the old intent-based architecture.
Please migrate to the new LLM-driven architecture.
See: core/llm_tool_selector.py and docs/MIGRATION_GUIDE.md
"""

import os
import sys
import json
import time
import logging
import warnings
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio

from pydantic import BaseModel, Field

from .exceptions import (
    AgentError,
    InputValidationError, 
    ResponseGenerationError,
    ConfigurationError,
    TimeoutError
)
from .cache import LRUCache, create_cache_key, hash_config
from .skill_manager import skill_manager, SkillResult, BaseSkill
from .session import session_manager, Session, Message
from .i18n import I18n
from .logging_manager import (
    get_access_logger,
    get_decision_logger,
    get_execution_logger,
    get_llm_logger,
    get_tool_logger,
    set_log_level
)
from .response_router import ResponseStrategyRouter, ResponseStrategy


warnings.warn(
    "This module uses the deprecated intent-based architecture. "
    "Please migrate to core/llm_tool_selector.py. "
    "See docs/MIGRATION_GUIDE.md for instructions.",
    DeprecationWarning,
    stacklevel=2
)


class AgentConfig(BaseModel):
    """Agent configuration using Pydantic for validation."""
    name: str = "CustomAgent"
    version: str = "1.0.0"
    explanation_depth: str = "detailed"
    response_format: str = "structured" 
    language: str = "zh"
    enable_caching: bool = True
    max_response_length: int = 4000
    timeout_seconds: float = 30.0
    enable_routing: bool = True
    enable_skills: bool = True
    enable_session: bool = True
    
    enable_task_planning: bool = True
    task_complexity_threshold: int = 2
    
    enable_advanced_reasoning: bool = True
    
    supported_languages: List[str] = ["zh", "en", "ja", "ko"]
    
    log_level: str = "info"
    enable_detailed_logs: bool = True
    enable_summary_logs: bool = True
    
    class Config:
        extra = "allow"


@dataclass
class AgentResponse:
    """Response from the agent."""
    content: str
    reasoning_steps: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    error_code: int = 0


class BaseAgentModule(ABC):
    """Base class for agent modules."""
    
    __slots__ = ('config', 'logger')
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.propagate = False
    
    @abstractmethod
    async def process(self, input_data: Any, session: Optional[Session] = None) -> AgentResponse:
        """Process input and return response."""
        pass


class ExplanationModule(BaseAgentModule):
    """Module for generating explanations."""
    
    __slots__ = ('_logger',)
    
    def __init__(self, config=None):
        super().__init__(config)
        from .logging_manager import get_postprocess_logger
        self._logger = get_postprocess_logger("ExplanationModule")
    
    async def process(self, input_data: Any, session: Optional[Session] = None) -> AgentResponse:
        """Generate explanation for the response."""
        self._logger.debug(f"ExplanationModule processing: {input_data}")
        
        return AgentResponse(
            content=str(input_data),
            reasoning_steps=["Generated explanation"]
        )


class CustomAgent:
    """
    Custom Agent - DEPRECATED.
    
    WARNING: This class uses the deprecated intent-based architecture.
    Please migrate to the new LLM-driven architecture.
    
    Migration guide: See docs/MIGRATION_GUIDE.md
    """
    
    __slots__ = (
        'config', 'explanation_module',
        '_access_logger', '_cache_logger', '_memory_logger',
        '_router_logger', '_tool_select_logger', '_session_logger',
        '_postprocess_logger', '_execution_logger', '_cache', '_config_hash',
        '_session', '_router',
        'llm_provider', '_i18n', '_task_planner', '_advanced_reasoning_module',
        '_strategy_router'
    )
    
    def __init__(self, config: Optional[AgentConfig] = None, session_id: Optional[str] = None):
        warnings.warn(
            "CustomAgent is deprecated. Please use the new architecture from "
            "core/llm_tool_selector.py or core/simplified_agent.py",
            DeprecationWarning,
            stacklevel=2
        )

        self.config = config or AgentConfig()
        self.explanation_module = ExplanationModule(self.config)
        self._i18n = I18n(self.config.language)
        self.setup_logging()

        from .logging_manager import (
            get_access_logger, get_execution_logger,
            get_memory_logger, get_postprocess_logger, get_decision_logger
        )

        self._access_logger = get_access_logger("InputHandler")
        self._cache_logger = get_execution_logger("MemoryCache")
        self._memory_logger = get_memory_logger("MemoryRetrieval")
        self._router_logger = get_decision_logger("TaskRouter")
        self._tool_select_logger = get_decision_logger("ToolSelector")
        self._session_logger = get_execution_logger("SessionManager")
        self._postprocess_logger = get_postprocess_logger("PostProcessor")
        self._execution_logger = get_execution_logger("ExecutionLayer")

        skill_manager.set_explanation_depth(self.config.explanation_depth)

        # 初始化路由器 - 使用全局 router 实例
        self._router = None
        if self.config.enable_routing:
            try:
                from .router import router
                self._router = router
                self._router_logger.info(f"TaskRouter initialized with {len(router.routes)} handlers")
            except Exception as e:
                self._router_logger.error(f"Failed to load router: {e}")

        if self.config.enable_caching:
            self._cache = LRUCache(maxsize=100)
            self._config_hash = hash_config(self.config)
        else:
            self._cache = None
            self._config_hash = None

        if self.config.enable_session:
            session_manager._enable_detailed_logs = self.config.enable_detailed_logs
            self._session = session_manager.create_session(
                session_id,
                enable_detailed_logs=self.config.enable_detailed_logs
            )
        else:
            self._session = None

        self.llm_provider = None
        self._task_planner = None
        self._advanced_reasoning_module = None
        self._strategy_router = None
    
    def setup_logging(self):
        """Setup logging configuration."""
        if self.config.log_level:
            level = getattr(logging, self.config.log_level.upper(), logging.INFO)
            logging.root.setLevel(level)
    
    def set_llm_provider(self, provider):
        """Set the LLM provider."""
        self.llm_provider = provider
        
        if self.config.enable_advanced_reasoning:
            try:
                from .advanced_reasoning.integration import AdvancedReasoningModule
                self._advanced_reasoning_module = AdvancedReasoningModule(provider)
            except ImportError:
                self._advanced_reasoning_module = None
        
        if self.config.enable_task_planning:
            try:
                from .task_planner import TaskPlanner
                self._task_planner = TaskPlanner(provider)
            except ImportError:
                self._task_planner = None
    
    async def chat(self, user_input: str) -> AgentResponse:
        """
        Process user input and generate response.

        DEPRECATED: This method uses the old intent-based architecture.
        Please migrate to the new LLM-driven architecture.
        """
        warnings.warn(
            "The chat() method uses the deprecated intent-based architecture. "
            "Please migrate to the new LLM-driven decision engine. "
            "See docs/MIGRATION_GUIDE.md",
            DeprecationWarning,
            stacklevel=2
        )

        if not user_input or not user_input.strip():
            return AgentResponse(
                content="Please provide input.",
                error_code=400
            )

        if self._session:
            self._session.add_message('user', user_input)

        # 尝试使用路由器
        if self._router:
            self._router_logger.info(f"Routing request: {user_input[:50]}...")
            self._execution_logger.info(f"[执行层] 收到请求: {user_input[:30]}...")

            try:
                # 构建路由上下文
                context = {
                    'session_id': self._session.session_id if self._session else None,
                    'llm_provider': self.llm_provider,
                    'skill_manager': skill_manager,
                    'session_history': self._session.messages if self._session else [],
                    'enable_detailed_logs': self.config.enable_detailed_logs
                }

                # 执行路由
                route_match = self._router.route(user_input)

                if route_match:
                    self._router_logger.info(
                        f"Routed to {route_match.route_id} "
                        f"(confidence: {route_match.confidence:.2f})"
                    )
                    self._execution_logger.info(f"[执行层] 路由到: {route_match.route_id}")

                    # 执行处理器
                    if asyncio.iscoroutinefunction(route_match.handler):
                        response_text, execution_flow = await route_match.handler(
                            user_input,
                            context
                        )
                    else:
                        # 同步处理器
                        response_text, execution_flow = route_match.handler(
                            user_input,
                            context
                        )

                    # 记录执行流程
                    for step in execution_flow:
                        self._execution_logger.debug(f"  {step}")

                    if self._session:
                        self._session.add_message('assistant', response_text)
                        self._session._save_session()

                    return AgentResponse(
                        content=response_text,
                        reasoning_steps=execution_flow,
                        confidence_score=route_match.confidence
                    )

            except Exception as e:
                self._router_logger.error(f"Routing failed: {e}")
                self._execution_logger.error(f"[执行层] 路由失败: {e}")
                # 继续使用 LLM 作为 fallback

        # 如果没有路由器或路由失败，使用 LLM
        if not self.llm_provider:
            return AgentResponse(
                content="LLM provider not configured and no router handler matched.",
                error_code=500
            )

        try:
            self._router_logger.info("No route matched, using LLM directly")
            self._execution_logger.info("[执行层] 使用 LLM 直接响应")

            response_text = await self.llm_provider.generate(user_input)

            if self._session:
                self._session.add_message('assistant', response_text)
                self._session._save_session()

            return AgentResponse(
                content=response_text,
                confidence_score=1.0
            )

        except Exception as e:
            self._router_logger.error(f"LLM generation failed: {e}")
            return AgentResponse(
                content=f"Error: {str(e)}",
                error_code=500
            )
    
    async def process(self, user_input: str) -> AgentResponse:
        """
        Process user input (alias for chat).

        DEPRECATED: Use the new architecture instead.
        """
        warnings.warn(
            "process() is deprecated. Use chat() or migrate to the new architecture.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self.chat(user_input)

    async def respond(self, user_input: str) -> AgentResponse:
        """
        Respond to user input (alias for chat).

        DEPRECATED: This method is deprecated. Please use the new LLM-driven
        architecture from core.llm_tool_selector instead.

        Args:
            user_input: User input string

        Returns:
            AgentResponse: Response from the agent
        """
        warnings.warn(
            "respond() is deprecated. Please use the new LLM-driven architecture "
            "from core.llm_tool_selector instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self.chat(user_input)
