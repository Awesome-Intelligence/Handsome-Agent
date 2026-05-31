#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collaborative Task Planning - 协作式任务规划

TaskPlanning + AdvancedReasoning 协同工作:
1. TaskPlanning 拆解任务
2. AdvancedReasoning 提供技术选型建议
3. 两者递进式协作

设计原则:
- TaskPlanning 负责"做什么"（任务拆解）
- AdvancedReasoning 负责"为什么"（技术选型解释）
- 两者协同，提供带推理的完整执行计划
"""

import json
import re
from typing import Dict, Any, Optional, List
from enum import Enum

from .task_planner import TaskPlanner, SubTask, TaskStatus, TaskPlan
from .task_logger import TaskLogger, create_task_logger


class CollaborationStrategy(Enum):
    """协作策略"""
    DECOMPOSITION_ONLY = "decomposition_only"      # 仅拆解
    DECOMPOSITION_WITH_REASONING = "decomposition_with_reasoning"  # 拆解+推理
    EXECUTION_WITH_REASONING = "execution_with_reasoning"      # 执行+推理


class TechnicalDomain(Enum):
    """技术领域（需要 AdvancedReasoning 的场景）"""
    DATABASE = "database"            # 数据库选型
    AUTHENTICATION = "auth"         # 认证方式
    API_DESIGN = "api_design"      # API 设计
    ARCHITECTURE = "architecture"  # 架构设计
    SECURITY = "security"           # 安全设计
    DEPLOYMENT = "deployment"        # 部署策略
    TESTING = "testing"            # 测试策略
    FRONTEND = "frontend"         # 前端技术
    BACKEND = "backend"           # 后端技术


class CollaborativeTaskPlanner:
    """
    协作式任务规划器
    
    TaskPlanning 和 AdvancedReasoning 协同工作：
    
    ┌─────────────────────────────────────────────────────────────┐
    │  1. TaskPlanning 拆解任务                                   │
    │     "帮我开发一个用户注册功能"                               │
    │     ↓                                                      │
    │  2. AdvancedReasoning 提供技术建议                         │
    │     "认证: JWT vs Session → 推荐 JWT (无状态，适合微服务)"  │
    │     ↓                                                      │
    │  3. 生成带推理的执行计划                                   │
    │     #1 需求分析                                          │
    │     #2 技术选型 [理由: JWT 无状态，适合分布式]                │
    │     #3 数据库设计 [理由: PostgreSQL，事务支持强]            │
    └─────────────────────────────────────────────────────────────┘
    """
    
    def __init__(
        self,
        task_planner: TaskPlanner,
        advanced_reasoning=None,
        enable_collaboration: bool = True
    ):
        self.task_planner = task_planner
        self.advanced_reasoning = advanced_reasoning
        self.enable_collaboration = enable_collaboration
        self.logger = create_task_logger("CollaborativePlanner")
        
        self._technical_keywords = {
            TechnicalDomain.DATABASE: [],
            TechnicalDomain.AUTHENTICATION: [],
            TechnicalDomain.API_DESIGN: [],
            TechnicalDomain.ARCHITECTURE: [],
            TechnicalDomain.SECURITY: [],
            TechnicalDomain.TESTING: [],
        }
    
    def _identify_technical_domains(self, task: str) -> List[TechnicalDomain]:
        """识别任务涉及的技术领域"""
        task_lower = task.lower()
        domains = []
        
        for domain, keywords in self._technical_keywords.items():
            if any(kw.lower() in task_lower for kw in keywords):
                domains.append(domain)
        
        return domains
    
    def _generate_reasoning_prompt(self, domain: TechnicalDomain, context: str) -> str:
        """生成推理提示"""
        prompts = {
            TechnicalDomain.DATABASE: f"""对于一个{context}的系统，请提供数据库选型建议。

考虑因素：
- 数据一致性要求
- 扩展性需求
- 事务支持
- 团队技术栈

请简洁回答：
1. 推荐方案
2. 主要理由（1-2句话）
3. 适用场景""",

            TechnicalDomain.AUTHENTICATION: f"""对于一个{context}的系统，请提供认证方案建议。

考虑因素：
- 是否需要无状态
- 微服务架构
- 安全要求
- 用户规模

请简洁回答：
1. 推荐方案（JWT/Session/OAuth）
2. 主要理由（1-2句话）
3. 实现要点""",

            TechnicalDomain.API_DESIGN: f"""对于一个{context}的API，请提供设计建议。

考虑因素：
- RESTful vs GraphQL
- 版本管理
- 错误处理
- 文档

请简洁回答：
1. 推荐方案
2. 主要理由
3. 设计要点""",

            TechnicalDomain.ARCHITECTURE: f"""对于一个{context}的系统，请提供架构建议。

考虑因素：
- 团队规模
- 业务复杂度
- 部署环境
- 扩展需求

请简洁回答：
1. 推荐架构（单体/微服务/模块化）
2. 主要理由
3. 演进建议""",

            TechnicalDomain.SECURITY: f"""对于一个{context}的系统，请提供安全建议。

考虑因素：
- 常见攻击防护
- 数据加密
- 身份验证
- 权限控制

