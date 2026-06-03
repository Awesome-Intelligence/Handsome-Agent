"""
LLM Provider 单元测试
🧠 Decision - 🤖 LLM - Provider 测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent.llm import LLMFactory
from agent.llm.providers.base import BaseProvider, ProviderConfig, Message


class TestLLMFactory:
    """LLMFactory 测试"""

    def test_list_providers(self):
        """测试列出所有 Provider"""
        providers = LLMFactory.list_providers()
        assert "openai" in providers
        assert "claude" in providers
        assert "deepseek" in providers
        assert "gemini" in providers
        assert "kimi" in providers
        assert "azure" in providers

    def test_create_openai_provider(self):
        """测试创建 OpenAI Provider"""
        provider = LLMFactory.create("openai", api_key="test-key")
        assert provider.__class__.__name__ == "OpenAIProvider"
        assert provider.config.api_key == "test-key"
        assert provider.config.model == "gpt-4o-mini"

    def test_create_claude_provider(self):
        """测试创建 Claude Provider"""
        provider = LLMFactory.create("claude", api_key="test-key")
        assert provider.__class__.__name__ == "ClaudeProvider"
        assert provider.config.api_key == "test-key"
        assert provider.config.model == "claude-3-5-sonnet"

    def test_create_deepseek_provider(self):
        """测试创建 DeepSeek Provider"""
        provider = LLMFactory.create("deepseek", api_key="test-key")
        assert provider.__class__.__name__ == "DeepSeekProvider"
        assert provider.config.api_key == "test-key"
        assert provider.config.model == "deepseek-chat"

    def test_create_gemini_provider(self):
        """测试创建 Gemini Provider"""
        provider = LLMFactory.create("gemini", api_key="test-key", model="gemini-1.5-pro")
        assert provider.__class__.__name__ == "GeminiProvider"
        assert provider.config.api_key == "test-key"
        assert provider.config.model == "gemini-1.5-pro"

    def test_create_kimi_provider(self):
        """测试创建 Kimi Provider"""
        provider = LLMFactory.create("kimi", api_key="test-key")
        assert provider.__class__.__name__ == "KimiProvider"
        assert provider.config.api_key == "test-key"
        assert provider.config.model == "moonshot-v1-32k"

    def test_create_azure_provider(self):
        """测试创建 Azure Provider"""
        provider = LLMFactory.create(
            "azure",
            api_key="test-key",
            base_url="https://test.openai.azure.com/"
        )
        assert provider.__class__.__name__ == "AzureProvider"
        assert provider.config.api_key == "test-key"

    def test_create_with_alias(self):
        """测试使用别名创建 Provider"""
        provider = LLMFactory.create("gpt", api_key="test-key")
        assert provider.__class__.__name__ == "OpenAIProvider"

        provider = LLMFactory.create("anthropic", api_key="test-key")
        assert provider.__class__.__name__ == "ClaudeProvider"

    def test_create_with_custom_model(self):
        """测试创建时指定自定义模型"""
        provider = LLMFactory.create("openai", api_key="test-key", model="gpt-4")
        assert provider.config.model == "gpt-4"

    def test_create_unknown_provider_raises(self):
        """测试创建未知 Provider 抛出异常"""
        with pytest.raises(ValueError) as exc_info:
            LLMFactory.create("unknown", api_key="test-key")
        assert "Unknown provider" in str(exc_info.value)

    def test_get_provider_info(self):
        """测试获取 Provider 信息"""
        info = LLMFactory.get_provider_info("openai")
        assert info["name"] == "openai"
        assert info["display_name"] == "OpenAI"
        assert "gpt-4" in info["supported_models"]
        assert info["default_model"] == "gpt-4o-mini"

    def test_list_all_providers_info(self):
        """测试列出所有 Provider 信息"""
        all_info = LLMFactory.list_all_providers_info()
        assert len(all_info) >= 6  # 至少6个 Provider
        names = [p["name"] for p in all_info]
        assert "openai" in names
        assert "claude" in names
        assert "deepseek" in names


class TestProviderConfig:
    """ProviderConfig 测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = ProviderConfig(api_key="test")
        assert config.api_key == "test"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 4000

    def test_custom_config(self):
        """测试自定义配置"""
        config = ProviderConfig(
            api_key="test",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2000,
            base_url="https://custom.api.com"
        )
        assert config.model == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000
        assert config.base_url == "https://custom.api.com"


