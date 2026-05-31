"""LLM Provider 测试"""
import pytest
from unittest.mock import patch, MagicMock
import sys


class TestLLMProviders:
    """LLM Provider 配置和功能测试"""
    
    def test_get_all_providers(self):
        """测试获取所有提供商"""
        from llm_integration import get_all_providers
        
        providers = get_all_providers()
        
        assert isinstance(providers, list)
        assert len(providers) > 0
        
        # 检查常见提供商
        provider_ids = [p['id'] for p in providers]
        assert 'openai' in provider_ids or 'custom' in provider_ids
    
    def test_provider_structure(self):
        """测试提供商结构"""
        from llm_integration import get_all_providers
        
        providers = get_all_providers()
        
        for provider in providers:
            assert 'id' in provider
            assert 'name' in provider
            assert 'description' in provider
            assert 'default_model' in provider
    
    def test_get_provider_models_openai(self):
        """测试获取 OpenAI 模型列表"""
        from llm_integration import get_provider_models
        
        models = get_provider_models('openai')
        
        # 应该返回模型列表
        assert isinstance(models, list)
        # OpenAI 应该有一些模型
        if len(models) > 0:
            assert 'id' in models[0]
            assert 'name' in models[0]
    
    def test_get_provider_models_custom(self):
        """测试获取自定义模型列表"""
        from llm_integration import get_provider_models
        
        models = get_provider_models('custom')
        
        # 自定义可能没有预定义模型
        assert isinstance(models, list)
    
    def test_provider_with_api_key_url(self):
        """测试带 API Key URL 的提供商"""
        from llm_integration import get_all_providers
        
        providers = get_all_providers()
        
        for provider in providers:
            if provider.get('api_key_url'):
                assert isinstance(provider['api_key_url'], str)
                assert len(provider['api_key_url']) > 0
    
    def test_provider_base_url(self):
        """测试提供商基础 URL"""
        from llm_integration import get_all_providers
        
        providers = get_all_providers()
        
        for provider in providers:
            if provider.get('base_url'):
                assert isinstance(provider['base_url'], str)
                assert 'http' in provider['base_url'] or 'localhost' in provider['base_url']


class TestLLMIntegration:
    """LLM 集成功能测试"""
    
    def test_import_llm_integration(self):
        """测试导入 LLM 集成模块"""
        from llm_integration import get_all_providers, get_provider_models
        from llm_integration import LLMProvider, LLMMessage, LLMResponse
        
        # 应该成功导入
        assert callable(get_all_providers)
        assert callable(get_provider_models)
    
    def test_llm_provider_class(self):
        """测试 LLM Provider 类"""
        from llm_integration import LLMProvider
        
        # 检查类是否存在
        assert LLMProvider is not None
    
    def test_llm_message_class(self):
        """测试 LLM Message 类"""
        from llm_integration import LLMMessage
        
        # 检查类是否存在
        assert LLMMessage is not None
    
    def test_llm_response_class(self):
        """测试 LLM Response 类"""
        from llm_integration import LLMResponse
        
        # 检查类是否存在
        assert LLMResponse is not None


class TestLLMConfiguration:
    """LLM 配置测试"""
    
    def test_default_provider_config(self):
        """测试默认提供商配置"""
        from shared.config import get_settings, get_llm_provider_config
        
        settings = get_settings()
        
        # 应该能获取设置
        assert settings is not None
    
    def test_provider_config_structure(self):
        """测试提供商配置结构"""
        from shared.config import LLMProviderConfig
        
        config = LLMProviderConfig(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4",
            enabled=True
        )
        
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.model == "gpt-4"
        assert config.enabled == True
    
    def test_get_llm_provider_config(self):
        """测试获取提供商配置"""
        from shared.config import get_llm_provider_config
        
        # 测试获取不存在的提供商
        config = get_llm_provider_config('nonexistent')
        
        assert config is not None
        assert config.api_key is None
        assert config.enabled == False
    
    def test_model_config_defaults(self):
        """测试模型配置默认值"""
        from shared.config import ModelConfig
        
        config = ModelConfig()
        
        assert config.default == "openai/gpt-4o-mini"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.context_window == 128000
    
    def test_model_config_custom(self):
        """测试自定义模型配置"""
        from shared.config import ModelConfig
        
        config = ModelConfig(
            default="anthropic/claude-3-opus",
            max_tokens=8192,
            temperature=0.9,
            context_window=200000
        )
        
        assert config.default == "anthropic/claude-3-opus"
        assert config.max_tokens == 8192
        assert config.temperature == 0.9
        assert config.context_window == 200000