#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Planner - LLM驱动的智能任务规划与追踪系统

核心功能:
1. 任务复杂度检测 - 自动判断是否需要拆解
2. 任务自动拆解 - LLM 将复杂任务分解为子任务
3. 任务执行引擎 - 逐个执行子任务，支持依赖
4. 进度追踪汇报 - 主动向用户汇报进度

与 OpenClaw/Hermes 的差异化:
- 不需要用户说"创建任务"，自动检测复杂任务
- LLM 自主决定如何拆解，而非硬编码规则
- 多步骤任务自动追踪和汇报
"""

import json
import re
import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .todo_toolkit import TodoToolkit, TaskStatus, Task
from .todo_adapter import TodoToolkitAdapter, ToolCallResult, get_todo_adapter


class TaskComplexity(Enum):
    """任务复杂度等级"""
    SIMPLE = "simple"        # 简单任务，无需拆解
    MODERATE = "moderate"    # 中等复杂度，可选拆解
    COMPLEX = "complex"      # 复杂任务，建议拆解
    VERY_COMPLEX = "very_complex"  # 极度复杂，必须拆解


@dataclass
class SubTask:
    """子任务定义"""
    id: int
    title: str
    description: str
    status: TaskStatus = TaskStatus.WAITING
    depends_on: List[int] = field(default_factory=list)
    result: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class TaskPlan:
    """任务计划"""
    main_task: str
    subtasks: List[SubTask]
    complexity: TaskComplexity
    reasoning: str  # LLM 拆解的理由
    created_at: str


@dataclass
class ExecutionProgress:
    """执行进度"""
    current_task_id: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    current_status: str


class TaskPlanner:
    """
    LLM驱动的智能任务规划器
    
    核心流程:
    1. 接收用户请求
    2. LLM 判断复杂度
    3. 如果复杂，LLM 自动拆解
    4. 创建任务列表
    5. 执行并追踪
    """

    def __init__(self, llm_provider, session_id: str, workspace_dir: Optional[str] = None):
        self.llm_provider = llm_provider
        self.session_id = session_id
        self.workspace_dir = workspace_dir
        self.adapter = get_todo_adapter(session_id, workspace_dir)
        self.current_plan: Optional[TaskPlan] = None
        
        self._complexity_check_prompt = """你是一个任务规划专家。分析用户的请求，判断任务复杂度。

任务: {task}

请以 JSON 格式返回分析结果:
{{
    "complexity": "simple|moderate|complex|very_complex",
    "reasoning": "判断理由",
    "estimated_steps": 估计的步骤数(数字),
    "needs_decomposition": true或false，是否需要拆解
}}

复杂度定义:
- simple: 可以一步完成，无需思考
- moderate: 需要几步简单操作，2-3步
- complex: 需要多个步骤，可能需要工具调用，4-7步
- very_complex: 需要大量步骤，涉及多个领域或系统，8步以上

只返回 JSON，不要有其他内容。"""

        self._decomposition_prompt = """你是一个专业的任务规划专家。分析以下复杂任务，并将其拆解为可执行的子任务。

主任务: {main_task}
任务复杂度: {complexity}

请以 JSON 格式返回任务拆解:
{{
    "subtasks": [
        {{
            "id": 1,
            "title": "子任务标题(简短)",
            "description": "子任务详细描述",
            "depends_on": [],  // 依赖的任务ID数组，如果没有依赖则为空
            "estimated_difficulty": "easy|medium|hard"
        }},
        ...
    ],
    "execution_order": [1, 2, 3, ...],  // 推荐执行顺序
    "overall_reasoning": "整体拆解策略说明"
}}

拆解原则:
1. 每个子任务应该可以独立执行
2. 考虑任务之间的依赖关系
3. 保持子任务大小适中，便于追踪
4. 对于编程任务，至少包含：设计、实现、测试

只返回 JSON，不要有其他内容。"""

        self._progress_report_prompt = """作为任务执行助手，你需要向用户汇报任务进度。

任务计划:
主任务: {main_task}

子任务状态:
{subtasks_status}

请生成进度汇报，要求:
1. 简洁明了，突出重点
2. 使用进度条或百分比
3. 明确当前执行到哪一步
4. 预估剩余时间(如果可以)
5. 如果有失败，说明原因和建议

