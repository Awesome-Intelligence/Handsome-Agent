"""Setup Wizard 测试"""
import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys


@pytest.fixture
def isolated_config():
    """创建隔离的配置环境"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".handsome_agent"
        config_dir.mkdir()
        
        # 保存原始值
        original_config_dir = os.environ.get('HANDSOME_HOME')
        original_home = os.environ.get('HOME')
        
        # 设置测试环境
        os.environ['HANDSOME_HOME'] = str(config_dir)
        
        yield config_dir
        
        # 恢复原始环境
        if original_config_dir:
            os.environ['HANDSOME_HOME'] = original_config_dir
        elif 'HANDSOME_HOME' in os.environ:
            del os.environ['HANDSOME_HOME']
        
        if original_home:
            os.environ['HOME'] = original_home


class TestSetupWizard:
    """Setup Wizard 功能测试"""
    
    def test_should_quit(self):
        """测试退出命令检测"""
        from cli.setup.setup_wizard import should_quit
        
        assert should_quit('quit') == True
        assert should_quit('exit') == True
        assert should_quit('q') == True
        assert should_quit('退出') == True
        assert should_quit('Q') == True
        assert should_quit('Exit') == True
        assert should_quit('continue') == False
        assert should_quit('next') == False
    
    def test_load_config_empty(self, isolated_config):
        """测试加载空配置"""
        from cli.setup.setup_wizard import load_config
        
        config = load_config()
        
        # 如果没有配置文件，应该返回空字典或默认值
        assert isinstance(config, dict)
    
    def test_load_config_json(self, isolated_config):
        """测试加载 JSON 配置文件"""
        from cli.setup.setup_wizard import load_config
        
        config_file = isolated_config / "config.json"
        test_config = {
            "language": "zh",
            "llm": {
                "provider": "openai",
                "model": "gpt-4"
            }
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
        
        config = load_config()
        
        # 检查结构（可能已经被合并了默认值）
        assert 'language' in config or 'language' in config.get('language', {})
    
    def test_save_config(self, isolated_config):
        """测试保存配置"""
        from cli.setup.setup_wizard import save_config, load_config
        
        test_config = {
            "language": "zh",
            "terminal": {
                "backend": "local"
            }
        }
        save_config(test_config)
        
        config_file = isolated_config / "config.json"
        assert config_file.exists()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded["language"] == "zh"
        assert loaded["terminal"]["backend"] == "local"
    
    def test_has_existing_config_false(self, isolated_config):
        """测试配置文件不存在"""
        from cli.setup.setup_wizard import has_existing_config
        
        assert has_existing_config() == False
    
    def test_has_existing_config_json(self, isolated_config):
        """测试 JSON 配置文件存在"""
        from cli.setup.setup_wizard import has_existing_config
        
        config_file = isolated_config / "config.json"
        config_file.write_text("{}")
        
        assert has_existing_config() == True
    
    def test_show_current_config_empty(self, capsys):
        """测试显示空配置"""
        from cli.setup.setup_wizard import show_current_config
        
        config = {}
        show_current_config(config)
        
        captured = capsys.readouterr()
        assert "📋 当前配置:" in captured.out
    
    def test_show_current_config_full(self, capsys):
        """测试显示完整配置"""
        from cli.setup.setup_wizard import show_current_config
        
        config = {
            "language": "zh",
            "llm": {
                "provider": "openai",
                "model": "gpt-4"
            },
            "model": {
                "max_tokens": 4096,
                "temperature": 0.7
            },
            "terminal": {
                "backend": "local",
                "timeout": 60
            },
            "session_reset": {
                "mode": "both",
                "at_hour": 4,
                "idle_minutes": 1440
            },
            "memory": {
                "enabled": True,
                "vector_store": "sqlite"
            },
            "compression": {
                "enabled": True,
                "threshold": 0.85
            }
        }
        show_current_config(config)
        
        captured = capsys.readouterr()
        assert "🌐 显示语言" in captured.out or "🤖 大模型" in captured.out
        assert "💻 Terminal 后端" in captured.out or "🔄 Session 重置" in captured.out
    
    def test_show_current_config_invalid(self, capsys):
        """测试传入无效配置"""
        from cli.setup.setup_wizard import show_current_config
        
        # 不应该崩溃
        show_current_config(None)
        show_current_config("invalid")
        show_current_config([1, 2, 3])
    
    def test_setup_language(self, isolated_config, monkeypatch):
        """测试语言设置"""
        # Mock ask_choice
        def mock_ask_choice(question, options, default=0, current_value=None):
            return 0  # 选择第一个选项
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_choice', mock_ask_choice)
        
        from cli.setup.setup_wizard import setup_language
        
        config = {}
        result = setup_language(config)
        
        assert result is not None
        assert result["language"] == "zh"
    
    def test_setup_language_cancel(self, isolated_config, monkeypatch):
        """测试取消语言设置"""
        def mock_ask_choice(question, options, default=0, current_value=None):
            return None
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_choice', mock_ask_choice)
        
        from cli.setup.setup_wizard import setup_language
        
        config = {}
        result = setup_language(config)
        
        assert result is None
    
    def test_setup_model_config(self, isolated_config, monkeypatch):
        """测试模型参数配置"""
        inputs = iter(["8192", "0.8", "64000"])
        def mock_ask_input(question, default=None, password=False, required=True):
            return next(inputs)
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_input', mock_ask_input)
        
        from cli.setup.setup_wizard import setup_model_config
        
        config = {}
        result = setup_model_config(config)
        
        assert result is not None
        assert result["max_tokens"] == 8192
        assert result["temperature"] == 0.8
        assert result["context_window"] == 64000
    
    def test_setup_model_config_defaults(self, isolated_config, monkeypatch):
        """测试使用默认值"""
        def mock_ask_input(question, default=None, password=False, required=True):
            return ""  # 空输入使用默认值
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_input', mock_ask_input)
        
        from cli.setup.setup_wizard import setup_model_config
        
        config = {}
        result = setup_model_config(config)
        
        assert result is not None
        assert result["max_tokens"] == 4096
        assert result["temperature"] == 0.7
        assert result["context_window"] == 128000
    
    def test_setup_terminal_local(self, isolated_config, monkeypatch):
        """测试本地 Terminal 配置"""
        def mock_ask_choice(question, options, default=0, current_value=None):
            return 0  # local
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_choice', mock_ask_choice)
        
        from cli.setup.setup_wizard import setup_terminal
        
        config = {}
        result = setup_terminal(config)
        
        assert result is not None
        assert result["backend"] == "local"
    
    def test_setup_agent_settings(self, isolated_config, monkeypatch):
        """测试 Agent 设置"""
        inputs = ["20", "120"]
        def mock_ask_input(question, default=None, password=False, required=True):
            return inputs.pop(0) if inputs else default
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_input', mock_ask_input)
        
        from cli.setup.setup_wizard import setup_agent_settings
        
        config = {}
        result = setup_agent_settings(config)
        
        assert result is not None
        assert result["max_iterations"] == 20
        assert result["timeout_seconds"] == 120.0
    
    def test_setup_session_reset(self, isolated_config, monkeypatch):
        """测试 Session 重置策略"""
        def mock_ask_choice(question, options, default=0, current_value=None):
            return 0  # both mode
        
        inputs = ["8", "60"]
        def mock_ask_input_fixed(question, default=None, password=False, required=True):
            if "小时" in question or "at_hour" in question:
                return "8"
            elif "分钟" in question or "idle" in question:
                return "60"
            return default
        
        def mock_ask_yes_no(question, default=True):
            return True
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_choice', mock_ask_choice)
        monkeypatch.setattr('cli.setup.setup_wizard.ask_input', mock_ask_input_fixed)
        monkeypatch.setattr('cli.setup.setup_wizard.ask_yes_no', mock_ask_yes_no)
        
        from cli.setup.setup_wizard import setup_session_reset
        
        config = {}
        result = setup_session_reset(config)
        
        assert result is not None
        assert result["mode"] == "both"
    
    def test_setup_memory(self, isolated_config, monkeypatch):
        """测试记忆系统配置"""
        def mock_ask_yes_no(question, default=True):
            return True
        
        def mock_ask_choice(question, options, default=0, current_value=None):
            return 0  # sqlite
        
        inputs = ["text-embedding-3-small", "500"]
        def mock_ask_input(question, default=None, password=False, required=True):
            return inputs.pop(0) if inputs else default
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_yes_no', mock_ask_yes_no)
        monkeypatch.setattr('cli.setup.setup_wizard.ask_choice', mock_ask_choice)
        monkeypatch.setattr('cli.setup.setup_wizard.ask_input', mock_ask_input)
        
        from cli.setup.setup_wizard import setup_memory
        
        config = {}
        result = setup_memory(config)
        
        assert result is not None
        assert result["enabled"] == True
    
    def test_setup_compression(self, isolated_config, monkeypatch):
        """测试 Context 压缩配置"""
        def mock_ask_yes_no(question, default=True):
            return True
        
        inputs = ["0.9", "gpt-4"]
        def mock_ask_input(question, default=None, password=False, required=True):
            return inputs.pop(0) if inputs else default
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_yes_no', mock_ask_yes_no)
        monkeypatch.setattr('cli.setup.setup_wizard.ask_input', mock_ask_input)
        
        from cli.setup.setup_wizard import setup_compression
        
        config = {}
        result = setup_compression(config)
        
        assert result is not None
        assert result["enabled"] == True
        assert result["threshold"] == 0.9
    
    def test_setup_debug(self, isolated_config, monkeypatch):
        """测试 Debug 配置"""
        def mock_ask_yes_no(question, default=True):
            return True
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_yes_no', mock_ask_yes_no)
        
        from cli.setup.setup_wizard import setup_debug
        
        config = {}
        result = setup_debug(config)
        
        assert result is not None
        assert result["web_tools"] == True
        assert result["vision_tools"] == True
        assert result["moa_tools"] == True
        assert result["image_tools"] == True
    
    def test_setup_depth(self, isolated_config, monkeypatch):
        """测试响应详细程度配置"""
        def mock_ask_choice(question, options, default=0, current_value=None):
            return 0  # brief
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_choice', mock_ask_choice)
        
        from cli.setup.setup_wizard import setup_depth
        
        config = {}
        result = setup_depth(config)
        
        assert result is not None
        assert result["explanation_depth"] == "brief"
    
    def test_setup_caching(self, isolated_config, monkeypatch):
        """测试响应缓存配置"""
        def mock_ask_yes_no(question, default=True):
            return False
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_yes_no', mock_ask_yes_no)
        
        from cli.setup.setup_wizard import setup_caching
        
        config = {}
        result = setup_caching(config)
        
        assert result is not None
        assert result["enable_caching"] == False
    
    def test_setup_intent(self, isolated_config, monkeypatch):
        """测试意图识别配置"""
        def mock_ask_choice(question, options, default=0, current_value=None):
            return 2  # keyword
        
        monkeypatch.setattr('cli.setup.setup_wizard.ask_choice', mock_ask_choice)
        
        from cli.setup.setup_wizard import setup_intent
        
        config = {}
        result = setup_intent(config)
        
        assert result is not None
        assert result["intent_mode"] == "keyword"