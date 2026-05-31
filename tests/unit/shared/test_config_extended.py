"""Config 管理测试"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from shared.config import (
    Settings,
    LLMProviderConfig,
    ModelConfig,
    TerminalConfig,
    BrowserConfig,
    SessionResetPolicy,
    PlatformConfig,
    STTConfig,
    TTSConfig,
    MemoryConfig,
    CompressionConfig,
    DebugConfig,
    get_settings,
    get_llm_provider_config,
    get_terminal_config,
    get_browser_config,
    get_session_reset_policy,
    get_platform_config,
    get_stt_config,
    get_tts_config,
    get_memory_config,
    get_compression_config,
    get_debug_config,
    get_model_config,
    get_sessions_dir,
    get_memories_dir,
    get_logs_dir,
    get_config_dir,
    get_skills_dir,
    ensure_workspace_dirs,
    HANDSOME_HOME
)


class TestConfigClasses:
    """配置类测试"""
    
    def test_llm_provider_config_defaults(self):
        """测试 LLM Provider 配置默认值"""
        config = LLMProviderConfig()
        
        assert config.api_key is None
        assert config.base_url is None
        assert config.model is None
        assert config.enabled == False
    
    def test_llm_provider_config_custom(self):
        """测试 LLM Provider 自定义配置"""
        config = LLMProviderConfig(
            api_key="sk-test",
            base_url="https://api.test.com",
            model="test-model",
            enabled=True
        )
        
        assert config.api_key == "sk-test"
        assert config.base_url == "https://api.test.com"
        assert config.model == "test-model"
        assert config.enabled == True
    
    def test_model_config_defaults(self):
        """测试模型配置默认值"""
        config = ModelConfig()
        
        assert config.default == "openai/gpt-4o-mini"
        assert config.fallback is None
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.context_window == 128000
    
    def test_model_config_custom(self):
        """测试模型自定义配置"""
        config = ModelConfig(
            default="claude-3-opus",
            fallback="claude-3-sonnet",
            max_tokens=8192,
            temperature=0.5,
            context_window=200000
        )
        
        assert config.default == "claude-3-opus"
        assert config.fallback == "claude-3-sonnet"
        assert config.max_tokens == 8192
        assert config.temperature == 0.5
        assert config.context_window == 200000
    
    def test_terminal_config_defaults(self):
        """测试 Terminal 配置默认值"""
        config = TerminalConfig()
        
        assert config.backend == "local"
        assert config.timeout == 60
        assert config.cwd is None
        assert config.lifetime_seconds == 300
        assert config.docker_image is None
    
    def test_terminal_config_docker(self):
        """测试 Docker Terminal 配置"""
        config = TerminalConfig(
            backend="docker",
            timeout=120,
            cwd="/app",
            lifetime_seconds=600,
            docker_image="python:3.11"
        )
        
        assert config.backend == "docker"
        assert config.timeout == 120
        assert config.cwd == "/app"
        assert config.lifetime_seconds == 600
        assert config.docker_image == "python:3.11"
    
    def test_terminal_config_ssh(self):
        """测试 SSH Terminal 配置"""
        config = TerminalConfig(
            backend="ssh",
            ssh_host="192.168.1.100",
            ssh_user="admin",
            ssh_port=22,
            ssh_key="~/.ssh/id_rsa"
        )
        
        assert config.backend == "ssh"
        assert config.ssh_host == "192.168.1.100"
        assert config.ssh_user == "admin"
        assert config.ssh_port == 22
        assert config.ssh_key == "~/.ssh/id_rsa"
    
    def test_browser_config_defaults(self):
        """测试 Browser 配置默认值"""
        config = BrowserConfig()
        
        assert config.enabled == False
        assert config.provider == "browserbase"
        assert config.api_key is None
        assert config.project_id is None
        assert config.proxies == True
        assert config.advanced_stealth == False
    
    def test_browser_config_custom(self):
        """测试 Browser 自定义配置"""
        config = BrowserConfig(
            enabled=True,
            provider="browserbase",
            api_key="bb-test",
            project_id="proj-123",
            proxies=False,
            advanced_stealth=True,
            session_timeout=600,
            inactivity_timeout=300
        )
        
        assert config.enabled == True
        assert config.provider == "browserbase"
        assert config.api_key == "bb-test"
        assert config.project_id == "proj-123"
        assert config.proxies == False
        assert config.advanced_stealth == True
        assert config.session_timeout == 600
        assert config.inactivity_timeout == 300
    
    def test_session_reset_policy_defaults(self):
        """测试 Session 重置策略默认值"""
        config = SessionResetPolicy()
        
        assert config.mode == "both"
        assert config.at_hour == 4
        assert config.idle_minutes == 1440
        assert config.notify == True
    
    def test_session_reset_policy_daily(self):
        """测试每日重置策略"""
        config = SessionResetPolicy(
            mode="daily",
            at_hour=6,
            idle_minutes=60,
            notify=False
        )
        
        assert config.mode == "daily"
        assert config.at_hour == 6
        assert config.idle_minutes == 60
        assert config.notify == False
    
    def test_session_reset_policy_idle(self):
        """测试空闲重置策略"""
        config = SessionResetPolicy(
            mode="idle",
            at_hour=0,
            idle_minutes=30,
            notify=True
        )
        
        assert config.mode == "idle"
        assert config.idle_minutes == 30
    
    def test_session_reset_policy_none(self):
        """测试不自动重置策略"""
        config = SessionResetPolicy(
            mode="none",
            at_hour=0,
            idle_minutes=0,
            notify=False
        )
        
        assert config.mode == "none"
    
    def test_platform_config_defaults(self):
        """测试 Platform 配置默认值"""
        config = PlatformConfig()
        
        assert config.enabled == False
        assert config.token is None
        assert config.api_key is None
        assert config.home_channel is None
        assert config.allowed_users is None
        assert config.require_mention == False
    
    def test_platform_config_telegram(self):
        """测试 Telegram Platform 配置"""
        config = PlatformConfig(
            enabled=True,
            token="123456:ABCDEF",
            allowed_users=["user1", "user2"],
            require_mention=True
        )
        
        assert config.enabled == True
        assert config.token == "123456:ABCDEF"
        assert config.allowed_users == ["user1", "user2"]
        assert config.require_mention == True
    
    def test_stt_config_defaults(self):
        """测试 STT 配置默认值"""
        config = STTConfig()
        
        assert config.enabled == False
        assert config.provider == "local"
        assert config.model == "base"
    
    def test_stt_config_custom(self):
        """测试 STT 自定义配置"""
        config = STTConfig(
            enabled=True,
            provider="groq",
            model="large-v3"
        )
        
        assert config.enabled == True
        assert config.provider == "groq"
        assert config.model == "large-v3"
    
    def test_tts_config_defaults(self):
        """测试 TTS 配置默认值"""
        config = TTSConfig()
        
        assert config.enabled == False
        assert config.provider == "openai"
        assert config.model == "tts-1"
        assert config.voice == "alloy"
    
    def test_tts_config_custom(self):
        """测试 TTS 自定义配置"""
        config = TTSConfig(
            enabled=True,
            provider="elevenlabs",
            model="tts-1-hd",
            voice="onxy"
        )
        
        assert config.enabled == True
        assert config.provider == "elevenlabs"
        assert config.model == "tts-1-hd"
        assert config.voice == "onxy"
    
    def test_memory_config_defaults(self):
        """测试 Memory 配置默认值"""
        config = MemoryConfig()
        
        assert config.enabled == True
        assert config.vector_store == "sqlite"
        assert config.embedding_model == "text-embedding-3-small"
        assert config.max_entries == 1000
        assert config.summary_threshold == 10
    
    def test_memory_config_custom(self):
        """测试 Memory 自定义配置"""
        config = MemoryConfig(
            enabled=True,
            vector_store="chroma",
            embedding_model="text-embedding-3-large",
            max_entries=5000,
            summary_threshold=20
        )
        
        assert config.enabled == True
        assert config.vector_store == "chroma"
        assert config.embedding_model == "text-embedding-3-large"
        assert config.max_entries == 5000
        assert config.summary_threshold == 20
    
    def test_compression_config_defaults(self):
        """测试 Compression 配置默认值"""
        config = CompressionConfig()
        
        assert config.enabled == True
        assert config.threshold == 0.85
        assert config.summary_model == "openai/gpt-4o-mini"
    
    def test_compression_config_custom(self):
        """测试 Compression 自定义配置"""
        config = CompressionConfig(
            enabled=True,
            threshold=0.9,
            summary_model="claude-3-opus"
        )
        
        assert config.enabled == True
        assert config.threshold == 0.9
        assert config.summary_model == "claude-3-opus"
    
    def test_debug_config_defaults(self):
        """测试 Debug 配置默认值"""
        config = DebugConfig()
        
        assert config.web_tools == False
        assert config.vision_tools == False
        assert config.moa_tools == False
        assert config.image_tools == False
    
    def test_debug_config_custom(self):
        """测试 Debug 自定义配置"""
        config = DebugConfig(
            web_tools=True,
            vision_tools=True,
            moa_tools=False,
            image_tools=False
        )
        
        assert config.web_tools == True
        assert config.vision_tools == True
        assert config.moa_tools == False
        assert config.image_tools == False


class TestConfigHelperFunctions:
    """配置辅助函数测试"""
    
    def test_get_settings(self):
        """测试获取设置单例"""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2  # 应该是同一个实例
    
    def test_get_llm_provider_config_defaults(self):
        """测试获取默认 LLM Provider 配置"""
        config = get_llm_provider_config('test')
        
        assert isinstance(config, LLMProviderConfig)
        assert config.enabled == False
    
    def test_get_terminal_config(self):
        """测试获取 Terminal 配置"""
        config = get_terminal_config()
        
        assert isinstance(config, TerminalConfig)
        assert config.backend == "local"
    
    def test_get_browser_config(self):
        """测试获取 Browser 配置"""
        config = get_browser_config()
        
        assert isinstance(config, BrowserConfig)
        assert config.enabled == False
    
    def test_get_session_reset_policy(self):
        """测试获取 Session 重置策略"""
        policy = get_session_reset_policy()
        
        assert isinstance(policy, SessionResetPolicy)
        assert policy.mode == "both"
    
    def test_get_platform_config(self):
        """测试获取 Platform 配置"""
        config = get_platform_config('telegram')
        
        assert isinstance(config, PlatformConfig)
        assert config.enabled == False
    
    def test_get_stt_config(self):
        """测试获取 STT 配置"""
        config = get_stt_config()
        
        assert isinstance(config, STTConfig)
        assert config.enabled == False
    
    def test_get_tts_config(self):
        """测试获取 TTS 配置"""
        config = get_tts_config()
        
        assert isinstance(config, TTSConfig)
        assert config.enabled == False
    
    def test_get_memory_config(self):
        """测试获取 Memory 配置"""
        config = get_memory_config()
        
        assert isinstance(config, MemoryConfig)
        assert config.enabled == True
    
    def test_get_compression_config(self):
        """测试获取 Compression 配置"""
        config = get_compression_config()
        
        assert isinstance(config, CompressionConfig)
        assert config.enabled == True
    
    def test_get_debug_config(self):
        """测试获取 Debug 配置"""
        config = get_debug_config()
        
        assert isinstance(config, DebugConfig)
        assert config.web_tools == False
    
    def test_get_model_config(self):
        """测试获取 Model 配置"""
        config = get_model_config()
        
        assert isinstance(config, ModelConfig)
        assert config.default == "openai/gpt-4o-mini"


class TestDirectoryFunctions:
    """目录函数测试"""
    
    def test_get_sessions_dir(self, tmp_path, monkeypatch):
        """测试获取会话目录"""
        monkeypatch.setenv('HANDSOME_HOME', str(tmp_path / '.handsome_agent'))
        
        sessions_dir = get_sessions_dir()
        
        assert isinstance(sessions_dir, Path)
        assert 'sessions' in str(sessions_dir)
    
    def test_get_memories_dir(self, tmp_path, monkeypatch):
        """测试获取记忆目录"""
        monkeypatch.setenv('HANDSOME_HOME', str(tmp_path / '.handsome_agent'))
        
        memories_dir = get_memories_dir()
        
        assert isinstance(memories_dir, Path)
        assert 'memories' in str(memories_dir)
    
    def test_get_logs_dir(self, tmp_path, monkeypatch):
        """测试获取日志目录"""
        monkeypatch.setenv('HANDSOME_HOME', str(tmp_path / '.handsome_agent'))
        
        logs_dir = get_logs_dir()
        
        assert isinstance(logs_dir, Path)
        assert 'logs' in str(logs_dir)
    
    def test_get_config_dir(self, tmp_path, monkeypatch):
        """测试获取配置目录"""
        monkeypatch.setenv('HANDSOME_HOME', str(tmp_path / '.handsome_agent'))
        
        config_dir = get_config_dir()
        
        assert isinstance(config_dir, Path)
        assert 'config' in str(config_dir)
    
    def test_get_skills_dir(self, tmp_path, monkeypatch):
        """测试获取技能目录"""
        monkeypatch.setenv('HANDSOME_HOME', str(tmp_path / '.handsome_agent'))
        
        skills_dir = get_skills_dir()
        
        assert isinstance(skills_dir, Path)
        assert 'skills' in str(skills_dir)
    
    def test_ensure_workspace_dirs(self, tmp_path, monkeypatch):
        """测试确保工作区目录存在"""
        monkeypatch.setenv('HANDSOME_HOME', str(tmp_path / '.handsome_agent'))
        
        ensure_workspace_dirs()
        
        assert (tmp_path / '.handsome_agent').exists()
        assert (tmp_path / '.handsome_agent' / 'sessions').exists()
        assert (tmp_path / '.handsome_agent' / 'memories').exists()
        assert (tmp_path / '.handsome_agent' / 'logs').exists()
        assert (tmp_path / '.handsome_agent' / 'config').exists()
        assert (tmp_path / '.handsome_agent' / 'skills').exists()


class TestSettingsClass:
    """Settings 类测试"""
    
    def test_settings_defaults(self):
        """测试 Settings 默认值"""
        settings = Settings()
        
        assert settings.app_name == "HandsomeAgent"
        assert settings.app_version == "1.0.0"
        assert settings.debug == False
        assert settings.max_iterations == 10
        assert settings.timeout_seconds == 60.0
    
    def test_settings_llm_providers(self):
        """测试 Settings LLM Providers"""
        settings = Settings()
        
        assert isinstance(settings.llm_providers, dict)
    
    def test_settings_allowed_commands(self):
        """测试 Settings 允许的命令"""
        settings = Settings()
        
        assert isinstance(settings.allowed_commands, list)
        assert 'git' in settings.allowed_commands
        assert 'npm' in settings.allowed_commands
    
    def test_settings_blocked_patterns(self):
        """测试 Settings 阻止的模式"""
        settings = Settings()
        
        assert isinstance(settings.blocked_patterns, list)
        assert len(settings.blocked_patterns) > 0
    
    def test_settings_model_config(self):
        """测试 Settings 模型配置"""
        settings = Settings()
        
        assert isinstance(settings.model, dict)
        assert 'default' in settings.model
        assert 'max_tokens' in settings.model
    
    def test_settings_terminal_config(self):
        """测试 Settings Terminal 配置"""
        settings = Settings()
        
        assert isinstance(settings.terminal, dict)
        assert 'backend' in settings.terminal
        assert 'timeout' in settings.terminal
    
    def test_settings_memory_config(self):
        """测试 Settings Memory 配置"""
        settings = Settings()
        
        assert isinstance(settings.memory, dict)
        assert 'enabled' in settings.memory
        assert 'vector_store' in settings.memory
    
    def test_settings_compression_config(self):
        """测试 Settings Compression 配置"""
        settings = Settings()
        
        assert isinstance(settings.compression, dict)
        assert 'enabled' in settings.compression
        assert 'threshold' in settings.compression