汇报语言: 中文，友好专业"""

    async def analyze_complexity(self, user_request: str) -> Dict[str, Any]:
        """LLM 分析任务复杂度"""
        try:
            prompt = self._complexity_check_prompt.format(task=user_request)
            response = await self.llm_provider.generate(prompt)
            
            response = response.strip()
            if response.startswith('```'):
                response = re.sub(r'```json\s*', '', response)
                response = re.sub(r'```\s*$', '', response)
            
            result = json.loads(response)
            complexity = result.get('complexity', 'simple')
            needs_planning = result.get('needs_planning', False)
            estimated_steps = result.get('estimated_steps', 1)
            
            if complexity in ['complex', 'very_complex']:
                needs_planning = True
            
            return {
                'success': True,
                'complexity': complexity,
                'reasoning': result.get('reasoning', ''),
                'estimated_steps': estimated_steps,
                'needs_decomposition': needs_planning or estimated_steps >= 3
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'complexity': 'simple',
                'needs_decomposition': False
            }

    async def decompose_task(self, user_request: str, complexity: str) -> TaskPlan:
        """LLM 将任务拆解为子任务"""
        try:
            prompt = self._decomposition_prompt.format(
                main_task=user_request,
                complexity=complexity
            )
            response = await self.llm_provider.generate(prompt)
            
            response = response.strip()
            if response.startswith('```'):
                response = re.sub(r'```json\s*', '', response)
                response = re.sub(r'```\s*$', '', response)
            
            result = json.loads(response)
            
            subtasks = []
            for item in result.get('subtasks', []):
                subtask = SubTask(
                    id=item.get('id', 0),
                    title=item.get('title', ''),
                    description=item.get('description', ''),
                    depends_on=item.get('depends_on', []),
                    created_at=datetime.now().isoformat()
                )
                subtasks.append(subtask)
            
            plan = TaskPlan(
                main_task=user_request,
                subtasks=subtasks,
                complexity=TaskComplexity(complexity),
                reasoning=result.get('overall_reasoning', ''),
                created_at=datetime.now().isoformat()
            )
            
            self.current_plan = plan
            return plan
            
        except Exception as e:
            raise Exception(f"任务拆解失败: {str(e)}")

    async def create_task_list(self, plan: TaskPlan) -> str:
        """根据计划创建任务列表"""
        task_descriptions = [f"{i+1}. {t.title}" for i, t in enumerate(plan.subtasks)]
        
        result = self.adapter.call_tool('todo_create', {
            'tasks': task_descriptions
        })
        
        if not result.success:
            raise Exception(f"创建任务列表失败: {result.error}")
        
        return result.output

    async def generate_progress_report(self) -> str:
        """生成进度汇报"""
        if not self.current_plan:
            return "暂无任务计划"
        
        plan = self.current_plan
        
        tasks_status = []
        for task in plan.subtasks:
            status_icon = {
                TaskStatus.WAITING: "⏳ 待执行",
                TaskStatus.RUNNING: "🔄 执行中",
                TaskStatus.COMPLETED: "✅ 已完成",
                TaskStatus.CANCELLED: "❌ 已取消"
            }.get(task.status, "❓ 未知")
            
            tasks_status.append(f"#{task.id} {task.title}: {status_icon}")
        
        prompt = self._progress_report_prompt.format(
            main_task=plan.main_task,
            subtasks_status="\n".join(tasks_status)
        )
        
        try:
            report = await self.llm_provider.generate(prompt)
            return report
        except Exception:
            completed = sum(1 for t in plan.subtasks if t.status == TaskStatus.COMPLETED)
            total = len(plan.subtasks)
            progress = int(completed / total * 100) if total > 0 else 0
            return f"📊 进度: {completed}/{total} ({progress}%)\n" + "\n".join(tasks_status)

    def get_execution_progress(self) -> Optional[ExecutionProgress]:
        """获取当前执行进度"""
        if not self.current_plan:
            return None
        
        plan = self.current_plan
        completed = sum(1 for t in plan.subtasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in plan.subtasks if t.status == TaskStatus.CANCELLED)
        
        current = next(
            (t for t in plan.subtasks if t.status == TaskStatus.RUNNING),
            None
        )
        
        return ExecutionProgress(
            current_task_id=current.id if current else 0,
            total_tasks=len(plan.subtasks),
            completed_tasks=completed,
            failed_tasks=failed,
            current_status=current.title if current else "无"
        )

    def update_subtask_status(self, task_id: int, status: TaskStatus, result: Optional[str] = None):
        """更新子任务状态"""
        if not self.current_plan:
            return
        
        for task in self.current_plan.subtasks:
            if task.id == task_id:
                task.status = status
                if result:
                    task.result = result
                if status == TaskStatus.RUNNING:
                    task.started_at = datetime.now().isoformat()
                elif status == TaskStatus.COMPLETED:
                    task.completed_at = datetime.now().isoformat()
                break

    def is_task_ready(self, task_id: int) -> bool:
        """检查任务是否满足执行条件（依赖已完成）"""
        if not self.current_plan:
            return False
        
        task = next((t for t in self.current_plan.subtasks if t.id == task_id), None)
        if not task:
            return False
        
        for dep_id in task.depends_on:
            dep_task = next((t for t in self.current_plan.subtasks if t.id == dep_id), None)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True

    def get_next_ready_task(self) -> Optional[SubTask]:
        """获取下一个可执行的任务"""
        if not self.current_plan:
            return None
        
        for task in self.current_plan.subtasks:
            if task.status == TaskStatus.WAITING and self.is_task_ready(task.id):
                return task
        
        return None

    def get_pending_subtasks(self) -> List[SubTask]:
        """获取待执行的任务列表"""
        if not self.current_plan:
            return []
        
        return [
            t for t in self.current_plan.subtasks 
            if t.status in [TaskStatus.WAITING, TaskStatus.RUNNING]
        ]

    def get_completed_subtasks(self) -> List[SubTask]:
        """获取已完成的任务列表"""
        if not self.current_plan:
            return []
        
        return [t for t in self.current_plan.subtasks if t.status == TaskStatus.COMPLETED]

    def is_all_completed(self) -> bool:
        """检查所有任务是否完成"""
        if not self.current_plan:
            return False
        
        return all(t.status == TaskStatus.COMPLETED for t in self.current_plan.subtasks)


class TaskExecutionEngine:
    """
    任务执行引擎
    
    负责:
    1. 按依赖顺序执行子任务
    2. 调用工具执行实际任务
    3. 追踪进度并更新状态
    4. 处理执行失败
    """

    def __init__(self, planner: TaskPlanner, tool_executor: Callable):
        self.planner = planner
        self.tool_executor = tool_executor
        self._execution_history: List[Dict[str, Any]] = []

    async def execute_plan(self, user_request: str) -> Dict[str, Any]:
        """执行整个任务计划"""
        analysis = await self.planner.analyze_complexity(user_request)
        
        if not analysis.get('needs_decomposition', False):
            return {
                'is_complex': False,
                'analysis': analysis,
                'message': '任务较简单，直接执行即可'
            }
        
        plan = await self.planner.decompose_task(
            user_request, 
            analysis['complexity']
        )
        
        task_list = await self.planner.create_task_list(plan)
        
        results = {
            'is_complex': True,
            'analysis': analysis,
            'plan': {
                'main_task': plan.main_task,
                'subtasks_count': len(plan.subtasks),
                'reasoning': plan.reasoning
            },
            'execution': []
        }
        
        while True:
            next_task = self.planner.get_next_ready_task()
            
            if not next_task:
                if self.planner.is_all_completed():
                    break
                failed_count = sum(1 for t in plan.subtasks if t.status == TaskStatus.CANCELLED)
                if failed_count > 0:
                    break
                await asyncio.sleep(0.5)
                continue
            
            self.planner.update_subtask_status(next_task.id, TaskStatus.RUNNING)
            
            try:
                task_result = await self.tool_executor(
                    next_task.title,
                    next_task.description,
                    self.planner.get_completed_subtasks()
                )
                
                if task_result.get('success', False):
                    self.planner.update_subtask_status(
                        next_task.id, 
                        TaskStatus.COMPLETED,
                        task_result.get('output', '')
                    )
                else:
                    self.planner.update_subtask_status(
                        next_task.id,
                        TaskStatus.CANCELLED,
                        task_result.get('error', '执行失败')
                    )
                
                results['execution'].append({
                    'task_id': next_task.id,
                    'task_title': next_task.title,
                    'result': task_result
                })
                
                progress = await self.planner.generate_progress_report()
                results['current_progress'] = progress
                
            except Exception as e:
                self.planner.update_subtask_status(
                    next_task.id,
                    TaskStatus.CANCELLED,
                    str(e)
                )
        
        final_report = await self.planner.generate_progress_report()
        results['final_report'] = final_report
        results['completed'] = self.planner.is_all_completed()
        
        return results


_global_planners: Dict[str, TaskPlanner] = {}


def get_task_planner(session_id: str, llm_provider, workspace_dir: Optional[str] = None) -> TaskPlanner:
    """获取或创建 TaskPlanner 实例"""
    if session_id not in _global_planners:
        _global_planners[session_id] = TaskPlanner(llm_provider, session_id, workspace_dir)
    return _global_planners[session_id]


def reset_task_planner(session_id: str) -> None:
    """重置 TaskPlanner"""
    if session_id in _global_planners:
        del _global_planners[session_id]