请简洁回答：
1. 关键安全措施
2. 建议方案
3. 注意事项""",
        }
        
        return prompts.get(domain, f"请提供关于{domain.value}的建议")
    
    async def plan_with_collaboration(self, user_request: str) -> Dict[str, Any]:
        """
        协作式任务规划
        
        流程:
        1. TaskPlanning 拆解任务
        2. AdvancedReasoning 提供技术建议
        3. 生成带推理的执行计划
        """
        result = {
            'success': True,
            'main_task': user_request,
            'subtasks': [],
            'technical_reasoning': {},
            'plan': ''
        }
        
        # 1. 分析技术领域
        domains = self._identify_technical_domains(user_request)
        
        # 2. 获取技术建议
        if self.enable_collaboration and self.advanced_reasoning and domains:
            for domain in domains:
                reasoning_prompt = self._generate_reasoning_prompt(domain, user_request)
                try:
                    reasoning_response = await self.advanced_reasoning.process(reasoning_prompt)
                    if hasattr(reasoning_response, 'content'):
                        result['technical_reasoning'][domain.value] = reasoning_response.content
                    else:
                        result['technical_reasoning'][domain.value] = str(reasoning_response)
                except Exception as e:
                    result['technical_reasoning'][domain.value] = f"建议: 请根据实际需求选择"
        
        # 3. TaskPlanning 拆解任务
        try:
            complexity = await self.task_planner.analyze_complexity(user_request)
            
            if complexity.get('needs_decomposition', False):
                plan = await self.task_planner.decompose_task(
                    user_request,
                    complexity.get('complexity', 'moderate')
                )
                
                result['subtasks'] = [
                    {
                        'id': t.id,
                        'title': t.title,
                        'description': t.description,
                        'depends_on': t.depends_on
                    }
                    for t in plan.subtasks
                ]
                result['main_task'] = plan.main_task
            else:
                # 简单任务
                result['subtasks'] = [
                    {
                        'id': 1,
                        'title': user_request,
                        'description': '执行任务',
                        'depends_on': []
                    }
                ]
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        
        # 4. 生成带推理的计划
        result['plan'] = self._format_collaborative_plan(result)
        
        return result
    
    def _format_collaborative_plan(self, result: Dict[str, Any]) -> str:
        """格式化协作式计划"""
        lines = []
        
        # 表头
        lines.append("🎯 **智能执行计划** (TaskPlanning + AdvancedReasoning)")
        lines.append("")
        lines.append(f"📋 主任务: {result['main_task']}")
        lines.append("")
        
        # 技术建议摘要
        if result['technical_reasoning']:
            lines.append("💡 **技术选型建议:**")
            for domain, reasoning in result['technical_reasoning'].items():
                lines.append(f"\n**{domain.upper()}:**")
                if len(reasoning) > 200:
                    reasoning = reasoning[:200] + "..."
                lines.append(f"  {reasoning}")
            lines.append("")
        
        # 子任务列表
        if result['subtasks']:
            lines.append("📋 **执行计划:**")
            for i, task in enumerate(result['subtasks'], 1):
                lines.append(f"\n  {i}. **{task['title']}**")
                if task.get('description'):
                    lines.append(f"     └─ {task['description']}")
                if task.get('depends_on'):
                    lines.append(f"     └─ 依赖: {task['depends_on']}")
        
        return "\n".join(lines)


class SubTaskExecutor:
    """
    子任务执行器
    
    支持在子任务执行时调用 AdvancedReasoning
    """
    
    def __init__(self, advanced_reasoning=None):
        self.advanced_reasoning = advanced_reasoning
        self.logger = create_task_logger("SubTaskExecutor")
    
    async def execute_with_reasoning(
        self,
        subtask: SubTask,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        带推理的子任务执行
        
        检测子任务是否需要推理，如果需要则调用 AdvancedReasoning
        """
        result = {
            'success': True,
            'output': '',
            'reasoning': '',
            'needs_reasoning': False
        }
        
        # DEPRECATED: 检测是否需要推理应该由 LLM 来判断，这里仅作为降级使用
        # 简化：默认不需要推理
        needs_reasoning = False
        
        if needs_reasoning and self.advanced_reasoning:
            result['needs_reasoning'] = True
            
            try:
                prompt = f"""任务: {subtask.title}
描述: {subtask.description}
上下文: {context or {}}

请提供:
1. 为什么要这样做
2. 最佳实践建议
3. 常见问题提示

请简洁回答。"""
                
                reasoning_response = await self.advanced_reasoning.process(prompt)
                if hasattr(reasoning_response, 'content'):
                    result['reasoning'] = reasoning_response.content
                else:
                    result['reasoning'] = str(reasoning_response)
                    
            except Exception as e:
                result['reasoning'] = f"推理生成失败: {str(e)}"
        
        return result


def create_collaborative_planner(
    task_planner: TaskPlanner,
    advanced_reasoning=None,
    enable_collaboration: bool = True
) -> CollaborativeTaskPlanner:
    """创建协作式任务规划器"""
    return CollaborativeTaskPlanner(
        task_planner=task_planner,
        advanced_reasoning=advanced_reasoning,
        enable_collaboration=enable_collaboration
    )


def create_subtask_executor(advanced_reasoning=None) -> SubTaskExecutor:
    """创建子任务执行器"""
    return SubTaskExecutor(advanced_reasoning=advanced_reasoning)
