#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Planning Middleware - 任务规划中间件

自动检测复杂任务并触发 LLM 驱动的任务拆解流程

功能:
1. 在 Agent 处理请求前自动判断是否需要任务规划
2. 调用 LLM 分解复杂任务
3. 创建任务列表并执行
4. 返回带有进度追踪的响应
"""

import json
import re
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from .task_planner import TaskPlanner, TaskComplexity, get_task_planner, SubTask, TaskStatus
from .todo_adapter import get_todo_adapter
from .task_logger import TaskLogger, create_task_logger


@dataclass
class PlanningResult:
    """规划结果"""
    is_complex: bool
    complexity: str
    subtasks: List[Dict[str, Any]]
    reasoning: str
    initial_plan: Optional[str] = None


class TaskPlanningMiddleware:
    """
    任务规划中间件
    
    集成到 Agent 的响应流程中:
    1. 接收用户请求
    2. 调用 LLM 分析复杂度
    3. 如果复杂，自动拆解并创建任务列表
    4. 返回执行计划给用户
    5. 在后台执行任务（可选）
    """

    def __init__(
        self, 
        llm_provider,
        session_id: str,
        workspace_dir: Optional[str] = None,
        auto_execute: bool = False,
        complexity_threshold: int = 2,
        enable_logging: bool = True,
        advanced_reasoning=None,
        enable_collaboration: bool = True,
        stream_emitter=None
    ):
        self.llm_provider = llm_provider
        self.session_id = session_id
        self.workspace_dir = workspace_dir
        self.auto_execute = auto_execute
        self.complexity_threshold = complexity_threshold
        self.enable_logging = enable_logging
        self.enable_collaboration = enable_collaboration
        self.advanced_reasoning = advanced_reasoning
        self._stream_emitter = stream_emitter
        
        self.planner = get_task_planner(session_id, llm_provider, workspace_dir)
        self.adapter = get_todo_adapter(session_id, workspace_dir)
        self.logger = create_task_logger(f"TaskMiddleware[{session_id}]") if enable_logging else None
        
        self._collaborative_planner = None
        if self.enable_collaboration and self.advanced_reasoning:
            from .collaborative_planning import create_collaborative_planner
            self._collaborative_planner = create_collaborative_planner(
                task_planner=self.planner,
                advanced_reasoning=self.advanced_reasoning,
                enable_collaboration=True
            )
        
        self._complexity_prompt = """你是一个任务规划专家。分析用户请求，判断任务复杂度。

用户请求: {request}

请分析并以 JSON 格式返回:
{{
    "complexity": "simple|moderate|complex|very_complex",
    "estimated_steps": 估计步骤数(数字),
    "needs_planning": true或false,
    "reasoning": "判断理由，简洁"
}}

复杂度标准:
- simple: 1步可完成
- moderate: 2-3步
- complex: 4-6步
- very_complex: 7步以上

只返回 JSON。"""

        self._decomposition_prompt = """你是一个专业的任务规划师。将复杂的用户请求拆解为可执行的子任务。

用户请求: {request}
复杂度: {complexity}

请拆解任务并以 JSON 返回:
{{
    "subtasks": [
        {{
            "id": 1,
            "title": "简短标题(5字内)",
            "description": "详细描述(1-2句)",
            "depends_on": [],
            "priority": "high|medium|low"
        }}
    ],
    "overall_plan": "整体计划说明"
}}

