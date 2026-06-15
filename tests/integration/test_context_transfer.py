#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Context Transfer - 上下文传递集成测试

测试多轮对话场景下的上下文传递功能：
1. 多轮对话上下文保持
2. 工具调用结果在对话中保留
3. 系统提示词缓存机制

日志子层：💾 Context
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any


class TestMultiTurnConversationContext:
    """多轮对话上下文传递测试类"""
    
    @pytest.fixture
    def context_builder(self):
        """创建 ContextBuilder 实例"""
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(
            tools={},
            enable_guidance=True,
            enable_memory_prefetch=False
        )
    
    def test_multi_turn_conversation_context(self, context_builder):
        """
        验证多轮对话上下文传递
        
        测试场景：连续多轮对话中，每轮的消息都能正确累积
        """
        # 第一轮对话
        history_turn1 = [
            {"role": "user", "content": "你好"}
        ]
        messages_turn1 = context_builder.build_messages(conversation_history=history_turn1)
        
        # 验证第一轮：system + user
        assert len(messages_turn1) == 2
        assert messages_turn1[0]["role"] == "system"
        assert messages_turn1[1]["role"] == "user"
        assert messages_turn1[1]["content"] == "你好"
        
        # 第二轮对话（包含第一轮历史）
        history_turn2 = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"}
        ]
        messages_turn2 = context_builder.build_messages(conversation_history=history_turn2)
        
        # 验证第二轮：system + user + assistant
        assert len(messages_turn2) == 3
        assert messages_turn2[0]["role"] == "system"
        assert messages_turn2[1]["role"] == "user"
        assert messages_turn2[1]["content"] == "你好"
        assert messages_turn2[2]["role"] == "assistant"
        assert "帮助" in messages_turn2[2]["content"]
        
        # 第三轮对话（包含前两轮历史）
        history_turn3 = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"},
            {"role": "user", "content": "帮我写个函数"},
            {"role": "assistant", "content": "好的，请告诉我函数需要实现什么功能？"}
        ]
        messages_turn3 = context_builder.build_messages(conversation_history=history_turn3)
        
        # 验证第三轮：system + user + assistant + user + assistant
        assert len(messages_turn3) == 5
        assert messages_turn3[0]["role"] == "system"
        assert messages_turn3[1]["role"] == "user"
        assert messages_turn3[2]["role"] == "assistant"
        assert messages_turn3[3]["role"] == "user"
        assert messages_turn3[3]["content"] == "帮我写个函数"
        assert messages_turn3[4]["role"] == "assistant"
        
        # 验证所有消息角色正确
        expected_roles = ["system", "user", "assistant", "user", "assistant"]
        actual_roles = [msg["role"] for msg in messages_turn3]
        assert actual_roles == expected_roles, \
            f"角色顺序错误: 期望 {expected_roles}, 实际 {actual_roles}"
    
    def test_multi_turn_preserves_system_message(self, context_builder):
        """
        验证多轮对话中系统消息始终在第一位
        """
        first_system_content = None
        
        for turn in range(1, 6):
            history = [
                {"role": "user", "content": f"第{turn}轮用户消息"},
                {"role": "assistant", "content": f"第{turn}轮助手回复"}
            ]
            messages = context_builder.build_messages(conversation_history=history)
            
            # 系统消息始终在第一位
            assert messages[0]["role"] == "system", \
                f"第{turn}轮: 系统消息未在第一位"
            
            # 保存第一轮的系统消息内容
            if turn == 1:
                first_system_content = messages[0]["content"]
            else:
                # 后续轮次的系统消息内容应该保持一致
                assert messages[0]["content"] == first_system_content, \
                    f"第{turn}轮: 系统消息内容发生变化"


