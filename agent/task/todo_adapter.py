#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TodoToolkit Adapter - 将 TodoToolkit 方法暴露为 Agent 工具调用

提供结构化的任务管理能力，让 Agent 能够：
- 创建任务列表
- 添加/完成任务
- 列出和追踪任务进度
- 持久化任务状态到文件系统
"""

import re
from typing import List, Tuple, Dict, Any, Optional, Callable
from dataclasses import dataclass

from .todo_toolkit import TodoToolkit, get_todo_toolkit, TaskStatus


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: List[Dict[str, Any]]
    handler: Callable


@dataclass
class ToolCallResult:
    """工具调用结果"""
    success: bool
    output: str
    error: Optional[str] = None


class TodoToolkitAdapter:
    """
    TodoToolkit 适配器
    将 TodoToolkit 方法转换为 Agent 可调用的工具
    """

    def __init__(self, session_id: str, workspace_dir: Optional[str] = None):
        self.session_id = session_id
        self.workspace_dir = workspace_dir
        self._toolkit: Optional[TodoToolkit] = None
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_tools()

    @property
    def toolkit(self) -> TodoToolkit:
        """懒加载获取 TodoToolkit 实例"""
        if self._toolkit is None:
            self._toolkit = get_todo_toolkit(self.session_id, self.workspace_dir)
        return self._toolkit

    def _register_tools(self):
        """注册所有 todo 工具"""
        self._tools = {
            'todo_create': ToolDefinition(
                name='todo_create',
                description='创建新的任务列表，用于初始化任务管理',
                parameters=[
                    {'name': 'tasks', 'type': 'array', 'required': True,
                     'description': '任务描述数组，如 ["任务1", "任务2", "任务3"]'}
                ],
                handler=self._handle_create
            ),
            'todo_add': ToolDefinition(
                name='todo_add',
                description='添加新任务到现有列表',
                parameters=[
                    {'name': 'task', 'type': 'string', 'required': True,
                     'description': '任务描述文本'},
                    {'name': 'index', 'type': 'integer', 'required': False,
                     'description': '插入位置索引，不指定则追加到末尾'}
                ],
                handler=self._handle_add
            ),
            'todo_complete': ToolDefinition(
                name='todo_complete',
                description='标记任务为已完成',
                parameters=[
                    {'name': 'task_id', 'type': 'integer', 'required': True,
                     'description': '任务 ID（数字）'},
                    {'name': 'result', 'type': 'string', 'required': False,
                     'description': '任务完成结果或备注'}
                ],
                handler=self._handle_complete
            ),
            'todo_cancel': ToolDefinition(
                name='todo_cancel',
                description='取消一个任务',
                parameters=[
                    {'name': 'task_id', 'type': 'integer', 'required': True,
                     'description': '任务 ID（数字）'},
                    {'name': 'reason', 'type': 'string', 'required': False,
                     'description': '取消原因'}
                ],
                handler=self._handle_cancel
            ),
            'todo_remove': ToolDefinition(
                name='todo_remove',
                description='删除一个任务',
                parameters=[
                    {'name': 'task_id', 'type': 'integer', 'required': True,
                     'description': '任务 ID（数字）'}
                ],
                handler=self._handle_remove
            ),
            'todo_list': ToolDefinition(
                name='todo_list',
                description='列出所有任务及其状态',
                parameters=[],
                handler=self._handle_list
            ),
            'todo_reset': ToolDefinition(
                name='todo_reset',
                description='重置任务列表（清除已完成的任务）',
                parameters=[],
                handler=self._handle_reset
            ),
            'todo_clear': ToolDefinition(
                name='todo_clear',
                description='清空所有任务',
                parameters=[],
                handler=self._handle_clear
            ),
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具的描述"""
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'parameters': tool.parameters
            }
            for tool in self._tools.values()
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolCallResult:
        """调用指定的工具"""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolCallResult(
                success=False,
                output="",
                error=f"未知工具: {tool_name}"
            )

        try:
            return tool.handler(arguments)
        except Exception as e:
            return ToolCallResult(
                success=False,
                output="",
                error=f"工具执行失败: {str(e)}"
            )

    def _extract_task_ids(self, text: str) -> List[int]:
        """从文本中提取任务 ID"""
        patterns = [
            r'#?(\d+)',
            r'第\s*([一二三四五六七八九十]+)\s*个',
            r'第\s*(\d+)\s*个',
        ]
        task_ids = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match.isdigit():
                    task_ids.append(int(match))
                elif isinstance(match, str) and match.isdigit():
                    task_ids.append(int(match))
        return task_ids

    def _extract_tasks_from_text(self, text: str) -> List[str]:
        """从文本中提取任务列表"""
        tasks = []

        list_patterns = [
            r'[-*]\s*(.+?)(?:\n|$)',
            r'\d+[.、](.+?)(?:\n|$)',
            r'"([^"]+)"',
            r"'([^']+)'",
        ]

        for pattern in list_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            tasks.extend([m.strip() for m in matches if m.strip()])

        if not tasks:
            cleaned = text.strip()
            if cleaned:
                tasks = [cleaned]

        return tasks

    def _handle_create(self, args: Dict[str, Any]) -> ToolCallResult:
        """处理创建任务列表"""
        tasks_input = args.get('tasks', [])

        if isinstance(tasks_input, str):
            tasks = self._extract_tasks_from_text(tasks_input)
        elif isinstance(tasks_input, list):
            tasks = tasks_input
        else:
            return ToolCallResult(
                success=False,
                output="",
                error="tasks 参数必须是数组或字符串"
            )

        if not tasks:
            return ToolCallResult(
                success=False,
                output="",
                error="未提供有效任务内容"
            )

        result = self.toolkit.todo_create(tasks)
        return ToolCallResult(success=True, output=result)

    def _handle_add(self, args: Dict[str, Any]) -> ToolCallResult:
        """处理添加任务"""
        task = args.get('task', '')
        index = args.get('index')

        if not task:
            return ToolCallResult(
                success=False,
                output="",
                error="未提供任务内容"
            )

        result = self.toolkit.todo_add(task, index)
        return ToolCallResult(success=True, output=result)

    def _handle_complete(self, args: Dict[str, Any]) -> ToolCallResult:
        """处理完成任务"""
        task_id = args.get('task_id')
        result_note = args.get('result')

        if task_id is None:
            return ToolCallResult(
                success=False,
                output="",
                error="未提供 task_id"
            )

        result = self.toolkit.todo_complete(int(task_id), result_note)
        return ToolCallResult(success=True, output=result)

    def _handle_cancel(self, args: Dict[str, Any]) -> ToolCallResult:
        """处理取消任务"""
        task_id = args.get('task_id')
        reason = args.get('reason')

        if task_id is None:
            return ToolCallResult(
                success=False,
                output="",
                error="未提供 task_id"
            )

        result = self.toolkit.todo_cancel(int(task_id), reason)
        return ToolCallResult(success=True, output=result)

    def _handle_remove(self, args: Dict[str, Any]) -> ToolCallResult:
        """处理删除任务"""
        task_id = args.get('task_id')

        if task_id is None:
            return ToolCallResult(
                success=False,
                output="",
                error="未提供 task_id"
            )

        result = self.toolkit.todo_remove(int(task_id))
        return ToolCallResult(success=True, output=result)

    def _handle_list(self, args: Dict[str, Any]) -> ToolCallResult:
        """处理列出任务"""
        result = self.toolkit.todo_list()
        return ToolCallResult(success=True, output=result)

    def _handle_reset(self, args: Dict[str, Any]) -> ToolCallResult:
        """处理重置任务列表"""
        result = self.toolkit.todo_reset()
        return ToolCallResult(success=True, output=result)

    def _handle_clear(self, args: Dict[str, Any]) -> ToolCallResult:
        """处理清空任务"""
        result = self.toolkit.todo_clear()
        return ToolCallResult(success=True, output=result)


def create_todo_adapter(session_id: str, workspace_dir: Optional[str] = None) -> TodoToolkitAdapter:
    """创建 TodoToolkit 适配器实例"""
    return TodoToolkitAdapter(session_id, workspace_dir)


_todo_adapters: Dict[str, TodoToolkitAdapter] = {}


def get_todo_adapter(session_id: str, workspace_dir: Optional[str] = None) -> TodoToolkitAdapter:
    """获取或创建 TodoToolkit 适配器实例（单例模式）"""
    if session_id not in _todo_adapters:
        _todo_adapters[session_id] = create_todo_adapter(session_id, workspace_dir)
    return _todo_adapters[session_id]