只返回 JSON。"""

    def set_stream_emitter(self, emitter):
        """设置流式发射器"""
        self._stream_emitter = emitter

    def _emit_plan_event(self, event_type: str, **kwargs):
        """发射任务规划事件到流"""
        if not self._stream_emitter:
            return
        
        try:
            if event_type == "start":
                self._stream_emitter.emit_plan_start(
                    kwargs.get('main_task', ''),
                    kwargs.get('complexity', '')
                )
            elif event_type == "progress":
                self._stream_emitter.emit_plan_progress(
                    kwargs.get('subtasks', []),
                    kwargs.get('completed', 0),
                    kwargs.get('total', 0),
                    kwargs.get('current_task', ''),
                    kwargs.get('progress_percent', 0)
                )
            elif event_type == "complete":
                self._stream_emitter.emit_plan_complete(
                    kwargs.get('subtasks', []),
                    kwargs.get('completed', 0),
                    kwargs.get('total', 0),
                    kwargs.get('success', True),
                    kwargs.get('summary', '')
                )
        except Exception as e:
            # 静默处理，避免影响主流程
            pass

    async def process(self, user_request: str) -> PlanningResult:
        """
        处理请求，判断复杂度并决定是否需要规划
        
        如果启用了协作模式且有 AdvancedReasoning，
        则使用 CollaborativeTaskPlanner 获取带推理的执行计划
        
        Returns:
            PlanningResult: 包含复杂度判断和任务列表(如果需要)
        """
        if self.logger:
            self._log = self.logger.plan_start(user_request)
        else:
            self._log = ""
        
        complexity_result = await self._analyze_complexity(user_request)
        
        if not complexity_result['needs_planning']:
            return PlanningResult(
                is_complex=False,
                complexity=complexity_result['complexity'],
                subtasks=[],
                reasoning=complexity_result['reasoning']
            )
        
        # 发射任务规划开始事件
        self._emit_plan_event("start", main_task=user_request, complexity=complexity_result['complexity'])
        
        # 尝试使用协作式规划（TaskPlanning + AdvancedReasoning）
        if self._collaborative_planner:
            try:
                collaborative_result = await self._collaborative_planner.plan_with_collaboration(user_request)
                
                if collaborative_result.get('success'):
                    task_descriptions = [
                        f"#{t['id']}. {t['title']}" 
                        for t in collaborative_result.get('subtasks', [])
                    ]
                    
                    if task_descriptions:
                        self.adapter.call_tool('todo_clear', {})
                        self.adapter.call_tool('todo_create', {'tasks': task_descriptions})
                    
                    # 使用协作式计划
                    initial_plan = collaborative_result.get('plan', '')
                    subtasks = collaborative_result.get('subtasks', [])
                    
                    if self.logger:
                        self._log += self.logger.plan_complete(
                            complexity_result['complexity'],
                            subtasks,
                            collaborative_result.get('technical_reasoning', {})
                        )
                    
                    # 发射任务规划完成事件
                    self._emit_plan_event(
                        "complete",
                        subtasks=subtasks,
                        completed=0,
                        total=len(subtasks),
                        success=True,
                        summary=initial_plan
                    )
                    
                    return PlanningResult(
                        is_complex=True,
                        complexity=complexity_result['complexity'],
                        subtasks=subtasks,
                        reasoning=collaborative_result.get('technical_reasoning', {}),
                        initial_plan=initial_plan
                    )
            except Exception as e:
                # 协作规划失败，fallback 到普通规划
                pass
        
        # 普通规划（fallback）
        decomposition = await self._decompose_task(
            user_request, 
            complexity_result['complexity']
        )
        
        task_descriptions = [
            f"#{t['id']}. {t['title']}" 
            for t in decomposition['subtasks']
        ]
        
        if task_descriptions:
            self.adapter.call_tool('todo_clear', {})
            self.adapter.call_tool('todo_create', {'tasks': task_descriptions})
        
        if self.logger:
            self._log += self.logger.plan_complete(
                complexity_result['complexity'],
                decomposition['subtasks'],
                decomposition.get('overall_plan', '')
            )
        
        subtasks = decomposition['subtasks']
        initial_plan = self._format_initial_plan(
            user_request,
            complexity_result['complexity'],
            subtasks,
            decomposition['overall_plan']
        )
        
        # 发射任务规划完成事件
        self._emit_plan_event(
            "complete",
            subtasks=subtasks,
            completed=0,
            total=len(subtasks),
            success=True,
            summary=initial_plan
        )
        
        return PlanningResult(
            is_complex=True,
            complexity=complexity_result['complexity'],
            subtasks=subtasks,
            reasoning=decomposition['overall_plan'],
            initial_plan=initial_plan
        )

    async def _analyze_complexity(self, request: str) -> Dict[str, Any]:
        """LLM 分析任务复杂度"""
        try:
            prompt = self._complexity_prompt.format(request=request)
            response = await self.llm_provider.generate(prompt)
            
            response = self._clean_json_response(response)
            result = json.loads(response)
            
            needs_planning = (
                result.get('needs_planning', False) or
                result.get('estimated_steps', 1) >= self.complexity_threshold or
                result.get('complexity') in ['complex', 'very_complex']
            )
            
            return {
                'complexity': result.get('complexity', 'simple'),
                'estimated_steps': result.get('estimated_steps', 1),
                'needs_planning': needs_planning,
                'reasoning': result.get('reasoning', '')
            }
        except Exception as e:
            return {
                'complexity': 'simple',
                'estimated_steps': 1,
                'needs_planning': False,
                'reasoning': f'分析失败: {str(e)}，默认简单处理'
            }

    async def _decompose_task(self, request: str, complexity: str) -> Dict[str, Any]:
        """LLM 拆解任务"""
        try:
            prompt = self._decomposition_prompt.format(
                request=request,
                complexity=complexity
            )
            response = await self.llm_provider.generate(prompt)
            
            response = self._clean_json_response(response)
            result = json.loads(response)
            
            return {
                'subtasks': result.get('subtasks', []),
                'overall_plan': result.get('overall_plan', '')
            }
        except Exception as e:
            return {
                'subtasks': [],
                'overall_plan': f'拆解失败: {str(e)}'
            }

    def _clean_json_response(self, response: str) -> str:
        """清理 LLM 返回的 JSON 响应"""
        response = response.strip()
        
        json_patterns = [
            r'```json\s*(.+?)\s*```',
            r'```\s*(.+?)\s*```',
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                response = match.group(1)
                break
        
        return response

    def _format_initial_plan(
        self, 
        request: str, 
        complexity: str,
        subtasks: List[Dict],
        overall_plan: str
    ) -> str:
        """格式化初始执行计划"""
        complexity_emoji = {
            'simple': '⚡',
            'moderate': '📋',
            'complex': '🎯',
            'very_complex': '🚀'
        }
        
        emoji = complexity_emoji.get(complexity, '📋')
        
        lines = [
            f"{emoji} **任务规划完成**",
            "",
            f"📝 主任务: {request}",
            f"📊 复杂度: {complexity}",
            f"📋 步骤: {len(subtasks)} 步",
            "",
            "**执行计划:**"
        ]
        
        for i, task in enumerate(subtasks, 1):
            priority_emoji = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(task.get('priority', 'medium'), '🟡')
            
            lines.append(f"  {i}. {priority_emoji} {task['title']}")
            if task.get('description'):
                lines.append(f"     └─ {task['description']}")
        
        lines.append("")
        lines.append(f"💡 {overall_plan}")
        
        return "\n".join(lines)

    def get_progress_report(self) -> str:
        """获取当前进度报告"""
        progress = self.planner.get_execution_progress()
        
        if not progress or progress.total_tasks == 0:
            return "暂无任务进行中"
        
        bar_length = 20
        completed = progress.completed_tasks
        total = progress.total_tasks
        percentage = int(completed / total * 100) if total > 0 else 0
        
        filled = int(bar_length * completed / total) if total > 0 else 0
        bar = '█' * filled + '░' * (bar_length - filled)
        
        lines = [
            f"📊 **执行进度**: {completed}/{total} ({percentage}%)",
            f"`{bar}`",
        ]
        
        if progress.current_status:
            lines.append(f"🔄 当前: {progress.current_status}")
        
        if progress.failed_tasks > 0:
            lines.append(f"⚠️ 失败: {progress.failed_tasks}")
        
        return "\n".join(lines)


class IntelligentTaskAgent:
    """
    智能任务 Agent - 集成任务规划的 Agent
    
    自动检测复杂任务并触发规划流程
    """

    def __init__(
        self,
        llm_provider,
        session_id: str,
        workspace_dir: Optional[str] = None,
        complexity_threshold: int = 2,
        stream_emitter=None
    ):
        self.llm_provider = llm_provider
        self.session_id = session_id
        self.workspace_dir = workspace_dir
        
        self.middleware = TaskPlanningMiddleware(
            llm_provider=llm_provider,
            session_id=session_id,
            workspace_dir=workspace_dir,
            complexity_threshold=complexity_threshold,
            stream_emitter=stream_emitter
        )

    def set_stream_emitter(self, emitter):
        """设置流式发射器"""
        self.middleware.set_stream_emitter(emitter)

    async def respond(self, user_request: str) -> Dict[str, Any]:
        """
        处理用户请求，自动检测并规划复杂任务
        
        Returns:
            Dict 包含:
            - is_complex: 是否是复杂任务
            - response: 返回给用户的文本响应
            - subtasks: 子任务列表(如果复杂)
            - progress_report: 当前进度(如果执行中)
        """
        result = await self.middleware.process(user_request)
        
        if not result.is_complex:
            return {
                'is_complex': False,
                'response': f"✅ 收到请求: {user_request}",
                'subtasks': [],
                'progress_report': None
            }
        
        progress_report = self.middleware.get_progress_report()
        
        return {
            'is_complex': True,
            'response': result.initial_plan,
            'subtasks': result.subtasks,
            'progress_report': progress_report,
            'complexity': result.complexity,
            'reasoning': result.reasoning
        }

    def get_current_tasks(self) -> Dict[str, Any]:
        """获取当前任务状态"""
        progress = self.middleware.planner.get_execution_progress()
        pending = self.middleware.planner.get_pending_subtasks()
        completed = self.middleware.planner.get_completed_subtasks()
        
        return {
            'main_task': self.middleware.planner.current_plan.main_task if self.middleware.planner.current_plan else None,
            'progress': {
                'completed': progress.completed_tasks if progress else 0,
                'total': progress.total_tasks if progress else 0,
                'failed': progress.failed_tasks if progress else 0,
                'percentage': int(progress.completed_tasks / progress.total_tasks * 100) if progress and progress.total_tasks > 0 else 0
            },
            'pending': [
                {'id': t.id, 'title': t.title, 'status': t.status.value}
                for t in pending
            ],
            'completed': [
                {'id': t.id, 'title': t.title, 'result': t.result}
                for t in completed
            ]
        }