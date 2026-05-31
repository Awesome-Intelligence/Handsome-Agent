#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Response Strategy Router - 响应策略路由器

根据请求类型智能选择最佳响应策略:
1. TaskPlanningMiddleware - 复杂多步骤任务
2. SkillManager - 工具/技能执行
3. AdvancedReasoningModule - 知识问答/推理

设计原则:
- 避免重复调用 LLM
- 合理分工，各司其职
- 灵活可配置
"""

import logging
from typing import Dict, Any, Optional, Tuple, List, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .agent import AgentResponse

from .exceptions import ResponseGenerationError


class ResponseStrategy(Enum):
    """响应策略枚举"""
    TASK_PLANNING = "task_planning"      # 复杂任务规划
    SKILL_EXECUTION = "skill_execution" # 技能执行
    ADVANCED_REASONING = "advanced_reasoning"  # 高级推理
    SIMPLE_RESPONSE = "simple_response"  # 简单响应


class ResponseStrategyRouter:
    """
    响应策略路由器
    
    根据请求特征选择最佳响应策略:
    
    ┌─────────────────────────────────────────────────────────────┐
    │                    Request Analysis                          │
    │  • 关键词检测                                                │
    │  • 复杂度评估                                                │
    │  • 历史上下文                                                │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                  Strategy Selection                         │
    │                                                              │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
    │  │ TaskPlan   │  │ SkillExec  │  │ AdvReason  │           │
    │  │ (复杂任务) │  │ (工具执行) │  │ (知识问答) │           │
    │  └─────────────┘  └─────────────┘  └─────────────┘           │
    └─────────────────────────────────────────────────────────────┘
    """
    
    def __init__(
        self,
        enable_task_planning: bool = True,
        enable_skills: bool = True,
        enable_advanced_reasoning: bool = True
    ):
        self.enable_task_planning = enable_task_planning
        self.enable_skills = enable_skills
        self.enable_advanced_reasoning = enable_advanced_reasoning
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.propagate = False
    
    def analyze(self, user_input: str, context: Dict[str, Any] = None) -> ResponseStrategy:
        """
        分析请求并选择最佳策略
        
        Args:
            user_input: 用户输入
            context: 上下文信息
            
        Returns:
            ResponseStrategy: 最佳响应策略
        """
        input_lower = user_input.lower()
        context = context or {}
        
        # 优先级 1: 任务规划 (复杂多步骤任务)
        if self.enable_task_planning and self._is_complex_task(input_lower, user_input):
            self.logger.info(f"🎯 策略选择: TASK_PLANNING (复杂任务)")
            return ResponseStrategy.TASK_PLANNING
        
        # 优先级 2: 技能执行 (工具调用请求)
        if self.enable_skills and self._is_skill_request(input_lower, user_input):
            self.logger.info(f"🎯 策略选择: SKILL_EXECUTION (技能执行)")
            return ResponseStrategy.SKILL_EXECUTION
        
        # 优先级 3: 高级推理 (知识问答/推理)
        if self.enable_advanced_reasoning and self._needs_reasoning(input_lower, user_input):
            self.logger.info(f"🎯 策略选择: ADVANCED_REASONING (高级推理)")
            return ResponseStrategy.ADVANCED_REASONING
        
        # 默认: 简单响应 (对话/问候)
        self.logger.info(f"🎯 策略选择: SIMPLE_RESPONSE (简单响应)")
        return ResponseStrategy.SIMPLE_RESPONSE
    
    def _is_complex_task(self, input_lower: str, user_input: str) -> bool:
        """
        判断是否为复杂任务
        
        DEPRECATED: 应该使用 LLM 来判断任务复杂度，这里仅作为降级使用
        """
        # 这个方法应该由 LLM 调用来替代
        # 这里仅保留作为降级，且不应该用于主要判断逻辑
        
        # 简化判断：只检查是否有明显的多步骤特征
        has_multi_step = '以及' in input_lower or '包括' in input_lower and '和' in input_lower
        has_project_words = '项目' in input_lower or '系统' in input_lower
        
        return has_multi_step and has_project_words
    
    def _is_skill_request(self, input_lower: str, user_input: str) -> bool:
        """
        判断是否为技能执行请求
        
        DEPRECATED: 应该使用 LLM 来判断意图，这里仅作为降级使用
        """
        # 这个方法应该由 LLM 调用来替代
        # 这里仅保留作为降级
        skill_indicators = [
            '运行', '执行', '打开', '启动',
            '创建文件', '读取文件', '删除',
            '搜索', '查找',
            '打开浏览器', '打开终端',
            'run ', 'execute', 'open ', 'start',
            'file', 'terminal', 'command',
        ]
        
        return any(kw in input_lower for kw in skill_indicators)
    
    def _needs_reasoning(self, input_lower: str, user_input: str) -> bool:
        """
        判断是否需要高级推理
        
        DEPRECATED: 应该使用 LLM 来判断意图，这里仅作为降级使用
        """
        # 这个方法应该由 LLM 调用来替代
        # 这里仅保留作为降级
        reasoning_indicators = [
            '为什么', '如何', '是什么', '什么意思',
            '解释', '原理', '机制',
            '比较', '区别', '差异',
            'why', 'how', 'what', 'explain',
            'python', 'java', 'javascript', '代码',
            '算法', '架构', '设计模式',
        ]
        
        # 简单对话排除
        simple_conversation = [
            '你好', 'hello', 'hi', '嗨',
            '天气', '时间', '日期',
            '谢谢', '再见', 'bye',
        ]
        
        is_reasoning = any(kw in input_lower for kw in reasoning_indicators)
        is_simple = any(kw in input_lower for kw in simple_conversation)
        
        return is_reasoning and not is_simple


class UnifiedAgentIntegration:
    """
    统一 Agent 集成
    
    整合三大模块到单一入口:
    1. TaskPlanningMiddleware - 复杂任务
    2. SkillManager - 工具执行  
    3. AdvancedReasoningModule - 知识推理
    """
    
    def __init__(
        self,
        agent,  # CustomAgent instance
        enable_advanced_reasoning: bool = True
    ):
        self.agent = agent
        self.strategy_router = ResponseStrategyRouter(
            enable_task_planning=agent.config.enable_task_planning,
            enable_skills=agent.config.enable_skills,
            enable_advanced_reasoning=enable_advanced_reasoning
        )
        
        self._advanced_reasoning = None
        if enable_advanced_reasoning:
            from advanced_reasoning.module import AdvancedReasoningModule
            self._advanced_reasoning = AdvancedReasoningModule(agent.config)
            if agent.llm_provider:
                self._advanced_reasoning.set_llm_provider(agent.llm_provider)
    
    async def respond(self, user_input: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        统一响应入口
        
        Returns:
            Tuple[response, execution_flow, metadata]
        """
        strategy = self.strategy_router.analyze(user_input)
        
        if strategy == ResponseStrategy.TASK_PLANNING:
            return await self._handle_task_planning(user_input)
        elif strategy == ResponseStrategy.SKILL_EXECUTION:
            return await self._handle_skill_execution(user_input)
        elif strategy == ResponseStrategy.ADVANCED_REASONING:
            return await self._handle_advanced_reasoning(user_input)
        else:
            return await self._handle_simple_response(user_input)
    
    async def _handle_task_planning(self, user_input: str):
        """处理复杂任务规划"""
        from .task_middleware import TaskPlanningMiddleware
        
        middleware = TaskPlanningMiddleware(
            llm_provider=self.agent.llm_provider,
            session_id=self.agent._session.session_id if self.agent._session else 'default',
            enable_logging=True
        )
        
        result = await middleware.process(user_input)
        
        execution_flow = [
            f"🎯 [策略路由] 选择任务规划策略",
            f"📊 [任务规划] 复杂度: {result.complexity}",
            f"📋 [任务规划] 子任务数: {len(result.subtasks)}"
        ]
        
        metadata = {
            'strategy': 'task_planning',
            'is_complex': True,
            'subtasks': result.subtasks
        }
        
        return result.initial_plan, execution_flow, metadata
    
    async def _handle_skill_execution(self, user_input: str):
        """处理技能执行"""
        # 委托给原始 Agent 的技能处理
        # 这里简化处理，实际应该调用 SkillManager
        response = "技能执行 (简化实现)"
        execution_flow = [
            f"🎯 [策略路由] 选择技能执行策略",
            f"🔧 [技能管理] 执行技能..."
        ]
        metadata = {'strategy': 'skill_execution'}
        return response, execution_flow, metadata
    
    async def _handle_advanced_reasoning(self, user_input: str):
        """处理高级推理"""
        if self._advanced_reasoning is None:
            return "高级推理未启用", [], {'strategy': 'advanced_reasoning', 'error': 'disabled'}
        
        result = await self._advanced_reasoning.process(user_input)
        
        execution_flow = [
            f"🎯 [策略路由] 选择高级推理策略",
            f"🤖 [高级推理] 生成响应..."
        ]
        metadata = {
            'strategy': 'advanced_reasoning',
            'input_type': result.metadata.get('input_type'),
            'complexity': result.metadata.get('complexity_level')
        }
        
        return result.content, execution_flow, metadata
    
    async def _handle_simple_response(self, user_input: str):
        """处理简单响应
        
        DEPRECATED: 应该使用 LLM 来判断意图和生成响应
        """
        # 直接使用 agent 的 LLM 来响应
        if self.agent.llm_provider:
            try:
                response = await self.agent.llm_provider.generate(user_input)
                execution_flow = [
                    f"🎯 [策略路由] 选择简单响应策略",
                    f"💬 [LLM响应] 生成回复..."
                ]
                metadata = {'strategy': 'simple_response', 'method': 'llm'}
                return response, execution_flow, metadata
            except Exception:
                pass
        
        # 降级：默认响应
        response = "我理解你的意思。有什么具体需要帮助的吗？"
        execution_flow = [
            f"🎯 [策略路由] 选择简单响应策略",
            f"💬 [简单响应] 生成回复..."
        ]
        metadata = {'strategy': 'simple_response', 'method': 'fallback'}
        
        return response, execution_flow, metadata