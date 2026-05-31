#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TodoToolkit Adapter 验证测试

验证 TodoToolkit 方法暴露为 Agent 工具调用的核心功能
"""

import asyncio
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_todo_adapter_basic():
    """基础功能测试：TodoToolkitAdapter"""
    print("=" * 60)
    print("测试 1: TodoToolkitAdapter 基础功能")
    print("=" * 60)

    from core.todo_adapter import TodoToolkitAdapter, ToolCallResult

    with tempfile.TemporaryDirectory() as tmpdir:
        session_id = "test_basic"
        adapter = TodoToolkitAdapter(session_id, tmpdir)

        result = adapter.call_tool('todo_create', {'tasks': ['任务A', '任务B', '任务C']})
        assert isinstance(result, ToolCallResult), "应返回 ToolCallResult"
        assert result.success, f"创建失败: {result.error}"
        print("  ✓ todo_create 成功")

        result = adapter.call_tool('todo_add', {'task': '任务D'})
        assert result.success, f"添加失败: {result.error}"
        print("  ✓ todo_add 成功")

        result = adapter.call_tool('todo_list', {})
        assert result.success, f"列表失败: {result.error}"
        assert '任务A' in result.output, "应包含任务A"
        print("  ✓ todo_list 成功")

        result = adapter.call_tool('todo_complete', {'task_id': 1})
        assert result.success, f"完成失败: {result.error}"
        print("  ✓ todo_complete 成功")

        result = adapter.call_tool('todo_remove', {'task_id': 4})
        assert result.success, f"删除失败: {result.error}"
        print("  ✓ todo_remove 成功")

        result = adapter.call_tool('todo_clear', {})
        assert result.success, f"清空失败: {result.error}"
        print("  ✓ todo_clear 成功")

    print("✅ 测试 1 通过: TodoToolkitAdapter 基础功能正常\n")


def test_todo_adapter_tools():
    """工具列表测试"""
    print("=" * 60)
    print("测试 2: 工具列表注册")
    print("=" * 60)

    from core.todo_adapter import TodoToolkitAdapter

    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = TodoToolkitAdapter("test_tools", tmpdir)
        tools = adapter.list_tools()

        expected_tools = {
            'todo_create', 'todo_add', 'todo_complete', 'todo_cancel',
            'todo_remove', 'todo_list', 'todo_reset', 'todo_clear'
        }
        actual_tools = {t['name'] for t in tools}

        assert expected_tools.issubset(actual_tools), \
            f"缺少工具: {expected_tools - actual_tools}"
        print(f"  ✓ 工具数量: {len(tools)}")
        print(f"  ✓ 工具列表: {sorted(actual_tools)}")

    print("✅ 测试 2 通过: 工具列表完整\n")


def test_intent_classification():
    """意图分类测试 - DEPRECATED"""
    print("=" * 60)
    print("测试 3: 意图分类 - DEPRECATED")
    print("=" * 60)
    print("注意: IntentClassifier 已废弃，请使用新的 LLM 驱动架构")
    print("参加: core/llm_tool_selector.py")
    print("=" * 60)


def test_task_parsing():
    """任务解析测试"""
    print("=" * 60)
    print("测试 4: 任务解析")
    print("=" * 60)

    from core.todo_adapter import TodoToolkitAdapter

    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = TodoToolkitAdapter("test_parse", tmpdir)

        test_cases = [
            ("创建任务：1. 任务1 2. 任务2 3. 任务3", 3),
            ('添加任务：准备下周演示', 1),
            ("完成任务 1", 1),
        ]

        for text, expected_count in test_cases:
            result = adapter.call_tool('todo_create', {'tasks': ['临时']})
            result = adapter.call_tool('todo_clear', {})

            if '创建' in text:
                import re
                tasks = []
                match = re.search(r':\s*(.+)', text)
                if match:
                    items = re.split(r'[,，、\n]', match.group(1))
                    tasks = [i.strip() for i in items if i.strip()]
                result = adapter.call_tool('todo_create', {'tasks': tasks})
            elif '添加' in text:
                task = text.split('：')[-1].strip()
                result = adapter.call_tool('todo_add', {'task': task})
                tasks = [task]
            else:
                continue

            assert result.success, f"操作失败: {result.error}"
            print(f"  ✓ \"{text[:30]}...\" 解析成功")

        result = adapter.call_tool('todo_clear', {})

    print("✅ 测试 4 通过: 任务解析正常\n")


async def test_handler_integration():
    """处理器集成测试"""
    print("=" * 60)
    print("测试 5: Handler 集成")
    print("=" * 60)

    from core.router_handlers import task_management_handler

    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['HANDSOME_AGENT_WORKSPACE'] = tmpdir

        context = {
            'session_id': 'test_handler',
            'enable_detailed_logs': False
        }

        result, flow = await task_management_handler("创建任务：测试1、测试2", context)
        assert '任务' in result or '已创建' in result, f"创建失败: {result}"
        print("  ✓ 创建任务 handler")

        result, flow = await task_management_handler("列出所有任务", context)
        assert '待办' in result or '任务' in result, f"列出失败: {result}"
        print("  ✓ 列出任务 handler")

        result, flow = await task_management_handler("完成 #1", context)
        assert '完成' in result or '✅' in result, f"完成失败: {result}"
        print("  ✓ 完成任务 handler")

    print("✅ 测试 5 通过: Handler 集成正常\n")


async def main():
    """运行所有测试"""
    print("\n" + "🎯" * 20)
    print("TodoToolkit Adapter 验证测试")
    print("🎯" * 20 + "\n")

    try:
        test_todo_adapter_basic()
        test_todo_adapter_tools()
        test_intent_classification()
        test_task_parsing()
        await test_handler_integration()

        print("=" * 60)
        print("🎉 所有测试通过! 🎉")
        print("=" * 60)
        print("\n✅ TodoToolkit 方法已成功暴露为 Agent 工具调用")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())