class TestMessage:
    """Message 测试"""

    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_message_with_name(self):
        """测试带名称的消息"""
        msg = Message(role="user", content="Hello", name="test_user")
        assert msg.name == "test_user"

    def test_message_model_dump(self):
        """测试消息序列化"""
        msg = Message(role="user", content="Hello")
        data = msg.model_dump()
        assert data["role"] == "user"
        assert data["content"] == "Hello"


class TestBaseProvider:
    """BaseProvider 测试"""

    def test_provider_metadata(self):
        """测试 Provider 元数据"""
        from agent.llm.providers.openai import OpenAIProvider
        from agent.llm.providers.claude import ClaudeProvider

        assert OpenAIProvider.provider_name == "openai"
        assert OpenAIProvider.provider_display_name == "OpenAI"
        assert "gpt-4" in OpenAIProvider.supported_models

        assert ClaudeProvider.provider_name == "claude"
        assert ClaudeProvider.provider_display_name == "Anthropic Claude"
        assert "claude-3-5-sonnet" in ClaudeProvider.supported_models

    def test_message_history(self):
        """测试消息历史管理"""
        from agent.llm.providers.openai import OpenAIProvider

        provider = OpenAIProvider(ProviderConfig(api_key="test"))

        # 添加消息
        provider.add_message("user", "Hello")
        provider.add_message("assistant", "Hi there")

        history = provider.get_history()
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"

        # 清空历史
        provider.clear_history()
        assert len(provider.get_history()) == 0

    def test_set_history(self):
        """测试设置历史"""
        from agent.llm.providers.openai import OpenAIProvider

        provider = OpenAIProvider(ProviderConfig(api_key="test"))
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi"),
        ]
        provider.set_history(messages)

        assert len(provider.get_history()) == 2

    def test_build_messages(self):
        """测试消息构建"""
        from agent.llm.providers.openai import OpenAIProvider

        provider = OpenAIProvider(ProviderConfig(api_key="test"))

        system, msg_list = provider._build_messages(
            prompt="Test prompt",
            messages=[Message(role="user", content="Previous")],
            system_prompt="You are helpful"
        )

        assert system == "You are helpful"
        assert len(msg_list) == 2
        assert msg_list[0]["role"] == "user"
        assert msg_list[0]["content"] == "Previous"
        assert msg_list[1]["role"] == "user"
        assert msg_list[1]["content"] == "Test prompt"

    def test_estimate_tokens(self):
        """测试 token 估算"""
        from agent.llm.providers.openai import OpenAIProvider

        provider = OpenAIProvider(ProviderConfig(api_key="test"))

        # 英文 token 估算
        english_tokens = provider._estimate_tokens("Hello world")
        assert english_tokens > 0

        # 中文 token 估算
        chinese_tokens = provider._estimate_tokens("你好世界")
        assert chinese_tokens > english_tokens  # 中文通常需要更多 tokens


