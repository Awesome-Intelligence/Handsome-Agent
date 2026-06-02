#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Executor - 任务执行引擎

将 LLM 拆解的子任务转换为实际的工具调用
"""

import asyncio
import re
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from .task_planner import TaskPlanner, SubTask, TaskStatus


@dataclass
class ToolCall:
    """工具调用请求"""
    tool_name: str
    arguments: Dict[str, Any]


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: str = ""
    error: Optional[str] = None
    tool_calls: List[ToolCall] = None
    subtask_id: int = 0
    
    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


class TaskExecutor:
    """
    任务执行器
    
    职责:
    1. 将子任务转换为工具调用
    2. 管理执行上下文
    3. 处理执行失败和重试
    4. 收集执行结果
    """

    def __init__(
        self, 
        planner: TaskPlanner,
        llm_provider,
        available_tools: Dict[str, Callable]
    ):
        self.planner = planner
        self.llm_provider = llm_provider
        self.available_tools = available_tools
        self.execution_context: Dict[str, Any] = {}
        
        self._task_to_tool_prompt = """你是一个任务执行规划器。根据子任务描述，决定需要调用哪些工具。

当前工具列表:
{tools_list}

子任务:
- ID: {task_id}
- 标题: {title}
- 描述: {description}

已完成的上一个任务结果（如果有）:
{previous_results}

请以 JSON 格式返回需要调用的工具:
{{
    "tool_calls": [
        {{
            "tool_name": "工具名",
            "arguments": {{"参数名": "参数值"}}
        }}
    ],
    "execution_plan": "简要执行计划说明",
    "expected_output": "预期输出格式"
}}

注意:
1. 选择最合适的工具来完成任务
2. 参数要准确匹配工具定义
3. 如果需要多个步骤，按顺序列出
4. 只返回 JSON

