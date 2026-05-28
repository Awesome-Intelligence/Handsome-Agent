"""测试内置记忆提供者"""
import pytest
import tempfile
import os
from core.builtin_memory import BuiltinMemoryProvider


class TestBuiltinMemoryProvider:
    """测试内置记忆提供者"""

    def test_initialize(self):
        """测试初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = BuiltinMemoryProvider()
            provider.initialize("test_session", hermes_home=tmpdir, platform="cli")
            
            assert provider.is_available() == True
            assert provider.name == "builtin"

    def test_save_and_retrieve_fact(self):
        """测试保存和检索事实"""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = BuiltinMemoryProvider()
            provider.initialize("test_session", hermes_home=tmpdir)
            
            # 保存事实
            result = provider.handle_tool_call("memory_save", {
                "key": "test_key",
                "value": "test_value",
                "category": "fact"
            })
            
            assert "success" in result
            
            # 检索事实
            result = provider.handle_tool_call("memory_retrieve", {"key": "test_key"})
            assert "test_value" in result

    def test_search_memory(self):
        """测试搜索记忆"""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = BuiltinMemoryProvider()
            provider.initialize("test_session", hermes_home=tmpdir)
            
            # 保存多个事实
            provider.handle_tool_call("memory_save", {
                "key": "favorite_color",
                "value": "blue",
                "category": "fact"
            })
            provider.handle_tool_call("memory_save", {
                "key": "favorite_food",
                "value": "pizza",
                "category": "fact"
            })
            
            # 搜索
            result = provider.handle_tool_call("memory_search", {"query": "favorite"})
            assert "blue" in result
            assert "pizza" in result

    def test_list_memory_keys(self):
        """测试列出记忆键"""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = BuiltinMemoryProvider()
            provider.initialize("test_session", hermes_home=tmpdir)
            
            result = provider.handle_tool_call("memory_list", {})
            assert "factual" in result
            assert "profile" in result

    def test_delete_memory(self):
        """测试删除记忆"""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = BuiltinMemoryProvider()
            provider.initialize("test_session", hermes_home=tmpdir)
            
            # 保存事实
            provider.handle_tool_call("memory_save", {
                "key": "to_delete",
                "value": "value",
                "category": "fact"
            })
            
            # 删除
            result = provider.handle_tool_call("memory_delete", {"key": "to_delete"})
            assert "success" in result
            
            # 验证已删除
            result = provider.handle_tool_call("memory_retrieve", {"key": "to_delete"})
            assert "Key not found" in result

    def test_prefetch(self):
        """测试预取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = BuiltinMemoryProvider()
            provider.initialize("test_session", hermes_home=tmpdir)
            
            provider.handle_tool_call("memory_save", {
                "key": "weather",
                "value": "sunny",
                "category": "fact"
            })
            
            result = provider.prefetch("weather")
            assert "sunny" in result

    def test_sync_turn(self):
        """测试同步回合"""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = BuiltinMemoryProvider()
            provider.initialize("test_session", hermes_home=tmpdir)
            
            provider.sync_turn("Hello", "Hi there!")
            
            # 检查会话记忆是否被更新
            assert len(provider._episodic_memory) == 1
            assert "Hello" in provider._episodic_memory[0]["user"]