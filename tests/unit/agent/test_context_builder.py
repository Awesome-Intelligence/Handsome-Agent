#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test ContextBuilder - 上下文构建器测试

测试 ContextBuilder 的核心功能：
1. 系统提示词构建
2. 记忆预取（memory_prefetch）
3. 记忆检索算法
4. ReAct 决策提示词

日志子层：💾 Context
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any


class TestContextBuilder:
    """ContextBuilder 测试类"""
    
    @pytest.fixture
    def context_builder(self):
        """创建 ContextBuilder 实例"""
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(
            tools={},
            enable_guidance=True,
            enable_memory_prefetch=True
        )
    
    def test_init(self, context_builder):
        """测试初始化"""
        assert context_builder is not None
        assert context_builder.enable_guidance is True
        assert context_builder.enable_memory_prefetch is True
    
    def test_set_tools(self, context_builder):
        """测试设置工具"""
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool"
        mock_tool.parameters = {}
        
        context_builder.set_tools({"test_tool": mock_tool})
        assert len(context_builder.tools) == 1
        assert "test_tool" in context_builder.tools
    
    def test_get_tools_schema(self, context_builder):
        """测试获取工具 Schema"""
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool description"
        mock_tool.parameters = {"type": "string"}
        
        context_builder.set_tools({"test_tool": mock_tool})
        schema = context_builder.get_tools_schema()
        
        assert len(schema) == 1
        assert schema[0]["name"] == "test_tool"
        assert schema[0]["description"] == "Test tool description"


class TestBuildSystemPrompt:
    """build_system_prompt 测试类"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(
            tools={},
            enable_guidance=True,
            enable_memory_prefetch=False  # 关闭记忆预取简化测试
        )
    
    def test_build_system_prompt_basic(self, context_builder):
        """测试基本提示词构建"""
        prompt = context_builder.build_system_prompt()
        
        assert prompt is not None
        assert len(prompt) > 0
        assert "Handsome Agent" in prompt
    
    def test_build_system_prompt_with_identity(self, context_builder):
        """测试身份定义"""
        prompt = context_builder.build_system_prompt()
        
        assert "Agent Definition" in prompt
        assert "能力边界" in prompt
        assert "你能做的" in prompt
    
    def test_build_system_prompt_with_capabilities(self, context_builder):
        """测试能力清单"""
        prompt = context_builder.build_system_prompt()
        
        assert "能力概览" in prompt
        assert "Intent Recognition" in prompt
    
    def test_build_system_prompt_with_user_profile(self, context_builder):
        """测试用户画像"""
        prompt = context_builder.build_system_prompt()
        
        assert "User Profile" in prompt
    
    def test_build_system_prompt_with_memory_guidance(self, context_builder):
        """测试记忆使用指南"""
        prompt = context_builder.build_system_prompt()
        
        assert "Memory System" in prompt
        assert "memory" in prompt.lower()
    
    def test_build_system_prompt_with_history(self, context_builder):
        """测试对话历史"""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        prompt = context_builder.build_system_prompt(conversation_history=history)
        
        assert "Recent conversation" in prompt
        assert "Hello" in prompt
        assert "Hi there!" in prompt
    
    def test_build_system_prompt_empty_history(self, context_builder):
        """测试空历史"""
        prompt = context_builder.build_system_prompt(conversation_history=[])
        
        assert "Recent conversation" not in prompt


class TestMemoryPrefetch:
    """记忆预取测试类"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(
            tools={},
            enable_guidance=False,
            enable_memory_prefetch=True
        )
    
    def test_prefetch_memories_empty_query(self, context_builder):
        """测试空查询"""
        result = context_builder._prefetch_memories("")
        assert result == ""
    
    def test_prefetch_memories_no_entries(self, context_builder):
        """测试无记忆条目"""
        # 使用 patch.object 方式 mock 私有属性 _memory_store
        with patch.object(context_builder, '_memory_store', None):
            # 重新访问 memory_store 会触发加载，但文件不存在
            # 这里测试空结果路径
            pass
        
        # 直接测试 find_relevant_memories 方法
        result = context_builder._find_relevant_memories("用户偏好", [])
        assert len(result) == 0


