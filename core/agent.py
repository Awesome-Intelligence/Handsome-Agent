#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Handsome Agent Core Implementation
Inspired by Hermes Agent Architecture

This module implements the foundational architecture for the Handsome Agent,
including configuration management, response structuring, and task routing.
Three-layer architecture: Access / Decision / Execution
"""

import os
import sys
import json
import time
import logging
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
from .router import router, RouteMatch, IntentClassifier
from .skill_manager import skill_manager, SkillResult, BaseSkill
from .session import session_manager, Session, Message
from .i18n import I18n
from .layer_logger import get_layer_logger


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
    
    class Config:
        extra = "allow"


@dataclass
class AgentResponse:
    content: str
    reasoning_steps: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    error_code: int = 0


class BaseAgentModule(ABC):
    __slots__ = ('config', 'logger')
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def process(self, input_data: Any, session: Optional[Session] = None) -> AgentResponse:
        pass


class ExplanationModule(BaseAgentModule):
    __slots__ = ()
    
    async def process(self, input_data: str, session: Optional[Session] = None) -> AgentResponse:
        start_time = time.time()
        input_type = self._classify_input(input_data)
        complexity_level = self._assess_complexity(input_data)
        
        reasoning_steps = []
        explanation_content = ""
        
        reasoning_steps.append("Understanding user request and context")
        explanation_content += self._generate_acknowledgment(input_data)
        
        if complexity_level >= 2:
            reasoning_steps.append("Providing contextual background information")
            explanation_content += "\n\n## Context and Background\n"
            explanation_content += self._generate_context(input_data, input_type)
        
        reasoning_steps.append("Developing comprehensive solution or explanation")
        explanation_content += "\n\n## Detailed Explanation\n"
        explanation_content += self._generate_detailed_explanation(input_data, input_type)
        
        if complexity_level >= 1:
            reasoning_steps.append("Providing practical examples and illustrations")
            explanation_content += "\n\n## Practical Examples\n"
            explanation_content += self._generate_examples(input_data, input_type)
        
        reasoning_steps.append("Summarizing key takeaways")
        explanation_content += "\n\n## Key Takeaways\n"
        explanation_content += self._generate_summary(input_data)
        
        execution_time = time.time() - start_time
        
        return AgentResponse(
            content=explanation_content,
            reasoning_steps=reasoning_steps,
            confidence_score=self._calculate_confidence(input_data),
            metadata={
                "input_type": input_type,
                "complexity_level": complexity_level,
                "explanation_style": self.config.explanation_depth
            },
            execution_time=execution_time
        )
    
    def _classify_input(self, input_data: str) -> str:
        input_lower = input_data.lower()
        if any(keyword in input_lower for keyword in ['solve', 'problem', 'issue', 'debug', "isn't working", 'not working', 'error', 'bug', 'fix']):
            return 'problem_solving'
        elif any(keyword in input_lower for keyword in ['code', 'program', 'function', 'implement', 'write a function', 'python code']):
            return 'code_request'
        elif any(keyword in input_lower for keyword in ['explain', 'what is', 'how does', 'why', 'tell me about']):
            return 'conceptual_question'
        elif any(keyword in input_lower for keyword in ['create', 'build', 'design', 'develop', 'make']):
            return 'creation_task'
        else:
            return 'general_inquiry'
    
    def _assess_complexity(self, input_data: str) -> int:
        word_count = len(input_data.split())
        question_marks = input_data.count('?')
        technical_terms = len([word for word in input_data.split() if any(term in word.lower() for term in ['algorithm', 'framework', 'architecture', 'system'])])
        complexity = 0
        if word_count > 50:
            complexity += 1
        if question_marks > 1:
            complexity += 1
        if technical_terms > 2:
            complexity += 1
        return min(complexity, 3)
    
    def _generate_acknowledgment(self, input_data: str) -> str:
        return f"I understand you're asking about: '{input_data[:100]}{'...' if len(input_data) > 100 else ''}'\n\nLet me provide you with a comprehensive explanation."
    
    def _generate_context(self, input_data: str, input_type: str) -> str:
        contexts = {
            'code_request': "This involves programming concepts and implementation details.",
            'conceptual_question': "Understanding this concept requires exploring its fundamental principles.",
            'problem_solving': "To solve this effectively, we need to analyze systematically.",
            'creation_task': "Creating this requires understanding design principles.",
            'general_inquiry': "This topic connects to several important concepts."
        }
        return contexts.get(input_type, "I'll provide relevant background information.")
    
    def _generate_detailed_explanation(self, input_data: str, input_type: str) -> str:
        return "Here's my detailed analysis:\n\n1. **Core Concept**: The fundamental idea...\n2. **Key Components**: The main elements...\n3. **How It Works**: The mechanism operates by...\n4. **Best Practices**: Recommended approaches include..."
    
    def _generate_examples(self, input_data: str, input_type: str) -> str:
        return "**Example 1**: A practical scenario...\n\n**Example 2**: Another illustration..."
    
    def _generate_summary(self, input_data: str) -> str:
        return "- **Main Point 1**: Essential insight\n- **Main Point 2**: Critical consideration\n- **Main Point 3**: Practical recommendation"
    
    def _calculate_confidence(self, input_data: str) -> float:
        clarity_indicators = ['?' in input_data, len(input_data.split()) > 10, any(word in input_data.lower() for word in ['please', 'help', 'explain'])]
        return min(0.7 + sum(clarity_indicators) * 0.1, 1.0)


class CustomAgent:
    __slots__ = ('config', 'explanation_module', 'logger', '_cache', '_config_hash',
                 '_session', '_intent_classifier', 'llm_provider', '_i18n',
                 '_access_logger', '_decision_logger', '_execution_logger',
                 '_intent_logger', '_memory_logger', '_routing_logger', '_tool_logger', '_post_logger')
    
    def __init__(self, config: Optional[AgentConfig] = None, session_id: Optional[str] = None):
        self.config = config or AgentConfig()
        self.explanation_module = ExplanationModule(self.config)
        self._intent_classifier = IntentClassifier()
        self._i18n = I18n(self.config.language)
        self.setup_logging()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self._access_logger = get_layer_logger("access", "CLI")
        self._decision_logger = get_layer_logger("decision", "CustomAgent")
        self._execution_logger = get_layer_logger("execution", "SessionManager")
        
        self._intent_logger = get_layer_logger("decision", "IntentClassifier", "intent")
        self._memory_logger = get_layer_logger("decision", "MemoryCache", "memory")
        self._routing_logger = get_layer_logger("decision", "TaskRouter", "routing")
        self._tool_logger = get_layer_logger("decision", "SkillManager", "tool_select")
        self._post_logger = get_layer_logger("decision", "ResponsePost", "post_process")
        
        if self.config.enable_caching:
            self._cache = LRUCache(maxsize=100)
            self._config_hash = hash_config(self.config)
        else:
            self._cache = None
            self._config_hash = None
        
        if self.config.enable_session:
            self._session = session_manager.create_session(session_id)
        else:
            self._session = None
        
        self.llm_provider = None
        
        self._intent_classifier.set_llm_provider(self.llm_provider)
    
    def set_llm_provider(self, provider):
        """Set the LLM provider for both generation and intent classification."""
        self.llm_provider = provider
        self._intent_classifier.set_llm_provider(provider)
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def respond(self, user_input: str) -> AgentResponse:
        execution_flow = []
        t = self._i18n.t
        
        access = self._access_logger
        intent = self._intent_logger
        memory = self._memory_logger
        routing = self._routing_logger
        tool = self._tool_logger
        post = self._post_logger
        execution = self._execution_logger
        
        access.info(f"{t('flow_header')}")
        access.info(f"respond() 接收用户输入: {user_input[:80]}{'...' if len(user_input) > 80 else ''}")
        access.info(f"   → 下一步: 进行输入验证")
        execution_flow.append("🚪 [接入层] 接收用户输入 → [决策层-意图识别层] 进行验证")
        
        self.logger.info(f"Using explanation_module: {type(self.explanation_module)}")
        
        if not isinstance(user_input, str):
            raise InputValidationError("Input must be a string")
        if not user_input.strip():
            raise InputValidationError("Input cannot be empty")
        intent.info(t('validation_pass'))
        intent.info(f"   → 下一步将调用: [执行层] 保存消息到会话")
        execution_flow.append("🧠 [决策层-意图识别层] 输入格式验证通过 → [执行层] 保存消息")
        
        if self._session:
            memory.info(f"{t('session_add')} (session_id: {self._session.session_id})")
            self._session.add_message('user', user_input)
            memory.info(f"   → 下一步将调用: [决策层-记忆检索层] 检查缓存")
            execution.info(f"消息已添加到会话 [{self._session.session_id}] → 检查缓存")
            execution_flow.append(f"⚡ [执行层] 消息已添加到会话 [{self._session.session_id}] → [决策层-记忆检索层] 检查缓存")
        
        if self._cache is not None:
            cache_key = create_cache_key(user_input, self._config_hash)
            cached_response = self._cache.get(cache_key)
            if cached_response is not None:
                memory.info(t('cache_hit'))
                memory.info(f"   → 流程结束，直接返回缓存响应")
                execution_flow.append("🧠 [决策层-记忆检索层] 缓存命中 → 直接返回")
                memory.info(f"{t('flow_header')}")
                cached_response.execution_time = 0.0
                return cached_response
            memory.info(t('cache_miss'))
            memory.info(f"   → 下一步将调用: [决策层-路由层] 开始处理请求")
            execution_flow.append("🧠 [决策层-记忆检索层] 缓存未命中 → [决策层-路由层] 开始处理")
        
        routing.info(t('processing_start'))
        routing.info(f"   → 下一步将调用: [决策层-路由层] 进入任务路由模块")
        execution_flow.append("🧠 [决策层-路由层] 开始处理请求 → [决策层-路由层] 任务路由")
        start_time = time.time()
        
        try:
            if self.config.enable_routing:
                routing.info(f"TaskRouter 启用路由功能")
                routing.info(f"   → 下一步将调用: IntentClassifier 进行意图分类")
                execution_flow.append("🧠 [决策层-路由层] TaskRouter 启用路由功能 → IntentClassifier")
                
                route_context = {
                    'llm_provider': getattr(self, 'llm_provider', None),
                    'skill_manager': skill_manager
                }
                route_match = await router.route_async(user_input)
                if route_match:
                    routing.info(f"TaskRouter 找到匹配的路由: {route_match.route_id} (置信度: {route_match.confidence:.2f})")
                    execution_flow.append(f"   ├─ TaskRouter 匹配路由: {route_match.route_id}")
                    execution_flow.append(f"   └─ TaskRouter 置信度: {route_match.confidence:.2f}")
                    
                    routing.info(f"   → 下一步: [决策层-路由层] {route_match.route_id}.handler()")
                    execution_flow.append(f"🧠 [决策层-路由层] TaskRouter → [决策层-路由层] {route_match.route_id}")
                    
                    route_response, handler_flow = await self._handle_route(route_match, user_input, route_context)
                    execution_flow.extend(handler_flow)
                    
                    if route_response:
                        routing.info(f"TaskRouter 路由匹配成功")
                        routing.info(f"   → 流程结束，返回响应")
                        execution_flow.append("🧠 [决策层-路由层] 返回响应 → 完成")
                        post.info(f"🔔 执行流程汇总:\n  " + "\n  ".join(execution_flow))
                        post.info(f"{t('flow_header')}")
                        
                        execution_time = time.time() - start_time
                        return AgentResponse(
                            content=route_response,
                            reasoning_steps=execution_flow,
                            confidence_score=route_match.confidence,
                            execution_time=execution_time
                        )
                else:
                    routing.info(f"TaskRouter 未匹配任何路由")
                    routing.info(f"   → 下一步将调用: SkillManager 进行技能发现")
                    execution_flow.append("🧠 [决策层-路由层] TaskRouter 未匹配路由 → SkillManager")
            
            if self.config.enable_skills:
                tool.info(f"SkillManager 启用技能执行")
                tool.info(f"   → 下一步将调用: IntentClassifier 进行意图分类")
                execution_flow.append("🧠 [决策层-工具选择层] SkillManager 启用技能执行")
                
                intent_result = await self._intent_classifier.classify_async(user_input)
                intent.info(f"IntentClassifier 分类结果: {intent_result}")
                intent.info(f"   → 下一步将调用: SkillManager.discover_skills()")
                execution_flow.append(f"   ├─ [决策层-意图识别层] IntentClassifier 意图: {intent_result}")
                
                relevant_skills = await skill_manager.discover_skills(intent_result, user_input)
                execution.info(f"SkillManager 发现 {len(relevant_skills)} 个相关技能")
                tool.info(f"   → 下一步将调用: Skill.execute() 执行技能")
                execution_flow.append(f"   └─ [执行层] SkillManager 发现 {len(relevant_skills)} 个技能")
                
                for skill_meta in relevant_skills:
                    execution.info(f"Skill.execute() 执行技能: {skill_meta.id} ({skill_meta.name})")
                    tool.info(f"   → 调用: {skill_meta.id}.execute()")
                    execution_flow.append(f"   → [执行层] Skill.execute({skill_meta.id})")
                    
                    skill_result = await skill_manager.execute_skill(skill_meta.id)
                    if skill_result and skill_result.success:
                        execution.info(f"Skill.execute() 执行成功")
                        post.info(f"   → 流程结束，返回技能执行结果")
                        execution_flow.append("   ⚡ [执行层] Skill.execute() 成功 → 完成")
                        post.info(f"🔔 执行流程汇总:\n  " + "\n  ".join(execution_flow))
                        post.info(f"{t('flow_header')}")
                        
                        execution_time = time.time() - start_time
                        return AgentResponse(
                            content=skill_result.output,
                            reasoning_steps=execution_flow,
                            confidence_score=0.8,
                            execution_time=execution_time
                        )
                    else:
                        tool.warning(f"{t('skill_fail')}: {skill_result.error if skill_result else 'Unknown'}")
                        tool.info(f"   → 尝试下一个技能")
                tool.info(f"❌ [决策层-工具选择层] 所有技能执行失败")
                tool.info(f"   → 下一步将调用: [决策层-后处理层] 解释模块")
                execution_flow.append("❌ [决策层-工具选择层] 技能执行均失败 → [决策层-后处理层] 解释模块")
            
            post.info(t('explanation_module'))
            post.info(f"   → 下一步将调用: [决策层-后处理层] AdvancedReasoningModule.process()")
            execution_flow.append("🧠 [决策层-后处理层] 回退到解释模块 → [决策层-后处理层] AdvancedReasoningModule")
            response = await self._generate_response(user_input)
            
            post.info(f"{t('response_complete')} (长度: {len(response.content)} 字符)")
            post.info(f"   → 下一步将调用: [执行层] 保存响应到会话")
            execution_flow.append("   ✅ [决策层-后处理层] 响应生成完成 → [执行层] 保存")
            
            execution_time = time.time() - start_time
            response.execution_time = execution_time
            
            if self._session:
                execution.info(t('session_add_assistant'))
                memory.info(f"   → 下一步将调用: [决策层-记忆检索层] 缓存响应")
                self._session.add_message('assistant', response.content)
                execution.info("保存助手响应 → 缓存")
                execution_flow.append("⚡ [执行层] 保存助手响应 → [决策层-记忆检索层] 缓存")
            
            if self._cache is not None:
                memory.info(t('cache_store'))
                cache_key = create_cache_key(user_input, self._config_hash)
                self._cache.put(cache_key, response)
                memory.info("响应已缓存")
                execution_flow.append("🧠 [决策层-记忆检索层] 响应已缓存")
            
            post.info(f"🧠 [完成] 响应生成完成，耗时 {execution_time:.2f} 秒")
            execution_flow.append(f"🚪 [完成] 总耗时 {execution_time:.2f}s → 完成")
            post.info(f"🔔 执行流程汇总:\n  " + "\n  ".join(execution_flow))
            post.info(f"{t('flow_header')}")
            return response
            
        except asyncio.TimeoutError:
            timeout_error = TimeoutError(self.config.timeout_seconds)
            post.error(f"Timeout error: {timeout_error}")
            return AgentResponse(
                content=f"I apologize, but your request took too long to process (timeout after {self.config.timeout_seconds} seconds). Please try a simpler query.",
                confidence_score=0.0,
                execution_time=time.time() - start_time,
                error_code=TimeoutError.error_code
            )
            
        except InputValidationError as e:
            intent.error(f"Input validation error: {e}")
            return AgentResponse(
                content=f"I apologize, but there was an issue with your input: {str(e)}",
                confidence_score=0.0,
                execution_time=time.time() - start_time,
                error_code=InputValidationError.error_code
            )
            
        except Exception as e:
            response_error = ResponseGenerationError(
                f"Failed to generate response for input: {user_input[:100]}...",
                original_exception=e
            )
            post.error(f"Response generation error: {response_error}", exc_info=True)
            return AgentResponse(
                content=f"I apologize, but I encountered an unexpected error while processing your request. Please try again or rephrase your question.",
                confidence_score=0.0,
                execution_time=time.time() - start_time,
                error_code=ResponseGenerationError.error_code
            )
    
    async def _handle_route(self, route_match: RouteMatch, user_input: str, context: Dict[str, Any] = None) -> tuple:
        decision = self._decision_logger
        try:
            decision.info(f"Handling route: {route_match.route_id} with handler: {route_match.handler}")
            ctx = context or {}
            result = await route_match.handler(user_input, ctx)
            if result:
                if isinstance(result, tuple):
                    response, handler_flow = result
                    decision.info(f"Route handler returned: {response[:50] if response else 'None'}...")
                    return response, handler_flow
                else:
                    decision.info(f"Route handler returned: {result[:50] if result else 'None'}...")
                    return result, []
            decision.info(f"Route handler returned: None")
            return None, []
        except Exception as e:
            decision.error(f"Error handling route {route_match.route_id}: {e}")
            return None, []
    
    async def _generate_response(self, user_input: str) -> AgentResponse:
        if self.config.timeout_seconds > 0:
            response_task = self.explanation_module.process(user_input, self._session)
            response = await asyncio.wait_for(
                response_task, 
                timeout=self.config.timeout_seconds
            )
        else:
            response = await self.explanation_module.process(user_input, self._session)
        
        if self.config.response_format == "markdown":
            response.content = self._format_as_markdown(response.content)
        elif self.config.response_format == "structured":
            response.content = self._format_structured(response.content)
        
        if len(response.content) > self.config.max_response_length:
            response.content = response.content[:self.config.max_response_length] + "...\n\n[Response truncated for length]"
        
        return response
    
    def _format_as_markdown(self, content: str) -> str:
        return content
    
    def _format_structured(self, content: str) -> str:
        return content
    
    def get_session(self) -> Optional[Session]:
        return self._session
    
    def set_session(self, session: Session):
        self._session = session
    
    def end_session(self):
        if self._session:
            self._session.end()


async def main():
    agent = CustomAgent(AgentConfig(
        name="DetailedAssistant",
        explanation_depth="detailed",
        response_format="markdown"
    ))
    
    test_queries = [
        "How do neural networks work?",
        "Can you help me write a Python function to sort a list?",
        "What's the difference between REST and GraphQL APIs?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        response = await agent.respond(query)
        print(response.content)
        print(f"\nExecution time: {response.execution_time:.2f}s")
        print(f"Confidence: {response.confidence_score:.2f}")


if __name__ == "__main__":
    asyncio.run(main())