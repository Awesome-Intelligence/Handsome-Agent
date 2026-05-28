"""测试记忆管理器"""
import pytest
from unittest.mock import Mock
from core.memory_manager import MemoryManager, build_memory_context_block, sanitize_context


class TestMemoryManager:
    """测试记忆管理器"""

    def test_add_provider(self):
        """测试添加提供者"""
        manager = MemoryManager()
        
        mock_provider = Mock()
        mock_provider.name = "builtin"
        mock_provider.is_available.return_value = True
        mock_provider.get_tool_schemas.return_value = []
        
        manager.add_provider(mock_provider)
        
        assert len(manager._providers) == 1
        assert manager.get_provider("builtin") == mock_provider

    def test_add_multiple_providers(self):
        """测试添加多个提供者"""
        manager = MemoryManager()
        
        mock_builtin = Mock()
        mock_builtin.name = "builtin"
        mock_builtin.is_available.return_value = True
        mock_builtin.get_tool_schemas.return_value = []
        
        mock_external = Mock()
        mock_external.name = "honcho"
        mock_external.is_available.return_value = True
        mock_external.get_tool_schemas.return_value = []
        
        manager.add_provider(mock_builtin)
        manager.add_provider(mock_external)
        
        assert len(manager._providers) == 2

    def test_prefetch_all(self):
        """测试预取所有提供者"""
        manager = MemoryManager()
        
        mock_provider = Mock()
        mock_provider.name = "builtin"
        mock_provider.is_available.return_value = True
        mock_provider.get_tool_schemas.return_value = []
        mock_provider.prefetch.return_value = "test context"
        
        manager.add_provider(mock_provider)
        
        result = manager.prefetch_all("query")
        assert "test context" in result

    def test_sync_all(self):
        """测试同步所有提供者"""
        manager = MemoryManager()
        
        mock_provider = Mock()
        mock_provider.name = "builtin"
        mock_provider.is_available.return_value = True
        mock_provider.get_tool_schemas.return_value = []
        
        manager.add_provider(mock_provider)
        manager.sync_all("user", "assistant")
        
        mock_provider.sync_turn.assert_called_once_with("user", "assistant", session_id="")


class TestMemoryContextHelpers:
    """测试上下文辅助函数"""

    def test_sanitize_context(self):
        """测试清理上下文"""
        raw = "<memory-context>content</memory-context>"
        result = sanitize_context(raw)
        assert result == ""

    def test_build_context_block(self):
        """测试构建上下文块"""
        result = build_memory_context_block("test content")
        assert "<memory-context>" in result
        assert "test content" in result

    def test_build_empty_context(self):
        """测试空上下文"""
        result = build_memory_context_block("")
        assert result == ""