class TestOpenAIProvider:
    """OpenAIProvider 详细测试"""

    @pytest.fixture
    def provider(self):
        from agent.llm.providers.openai import OpenAIProvider
        return OpenAIProvider(ProviderConfig(api_key="test-key", model="gpt-4"))

    def test_api_url_default(self, provider):
        """测试默认 API URL"""
        assert provider.base_url == "https://api.openai.com/v1"

    def test_api_url_custom(self):
        from agent.llm.providers.openai import OpenAIProvider
        provider = OpenAIProvider(ProviderConfig(
            api_key="test",
            base_url="https://custom.api.com/v1"
        ))
        assert provider.base_url == "https://custom.api.com/v1"

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """测试 generate 方法成功调用"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}],
            "model": "gpt-4",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }

        with patch.object(provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            response = await provider.generate("Hi")
            assert response.content == "Hello!"
            assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_generate_with_messages(self, provider):
        """测试带历史消息的 generate"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}, "finish_reason": "stop"}],
            "model": "gpt-4",
            "usage": {}
        }

        with patch.object(provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            messages = [Message(role="user", content="Previous message")]
            response = await provider.generate("New message", messages=messages)
            assert response.content == "Response"

            # 验证请求中包含历史消息
            call_args = mock_client.post.call_args
            request_body = call_args[1]["json"]
            # 2 messages: history + new prompt (没有 system_prompt)
            assert len(request_body["messages"]) == 2

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, provider):
        """测试带系统提示的 generate"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}, "finish_reason": "stop"}],
            "model": "gpt-4",
            "usage": {}
        }

        with patch.object(provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            response = await provider.generate("Hi", system_prompt="You are helpful")
            assert response.content == "Response"

            # 验证请求中包含系统消息
            call_args = mock_client.post.call_args
            request_body = call_args[1]["json"]
            assert request_body["messages"][0]["role"] == "system"
            assert request_body["messages"][0]["content"] == "You are helpful"

    @pytest.mark.asyncio
    async def test_generate_api_error(self, provider):
        """测试 API 返回错误的处理"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            with pytest.raises(Exception) as exc_info:
                await provider.generate("Hi")
            assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_stream_with_error_response(self, provider):
        """测试流式响应 API 错误处理"""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()

            # 创建异步上下文管理器
            async_ctx = AsyncMock()
            async_ctx.__aenter__.return_value = mock_response
            async_ctx.__aexit__.return_value = AsyncMock()
            mock_client.stream.return_value = async_ctx

            mock_get_client.return_value = mock_client

            chunks = []
            async for chunk in provider.generate_stream("Hi"):
                chunks.append(chunk)

            # 错误时应该返回包含错误的 chunk
            assert len(chunks) == 1
            assert "Error" in chunks[0].content

    @pytest.mark.asyncio
    async def test_close(self, provider):
        """测试客户端关闭"""
        mock_client = AsyncMock()
        provider._client = mock_client

        await provider.close()
        mock_client.aclose.assert_called_once()
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_close_when_client_none(self, provider):
        """测试客户端未初始化时的关闭"""
        provider._client = None
        await provider.close()  # 不应抛出异常


