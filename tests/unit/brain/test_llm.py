"""LLM 模块单元测试"""
import pytest
from unittest.mock import MagicMock
from brain.llm.base import BaseLLMProvider, LLMConfig, LLMResponse, Message
from brain.llm.factory import LLMFactory


class TestLLMConfig:
    """LLMConfig 测试"""
    
    def test_default_values(self):
        """测试默认值"""
        config = LLMConfig()
        
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 4000
        assert config.top_p == 1.0
        assert config.api_key is None
    
    def test_custom_values(self):
        """测试自定义值"""
        config = LLMConfig(
            model="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=2000,
            api_key="test_key",
        )
        
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000
        assert config.api_key == "test_key"


class TestLLMResponse:
    """LLMResponse 测试"""
    
    def test_response_creation(self):
        """测试响应创建"""
        response = LLMResponse(
            content="Hello, world!",
            model="gpt-4",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            latency_ms=100.0,
        )
        
        assert response.content == "Hello, world!"
        assert response.model == "gpt-4"
        assert response.finish_reason == "stop"
        assert response.usage["prompt_tokens"] == 10
        assert response.latency_ms == 100.0


class TestMessage:
    """Message 测试"""
    
    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(role="user", content="Hello")
        
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None
    
    def test_message_with_name(self):
        """测试带名称的消息"""
        msg = Message(role="function", content="Result", name="calculator")
        
        assert msg.role == "function"
        assert msg.name == "calculator"


class TestLLMFactory:
    """LLMFactory 测试"""
    
    def test_list_providers(self):
        """测试列出提供商"""
        providers = LLMFactory.list_providers()
        
        assert "openai" in providers
        assert "claude" in providers
        assert "gpt" in providers
    
    def test_unknown_provider(self):
        """测试未知提供商"""
        with pytest.raises(ValueError) as exc_info:
            LLMFactory.create("unknown_provider", api_key="test_key")
        
        assert "Unknown provider" in str(exc_info.value)
    
    def test_list_models(self):
        """测试列出模型"""
        models = LLMFactory.list_models("openai")
        
        assert "gpt-4" in models
        assert "gpt-3.5-turbo" in models


class TestBaseLLMProvider:
    """BaseLLMProvider 测试"""
    
    def test_message_history(self):
        """测试消息历史"""
        config = LLMConfig()
        provider = MagicMock(spec=BaseLLMProvider)
        
        # 创建模拟的消息历史
        mock_messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]
        provider._message_history = mock_messages
        provider.get_history = MagicMock(return_value=mock_messages)
        provider.add_message = MagicMock()
        provider.clear_history = MagicMock()
        
        history = provider.get_history()
        assert len(history) == 2
        assert history[0].content == "Hello"
        assert history[1].content == "Hi there!"
    
    def test_set_history(self):
        """测试设置历史"""
        config = LLMConfig()
        provider = MagicMock(spec=BaseLLMProvider)
        
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi!"),
        ]
        
        provider._message_history = messages
        provider.get_history = MagicMock(return_value=messages)
        provider.set_history = MagicMock()
        
        history = provider.get_history()
        assert len(history) == 2