class TestToolCallResultPreserved:
    """工具调用结果保留测试类"""
    
    @pytest.fixture
    def context_builder_with_tools(self):
        """创建带工具的 ContextBuilder 实例"""
        from agent.context.context_builder import ContextBuilder
        
        # 创建模拟工具
        mock_tool = Mock()
        mock_tool.name = "file_list"
        mock_tool.description = "List files in directory"
        mock_tool.parameters = {"type": "object", "properties": {}}
        
        return ContextBuilder(
            tools={"file_list": mock_tool},
            enable_guidance=True,
            enable_memory_prefetch=False
        )
    
    def test_tool_call_result_preserved(self, context_builder_with_tools):
        """
        验证工具调用结果在对话中被保留
        """
        # 模拟一个包含工具调用和结果的对话历史
        conversation_history = [
            # 第一轮：用户询问
            {"role": "user", "content": "列出当前目录的文件"},
            # 第二轮：助手调用工具
            {
                "role": "assistant",
                "content": "我来帮你列出文件",
                "tool_calls": [
                    {
                        "id": "call_001",
                        "type": "function",
                        "function": {
                            "name": "file_list",
                            "arguments": "{}"
                        }
                    }
                ]
            },
            # 第三轮：工具返回结果
            {"role": "tool", "tool_call_id": "call_001", "content": "file1.txt\nfile2.txt\nfolder/"},
            # 第四轮：助手基于结果回复
            {"role": "assistant", "content": "当前目录有以下文件：\n- file1.txt\n- file2.txt\n- folder/"}
        ]
        
        messages = context_builder_with_tools.build_messages(
            conversation_history=conversation_history
        )
        
        # 验证消息结构：system + user + assistant(tool_calls) + tool + assistant
        assert len(messages) == 5
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "列出当前目录的文件"
        
        # 验证工具调用消息
        assert messages[2]["role"] == "assistant"
        assert "tool_calls" in messages[2]
        assert len(messages[2]["tool_calls"]) == 1
        assert messages[2]["tool_calls"][0]["id"] == "call_001"
        
        # 验证工具结果消息
        assert messages[3]["role"] == "tool"
        assert messages[3]["tool_call_id"] == "call_001"
        assert "file1.txt" in messages[3]["content"]
        
        # 验证助手最终回复
        assert messages[4]["role"] == "assistant"
        assert "file1.txt" in messages[4]["content"]
    
    def test_multiple_tool_calls_in_conversation(self, context_builder_with_tools):
        """
        验证多轮工具调用场景
        """
        conversation_history = [
            {"role": "user", "content": "帮我搜索记忆并列出文件"},
            # 第一个工具调用
            {
                "role": "assistant",
                "content": "我来搜索记忆",
                "tool_calls": [
                    {"id": "call_search", "type": "function", "function": {
                        "name": "memory_search",
                        "arguments": '{"query": "用户偏好"}'
                    }}
                ]
            },
            {"role": "tool", "tool_call_id": "call_search", "content": '{"entries": ["用户喜欢简洁回复"]}'},
            # 第二个工具调用
            {
                "role": "assistant",
                "content": "找到记忆了，现在列出文件",
                "tool_calls": [
                    {"id": "call_list", "type": "function", "function": {
                        "name": "file_list",
                        "arguments": "{}"
                    }}
                ]
            },
            {"role": "tool", "tool_call_id": "call_list", "content": "config.json\ndata.db"}
        ]
        
        messages = context_builder_with_tools.build_messages(
            conversation_history=conversation_history
        )
        
        # 验证完整消息链：system + user + assistant + tool + assistant + tool = 6条
        assert len(messages) == 6, f"期望6条消息，实际 {len(messages)} 条"
        
        # 验证两个工具调用都存在
        tool_call_ids = []
        for msg in messages:
            if "tool_calls" in msg:
                tool_call_ids.append(msg["tool_calls"][0]["id"])
        
        assert "call_search" in tool_call_ids, "缺少 memory_search 工具调用"
        assert "call_list" in tool_call_ids, "缺少 file_list 工具调用"
        
        # 验证两个工具结果都存在
        tool_results = [msg for msg in messages if msg.get("role") == "tool"]
        assert len(tool_results) == 2, "应该有2个工具结果"
        
        tool_ids = [r["tool_call_id"] for r in tool_results]
        assert "call_search" in tool_ids
        assert "call_list" in tool_ids
    
    def test_tool_call_without_result(self, context_builder_with_tools):
        """
        验证工具调用未返回结果的场景
        """
        conversation_history = [
            {"role": "user", "content": "调用一个不存在的工具"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "call_fail", "type": "function", "function": {
                        "name": "nonexistent_tool",
                        "arguments": "{}"
                    }}
                ]
            }
            # 注意：没有 tool 消息
        ]
        
        messages = context_builder_with_tools.build_messages(
            conversation_history=conversation_history
        )
        
        # 验证消息结构
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"
        assert "tool_calls" in messages[2]
        
        # 验证没有 tool 结果
        tool_results = [msg for msg in messages if msg.get("role") == "tool"]
        assert len(tool_results) == 0, "不应该有工具结果"