class TestClaudeProvider:
    """ClaudeProvider 详细测试"""

    @pytest.fixture
    def provider(self):
        from agent.llm.providers.claude import ClaudeProvider
        return ClaudeProvider(ProviderConfig(api_key="test-key", model="claude-3-5-sonnet"))

    def test_api_url(self, provider):
        """测试 API URL"""
        assert provider.API_URL == "https://api.anthropic.com/v1"

    def test_supported_models(self, provider):
        """测试支持的模型列表"""
        from agent.llm.providers.claude import ClaudeProvider
        assert "claude-3-5-sonnet" in ClaudeProvider.supported_models
        assert "claude-3-opus" in ClaudeProvider.supported_models

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """测试 generate 方法成功调用"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Claude response"}],
            "model": "claude-3-5-sonnet",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 8}
        }

        with patch.object(provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            response = await provider.generate("Hello")
            assert response.content == "Claude response"


class TestDeepSeekProvider:
    """DeepSeekProvider 详细测试"""

    @pytest.fixture
    def provider(self):
        from agent.llm.providers.deepseek import DeepSeekProvider
        return DeepSeekProvider(ProviderConfig(api_key="test-key", model="deepseek-chat"))

    def test_api_url(self, provider):
        """测试 API URL"""
        assert provider.API_URL == "https://api.deepseek.com/chat"

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """测试 generate 方法成功调用"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "DeepSeek response"}, "finish_reason": "stop"}],
            "model": "deepseek-chat",
            "usage": {"prompt_tokens": 10, "completion_tokens": 8}
        }

        with patch.object(provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            response = await provider.generate("Hello")
            assert response.content == "DeepSeek response"


class TestGeminiProvider:
    """GeminiProvider 详细测试"""

    @pytest.fixture
    def provider(self):
        from agent.llm.providers.gemini import GeminiProvider
        return GeminiProvider(ProviderConfig(api_key="test-key", model="gemini-1.5-flash"))

    def test_api_url(self, provider):
        """测试 API URL"""
        assert provider.API_URL == "https://generativelanguage.googleapis.com/v1beta/models"

    def test_supported_models(self, provider):
        """测试支持的模型列表"""
        from agent.llm.providers.gemini import GeminiProvider
        assert "gemini-1.5-flash" in GeminiProvider.supported_models
        assert "gemini-1.5-pro" in GeminiProvider.supported_models

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """测试 generate 方法成功调用"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {"parts": [{"text": "Gemini response"}]}
            }],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 5,
                "totalTokenCount": 15
            }
        }

        with patch.object(provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            response = await provider.generate("Hello")
            assert response.content == "Gemini response"
            assert response.usage["prompt_tokens"] == 10


class TestKimiProvider:
    """KimiProvider 详细测试"""

    @pytest.fixture
    def provider(self):
        from agent.llm.providers.kimi import KimiProvider
        return KimiProvider(ProviderConfig(api_key="test-key", model="moonshot-v1-32k"))

    def test_api_url(self, provider):
        """测试 API URL"""
        assert provider.API_URL == "https://api.moonshot.cn/v1"
        assert provider.CHAT_COMPLETIONS_URL == "https://api.moonshot.cn/v1/chat/completions"


class TestAzureProvider:
    """AzureProvider 详细测试"""

    @pytest.fixture
    def provider(self):
        from agent.llm.providers.azure import AzureProvider
        return AzureProvider(ProviderConfig(
            api_key="test-key",
            base_url="https://test.openai.azure.com/openai/deployments/gpt-4"
        ))

    def test_base_url_format(self, provider):
        """测试 Azure base_url 格式"""
        assert "openai.azure.com" in provider.base_url

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """测试 generate 方法成功调用"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Azure response"}, "finish_reason": "stop"}],
            "model": "gpt-4",
            "usage": {}
        }

        with patch.object(provider, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            response = await provider.generate("Hello")
            assert response.content == "Azure response"


class TestProviderResponse:
    """ProviderResponse 测试"""

    def test_response_creation(self):
        from agent.llm.providers.base import ProviderResponse
        response = ProviderResponse(
            content="Hello",
            model="gpt-4",
            finish_reason="stop",
            usage={"prompt_tokens": 10}
        )
        assert response.content == "Hello"
        assert response.model == "gpt-4"
        assert response.latency_ms == 0.0

    def test_response_with_latency(self):
        from agent.llm.providers.base import ProviderResponse
        response = ProviderResponse(
            content="Hello",
            model="gpt-4",
            latency_ms=123.45
        )
        assert response.latency_ms == 123.45


class TestStreamChunk:
    """StreamChunk 测试"""

    def test_chunk_creation(self):
        from agent.llm.providers.base import StreamChunk
        chunk = StreamChunk(content="Hello", delta="He", finish=False)
        assert chunk.content == "Hello"
        assert chunk.delta == "He"
        assert chunk.finish is False

    def test_chunk_finish(self):
        from agent.llm.providers.base import StreamChunk
        chunk = StreamChunk(finish=True)
        assert chunk.finish is True
        assert chunk.content == ""