class TestFindRelevantMemories:
    """记忆检索测试类"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder()
    
    def test_find_relevant_exact_match(self, context_builder):
        """测试精确匹配"""
        entries = ["用户偏好使用简洁回复"]
        result = context_builder._find_relevant_memories("用户偏好", entries)
        
        assert len(result) == 1
        assert result[0] == "用户偏好使用简洁回复"
    
    def test_find_relevant_partial_match(self, context_builder):
        """测试部分匹配"""
        entries = [
            "用户偏好使用简洁回复",
            "用户是 Python 开发者",
            "今天的天气很好"
        ]
        result = context_builder._find_relevant_memories("Python", entries)
        
        assert len(result) >= 1
        assert "Python" in result[0] or "python" in result[0].lower()
    
    def test_find_relevant_no_match(self, context_builder):
        """测试无匹配"""
        entries = ["用户偏好使用简洁回复"]
        result = context_builder._find_relevant_memories("咖啡", entries)
        
        assert len(result) == 0
    
    def test_find_relevant_empty_entries(self, context_builder):
        """测试空条目列表"""
        result = context_builder._find_relevant_memories("用户偏好", [])
        assert len(result) == 0
    
    def test_find_relevant_max_entries(self, context_builder):
        """测试限制返回条目数"""
        entries = [
            "测试条目1",
            "测试条目2",
            "测试条目3",
            "测试条目4",
            "测试条目5",
            "测试条目6"
        ]
        result = context_builder._find_relevant_memories("测试", entries, max_entries=3)
        
        assert len(result) <= 3


class TestFormatMemoryContext:
    """记忆上下文格式化测试类"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder()
    
    def test_format_empty_entries(self, context_builder):
        """测试空条目"""
        result = context_builder._format_memory_context([])
        assert result == ""
    
    def test_format_single_entry(self, context_builder):
        """测试单一条目"""
        entries = ["用户偏好使用简洁回复"]
        result = context_builder._format_memory_context(entries)
        
        assert "<memory-context>" in result
        assert "用户偏好使用简洁回复" in result
        assert "</memory-context>" in result
    
    def test_format_multiple_entries(self, context_builder):
        """测试多条目"""
        entries = [
            "用户偏好使用简洁回复",
            "用户是 Python 开发者"
        ]
        result = context_builder._format_memory_context(entries)
        
        assert "用户偏好使用简洁回复" in result
        assert "用户是 Python 开发者" in result


class TestBuildGuidance:
    """指导性文本测试类"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(enable_guidance=True)
    
    def test_build_guidance(self, context_builder):
        """测试指导性文本构建"""
        guidance = context_builder._build_guidance()
        
        assert guidance is not None
        assert len(guidance) > 0
        assert "Memory System" in guidance
        assert "Session Search" in guidance
        assert "Skills System" in guidance
    
    def test_guidance_disabled(self):
        """测试禁用指导性文本"""
        from agent.context.context_builder import ContextBuilder
        cb = ContextBuilder(enable_guidance=False)
        prompt = cb.build_system_prompt()
        
        # 指导性文本应该在 build_system_prompt 中被跳过
        # 但基础内容仍应该存在
        assert "Handsome Agent" in prompt


class TestGetUserProfile:
    """用户画像测试类"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder()
    
    def test_get_user_profile_returns_content(self, context_builder):
        """测试用户画像返回内容"""
        profile = context_builder._get_user_profile()
        
        assert profile is not None
        assert "User Profile" in profile
        # 内容可能来自文件或默认模板
        assert len(profile) > 0


class TestBuildReactDecisionPrompt:
    """ReAct 决策提示词测试类"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(
            tools={},
            enable_guidance=False,
            enable_memory_prefetch=False
        )
    
    def test_build_react_decision_prompt(self, context_builder):
        """测试基本 ReAct 决策提示词"""
        prompt = context_builder.build_react_decision_prompt(
            task_description="测试任务"
        )
        
        assert prompt is not None
        assert "测试任务" in prompt
        assert "Current Task" in prompt
        assert "Recent Conversation" in prompt
        assert "Available Tools" in prompt
    
    def test_build_react_decision_prompt_with_history(self, context_builder):
        """测试带历史的 ReAct 决策提示词"""
        history = [
            {"role": "user", "content": "之前的问题"}
        ]
        prompt = context_builder.build_react_decision_prompt(
            task_description="继续任务",
            conversation_history=history
        )
        
        assert "之前的问题" in prompt


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests - 集成测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestContextBuilderIntegration:
    """ContextBuilder 集成测试"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(
            enable_guidance=True,
            enable_memory_prefetch=True
        )
    
    def test_full_prompt_generation(self, context_builder):
        """测试完整的提示词生成"""
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool"
        mock_tool.parameters = {}
        
        context_builder.set_tools({"test_tool": mock_tool})
        
        prompt = context_builder.build_system_prompt(
            conversation_history=[
                {"role": "user", "content": "测试消息"}
            ],
            user_message="用户偏好"
        )
        
        # 验证所有关键部分都存在
        assert "Handsome Agent" in prompt
        assert "能力概览" in prompt
        assert "User Profile" in prompt
        assert "Memory System" in prompt
        assert "Recent conversation" in prompt
    
    def test_prompt_with_memory_prefetch_disabled(self, context_builder):
        """测试禁用记忆预取时的提示词生成"""
        # 禁用记忆预取
        context_builder.enable_memory_prefetch = False
        
        prompt = context_builder.build_system_prompt(
            user_message="用户偏好"
        )
        
        # 基础内容仍应该存在
        assert "Handsome Agent" in prompt
        assert "能力概览" in prompt