只返回 JSON，不要有其他内容。"""

    async def plan_tool_calls(self, subtask: SubTask) -> List[ToolCall]:
        """LLM 规划子任务需要调用的工具"""
        tools_list = "\n".join([
            f"- {name}: {tool.__doc__ or '无描述'}"
            for name, tool in self.available_tools.items()
        ])
        
        previous_results = []
        for completed in self.planner.get_completed_subtasks():
            if completed.result:
                previous_results.append(f"#{completed.id} {completed.title}: {completed.result}")
        
        prompt = self._task_to_tool_prompt.format(
            tools_list=tools_list or "无可用工具",
            task_id=subtask.id,
            title=subtask.title,
            description=subtask.description,
            previous_results="\n".join(previous_results) or "无"
        )
        
        try:
            response = await self.llm_provider.generate(prompt)
            
            response = response.strip()
            if response.startswith('```'):
                response = re.sub(r'```json\s*', '', response)
                response = re.sub(r'```\s*$', '', response)
            
            result = json.loads(response)
            
            tool_calls = []
            for call in result.get('tool_calls', []):
                tool_calls.append(ToolCall(
                    tool_name=call.get('tool_name', ''),
                    arguments=call.get('arguments', {})
                ))
            
            return tool_calls
            
        except Exception as e:
            return []

    async def execute_subtask(self, subtask: SubTask) -> ExecutionResult:
        """执行单个子任务"""
        result = ExecutionResult(success=False, subtask_id=subtask.id)
        
        try:
            tool_calls = await self.plan_tool_calls(subtask)
            result.tool_calls = tool_calls
            
            if not tool_calls:
                result.output = "无合适的工具，执行跳过"
                return result
            
            outputs = []
            for tool_call in tool_calls:
                tool_name = tool_call.tool_name
                args = tool_call.arguments
                
                if tool_name not in self.available_tools:
                    outputs.append(f"工具 {tool_name} 不存在")
                    continue
                
                tool_func = self.available_tools[tool_name]
                
                if asyncio.iscoroutinefunction(tool_func):
                    output = await tool_func(**args)
                else:
                    output = tool_func(**args)
                
                if isinstance(output, dict):
                    outputs.append(output.get('output', str(output)))
                else:
                    outputs.append(str(output))
                
                self.execution_context[f"task_{subtask.id}_last_output"] = outputs[-1]
            
            result.success = True
            result.output = "\n".join(outputs)
            
        except Exception as e:
            result.error = str(e)
            result.output = f"执行失败: {str(e)}"
        
        return result

    async def execute_all(
        self, 
        user_request: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """执行整个任务计划"""
        
        analysis = await self.planner.analyze_complexity(user_request)
        
        if not analysis.get('needs_decomposition', False):
            return {
                'type': 'simple',
                'complexity': analysis,
                'message': '任务简单，直接执行'
            }
        
        plan = await self.planner.decompose_task(
            user_request,
            analysis['complexity']
        )
        
        await self.planner.create_task_list(plan)
        
        results = {
            'type': 'complex',
            'complexity': analysis,
            'plan': {
                'main_task': plan.main_task,
                'subtasks': [
                    {'id': t.id, 'title': t.title, 'description': t.description}
                    for t in plan.subtasks
                ]
            },
            'execution': []
        }
        
        if progress_callback:
            await progress_callback({
                'stage': 'start',
                'message': f"开始执行任务计划，共 {len(plan.subtasks)} 个子任务",
                'progress': 0
            })
        
        while True:
            next_task = self.planner.get_next_ready_task()
            
            if not next_task:
                break
            
            self.planner.update_subtask_status(next_task.id, TaskStatus.RUNNING)
            
            if progress_callback:
                completed = len(self.planner.get_completed_subtasks())
                total = len(plan.subtasks)
                progress = int(completed / total * 100)
                await progress_callback({
                    'stage': 'executing',
                    'task': next_task.title,
                    'message': f"正在执行: {next_task.title}",
                    'progress': progress,
                    'completed': completed,
                    'total': total
                })
            
            task_result = await self.execute_subtask(next_task)
            
            if task_result.success:
                self.planner.update_subtask_status(
                    next_task.id,
                    TaskStatus.COMPLETED,
                    task_result.output
                )
            else:
                self.planner.update_subtask_status(
                    next_task.id,
                    TaskStatus.CANCELLED,
                    task_result.error or '执行失败'
                )
            
            results['execution'].append({
                'task_id': next_task.id,
                'task_title': next_task.title,
                'success': task_result.success,
                'output': task_result.output,
                'error': task_result.error,
                'tool_calls': [
                    {'tool': tc.tool_name, 'args': tc.arguments}
                    for tc in task_result.tool_calls
                ]
            })
        
        final_progress = self.planner.get_execution_progress()
        final_report = await self.planner.generate_progress_report()
        
        results['final_report'] = final_report
        results['completed'] = self.planner.is_all_completed()
        results['stats'] = {
            'total': final_progress.total_tasks if final_progress else len(plan.subtasks),
            'completed': final_progress.completed_tasks if final_progress else 0,
            'failed': final_progress.failed_tasks if final_progress else 0
        }
        
        if progress_callback:
            await progress_callback({
                'stage': 'complete',
                'message': final_report,
                'progress': 100,
                'completed': results['stats']['completed'],
                'total': results['stats']['total']
            })
        
        return results


import json
from .task_planner import get_task_planner


class MultiStepAgent:
    """
    多步骤任务处理 Agent
    
    与传统 Agent 的区别:
    1. 自动检测复杂任务（无需用户说"创建任务"）
    2. LLM 主动拆解子任务
    3. 自动追踪执行进度
    4. 主动向用户汇报
    """

    def __init__(
        self, 
        llm_provider,
        session_id: str,
        available_tools: Dict[str, Callable],
        workspace_dir: Optional[str] = None
    ):
        self.llm_provider = llm_provider
        self.session_id = session_id
        self.workspace_dir = workspace_dir or os.path.expanduser("~/.handsome-agent")
        
        self.planner = get_task_planner(session_id, llm_provider, workspace_dir)
        self.executor = TaskExecutor(self.planner, llm_provider, available_tools)
        
        self._complexity_threshold = 2  # 估计步骤数 > 2 则认为复杂

    async def process(self, user_request: str) -> Dict[str, Any]:
        """
        处理用户请求
        
        自动判断是否需要任务规划:
        - 简单任务: 直接执行
        - 复杂任务: LLM 拆解 → 创建任务列表 → 执行 → 汇报
        """
        analysis = await self.planner.analyze_complexity(user_request)
        
        if not analysis.get('needs_decomposition', False):
            return {
                'type': 'simple',
                'request': user_request,
                'analysis': analysis
            }
        
        execution_result = await self.executor.execute_all(user_request)
        
        return execution_result

    def get_current_tasks(self) -> List[Dict[str, Any]]:
        """获取当前活跃任务"""
        pending = self.planner.get_pending_subtasks()
        completed = self.planner.get_completed_subtasks()
        
        return {
            'pending': [
                {'id': t.id, 'title': t.title, 'status': t.status.value}
                for t in pending
            ],
            'completed': [
                {'id': t.id, 'title': t.title, 'result': t.result}
                for t in completed
            ],
            'progress': self.planner.get_execution_progress()
        }


import os