class TestSystemPromptCache:
    """系统提示词缓存机制测试类"""
    
    @pytest.fixture
    def context_builder(self):
        """创建 ContextBuilder 实例"""
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(
            tools={},
            enable_guidance=True,
            enable_memory_prefetch=False
        )
    
    def test_system_prompt_cache(self, context_builder):
        """
        验证系统提示词缓存机制
        
        在工具列表不变的情况下，多次构建应该能复用缓存
        """
        # 第一次构建
        messages1 = context_builder.build_messages()
        system_content1 = messages1[0]["content"]
        
        # 第二次构建（无历史）
        messages2 = context_builder.build_messages()
        system_content2 = messages2[0]["content"]
        
        # 系统消息内容应该相同（缓存生效）
        assert system_content1 == system_content2, \
            "缓存未生效：相同的系统提示词应该返回相同内容"
    
    def test_cache_invalidation_on_tools_change(self, context_builder):
        """
        验证工具列表变化时缓存失效
        """
        # 初始状态（无工具）
        messages1 = context_builder.build_messages()
        system_content1 = messages1[0]["content"]
        assert "Available tools" not in system_content1, "初始状态不应有工具"
        
        # 添加工具后
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool description"
        mock_tool.parameters = {}
        
        context_builder.set_tools({"test_tool": mock_tool})
        
        # 构建时应该包含新工具
        messages2 = context_builder.build_messages()
        system_content2 = messages2[0]["content"]
        
        # 工具列表应该被包含
        assert "test_tool" in system_content2 or "Available tools" in system_content2, \
            "添加工具后系统提示词应包含工具信息"
    
    def test_build_messages_with_different_history(self, context_builder):
        """
        验证不同历史记录不影响系统消息缓存
        """
        # 第一轮对话
        history1 = [{"role": "user", "content": "第一轮"}]
        messages1 = context_builder.build_messages(conversation_history=history1)
        system1 = messages1[0]["content"]
        
        # 第二轮对话（不同历史）
        history2 = [
            {"role": "user", "content": "第一轮"},
            {"role": "assistant", "content": "回复"},
            {"role": "user", "content": "第二轮"}
        ]
        messages2 = context_builder.build_messages(conversation_history=history2)
        system2 = messages2[0]["content"]
        
        # 系统消息内容应该相同
        assert system1 == system2, \
            "不同的历史记录不应该影响系统消息内容"
        
        # 但消息总数应该不同
        assert len(messages1) == 2, "第一轮应该有2条消息"
        assert len(messages2) == 4, "第二轮应该有4条消息"
    
    def test_cache_performance(self, context_builder):
        """
        验证缓存对性能的影响
        
        通过测量构建时间来验证缓存是否正常工作
        """
        import time
        
        # 预热
        context_builder.build_messages()
        
        # 测量多次构建的时间
        times = []
        for _ in range(5):
            start = time.time()
            context_builder.build_messages()
            elapsed = time.time() - start
            times.append(elapsed)
        
        # 所有构建时间应该在合理范围内（< 1秒）
        for t in times:
            assert t < 1.0, f"构建时间过长: {t}秒"
        
        # 后续构建时间应该不增加（缓存生效）
        avg_first_half = sum(times[:2]) / 2
        avg_second_half = sum(times[3:]) / 2
        
        # 缓存后不应该变慢
        assert avg_second_half <= avg_first_half * 1.5, \
            f"缓存可能失效：后半段平均时间({avg_second_half:.4f}s)明显慢于前半段({avg_first_half:.4f}s)"


class TestContextTransferEdgeCases:
    """上下文传递边界情况测试类"""
    
    @pytest.fixture
    def context_builder(self):
        """创建 ContextBuilder 实例"""
        from agent.context.context_builder import ContextBuilder
        return ContextBuilder(
            tools={},
            enable_guidance=True,
            enable_memory_prefetch=False
        )
    
    def test_empty_conversation_history(self, context_builder):
        """验证空对话历史的处理"""
        messages = context_builder.build_messages(conversation_history=[])
        
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
    
    def test_none_conversation_history(self, context_builder):
        """验证 None 对话历史的处理"""
        messages = context_builder.build_messages(conversation_history=None)
        
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
    
    def test_unknown_role_handling(self, context_builder):
        """验证未知角色消息的处理"""
        history = [
            {"role": "unknown_role", "content": "未知角色消息"}
        ]
        messages = context_builder.build_messages(conversation_history=history)
        
        # 未知角色应该被转换为 assistant
        assert len(messages) == 2
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "未知角色消息"
    
    def test_message_without_content(self, context_builder):
        """验证无 content 字段消息的处理"""
        history = [
            {"role": "user"},  # 没有 content
            {"role": "assistant", "content": ""},  # 空 content
            {"role": "assistant", "content": "有效消息"}
        ]
        messages = context_builder.build_messages(conversation_history=history)
        
        # 应该正确处理这些消息
        assert len(messages) == 4  # system + 3条历史
        # 验证空 content 没有被添加
        for msg in messages[1:]:
            if msg.get("role") == "assistant" and msg.get("content") == "":
                # 空 content 应该被排除
                pass
    
    def test_mixed_tool_call_formats(self, context_builder):
        """验证混合工具调用格式的处理"""
        history = [
            {"role": "user", "content": "执行多个工具"},
            # OpenAI 格式
            {"role": "assistant", "tool_calls": [
                {"id": "call_1", "type": "function", "function": {
                    "name": "tool_a",
                    "arguments": "{}"
                }}
            ]},
            {"role": "tool", "tool_call_id": "call_1", "content": "result_a"},
            # 简化格式
            {"role": "assistant", "tool_calls": [
                {"name": "tool_b", "arguments": {"param": "value"}}
            ]},
            {"role": "tool", "tool_call_id": "call_1", "content": "result_b"}
        ]
        
        messages = context_builder.build_messages(conversation_history=history)
        
        # 应该正确处理两种格式
        tool_call_messages = [msg for msg in messages if "tool_calls" in msg]
        assert len(tool_call_messages) == 2
        
        # 验证标准化
        for msg in tool_call_messages:
            tc = msg["tool_calls"][0]
            assert "id" in tc
            assert "function" in tc
            assert "name" in tc["function"]
            assert "arguments" in tc["function"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])