class TestBuildMessages:
    """build_messages 测试类 - 验证上下文传递功能"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(
            tools={},
            enable_guidance=True,
            enable_memory_prefetch=False  # 关闭记忆预取简化测试
        )
    
    def test_build_messages_returns_list_format(self, context_builder):
        """验证返回消息列表格式"""
        messages = context_builder.build_messages()
        
        assert isinstance(messages, list), "返回结果应该是列表"
        assert len(messages) > 0, "消息列表不应为空"
        
        # 验证每条消息的格式
        for msg in messages:
            assert "role" in msg, "每条消息必须包含 role 字段"
            assert msg["role"] in ["system", "user", "assistant", "tool"], \
                f"未知的消息角色: {msg['role']}"
    
    def test_build_messages_contains_system_message(self, context_builder):
        """验证包含系统消息"""
        messages = context_builder.build_messages()
        
        # 第一条必须是系统消息
        assert messages[0]["role"] == "system"
        assert "content" in messages[0]
        assert len(messages[0]["content"]) > 0, "系统消息内容不应为空"
        
        # 验证系统消息包含关键内容
        content = messages[0]["content"]
        assert "Handsome Agent" in content or "Agent" in content, \
            "系统消息应包含 Agent 身份定义"
    
    def test_build_messages_contains_history(self, context_builder):
        """验证历史消息被正确添加"""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        messages = context_builder.build_messages(conversation_history=history)
        
        # 应该有 system + 2条历史消息
        assert len(messages) >= 3, f"期望至少3条消息，实际 {len(messages)} 条"
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Hi there!"
    
    def test_build_messages_tool_calls_format(self, context_builder):
        """验证工具调用格式正确"""
        history = [
            {"role": "user", "content": "List files"},
            {"role": "assistant", "content": "I'll list the files", "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "file_list",
                        "arguments": "{}"
                    }
                }
            ]},
            {"role": "tool", "tool_call_id": "call_1", "content": "file1.txt\nfile2.txt"}
        ]
        messages = context_builder.build_messages(conversation_history=history)
        
        # 找到包含 tool_calls 的消息
        tool_call_msg = None
        for msg in messages:
            if "tool_calls" in msg:
                tool_call_msg = msg
                break
        
        assert tool_call_msg is not None, "应该包含 tool_calls 的消息"
        assert tool_call_msg["role"] == "assistant", "工具调用消息应该是 assistant 角色"
        
        # 验证 tool_calls 格式
        tool_calls = tool_call_msg["tool_calls"]
        assert len(tool_calls) == 1, "应该有1个工具调用"
        
        tc = tool_calls[0]
        assert "id" in tc, "tool_call 必须包含 id"
        assert "type" in tc, "tool_call 必须包含 type"
        assert tc["type"] == "function", "tool_call type 应该是 function"
        assert "function" in tc, "tool_call 必须包含 function"
        assert "name" in tc["function"], "function 必须包含 name"
        assert "arguments" in tc["function"], "function 必须包含 arguments"
        
        # 验证工具名
        assert tc["function"]["name"] == "file_list", "工具名应该是 file_list"
    
    def test_build_messages_tool_results_format(self, context_builder):
        """验证工具结果格式正确"""
        history = [
            {"role": "user", "content": "Search memory"},
            {"role": "assistant", "content": "", "tool_calls": [
                {"id": "call_abc123", "type": "function", "function": {
                    "name": "memory_search",
                    "arguments": '{"query": "test"}'
                }}
            ]},
            {"role": "tool", "tool_call_id": "call_abc123", "content": '{"entries": ["user prefers concise replies"]}'}
        ]
        messages = context_builder.build_messages(conversation_history=history)
        
        # 找到 tool 结果消息
        tool_result_msg = None
        for msg in messages:
            if msg.get("role") == "tool" and msg.get("tool_call_id") == "call_abc123":
                tool_result_msg = msg
                break
        
        assert tool_result_msg is not None, "应该包含 tool 结果消息"
        assert tool_result_msg["role"] == "tool", "工具结果角色应该是 tool"
        assert "tool_call_id" in tool_result_msg, "tool 结果必须包含 tool_call_id"
        assert tool_result_msg["tool_call_id"] == "call_abc123", "tool_call_id 应该匹配"
        assert "content" in tool_result_msg, "tool 结果必须包含 content"
        assert tool_result_msg["content"] == '{"entries": ["user prefers concise replies"]}'
    
    def test_build_messages_basic(self, context_builder):
        """测试基本消息列表构建"""
        messages = context_builder.build_messages()
        
        assert messages is not None
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"
        assert "content" in messages[0]
    
    def test_build_messages_with_history(self, context_builder):
        """测试带历史的消息列表"""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        messages = context_builder.build_messages(conversation_history=history)
        
        # 应该有 system + 2条历史消息
        assert len(messages) >= 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Hi there!"
    
    def test_build_messages_with_tool_calls(self, context_builder):
        """测试带工具调用的消息列表"""
        history = [
            {"role": "user", "content": "List files"},
            {"role": "assistant", "content": "I'll list the files", "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "file_list",
                        "arguments": "{}"
                    }
                }
            ]},
            {"role": "tool", "tool_call_id": "call_1", "content": "file1.txt\nfile2.txt"}
        ]
        messages = context_builder.build_messages(conversation_history=history)
        
        # 找到包含 tool_calls 的消息
        tool_call_msg = None
        for msg in messages:
            if "tool_calls" in msg:
                tool_call_msg = msg
                break
        
        assert tool_call_msg is not None
        assert tool_call_msg["role"] == "assistant"
        assert len(tool_call_msg["tool_calls"]) == 1
        assert tool_call_msg["tool_calls"][0]["function"]["name"] == "file_list"
        
        # 找到 tool 结果消息
        tool_result_msg = None
        for msg in messages:
            if msg.get("role") == "tool" and msg.get("tool_call_id") == "call_1":
                tool_result_msg = msg
                break
        
        assert tool_result_msg is not None
        assert tool_result_msg["content"] == "file1.txt\nfile2.txt"
    
    def test_build_messages_with_simplified_tool_calls(self, context_builder):
        """测试简化格式的工具调用"""
        history = [
            {"role": "user", "content": "Search memory"},
            {"role": "assistant", "content": "", "tool_calls": [
                {"name": "memory", "arguments": {"query": "test"}}
            ]}
        ]
        messages = context_builder.build_messages(conversation_history=history)
        
        # 找到包含 tool_calls 的消息
        tool_call_msg = None
        for msg in messages:
            if "tool_calls" in msg:
                tool_call_msg = msg
                break
        
        assert tool_call_msg is not None
        assert len(tool_call_msg["tool_calls"]) == 1
        assert tool_call_msg["tool_calls"][0]["function"]["name"] == "memory"
    
    def test_build_messages_empty_history(self, context_builder):
        """测试空历史"""
        messages = context_builder.build_messages(conversation_history=[])
        
        # 只有 system 消息
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
    
    def test_build_messages_system_content(self, context_builder):
        """测试系统消息内容"""
        messages = context_builder.build_messages()
        
        system_msg = messages[0]
        assert "Handsome Agent" in system_msg["content"]
        assert "能力概览" in system_msg["content"]
        assert "User Profile" in system_msg["content"]
    
    def test_build_messages_none_history(self, context_builder):
        """测试 None 历史"""
        messages = context_builder.build_messages(conversation_history=None)
        
        # 只有 system 消息
        assert len(messages) == 1
        assert messages[0]["role"] == "system"


class TestNormalizeToolCalls:
    """工具调用标准化测试类"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder()
    
    def test_normalize_openai_format(self, context_builder):
        """测试 OpenAI 格式标准化"""
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "arguments": '{"param": "value"}'
                }
            }
        ]
        result = context_builder._normalize_tool_calls(tool_calls)
        
        assert len(result) == 1
        assert result[0]["id"] == "call_123"
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "test_tool"
    
    def test_normalize_simplified_format(self, context_builder):
        """测试简化格式标准化"""
        tool_calls = [
            {"name": "test_tool", "arguments": {"param": "value"}}
        ]
        result = context_builder._normalize_tool_calls(tool_calls)
        
        assert len(result) == 1
        assert result[0]["id"] == "call_0"
        assert result[0]["function"]["name"] == "test_tool"
        assert '{"param"' in result[0]["function"]["arguments"]
    
    def test_normalize_empty(self, context_builder):
        """测试空工具调用"""
        result = context_builder._normalize_tool_calls([])
        assert result == []
    
    def test_normalize_none(self, context_builder):
        """测试 None 工具调用"""
        result = context_builder._normalize_tool_calls(None)
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])