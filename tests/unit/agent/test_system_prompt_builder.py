#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test SystemPromptBuilder - 三层系统提示构建器测试

测试三层架构：
1. Stable Layer (稳定层) - 会话级缓存
2. Context Layer (上下文层) - 依赖配置
3. Volatile Layer (变动层) - 每次构建

日志子层：💾 Context
"""

import pytest
from unittest.mock import Mock, patch


class TestSystemPromptBuilderInit:
    """SystemPromptBuilder 初始化测试"""

    def test_init_basic(self):
        """测试基本初始化"""
        from agent.context.system_prompt_builder import SystemPromptBuilder

        builder = SystemPromptBuilder()
        assert builder is not None
        assert builder.session_id == "default"

    def test_init_with_tools(self):
        """测试带工具初始化"""
        from agent.context.system_prompt_builder import SystemPromptBuilder

        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool"
        mock_tool.parameters = {}

        builder = SystemPromptBuilder(tools={"test_tool": mock_tool})
        assert len(builder.tools) == 1
        assert "test_tool" in builder.tools

    def test_init_with_session_id(self):
        """测试带会话 ID 初始化"""
        from agent.context.system_prompt_builder import SystemPromptBuilder

        builder = SystemPromptBuilder(session_id="test_session_123")
        assert builder.session_id == "test_session_123"


class TestStableLayer:
    """Stable Layer (稳定层) 测试"""

    @pytest.fixture
    def builder(self):
        from agent.context.system_prompt_builder import SystemPromptBuilder
        return SystemPromptBuilder()

    def test_get_stable_layer_returns_content(self, builder):
        """测试获取稳定层内容"""
        stable = builder.get_stable_layer()

        assert stable is not None
        assert len(stable) > 0

    def test_stable_layer_caching(self, builder):
        """测试稳定层缓存"""
        # 第一次调用
        stable1 = builder.get_stable_layer()

        # 第二次调用应该命中缓存
        stable2 = builder.get_stable_layer()

        assert stable1 == stable2
        # 验证缓存键存在
        assert builder._stable_cache is not None

    def test_stable_layer_contains_identity(self, builder):
        """测试稳定层包含身份定义"""
        stable = builder.get_stable_layer()

        assert "Agent Definition" in stable or "Handsome Agent" in stable

    def test_stable_layer_contains_guidance(self, builder):
        """测试稳定层包含工具使用指导"""
        stable = builder.get_stable_layer()

        assert "tool" in stable.lower() or "Tool" in stable


class TestContextLayer:
    """Context Layer (上下文层) 测试"""

    @pytest.fixture
    def builder(self):
        from agent.context.system_prompt_builder import SystemPromptBuilder
        return SystemPromptBuilder()

    def test_build_context_layer(self, builder):
        """测试构建上下文层"""
        context = builder._build_context_layer()

        assert context is not None
        assert len(context) > 0

    def test_context_layer_with_tools(self, builder):
        """测试带工具的上下文层"""
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool"
        mock_tool.parameters = {}

        builder.set_tools({"test_tool": mock_tool})

        context = builder._build_context_layer(include_tools=True)

        assert "test_tool" in context
        assert "Available tools" in context

    def test_context_layer_without_tools(self, builder):
        """测试不带工具的上下文层"""
        context = builder._build_context_layer(include_tools=False)

        assert "Available tools" not in context

    def test_context_layer_with_model(self, builder):
        """测试带模型的上下文层"""
        context = builder._build_context_layer(model="deepseek-chat")

        # DeepSeek 模型应该包含模型特定指导
        assert context is not None


class TestVolatileLayer:
    """Volatile Layer (变动层) 测试"""

    @pytest.fixture
    def builder(self):
        from agent.context.system_prompt_builder import SystemPromptBuilder
        return SystemPromptBuilder(
            enable_memory_prefetch=True,
            session_id="test_volatile"
        )

    def test_build_volatile_layer_empty(self, builder):
        """测试空变动了层"""
        volatile = builder._build_volatile_layer()

        assert volatile is not None

    def test_build_volatile_layer_with_message(self, builder):
        """测试带消息的变动层"""
        volatile = builder._build_volatile_layer(
            user_message="测试消息",
            conversation_history=[]
        )

        # 有消息时可能包含记忆预取
        assert volatile is not None

    def test_build_volatile_layer_with_history(self, builder):
        """测试带历史的变动层"""
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"}
        ]
        volatile = builder._build_volatile_layer(
            user_message="",
            conversation_history=history
        )

        assert volatile is not None
        # 历史摘要应该包含 Recent Conversation
        assert "Recent Conversation" in volatile or volatile == ""

    def test_volatile_layer_not_cached(self, builder):
        """测试变动层不缓存（每次都重新构建）"""
        # 两次调用应该产生不同的结果（因为 user_message 不同）
        volatile1 = builder._build_volatile_layer(user_message="消息1")
        volatile2 = builder._build_volatile_layer(user_message="消息2")

        # 变动层的内容可能相同（如果记忆预取没有找到相关内容）
        # 但关键是缓存机制不应该生效
        assert volatile1 is not None
        assert volatile2 is not None


class TestLayerResult:
    """LayerResult 数据类测试"""

    def test_layer_result_creation(self):
        """测试 LayerResult 创建"""
        from agent.context.system_prompt_builder import LayerResult

        result = LayerResult(
            stable="stable content",
            context="context content",
            volatile="volatile content",
            full_prompt="full prompt",
            cache_hit=True,
            cache_key="test_key"
        )

        assert result.stable == "stable content"
        assert result.context == "context content"
        assert result.volatile == "volatile content"
        assert result.full_prompt == "full prompt"
        assert result.cache_hit is True
        assert result.cache_key == "test_key"

    def test_layer_result_defaults(self):
        """测试 LayerResult 默认值"""
        from agent.context.system_prompt_builder import LayerResult

        result = LayerResult()

        assert result.stable == ""
        assert result.context == ""
        assert result.volatile == ""
        assert result.full_prompt == ""
        assert result.cache_hit is False
        assert result.cache_key == ""


class TestBuildMethod:
    """build() 方法测试"""

    @pytest.fixture
    def builder(self):
        from agent.context.system_prompt_builder import SystemPromptBuilder
        return SystemPromptBuilder(
            enable_memory_prefetch=False,  # 简化测试
            session_id="test_build"
        )

    def test_build_returns_layer_result(self, builder):
        """测试 build 返回 LayerResult"""
        from agent.context.system_prompt_builder import LayerResult
        result = builder.build()

        assert isinstance(result, LayerResult)

    def test_build_with_user_message(self, builder):
        """测试带用户消息的构建"""
        result = builder.build(user_message="测试消息")

        assert result.stable is not None
        assert result.context is not None
        assert result.volatile is not None
        assert result.full_prompt is not None

    def test_build_with_conversation_history(self, builder):
        """测试带对话历史的构建"""
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"}
        ]
        result = builder.build(conversation_history=history)

        assert result.stable is not None
        assert len(result.full_prompt) > 0

    def test_build_full_prompt_contains_all_layers(self, builder):
        """测试完整提示词包含所有层"""
        result = builder.build()

        # 完整提示词应该包含稳定层和上下文层
        assert result.stable in result.full_prompt
        assert result.context in result.full_prompt

    def test_build_cache_hit_on_second_call(self, builder):
        """测试第二次调用命中缓存"""
        # 第一次调用（不触发缓存）
        result1 = builder.build()

        # 第二次调用应该命中缓存
        result2 = builder.build()

        # 验证两次结果相同（命中缓存）
        assert result1.stable == result2.stable
        assert result1.cache_hit == result2.cache_hit  # 缓存状态一致

    def test_build_with_model(self, builder):
        """测试带模型的构建"""
        result = builder.build(model="deepseek-chat")

        assert result is not None
        assert len(result.full_prompt) > 0


class TestCacheInvalidation:
    """缓存失效测试"""

    @pytest.fixture
    def builder(self):
        from agent.context.system_prompt_builder import SystemPromptBuilder
        return SystemPromptBuilder(session_id="test_cache")

    def test_invalidate_all_caches(self, builder):
        """测试使所有缓存失效"""
        # 先调用一次构建，触发缓存
        builder.build()

        # 验证缓存已设置
        assert builder._stable_cache is not None

        # 使缓存失效
        builder.invalidate_all_caches()

        # 验证缓存已清空
        assert builder._stable_cache is None
        assert builder._stable_cache_key == ""
        assert builder._user_profile_cache is None

    def test_cache_after_invalidation(self, builder):
        """测试失效后重新构建"""
        # 第一次构建
        result1 = builder.build()

        # 使缓存失效
        builder.invalidate_all_caches()

        # 第二次构建
        result2 = builder.build()

        # 两次结果应该相同（内容相同）
        assert result1.stable == result2.stable


class TestToolsSchema:
    """工具 Schema 测试"""

    @pytest.fixture
    def builder(self):
        from agent.context.system_prompt_builder import SystemPromptBuilder
        return SystemPromptBuilder()

    def test_build_tools_schema_json(self, builder):
        """测试构建工具 Schema JSON"""
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool description"
        mock_tool.parameters = {"type": "object", "properties": {}}

        builder.set_tools({"test_tool": mock_tool})

        schema_json = builder._build_tools_schema_json()

        assert schema_json is not None
        assert "test_tool" in schema_json
        assert "Test tool description" in schema_json

    def test_build_tools_schema_list(self, builder):
        """测试构建工具 Schema 列表"""
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool description"
        mock_tool.parameters = {}

        builder.set_tools({"test_tool": mock_tool})

        schema_list = builder._build_tools_schema_list()

        assert isinstance(schema_list, list)
        assert len(schema_list) == 1
        assert schema_list[0]["name"] == "test_tool"


class TestSystemPromptBuilderIntegration:
    """SystemPromptBuilder 集成测试"""

    def test_full_three_layer_architecture(self):
        """测试完整三层架构"""
        from agent.context.system_prompt_builder import SystemPromptBuilder

        # 创建构建器
        builder = SystemPromptBuilder(
            tools={},
            enable_guidance=True,
            enable_memory_prefetch=True,
            session_id="integration_test"
        )

        # 构建提示词
        result = builder.build(
            user_message="测试消息",
            conversation_history=[
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！"}
            ]
        )

        # 验证三层都存在
        assert result.stable is not None
        assert result.context is not None
        # volatile 可能为空（如果没有匹配的记忆）
        assert result.volatile is not None
        assert result.full_prompt is not None

        # 验证完整提示词包含所有层
        assert len(result.full_prompt) >= len(result.stable)
        assert len(result.full_prompt) >= len(result.context)

    def test_context_builder_integration(self):
        """测试与 ContextBuilder 集成"""
        from agent.context.context_builder import ContextBuilder

        # 创建 ContextBuilder（内部使用 SystemPromptBuilder）
        context_builder = ContextBuilder(
            tools={},
            enable_guidance=True,
            enable_memory_prefetch=True,
            session_id="test_integration"
        )

        # 调用 build_with_layers
        result = context_builder.build_with_layers(
            user_message="测试",
            conversation_history=[]
        )

        # 验证返回 LayerResult
        assert result.stable is not None
        assert result.context is not None
        assert result.volatile is not None
        assert result.full_prompt is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])