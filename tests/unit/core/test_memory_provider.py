"""测试记忆提供者基类"""
import pytest
from core.memory_provider import MemoryProvider


class TestMemoryProvider:
    """测试记忆提供者抽象基类"""

    def test_is_available_raises(self):
        """测试 is_available 方法必须被实现"""
        class MockProvider(MemoryProvider):
            @property
            def name(self):
                return "mock"
            def is_available(self):
                return True
            def initialize(self, session_id, **kwargs):
                pass
            def get_tool_schemas(self):
                return []
        
        provider = MockProvider()
        assert provider.is_available() == True

    def test_name_property(self):
        """测试 name 属性"""
        class MockProvider(MemoryProvider):
            @property
            def name(self):
                return "test_provider"
            def is_available(self):
                return False
            def initialize(self, session_id, **kwargs):
                pass
            def get_tool_schemas(self):
                return []
        
        provider = MockProvider()
        assert provider.name == "test_provider"

    def test_default_methods(self):
        """测试默认方法返回空值"""
        class MockProvider(MemoryProvider):
            @property
            def name(self):
                return "mock"
            def is_available(self):
                return True
            def initialize(self, session_id, **kwargs):
                pass
            def get_tool_schemas(self):
                return []
        
        provider = MockProvider()
        
        assert provider.system_prompt_block() == ""
        assert provider.prefetch("query") == ""
        assert provider.on_pre_compress([]) == ""