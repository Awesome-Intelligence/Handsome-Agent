#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test ContextBuilder - 上下文构建器测试

测试 ContextBuilder 的核心功能：
1. 系统提示词构建
2. 三层架构构建
3. 决策提示词

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
            enable_guidance=True
        )
    
    def test_init(self, context_builder):
        """测试初始化"""
        assert context_builder is not None
        assert context_builder.enable_guidance is True
    
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
        # 新格式为 OpenAI function calling 格式
        assert schema[0]["type"] == "function"
        assert schema[0]["function"]["name"] == "test_tool"
        assert schema[0]["function"]["description"] == "Test tool description"


class TestBuildGuidance:
    """指导性文本测试类"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(enable_guidance=True)
    
    def test_build_guidance(self, context_builder):
        """测试指导性文本构建（通过 build_parts 验证 stable 层）"""
        parts = context_builder.build_parts(user_message="", model=None, memory_context="")
        
        # 验证 stable 层包含指导性内容
        stable = parts.get("stable", "")
        assert stable is not None
        assert len(stable) > 0
        assert "Memory System" in stable
        assert "Session Search" in stable
        assert "Skills System" in stable
    
    def test_guidance_disabled(self):
        """测试禁用指导性文本"""
        from agent.context.context_builder import ContextBuilder
        cb = ContextBuilder(enable_guidance=False)
        parts = cb.build_parts(user_message="", model=None, memory_context="")

        # 验证 stable 层包含基础内容（身份和能力）
        assert "Handsome Agent" in parts["stable"]
        # 验证 stable 层不包含指导性文本
        assert "Memory System" not in parts["stable"]


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


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests - 集成测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestContextBuilderIntegration:
    """ContextBuilder 集成测试"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(
            enable_guidance=True
        )
    
    def test_full_prompt_generation(self, context_builder):
        """测试完整的提示词生成"""
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool"
        mock_tool.parameters = {}
        
        context_builder.set_tools({"test_tool": mock_tool})

        # 使用 build_messages() 测试完整上下文构建
        messages = context_builder.build_messages(
            conversation_history=[
                {"role": "user", "content": "测试消息"}
            ],
            user_message="用户偏好"
        )

        # 验证消息列表格式
        assert isinstance(messages, list)
        assert len(messages) >= 2  # system + history messages

        # 验证 system 消息包含所有关键部分
        system_msg = messages[0]
        assert system_msg.get("role") == "system"
        content = system_msg.get("content", "")
        assert "Handsome Agent" in content
        assert "能力概览" in content
        assert "User Profile" in content
        assert "Memory System" in content

        # 验证对话历史在消息列表中
        history_msgs = [msg for msg in messages if msg.get("role") == "user"]
        assert len(history_msgs) > 0
        assert "测试消息" in history_msgs[0].get("content", "")


class TestBuildMessages:
    """build_messages 测试类 - 验证上下文传递功能"""
    
    @pytest.fixture
    def context_builder(self):
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(
            tools={},
            enable_guidance=True
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