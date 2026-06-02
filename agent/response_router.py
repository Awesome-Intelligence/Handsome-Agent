#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Response Strategy Router

Intelligently selects the best response strategy based on request type

Design principles:
- Avoid redundant LLM calls
- Clear division of responsibilities
- Flexible and configurable
"""

from typing import Dict, Any
from enum import Enum

from common.logging_manager import get_decision_logger


class ResponseStrategy(Enum):
    """Response strategy enum"""
    TASK_PLANNING = "task_planning"
    SKILL_EXECUTION = "skill_execution"
    SIMPLE_RESPONSE = "simple_response"


class ResponseStrategyRouter:
    """
    Response Strategy Router
    
    Analyzes request and selects best strategy:
    
    ┌─────────────────────────────────────┐
    │  Request Analysis                  │
    │  • Keyword detection              │
    │  • Complexity assessment          │
    │  • Context analysis              │
    └─────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────┐
    │  Strategy Selection                │
    │  ┌───────────┐  ┌───────────┐    │
    │  │ TaskPlan  │  │ SkillExec │    │
    │  │ (complex) │  │ (tool use)│    │
    │  └───────────┘  └───────────┘    │
    │                  │              │
    │                  ▼              │
    │            ┌───────────┐          │
    │            │ Simple   │          │
    │            │ (basic)  │          │
    │            └───────────┘          │
    └─────────────────────────────────┘
    """
    
    def __init__(
        self,
        enable_task_planning: bool = True,
        enable_skills: bool = True
    ):
        self.enable_task_planning = enable_task_planning
        self.enable_skills = enable_skills
        
        self.logger = get_decision_logger(self.__class__.__name__)
        self.logger.propagate = False
    
    def analyze(self, user_input: str, context: Dict[str, Any] = None) -> ResponseStrategy:
        """
        Analyze request and select best strategy
        
        Args:
            user_input: User input
            context: Context information
            
        Returns:
            ResponseStrategy: Best response strategy
        """
        input_lower = user_input.lower()
        context = context or {}
        
        # Priority 1: Task planning (complex multi-step tasks)
        if self.enable_task_planning and self._is_complex_task(input_lower, user_input):
            self.logger.info(f"Strategy: TASK_PLANNING")
            return ResponseStrategy.TASK_PLANNING
        
        # Priority 2: Skill execution (tool execution requests)
        if self.enable_skills and self._is_skill_request(input_lower, user_input):
            self.logger.info(f"Strategy: SKILL_EXECUTION")
            return ResponseStrategy.SKILL_EXECUTION
        
        # Default: Simple response
        self.logger.info(f"Strategy: SIMPLE_RESPONSE")
        return ResponseStrategy.SIMPLE_RESPONSE
    
    def _is_complex_task(self, input_lower: str, user_input: str) -> bool:
        """
        Check if input requires task planning
        
        DEPRECATED: Should use LLM to determine task complexity
        This is only used as fallback
        """
        has_multi_step = ('以及' in input_lower or '包括' in input_lower) and '和' in input_lower
        has_project_words = '项目' in input_lower or '系统' in input_lower
        
        return has_multi_step and has_project_words
    
    def _is_skill_request(self, input_lower: str, user_input: str) -> bool:
        """
        Check if input is a skill/tool request
        
        DEPRECATED: Should use LLM to determine intent
        This is only used as fallback
        """
        skill_indicators = [
            '运行', '执行', '打开', '启动',
            '创建文件', '读取文件', '删除',
            '搜索', '查找',
            '打开浏览器', '打开终端',
            'run ', 'execute', 'open ', 'start',
            'file', 'terminal', 'command',
        ]
        
        return any(kw in input_lower for kw in skill_indicators)
