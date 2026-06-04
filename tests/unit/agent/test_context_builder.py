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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])