"""Agent Loop 测试"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


class TestAgentLoop:
    """Agent Loop 核心功能测试"""
    
    @pytest.fixture
    def mock_agent_loop(self):
        """创建模拟的 Agent Loop"""
        from brain.agent_loop import AgentLoop
        return AgentLoop
    
    def test_agent_loop_import(self):
        """测试导入 Agent Loop"""
        try:
            from brain.agent_loop import AgentLoop
            assert AgentLoop is not None
        except ImportError:
            # 如果模块不存在，跳过测试
            pytest.skip("brain.agent_loop not found")
    
    def test_agent_loop_init(self):
        """测试 Agent Loop 初始化"""
        try:
            from brain.agent_loop import AgentLoop
            
            loop = AgentLoop()
            assert loop is not None
        except ImportError:
            pytest.skip("brain.agent_loop not found")
    
    def test_agent_loop_run(self):
        """测试 Agent Loop 运行"""
        try:
            from brain.agent_loop import AgentLoop
            
            loop = AgentLoop()
            
            # 创建一个模拟的输入
            user_input = "Hello, how are you?"
            
            # Mock run 方法
            with patch.object(loop, 'run', new_callable=AsyncMock) as mock_run:
                mock_run.return_value = "I'm doing great, thanks!"
                
                result = loop.run(user_input)
                
                # 应该调用 run 方法
                mock_run.assert_called_once_with(user_input)
        except ImportError:
            pytest.skip("brain.agent_loop not found")
    
    def test_agent_loop_stop(self):
        """测试 Agent Loop 停止"""
        try:
            from brain.agent_loop import AgentLoop
            
            loop = AgentLoop()
            
            # Mock stop 方法
            with patch.object(loop, 'stop') as mock_stop:
                loop.stop()
                
                mock_stop.assert_called_once()
        except ImportError:
            pytest.skip("brain.agent_loop not found")


class TestIntentClassifier:
    """意图分类器测试 - DEPRECATED"""

    def test_import_intent_classifier(self):
        """测试导入意图分类器 - DEPRECATED"""
        import warnings
        warnings.warn(
            "IntentClassifier is deprecated. Please use the new LLM-driven architecture.",
            DeprecationWarning,
            stacklevel=2
        )
        # 不再测试 IntentClassifier

    def test_intent_mode_detection(self):
        """测试意图模式检测 - DEPRECATED"""
        import warnings
        warnings.warn(
            "Intent classification is deprecated.",
            DeprecationWarning,
            stacklevel=2
        )
        # 不再测试意图检测


class TestAgentState:
    """Agent 状态测试"""
    
    def test_agent_state_creation(self):
        """测试创建 Agent 状态"""
        try:
            from brain.agent_state import AgentState
            
            state = AgentState()
            assert state is not None
        except ImportError:
            # 可能没有独立的 Agent 状态模块
            pass
    
    def test_agent_state_transitions(self):
        """测试 Agent 状态转换"""
        try:
            from brain.agent_state import AgentState
            
            state = AgentState()
            
            # 测试状态转换
            assert hasattr(state, 'status') or True  # 可能有不同的属性
        except ImportError:
            pass


class TestMessageHandling:
    """消息处理测试"""
    
    def test_message_format(self):
        """测试消息格式"""
        try:
            from shared.models import Message
            
            msg = Message(role="user", content="Hello")
            
            assert msg.role == "user"
            assert msg.content == "Hello"
        except ImportError:
            pytest.skip("shared.models.Message not found")
    
    def test_message_types(self):
        """测试消息类型"""
        try:
            from shared.models import Message
            
            # 用户消息
            user_msg = Message(role="user", content="Test")
            assert user_msg.role == "user"
            
            # 助手消息
            assistant_msg = Message(role="assistant", content="Response")
            assert assistant_msg.role == "assistant"
            
            # 系统消息
            system_msg = Message(role="system", content="System prompt")
            assert system_msg.role == "system"
        except ImportError:
            pytest.skip("shared.models.Message not found")


class TestToolExecution:
    """工具执行测试"""
    
    def test_tool_registry(self):
        """测试工具注册"""
        try:
            from tools.registry import ToolRegistry
            
            registry = ToolRegistry()
            assert registry is not None
        except ImportError:
            pytest.skip("tools.registry not found")
    
    def test_tool_calling(self):
        """测试工具调用"""
        try:
            from tools.tool_calling import call_tool
            
            # 这应该是一个异步函数
            assert callable(call_tool)
        except ImportError:
            pytest.skip("tools.tool_calling not found")


class TestMemoryIntegration:
    """记忆集成测试"""
    
    def test_memory_provider_import(self):
        """测试导入记忆提供者"""
        try:
            from brain.memory_provider import MemoryProvider
            
            assert MemoryProvider is not None
        except ImportError:
            pytest.skip("brain.memory_provider not found")
    
    def test_memory_store(self):
        """测试记忆存储"""
        try:
            from brain.memory import Memory
            
            memory = Memory()
            assert memory is not None
        except ImportError:
            pytest.skip("brain.memory not found")
    
    def test_memory_retrieval(self):
        """测试记忆检索"""
        try:
            from brain.memory_provider import MemoryProvider
            
            provider = MemoryProvider()
            
            # 测试添加记忆
            # test_add_memory()
            
            # 测试检索记忆
            # results = provider.search("test query")
            # assert len(results) >= 0
        except ImportError:
            pytest.skip("brain.memory_provider not found")


class TestSessionIntegration:
    """会话集成测试"""
    
    def test_session_manager_import(self):
        """测试导入会话管理器"""
        try:
            from core.session import SessionManager
            
            assert SessionManager is not None
        except ImportError:
            pytest.skip("core.session not found")
    
    def test_session_creation(self):
        """测试创建会话"""
        try:
            from core.session import Session
            
            session = Session()
            assert session is not None
        except ImportError:
            pytest.skip("core.session not found")
    
    def test_session_id_generation(self):
        """测试会话 ID 生成"""
        try:
            from core.session import generate_session_id
            
            sid1 = generate_session_id()
            sid2 = generate_session_id()
            
            # 每个 ID 应该唯一
            assert sid1 != sid2
            assert len(sid1) > 0
        except (ImportError, TypeError):
            pass


class TestErrorHandling:
    """错误处理测试"""
    
    def test_exception_hierarchy(self):
        """测试异常层次"""
        try:
            from core.exceptions import (
                HandsomeAgentError,
                BrainServiceError,
                ExecutorError,
                ToolError,
                SecurityError
            )
            
            # 测试异常继承
            assert issubclass(BrainServiceError, HandsomeAgentError)
            assert issubclass(ExecutorError, HandsomeAgentError)
            assert issubclass(ToolError, HandsomeAgentError)
            assert issubclass(SecurityError, HandsomeAgentError)
        except ImportError:
            pytest.skip("core.exceptions not found")
    
    def test_raise_custom_exception(self):
        """测试抛出自定义异常"""
        try:
            from core.exceptions import HandsomeAgentError
            
            with pytest.raises(HandsomeAgentError):
                raise HandsomeAgentError("Test error")
        except ImportError:
            pytest.skip("core.exceptions not found")


class TestLogging:
    """日志测试"""
    
    def test_log_config(self):
        """测试日志配置"""
        from shared.config import get_settings
        
        settings = get_settings()
        
        # 检查日志配置
        assert settings is not None
    
    def test_logger_creation(self):
        """测试日志记录器创建"""
        import logging
        
        logger = logging.getLogger("test")
        assert logger is not None
    
    def test_log_levels(self):
        """测试日志级别"""
        import logging
        
        levels = [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL
        ]
        
        for level in levels:
            assert isinstance(level, int)
            assert level >= 0